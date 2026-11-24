# Held-out test set: selection record

This folder is a second, frozen test set for the doc-to-Markdown benchmark (PackForAI vs Microsoft MarkItDown).
It has the same layout as `corpus/`: documents here, answers in `ground-truth/<file>.json`, scored with

```
node score.mjs holdout <outDir>
```

## Blind protocol

The documents were chosen and the answers written **before** any converter touched them:

- PackForAI, MarkItDown and every other document converter or text extractor (pdftotext, pdfminer, pdfplumber,
  pypdf text extraction, OCR) were **not** run on these files. pypdf is used only to count pages, read structural
  flags (tagged, form dictionary, encryption) and, where noted, to keep a page range; `pdftoppm` is used only to
  render pages to images for reading.
- The conversion engine code (`aireadydoc/services/`, `packforai-motor*`), earlier results (`results/`) and earlier
  development outputs were not opened.
- Public PDFs: every check was copied from the rendered pages (read as images), not from a text layer.
- Generated files: every check is derived from the data in `generate_holdout.py`, which also writes the files.

## Selection rule (fixed before any document was downloaded or opened)

1. **Kinds**: one document of each kind the existing corpus does not have, each from a different publisher than the
   corpus (which has an Office of the Federal Register rule, a Senate committee report and a Census Bureau release)
   and than each other:
   (a) a national-accounts statistical news release with tables,
   (b) a two-column scientific report,
   (c) federal tax form instructions,
   (d) a single-column agency technical/policy publication (one section kept).
2. **Hosts**: official `.gov` hosts only, fetched with plain `curl` (default user agent, no browser emulation).
   Hosts that answered HTTP 403 to plain curl on 2026-11-24 (bls.gov, gao.gov, ssa.gov, cbo.gov, osha.gov, ftc.gov)
   were dropped rather than worked around; this is why the release is from BEA and not BLS, and why no GAO report
   is included.
3. **Fixed issue, not a hand-picked one**: for periodic series, the first issue published in calendar 2025; for
   the others, the current edition of the series' flagship document. Each document is taken as served, with no look
   at its content before it was fixed here.
