#!/usr/bin/env node
/**
 * Doc-to-Markdown benchmark scorer: PackForAI vs Microsoft MarkItDown.
 *
 *   node score.mjs <corpusDir> <outDir> > results.json
 *
 * For every <corpusDir>/ground-truth/*.json it scores three candidate outputs:
 * <file>.packforai.document.md, <file>.packforai.compact.md and
 * <file>.markitdown.md. Each is looked up directly in <outDir>, or in the
 * sub-folder of <outDir> that mirrors the corpus file's folder (the layout
 * run_markitdown.py writes). A missing output is scored as empty text and
 * flagged. One JSON report goes to stdout, a short summary to stderr. The report
 * carries the exact normalization rules, metric definitions, tokenizer and
 * runtime versions, per-file metrics and macro-averaged aggregates.
 * SCORING.md (next to this file) explains each rule change since 1.1.0.
 *
 * Exit status: 0 scored; 1 report printed, but a ground-truth file was invalid
 * (skipped) or none was found; 2 usage error (nothing on stdout).
 *
 * Read-only: never writes files. Dependencies: Node built-ins and gpt-tokenizer.
 */

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { countTokens } from 'gpt-tokenizer/encoding/o200k_base';

export const SCORER_VERSION = '1.2.0';

export const CANDIDATES = Object.freeze([
  Object.freeze({ key: 'packforai.document', suffix: '.packforai.document.md' }),
  Object.freeze({ key: 'packforai.compact', suffix: '.packforai.compact.md' }),
  Object.freeze({ key: 'markitdown', suffix: '.markitdown.md' }),
]);
export const BASELINE = 'markitdown';
export const FORMATS = Object.freeze(['pdf', 'docx', 'xlsx', 'pptx', 'csv', 'json']);
export const CHECK_KEYS = Object.freeze(['must_contain', 'ordered', 'headings', 'tables', 'noise', 'absent']);

const SELF_PATH = fileURLToPath(import.meta.url);
const TOKENIZER_PACKAGE_JSON = createRequire(import.meta.url).resolve('gpt-tokenizer/package.json');
const MAX_INDEXED_ENTRIES = 200000;

export const TOKENIZER = Object.freeze({
  name: 'o200k_base',
  package: 'gpt-tokenizer',
  version: JSON.parse(fs.readFileSync(TOKENIZER_PACKAGE_JSON, 'utf8')).version,
  import: "import { countTokens } from 'gpt-tokenizer/encoding/o200k_base'",
  resolved_package_dir: toPosix(path.relative(path.dirname(SELF_PATH), path.dirname(TOKENIZER_PACKAGE_JSON))),
  counted_text: 'each output file exactly as stored, decoded as UTF-8 (no normalization; line endings and any BOM are kept)',
  special_tokens:
    "strings such as '<|endoftext|>' are counted as ordinary text: countTokens(text, { disallowedSpecial: new Set() }), like tiktoken's disallowed_special=()",
});

// ---------------------------------------------------------------------------
// Normalization
// ---------------------------------------------------------------------------

export const NORMALIZATION = Object.freeze({
  steps: [
    "1. Unicode NFKC: text.normalize('NFKC') (ligatures, full-width forms and no-break spaces become plain characters)",
    '2. Case-insensitive: String.prototype.toLowerCase() (locale-independent Unicode default lowercase mapping)',
    "3. Markdown emphasis and escape characters are deleted: every '*', '_', '\\' and '`'",
    "4. Table pipes: every '|' becomes a space, so '|a|b|' and '| a | b |' both read 'a b'",
    "5. NFKC again, so a deletion cannot leave an unnormalized sequence (e.g. 'e', '*', combining acute)",
    '6. Whitespace: every run of JavaScript \\s characters (Unicode White_Space incl. line breaks, tabs, NBSP, U+FEFF) becomes one space; the ends are trimmed',
  ],
  applied_to:
    'the candidate output and every ground-truth string (must_contain phrases, ordered anchors, headings, table cells, noise texts, absent strings) before they are compared',
  text_and_order_only:
    "after steps 1-6, for must_contain phrases and ordered anchors (on both sides) a hyphen-minus between a letter or digit and a letter loses the space that follows it: /([\\p{L}\\p{N}])- (?=\\p{L})/gu -> '$1-', so a compound broken at a line end ('per-' + line break + 'pound', '40,000-' + line break + 'pound') reads 'per-pound', '40,000-pound'. A split word ('regu-' + line break + 'lation') becomes 'regu-lation', which still differs from 'regulation'. Not applied to headings, table cells, noise or absent strings.",
  table_cells_only:
    "after steps 1-6, a table cell (expected or parsed) that is a number written with comma thousands separators loses those commas: the whole cell must match /^(?:[a-z]{3} ?)?[(+\\-\\u2212]?[$€£¥]?[(+\\-\\u2212]?\\d{1,3}(?:,\\d{3})+(?:\\.\\d+)?%?\\)?\\.?$/u (optional three-letter currency code, sign, parenthesis and currency symbol; groups of exactly 3 digits; optional decimals, '%', ')' and a final '.'); signs, decimals, currency and parentheses are kept, so '1,849,906' = '1849906' and '$7,560.00' = '$7560.00' but '$7,560.00' != '7560'.",
  matching:
    'must_contain, ordered and noise match as substrings of the normalized output (no word-boundary rule); absent strings use the word-boundary and split-word rule of absent_violations; table cells must be equal after normalization',
  not_unified:
    "nothing else is unified: curly vs straight quotes, dash and hyphen variants, soft hyphens (U+00AD), zero-width characters, HTML entities, <br> and CSV's doubled quotes outside parsed CSV tables stay distinct; other Markdown syntax ('#', '-', '>', list numbers, link brackets) stays in the text",
});

