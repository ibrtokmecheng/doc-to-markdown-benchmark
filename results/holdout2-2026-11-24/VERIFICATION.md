# Second held-out run, 2026-11-24: how it was run and what was checked

## Protocol

1. The conversion engine was frozen at `motor/rapor-ve-tablolar-kas24` fc6c6ed. Its changes since the first
   held-out run were developed on the original corpus and on the first held-out set, which from then on counts
   as development data, not as a test.
2. The second held-out set (`holdout2/`, commit 7d693af) was chosen and answered by a separate agent that never
   ran either tool, never read the engine code and never saw any output. PDF answers were typed from page images.
   Disclosure (also in `holdout2/SELECTION.md`): while checking the branch, that agent saw the latest commit
   subject, which names the PDF areas the engine had just been worked on. Its selection rule had been written
   before any document was looked up, and the picks follow that rule.
3. Both tools were run on the set once, from commit 7d693af: `node run-packforai.mjs holdout2 <out>` and
   `<venv>/python -I run_markitdown.py holdout2 <out>` (MarkItDown 0.1.9, Python 3.12.13), then
   `node score.mjs holdout2 <out>` with scorer 1.2.0.
4. The engine and the scorer were not changed after this run. Findings below are reported as they are.

Housekeeping: as in the first run, `SELECTION.md` and `generate_holdout2.py` in `holdout2/` were converted by
MarkItDown and rejected by the PackForAI runner; those stray outputs were deleted and the scorer was run again on
the unchanged tool outputs.

## Result (scorer 1.2.0)

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.901  0.900  0.939  0.861   1557      0      1     40231
packforai.compact    0.890  0.900  0.939  0.677   1557      0      1     39763
markitdown           0.922  0.929  0.286  0.474    405     15      2     43640
```

The six generated office files (DOCX, PPTX, XLSX, CSV, JSON, PDF price list) score 1.000 on text for both tools.
The differences come from the four public PDFs.

## Surprising results, checked against the outputs

- **DOL weekly claims release, PackForAI text 0.24 and order 0 (MarkItDown 1.00 and 1.00).** Real limitation,
  in the PDF reading layer below the engine. The body font ("Times") is not embedded and the file positions its
  letters with large kerning adjustments. pdf.js, which PackForAI uses to read PDF text, treats those
  adjustments as word gaps and puts spaces inside words before the engine sees the text: "the a dva nce figure
  for sea sona lly a djusted initial claims wa s 233,000". The bundled pdf.js 2.0.550 does the same. Sentence
  matching then fails, so text recall and reading order collapse for this one file. MarkItDown (pdfminer) reads
  it correctly.
- **FDA BsUFA guidance, PackForAI text 0.97.** Same cause, one place: "The FDA honors r equests for BPD Type 2b".
- **Treasury monthly statement, text 0.80 for both tools.** Both tools miss the same three sentences: footnotes
  set side by side in two columns are read line by line across both columns. PackForAI also writes them as a
  table, which adds spurious cells.
- **USGS fact sheet, PackForAI tables 0.46 with 283 spurious cells (MarkItDown 0.10).** Table 1 scores 0.92.
  Table 2 scores 0 although every number is in the output, on the right row and in the right order: the
  "AU probability" values (1.0) are centred between the Oil and Gas lines, so the engine gives them a row of
  their own instead of a column. With one column fewer, the scorer's fixed column rule (header match, else
  same position) shifts every value column by one and no cell matches. Real engine limitation; the scorer was
  not adjusted. The same file has one absent-text violation for PackForAI ("assess- ment") and two for
  MarkItDown.
- **Spurious table cells, PackForAI 1557 vs MarkItDown 405.** Almost all in three files: DOL 745 (neighbouring
  tables on page 4 and the page 6 table merged with text around them), Treasury 503 (footnotes and nearby text
  pulled into Tables 3 and 4) and USGS 283 (the shifted Table 2). MarkItDown writes many small tables (48 in
  DOL, 45 in Treasury) with fewer extra cells but much lower recall.
- **Headings, PackForAI 0.939 vs MarkItDown 0.286.** MarkItDown marks no headings in PDFs; PackForAI misses some
  in DOL (0.57).

## What this run supports

- Tables and headings: PackForAI ahead on a set it was not developed on (table recall 0.861 vs 0.474, headings
  0.939 vs 0.286), with more spurious cells than MarkItDown.
- Text and reading order: MarkItDown slightly ahead (0.922 vs 0.901, 0.929 vs 0.900), driven by one PDF whose
  letters pdf.js splits apart.
- Tokens: PackForAI document.md 40,231 vs MarkItDown 43,640 on the same files.
