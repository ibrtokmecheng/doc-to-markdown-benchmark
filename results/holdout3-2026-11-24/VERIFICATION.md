# Third held-out run, 2026-11-24: how it was run and what was checked

## Protocol

1. The conversion engine was frozen at `motor/pdfjs-guncel-kas24` 65dfcb0. Since the second held-out run it reads
   PDF text with current PDF.js (pdfjs-dist 6.5.438) and takes the spacing of doubtful lines from a second reading
   with PDF.js 1.10. It was developed on `corpus/`, `holdout/` and `holdout2/`, which all count as development data.
2. The third held-out set (`holdout3/`, commit af11a88) was chosen and answered by a separate agent that ran no git
   command, never ran either tool or any text extractor, never read the engine code and never saw any output. PDF
   answers were typed from page images. The agent read README.md and SCORING.md, which name areas where each tool
   lost points earlier; its selection rule was written before any listing was read (disclosed in SELECTION.md).
3. Both tools were run on the set once, from commit af11a88: `node run-packforai.mjs holdout3 <out>` and
   `<venv>/python -I run_markitdown.py holdout3 <out>` (MarkItDown 0.1.9, Python 3.12.13), then
   `node score.mjs holdout3 <out>` with scorer 1.2.0. The engine and the scorer were not changed after this run.

Housekeeping: MarkItDown also converted `SELECTION.md` and `generate_holdout3.py` and the PackForAI runner rejected
them; those stray outputs were deleted before scoring.

The set has 9 documents, not 10: no document of the fourth public kind (a technical report set in columns) met the
selection rule (SELECTION.md explains each series tried). Two picks deviate from the letter of the rule in ways
SELECTION.md records (DOE's listing gives an effective date, not an approval date; FDIC serves a re-issue of the
August edition).

## Result (scorer 1.2.0)

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.949  1.000  0.676  0.907   6909      9      0     61486
packforai.compact    0.942  1.000  0.676  0.673   6907      7      0     60852
markitdown           0.848  0.889  0.333  0.558    515     28      2     53093
```

For comparison only (not a held-out claim for either): the engine that was live when this set was made
(1409923, PDF.js 1.10 only), run on the same files after the blind run, scored text 0.949, order 1.000, headings
0.676, tables 0.869, spurious 6968, tokens 62,597. Neither engine was tuned on this set.

## Surprising results, checked against the outputs

- **Federal Reserve G.17, 5,832 of PackForAI's 6,909 spurious cells.** The answer file transcribes 4 of the 13
  tables on the 15 pages kept. PackForAI matched those 4 almost cell for cell (85 of 85, 102 of 102, 179 of 180,
  69 of 75 candidate cells on the expected cells) and output the other tables as tables too; their cells sit on
  no expected cell, so they count as spurious. The count measures untranscribed real tables here, not noise.
- **G.17, MarkItDown text 0.04 and order 0.** Real: MarkItDown runs the words of this PDF together
  ("Industrial production(IP)edgeddown0.1percentinJuly"). PackForAI reads it with normal spacing (1.00).
- **Tokens, PackForAI 61,486 vs MarkItDown 53,093.** G.17 accounts for most of it: 37,111 vs 29,321, from 13 wide
  tables kept as Markdown tables by PackForAI and words run together by MarkItDown. Without G.17 the totals are
  24,375 vs 23,772 (PackForAI 2.5% larger).
- **DOE policy directive, PackForAI headings 0.17 and 6 tables in a document that has none.** Real engine
  limitation, also present in the live engine: lettered sub-items with a hanging indent ("a." in its own column,
  the text indented beside it) are read as a two-column table, and the numbered section headings
  ("1. FREEDOM OF EXPRESSION.") end up inside those tables. MarkItDown marks no headings (0.00) and keeps the text.
- **FDIC Quarterly Banking Profile, text 0.76 for both tools, PackForAI headings 0.06.** Both miss the same seven
  sentences. The page sets each section heading in a narrow left column beside the body text: MarkItDown reads
  across both columns line by line; PackForAI makes a two-column table of heading and body, so the body text is
  in one column, in order, but every sentence is cut at each table row and the headings are table cells. Same
  family of limitation as the DOE directive.
- **Generated inspection report, text 0.83 for both tools.** Both miss the same three sentences, each inside a
  table cell that wraps over two lines: PackForAI keeps the continuation on a row of its own (a deliberate rule,
  so a wrapped line is never merged into the wrong cell), MarkItDown writes the table as plain lines.

## What this run supports

- Tables, headings and reading order: PackForAI ahead on documents it was not developed on (tables 0.907 vs
  0.558, headings 0.676 vs 0.333, order 1.000 vs 0.889), text kept 0.949 vs 0.848.
- Page clutter: 9 repeated header and footer lines vs 28.
- Known weak spots shown here: label-and-text layouts (hanging-indent lists, side headings) read as two-column
  tables, which also costs headings; output larger than MarkItDown's on table-heavy releases.
