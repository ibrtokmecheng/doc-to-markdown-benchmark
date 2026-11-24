# Held-out test set 2: selection record

This folder is the second held-out test set (the third frozen set, after `corpus/` and `holdout/`) for the
doc-to-Markdown benchmark (PackForAI vs Microsoft MarkItDown), built with the same method as `holdout/`. Same layout as `corpus/` and `holdout/`: documents here, answers in
`ground-truth/<file>.json`, scored with

```
node score.mjs holdout2 <outDir>
```

Status: selection fixed first (rule and picks below), then downloaded; answers written blind (see below).

## Blind protocol

The documents are chosen and the answers written **before** any converter touches them:

- PackForAI, MarkItDown and every other document converter or text extractor (pdftotext, pdfminer, pdfplumber,
  pypdf text extraction, OCR) are **not** run on these files. pypdf is used only to keep a page range and to count
  pages; `pdfinfo` only for page count and page size; `pdftoppm` only to render pages to images for reading;
  `pdffonts` only once, on the generated PDF, to confirm its font names.
- The conversion engine code (`aireadydoc/services/`, `packforai-motor*`), earlier results (`results/`) and earlier
  development or scratchpad outputs are not opened.
- Public PDFs: every check is copied from the rendered pages (read as images), not from a text layer.
- Generated files: every check is derived from the data in `generate_holdout2.py`, which also writes the files.

## Selection rule for the public PDFs (fixed before any document was downloaded or opened)

1. **Kinds**: one document of each of these kinds, each from a publisher that is not in `corpus/` (Office of the
   Federal Register/GPO, Senate committee, Census Bureau) or `holdout/` (BEA, CDC MMWR, IRS, NIST), and a different
   publisher for each kind:
   (a) a weekly or monthly statistical news release with data tables,
   (b) an agency guidance document with numbered headings and lists,
   (c) a technical/scientific report set in columns,
   (d) a budget or financial statement made mostly of tables.
2. **Hosts**: official `.gov` hosts only, fetched with plain `curl` (default user agent, no browser emulation, no
   cookies). On 2026-11-24 `usda.gov`, `ed.gov`, `hud.gov`, `opm.gov` and `transportation.gov` answered HTTP 403 to
   plain curl and were dropped rather than worked around (so no USDA WASDE); `bls.gov`, `gao.gov`, `ssa.gov`,
   `cbo.gov`, `osha.gov` and `ftc.gov` were already dropped for the same reason in `holdout/`.
3. **Fixed issue, not a hand-picked one**: the issue or document **first published in July 2025** in a named
   series, taken from the publisher's own listing (titles and dates only). July 2025 is a fixed month chosen before
   any listing was read (`holdout/` used the first issue of calendar 2025). Ties go to the earliest publication time,
   then to the lowest series number. The series for each kind, in order of preference (the next one is used only if
   the host refuses plain curl or the file is 5 MB or larger):
   (a) U.S. Department of Labor, Employment and Training Administration, *Unemployment Insurance Weekly Claims* news
       release (archive list at `oui.doleta.gov/unemploy/claims_arch.asp`); then Federal Reserve G.17; then EIA
       *Short-Term Energy Outlook*.
   (b) U.S. Food and Drug Administration guidance documents, **final** guidance only, by issue date in FDA's guidance
       search listing (`fda.gov/files/api/datatables/static/search-for-guidance.json`); ICH guidelines are excluded
       because they are not U.S. Government works; then OMB memoranda (M-25 series, by upload month).
   (c) U.S. Geological Survey *Fact Sheet* series, by `displayToPublicDate` in the USGS Publications Warehouse
       (`pubs.usgs.gov/pubs-services/publication/?seriesName=Fact Sheet&year=2025`).
   (d) U.S. Department of the Treasury, Bureau of the Fiscal Service, *Monthly Treasury Statement* (the statement
       published in July 2025 is the one for June 2025).
