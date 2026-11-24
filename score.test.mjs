// Tests for score.mjs. Run: node --test score.test.mjs
// Small synthetic cases for every metric, the ground-truth checks and the CLI.

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import * as cl100k from 'gpt-tokenizer/encoding/cl100k_base';
import * as o200k from 'gpt-tokenizer/encoding/o200k_base';
import {
  absentScore,
  aggregate,
  findAbsent,
  formatSummary,
  headingRecall,
  longestIncreasingSubsequence,
  mapColumns,
  noiseScore,
  normalize,
  normalizeCell,
  normalizeText,
  orderScore,
  parseBareCsvLine,
  parseCsv,
  parsePipeTables,
  scanMarkdown,
  scoreCandidate,
  serializeReport,
  sizeOf,
  tableScores,
  textRecall,
  TOKENIZER,
  validateGroundTruth,
} from './score.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCORE = path.join(HERE, 'score.mjs');

function close(actual, expected, message) {
  assert.ok(Math.abs(actual - expected) < 1e-12, `${message ?? 'value'}: ${actual} is not ${expected}`);
}

const PEOPLE = { name: 'People', rows: [['Name', 'Age'], ['Alice', '30'], ['Bob', '25']] };
const PEOPLE_MD = ['| Name | Age |', '| --- | --- |', '| Alice | 30 |', '| Bob | 25 |'].join('\n');

describe('normalize', () => {
  test('applies NFKC, lowercases and collapses whitespace', () => {
    assert.equal(normalize('  Hello\t\n  WORLD \r\n'), 'hello world');
    assert.equal(normalize('ﬁnance ＡＢＣ x'), 'finance abc x');
  });

  test('deletes * _ \\ and backticks, turns table pipes into spaces', () => {
    assert.equal(normalize('**Bold** _it_ \\*esc\\* `code`'), 'bold it esc code');
    assert.equal(normalize('snake\\_case and snake_case'), 'snakecase and snakecase');
    assert.equal(normalize('| a | b |'), 'a b');
    assert.equal(normalize('|a|b|'), 'a b');
  });

  test('is idempotent and cannot separate a letter from its accent', () => {
    for (const s of ['Ä *b* | ¨x İstanbul', 'e*́', '  ##  Title  ', 'a\\|b']) {
      assert.equal(normalize(normalize(s)), normalize(s));
    }
    assert.equal(normalize('e*́'), normalize('é'));
  });

  test('does not unify quotes, dashes or soft hyphens', () => {
    assert.notEqual(normalize('“quoted”'), normalize('"quoted"'));
    assert.notEqual(normalize('a–b'), normalize('a-b'));
    assert.notEqual(normalize('regu­lation'), normalize('regulation'));
  });
});

describe('text recall', () => {
  test('matches phrases across line breaks, emphasis, escapes and table pipes', () => {
    const out = 'The **quick** brown\nfox jumps over the lazy\\_dog.\n\n| Alice | 30 |';
    const r = textRecall(out, ['quick brown fox', 'LAZY_DOG', 'alice 30', 'purple cow']);
    assert.equal(r.found, 3);
    assert.equal(r.total, 4);
    assert.equal(r.score, 0.75);
    assert.deepEqual(r.missing, ['purple cow']);
  });

  test('is null when there are no phrases', () => {
    assert.equal(textRecall('anything', []).score, null);
  });
});

describe('order score', () => {
  const anchors = ['Alpha', 'Beta', 'Gamma', 'Delta'];

  test('is 1 when every anchor is in reading order', () => {
    const r = orderScore('Alpha intro. Beta section. Gamma results. Delta end.', anchors);
    assert.equal(r.score, 1);
    assert.deepEqual(r.not_in_order, []);
  });

  test('reordered anchors: one anchor out of place gives 3/4', () => {
    const r = orderScore('Alpha intro. Gamma results. Beta section. Delta end.', anchors);
    assert.equal(r.in_order, 3);
    assert.equal(r.score, 0.75);
    assert.deepEqual(r.not_in_order, ['Beta']);
    assert.deepEqual(r.missing, []);
  });

  test('a missing anchor counts as not in order', () => {
    const r = orderScore('Alpha intro. Beta section. Gamma results.', anchors);
    assert.equal(r.score, 0.75);
    assert.deepEqual(r.missing, ['Delta']);
  });

  test('fully reversed anchors give 1/n', () => {
    assert.equal(orderScore('Delta. Gamma. Beta. Alpha.', anchors).score, 0.25);
  });

  test('uses the first occurrence of each anchor, after normalization', () => {
    const r = orderScore('Beta preview. Alpha intro. Beta section. **GAMMA** results. Delta end.', anchors);
    assert.equal(r.score, 0.75);
  });

  test('longest strictly increasing subsequence', () => {
    assert.deepEqual(longestIncreasingSubsequence([3, 1, 2, 4]), [1, 2, 3]);
    assert.equal(longestIncreasingSubsequence([5, 5, 5]).length, 1);
    assert.equal(longestIncreasingSubsequence([10, 20, 5, 6, 7, 30]).length, 4);
    assert.deepEqual(longestIncreasingSubsequence([]), []);
  });

  test('is null when there are no anchors', () => {
    assert.equal(orderScore('text', []).score, null);
  });
});

describe('heading recall', () => {
  test('a heading not marked as heading (bold line) is not found', () => {
    const md = ['# Introduction', '', 'Some text.', '', '**Methods**', '', 'More text.', '', '## 2. Results and *Discussion* ##'].join('\n');
    const r = headingRecall(md, ['Introduction', 'Methods', 'Results and Discussion']);
    assert.equal(r.found, 2);
    close(r.score, 2 / 3);
    assert.deepEqual(r.missing, ['Methods']);
  });

  test('lines that are not ATX headings do not count', () => {
    const md = [
      '#NoSpace',
      '####### Seven hashes',
      '    # Indented four spaces',
      'Setext title',
      '======',
      '<h2>Html</h2>',
      '```',
      '# Inside fence',
      '```',
    ].join('\n');
    const r = headingRecall(md, ['NoSpace', 'Seven hashes', 'Indented four spaces', 'Setext title', 'Html', 'Inside fence']);
    assert.equal(r.found, 0);
  });

  test('accepts CommonMark ATX variants and keeps a closing # that is part of the text', () => {
    const md = ['   ### Three-space indent', '#\tTab separated', '# Learn C#', '## Closed heading ##'].join('\n');
    assert.deepEqual(
      scanMarkdown(md).headings.map((h) => [h.level, h.text]),
      [[3, 'Three-space indent'], [1, 'Tab separated'], [1, 'Learn C#'], [2, 'Closed heading']],
    );
    assert.equal(headingRecall(md, ['Three-space indent', 'Tab separated', 'Learn C#', 'Closed heading']).score, 1);
  });

  test('each heading line satisfies at most one expected heading (maximum matching)', () => {
    assert.equal(headingRecall('## Summary\n\ntext', ['Summary', 'Summary']).score, 0.5);
    assert.equal(headingRecall('## Summary\n\n## Summary', ['Summary', 'Summary']).score, 1);
    // A greedy pass would give "Results" the first line and miss the longer heading.
    assert.equal(headingRecall('## Results and Discussion\n\n## Results', ['Results', 'Results and Discussion']).score, 1);
  });

  test('is null when there are no headings', () => {
    assert.equal(headingRecall('# A', []).score, null);
  });
});