/** Normalizes text for matching; see NORMALIZATION.steps (same order). */
export function normalize(text) {
  return String(text ?? '')
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[*_\\`]/g, '')
    .replace(/\|/g, ' ')
    .normalize('NFKC')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * normalize() plus the compound-hyphen rule used by must_contain and ordered (both sides): a
 * hyphen between a letter or digit and a letter keeps no space after it ('per- pound' -> 'per-pound').
 */
export function normalizeText(text) {
  return normalize(text).replace(/([\p{L}\p{N}])- (?=\p{L})/gu, '$1-');
}

const GROUPED_NUMBER_CELL = /^(?:[a-z]{3} ?)?[(+\-\u2212]?[$€£¥]?[(+\-\u2212]?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?\)?\.?$/u;

/** normalize() for a table cell: a whole-cell number loses its comma thousands separators. */
export function normalizeCell(text) {
  const n = normalize(text);
  return GROUPED_NUMBER_CELL.test(n) ? n.replace(/(?<=\d),(?=\d{3})/g, '') : n;
}

export const METRIC_DEFINITIONS = Object.freeze({
  text_recall:
    'found / total over checks.must_contain; a phrase is found when its normalized text is a substring of the normalized output, both normalized with the compound-hyphen rule (normalization.text_and_order_only). null when must_contain is empty.',
  order_score:
    "Each anchor's position is the first occurrence of its normalized text in the normalized output (both with the compound-hyphen rule of normalization.text_and_order_only). order_score = length of the longest strictly increasing subsequence of the positions of the anchors that were found, taken in ground-truth order, divided by the number of anchors; a missing anchor counts as not in order. not_in_order lists the found anchors outside one such longest subsequence (when several tie, the one patience sorting reconstructs, which ends at the smallest position; ties never change the score). null when ordered is empty.",
  heading_recall:
    "Heading lines are CommonMark ATX headings outside fenced code blocks: up to 3 spaces of indentation, 1-6 '#', then a space, a tab or the end of the line; an optional closing run of '#' is dropped. Setext (underlined) headings, bold lines and HTML headings do not count. An expected heading is found when its normalized text is a substring of the normalized text of a heading line; each heading line can satisfy at most one expected heading (maximum one-to-one matching). heading_recall = found / total; null when headings is empty.",
  table_recall:
    "The headline table metric. Pipe tables are parsed like GFM tables, outside fenced code blocks: a header line followed by a delimiter line (cells of the form :?-+:?, at least one unescaped '|', the same cell count as the header line), then body lines until a blank line, a line without an unescaped '|', an ATX heading or a code fence (one deliberate difference from GFM: a non-blank line without a '|' right after a table ends it instead of becoming a one-cell row); body rows are padded with empty cells or cut to the header width; '\\|' does not split cells. CSV blocks are parsed as tables too (RFC 4180: comma-separated, a field holding a comma, quote or line break is quoted, a doubled quote inside quotes is one quote): (1) a fenced code block whose info string starts with 'csv', with at least 2 records and a header of at least 2 fields (rows padded or cut to the header width; a block with an unterminated quote or a stray quote is not a table); (2) outside code fences, a paragraph (a run of non-blank lines that are not ATX headings, fences or pipe-table lines) whose lines, after at most one leading caption line, are all one-line CSV records with the same field count of at least 2, at least 2 records in all; a record must not start with a Markdown block marker ('>', '- ', '* ', '+ ', '1. ', '1) '), and no unquoted field may start or end with whitespace (so prose with ', ' never qualifies). The caption line is not part of the table. Parsed tables of both kinds are used in document order. Cells are compared after normalization.table_cells_only (comma thousands separators dropped from whole-cell numbers on both sides). A column of a parsed table that is empty in every row, header included, is padding: each parsed table is scored as written and again with such columns dropped, and the variant with more matching cells is kept (as written on a tie); column indices reported always refer to the table as written. For each expected table, every parsed table is scored: (a) columns are paired by equal non-empty normalized header text, one-to-one, left to right; (b) each other expected column is paired by position, keeping the column offset of the nearest header-paired column (looking left first, then right; offset 0 when no column was paired by header), if that column exists and is free; (c) expected columns still unpaired take the remaining free columns left to right; (d) rows, header rows included, are aligned in order by dynamic programming to maximize the number of matching cells. A matching cell is an aligned pair of cells with equal, non-empty normalized text; an aligned row pair whose only matching cell is a number (a cell without a letter) does not count, unless it is the only non-empty cell of the expected row (a lone shared '5' or '2024', such as a table-of-contents page number, is no evidence that two rows correspond; a lone row label such as 'Bob' still counts). Cells that are empty after normalization are not counted on either side. recall R = matching cells / non-empty expected cells; precision P = matching cells / non-empty cells of the parsed table; F1 = 2PR / (P + R), 0 when P + R = 0. Separately for each expected table, the parsed table with the highest recall is picked; ties on recall go to the higher precision, then to the earliest table in the output. A parsed table with no matching cell is never picked: when no parsed table has a matching cell (or the output has none), R = P = F1 = 0 and no table is named. table_recall = mean R over expected tables. null when tables is empty.",
  table_precision:
    'Secondary. Mean P over expected tables, each P taken from the same parsed table that table_recall picked. Precision is secondary because an expected table can be partial: it may list only some rows of a larger source table, so a complete, faithful conversion carries correct cells beyond the expected ones, and they lower precision. null when tables is empty.',
  table_f1:
    'Secondary. Mean F1 over expected tables, each F1 computed on the same parsed table that table_recall picked (so it is not the best F1 over all parsed tables). Secondary for the same reason as table_precision. null when tables is empty.',
  spurious_table_cells:
    "Secondary; does not change table_recall. The number of non-empty cells inside parsed tables (pipe and CSV) that sit on no ground-truth table cell. Every parsed table is aligned with every expected table by the table_recall rules (column pairing, empty-column variant, row alignment; a row pair is aligned only when it has matching cells that count under rule (d)). A parsed cell sits on a ground-truth cell when, for at least one expected table, its row is aligned to an expected row, its column is paired with an expected column and that expected cell is non-empty; such a cell is not spurious even when its text differs (a wrong value lowers recall and precision instead). Everything else counts: tables built from prose, rows no expected row aligns with (titles, captions, stray text), placeholder header cells ('Column 2', 'Unnamed: 1') and filler such as 'NaN' where the expected cell is empty. Rows of a real table that the ground truth does not list also count, so compare tools on the same file. tables.per_output_table gives the figure for each parsed table. null when tables is empty.",
  noise_excess:
    'For each noise entry, count the non-overlapping occurrences of its normalized text in the normalized output; excess = max(0, count - max). noise_excess = sum of the excesses. null when noise is empty.',
  absent_violations:
    "Number of absent entries present in the output (each entry counts once). Entry and output are normalized (steps 1-6, no compound-hyphen rule). An entry is present when (a) its normalized text occurs in the normalized output and, if it starts with a letter or digit, the occurrence does not start inside a word (no letter or digit right before it); or (b) the entry is a split word '<prefix>- <rest>' (prefix ending in a letter or digit, rest starting with a letter) and the output, read line by line (each line normalized, blank lines skipped), has '<prefix>-' starting a word and followed by a space or the end of the line, with '<rest>' starting a word later on that line or on one of the next 2 lines. Rule (b) catches a line-end hyphen whose two halves were pulled apart by text from another column; absent.found_split lists the entries found only that way. null when absent is empty.",
  size: 'chars = Unicode code points of the output file as stored; bytes = its UTF-8 bytes; tokens = o200k_base tokens of the same text (see tokenizer). A missing output is empty: 0 / 0 / 0.',
  aggregates:
    'Macro averages: for each candidate, the mean of each per-file score over the files where that check applies (n). Missing outputs are scored as empty text and included. For tables, table_recall is the headline number (the tblRec column of the stderr summary); table_precision and table_f1 are kept beside it as secondary fields. spurious_table_cells (the spur column), noise_excess and absent_violations give their total and mean per file; chars and tokens give totals and means. complete_files = files where every candidate produced an output; tokens.total_on_complete_files sums tokens over those files only, and tokens.ratio_vs_markitdown_on_complete_files divides it by markitdown\'s sum on the same files.',
  rounding: 'Non-integer numbers in the report are rounded to 6 decimal places when written; means are computed from unrounded values.',
});

// ---------------------------------------------------------------------------
// Markdown structure: ATX headings and GFM pipe tables outside code fences
// ---------------------------------------------------------------------------

function parseAtxHeading(line) {
  const m = /^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$/.exec(line);
  if (!m) return null;
  const text = m[2].replace(/(?:^|[ \t]+)#+[ \t]*$/, '').trim();
  return { level: m[1].length, text };
}

function parseFenceOpen(line) {
  const m = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
  if (!m) return null;
  if (m[1][0] === '`' && m[2].includes('`')) return null; // an inline code span, not a fence
  const info = m[2].trim().split(/\s+/)[0].toLowerCase();
  return { char: m[1][0], length: m[1].length, csv: info === 'csv' };
}

function isFenceClose(line, fence) {
  const m = /^ {0,3}(`{3,}|~{3,})[ \t]*$/.exec(line);
  return m !== null && m[1][0] === fence.char && m[1].length >= fence.length;
}

function hasUnescapedPipe(line) {
  for (let i = 0; i < line.length; i += 1) {
    if (line[i] === '\\') i += 1;
    else if (line[i] === '|') return true;
  }
  return false;
}

