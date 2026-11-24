# Document-to-Markdown benchmark: PackForAI vs Microsoft MarkItDown

A small, reproducible benchmark of how well two converters keep a document's content and structure when they
turn it into Markdown for language models. Write-up: https://packforai.com/blog/packforai-vs-markitdown-benchmark

We make PackForAI. To keep the comparison checkable, the answer files were written before either tool ran, each
held-out set was chosen and answered by a reviewer who never ran either tool, and every raw output is included.

## What is here

| Path | Contents |
|---|---|
| `corpus/` | First set: 3 public U.S. government PDFs and 6 generated files, with answer files in `corpus/ground-truth/`. PackForAI was developed against this set after run 1. |
| `holdout/` | First held-out set: 4 public U.S. government PDFs and 5 generated files, chosen and answered blind (`holdout/SELECTION.md`), frozen before either tool ran on them. PackForAI was worked on after that run, so it now counts as development data. |
| `holdout2/` | Second held-out set: 4 public U.S. government PDFs and 6 generated files, chosen and answered blind the same way (`holdout2/SELECTION.md`). Development data since the PDF reader changed. |
| `holdout3/` | Third held-out set: 3 public PDFs (Federal Reserve, DOE, FDIC) and 6 generated files, chosen and answered blind the same way (`holdout3/SELECTION.md`; no document met the rule for a fourth, two-column kind). Development data since the list and side-heading change. |
| `holdout4/` | Fourth held-out set: 3 public PDFs (FHFA, FAA, NCUA) and 6 generated files, chosen and answered blind by a reviewer who did not read earlier results (`holdout4/SELECTION.md`). |
| `score.mjs` | The scorer (version 1.2.0). Rules and the reasons for every change are in `SCORING.md`. Tests: `node --test score.test.mjs`. |
| `run_markitdown.py` | Runs MarkItDown on a folder (`MarkItDown(enable_plugins=False)`, no LLM, no Azure Document Intelligence). |
| `run-packforai.mjs` | Runs PackForAI's production conversion code on a folder (free plan, OCR off, network blocked). The engine itself is not part of this kit; see "Reproducing the PackForAI side". |
| `generate_corpus.py`, `holdout/generate_holdout.py`, `holdout2/generate_holdout2.py`, `holdout3/generate_holdout3.py`, `holdout4/generate_holdout4.py` | Deterministic generators for the generated files and their answers. |
| `results/run1-2026-11-24/` | First run, before PackForAI's fixes (scored again with 1.2.0: `results-scorer-1.2.0.json`, `summary-scorer-1.2.0.txt`). `verification.json` records the checks of surprising results. |
| `results/run2-2026-11-24/` | First set again, after the fixes. Not a fair test: PackForAI was tuned on these files. |
| `results/holdout-2026-11-24/` | First held-out set, each tool run once. `VERIFICATION.md` explains the protocol and the surprising results. |
| `results/holdout2-2026-11-24/` | Second held-out set, each tool run once, with its own `VERIFICATION.md`. |
| `results/holdout3-2026-11-24/` | Third held-out set, each tool run once, with its own `VERIFICATION.md`. |
| `results/holdout4-2026-11-24/` | Fourth held-out set, each tool run once, with its own `VERIFICATION.md`. |

## Results

Fourth held-out set (9 documents), scorer 1.2.0:

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.970  0.986  0.853  0.788    741      1      0     37028
packforai.compact    0.958  0.986  0.853  0.555    739      0      0     36390
markitdown           0.970  0.986  0.333  0.562     78     16      0     34508
```

707 of PackForAI's unmatched cells are in the NCUA report, whose large tables it rebuilt poorly. Decimal-numbered
paragraphs with a hanging indent (FAA advisory circular) are still read as two-column tables. See
`results/holdout4-2026-11-24/VERIFICATION.md`.

Third held-out set (9 documents), scorer 1.2.0:

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.949  1.000  0.676  0.907   6909      9      0     61486
packforai.compact    0.942  1.000  0.676  0.673   6907      7      0     60852
markitdown           0.848  0.889  0.333  0.558    515     28      2     53093
```