describe('pipe table parsing', () => {
  test('parses GFM tables with and without outer pipes', () => {
    const md = [
      'Intro text',
      '',
      '| Name | Note |',
      '| :--- | ---: |',
      '| Alice | a \\| b |',
      '| Bob |',
      '| Carol | x | extra |',
      '',
      'Region | Sales',
      '--- | ---',
      'North | 10',
      'after',
    ].join('\n');
    const tables = parsePipeTables(md);
    assert.equal(tables.length, 2);
    assert.equal(tables[0].line, 3);
    assert.deepEqual(tables[0].rows, [['Name', 'Note'], ['Alice', 'a \\| b'], ['Bob', ''], ['Carol', 'x']]);
    assert.deepEqual(tables[1].rows, [['Region', 'Sales'], ['North', '10']]);
  });

  test('does not parse non-tables', () => {
    assert.equal(parsePipeTables('| a | b |\n| --- |\n| 1 | 2 |').length, 0, 'delimiter cell count differs');
    assert.equal(parsePipeTables('```\n| a | b |\n| --- | --- |\n```').length, 0, 'inside a code fence');
    assert.equal(parsePipeTables('Title\n---\ntext').length, 0, 'setext underline');
    assert.equal(parsePipeTables('<table><tr><td>a</td></tr></table>').length, 0, 'HTML table');
  });
});

describe('table cells (recall is the headline, precision and F1 secondary)', () => {
  test('an exact table scores 1', () => {
    const r = tableScores(PEOPLE_MD, [PEOPLE]);
    assert.deepEqual([r.recall, r.precision, r.f1], [1, 1, 1]);
    assert.equal(r.per_table[0].matching_cells, 6);
    assert.equal(r.per_table[0].matched_table_index, 0);
  });

  test('a table with a missing cell loses recall, not precision', () => {
    const md = ['| Name | Age |', '| --- | --- |', '| Alice | 30 |', '| Bob |'].join('\n');
    const t = tableScores(md, [PEOPLE]).per_table[0];
    assert.equal(t.expected_cells, 6);
    assert.equal(t.candidate_cells, 5);
    assert.equal(t.matching_cells, 5);
    assert.equal(t.precision, 1);
    close(t.recall, 5 / 6);
    close(t.f1, 10 / 11);
  });

  test('columns are aligned by header text when the order differs', () => {
    const md = ['| Age | Name |', '|---|---|', '| 30 | Alice |', '| 25 | Bob |'].join('\n');
    const t = tableScores(md, [PEOPLE]).per_table[0];
    assert.equal(t.f1, 1);
    assert.deepEqual(t.column_map, [1, 0]);
  });

  test('an empty header row (markdownify style) falls back to position and row alignment', () => {
    const md = ['|  |  |', '| --- | --- |', '| Name | Age |', '| Alice | 30 |', '| Bob | 25 |'].join('\n');
    assert.equal(tableScores(md, [PEOPLE]).f1, 1);
  });

  test('placeholder headers and NaN cells cost precision the same way for every tool', () => {
    const expected = { name: 'Q', rows: [['', 'Q1', 'Q2'], ['North', '10', '12'], ['South', '7', '']] };
    const columnN = ['| Column 1 | Q1 | Q2 |', '| --- | --- | --- |', '| North | 10 | 12 |', '| South | 7 |  |'].join('\n');
    const pandas = ['| Unnamed: 0 | Q1 | Q2 |', '| --- | --- | --- |', '| North | 10 | 12 |', '| South | 7 | NaN |'].join('\n');
    const a = tableScores(columnN, [expected]).per_table[0];
    assert.deepEqual([a.matching_cells, a.expected_cells, a.candidate_cells], [7, 7, 8]);
    close(a.f1, 14 / 15);
    const b = tableScores(pandas, [expected]).per_table[0];
    assert.deepEqual([b.matching_cells, b.expected_cells, b.candidate_cells], [7, 7, 9]);
    close(b.f1, 7 / 8);
  });

  test('a shifted column keeps the offset of its header-matched neighbour', () => {
    const expected = { name: 'G', rows: [['Region', 'Sales', 'Growth'], ['North', '10', '5%']] };
    const md = ['| # | Region | Sales | Growth (%) |', '|---|---|---|---|', '| 1 | North | 10 | 5% |'].join('\n');
    const t = tableScores(md, [expected]).per_table[0];
    assert.deepEqual(t.column_map, [1, 2, 3]);
    assert.equal(t.matching_cells, 5);
    close(t.precision, 5 / 8);
    close(t.recall, 5 / 6);
    close(t.f1, 5 / 7);
    assert.deepEqual(mapColumns(['a', 'b', 'c'], ['a', 'c', 'x']), [0, 2, 1]);
  });

  test('extra junk rows lower precision; rows are aligned in order', () => {
    const md = ['| People list | |', '| --- | --- |', '| | |', '| Name | Age |', '| Alice | 30 |', '| Bob | 25 |'].join('\n');
    const t = tableScores(md, [PEOPLE]).per_table[0];
    assert.equal(t.matching_cells, 6);
    close(t.precision, 6 / 7);
    close(t.f1, 12 / 13);
  });

  test('the best-matching table is picked', () => {
    const md = ['| X | Y |', '|---|---|', '| 1 | 2 |', '', PEOPLE_MD].join('\n');
    const r = tableScores(md, [PEOPLE]);
    assert.equal(r.tables_in_output, 2);
    assert.equal(r.per_table[0].matched_table_index, 1);
    assert.equal(r.recall, 1);
    assert.equal(r.f1, 1);
  });

  // A partial expected table: the source has 10 data rows, the ground truth lists only 2.
  const PARTIAL = { name: 'Sales (first 2 of 10 rows)', rows: [['Region', 'Sales'], ['North', '10'], ['South', '7']] };
  const REGIONS = ['North', 'South', 'East', 'West', 'Central', 'Coast', 'Hills', 'Lakes', 'Plains', 'Valley'];
  const COMPLETE_MD = ['| Region | Sales |', '| --- | --- |', ...REGIONS.map((name, i) => `| ${name} | ${i === 0 ? 10 : i === 1 ? 7 : i + 20} |`)].join('\n');
  const FRAGMENT_MD = ['| Region | Sales |', '| --- | --- |', '| North | 10 |'].join('\n');

  test('picks by recall, not F1: a complete large table beats a small exact fragment', () => {
    // The fragment alone: P = 4/4, R = 4/6, F1 = 0.8.
    const fragment = tableScores(FRAGMENT_MD, [PARTIAL]).per_table[0];
    assert.deepEqual([fragment.matching_cells, fragment.candidate_cells], [4, 4]);
    close(fragment.recall, 4 / 6);
    close(fragment.f1, 0.8);
    // The complete table alone: P = 6/22, R = 1, F1 = 3/7 (lower than the fragment's F1).
    const complete = tableScores(COMPLETE_MD, [PARTIAL]).per_table[0];
    assert.deepEqual([complete.matching_cells, complete.candidate_cells], [6, 22]);
    assert.equal(complete.recall, 1);
    close(complete.f1, 3 / 7);
    assert.ok(complete.f1 < fragment.f1 && complete.recall > fragment.recall);

    // Both in one output, fragment first: the higher-recall complete table is picked,
    // and its precision and F1 are the ones reported.
    const r = tableScores(`${FRAGMENT_MD}\n\n${COMPLETE_MD}`, [PARTIAL]);
    const t = r.per_table[0];
    assert.equal(r.tables_in_output, 2);
    assert.equal(t.matched_table_index, 1);
    assert.equal(t.matched_table_line, 5);
    assert.deepEqual([t.matching_cells, t.expected_cells, t.candidate_cells], [6, 6, 22]);
    assert.equal(r.recall, 1);
    close(r.precision, 6 / 22);
    close(r.f1, 3 / 7);
  });

  test('ties on recall go to the higher precision, then to the earliest table', () => {
    // Same recall (1) in both: the extra "City" column costs the first table precision.
    const withCity = ['| Name | Age | City |', '| --- | --- | --- |', '| Alice | 30 | Oslo |', '| Bob | 25 | Rome |'].join('\n');
    const byPrecision = tableScores(`${withCity}\n\n${PEOPLE_MD}`, [PEOPLE]).per_table[0];
    assert.equal(byPrecision.matched_table_index, 1);
    assert.deepEqual([byPrecision.recall, byPrecision.precision], [1, 1]);
    // Same recall below 1, different precision: fewer extra cells wins even when it comes second.
    const partialA = ['| Name | Age |', '| --- | --- |', '| Alice | 30 |', '| Zed | 99 |'].join('\n');
    const partialB = ['| Name | Age |', '| --- | --- |', '| Alice | 30 |'].join('\n');
    const lowerRecall = tableScores(`${partialA}\n\n${partialB}`, [PEOPLE]).per_table[0];
    assert.equal(lowerRecall.matched_table_index, 1);
    close(lowerRecall.recall, 4 / 6);
    assert.equal(lowerRecall.precision, 1);
    // Equal recall and precision: the earliest table is kept.
    const twin = ['| Name | Age |', '| --- | --- |', '| Alice | 30 |', '| Bob | 25 |'].join('\n');
    const byOrder = tableScores(`${PEOPLE_MD}\n\n${twin}`, [PEOPLE]).per_table[0];
    assert.equal(byOrder.matched_table_index, 0);
    assert.equal(byOrder.matched_table_line, 1);
  });

  test('no pipe table, or none with a matching cell, gives 0 and names no table', () => {
    const r = tableScores('Name Age\nAlice 30\nBob 25', [PEOPLE]);
    assert.deepEqual([r.recall, r.precision, r.f1, r.tables_in_output], [0, 0, 0, 0]);
    assert.equal(r.per_table[0].matched_table_index, null);
    assert.equal(tableScores(`\`\`\`\n${PEOPLE_MD}\n\`\`\``, [PEOPLE]).recall, 0, 'a table inside a code fence is not a table');
    const unrelated = tableScores('| X | Y |\n|---|---|\n| 1 | 2 |', [PEOPLE]);
    assert.deepEqual([unrelated.recall, unrelated.precision, unrelated.f1, unrelated.tables_in_output], [0, 0, 0, 1]);
    assert.equal(unrelated.per_table[0].matched_table_index, null);
    assert.equal(unrelated.per_table[0].candidate_cells, null);
  });

  test('recall, precision and F1 are averaged over expected tables, and null without expected tables', () => {
    const other = { name: 'Other', rows: [['K', 'V'], ['a', '1']] };
    const r = tableScores(PEOPLE_MD, [PEOPLE, other]);
    assert.deepEqual(r.per_table.map((t) => [t.recall, t.precision, t.f1]), [[1, 1, 1], [0, 0, 0]]);
    assert.deepEqual([r.recall, r.precision, r.f1], [0.5, 0.5, 0.5]);
    const none = tableScores(PEOPLE_MD, []);
    assert.deepEqual([none.recall, none.precision, none.f1], [null, null, null]);
    assert.deepEqual(Object.keys(r).slice(0, 3), ['recall', 'precision', 'f1'], 'recall is listed first');
  });
});