4. **Size**: under 5 MB. Documents over 15 pages keep a contiguous page range that starts at page 1 and ends at the
   end of a section or table (chosen from the rendered pages' headings only), cut with pypdf.
5. **No tool influence**: no document is swapped after download, and nothing about how any converter handles a
   document is looked up or tried. (Disclosure: the branch's latest commit subject, seen in `git log` while
   checking the branch, names PDF areas the engine is being worked on; the rule above was written so that the
   picks follow from the series and the date alone.)

## Public documents chosen by the rule (US federal works, public domain under 17 U.S.C. 105)

| file | kind | publisher | URL | why |
|---|---|---|---|---|
| `pub-dol-ui-claims-070325.pdf` | (a) weekly statistical news release | U.S. Department of Labor, Employment and Training Administration | https://oui.doleta.gov/press/2025/070325.pdf | First weekly claims release published in July 2025 (3 July 2025); DOL's most-watched weekly release: narrative plus national and state tables |
| `pub-fda-bsufa-meetings.pdf` | (b) agency guidance document | U.S. Food and Drug Administration (CDER) | https://www.fda.gov/media/113913/download | First final guidance with a July 2025 issue date in FDA's listing (18 July 2025): *Formal Meetings Between the FDA and Sponsors or Applicants of BsUFA Products, Guidance for Industry*; standard FDA guidance layout with numbered sections and lists |
| `pub-usgs-fs20253016.pdf` | (c) technical report in columns | U.S. Geological Survey | https://pubs.usgs.gov/fs/2025/3016/fs20253016.pdf | First USGS Fact Sheet made public in July 2025 (9 July 2025, 11:50; FS 2025-3016, a resource assessment) |
| `pub-treasury-mts-202506.pdf` | (d) financial statement tables | U.S. Department of the Treasury, Bureau of the Fiscal Service | https://fiscaldata.treasury.gov/static-data/published-reports/mts/MonthlyTreasuryStatement_202506.pdf | The Monthly Treasury Statement published in July 2025 (June 2025 statement); the federal government's monthly receipts and outlays tables |

Pre-download check (HTTP HEAD with plain curl, 2026-11-24): all four answered 200 `application/pdf`, sizes 632,960,
366,602, 1,590,508 and 3,503,068 bytes, all under 5 MB.

### Download record (2026-11-24, plain curl, each file into its own empty folder first)

| file | served file sha256 | pages served | kept | file in this folder (sha256) |
|---|---|---|---|---|
| `pub-dol-ui-claims-070325.pdf` | `42f93aff03d17a37811ff827353107f5066ed6957f672f47d73d430bf236b655` (632,960 bytes) | 9 | all | same as served |
| `pub-fda-bsufa-meetings.pdf` | `a6cb3d8e1d29c25db64e592876c72fc7c7b29940a284d3df458164019a96c383` (366,602 bytes) | 23 | pages 1-15 (two cover pages, table of contents, guidance pages 1-12 = sections I-VII); section VIII starts at the top of PDF page 16; pages 16-23 are sections VIII-XIV and References | `d43daf072f3864f05885cf79e479ecb08a2ba0e6c71c499997aa69e035fe14bf` |
| `pub-usgs-fs20253016.pdf` | `76523873e3be1f9bf116beb5be1ed558c8652ae30f65207f7f7c554256d84ea2` (1,590,508 bytes) | 4 | all | same as served |
| `pub-treasury-mts-202506.pdf` | `ccc4a50e85b1a2ac70939db0e87c0fc73ffbe753664db803e70882573da68d68` (3,503,068 bytes) | 40 | pages 1-10 (cover, highlight/contents/introduction, Figures 1-8, Tables 1-4; the Contents lists Receipts on page 10 and Outlays from page 11); pages 11-40 are Tables 5-9 and the explanatory notes | `8fc10c0400bd8684dbfc962ebb15b988d458a184233cced44008e4e8a6a6379c` |

Page ranges were chosen from low-resolution renders of the contents/heading pages only, then cut with pypdf 7.1.1
(`PdfWriter.add_page` for each kept page plus the document information dictionary; deterministic: two runs gave the
same bytes), with `uv run --with pypdf python3 -I cut_pages.py <served.pdf> <out.pdf> <first> <last>` and the same
script as `holdout/SELECTION.md`:

```python
import sys
from pypdf import PdfReader, PdfWriter
src, dst, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
reader = PdfReader(src)
writer = PdfWriter()
for i in range(first - 1, last):
    writer.add_page(reader.pages[i])
if reader.metadata:
    writer.add_metadata({k: v for k, v in reader.metadata.items() if isinstance(k, str)})
with open(dst, "wb") as fh:
    writer.write(fh)
```

The cut keeps every kept page's content and resources unchanged but drops document-level structures (tag tree,
outline), so both cut files are untagged PDFs (the served FDA PDF is tagged; the served MTS PDF is not). The DOL and
USGS files are tagged and kept as served.