function isEscapedAt(text, index) {
  let backslashes = 0;
  for (let k = index - 1; k >= 0 && text[k] === '\\'; k -= 1) backslashes += 1;
  return backslashes % 2 === 1;
}

/** Splits one table line into trimmed cells; '\|' stays inside its cell. */
export function splitTableRow(line) {
  let s = line.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|') && !isEscapedAt(s, s.length - 1)) s = s.slice(0, -1);
  const cells = [];
  let cell = '';
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    if (ch === '\\' && i + 1 < s.length) {
      cell += ch + s[i + 1];
      i += 1;
    } else if (ch === '|') {
      cells.push(cell.trim());
      cell = '';
    } else {
      cell += ch;
    }
  }
  cells.push(cell.trim());
  return cells;
}

function fitRow(row, width) {
  return Array.from({ length: width }, (_, i) => (i < row.length ? row[i] : ''));
}

function isDelimiterRow(line, headerCells) {
  if (!/^ {0,3}\S/.test(line) || !hasUnescapedPipe(line)) return false;
  const cells = splitTableRow(line);
  return cells.length === headerCells.length && cells.every((c) => /^:?-+:?$/.test(c));
}

/**
 * RFC 4180 parser: comma-separated fields, '\n' between records; a field that starts with '"' is
 * quoted, may hold commas and line breaks, and '""' inside it is one '"'. Returns
 * [{ line, fields: [{ value, quoted }] }] (line = 0-based line where the record starts), or null
 * when the text is not valid RFC 4180 (an unterminated quote, text after a closing quote, or a '"'
 * inside an unquoted field).
 */
export function parseCsv(text) {
  const s = String(text ?? '');
  const n = s.length;
  const records = [];
  let i = 0;
  let line = 0;
  for (;;) {
    const record = { line, fields: [] };
    for (;;) {
      if (s[i] === '"') {
        let value = '';
        i += 1;
        for (;;) {
          if (i >= n) return null;
          if (s[i] === '"') {
            if (s[i + 1] === '"') {
              value += '"';
              i += 2;
            } else {
              i += 1;
              break;
            }
          } else {
            if (s[i] === '\n') line += 1;
            value += s[i];
            i += 1;
          }
        }
        if (i < n && s[i] !== ',' && s[i] !== '\n') return null;
        record.fields.push({ value, quoted: true });
      } else {
        let j = i;
        while (j < n && s[j] !== ',' && s[j] !== '\n') j += 1;
        const value = s.slice(i, j);
        if (value.includes('"')) return null;
        record.fields.push({ value, quoted: false });
        i = j;
      }
      if (i < n && s[i] === ',') {
        i += 1;
        continue;
      }
      break;
    }
    records.push(record);
    if (i >= n) return records;
    i += 1; // the '\n' that ends the record
    line += 1;
  }
}

const BLOCK_MARKER = /^(?:>|[-*+][ \t]|\d{1,9}[.)][ \t])/;
// A whitespace-delimited token that is a number with comma thousands separators, e.g. '1,450,000',
// '$1,234.50' or '(12,000).': its commas cannot be told apart from field separators.
const GROUPED_NUMBER_TOKEN = /(?:^|\s)[([$€£¥+\-\u2212]*\d{1,3}(?:,\d{3})+(?:\.\d+)?[.,;:!?)\]%-]*(?=\s|$)/u;

/**
 * One line as a bare CSV record (outside fences): the field values, or null when the line is not a
 * complete RFC 4180 record, has fewer than 2 fields, starts with a Markdown block marker, has an
 * unquoted field that starts or ends with whitespace (CSV writers never put a space after the
 * comma), or holds a whitespace-delimited number with comma thousands separators (ambiguous).
 */
export function parseBareCsvLine(line) {
  if (BLOCK_MARKER.test(line) || GROUPED_NUMBER_TOKEN.test(line)) return null;
  const records = parseCsv(line);
  if (records === null || records.length !== 1) return null;
  const { fields } = records[0];
  if (fields.length < 2) return null;
  if (fields.some((f) => !f.quoted && /^\s|\s$/.test(f.value))) return null;
  return fields.map((f) => f.value);
}

/** A paragraph (line indices) as a bare CSV table, or null; see table_recall rule (2). */
function csvParagraphTable(lines, indices) {
  if (indices.length < 2) return null;
  const records = indices.map((i) => parseBareCsvLine(lines[i]));
  const captioned = records[0] === null || records[1] === null || records[0].length !== records[1].length;
  const body = captioned ? records.slice(1) : records;
  if (body.length < 2 || body[0] === null) return null;
  const width = body[0].length;
  if (body.some((r) => r === null || r.length !== width)) return null;
  const first = captioned ? 1 : 0;
  return {
    line: indices[first] + 1,
    kind: 'csv',
    caption: captioned ? lines[indices[0]].trim() : null,
    width,
    rows: body,
  };
}

/** The content of a ```csv fence as a table, or null; see table_recall rule (1). */
function csvFenceTable(lines, firstContentIndex) {
  const records = parseCsv(lines.join('\n'));
  if (records === null) return null;
  const rows = records.filter((r) => !(r.fields.length === 1 && !r.fields[0].quoted && r.fields[0].value.trim() === ''));
  if (rows.length < 2 || rows[0].fields.length < 2) return null;
  const width = rows[0].fields.length;
  return {
    line: firstContentIndex + rows[0].line + 1,
    kind: 'csv',
    caption: null,
    width,
    rows: rows.map((r) => fitRow(r.fields.map((f) => f.value), width)),
  };
}

/** Returns the ATX headings and the tables (pipe and CSV) of a Markdown text (1-based line numbers). */
export function scanMarkdown(text) {
  const lines = String(text ?? '').split(/\r\n|\r|\n/);
  const headings = [];
  const tables = [];
  let fence = null;
  let paragraph = [];
  const flush = () => {
    const table = csvParagraphTable(lines, paragraph);
    if (table) tables.push(table);
    paragraph = [];
  };
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (fence) {
      if (isFenceClose(line, fence)) {
        if (fence.csv) {
          const table = csvFenceTable(lines.slice(fence.start + 1, i), fence.start + 1);
          if (table) tables.push(table);
        }
        fence = null;
      }
      continue;
    }
    const open = parseFenceOpen(line);
    if (open) {
      flush();
      fence = { ...open, start: i };
      continue;
    }
    const heading = parseAtxHeading(line);
    if (heading) {
      flush();
      headings.push({ line: i + 1, level: heading.level, text: heading.text });
      continue;
    }
    if (i + 1 < lines.length && /^ {0,3}\S/.test(line) && hasUnescapedPipe(lines[i + 1])) {
      const header = splitTableRow(line);
      if (isDelimiterRow(lines[i + 1], header)) {
        flush();
        const rows = [header];
        let j = i + 2;
        while (
          j < lines.length &&
          lines[j].trim() !== '' &&
          hasUnescapedPipe(lines[j]) &&
          !parseAtxHeading(lines[j]) &&
          !parseFenceOpen(lines[j])
        ) {
          rows.push(fitRow(splitTableRow(lines[j]), header.length));
          j += 1;
        }
        tables.push({ line: i + 1, kind: 'pipe', width: header.length, rows });
        i = j - 1;
        continue;
      }
    }
    if (line.trim() === '') flush();
    else paragraph.push(i);
  }
  if (fence?.csv) {
    // An unclosed fence runs to the end of the document (CommonMark).
    const table = csvFenceTable(lines.slice(fence.start + 1), fence.start + 1);
    if (table) tables.push(table);
  }
  flush();
  tables.sort((a, b) => a.line - b.line);
  return { headings, tables };
}