describe('noise', () => {
  test('sums occurrences beyond max over all entries', () => {
    const out = 'ACME Confidential\nPage 1 of 2\nBody text.\nacme confidential\nPage 1 of 2\n**ACME** Confidential';
    const r = noiseScore(out, [
      { text: 'Acme Confidential', max: 1 },
      { text: 'Page 1 of 2', max: 0 },
      { text: 'Not present', max: 0 },
    ]);
    assert.deepEqual(r.per_entry.map((e) => [e.count, e.excess]), [[3, 2], [2, 2], [0, 0]]);
    assert.equal(r.excess, 4);
  });

  test('counts non-overlapping occurrences; null when there is no entry', () => {
    assert.equal(noiseScore('aaaa', [{ text: 'aa', max: 0 }]).excess, 2);
    assert.equal(noiseScore('aaa', [{ text: 'aa', max: 0 }]).excess, 1);
    assert.equal(noiseScore('Header\nbody', [{ text: 'Header', max: 1 }]).excess, 0);
    assert.equal(noiseScore('x', []).excess, null);
  });
});

describe('absent strings', () => {
  test('a hyphenation artifact is a violation and breaks the phrase', () => {
    const broken = 'The new regu-\nlation applies to all members.';
    const fixed = 'The new regulation applies to all members.';
    const absent = ['regu- lation', 'DRAFT WATERMARK'];
    assert.deepEqual(absentScore(broken, absent), { violations: 1, found: ['regu- lation'], found_split: [] });
    assert.deepEqual(absentScore(fixed, absent), { violations: 0, found: [], found_split: [] });
    assert.equal(textRecall(broken, ['regulation applies']).score, 0);
    assert.equal(textRecall(fixed, ['regulation applies']).score, 1);
  });

  test('each entry counts once; null when there is no entry', () => {
    assert.equal(absentScore('x x x', ['x']).violations, 1);
    assert.equal(absentScore('x', []).violations, null);
  });
});

describe('size', () => {
  test('counts code points, UTF-8 bytes and o200k_base tokens', () => {
    const text = 'héllo \u{1F44B}\n';
    const s = sizeOf(text);
    assert.equal(text.length, 9);
    assert.equal(s.chars, 8);
    assert.equal(s.bytes, 12);
    assert.equal(s.tokens, o200k.encode(text).length);
    assert.equal(sizeOf('Hello, world!').tokens, 4);
    assert.deepEqual(sizeOf(''), { chars: 0, bytes: 0, tokens: 0 });
  });

  test('uses o200k_base, not cl100k_base', () => {
    const turkish = 'Yönetmelik değişikliği yürürlüğe girdi.';
    assert.equal(sizeOf(turkish).tokens, 13);
    assert.equal(cl100k.countTokens(turkish), 22);
    assert.equal(TOKENIZER.name, 'o200k_base');
    assert.equal(TOKENIZER.package, 'gpt-tokenizer');
    const pkg = JSON.parse(fs.readFileSync(path.join(HERE, TOKENIZER.resolved_package_dir, 'package.json'), 'utf8'));
    assert.equal(TOKENIZER.version, pkg.version);
  });

  test('special-token text is counted as ordinary text instead of throwing', () => {
    assert.throws(() => o200k.encode('<|endoftext|>'));
    assert.equal(sizeOf('<|endoftext|>').tokens, 7);
  });
});

