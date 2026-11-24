# Held-out test set 3: selection record

This folder is the third held-out test set (the fourth frozen set, after `corpus/`, `holdout/` and `holdout2/`) for
the doc-to-Markdown benchmark (PackForAI vs Microsoft MarkItDown), built with the same method as `holdout2/`. Same
layout: documents here, answers in `ground-truth/<file>.json`, scored with

```
node score.mjs holdout3 <outDir>
```

Status: FROZEN (2026-11-24). The selection rule below was written at 14:20 UTC, before any document, listing or
catalogue page was downloaded or opened; Amendment 1 was added at 14:32 UTC (see there); picks, download record,
answers and audit follow. **This set has 9 files, not 10: kind (c) (a column-set technical report) is left out
because every series listed for it failed under the rule (see "How the rule resolved").**

## Blind protocol

The documents are chosen and the answers written **before** any converter touches them:

- PackForAI, MarkItDown and every other document converter or text extractor (pdftotext, pdfminer, pdfplumber,
  pypdf text extraction, OCR) are **not** run on these files. pypdf is used only to keep a page range and to count
  pages; `pdfinfo` only for page count and page size; `pdftoppm` only to render pages to images for reading;
  `pdffonts` only once, on the generated PDF, to confirm its font names.
- The conversion engine code (`aireadydoc/services/`, `packforai-motor*`), earlier results (`results/`), scratchpad
  folders and earlier development outputs are not opened. No git command is run. The only files read outside this
  folder are `README.md`, `SCORING.md`, `score.mjs` (read, not run), `holdout/SELECTION.md`, `holdout2/SELECTION.md`,
  `holdout2/generate_holdout2.py` and three answer files of `holdout2/ground-truth/` (FDA, USGS, Treasury) as format
  examples.
- Public PDFs: every check is typed from the rendered pages (read as images), never copied from a text layer.
- Generated files: every check is derived from the data in `generate_holdout3.py`, which also writes the files.
- `score.mjs` is not run on this folder by the reviewer; its validation rules (`validateGroundTruth`) and the audit
  rules of `holdout2/` are applied by reading them and re-implementing them in the generator's self-check and in a
  throwaway check of the public answer files (not committed).

## Selection rule for the public PDFs (fixed before any document was downloaded or opened)

1. **Kinds**: one document of each of these kinds, each from a publisher not used before (not the Office of the
   Federal Register/GPO, the Senate or the Census Bureau of `corpus/`; not BEA, CDC (any CDC series), IRS or NIST of
   `holdout/`; not the Department of Labor, FDA, USGS or Treasury/Bureau of the Fiscal Service of `holdout2/`), and
   a different publisher for each kind:
   (a) a weekly or monthly statistical release with data tables,
   (b) an agency guidance document or regulatory guide with numbered headings and lists,
   (c) a technical or scientific report set in two or more columns, authored by federal employees,
   (d) a financial or budget statement made mostly of tables.
2. **Works and hosts**: U.S. federal government works only (public domain under 17 U.S.C. 105). Official `.gov`
   hosts only, fetched with plain `curl` (default user agent, no browser emulation, no cookies; redirects followed
   only while they stay on `.gov` hosts). A host that refuses plain curl (HTTP 403 or another refusal) is dropped,
   not worked around. Already known to refuse and not used: `usda.gov`, `ed.gov`, `hud.gov`, `opm.gov`,
   `transportation.gov`, `bls.gov`, `gao.gov`, `ssa.gov`, `cbo.gov`, `osha.gov`, `ftc.gov`.