## Generated documents

Written by `generate_holdout2.py` (deterministic; new content, not reused from `generate_corpus.py` or
`holdout/generate_holdout.py`), run as
`uv run --with python-docx --with openpyxl --with python-pptx --with reportlab python3 -I holdout2/generate_holdout2.py`
from the benchmark folder. Rule: one ordinary business document per format, using features such documents commonly
have; nothing was designed around any converter's known strengths or weaknesses. Running the script twice gives
byte-identical files (python-docx 1.2.0, openpyxl 3.1.5, python-pptx 1.0.2, lxml 6.1.3, reportlab 5.1.0, Python
3.14.6). Two names were changed during writing because the script's audit rule rejected them: a table cell
'Travel' and the sheet name 'Pipeline' were substrings of the first file names (`gen-travel-policy.docx`,
`gen-sales-pipeline.xlsx`), which a converter writes into its output; the files are now `gen-expense-policy.docx`
and `gen-revenue-tracker.xlsx`. The price list came out at 2 pages, not the 3 first planned, and was kept.

| file | what it is | sha256 |
|---|---|---|
| `gen-expense-policy.docx` | travel and expense policy: Title + Subtitle, auto-numbered Heading 1/2 (numbers from Word numbering, not text), key-value table without a header row, three-level numbered list (1./a./i.), a second list restarting at 1, two-level bullets, table with header cells merged across and down, table with row-group cells merged down in the body, hyperlink, e-mail address, soft line break, bold/italic runs, page header and footer | `529edced52e516a34fa1fe5303827c1912ca46d1175c7c4064fde52dc649112d` |
| `gen-revenue-tracker.xlsx` | 3 sheets: monthly revenue with a two-row header (quarters merged across, three headers merged down), negative currency `-$8,450`, 34 formulas saved with computed values, one-decimal percent; CRM pipeline with US dates, currency with cents, whole percent, booleans, account numbers stored as text with leading zeros, a formula column, autofilter, frozen header; assumptions sheet | `d35bec669cbd314a9f4cdd55678f97ff7db9738f546b73d3fb2ddbf0e6e3079e` |
| `gen-qbr-deck.pptx` | 7-slide quarterly review: title slide, Section Header slide, auto-numbered list, native table, process diagram of grouped shapes plus a free text box, Comparison slide, two-level bullets, speaker notes on 3 slides | `865b19f28236083572aa8c26cb6673be5d0274e2abe5026eaee74f279a32447b` |
| `gen-support-tickets.csv` | help-desk export: comma delimiter, every field quoted, LF, UTF-8 without BOM, quoted fields with embedded line breaks (6), commas, doubled quotes, thousands separators, empty fields, ISO 8601 timestamps, non-ASCII names | `206ad34bfb05eca41e5aa187028251a52d7be3a03504e0e1f4e95186d51f85e0` |
| `gen-product-catalog.json` | product catalog export: minified on one line, top-level array of 8 objects, nested objects and arrays (arrays of objects, of numbers, of strings), nulls, booleans, empty array and object, UTC-offset timestamps, non-ASCII text, an escaped quote | `4eeb1453fad4a3ea39ad2a54494aafab1f12afe775c0eef5222b43b9e9899ea1` |
| `gen-price-list.pdf` | ReportLab price list, 2 pages: title and headings by font size and Helvetica-Bold only, numbered and bulleted lists, one 45-row table continuing onto page 2 with its header row repeated, running header and footer ('Page N of 2') | `2c470705a9799bd94bb477a2586c4a1211f4fd9556aa74aa0bb37a31c6f19d22` |

## Checks per file