describe('candidate scoring', () => {
  const checks = {
    must_contain: ['alpha'],
    ordered: ['a1', 'a2', 'a3', 'a4'],
    headings: ['H'],
    tables: [PEOPLE],
    noise: [{ text: 'footer', max: 1 }],
    absent: ['bad'],
  };

  test('a missing output is scored as empty text and flagged', () => {
    const r = scoreCandidate(null, checks);
    assert.equal(r.missing, true);
    assert.deepEqual(r.size, { chars: 0, bytes: 0, tokens: 0 });
    assert.deepEqual(
      [r.text_recall.score, r.order.score, r.heading_recall.score, r.tables.recall, r.noise.excess, r.absent.violations],
      [0, 0, 0, 0, 0, 0],
    );
    assert.deepEqual([r.tables.precision, r.tables.f1], [0, 0]);
  });

  test('macro averages skip checks that do not apply and count missing outputs', () => {
    const full = scoreCandidate(`# H\n\nalpha a1 a2 a3 a4 footer\n\n${PEOPLE_MD}\n`, checks);
    const none = scoreCandidate('# H\n\nalpha', { ...checks, ordered: [], tables: [], noise: [], absent: [] });
    const candidates = (r) => ({ 'packforai.document': r, 'packforai.compact': r, markitdown: r });
    const agg = aggregate([
      { format: 'pdf', candidates: candidates({ ...full, missing: false }) },
      { format: 'pdf', candidates: { ...candidates({ ...none, missing: false }), markitdown: scoreCandidate(null, checks) } },
    ]);
    assert.equal(agg.files, 2);
    assert.equal(agg.complete_files, 1);
    const md = agg.candidates.markitdown;
    assert.equal(md.outputs_missing, 1);
    assert.deepEqual(md.text_recall, { mean: 0.5, n: 2 });
    assert.deepEqual(md.order_score, { mean: 0.5, n: 2 });
    const doc = agg.candidates['packforai.document'];
    assert.deepEqual(doc.order_score, { mean: 1, n: 1 });
    assert.deepEqual(doc.noise_excess, { total: 0, mean: 0, n: 1 });
    assert.equal(doc.tokens.total, full.size.tokens + none.size.tokens);
    assert.equal(doc.tokens.total_on_complete_files, full.size.tokens);
    assert.equal(doc.tokens.ratio_vs_markitdown_on_complete_files, 1);
  });

  test('the report rounds non-integers to 6 decimals', () => {
    assert.equal(serializeReport({ a: 10 / 11, b: 3, c: null }), '{\n  "a": 0.909091,\n  "b": 3,\n  "c": null\n}\n');
  });

  test('aggregates list table_recall first and keep table_precision and table_f1', () => {
    // Recall 1, precision 6/9, F1 0.8: the three table numbers differ.
    const md = ['| Name | Age | City |', '| --- | --- | --- |', '| Alice | 30 | Oslo |', '| Bob | 25 | Rome |'].join('\n');
    const r = { ...scoreCandidate(md, { ...checks, tables: [PEOPLE] }), missing: false };
    const agg = aggregate([{ format: 'pdf', candidates: { 'packforai.document': r, 'packforai.compact': r, markitdown: r } }]);
    const a = agg.candidates.markitdown;
    assert.deepEqual(a.table_recall, { mean: 1, n: 1 });
    close(a.table_precision.mean, 6 / 9);
    close(a.table_f1.mean, 0.8);
    const keys = Object.keys(a);
    assert.ok(keys.indexOf('table_recall') < keys.indexOf('table_precision'));
    assert.ok(keys.indexOf('table_precision') < keys.indexOf('table_f1'));
  });
});

describe('summary', () => {
  test('the single table column shows table_recall, not table_f1', () => {
    const checks = { must_contain: [], ordered: [], headings: [], tables: [PEOPLE], noise: [], absent: [] };
    // Recall 1 with precision 6/9 (F1 0.8) for PackForAI; recall 2/6 with precision 1 (F1 0.5) for MarkItDown.
    const wide = ['| Name | Age | City |', '| --- | --- | --- |', '| Alice | 30 | Oslo |', '| Bob | 25 | Rome |'].join('\n');
    const narrow = ['| Name | Age |', '| --- | --- |'].join('\n');
    const pf = { ...scoreCandidate(wide, checks), missing: false };
    const mi = { ...scoreCandidate(narrow, checks), missing: false };
    const files = [{ format: 'pdf', candidates: { 'packforai.document': pf, 'packforai.compact': pf, markitdown: mi } }];
    const report = { files, aggregates: { overall: aggregate(files) }, issues: { errors: [], warnings: [] } };
    const lines = formatSummary(report).trimEnd().split('\n');
    const header = lines[1].trim().split(/\s+/);
    assert.deepEqual(header, ['candidate', 'text', 'order', 'heads', 'tblRec', 'spur', 'noise', 'absent', 'tokens', 'missing']);
    const column = header.indexOf('tblRec');
    const row = (key) => lines.find((l) => l.startsWith(`${key} `)).trim().split(/\s+/);
    assert.equal(row('packforai.document')[column], '1.000');
    assert.equal(row('markitdown')[column], '0.333');
    assert.doesNotMatch(lines.join('\n'), /tblF1|0\.800|0\.500/);
  });
});

describe('ground-truth validation', () => {
  // A fresh deep copy per test: the error cases mutate it (PEOPLE must stay intact).
  const valid = () => structuredClone({
    file: 'doc.pdf',
    format: 'pdf',
    origin: 'generated',
    source_url: null,
    title: 'Doc',
    publisher: null,
    license: 'generated for this benchmark',
    sha256: 'a'.repeat(64),
    pages_or_sheets: 2,
    stresses: ['two-column reading order'],
    checks: {
      must_contain: ['regulation applies'],
      ordered: ['one', 'two', 'three', 'four'],
      headings: ['Scope'],
      tables: [PEOPLE],
      noise: [{ text: 'Page 1 of 2', max: 0 }],
      absent: ['regu- lation'],
    },
    notes: '',
  });

  test('a valid file has no errors and no warnings', () => {
    assert.deepEqual(validateGroundTruth(valid(), 'doc.pdf.json'), { errors: [], warnings: [] });
  });

  const errorCases = [
    ['an empty phrase', (g) => { g.checks.must_contain.push(' ** '); }, /empty after normalization/],
    ['a missing check', (g) => { delete g.checks.absent; }, /checks\.absent is missing/],
    ['an unknown format', (g) => { g.format = 'doc'; }, /"format" must be one of/],
    ['a numeric table cell', (g) => { g.checks.tables[0].rows[1][1] = 30; }, /must be a string/],
    ['a path in "file"', (g) => { g.file = '../doc.pdf'; }, /bare file name/],
    ['duplicate anchors', (g) => { g.checks.ordered[3] = 'One'; }, /twice/],
    ['an absent string inside a required phrase', (g) => { g.checks.absent.push('regulation'); }, /occurs inside the required must_contain/],
    ['a max-0 noise text inside a heading', (g) => { g.checks.noise.push({ text: 'scope', max: 0 }); }, /has max 0/],
    ['a negative noise max', (g) => { g.checks.noise[0].max = -1; }, /integer >= 0/],
  ];
  for (const [label, mutate, pattern] of errorCases) {
    test(`error: ${label}`, () => {
      const g = valid();
      mutate(g);
      const { errors } = validateGroundTruth(g, 'doc.pdf.json');
      assert.ok(errors.some((e) => pattern.test(e)), JSON.stringify(errors));
    });
  }

  test('warnings: anchor count, ragged rows, unknown key, file name', () => {
    const g = valid();
    g.checks.ordered = ['one', 'two', 'three'];
    g.checks.tables[0].rows.push(['Carol']);
    g.checks.extra = [];
    const { errors, warnings } = validateGroundTruth(g, 'other.json');
    assert.deepEqual(errors, []);
    for (const pattern of [/3 anchors/, /different lengths/, /checks\.extra/, /expected "doc\.pdf\.json"/]) {
      assert.ok(warnings.some((w) => pattern.test(w)), `${pattern} in ${JSON.stringify(warnings)}`);
    }
  });
});