/** The GFM pipe tables of a Markdown text (CSV tables are left out). */
export function parsePipeTables(text) {
  return scanMarkdown(text).tables.filter((t) => t.kind === 'pipe');
}

/** Indices of the columns that are empty in every row of a normalized table, header included. */
export function emptyColumns(normRows, width) {
  const empty = [];
  for (let k = 0; k < width; k += 1) if (normRows.every((row) => (row[k] ?? '') === '')) empty.push(k);
  return empty;
}

/** Parses a candidate output once; every metric accepts this object or a plain string. */
export function analyzeOutput(text) {
  const raw = String(text ?? '');
  const { headings, tables } = scanMarkdown(raw);
  return {
    text: raw,
    norm: normalize(raw),
    normText: normalizeText(raw),
    lines: raw
      .split(/\r\n|\r|\n/)
      .map(normalize)
      .filter((l) => l !== ''),
    headings: headings.map((h) => ({ ...h, norm: normalize(h.text) })),
    tables: tables.map((t) => {
      const norm = t.rows.map((row) => row.map(normalizeCell));
      return { ...t, norm, empty_columns: emptyColumns(norm, t.width) };
    }),
  };
}

function asDoc(doc) {
  return doc !== null && typeof doc === 'object' && typeof doc.norm === 'string' ? doc : analyzeOutput(doc);
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export function textRecall(doc, phrases = []) {
  const d = asDoc(doc);
  if (phrases.length === 0) return { score: null, found: 0, total: 0, missing: [] };
  const missing = phrases.filter((p) => !d.normText.includes(normalizeText(p)));
  const found = phrases.length - missing.length;
  return { score: found / phrases.length, found, total: phrases.length, missing };
}

/** Indices (into seq) of one longest strictly increasing subsequence (patience sorting). */
export function longestIncreasingSubsequence(seq) {
  const tails = [];
  const prev = new Array(seq.length).fill(-1);
  for (let i = 0; i < seq.length; i += 1) {
    let lo = 0;
    let hi = tails.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (seq[tails[mid]] < seq[i]) lo = mid + 1;
      else hi = mid;
    }
    if (lo > 0) prev[i] = tails[lo - 1];
    tails[lo] = i;
  }
  const chain = [];
  for (let k = tails.length > 0 ? tails[tails.length - 1] : -1; k !== -1; k = prev[k]) chain.push(k);
  return chain.reverse();
}

export function orderScore(doc, anchors = []) {
  const d = asDoc(doc);
  if (anchors.length === 0) return { score: null, in_order: 0, total: 0, missing: [], not_in_order: [] };
  const positions = anchors.map((a) => d.normText.indexOf(normalizeText(a)));
  const foundIdx = [];
  positions.forEach((p, i) => {
    if (p >= 0) foundIdx.push(i);
  });
  const chain = new Set(longestIncreasingSubsequence(foundIdx.map((i) => positions[i])).map((k) => foundIdx[k]));
  return {
    score: chain.size / anchors.length,
    in_order: chain.size,
    total: anchors.length,
    missing: anchors.filter((_, i) => positions[i] < 0),
    not_in_order: anchors.filter((_, i) => positions[i] >= 0 && !chain.has(i)),
  };
}

export function headingRecall(doc, headings = []) {
  const d = asDoc(doc);
  if (headings.length === 0) return { score: null, found: 0, total: 0, missing: [] };
  const edges = headings.map((h) => {
    const needle = normalize(h);
    const hits = [];
    d.headings.forEach((line, k) => {
      if (line.norm.includes(needle)) hits.push(k);
    });
    return hits;
  });
  // Maximum one-to-one matching of expected headings to heading lines (Kuhn's augmenting paths).
  const owner = new Array(d.headings.length).fill(-1);
  const augment = (i, seen) => {
    for (const k of edges[i]) {
      if (seen[k]) continue;
      seen[k] = true;
      if (owner[k] === -1 || augment(owner[k], seen)) {
        owner[k] = i;
        return true;
      }
    }
    return false;
  };
  for (let i = 0; i < headings.length; i += 1) augment(i, new Array(d.headings.length).fill(false));
  const matched = new Set(owner.filter((i) => i >= 0));
  return {
    score: matched.size / headings.length,
    found: matched.size,
    total: headings.length,
    missing: headings.filter((_, i) => !matched.has(i)),
  };
}

/** Pairs expected columns with candidate columns (rules (a)-(c) of table_recall). -1 = unpaired. */
export function mapColumns(expectedHeader, candidateHeader) {
  const we = expectedHeader.length;
  const wc = candidateHeader.length;
  const map = new Array(we).fill(-1);
  const used = new Array(wc).fill(false);
  const byHeader = new Array(we).fill(false);
  for (let j = 0; j < we; j += 1) {
    if (expectedHeader[j] === '') continue;
    const k = candidateHeader.findIndex((h, idx) => !used[idx] && h === expectedHeader[j]);
    if (k >= 0) {
      map[j] = k;
      used[k] = true;
      byHeader[j] = true;
    }
  }
  for (let j = 0; j < we; j += 1) {
    if (map[j] !== -1) continue;
    let anchor = -1;
    for (let l = j - 1; l >= 0 && anchor < 0; l -= 1) if (byHeader[l]) anchor = l;
    for (let r = j + 1; r < we && anchor < 0; r += 1) if (byHeader[r]) anchor = r;
    const k = anchor < 0 ? j : j + (map[anchor] - anchor);
    if (k >= 0 && k < wc && !used[k]) {
      map[j] = k;
      used[k] = true;
    }
  }
  for (let j = 0; j < we; j += 1) {
    if (map[j] !== -1) continue;
    const k = used.indexOf(false);
    if (k >= 0) {
      map[j] = k;
      used[k] = true;
    }
  }
  return map;
}

// A cell with no letter: a number, possibly with sign, currency, '%' or parentheses.
const NUMBER_ONLY = /^[^\p{L}]*\p{N}[^\p{L}]*$/u;

/**
 * Most matching cells over order-preserving row alignments (rule (d) of table_recall), with one
 * optimal alignment: pairs = [[expectedRow, candidateRow], ...]. A row pair whose only matching
 * cell is a number (no letter) does not count, unless that is the expected row's only non-empty
 * cell: a lone shared '5' or '2024' is no evidence that two rows correspond. The traceback prefers
 * skipping a row over pairing it, so every reported pair has matching cells.
 */
export function alignRowsDetailed(expectedRows, candidateRows, map) {
  const e = expectedRows.length;
  const s = candidateRows.length;
  const w = s + 1;
  const dp = new Int32Array((e + 1) * w);
  for (let i = 1; i <= e; i += 1) {
    const er = expectedRows[i - 1];
    const single = er.filter((c) => c !== '').length === 1;
    for (let r = 1; r <= s; r += 1) {
      const cr = candidateRows[r - 1];
      let same = 0;
      let lone = '';
      for (let j = 0; j < er.length; j += 1) {
        const k = map[j];
        if (k >= 0 && er[j] !== '' && er[j] === cr[k]) {
          same += 1;
          lone = er[j];
        }
      }
      if (same === 1 && !single && NUMBER_ONLY.test(lone)) same = 0;
      dp[i * w + r] = Math.max(dp[(i - 1) * w + r - 1] + same, dp[(i - 1) * w + r], dp[i * w + r - 1]);
    }
  }
  const pairs = [];
  for (let i = e, r = s; i > 0 && r > 0; ) {
    const v = dp[i * w + r];
    if (v === dp[(i - 1) * w + r]) i -= 1;
    else if (v === dp[i * w + r - 1]) r -= 1;
    else {
      pairs.push([i - 1, r - 1]);
      i -= 1;
      r -= 1;
    }
  }
  return { matching: dp[e * w + s], pairs: pairs.reverse() };
}

