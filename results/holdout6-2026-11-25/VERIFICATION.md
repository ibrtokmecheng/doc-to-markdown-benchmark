# Sixth held-out run, 2026-11-25: how it was run and what was checked

## Protocol

1. The conversion engine was frozen at 88d7fc4 (`motor/hucre-satiri-kas25`) before the set was opened. Since the
   fifth held-out run it reads pages shown turned (`/Rotate`) as they are shown, reads appendix numbers such as
   "B.1.1" like section numbers, keeps text that wraps inside a table cell in its cell (also over a page break),
   drops running headers and footers that change with the section ("Appendix B", "… -- Chapter1 … Page 5 of 26"),
   keeps a numbered paragraph together at its hanging indent, drops a chapter's first page label set at another
   height, and keeps table-of-contents entries without page numbers one per line. It was developed on `corpus/`
   and `holdout/` to `holdout5/`, which all count as development data now. The engine in production when the set
   was run was f18c775 (worker revision 00050), which has the first two of these changes.
2. The sixth held-out set (`holdout6/`, commit d041b4f) was chosen and answered by a separate agent that ran no git
   command, never ran either tool or any text extractor, never read the engine code, README.md or any earlier
   result, and never saw any output. PDF answers were typed from page images. The selection rule was written at
   08:35 UTC on 2026-11-25, before any listing was read, with amendments at 08:41 and 08:45 UTC; the set was frozen
   at 09:27 UTC. The engine was frozen and committed (88d7fc4) while the set was being built and was not changed
   after the set was opened.
3. Both tools were run on the set once, from commit d041b4f: `node run-packforai.mjs holdout6 <out>` and
   `<venv>/python -I run_markitdown.py holdout6 <out>` (MarkItDown 0.1.9, Python 3.12.13), then
   `node score.mjs holdout6 <out>` with scorer 1.2.0 (Node 24.22.1). The engine and the scorer were not changed after
   this run.

Housekeeping: MarkItDown also converted `SELECTION.md` and `generate_holdout6.py` and the PackForAI runner rejected
them; those stray outputs were deleted before scoring.

**The set has 8 files, not 10.** Two public documents, six generated. No document of kind (a) (a weekly or monthly
statistical release) or kind (b) (an agency directive or guidance document) met the selection rule, even after
each kind got two more series by a dated amendment: most series published nothing in October 2025, the month
federal appropriations lapsed; one host refused plain curl, one served a block page, one series is Excel only, one
is larger than 5 MB in every candidate edition. `holdout6/SELECTION.md` lists every series tried and why each
failed. Kind (c) is the Defense Health Agency's Medical Surveillance Monthly Report (series 2: series 1's host,
on `army.mil`, could not be reached from the selecting machine, which was recorded as a refusal and not worked
around); kind (d) is FEMA's Disaster Relief Fund Monthly Report. Two slips are recorded in SELECTION.md: a script
printed about 1.8 KB of the raw bytes of a skipped MSMR issue (metadata and article titles already shown in the
listing; no text layer was read), and one diagnostic request was not plain curl (`--resolve`, it failed). Neither
file involved is in the set.