// ---------------------------------------------------------------------------
// 1.2.0 rule changes (SCORING.md): one block per change, positive and negative cases.
// ---------------------------------------------------------------------------

describe('1.2.0 change 1: compound hyphen across a line break (text and order only)', () => {
  test('a compound broken at a line end matches its hyphenated form', () => {
    const out = 'the proposed per-\npound rate, applicants importing typical 40,000-\npound loads';
    const r = textRecall(out, ['the proposed per-pound rate', 'typical 40,000-pound loads']);
    assert.equal(r.score, 1);
    assert.equal(normalizeText('per- pound'), 'per-pound');
    assert.equal(normalizeText('Per-\n\n  Pound'), 'per-pound');
    const anchors = ['first', 'per-pound rate', 'third', 'fourth'];
    assert.equal(orderScore('first. the per-\npound rate. third. fourth.', anchors).score, 1);
  });

  test('the ground truth side gets the same rule', () => {
    assert.equal(textRecall('a per-pound rate', ['a per- pound rate']).score, 1);
  });

  test('a split word stays split, and dashes, ranges and list markers are untouched', () => {
    assert.equal(textRecall('The regu-\nlation applies.', ['regulation applies']).score, 0);
    assert.equal(normalizeText('regu- lation'), 'regu-lation');
    assert.equal(normalizeText('pages 10- 12'), 'pages 10- 12', 'a digit after the hyphen');
    assert.equal(normalizeText('word - next'), 'word - next', 'a spaced dash');
    assert.equal(normalizeText('Intro\n- item'), 'intro - item', 'a list marker');
    assert.equal(textRecall('the per- pound rate', ['the per pound rate']).score, 0, 'the hyphen is not deleted');
  });

  test('absent strings keep the base normalization: split and joined forms stay distinct', () => {
    const r = absentScore('The com-\nmercial team', ['com- mercial', 'com-mercial']);
    assert.deepEqual(r.found, ['com- mercial']);
    assert.equal(absentScore('The com-mercial team', ['com- mercial', 'com-mercial']).found[0], 'com-mercial');
  });
});

describe('1.2.0 change 2: absent strings split by other text, and word boundaries', () => {
  test('two-column interleaving: the halves sit on consecutive lines with other text between', () => {
    // gen-two-column.pdf, MarkItDown: the right column's line sits between 'com-' and 'mercial'.
    const out = 'percent in the third quarter of 2026, and the com- positions during the evening peak\nmercial team expects a further 11 percent';
    const r = absentScore(out, ['com- mercial', 'com-mercial']);
    assert.deepEqual(r, { violations: 1, found: ['com- mercial'], found_split: ['com- mercial'] });
  });

  test('three-column interleaving: the rest starts mid-line on the next line', () => {
    // pub-fedreg-2024-31144.pdf, MarkItDown.
    const out = 'Fees and Charges at Destina- applicable fees for additional lots of the\ntotal number of lots inspected.  tion Markets (undesignated center head-';
    assert.equal(findAbsent(out, 'Destina- tion'), 'split');
  });

  test('the rest may be up to two lines below the prefix line, not three', () => {
    const two = 'between April and August 2027. | Instal- |\nadditional fire doors where the loop crosses the\nexisting floor. lation would take place';
    assert.equal(findAbsent(two, 'Instal- lation'), 'split');
    const three = 'August 2027. Instal-\nline one\nline two\nlation would take place';
    assert.equal(findAbsent(three, 'Instal- lation'), null);
    assert.equal(findAbsent('Instal-\n\n\nline one\nlation', 'Instal- lation'), 'split', 'blank lines are skipped');
  });

  test('a prefix inside a longer word, or a rest inside a longer word, does not count', () => {
    assert.equal(absentScore('the code- scribes it', ['de- scribes']).violations, 0, 'contiguous, prefix inside "code-"');
    assert.equal(absentScore('the made- other\nscribes', ['de- scribes']).violations, 0, 'split, prefix inside "made-"');
    assert.equal(absentScore('the com- positions\nthe commercial team', ['com- mercial']).violations, 0, 'rest inside "commercial"');
    assert.equal(absentScore('within- spection', ['in- spection']).violations, 0);
    assert.equal(absentScore('the ($254 in- spection cost', ['in- spection']).violations, 1, 'punctuation is a word boundary');
  });

  test('a hyphenated prefix without its rest nearby, or a joined word, is not a violation', () => {
    assert.equal(absentScore('pre- and post-war com- and other\nwords here', ['com- mercial']).violations, 0);
    assert.equal(absentScore('the commercial team', ['com- mercial', 'com-mercial']).violations, 0);
    assert.equal(absentScore('the com-mercial team', ['com- mercial']).violations, 0, 'the joined form is a separate entry');
  });

  test('entries that are not split words keep plain matching', () => {
    assert.equal(absentScore('Page 1 DRAFT\nWATERMARK', ['DRAFT WATERMARK']).violations, 1);
    assert.equal(absentScore('a "Rush" order', ['"Rush"']).violations, 1, 'no boundary rule before punctuation');
  });
});

describe('1.2.0 change 3: columns empty in every row are padding', () => {
  // No header pairs by text, so columns pair by position; an empty column 1 would shift every value.
  const expected = { name: 'Q', rows: [['Quarter', 'Total', 'E-commerce'], ['3rd', '10', '20'], ['2nd', '11', '21']] };

  test('an empty padding column is dropped when that aligns more cells', () => {
    const md = ['| 3rd |  | 10 | 20 |', '| --- | --- | --- | --- |', '| 2nd |  | 11 | 21 |'].join('\n');
    const t = tableScores(md, [expected]).per_table[0];
    assert.equal(t.matching_cells, 6);
    close(t.recall, 6 / 9);
    assert.equal(t.precision, 1);
    assert.deepEqual(t.dropped_empty_columns, [1]);
    // As written, only the row labels would match: '10' sits under 'Total' in the empty column's place.
    assert.equal(tableScores(md.replace(/\|  \|/g, '| x |'), [expected]).per_table[0].matching_cells, 2);
    assert.deepEqual(t.column_map, [0, 2, 3], 'indices of the table as written');
  });

  test('a column with a header or one filled cell is not padding', () => {
    const md = ['| 3rd | Unnamed: 1 | 10 | 20 |', '| --- | --- | --- | --- |', '| 2nd | NaN | 11 | 21 |'].join('\n');
    const t = tableScores(md, [expected]).per_table[0];
    // Only the row labels match; the values stay one column off.
    assert.deepEqual([t.matching_cells, t.dropped_empty_columns], [2, []]);
  });

  test('a faithful empty spacer column is kept when keeping it aligns better', () => {
    const spacer = { name: 'S', rows: [['h1', '', 'h3'], ['1', '', '2'], ['3', '', '4']] };
    const md = ['| Caption |  |  |', '| --- | --- | --- |', '| h1 |  | h3 |', '| 1 |  | 2 |', '| 3 |  | 4 |'].join('\n');
    const t = tableScores(md, [spacer]).per_table[0];
    assert.equal(t.recall, 1);
    assert.deepEqual([t.column_map, t.dropped_empty_columns], [[0, 1, 2], []]);
  });
});