/** Most matching cells over order-preserving row alignments (rule (d) of table_recall). */
export function alignRows(expectedRows, candidateRows, map) {
  return alignRowsDetailed(expectedRows, candidateRows, map).matching;
}

function countNonEmpty(rows) {
  let n = 0;
  for (const row of rows) for (const cell of row) if (cell !== '') n += 1;
  return n;
}

/**
 * Aligns one expected table (normalized rows) with one parsed table, as written and, when the
 * parsed table has columns that are empty in every row, without them; keeps the variant with more
 * matching cells (as written on a tie). column_map uses the column indices of the table as written.
 */
function alignTable(expectedRows, table) {
  const variants = [null];
  if (table.empty_columns.length > 0 && table.empty_columns.length < table.width) {
    const dropped = new Set(table.empty_columns);
    variants.push([...Array(table.width).keys()].filter((k) => !dropped.has(k)));
  }
  let best = null;
  for (const keep of variants) {
    const rows = keep === null ? table.norm : table.norm.map((row) => keep.map((k) => row[k]));
    const map = mapColumns(expectedRows[0], rows[0]);
    const { matching, pairs } = alignRowsDetailed(expectedRows, rows, map);
    if (best === null || matching > best.matching) {
      best = {
        matching,
        pairs,
        map: keep === null ? map : map.map((k) => (k < 0 ? -1 : keep[k])),
        dropped_empty_columns: keep === null ? [] : table.empty_columns,
      };
    }
  }
  return best;
}

/**
 * Picks, for one expected table, the parsed table with the highest recall; ties on recall go to
 * the higher precision, then to the earliest table. A table with no matching cell is never picked.
 * Adds to onTruth[t] the cells ("row:column") of parsed table t that sit on a non-empty cell of
 * this expected table in its alignment (see spurious_table_cells).
 */
function scoreExpectedTable(expected, parsedTables, onTruth) {
  const width = Math.max(...expected.rows.map((r) => r.length));
  const rows = expected.rows.map((r) => fitRow(r.map(normalizeCell), width));
  const expectedCells = countNonEmpty(rows);
  let best = {
    name: expected.name ?? null,
    recall: 0,
    precision: 0,
    f1: 0,
    matching_cells: 0,
    expected_cells: expectedCells,
    candidate_cells: null,
    matched_table_index: null,
    matched_table_line: null,
    matched_table_kind: null,
    column_map: null,
    dropped_empty_columns: null,
  };
  parsedTables.forEach((table, index) => {
    const aligned = alignTable(rows, table);
    for (const [er, cr] of aligned.pairs) {
      for (let j = 0; j < width; j += 1) {
        if (aligned.map[j] >= 0 && rows[er][j] !== '') onTruth[index].add(`${cr}:${aligned.map[j]}`);
      }
    }
    const matching = aligned.matching;
    const candidateCells = countNonEmpty(table.norm);
    const precision = candidateCells > 0 ? matching / candidateCells : 0;
    const recall = expectedCells > 0 ? matching / expectedCells : 0;
    const f1 = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;
    // Strict comparisons: a full tie keeps the earlier table, and a table with recall 0
    // (hence precision 0) never replaces the initial "no table" result.
    if (recall > best.recall || (recall === best.recall && precision > best.precision)) {
      best = {
        name: best.name,
        recall,
        precision,
        f1,
        matching_cells: matching,
        expected_cells: expectedCells,
        candidate_cells: candidateCells,
        matched_table_index: index,
        matched_table_line: table.line,
        matched_table_kind: table.kind,
        column_map: aligned.map,
        dropped_empty_columns: aligned.dropped_empty_columns,
      };
    }
  });
  return best;
}

export function tableScores(doc, expectedTables = []) {
  const d = asDoc(doc);
  const tablesInOutput = d.tables.length;
  const csvTablesInOutput = d.tables.filter((t) => t.kind === 'csv').length;
  if (expectedTables.length === 0) {
    return {
      recall: null,
      precision: null,
      f1: null,
      spurious_cells: null,
      tables_in_output: tablesInOutput,
      csv_tables_in_output: csvTablesInOutput,
      per_table: [],
      per_output_table: [],
    };
  }
  const onTruth = d.tables.map(() => new Set());
  const perTable = expectedTables.map((t) => scoreExpectedTable(t, d.tables, onTruth));
  const perOutputTable = d.tables.map((t, index) => {
    let cells = 0;
    let spurious = 0;
    t.norm.forEach((row, r) =>
      row.forEach((cell, k) => {
        if (cell === '') return;
        cells += 1;
        if (!onTruth[index].has(`${r}:${k}`)) spurious += 1;
      }),
    );
    return { line: t.line, kind: t.kind, rows: t.rows.length, columns: t.width, cells, spurious_cells: spurious };
  });
  const mean = (key) => perTable.reduce((sum, t) => sum + t[key], 0) / perTable.length;
  return {
    recall: mean('recall'),
    precision: mean('precision'),
    f1: mean('f1'),
    spurious_cells: perOutputTable.reduce((sum, t) => sum + t.spurious_cells, 0),
    tables_in_output: tablesInOutput,
    csv_tables_in_output: csvTablesInOutput,
    per_table: perTable,
    per_output_table: perOutputTable,
  };
}

function countOccurrences(haystack, needle) {
  if (needle === '') return 0;
  let count = 0;
  for (let i = haystack.indexOf(needle); i !== -1; i = haystack.indexOf(needle, i + needle.length)) count += 1;
  return count;
}

export function noiseScore(doc, noise = []) {
  const d = asDoc(doc);
  if (noise.length === 0) return { excess: null, per_entry: [] };
  const perEntry = noise.map(({ text, max }) => {
    const count = countOccurrences(d.norm, normalize(text));
    return { text, max, count, excess: Math.max(0, count - max) };
  });
  return { excess: perEntry.reduce((sum, e) => sum + e.excess, 0), per_entry: perEntry };
}

const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
const NOT_AFTER_WORD = '(?<![\\p{L}\\p{N}])';
/** Lines after the prefix line that rule (b) of absent_violations searches for the rest of a split word. */
export const SPLIT_WORD_LINES = 2;

/** How an absent entry occurs in the output: 'contiguous', 'split' or null (see absent_violations). */
export function findAbsent(doc, entry) {
  const d = asDoc(doc);
  const needle = normalize(entry);
  if (needle === '') return null;
  const lead = /^[\p{L}\p{N}]/u.test(needle) ? NOT_AFTER_WORD : '';
  if (new RegExp(lead + escapeRegExp(needle), 'u').test(d.norm)) return 'contiguous';
  const split = /^(\S*[\p{L}\p{N}])- (\p{L}\S*)$/u.exec(needle);
  if (split === null) return null;
  const prefix = new RegExp(`${NOT_AFTER_WORD}${escapeRegExp(split[1])}-(?= |$)`, 'gu');
  const rest = new RegExp(NOT_AFTER_WORD + escapeRegExp(split[2]), 'u');
  for (let i = 0; i < d.lines.length; i += 1) {
    prefix.lastIndex = 0;
    for (let m = prefix.exec(d.lines[i]); m !== null; m = prefix.exec(d.lines[i])) {
      const after = [d.lines[i].slice(m.index + m[0].length), ...d.lines.slice(i + 1, i + 1 + SPLIT_WORD_LINES)].join(' ');
      if (rest.test(after)) return 'split';
    }
  }
  return null;
}