Most of PackForAI's unmatched table cells (5,832) are real tables of the Federal Reserve release that the answer
file does not transcribe. See `results/holdout3-2026-11-24/VERIFICATION.md` for this and the other surprising
results (lists with a hanging indent and side headings read as two-column tables; MarkItDown running the words of
the Federal Reserve release together).

Second held-out set (10 documents), scorer 1.2.0:

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   0.901  0.900  0.939  0.861   1557      0      1     40231
packforai.compact    0.890  0.900  0.939  0.677   1557      0      1     39763
markitdown           0.922  0.929  0.286  0.474    405     15      2     43640
```

PackForAI's lower text and order scores come from one PDF (Department of Labor): its font is not embedded and its
letters are spaced by kerning, and pdf.js, which PackForAI reads PDF text with, puts spaces inside the words. See
`results/holdout2-2026-11-24/VERIFICATION.md` for this and the other surprising results.

First held-out set (9 documents), scorer 1.2.0:

```
candidate             text  order  heads tblRec   spur  noise absent    tokens
packforai.document   1.000  1.000  0.875  0.643    115      2      1     38070
packforai.compact    0.988  1.000  0.875  0.328    115      0      1     37548
markitdown           0.965  0.986  0.333  0.426    182     30      9     41845
```

- `text`: share of checked phrases present. `order`: share of ordered anchors in the right order.
- `heads`: share of headings output as Markdown headings. `tblRec`: share of table cells recovered in place.
- `spur`: table cells that match no answer cell. `noise`: repeated page furniture beyond its first copy.
- `absent`: leftovers that must not appear (split words such as `conju- gate`, hidden text-layer stamps).
- `tokens`: o200k_base (gpt-tokenizer), special-token strings counted as ordinary text.

PackForAI's compact.md writes spreadsheet tables as CSV text, which the scorer's CSV reader does not accept when
it holds thousands separators or semicolons; its table score understates it. See `results/holdout-2026-11-24/VERIFICATION.md`.

## Running it

Requirements: Node.js 20+, Python 3.12 with `markitdown==0.1.9`, and for the generators `uv`.

```sh
# MarkItDown
python -I run_markitdown.py holdout out/
# score (writes JSON to stdout and a summary to stderr)
node score.mjs holdout out/ > results.json
```

The scorer scores `<file>.packforai.document.md`, `<file>.packforai.compact.md` and `<file>.markitdown.md` for every
answer file it finds; a missing output is reported, not guessed.

### Reproducing the PackForAI side

`run-packforai.mjs` calls PackForAI's conversion code directly and is included to show exactly how the outputs
were produced; that code is not open source. To check the PackForAI outputs yourself, convert the same files at
https://packforai.com (or with its API) and save `document.md` as `<file>.packforai.document.md` next to the
MarkItDown outputs. The outputs in `results/holdout-2026-11-24/` were produced by engine commit `d695968`, those in
`results/holdout2-2026-11-24/` by engine commit `fc6c6ed`, those in `results/holdout3-2026-11-24/` by engine commit `65dfcb0`
(current PDF.js, with PDF.js 1.10 supplying the spacing of doubtful lines), those in `results/holdout4-2026-11-24/` by
engine commit `e7e91a7` (lists with a hanging indent and side headings read as text).

## Sources and licences

- Public PDFs are works of the U.S. federal government (BEA, CDC, IRS, NIST, Census Bureau, Federal Register,
  U.S. Senate, Department of Labor, FDA, Treasury, USGS, Federal Reserve Board, Department of Energy, FDIC, FHFA, FAA, NCUA), in the
  public domain in the United States. Source URLs
  are in each answer file and in the `SELECTION.md` of each held-out set. Two PDFs in each held-out set are page
  ranges cut from the published files.
- Generated documents, answer files and outputs: CC0 1.0. Scripts: MIT.
- MarkItDown is Microsoft's open-source project (MIT). Its outputs are included as produced.