describe('1.2.0 change 4: thousands separators in numeric table cells', () => {
  test('a whole-cell number loses its comma separators; sign, decimals, currency and parentheses stay', () => {
    assert.equal(normalizeCell('1,849,906'), '1849906');
    assert.equal(normalizeCell('$7,560.00'), '$7560.00');
    assert.equal(normalizeCell('(1,234)'), '(1234)');
    assert.equal(normalizeCell('-1,200.5'), '-1200.5');
    assert.equal(normalizeCell('GBP 420,000'), 'gbp 420000');
    assert.equal(normalizeCell('12.5%'), '12.5%');
  });

  test('other cells are unchanged', () => {
    for (const cell of ['Fenwick, Lowe and Partners', '1,2', '12,34', '1,2345', '1,200 units', '≤40,000 lbs. per lot', '2,100,000 38']) {
      assert.equal(normalizeCell(cell), normalize(cell), cell);
    }
  });

  test('both sides: 1,200 matches 1200, but a lost currency or decimals still differs', () => {
    const t = { name: 'U', rows: [['Item', 'Units', 'Revenue'], ['Tents', '1,200', '$7,560.00'], ['Stoves', '3,990', '-1,050']] };
    const md = ['| Item | Units | Revenue |', '| --- | --- | --- |', '| Tents | 1200 | 7560 |', '| Stoves | 3990 | -1050 |'].join('\n');
    const r = tableScores(md, [t]).per_table[0];
    assert.equal(r.matching_cells, 8, 'all but 7560, which is not $7,560.00');
    const before = { name: 'U', rows: [['Item', 'Units'], ['Tents', '1.200']] };
    assert.equal(tableScores('| Item | Units |\n| --- | --- |\n| Tents | 1200 |', [before]).per_table[0].matching_cells, 3, '1.200 is not 1,200');
    assert.equal(normalizeText('1,200'), '1,200', 'text matching keeps separators');
  });
});

describe('1.2.0 change 5: spurious table cells', () => {
  const ROWS = { name: 'R', rows: [['Region', 'Sales', 'Note'], ['North', '10', ''], ['South', '7', 'late']] };

  test('a faithful table has none; a table built from prose counts every cell', () => {
    const exact = ['| Region | Sales | Note |', '| --- | --- | --- |', '| North | 10 |  |', '| South | 7 | late |'].join('\n');
    assert.equal(tableScores(exact, [ROWS]).spurious_cells, 0);
    const prose = ['| Benefits | are counted | only |', '| --- | --- | --- |', '| where | they | can be |'].join('\n');
    const r = tableScores(`${exact}\n\nText.\n\n${prose}`, [ROWS]);
    assert.equal(r.spurious_cells, 6);
    assert.deepEqual(r.per_output_table.map((t) => [t.line, t.cells, t.spurious_cells]), [[1, 8, 0], [8, 6, 6]]);
    assert.equal(r.recall, 1, 'table_recall is unchanged');
  });

  test('titles, placeholder headers and filler where the expected cell is empty count; a wrong value does not', () => {
    const md = [
      '| Sales by region | Unnamed: 1 | Unnamed: 2 |',
      '| --- | --- | --- |',
      '| Region | Sales | Note |',
      '| North | 10 | NaN |',
      '| South | 7.0 | late |',
    ].join('\n');
    const r = tableScores(md, [ROWS]);
    // Spurious: the 3 title-row cells and 'NaN' (expected cell empty). '7.0' sits on the expected '7': a wrong value.
    assert.equal(r.spurious_cells, 4);
    assert.equal(r.per_table[0].matching_cells, 7);
  });

  test('fragments of one expected table are not spurious, and a missing check is null', () => {
    const md = ['| Region | Sales | Note |', '| --- | --- | --- |', '| North | 10 |  |', 'Interrupting line', '| South | 7 | late |', '| --- | --- | --- |'].join('\n');
    const r = tableScores(md, [ROWS]);
    assert.equal(r.tables_in_output, 2);
    assert.equal(r.spurious_cells, 0);
    assert.equal(tableScores(md, []).spurious_cells, null);
  });

  test('aggregates report its total and mean', () => {
    const checks = { must_contain: [], ordered: [], headings: [], tables: [ROWS], noise: [], absent: [] };
    const junk = { ...scoreCandidate('| a | b |\n| --- | --- |\n| c | d |', checks), missing: false };
    const agg = aggregate([{ format: 'pdf', candidates: { 'packforai.document': junk, 'packforai.compact': junk, markitdown: junk } }]);
    assert.deepEqual(agg.candidates.markitdown.spurious_table_cells, { total: 4, mean: 4, n: 1 });
  });
});

describe('1.2.0 change 6: CSV blocks are parsed as tables', () => {
  test('RFC 4180 parsing undoes quote doubling and keeps quoted commas and line breaks', () => {
    const records = parseCsv('a,b,c\n"Harbourside ""Fresh"" Market","x, y",\n"two\nlines",2,3');
    assert.deepEqual(records.map((r) => r.fields.map((f) => f.value)), [['a', 'b', 'c'], ['Harbourside "Fresh" Market', 'x, y', ''], ['two\nlines', '2', '3']]);
    assert.deepEqual(records.map((r) => r.line), [0, 1, 2]);
    for (const bad of ['"open,b', '"a"x,b', 'a"b,c']) assert.equal(parseCsv(bad), null, bad);
  });

  test('a bare CSV paragraph, with an optional caption line, is a table', () => {
    const md = ['# Q1 Sales', 'Ledger title', 'Order,Customer,Units', 'SO-1,"Kestrel Print, Inc.",1200', 'SO-2,"Harbourside ""Fresh"" Market",40', '', 'after'].join('\n');
    const [t] = scanMarkdown(md).tables;
    assert.deepEqual([t.kind, t.line, t.caption, t.width], ['csv', 3, 'Ledger title', 3]);
    assert.deepEqual(t.rows[2], ['SO-2', 'Harbourside "Fresh" Market', '40']);
    const expected = { name: 'S', rows: [['Order', 'Customer', 'Units'], ['SO-1', 'Kestrel Print, Inc.', '1,200'], ['SO-2', 'Harbourside "Fresh" Market', '40']] };
    const r = tableScores(md, [expected]);
    assert.deepEqual([r.recall, r.precision, r.spurious_cells], [1, 1, 0]);
  });

  test('a ```csv fence is a table; other fences are not', () => {
    const csv = ['```csv', 'Region,Sales', 'North,10', '"South, coast",7', '```'].join('\n');
    const [t] = scanMarkdown(csv).tables;
    assert.deepEqual([t.kind, t.line, t.rows], ['csv', 2, [['Region', 'Sales'], ['North', '10'], ['South, coast', '7']]]);
    assert.equal(scanMarkdown(csv.replace('```csv', '```text')).tables.length, 0);
    assert.equal(scanMarkdown('```csv\nRegion,Sales\n"North,10\n```').tables.length, 0, 'unterminated quote');
  });

  test('prose, PDF number rows, lists and mixed paragraphs are not CSV tables', () => {
    const notTables = [
      'Leeds, Bristol and Glasgow grew.\nVolumes rose, costs fell.',
      // MarkItDown two-column output: grouped numbers in prose lines under a caption-like line.
      'during which manual sorting remains available as\nB: Tilt-tray sorter 1,450,000 31 a fallback.\nC: Cross-belt sorter 2,100,000 38 nance staff begins',
      '3rd quarter 2024(p)    1,849,906    300,053\n2nd quarter 2024(r)    1,826,454    292,567',
      '- a,b\n- c,d',
      'a,b\nplain line in between\nc,d',
      'only,one,line',
      '{\n  "id": "cus_0016",\n  "name": "Alder"\n}',
    ];
    for (const md of notTables) assert.equal(scanMarkdown(md).tables.length, 0, md);
    assert.equal(parseBareCsvLine('a, b'), null, 'space after the separator');
    assert.equal(parseBareCsvLine('total 1,200 units,x'), null, 'a grouped number token');
    assert.deepEqual(parseBareCsvLine('total,1,200'), ['total', '1', '200'], 'commas next to commas are separators');
    assert.deepEqual(parseBareCsvLine('SO-1,2026-01-05,15,315.00,'), ['SO-1', '2026-01-05', '15', '315.00', '']);
  });

  test('pipe and CSV tables are picked in document order', () => {
    const md = ['Region,Sales', 'North,10', '', '| Region | Sales |', '| --- | --- |', '| North | 10 |'].join('\n');
    const r = tableScores(md, [{ name: 'T', rows: [['Region', 'Sales'], ['North', '10']] }]);
    assert.deepEqual(r.per_output_table.map((t) => [t.line, t.kind]), [[1, 'csv'], [4, 'pipe']]);
    assert.equal(r.per_table[0].matched_table_index, 0, 'a full tie keeps the earlier table');
  });
});