export function absentScore(doc, absent = []) {
  const d = asDoc(doc);
  if (absent.length === 0) return { violations: null, found: [], found_split: [] };
  const found = [];
  const foundSplit = [];
  for (const a of absent) {
    const how = findAbsent(d, a);
    if (how !== null) found.push(a);
    if (how === 'split') foundSplit.push(a);
  }
  return { violations: found.length, found, found_split: foundSplit };
}

export function sizeOf(text) {
  const raw = String(text ?? '');
  let chars = 0;
  for (const _ of raw) chars += 1; // code points, not UTF-16 units
  return {
    chars,
    bytes: Buffer.byteLength(raw, 'utf8'),
    tokens: countTokens(raw, { disallowedSpecial: new Set() }),
  };
}

/** Scores one candidate output against one file's checks. text === null means missing. */
export function scoreCandidate(text, checks = {}) {
  const missing = text === null || text === undefined;
  const d = analyzeOutput(missing ? '' : text);
  return {
    missing,
    size: sizeOf(d.text),
    text_recall: textRecall(d, checks.must_contain ?? []),
    order: orderScore(d, checks.ordered ?? []),
    heading_recall: headingRecall(d, checks.headings ?? []),
    tables: tableScores(d, checks.tables ?? []),
    noise: noiseScore(d, checks.noise ?? []),
    absent: absentScore(d, checks.absent ?? []),
  };
}

// ---------------------------------------------------------------------------
// Ground-truth validation
// ---------------------------------------------------------------------------

const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

/** Returns { errors, warnings }; any error means the file cannot be scored fairly. */
export function validateGroundTruth(gt, gtFileName = null) {
  const errors = [];
  const warnings = [];
  if (!isObject(gt)) return { errors: ['the ground truth must be a JSON object'], warnings };

  if (typeof gt.file !== 'string' || gt.file.trim() === '') errors.push('"file" must be a non-empty string');
  else if (/[\\/\0]/.test(gt.file) || gt.file === '.' || gt.file === '..') {
    errors.push('"file" must be a bare file name (no path separators)');
  } else if (gtFileName !== null && gtFileName !== `${gt.file}.json`) {
    warnings.push(`ground-truth file is named "${gtFileName}", expected "${gt.file}.json"`);
  }
  if (!FORMATS.includes(gt.format)) errors.push(`"format" must be one of: ${FORMATS.join(', ')}`);
  else if (typeof gt.file === 'string') {
    const ext = path.extname(gt.file).slice(1).toLowerCase();
    if (ext !== gt.format) warnings.push(`file extension ".${ext}" does not match format "${gt.format}"`);
  }
  if (!['generated', 'public'].includes(gt.origin)) warnings.push('"origin" should be "generated" or "public"');
  if (typeof gt.sha256 !== 'string' || !/^[0-9a-f]{64}$/i.test(gt.sha256)) {
    warnings.push('"sha256" should be the 64-digit hex SHA-256 of the corpus file');
  }

  const checks = gt.checks;
  if (!isObject(checks)) {
    errors.push('"checks" must be an object');
    return { errors, warnings };
  }
  for (const key of CHECK_KEYS) {
    if (!Object.hasOwn(checks, key)) errors.push(`checks.${key} is missing (use [] when it does not apply)`);
  }
  for (const key of Object.keys(checks)) {
    if (!CHECK_KEYS.includes(key)) warnings.push(`checks.${key} is not a known check and is ignored`);
  }

  const strings = {};
  for (const key of ['must_contain', 'ordered', 'headings', 'absent']) {
    strings[key] = [];
    const list = checks[key];
    if (list === undefined) continue;
    if (!Array.isArray(list)) {
      errors.push(`checks.${key} must be an array of strings`);
      continue;
    }
    list.forEach((s, i) => {
      if (typeof s !== 'string') errors.push(`checks.${key}[${i}] must be a string`);
      else if (normalize(s) === '') errors.push(`checks.${key}[${i}] is empty after normalization`);
      else strings[key].push(s);
    });
    const seen = new Set();
    for (const s of strings[key]) {
      const n = normalize(s);
      if (seen.has(n)) {
        if (key === 'ordered') errors.push(`checks.ordered lists "${s}" twice; identical anchors can never all be in order`);
        else if (key !== 'headings') warnings.push(`checks.${key} lists "${s}" more than once`);
      }
      seen.add(n);
    }
  }
  const ordered = strings.ordered;
  if (ordered.length > 0 && (ordered.length < 4 || ordered.length > 8)) {
    warnings.push(`checks.ordered has ${ordered.length} anchors; the schema asks for 4-8`);
  }
  for (const a of ordered) {
    for (const b of ordered) {
      const na = normalize(a);
      const nb = normalize(b);
      if (na !== nb && nb.includes(na)) {
        warnings.push(`checks.ordered anchor "${a}" also occurs inside anchor "${b}"; its first position may come from that anchor`);
      }
    }
  }

  const tables = [];
  if (checks.tables !== undefined) {
    if (!Array.isArray(checks.tables)) errors.push('checks.tables must be an array');
    else {
      checks.tables.forEach((t, i) => {
        const label = `checks.tables[${i}]`;
        if (!isObject(t)) {
          errors.push(`${label} must be an object with "name" and "rows"`);
          return;
        }
        if (typeof t.name !== 'string' || t.name.trim() === '') warnings.push(`${label}.name should be a non-empty string`);
        if (!Array.isArray(t.rows) || t.rows.length === 0) {
          errors.push(`${label}.rows must be a non-empty array of rows`);
          return;
        }
        let valid = true;
        t.rows.forEach((row, r) => {
          if (!Array.isArray(row) || row.length === 0) {
            errors.push(`${label}.rows[${r}] must be a non-empty array of strings`);
            valid = false;
            return;
          }
          row.forEach((cell, c) => {
            if (typeof cell !== 'string') {
              errors.push(`${label}.rows[${r}][${c}] must be a string (cell text as a reader sees it)`);
              valid = false;
            }
          });
        });
        if (!valid) return;
        const widths = [...new Set(t.rows.map((row) => row.length))];
        if (widths.length > 1) warnings.push(`${label} has rows of different lengths (${widths.join(', ')}); short rows are padded with empty cells`);
        if (!t.rows.some((row) => row.some((cell) => normalize(cell) !== ''))) errors.push(`${label} has no non-empty cell`);
        if (t.rows.length < 2) warnings.push(`${label} has only a header row`);
        tables.push(t);
      });
    }
  }

  const noise = [];
  if (checks.noise !== undefined) {
    if (!Array.isArray(checks.noise)) errors.push('checks.noise must be an array');
    else {
      checks.noise.forEach((n, i) => {
        const label = `checks.noise[${i}]`;
        if (!isObject(n)) {
          errors.push(`${label} must be an object with "text" and "max"`);
          return;
        }
        let valid = true;
        if (typeof n.text !== 'string' || normalize(n.text) === '') {
          errors.push(`${label}.text must be a string that is not empty after normalization`);
          valid = false;
        } else if (normalize(n.text).length < 3) {
          warnings.push(`${label}.text "${n.text}" is very short; it is counted as a substring anywhere`);
        }
        if (!Number.isInteger(n.max) || n.max < 0) {
          errors.push(`${label}.max must be an integer >= 0`);
          valid = false;
        }
        if (valid) noise.push(n);
      });
    }
  }

  if (errors.length === 0) {
    // A faithful output must contain every required string, so these combinations can never all pass.
    const required = [
      ...strings.must_contain.map((s) => ['must_contain', s]),
      ...ordered.map((s) => ['ordered', s]),
      ...strings.headings.map((s) => ['headings', s]),
      ...tables.flatMap((t) => t.rows.flat()).filter((c) => normalize(c) !== '').map((c) => ['tables', c]),
    ];
    for (const a of strings.absent) {
      const na = normalize(a);
      for (const [key, s] of required) {
        if (normalize(s).includes(na)) errors.push(`checks.absent "${a}" occurs inside the required ${key} text "${s}"`);
      }
    }
    for (const n of noise) {
      if (n.max !== 0) continue;
      const nn = normalize(n.text);
      for (const [key, s] of required) {
        if (normalize(s).includes(nn)) errors.push(`checks.noise "${n.text}" has max 0 but occurs inside the required ${key} text "${s}"`);
      }
    }
  }
  return { errors, warnings };
}

