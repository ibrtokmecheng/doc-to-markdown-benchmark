# Fifth held-out run, 2026-11-24: how it was run and what was checked

## Protocol

1. The conversion engine was frozen at 5284170 (`motor/iki-satir-baslik-kas24`), the engine in production since worker
   revision 00046. Since the fourth held-out run it joins decimal section numbers set apart by a hanging indent
   ("1.4.1") to their text when the document has a related section number, marks numbered titles such as
   "1.3 Cancellation." as headings, drops page labels such as "ii" and "1-3", and accepts numbered headings of up to
   15 words. It was developed on `corpus/`, `holdout/`, `holdout2/`, `holdout3/` and `holdout4/`, which all count as
   development data now.
2. The fifth held-out set (`holdout5/`, commit b8a4fd7) was chosen and answered by a separate agent that ran no git
   command, never ran either tool or any text extractor, never read the engine code, README.md or any earlier
   result, and never saw any output. PDF answers were typed from page images. The selection rule was written at
   19:37 UTC, before any listing was read; the set was frozen at 20:14 UTC.
3. Both tools were run on the set once, from commit b8a4fd7: `node run-packforai.mjs holdout5 <out>` and
   `<venv>/python -I run_markitdown.py holdout5 <out>` (MarkItDown 0.1.9, Python 3.12.13), then
   `node score.mjs holdout5 <out>` with scorer 1.2.0 (Node 24.22.1). The engine and the scorer were not changed after
   this run.

Housekeeping: MarkItDown also converted `SELECTION.md` and `generate_holdout5.py` and the PackForAI runner rejected
them; those stray outputs were deleted before scoring.

The set has 9 documents, not 10: for the third time no document of the two-column technical report kind met the
selection rule, even with a three-month window and two series added by a dated amendment (SELECTION.md lists every
series tried and why each failed). The statistical release (kind (a)) comes from a series added by an amendment
after the three series written first had failed (one series no longer exists, two hosts refused plain curl);
SELECTION.md records it as a deviation. It is kept here. Without it (8 files) the averages are: text 0.975 for both;
order 1.000 vs 0.975; headings 0.982 vs 0.500; tables 0.774 vs 0.700 (PackForAI first). The direction is the same;
the table gap is smaller.

## Result (scorer 1.2.0)

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.978  1.000  0.986  0.807     86      8      0     43112
packforai.compact    0.972  1.000  0.986  0.620     85      8      0     42572
markitdown           0.978  0.978  0.400  0.619    139     43      0     45924
```

For comparison only: the engine frozen for the fourth run (e7e91a7), run on the same files after the blind run,
gave byte-identical output for all nine files, so the scores are the same. None of these documents has the layouts
the changes since e7e91a7 address. To make sure the comparison run really used the older engine, both engines were
also run on the fourth set's FAA advisory circular: e7e91a7 writes 243 table lines and 26 headings for it, 5284170
none and 46. Neither engine was tuned on this set.

## Surprising results, checked against the outputs

- **CFTC Financial Data for FCMs, tables 0 for both tools.** New engine limitation: the page is stored upright
  (612 × 1008 pt) and shown turned by 90 degrees (`/Rotate 90`). PackForAI reads the text positions without the
  turn, so every table cell comes out as a line of its own: all text is kept (1.00) but no table is written.
  MarkItDown writes no table either. Neither tool scores any of the 366 expected cells.
- **Generated safety report, text 0.80 for both tools.** The four missed sentences are each in a table cell that
  wraps onto a second line (the "Open findings" table, which also runs over two pages), the same limitation as in
  the third and fourth sets. PackForAI recovered 14 of that table's 35 cells, MarkItDown 3.
- **Reclamation 24-Month Study, PackForAI tables 1.00 (MarkItDown 0.13).** Both large reservoir tables (431 and 428
  cells) were recovered completely. The 69 cells that match no expected cell are in the other tables of the kept
  pages, which the answer file does not cover (MarkItDown: 75).
- **NASA NPR 1600.3B, PackForAI headings 26 of 28 (MarkItDown 0), and 7 extra copies of a running header.** The
  three appendix lines of the table of contents, which have no page numbers or leader dots, were joined into one
  heading line, so "Appendix B. Acronyms" and "Appendix C: References" do not stand as headings of their own. The
  running header ("NPR 1600.3B -- TOC", "-- Preface", "-- Chapter1" …) changes on every page and shares a line with
  the repeated notice "This document does not bind the public …", so it is not removed as page clutter; MarkItDown
  keeps both on every page (37 extra copies).
- **Tokens, PackForAI 43,112 vs MarkItDown 45,924.** About 6% fewer, mostly the Reclamation tables and the NASA
  directive (6,164 vs 7,432).

## What this run supports

- Headings and tables: PackForAI ahead on documents it was not developed on (headings 0.986 vs 0.400, tables 0.807
  vs 0.619); text kept equal (0.978); reading order 1.000 vs 0.978.
- Page clutter: 8 repeated header or footer lines vs 43; output about 6% smaller.
- The changes made after the fourth run did not alter any output on these nine documents; this set neither
  confirms nor refutes them.
- Known weak spots shown here: pages stored upright and shown turned (no table); wrapped lines inside table cells;
  table-of-contents lines without page numbers joined into one heading; running headers whose text changes from
  page to page.