describe('1.2.0 row alignment guard (safeguard for change 3)', () => {
  test('a single shared number does not align two rows', () => {
    // pub-srpt-118-226.pdf, MarkItDown: table-of-contents page numbers line up with a '5' of the CBO table.
    const cbo = { name: 'CBO', rows: [['', '2024', '2025'], ['Estimated Authorization', '0', '5'], ['Estimated Outlays', '0', '5']] };
    const toc = ['| I. Purpose and Summary |  |  |', '| --- | --- | --- |', '| V. Evaluation of Regulatory Impact |  | 5 |', '| VI. Congressional Budget Office |  | 5 |'].join('\n');
    const r = tableScores(toc, [cbo]);
    assert.equal(r.recall, 0);
    assert.equal(r.spurious_cells, 5);
  });

  test('a lone row label, or the only cell of an expected row, still counts', () => {
    const grouped = { name: 'G', rows: [['Quarter', 'Total'], ['Adjusted', ''], ['', '2024'], ['3rd', '10']] };
    const md = ['| Quarter | Total |', '| --- | --- |', '| Adjusted |  |', '|  | 2024 |', '| 3rd | 10 |'].join('\n');
    assert.equal(tableScores(md, [grouped]).recall, 1);
    const label = tableScores(['| Name | Age |', '| --- | --- |', '| Bob | 99 |'].join('\n'), [PEOPLE]).per_table[0];
    assert.equal(label.matching_cells, 3, 'Name, Age and the lone label Bob');
  });
});