// ---------------------------------------------------------------------------
// Corpus scoring
// ---------------------------------------------------------------------------

function toPosix(p) {
  return p.split(path.sep).join('/');
}

function sha256File(file) {
  const hash = createHash('sha256');
  const fd = fs.openSync(file, 'r');
  try {
    const buf = Buffer.allocUnsafe(1 << 20);
    for (let n = fs.readSync(fd, buf, 0, buf.length, null); n > 0; n = fs.readSync(fd, buf, 0, buf.length, null)) {
      hash.update(buf.subarray(0, n));
    }
  } finally {
    fs.closeSync(fd);
  }
  return hash.digest('hex');
}

/** Maps file name -> sorted relative paths of regular files under root (no dot entries, no symlinks). */
function indexFiles(root, { skipDirs = [], skipGroundTruth = false } = {}) {
  const base = path.resolve(root);
  const skip = new Set(skipDirs.map((d) => path.resolve(d)));
  const index = new Map();
  const stack = [base];
  let visited = 0;
  while (stack.length > 0 && visited < MAX_INDEXED_ENTRIES) {
    const dir = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      visited += 1;
      if (entry.name.startsWith('.')) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (skip.has(full) || (skipGroundTruth && entry.name.toLowerCase() === 'ground-truth')) continue;
        stack.push(full);
      } else if (entry.isFile()) {
        if (!index.has(entry.name)) index.set(entry.name, []);
        index.get(entry.name).push(toPosix(path.relative(base, full)));
      }
    }
  }
  for (const list of index.values()) list.sort();
  return index;
}

function checkSource(corpusDir, gt, sourceIndex) {
  const hits = sourceIndex.get(gt.file) ?? [];
  if (hits.length === 0) return { found: false, path: null, sha256_matches: null };
  if (hits.length > 1) return { found: true, path: null, ambiguous: hits, sha256_matches: null };
  let actual;
  try {
    actual = sha256File(path.join(corpusDir, hits[0]));
  } catch {
    return { found: true, path: hits[0], sha256_matches: null, unreadable: true };
  }
  const expected = typeof gt.sha256 === 'string' ? gt.sha256.toLowerCase() : null;
  return { found: true, path: hits[0], sha256_matches: expected === null ? null : actual === expected };
}

function locateOutput(outIndex, name, sourceRel) {
  const hits = outIndex.get(name) ?? [];
  if (hits.length <= 1) return { rel: hits[0] ?? null, ambiguous: [] };
  const mirrored = sourceRel ? path.posix.join(path.posix.dirname(sourceRel), name) : null;
  if (mirrored !== null && hits.includes(mirrored)) return { rel: mirrored, ambiguous: hits };
  if (hits.includes(name)) return { rel: name, ambiguous: hits };
  return { rel: null, ambiguous: hits };
}

function scoreOutputFile(outDir, outIndex, gt, candidate, sourceRel) {
  const name = gt.file + candidate.suffix;
  const located = locateOutput(outIndex, name, sourceRel);
  const flags = [];
  let buf = null;
  if (located.ambiguous.length > 0) flags.push('ambiguous_output');
  if (located.rel === null) flags.push('missing_output');
  else {
    try {
      buf = fs.readFileSync(path.join(outDir, located.rel));
    } catch {
      flags.push('unreadable_output');
    }
  }
  let text = null;
  let sha256 = null;
  if (buf !== null) {
    text = buf.toString('utf8');
    sha256 = createHash('sha256').update(buf).digest('hex');
    if (buf.length === 0) flags.push('empty_output');
    if (!Buffer.from(text, 'utf8').equals(buf)) flags.push('invalid_utf8');
    if (text.charCodeAt(0) === 0xfeff) flags.push('bom');
    if (text.includes('\r')) flags.push('cr_line_endings');
  }
  const result = {
    output_file: located.rel ?? name,
    missing: text === null,
    flags,
    sha256,
  };
  if (located.ambiguous.length > 0) result.output_candidates = located.ambiguous;
  const { missing, ...metrics } = scoreCandidate(text, gt.checks);
  return { ...result, ...metrics };
}

const SCORE_METRICS = [
  ['text_recall', (r) => r.text_recall.score],
  ['order_score', (r) => r.order.score],
  ['heading_recall', (r) => r.heading_recall.score],
  ['table_recall', (r) => r.tables.recall],
  ['table_precision', (r) => r.tables.precision],
  ['table_f1', (r) => r.tables.f1],
];
const COUNT_METRICS = [
  ['spurious_table_cells', (r) => r.tables.spurious_cells],
  ['noise_excess', (r) => r.noise.excess],
  ['absent_violations', (r) => r.absent.violations],
];

const sum = (values) => values.reduce((s, v) => s + v, 0);
const mean = (values) => (values.length > 0 ? sum(values) / values.length : null);

/** Macro-averaged aggregate over a list of per-file results. */
export function aggregate(files) {
  const complete = files.filter((f) => CANDIDATES.every((c) => !f.candidates[c.key].missing));
  const block = { files: files.length, complete_files: complete.length, candidates: {} };
  for (const c of CANDIDATES) {
    const results = files.map((f) => f.candidates[c.key]);
    const agg = { outputs_missing: results.filter((r) => r.missing).length };
    for (const [key, get] of SCORE_METRICS) {
      const values = results.map(get).filter((v) => v !== null);
      agg[key] = { mean: mean(values), n: values.length };
    }
    for (const [key, get] of COUNT_METRICS) {
      const values = results.map(get).filter((v) => v !== null);
      agg[key] = { total: sum(values), mean: mean(values), n: values.length };
    }
    const chars = results.map((r) => r.size.chars);
    const tokens = results.map((r) => r.size.tokens);
    agg.chars = { total: sum(chars), mean: mean(chars), n: chars.length };
    agg.tokens = {
      total: sum(tokens),
      mean: mean(tokens),
      n: tokens.length,
      total_on_complete_files: sum(complete.map((f) => f.candidates[c.key].size.tokens)),
      ratio_vs_markitdown_on_complete_files: null,
    };
    block.candidates[c.key] = agg;
  }
  const baseline = block.candidates[BASELINE].tokens.total_on_complete_files;
  for (const c of CANDIDATES) {
    const t = block.candidates[c.key].tokens;
    t.ratio_vs_markitdown_on_complete_files = baseline > 0 ? t.total_on_complete_files / baseline : null;
  }
  return block;
}