3. **Fixed issue, not a hand-picked one**: the issue or document **first published in August 2025** in a named
   series (August 2025 is fixed here, before any listing is read; `holdout/` used the first issue of 2025,
   `holdout2/` July 2025), taken from the publisher's own listing, reading titles and dates only (for kind (c) also
   the author affiliations the listing gives, see below). Ties go to the earliest publication time, then to the
   lowest series or report number. The series for each kind, in order of preference:
   (a) 1. Board of Governors of the Federal Reserve System, **G.17 Industrial Production and Capacity
          Utilization** (monthly; release dates from the Board's G.17 release listing);
       2. U.S. Energy Information Administration, **Short-Term Energy Outlook** (monthly; EIA's STEO archive);
       3. Federal Housing Finance Agency, **FHFA House Price Index** monthly report (FHFA's HPI release listing).
   (b) 1. U.S. Nuclear Regulatory Commission, **Regulatory Guides**, final guides only (no draft guides, DG-xxxx),
          by the issue month NRC's regulatory-guide listing gives;
       2. Federal Aviation Administration, **Advisory Circulars**, by the date in FAA's advisory circular listing
          (cancellation notices excluded);
       3. U.S. Department of Energy, **DOE directives** (Orders, Guides, Manuals, Policies), by approval date at
          `directives.doe.gov`.
   (c) 1. NASA **Technical Memorandum (NASA/TM)**, by publication date in the NASA Technical Reports Server
          (`ntrs.nasa.gov`);
       2. NASA **Conference Publication (NASA/CP)**, same listing;
       3. NASA **conference papers** (NTRS document type "Conference Paper"), same listing; not a numbered series
          but NASA's own named collection, listed because NASA/TM and NASA/CP are often set in one column.
       For kind (c) an item counts only if the listing gives every author a NASA affiliation (a NASA center or NASA
       Headquarters), as a proxy for "authored by federal employees" (on-site contractors who list a NASA center
       cannot be told apart; this limit is stated with the pick). Items that fail this are skipped in date order.
   (d) 1. Federal Deposit Insurance Corporation, **Quarterly Banking Profile** (the edition published in August
          2025), from FDIC's QBP listing;
       2. U.S. Energy Information Administration, **Monthly Energy Review** (the August 2025 issue);
       3. Board of Governors of the Federal Reserve System, **H.4.1 Factors Affecting Reserve Balances** (the first
          weekly release published in August 2025).
   The next series of a kind is used only if: the host refuses plain curl; the file is 5 MB or larger; the series
   has no issue (for (c): no qualifying item) first published in August 2025; for kind (c), the chosen item is not
   set in two or more columns as seen on the rendered first page of its main text (the first page with running text
   after any cover, notice, report-documentation or front-matter pages); or the series' publisher is already the
   pick of another kind (kinds are resolved in the order a, b, c, d). If every series of a kind fails, the kind is
   left out and reported; it is not replaced by a document picked by hand.
4. **Size and page range**: under 5 MB as served. A document of more than 15 pages keeps pages 1 to k, where k is
   the largest page number of at most 15 at whose end a section or a table ends (the next page starts with a new
   section heading or a new table title), judged from the rendered pages' headings only; cut with pypdf
   (`PdfWriter.add_page` plus the document information dictionary, as in `holdout/` and `holdout2/`). Source URL,
   retrieval date, page range and sha256 of the served and the kept file are recorded below.
5. **No tool influence**: no document is swapped after download, and nothing about how any converter handles a
   document is looked up or tried. Disclosure: `README.md` and `SCORING.md`, read for the format, report earlier
   results and name some areas where each tool lost points (for example a PDF whose letters are spaced by kerning,
   CSV-text tables with thousands separators, MarkItDown headings and pipe tables built from prose). The series
   above were fixed from the kinds alone, before any listing was read, and the generated files below use ordinary
   features listed in the task (headings, lists, merged or multi-line table headers, notes, numbers with
   separators) without being built around any of those findings.

## Generated documents (rule)

Six ordinary business files, one each of DOCX, PPTX, XLSX, CSV, JSON and PDF, written deterministically by
`generate_holdout3.py` (run with `uv run --with python-docx --with openpyxl --with python-pptx --with reportlab
python3 -I holdout3/generate_holdout3.py` from the benchmark folder), with new content (not reused from `holdout/` or
`holdout2/`) and features such documents commonly have: headings, lists, tables with merged or multi-line headers,
notes, numbers with separators. The script writes the files and their answer files; every check is derived from the
script's data and verified against the files read back (DOCX, XLSX, PPTX, CSV, JSON) or against the generator's own
data (PDF, never read back with a text extractor). File names start with `gen-`; public PDFs with `pub-`.

## Amendment 1 (2026-11-24, 14:32 UTC): a fourth series for kind (c) (DEVIATION from the rule above)

Written after the three (c) series above had failed under the rule (see "Picks" below: NASA/TM failed on size,
NASA/CP had no August 2025 issue, and none of the eight August 2025 NASA conference papers had NASA affiliations for
all authors) and **before** the listing of the series below was read and before any (c) document was opened. Under
the rule as first written, kind (c) would be left out. Because a set without a column-set document would lose a
whole kind, one more series is added; the maintainer may drop the resulting file if this amendment is not accepted
(the other nine files do not depend on it).

   (c) 4. NASA journal articles as printed (NTRS document type "Reprint", details "Version of Record" or "Reprint
          (Version printed in journal)"), by publication date in NTRS, ties by earliest publication time and then
          lowest NTRS id; an item counts only if every author has a NASA affiliation in the listing (as above), NTRS's
          copyright determination is `GOV_PUBLIC_USE_PERMITTED` (NASA's own marking of a U.S. Government work), and a
          PDF is offered. The size, host and column conditions of the rule apply unchanged; if this series fails too,
          kind (c) is left out.

## How the rule resolved (2026-11-24; listings read for titles and dates only, plus author affiliations for (c))

**(a) Statistical release.** Series 1, Federal Reserve G.17: the Board's release listing
(`https://www.federalreserve.gov/releases/g17/default.htm`, HTTP 200 to plain curl) shows one release in August
2025, **August 15** (folder `20250815/`). Picked: `g17.pdf` of that release (the supplement `g17_sup.pdf` is a
separate file and was not used).

**(b) Agency guidance.** Series 1, NRC Regulatory Guides: the division listings
(`https://www.nrc.gov/regulations-legislation/regulatory-guides-by-division` and its 33 guide sub-pages, all HTTP 200)
give two final guides with issue date "08/2025": RG 1.87 Revision 3 and RG 1.257 Revision 0. The listing gives only
the month, so the tie went to the lower guide number, RG 1.87 (guide 87 of Division 1, before guide 257, as NRC
numbers and lists them; read as decimals, 1.257 would be lower: this reading is a judgement and is disclosed here). Its
PDF, `https://www.nrc.gov/docs/ML2517/ML25176A084.pdf`, answered **HTTP 403 "Access Denied"** to plain curl (HEAD and
GET), so NRC was dropped (the 404-byte refusal page was deleted). Series 2, FAA Advisory Circulars: the complete
listings (`.../advisory_circulars/index.cfm/go/document.list` for active and inactive circulars, and the CSV exports
`.../document.exportAll/statusID/2` and `/statusID/3` for active and cancelled ones; the all-status page is cut at
1,000 rows, so the per-status lists were used) hold two entries dated August 2025, `8900-747` "FAA-Approved Deicing
Program for Winter 2025-2026" (2025-08-01) and `21-61` "Aircraft Systems Information Security Protection (ASISP)"
(2025-08-04), both status Inactive, and both detail pages say "This document's content is unavailable." No issue
could be obtained, so the series failed (treated as "no issue"; this condition is not spelled out in the rule and is
disclosed). Series 3, DOE directives: `directives.doe.gov` now redirects to `www.energy.gov` (a `.gov` host); the
Active Directives Library (`https://www.energy.gov/management/active-directives-library`, 195 directives embedded in
the page) and the Archived Directives Library (1,593 entries) hold one directive dated August 2025: **DOE P 411.2C,
DOE Scientific Integrity Policy, Effective Date 8/20/2025**. Picked. DEVIATION: the rule says "by approval date", but
the listing gives only an "Effective Date"; the listing's date was used, as the rule also says to take dates from the
publisher's listing. The document itself (seen after download) says "Approved: 07-24-2025".

**(c) Column-set technical report.** Series 1, NASA/TM (NTRS search API
`https://ntrs.nasa.gov/api/citations/search?stiType=TECHNICAL_MEMORANDUM&published.gte=2025-08-01&published.lte=2025-08-31`):
20 memoranda; in tie order (publication timestamp, then report number) the first with NASA affiliations for every
author is NASA/TM-20250001451 (Apollo heat-shield CFD database, one author, Johnson Space Center). Its PDF is
81,888,638 bytes, over 5 MB, so the series failed. (Slip: the HEAD request and the download ran in one command, so
the file was downloaded; only `pdfinfo` metadata was read from it (114 pages), and it was deleted unopened.) Series 2,
NASA/CP: NTRS lists no Conference Publication published in August 2025. Series 3, NASA conference papers: 8 papers
published in August 2025; none has a NASA affiliation for every author (each has a university or contractor
co-author). Amendment 1 series (NASA journal reprints, `stiType=REPRINT`): 112 items; 99 carry no affiliations, and the
only item marked `GOV_PUBLIC_USE_PERMITTED` (NTRS 20250009030) has mostly non-NASA authors, so none qualified. **Kind
(c) is therefore left out; no document was picked by hand.** If a column-set document is wanted, a new series list
should be fixed in advance in a separate selection.

**(d) Financial statement.** Series 1, FDIC Quarterly Banking Profile: FDIC's listing
(`https://www.fdic.gov/quarterly-banking-profile/past-quarterly-banking-profiles`) gives quarters, not dates; the
Second Quarter 2025 page links the press release "FDIC-Insured Institutions Reported Return on Assets of 1.13 Percent
and Net Income of $69.9 Billion in Second Quarter 2025", dated **August 26, 2025** on FDIC's site (the date was read
there because the listing has none). Picked: the "Complete Quarterly Banking Profile - Q2 2025" PDF. Disclosure: the
file served now has Last-Modified 10 Sep 2025 and its page says "Last Updated: September 10, 2025", so it is the
August edition as re-issued on September 10, 2025; there is no other copy on FDIC's site.

Publishers: Federal Reserve Board (a), Department of Energy (b), FDIC (d), all different and none used before.
Hosts that refused plain curl: `www.nrc.gov/docs/` (HTTP 403). No other refusal.

## Public documents (US federal works, public domain under 17 U.S.C. 105)

| file | kind | publisher | URL | why |
|---|---|---|---|---|
| `pub-frb-g17-20250815.pdf` | (a) monthly statistical release | Board of Governors of the Federal Reserve System | https://www.federalreserve.gov/releases/g17/20250815/g17.pdf | The G.17 Industrial Production and Capacity Utilization release published in August 2025 (August 15, 2025; July data) |
| `pub-doe-p4112c.pdf` | (b) agency guidance / directive | U.S. Department of Energy | https://energy.gov/media/360704 (redirects to https://www.energy.gov/documents/scientific-integrity-policy) | The only DOE directive with an August 2025 date in DOE's directives listing (DOE P 411.2C, effective 8/20/2025) |
| `pub-fdic-qbp-2025q2.pdf` | (d) financial statistics made mostly of tables | Federal Deposit Insurance Corporation | https://www.fdic.gov/quarterly-banking-profile/quarterly-banking-profile-second-quarter-2025-pdf.pdf | The Quarterly Banking Profile edition published in August 2025 (Second Quarter 2025, released August 26, 2025) |

### Download record (2026-11-24, plain curl, each file into its own empty folder first)

| file | served file sha256 | pages served | kept | file in this folder (sha256) |
|---|---|---|---|---|
| `pub-frb-g17-20250815.pdf` | `bc1261aaaff0c66f612aacb74727bbae28cfd2f5c2042f15fbfeb6dca97b6f96` (298,529 bytes, Last-Modified 15 Aug 2025) | 19 | pages 1-15 (narrative, list of tables and revision notice, charts on pages 4-6, Tables 1-13; page 15 ends Table 13 and Table 14 starts at the top of page 16); pages 16-19 hold Tables 14-15 and, from the 30 dpi render, explanatory text | `83323c20055745b77b247ef88689daaf5a6787b9cdbb651786f11516ccf42da6` |
| `pub-doe-p4112c.pdf` | `bc645a79f368bf21beb4d376cc4168c1b3a79b5b2e7bd0d1d34e93330ff9df95` (260,786 bytes, Last-Modified 18 May 2026; PDF creation date 9 Mar 2026) | 7 | all | same as served |
| `pub-fdic-qbp-2025q2.pdf` | `9eb27e3208f4bab992433ee8110bc5eb7d7d11c301919fedae54cc1d0918959d` (1,604,367 bytes, Last-Modified 10 Sep 2025) | 49 | pages 1-15 (cover, masthead, summary, blank page, Insured Institution Performance with Charts 1-8, Tables I-A, II-A and III-A; page 15 ends Table III-A and Table IV-A starts at the top of page 16); pages 16-49 (not looked at beyond the top of page 16) start with Table IV-A; the page-3 summary points to the community bank section on printed page 19 and the Deposit Insurance Fund section on printed page 31 | `7acc1038b2958fa2e56b7ef4cfb932815973e8858c8aa74463ff18caf9ab2b6a` |

Each page range is the largest k of at most 15 at which a table ends, judged from 30-60 dpi renders of pages 12-19
(headings and table titles only). Both were cut with pypdf 7.1.1 and the same script as `holdout/` and `holdout2/`
(`uv run --with pypdf python3 -I cut_pages.py <served.pdf> <out.pdf> 1 15`; `PdfWriter.add_page` for each kept page
plus the document information dictionary); two runs gave the same bytes. The cut drops document-level structures, so
the FDIC file, tagged as served, is untagged after the cut; the G.17 file was untagged as served. The DOE file is
tagged and kept as served. The served originals, the low-resolution renders and the reading renders were deleted
after use; only the kept files are in this folder.

## Generated documents

Written by `generate_holdout3.py` (deterministic; new content, not reused from `holdout/` or `holdout2/`), run as
`uv run --with python-docx --with openpyxl --with python-pptx --with reportlab python3 -I holdout3/generate_holdout3.py`
from the benchmark folder. Rule: one ordinary business document per format, using features such documents commonly
have; nothing was designed around any converter's known strengths or weaknesses. Running the script twice gives
byte-identical files and answer files (python-docx 1.2.0, openpyxl 3.1.5, python-pptx 1.0.2, lxml 6.1.3, reportlab
5.1.0, Python 3.14.6). Changes made while writing, because the script's audit rules rejected a check: the workbook was
first named `gen-capital-projects.xlsx` and its first sheet `Projects` (the header cell 'Project' occurred in the
file name, which a converter may write into its output, and the sheet name occurred inside the title); the building
cells 'A'-'D' became 'Building A' / 'Bldg A' (single letters occur in converter-added lines); two ordered anchors that
occur on two sheets were replaced; the PDF's noise maximum for the company name was set to 1 like the other running
texts. The inspection report's corrective-actions table came out split over the two pages (header row repeated) and
was kept.

| file | what it is | sha256 |
|---|---|---|
| `gen-maintenance-sow.docx` | statement of work: Title style, Heading 1/2/3 with typed section numbers, two-level bullets, a numbered list, a second numbered list with lettered sub-items restarting at 1, a table with two header rows (three cells merged down, one across) and two-paragraph body cells, a price table with line breaks inside header cells and a total row merged across four columns, an italic table note, bold/italic runs, a sign-off table with empty cells, page header and footer | `a1b4402aa82adec1d234ce4a40bb27d93c1cfc6f91b878571eae3b02a31731b9` |
| `gen-capex-register.xlsx` | 3 sheets: capital projects register (merged title and note rows, two header rows with a group merged across three columns and six headers merged down, header texts with line breaks, `#,##0`, a negative in parentheses `(12,400)`, `0.0%`, `d-mmm-yyyy` dates, 35 formula cells in the workbook saved with computed values, a total row, frozen panes, a note below the table); monthly spend with empty months and formula totals; vendors with text phone numbers, `mm/dd/yyyy` dates, booleans, one-decimal ratings, autofilter | `b5004f12f96ccc51695a0d6cc89cf8bed4d579dff56709299954e9b6342256a9` |
| `gen-facilities-update.pptx` | 7-slide committee deck: title slide, auto-numbered agenda, native table with two header rows (merged down and across), Two Content slide with two-level bullets, Title Only slide with two free text boxes, Section Header slide, two-level bullets, speaker notes on 3 slides | `12f0d21e662c5997cc5c5da56dde4112f3e539e3a569d1109157f91902dd9099` |
| `gen-work-orders.csv` | maintenance work-order export: comma delimiter, minimal quoting, CRLF record ends with bare LF inside 6 quoted multi-line fields, UTF-8 without BOM, commas, a semicolon and doubled quotes in fields, amounts with thousands separators, US date-times, empty fields, non-ASCII names | `879f08add0d8a4ab6cdd501a8e146ec408f376b966548f059dc76cd400621d8f` |
| `gen-asset-register.json` | equipment register export: pretty-printed (2-space indent), top-level object with a metadata object and an array of 8 assets, nested objects and arrays, varying keys, nulls, booleans, empty arrays, an escaped quote, non-ASCII text | `45c4fd179405c8930b447d83ab3ccd371199eb6b8551653e8fcdb2daa5445fbf` |
| `gen-inspection-report.pdf` | ReportLab inspection report, 2 pages: title and headings by font size, key-value table without a header row, a table with two header rows (spans across and down) and a total row, a numbered list, a table with wrapped cells continuing onto page 2 with its header repeated, a bulleted list, an italic note, running header and footer ('Page N of 2') | `757749a09a02a98ea8bf358fedb30ec7713c31ce4e0f9bb9b84bd37b43e44768` |

`generate_holdout3.py` itself: sha256 `a47f32e367af2d70d6d81639fb0e80150d5277032c3bbf83a4e223461ecb2080` at freeze.

## Checks per file

| file | must_contain | ordered | headings | tables (non-empty cells) | noise | absent |
|---|---|---|---|---|---|---|
| `gen-maintenance-sow.docx` | 33 | 8 | 9 | 3 (76) | 0 | 0 |
| `gen-capex-register.xlsx` | 16 | 6 | 0 | 3 (209) | 0 | 0 |
| `gen-facilities-update.pptx` | 19 | 7 | 7 | 1 (31) | 0 | 0 |
| `gen-work-orders.csv` | 16 | 5 | 0 | 1 (365) | 0 | 0 |
| `gen-asset-register.json` | 15 | 5 | 0 | 0 | 0 | 0 |
| `gen-inspection-report.pdf` | 18 | 7 | 6 | 3 (78) | 3 | 0 |
| `pub-frb-g17-20250815.pdf` | 28 | 8 | 6 | 4 (469; all complete) | 0 | 2 |
| `pub-doe-p4112c.pdf` | 38 | 8 | 12 | 0 (the directive has no tables) | 2 | 0 |
| `pub-fdic-qbp-2025q2.pdf` | 29 | 8 | 18 | 4 (546; Table II-A and both Table III-A pages are partial) | 1 | 1 |

## Answers and audit

- Public PDFs: answers typed from the rendered pages (pdftoppm, 100 dpi full pages, 200-320 dpi crops of every
  transcribed table and note, read as images). Every transcribed table was checked with the arithmetic the document
  implies, by a throwaway script (not committed) that reads the answer files and lists every mismatch: G.17 Table 3
  autos + trucks = total, light + medium and heavy = trucks, autos + light trucks = the memo row; G.17 Table 9 the
  component identities (exact in the 2017 base-year column, within 1 percent in the chained columns); FDIC Table I-A
  commercial banks + savings institutions = institutions reporting; FDIC Table II-A interest income - interest
  expense = net interest income, the income statement adds up to total net income (within 1), bank net income - cash
  dividends = retained earnings, and every %Change cell matches its two columns; FDIC Table III-A (both pages)
  commercial + savings = total and the groups sum to All Insured Institutions in every row. The only mismatches were
  eight sums in the bank net income rows (in millions) of Table III-A that are off by exactly 1; those cells were
  re-read at 320 dpi and are as printed (the publication's own rounding). G.17 Tables 6 and 10, which arithmetic
  cannot pin, were re-read digit by digit against the 220 dpi crops. A second pass re-read every phrase, anchor,
  heading and absent entry of the three files against the images; it corrected two counts in the DOE and FDIC notes
  and changed no check string.
- Generated files: `generate_holdout3.py` reads each DOCX/XLSX/PPTX/CSV/JSON file back (heading styles, list
  numbering and levels, merged cells, line breaks in cells, cached formula values, merged pptx table cells, text boxes,
  auto-numbered paragraphs and speaker notes) and verifies every check against it, plus the audit rules of `holdout/`
  and `holdout2/` (no file name or converter-added text in a check, prose phrases of 6+ words that occur once,
  data-file items that are whole fields not inside another field, ordered anchors unique, in reading order and never
  from speaker notes). The generated PDF is not read back with any text extractor: its checks come from the generator's
  data in reading order, its 2 pages were rendered and looked at, and `pdffonts` was used once to confirm its font
  names (Helvetica, Helvetica-Bold, Helvetica-Oblique; base-14, not embedded).
- `score.mjs` was not run. Its `validateGroundTruth` rules (errors and warnings) are re-implemented in
  `generate_holdout3.py` (`validate_ground_truth`); all nine answer files pass them with no error and no warning, and
  the sha256 in every answer file matches the file in this folder. The public answer files were also checked to have
  no non-ASCII character, quotation mark, apostrophe or in-word hyphen in any must_contain phrase or ordered anchor,
  and no dash or quote in any heading.

## Known limits (also in each file's notes)

- The PDF text layer was never read, so invisible text-layer content is not checked, and characters whose code point
  cannot be seen are avoided in phrases, anchors and headings. Where table cells must contain them, the assumption is
  stated and applies to every tool alike: ASCII hyphen-minus for negative numbers (G.17 Table 10, FDIC Tables I-A,
  II-A and III-A) and for hyphens in cells ('24Q2-25Q2'); superscript revision marks written as the modifier letters
  ʳ and ᵖ attached to the word and footnote marks as ¹ (NFKC makes them 'r', 'p', '1'); the FDIC ellipsis written
  '...' (NFKC equivalent).
- Cells whose text could not be pinned down are left empty (not scored): the G.17 Table 10 header 'July ’24 to July
  ’25'. Header cells that wrap or are hyphenated over lines are written joined ('International Banks').
- The DOE directive has no tables, so that file has no table check; its headings are the underlined numbered section
  titles of a DOE directive.
- The QBP side headings are long and printed over two to four lines in a narrow column; each is one expected heading.

## Disclosures

- No converter, text extractor or OCR was run on any file in this folder, and nothing about how a converter handles
  any of these documents was looked up. No git command was run.
- Read before writing the rule (format and method only): `README.md`, `SCORING.md`, `score.mjs`, both earlier
  `SELECTION.md` files, `holdout2/generate_holdout2.py` and three `holdout2` answer files. `README.md` and `SCORING.md`
  report earlier results, including areas where each tool lost points; see rule 5.
- Deviations from the rule as first written: (1) Amendment 1 added a fourth series for kind (c) after the three listed
  ones had failed; it failed too, so it changed no pick. (2) The DOE pick used the listing's "Effective Date" where the
  rule says "approval date" (the document's approval date is July 24, 2025). (3) The FAA series was treated as failed
  because its only two August 2025 entries have no obtainable document (not one of the listed fallback conditions).
  (4) The NRC tie was broken by guide number within the division (87 < 257). (5) The FDIC publication date was read
  from FDIC's press release page because the QBP listing gives quarters, not dates; the file served is the September
  10, 2025 re-issue of that edition. (6) Kind (c) is left out, so the set has three public PDFs instead of four.
- Slips: an oversized NASA PDF (81.9 MB) was downloaded because its size check and download ran in one command (only
  its page count was read; deleted); during the determinism check one shell command briefly wrote a hash list to
  `/tmp/h3-run1.txt`, outside this folder, and deleted it at once. Neither involved reading document content.