4. **Size**: under 5 MB. Documents over 15 pages keep a contiguous page range that starts at page 1 and ends at the
   end of a section (chosen from the rendered pages' headings only), cut with pypdf.
5. **No tool influence**: no document was swapped after download, and nothing about how any converter handles a
   document was looked up or tried.

## Public documents (US federal works, public domain under 17 U.S.C. 105)

| file | kind | publisher | URL | why |
|---|---|---|---|---|
| `pub-bea-gdp4q24-adv.pdf` | (a) statistical news release | U.S. Bureau of Economic Analysis | https://www.bea.gov/sites/default/files/2025-01/gdp4q24-adv.pdf | First GDP release of 2025 (Q4 2024 advance estimate, 30 Jan 2025); BEA's flagship release, a narrative plus numbered tables of the kind analysts paste into AI tools |
| `pub-mmwr-7401a1.pdf` | (b) two-column scientific report | Centers for Disease Control and Prevention (MMWR) | https://www.cdc.gov/mmwr/volumes/74/wr/pdfs/mm7401a1-H.pdf | First full report (article a1) of the first MMWR Weekly issue of 2025 (Vol. 74, No. 1); typical two-column public-health paper |
| `pub-irs-iw9.pdf` | (c) form instructions | Internal Revenue Service | https://www.irs.gov/pub/irs-pdf/iw9.pdf | Instructions for the Requester of Form W-9, the most widely exchanged IRS form between businesses; standalone instructions file (no fillable form) |
| `pub-nist-cswp29.pdf` | (d) agency technical publication, one section | National Institute of Standards and Technology | https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf | The NIST Cybersecurity Framework (CSF) 2.0, NIST's most widely used publication; long, so a leading page range is kept |

### Download record (2026-11-24, plain curl, each file into its own empty folder first)

| file | served file sha256 | pages served | kept | file in this folder (sha256) |
|---|---|---|---|---|
| `pub-bea-gdp4q24-adv.pdf` | `65cdc63c9f33ec1ec0933c369494bf99e7f549c3381c9095d52a51e69b7d7af1` (1,320,917 bytes) | 17 | pages 1-7 (narrative, technical notes, list of release tables, Table 1); pages 8-17 are Tables 2-8 and Appendix Tables A-B | `f6b8079310585ff2f6cca02350a8bc1d4237f0e5fe596f5c26ef36ac91c1931f` |
| `pub-mmwr-7401a1.pdf` | `2d7963de37d11f0931a5900287508f12172a744cfec92b8ca63578360bbe3a9e` (264,234 bytes) | 8 | all | same as served |
| `pub-irs-iw9.pdf` | `ec609a8bf9fac7da593355a57e49e0aa4d569eaceca3a7a84255104d864b1c34` (189,808 bytes) | 7 | all | same as served |
| `pub-nist-cswp29.pdf` | `3c31f46fee98cac0c4323453e5109291a213b4de7fef8c058af9bf67f717433c` (1,518,858 bytes) | 32 | pages 1-14 (cover, front matter, sections 1-4; section 5 starts at the top of page 15); pages 15-32 are section 5 and Appendices A-C | `aab529d97459f129af2c8900f5717bda5f3189830eaceb0c6f8996017ab4fc88` |

Page ranges were cut with pypdf 7.1.1 (`PdfWriter.add_page` for each kept page plus the document information
dictionary; deterministic: re-running gives the same bytes), with
`uv run --with pypdf python3 -I cut_pages.py <served.pdf> <out.pdf> <first> <last>` and this script:

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
 The cut keeps every kept page's content and resources
unchanged but drops document-level structures (tag tree, outline, form dictionary), so both cut files are untagged
PDFs. The BEA range ends after Table 1 (the release's headline table) rather than at the 15-page limit, to keep the
hand-transcribed table answers to one dense table page.

## Generated documents

Written by `generate_holdout.py` (deterministic; new content, not reused from `generate_corpus.py`), run as
`uv run --with python-docx --with openpyxl --with python-pptx --with reportlab python3 -I holdout/generate_holdout.py`
from the benchmark folder. Rule: one ordinary business document per remaining format, using features such documents
commonly have; nothing was designed around any converter's known strengths or weaknesses. Running the script twice
gives byte-identical files (python-docx 1.2.0, openpyxl 3.1.5, python-pptx 1.0.2, lxml 6.1.3, Python 3.14.6).

| file | what it is | sha256 |
|---|---|---|
| `gen-quality-review.docx` | supplier quality report: Title + Heading 1/2, three-level bullets, numbered list with lettered sub-items, table with vertically and horizontally merged header cells, GBP table, 3 Word footnotes, hyperlink, page header | `7dea1b0c671a49f039eee4cff8b0326eb3dfa6fc29a043b044e8de07bf71c78d` |
| `gen-opex-tracker.xlsx` | budget-vs-actual workbook, 3 sheets: merged title and note rows, formulas saved with computed values, currency with negatives in parentheses, percent, d mmm yyyy dates, rate, autofilter, frozen header | `43622043c9f16c8f6db38adc213827abb8cdf4eb2d940c615cd83748c93ab8ff` |
| `gen-steering-deck.pptx` | 6-slide steering-committee deck: title slide, two-level bullets, table with merged header cells, Two Content slide, speaker notes on 3 slides | `1b13bcd69c39203c82a4187ff2b436f0b6c833725754f18d8f9aca3e4c2737bd` |
| `gen-stock-export.csv` | European ERP stock export: semicolon delimiter, decimal comma, dd.mm.yyyy, UTF-8 BOM, CRLF, quoted fields with ';' and doubled quotes, non-ASCII names | `c88ed72d460d5e933f4d57546d16faf776b91ebdd281ebdb6092e62e9617cb55` |
| `gen-purchase-orders.json` | purchase-order export: nested objects and arrays, nulls, booleans, empty arrays, non-ASCII, escaped quotes | `e6322704d7efecd7d0870c4440d2f32d694d2598a2b729fae4d434f75fad61cd` |

## Checks per file

| file | must_contain | ordered | headings | tables (non-empty cells) | noise | absent |
|---|---|---|---|---|---|---|
| `gen-quality-review.docx` | 26 | 7 | 7 | 2 (64) | 0 | 0 |
| `gen-opex-tracker.xlsx` | 16 | 7 | 0 | 3 (179) | 0 | 0 |
| `gen-steering-deck.pptx` | 17 | 6 | 6 | 1 (24) | 0 | 0 |
| `gen-stock-export.csv` | 19 | 5 | 0 | 1 (385) | 0 | 0 |
| `gen-purchase-orders.json` | 19 | 6 | 0 | 0 | 0 | 0 |
| `pub-bea-gdp4q24-adv.pdf` | 20 | 7 | 6 | 2 (256) | 0 | 0 |
| `pub-irs-iw9.pdf` | 22 | 8 | 22 | 0 | 1 | 1 |
| `pub-mmwr-7401a1.pdf` | 29 | 8 | 20 | 1 (34) | 2 | 8 |
| `pub-nist-cswp29.pdf` | 23 | 8 | 15 | 0 | 1 | 0 |

## Answers and audit

- Public PDFs: answers typed from the rendered pages (150-300 dpi). Every file's `notes` states what is and is not
  checked and why. Then a second pass re-rendered every page and re-checked every must_contain phrase, ordered
  anchor, heading, table cell, noise and absent entry against the image; it found one wrong description (BEA page
  furniture is on pages 2-6, not 2-7), fixed in that file's notes; no check string changed.
- Generated files: `generate_holdout.py` reads each written file back (including the DOCX footnotes part and the
  XLSX cached formula values) and verifies every check against it, plus the corpus audit rules: no file name or
  converter-added text in a check, prose phrases of 6+ words that occur once, data-file items that are whole
  fields, ordered anchors unique, in reading order and never taken from footnotes or speaker notes.
- All nine answer files pass `validateGroundTruth` from `score.mjs` 1.2.0 with no errors and no warnings.
- Known limits of the blind protocol (also in each PDF's notes): the PDF text layer was never read, so invisible
  text-layer content is not checked, and characters whose code point cannot be seen (typographic quotes, dash and
  minus variants, the '≥' sign) are avoided in phrases and anchors; where table cells or headings must contain them
  (MMWR '≥' and en dashes, ASCII hyphen-minus assumed for BEA negative numbers and IRS 'W-9') the assumption is
  stated, and it applies to both tools alike.