## Result (scorer 1.2.0)

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.992  1.000  0.967  0.856   5462     12      0     51139
packforai.compact    0.983  1.000  0.967  0.583   5460     12      0     50394
markitdown           0.876  0.813  0.400  0.439   1679     13     14     50836
```

For comparison only: the engine in production when the set was run (f18c775), run on the same files after the
blind run, gave the same output for the five non-PDF files and different output for the three PDFs: text 0.983,
order 1.000, headings 0.967, tables 0.856, spurious cells 5513, noise 12, tokens 51,648. The difference in text is
one generated invoice, where f18c775 dropped the last word of a wrapped table cell ("hotel") out of the table into
the next paragraph. Neither engine was tuned on this set.

FEMA's pages 8-13 and 15 are stored upright and shown turned (`/Rotate 90`), so this set also tests the change for
such pages, which both engines above have. For comparison only, the engine frozen for the fifth run (5284170),
which reads those pages without the turn, was run on the same files: tables 0.817, spurious cells 1,409, tokens
44,993 (text 0.983, headings 0.967). On FEMA it recovers 0.21 of the table cells (Appendix B's first rows 0.01,
the Appendix D chart tables 0.04-0.05) against 0.49 (0.92; 0.30-0.43). The rise in spurious cells and tokens comes
from the same pages: their tables are now written as tables, and the answer file transcribes only part of them.

After the run, an independent review of the engine changes (with synthetic documents, in two rounds) found cases
where they could put rows or lines in the wrong place: a repeated line whose amount changes ("Balance carried
forward") taken for a repeated header and moved below the page's rows; a data row repeated word for word at the
top of every page dropped; a sub-row ("of which …") joined to the total above it; a cell ending in a capital letter
("Vitamin A") read as an open phrase; lettered items joined to a numbered paragraph, and a line starting with an
abbreviation ("Dr. Jones") split from it. They were fixed in 27f140a and its two follow-ups, which also keep the
first copy of each section header rather than one per place and skip a line repeated above a continued table only
when the same line stood right above the table on its first page; that version is the one released after this run.
On the six development sets its output is byte for byte that of 88d7fc4. On this set it loses no word against
88d7fc4 and moves two repeated table headers on continuation pages (MSMR, FEMA) to where they are printed; in FEMA
that header block now opens a table of its own ("($ in millions)" appears once more): spurious cells 5,503, tokens
51,330, every other score the same. The figures above are those of the blind run with 88d7fc4. Known limit, also in
the engine before: a table carried over from one page continues on the next page only, not on the page after it.

## Surprising results, checked against the outputs

- **Spurious table cells, PackForAI 5,462 vs MarkItDown 1,679.** Almost all are cells of real tables that the
  answer files do not cover. FEMA (4,441): the Appendix B spend-plan table is answered for its first ten rows only
  (PARTIAL); its other rows (742 cells) and the large tables of pages 9-13 (Appendix B by catastrophic disaster,
  Appendix C), which have no answer, count as spurious. MSMR (1,013): the burden table runs over pages 8-11 and is
  answered for its header and first rows only (PARTIAL). There are real defects among them too: in FEMA's spend
  plan the title line is taken as the header row and the row of footnote markers ("1 1 1 …") and the month row
  become body rows; some rows of the by-disaster table ("4335-Virgin Islands (329) - - - …") are written as one
  paragraph instead of table rows; dollar signs printed apart from their amounts land in the neighbouring cell
  ("| $ 14,133 $ | 15,816 $ |"; the numbers are in place).
- **FEMA tables, PackForAI 0.49 (MarkItDown 0.05).** The Appendix A table (0.80) and the first rows of Appendix B
  (0.92) are recovered; the small data tables under the charts of Appendix C and D are recovered at 0.30-0.43:
  their cells come apart from their labels. MarkItDown writes three cells for most of these tables.
- **MSMR text, MarkItDown 0.33 and order 0.50.** The report is set in three columns; MarkItDown reads across them,
  so one output line holds pieces of three columns ("…ventions with measurable impacts on force the general U.S.
  and global populations. encounters, greatest numbers of affected"). It also keeps 14 line-end hyphens
  ("dis- ease"). PackForAI misses one phrase: the answer has "Matthew W.R. Allman", typed from the page image, and
  both tools print "W. R." as the text layer has it.
- **Noise 12 for both tools.** The MSMR running header alternates between left and right pages ("MSMR Vol. 32 No. 9
  September 2025" and "September 2025 Vol. 32 No. 9 MSMR") and carries the page number ("Page 10"), so it changes on
  every page; both tools keep 7 copies of each. PackForAI writes them as level-6 headings. New engine limitation.
- **Tokens, PackForAI 51,139 vs MarkItDown 50,836.** About equal (0.6% more). MSMR: PackForAI 16,912 vs 23,079;
  FEMA: 25,060 vs 19,329, because PackForAI writes FEMA's wide tables as pipe tables (most cells empty) while
  MarkItDown writes little table structure; the generated JSON export: 2,452 vs 1,571.
- **Generated files.** CSV: MarkItDown text 0.80, order 0, tables 0 (PackForAI 1.00 for all three). XLSX tables
  0.91 vs 0.33. The generated invoice PDF: tables 0.63 vs 0.38, headings 1.00 vs 0. The DOCX: text 0.95 for both
  (the same phrase missed by both).

## What this run supports

- Headings, text and tables: PackForAI ahead on documents it was not developed on (headings 0.967 vs 0.400, text
  0.992 vs 0.876, order 1.000 vs 0.813, tables 0.856 vs 0.439).
- Output size: about equal on this set; smaller on multi-column prose (MSMR), larger on wide tables (FEMA).
- Known weak spots shown here: running headers that alternate between left and right pages and carry the page
  number; small data tables under charts; a table's title line taken as its header row; rows of a wide table
  written as a paragraph; lines marked as headings that are not ("Balance (6) $ 8,413 $ 1,163 $ 9,576", the list
  item "6. Appendix F presents a bridge table …" in FEMA; the heading score counts only expected headings, so it
  does not show this).
- The set is smaller than the earlier ones (8 files, two of them public) and has no statistical release and no
  directive. Its public part rests on two documents.