describe('command line', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'd2m-score-test-'));
  after(() => fs.rmSync(root, { recursive: true, force: true }));

  const write = (rel, content) => {
    const file = path.join(root, rel);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, content);
    return file;
  };
  const sha = (content) => createHash('sha256').update(content).digest('hex');
  const run = (...args) => spawnSync(process.execPath, [SCORE, ...args], { encoding: 'utf8', input: '' });

  const docxBytes = 'synthetic docx bytes';
  const csvBytes = 'Region,Sales\nNorth,10\nSouth,7\n';
  write('corpus/files/report.docx', docxBytes);
  write('corpus/files/sales.csv', csvBytes);
  const salesTable = { name: 'Sales', rows: [['Region', 'Sales'], ['North', '10'], ['South', '7']] };
  const gtBase = { origin: 'generated', source_url: null, publisher: null, license: 'generated', pages_or_sheets: 1, stresses: [], notes: '' };
  write(
    'corpus/ground-truth/report.docx.json',
    JSON.stringify({
      ...gtBase,
      file: 'report.docx',
      format: 'docx',
      title: 'Report',
      sha256: sha(docxBytes),
      checks: {
        must_contain: ['Quarterly revenue grew', 'regulation applies'],
        ordered: ['Overview', 'Quarterly revenue', 'Outlook', 'Appendix'],
        headings: ['Overview', 'Outlook'],
        tables: [salesTable],
        noise: [{ text: 'Company Confidential', max: 1 }],
        absent: ['regu- lation'],
      },
    }),
  );
  write(
    'corpus/ground-truth/sales.csv.json',
    JSON.stringify({
      ...gtBase,
      file: 'sales.csv',
      format: 'csv',
      title: 'Sales',
      sha256: '0'.repeat(64),
      checks: { must_contain: ['North'], ordered: [], headings: [], tables: [salesTable], noise: [], absent: [] },
    }),
  );
  const outputs = {
    'out/report.docx.packforai.document.md': [
      '# Overview', '', 'Quarterly revenue grew 12%.', '', '## Revenue', '', '| Region | Sales |', '| --- | --- |', '| North | 10 |', '| South | 7 |',
      '', '## Outlook', '', 'The regulation applies next year.', '', '## Appendix', '', 'Company Confidential', '',
    ].join('\n'),
    'out/report.docx.packforai.compact.md': [
      '# Overview', 'Quarterly revenue grew 12%.', 'Region,Sales', 'North,10', 'South,7', '## Outlook', 'The regu-', 'lation applies next year.',
      '## Appendix', 'Company Confidential', 'Company Confidential', '',
    ].join('\n'),
    // Mirrors the corpus sub-folder, as run_markitdown.py writes it.
    'out/files/report.docx.markitdown.md': [
      '**Overview**', '', 'Quarterly revenue grew 12%.', '', '## Appendix', '', 'Company Confidential', '', '## Outlook', '',
      'The regulation applies next year.', '', '|  |  |', '| --- | --- |', '| Region | Sales |', '| North | 10 |', '| South | 7 |', '',
    ].join('\n'),
    'out/sales.csv.packforai.document.md': '## sales\n\n| Region | Sales |\n| --- | --- |\n| North | 10 |\n| South | 7 |\n',
    'out/sales.csv.markitdown.md': '| Region | Sales |\n|---|---|\n| North | 10 |\n| South | 7 |\n',
    'out/old/sales.csv.markitdown.md': '',
    'out/unknown.pdf.markitdown.md': 'not scored',
  };
  for (const [rel, content] of Object.entries(outputs)) write(rel, content);
  const corpus = path.join(root, 'corpus');
  const out = path.join(root, 'out');

  test('scores a corpus and writes the JSON report to stdout', () => {
    const res = run(corpus, out);
    assert.equal(res.status, 0, res.stderr);
    const report = JSON.parse(res.stdout);
    assert.equal(report.tokenizer.name, 'o200k_base');
    assert.equal(report.tokenizer.version, TOKENIZER.version);
    assert.ok(report.normalization.steps.length >= 5);
    assert.ok(report.metric_definitions.table_recall.includes('dynamic programming'));
    assert.ok(report.metric_definitions.table_recall.includes('highest recall'));
    assert.match(report.metric_definitions.table_precision, /^Secondary\..*partial/);
    assert.match(report.metric_definitions.table_f1, /^Secondary\./);
    assert.equal(report.scorer.version, '1.2.0');
    assert.match(report.metric_definitions.spurious_table_cells, /^Secondary;/);
    assert.deepEqual(report.files.map((f) => f.file), ['report.docx', 'sales.csv']);
    assert.deepEqual(report.issues.errors, []);

    const [docx, csv] = report.files;
    assert.deepEqual(docx.source, { found: true, path: 'files/report.docx', sha256_matches: true });
    assert.equal(csv.source.sha256_matches, false);

    const pd = docx.candidates['packforai.document'];
    assert.deepEqual(
      [pd.text_recall.score, pd.order.score, pd.heading_recall.score, pd.tables.recall, pd.noise.excess, pd.absent.violations],
      [1, 1, 1, 1, 0, 0],
    );
    assert.deepEqual([pd.tables.precision, pd.tables.f1], [1, 1]);
    assert.equal(pd.size.tokens, o200k.countTokens(outputs['out/report.docx.packforai.document.md']));
    assert.equal(pd.sha256, sha(outputs['out/report.docx.packforai.document.md']));

    // The compact output holds the table as a bare CSV block under a caption line (1.2.0 parses it).
    const pc = docx.candidates['packforai.compact'];
    assert.deepEqual(
      [pc.text_recall.score, pc.order.score, pc.heading_recall.score, pc.tables.recall, pc.noise.excess, pc.absent.violations],
      [0.5, 1, 1, 1, 1, 1],
    );
    assert.deepEqual([pc.tables.tables_in_output, pc.tables.csv_tables_in_output, pc.tables.spurious_cells], [1, 1, 0]);
    assert.equal(pc.tables.per_table[0].matched_table_kind, 'csv');

    const mi = docx.candidates.markitdown;
    assert.equal(mi.output_file, 'files/report.docx.markitdown.md');
    assert.deepEqual(
      [mi.text_recall.score, mi.order.score, mi.heading_recall.score, mi.tables.recall, mi.noise.excess, mi.absent.violations],
      [1, 0.75, 0.5, 1, 0, 0],
    );
    assert.deepEqual([mi.tables.precision, mi.tables.f1], [1, 1]);
    // Overview < Quarterly revenue < Appendix < Outlook in the output: two longest subsequences of
    // length 3 tie; the reported one ends at the smaller position, so Outlook is the one named.
    assert.deepEqual(mi.order.not_in_order, ['Outlook']);

    const compactCsv = csv.candidates['packforai.compact'];
    assert.equal(compactCsv.missing, true);
    assert.deepEqual(compactCsv.flags, ['missing_output']);
    assert.equal(compactCsv.tables.recall, 0);
    assert.equal(csv.candidates.markitdown.output_file, 'sales.csv.markitdown.md');
    assert.deepEqual(csv.candidates.markitdown.flags, ['ambiguous_output']);
    assert.equal(csv.candidates['packforai.document'].order.score, null);

    const overall = report.aggregates.overall;
    assert.equal(overall.files, 2);
    assert.equal(overall.complete_files, 1);
    const compact = overall.candidates['packforai.compact'];
    assert.equal(compact.outputs_missing, 1);
    assert.deepEqual(compact.text_recall, { mean: 0.25, n: 2 });
    assert.deepEqual(compact.order_score, { mean: 1, n: 1 });
    assert.deepEqual(compact.table_recall, { mean: 0.5, n: 2 });
    assert.deepEqual(compact.table_precision, { mean: 0.5, n: 2 });
    assert.deepEqual(compact.table_f1, { mean: 0.5, n: 2 });
    assert.deepEqual(compact.spurious_table_cells, { total: 0, mean: 0, n: 2 });
    assert.deepEqual(compact.noise_excess, { total: 1, mean: 1, n: 1 });
    const tokensOf = (rel) => o200k.countTokens(outputs[rel]);
    assert.equal(
      overall.candidates['packforai.document'].tokens.total,
      tokensOf('out/report.docx.packforai.document.md') + tokensOf('out/sales.csv.packforai.document.md'),
    );
    const ratio = tokensOf('out/report.docx.packforai.document.md') / tokensOf('out/files/report.docx.markitdown.md');
    close(overall.candidates['packforai.document'].tokens.ratio_vs_markitdown_on_complete_files, Math.round(ratio * 1e6) / 1e6);
    assert.deepEqual(Object.keys(report.aggregates.by_format), ['docx', 'csv']);
    assert.equal(report.aggregates.by_format.csv.candidates.markitdown.table_recall.mean, 1);
    assert.equal(report.aggregates.by_format.csv.candidates.markitdown.table_f1.mean, 1);

    const warnings = report.issues.warnings.map((w) => w.message).join('\n');
    assert.match(warnings, /sha256 differs/);
    assert.match(warnings, /unknown\.pdf\.markitdown\.md/);
    assert.match(warnings, /several markitdown outputs/);
    assert.match(res.stderr, /2 file\(s\) scored/);
    assert.match(res.stderr, /^candidate +text +order +heads +tblRec +spur +noise/m);
    assert.doesNotMatch(res.stderr, /tblF1/);
    // packforai.compact: the CSV table of report.docx scores 1, the missing sales.csv output 0.
    assert.match(res.stderr, /^packforai\.compact +0\.250 +1\.000 +1\.000 +0\.500 +0 /m);
    // markitdown: the empty header row of its report.docx table sits on no expected cell, but its cells are empty.
    assert.match(res.stderr, /^markitdown +1\.000 +0\.750 +0\.500 +1\.000 +0 /m);
  });

  test('the report is byte-for-byte reproducible', () => {
    assert.equal(run(corpus, out).stdout, run(corpus, out).stdout);
  });

  test('an invalid ground-truth file is skipped and the exit status is 1', () => {
    write('corpus/ground-truth/broken.pdf.json', JSON.stringify({ file: 'broken.pdf', format: 'pdf', checks: { must_contain: 'x' } }));
    write('corpus/ground-truth/garbled.pdf.json', '{ not json');
    try {
      const res = run(corpus, out);
      assert.equal(res.status, 1);
      const report = JSON.parse(res.stdout);
      assert.equal(report.files.length, 2);
      const errorFiles = new Set(report.issues.errors.map((e) => e.file));
      assert.deepEqual([...errorFiles].sort(), ['broken.pdf.json', 'garbled.pdf.json']);
    } finally {
      fs.rmSync(path.join(corpus, 'ground-truth/broken.pdf.json'));
      fs.rmSync(path.join(corpus, 'ground-truth/garbled.pdf.json'));
    }
  });

  test('usage errors exit with 2 and print nothing on stdout', () => {
    const noArgs = run();
    assert.equal(noArgs.status, 2);
    assert.equal(noArgs.stdout, '');
    assert.match(noArgs.stderr, /Usage/);
    const missingDir = run(path.join(root, 'nope'), out);
    assert.equal(missingDir.status, 2);
    assert.equal(missingDir.stdout, '');
  });
});