| file | must_contain | ordered | headings | tables (non-empty cells) | noise | absent |
|---|---|---|---|---|---|---|
| `gen-expense-policy.docx` | 31 | 7 | 9 | 3 (61) | 0 | 0 |
| `gen-revenue-tracker.xlsx` | 16 | 7 | 0 | 3 (247) | 0 | 0 |
| `gen-qbr-deck.pptx` | 25 | 7 | 7 | 1 (30) | 0 | 0 |
| `gen-support-tickets.csv` | 18 | 5 | 0 | 1 (385) | 0 | 0 |
| `gen-product-catalog.json` | 17 | 5 | 0 | 0 | 0 | 0 |
| `gen-price-list.pdf` | 11 | 7 | 4 | 1 (276) | 3 | 0 |
| `pub-dol-ui-claims-070325.pdf` | 25 | 7 | 7 | 8 (638; the page-6 table is partial) | 0 | 0 |
| `pub-fda-bsufa-meetings.pdf` | 33 | 8 | 17 | 3 (36) | 1 | 0 |
| `pub-treasury-mts-202506.pdf` | 15 | 8 | 7 | 4 (326; Tables 3 and 4 are partial) | 0 | 0 |
| `pub-usgs-fs20253016.pdf` | 24 | 7 | 7 | 2 (415) | 0 | 2 |

## Answers and audit

- Public PDFs: answers typed from the rendered pages (pdftoppm, 90-230 dpi, cropped and read as images). Every
  transcribed table was checked with the arithmetic the document implies, by a throwaway script (not committed) that
  aborts on any mismatch: DOL change columns = differences, state rows sum to the US Total, continued-weeks rows sum
  to TOTAL, 4-week averages = means of four weeks; USGS Table 2 columns sum to both total rows; MTS months sum to
  Year-to-Date, outlays - receipts = deficit, on- + off-budget = total, financing rows sum, gross - refunds = receipts,
  and shared figures agree across Tables 1-4 (within the statement's own rounding of 1-3). A second pass re-read every
  table that arithmetic cannot pin (USGS Table 1, MTS Tables 1-4 digit by digit, FDA Tables 1-3, DOL page-8 tables)
  and every phrase, anchor, heading and absent entry against the zoomed images; it changed no check string.
- Generated files: `generate_holdout2.py` reads each DOCX/XLSX/PPTX/CSV/JSON file back (including heading numbering,
  list levels, merged cells, cached formula values, auto-numbered paragraphs, group shapes and speaker notes) and
  verifies every check against it, plus the audit rules of `holdout/` (no file name or converter-added text in a
  check, prose phrases of 6+ words that occur once, data-file items that are whole fields not inside another field,
  ordered anchors unique, in reading order and never from footnotes or speaker notes). The generated PDF is not read
  back with any text extractor: its checks come from the generator's data in reading order, its 2 pages were
  rendered and looked at, and `pdffonts` was used once to confirm its font names.
- All ten answer files pass `validateGroundTruth` from `score.mjs` 1.2.0 with no errors and no warnings, and
  `node score.mjs holdout2 <empty dir>` finds every document with a matching sha256.

## Known limits (also in each file's notes)

- The PDF text layer was never read, so invisible text-layer content is not checked, and characters whose code
  point cannot be seen are avoided in phrases and anchors. Where table cells or headings must contain them, the
  assumption is stated and applies to every tool alike: ASCII hyphen-minus for negative numbers (DOL, MTS) and for
  'West-Central' (USGS); U+2014 em dash in the USGS Table 1 header and U+2013 en dash in a USGS Table 2 section row;
  superscript note marks written attached to the word ('Prior Year¹', 'Fiscal Year¹'; NFKC turns them into digits)
  except DOL 'STC / Workshare ⁵', which shows a space.
- Cells whose text could not be pinned down are left empty (not scored): the MTS May outlays value printed with a
  leading note mark, and the four MTS '......' (no transactions) cells. A converter's text in those positions counts
  toward `spurious_table_cells`.
- DOL headings are body-size capital or underlined lines (the release has no bold headings); they were listed
  because they are its only section titles. The DOL page-7 table (stacked three-line headers over two groups) is not
  checked.
- The MTS cover and all figures (Sankey, bar and pie charts) may be images and are not checked; this document's body
  after page 3 is tables, so four of its ordered anchors are table titles.
