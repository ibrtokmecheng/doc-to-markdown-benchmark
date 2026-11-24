# Fourth held-out run, 2026-11-24: how it was run and what was checked

## Protocol

1. The conversion engine was frozen at `motor/liste-yan-baslik-kas24` e7e91a7. Since the third held-out run it
   joins list markers set apart by a hanging indent to their text, gathers headings set in a column beside the body
   text into one heading, and keeps table-of-contents entries one per line. It was developed on `corpus/`,
   `holdout/`, `holdout2/` and `holdout3/`, which all count as development data now.
2. The fourth held-out set (`holdout4/`, commit bf80889) was chosen and answered by a separate agent that ran no git
   command, never ran either tool or any text extractor, never read the engine code, README.md or any earlier
   result, and never saw any output. PDF answers were typed from page images.
3. Both tools were run on the set once, from commit bf80889: `node run-packforai.mjs holdout4 <out>` and
   `<venv>/python -I run_markitdown.py holdout4 <out>` (MarkItDown 0.1.9, Python 3.12.13), then
   `node score.mjs holdout4 <out>` with scorer 1.2.0. The engine and the scorer were not changed after this run.

Housekeeping: MarkItDown also converted `SELECTION.md` and `generate_holdout4.py` and the PackForAI runner rejected
them; those stray outputs were deleted before scoring.

The set has 9 documents, not 10: again no document of the two-column technical report kind met the selection rule
(SELECTION.md lists the five series tried). SELECTION.md also records the other deviations (a page-range judgement
for NCUA, files currently served being later uploads of the September 2025 releases).

## Result (scorer 1.2.0)

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.970  0.986  0.853  0.788    741      1      0     37028
packforai.compact    0.958  0.986  0.853  0.555    739      0      0     36390
markitdown           0.970  0.986  0.333  0.562     78     16      0     34508
```

For comparison only: the engine live when this set was made (65dfcb0), run on the same files after the blind run,
scored text 0.965, order 0.986, headings 0.839, tables 0.788, spurious 838, tokens 37,289. No file scored lower
with e7e91a7 than with 65dfcb0; the NCUA summary improved (text 0.95 to 1.00, headings 0.83 to 0.92, tables in
the output 19 to 11). Neither engine was tuned on this set.

## Surprising results, checked against the outputs

- **FAA Advisory Circular 20-167B, PackForAI headings 0.20 and 8 tables on pages that have none.** Real engine
  limitation: paragraphs numbered with decimal numbers ("1.1.1", "1.2.2") and a hanging indent are read as a
  two-column table, number and text. The change frozen for this run joins single-level markers ("1.", "a.",
  "(iv)") to their text but not decimal numbers. The section headings are set as "1.2 Applicability." (a number,
  a title in mixed case and a period) and are not marked. MarkItDown marks no headings. Both tools miss the same
  two sentences (the title and a signature line).
- **FHFA House Price Index report, tables 0.40 (MarkItDown 0.06).** PackForAI recovered the two large tables almost
  completely (140 of 142 and 208 of 208 cells) but wrote them as one table, which is why 23 of its cells match no
  expected cell; the index-availability table and the two release-date calendars did not come out as tables.
- **NCUA Quarterly Credit Union Data Summary, tables 0.37 (MarkItDown 0.00).** The three large call-report summary
  tables were rebuilt poorly (2%, 21% and 27% of their cells); 707 of PackForAI's 741 unmatched cells are in this
  file. MarkItDown wrote no table for it. Text kept is 1.00 for both tools.
- **Generated operations report, text 0.78 for all three runs.** The four missed sentences are each in a table cell
  that wraps onto a second line, the same limitation as in the third set.
- **Tokens, PackForAI 37,028 vs MarkItDown 34,508.** Mostly the NCUA tables (18,334 vs 16,066), which PackForAI
  writes as Markdown tables and MarkItDown as plain lines.

## What this run supports

- Headings and tables: PackForAI ahead on documents it was not developed on (headings 0.853 vs 0.333, tables
  0.788 vs 0.562); text kept and reading order equal (0.970, 0.986).
- Page clutter: 1 repeated header or footer line vs 16.
- Known weak spots shown here: decimal-numbered paragraphs with a hanging indent read as tables; complex financial
  tables; neighbouring tables merged; wrapped lines inside table cells.
