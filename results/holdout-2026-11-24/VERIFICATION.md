# Held-out run, 2026-11-24: how it was run and what was checked

## Protocol

1. The conversion engine was frozen at `motor/donusum-kas24` b1400c8 after all development and an independent
   adversarial code review. Development used only the original corpus (`corpus/`, runs 1 and 2).
2. The held-out set (`holdout/`, commit 0019b93) was chosen and answered by a separate agent that never ran either
   tool, never read the engine code and never saw earlier outputs. PDF answers were typed from page images.
3. Both tools were run on the held-out set once, from the release-candidate commit d695968 (engine + site +
   kit): `node run-packforai.mjs holdout <out>` and `<venv>/python -I run_markitdown.py holdout <out>`
   (MarkItDown 0.1.9, Python 3.12.13), then `node score.mjs holdout <out>` with scorer 1.2.0.
4. The engine was not changed after this run. Findings below are reported as they are.

Housekeeping: `holdout/` also holds `SELECTION.md` and `generate_holdout.py`. The PackForAI runner rejected them
(production accepts only document types) and MarkItDown converted them; those stray outputs were deleted and the
scorer was run again on the unchanged tool outputs. Scores did not change; only the "unmatched output" warning went.

## Result (scorer 1.2.0)

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   1.000  1.000  0.875  0.643    115      2      1     38070
packforai.compact    0.988  1.000  0.875  0.328    115      0      1     37548
markitdown           0.965  0.986  0.333  0.426    182     30      9     41845
```

## Surprising results, checked against the outputs

- **PackForAI compact, tables 0.328.** compact.md writes spreadsheet and CSV tables as CSV text. The scorer's CSV
  reader (1.2.0, rule 6) rejects CSV lines that contain numbers with thousands separators or a semicolon
  delimiter as ambiguous, so the XLSX and CSV tables in compact.md are not recognised at all (0 tables parsed).
  The values are there. This is a scorer limitation that only affects compact.md; it was found after the run, so
  the scorer was not changed. Compare tables on document.md.
- **BEA release, PackForAI tables 0.039 with 113 spurious cells; MarkItDown 0.** Real engine limitation: in the
  22-column Table 1 each row's numbers are drawn as one run of text separated by single spaces, so the engine
  cannot split them into columns; every row has its label and then all its numbers, in order, in one cell. The
  contact block at the top of page 1 is also turned into a small false table. MarkItDown produced no table.
- **MMWR article, PackForAI headings 0.25, tables 0 (MarkItDown 0 and 0).** Real limitation: the section headings
  are on lines of their own but were not marked as headings, and the recommendations table (long text cells
  that wrap) is read as paragraphs. All text is present (text recall 1.000).
- **Semicolon CSV, MarkItDown text 0.684, tables 0 with 145 spurious cells.** Real: MarkItDown splits the
  semicolon file at commas, so decimal commas ("0,14") cut cells apart. PackForAI detects the delimiter.
- **IRS instructions, one absent-text violation for both tools.** Both outputs contain the same flagged string,
  the split word "par- ty"; no difference between the tools.