/** Scores a whole corpus. Returns { report, errorCount } (report numbers are unrounded). */
export function scoreCorpus(corpusDir, outDir) {
  const gtDir = path.join(corpusDir, 'ground-truth');
  const issues = { errors: [], warnings: [] };
  const gtNames = fs
    .readdirSync(gtDir, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith('.json') && !e.name.startsWith('.'))
    .map((e) => e.name)
    .sort();
  if (gtNames.length === 0) issues.errors.push({ file: null, message: 'no ground-truth .json files found' });

  const sourceIndex = indexFiles(corpusDir, { skipDirs: [outDir], skipGroundTruth: true });
  const outIndex = indexFiles(outDir, { skipDirs: [gtDir] });
  const files = [];
  const scoredNames = new Set();
  const knownFiles = new Set();

  for (const gtName of gtNames) {
    let bytes;
    let gt;
    try {
      bytes = fs.readFileSync(path.join(gtDir, gtName));
      gt = JSON.parse(bytes.toString('utf8').replace(/^﻿/, ''));
    } catch (err) {
      issues.errors.push({ file: gtName, message: `cannot read or parse JSON: ${err.message}` });
      continue;
    }
    if (isObject(gt) && typeof gt.file === 'string') knownFiles.add(gt.file);
    const { errors, warnings } = validateGroundTruth(gt, gtName);
    for (const message of warnings) issues.warnings.push({ file: gtName, message });
    if (errors.length > 0) {
      for (const message of errors) issues.errors.push({ file: gtName, message: `${message} (file skipped)` });
      continue;
    }
    if (scoredNames.has(gt.file)) {
      issues.errors.push({ file: gtName, message: `a second ground truth for "${gt.file}" (file skipped)` });
      continue;
    }
    scoredNames.add(gt.file);

    const source = checkSource(corpusDir, gt, sourceIndex);
    if (source.sha256_matches === false) {
      issues.warnings.push({ file: gtName, message: `sha256 differs from the corpus file ${source.path}` });
    } else if (source.unreadable) {
      issues.warnings.push({ file: gtName, message: `corpus file ${source.path} could not be read; sha256 not checked` });
    } else if (!source.found) {
      issues.warnings.push({ file: gtName, message: `corpus file "${gt.file}" not found under the corpus directory; sha256 not checked` });
    } else if (source.ambiguous) {
      issues.warnings.push({ file: gtName, message: `several corpus files are named "${gt.file}"; sha256 not checked` });
    }

    const candidates = {};
    for (const c of CANDIDATES) {
      candidates[c.key] = scoreOutputFile(outDir, outIndex, gt, c, source.path);
      if (candidates[c.key].flags.includes('ambiguous_output')) {
        issues.warnings.push({ file: gtName, message: `several ${c.key} outputs found: ${candidates[c.key].output_candidates.join(', ')}` });
      }
    }
    files.push({
      file: gt.file,
      format: gt.format,
      origin: gt.origin ?? null,
      title: gt.title ?? null,
      publisher: gt.publisher ?? null,
      source_url: gt.source_url ?? null,
      license: gt.license ?? null,
      pages_or_sheets: gt.pages_or_sheets ?? null,
      stresses: gt.stresses ?? [],
      notes: gt.notes ?? null,
      ground_truth_file: gtName,
      ground_truth_sha256: createHash('sha256').update(bytes).digest('hex'),
      source,
      check_counts: Object.fromEntries(CHECK_KEYS.map((k) => [k, gt.checks[k].length])),
      candidates,
    });
  }

  const expectedOutputs = new Set();
  for (const f of knownFiles) for (const c of CANDIDATES) expectedOutputs.add(f + c.suffix);
  const orphans = [];
  for (const [name, rels] of outIndex) if (name.endsWith('.md') && !expectedOutputs.has(name)) orphans.push(...rels);
  if (orphans.length > 0) {
    orphans.sort();
    const shown = orphans.slice(0, 20).join(', ') + (orphans.length > 20 ? `, ... (${orphans.length} in all)` : '');
    issues.warnings.push({ file: null, message: `output .md files that match no ground truth and were not scored: ${shown}` });
  }

  const byFormat = {};
  for (const format of FORMATS) {
    const subset = files.filter((f) => f.format === format);
    if (subset.length > 0) byFormat[format] = aggregate(subset);
  }
  const report = {
    benchmark: 'doc-to-markdown: PackForAI vs Microsoft MarkItDown',
    scorer: { file: 'score.mjs', version: SCORER_VERSION },
    runtime: { node: process.versions.node, unicode: process.versions.unicode ?? null, icu: process.versions.icu ?? null },
    tokenizer: TOKENIZER,
    normalization: NORMALIZATION,
    metric_definitions: METRIC_DEFINITIONS,
    candidates: CANDIDATES.map((c) => ({ key: c.key, output_suffix: c.suffix })),
    files,
    aggregates: { overall: aggregate(files), by_format: byFormat },
    issues,
  };
  return { report, errorCount: issues.errors.length };
}

export function serializeReport(report) {
  const round = (key, value) => (typeof value === 'number' && !Number.isInteger(value) ? Math.round(value * 1e6) / 1e6 : value);
  return `${JSON.stringify(report, round, 2)}\n`;
}

export function formatSummary(report) {
  const o = report.aggregates.overall;
  const num = (v) => (v === null ? '-' : v.toFixed(3)).padStart(7);
  const int = (v, w) => String(v).padStart(w);
  const lines = [
    `score.mjs: ${report.files.length} file(s) scored, ${o.complete_files} with all outputs; ` +
      `${report.issues.errors.length} error(s), ${report.issues.warnings.length} warning(s)`,
    `${'candidate'.padEnd(19)}${'text'.padStart(7)}${'order'.padStart(7)}${'heads'.padStart(7)}${'tblRec'.padStart(7)}` +
      `${'spur'.padStart(7)}${'noise'.padStart(7)}${'absent'.padStart(7)}${'tokens'.padStart(10)}${'missing'.padStart(8)}`,
  ];
  for (const c of CANDIDATES) {
    const a = o.candidates[c.key];
    lines.push(
      `${c.key.padEnd(19)}${num(a.text_recall.mean)}${num(a.order_score.mean)}${num(a.heading_recall.mean)}${num(a.table_recall.mean)}` +
        `${int(a.spurious_table_cells.total, 7)}${int(a.noise_excess.total, 7)}${int(a.absent_violations.total, 7)}` +
        `${int(a.tokens.total, 10)}${int(a.outputs_missing, 8)}`,
    );
  }
  lines.push('spur = spurious_table_cells: table cells that sit on no ground-truth table cell (secondary; see SCORING.md)');
  for (const e of report.issues.errors) lines.push(`error: ${e.file ?? '-'}: ${e.message}`);
  for (const w of report.issues.warnings.slice(0, 30)) lines.push(`warning: ${w.file ?? '-'}: ${w.message}`);
  if (report.issues.warnings.length > 30) lines.push(`... ${report.issues.warnings.length - 30} more warning(s) in the report`);
  return `${lines.join('\n')}\n`;
}

function isDirectory(p) {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

function main(args) {
  if (args.length !== 2 || args.some((a) => a.startsWith('-'))) {
    process.stderr.write('Usage: node score.mjs <corpusDir> <outDir> > results.json\n');
    process.exitCode = 2;
    return;
  }
  const [corpusDir, outDir] = args;
  for (const [label, dir] of [
    ['corpusDir', corpusDir],
    ['corpusDir/ground-truth', path.join(corpusDir, 'ground-truth')],
    ['outDir', outDir],
  ]) {
    if (!isDirectory(dir)) {
      process.stderr.write(`score.mjs: ${label} is not a directory: ${dir}\n`);
      process.exitCode = 2;
      return;
    }
  }
  const { report, errorCount } = scoreCorpus(corpusDir, outDir);
  process.stdout.write(serializeReport(report));
  process.stderr.write(formatSummary(report));
  if (errorCount > 0) process.exitCode = 1;
}

function invokedDirectly() {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(process.argv[1]) === fs.realpathSync(SELF_PATH);
  } catch {
    return false;
  }
}

if (invokedDirectly()) main(process.argv.slice(2));
