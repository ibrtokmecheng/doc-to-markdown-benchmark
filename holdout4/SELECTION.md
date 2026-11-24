# Held-out test set 4: selection record

This folder is the fourth held-out test set (the fifth frozen set, after `corpus/`, `holdout/`, `holdout2/` and
`holdout3/`) for the doc-to-Markdown benchmark (PackForAI vs Microsoft MarkItDown), built with the method of
`holdout3/`. Same layout: documents here, answers in `ground-truth/<file>.json`, scored with

```
node score.mjs holdout4 <outDir>
```

Status: FROZEN (2026-11-24, 17:13 UTC). The selection rule below was written at 16:38 UTC, before any document, listing
or catalogue page was downloaded or opened; Amendment 1 was added at 16:44 UTC (see there); picks, download record,
answers and audit follow. **This set has 9 files, not 10: kind (c) (a column-set technical report) is left out again,
because every series listed for it, including the two added by Amendment 1, failed under the rule (see "How the rule
resolved").**

## Blind protocol

The documents are chosen and the answers written **before** any converter touches them:

- PackForAI, MarkItDown and every other document converter or text extractor (pdftotext, pdfminer, pdfplumber,
  pypdf text extraction, OCR) are **not** run on these files. pypdf is used only to keep a page range and to count
  pages; `pdfinfo` only for page count and page size; `pdftoppm` only to render pages to images for reading;
  `pdffonts` only once, on the generated PDF, to confirm its font names.
- The conversion engine code (`aireadydoc/services/`, `packforai-motor*`), earlier results (`results/`), the folders
  `corpus/`, `holdout/` and `holdout2/`, `README.md`, scratchpad folders and earlier development outputs are not
  opened. No git command is run. The only files read outside this folder are `SCORING.md`, `score.mjs` (read, not
  run), `holdout3/SELECTION.md`, `holdout3/generate_holdout3.py` and two answer files of `holdout3/ground-truth/`
  (`pub-doe-p4112c.pdf.json`, `pub-fdic-qbp-2025q2.pdf.json`) as format examples.
- Public PDFs: every check is typed from the rendered pages (read as images), never copied from a text layer.
- Generated files: every check is derived from the data in `generate_holdout4.py`, which also writes the files.
- `score.mjs` is not run on this folder by the reviewer; its validation rules (`validateGroundTruth`) are applied by
  reading them and re-implementing them in the generator's self-check and in a throwaway check of the public answer
  files (not committed).
- Temporary files are kept in `holdout4/.work/` only and deleted at the end; nothing is written to `/tmp`.

## Selection rule for the public PDFs (fixed before any document was downloaded or opened)

1. **Kinds**: one document of each of these kinds, each from a publisher not used before (not the Office of the
   Federal Register/GPO, the Senate or the Census Bureau of `corpus/`; not BEA, CDC (any CDC series), IRS or NIST of
   `holdout/`; not the Department of Labor, FDA, USGS or Treasury/Bureau of the Fiscal Service of `holdout2/`; not
   the Federal Reserve Board, the Department of Energy (including its offices, administrations and laboratories) or
   FDIC of `holdout3/`), and a different publisher for each kind. As in the earlier sets (Census Bureau and BEA, CDC
   and FDA, IRS and the Fiscal Service were separate publishers), the publisher is the issuing agency (bureau or
   operating administration), not the cabinet department:
   (a) a weekly or monthly statistical release with data tables,
   (b) an agency guidance document, directive or regulatory guide with numbered headings and lists,
   (c) a technical or scientific report set in two or more columns, authored by federal employees,
   (d) a financial or budget statement or report made mostly of tables.
2. **Works and hosts**: U.S. federal government works only (public domain under 17 U.S.C. 105). Official `.gov` or
   `.mil` hosts only, fetched with plain `curl` (default user agent, no browser emulation, no cookies; redirects
   followed only while they stay on `.gov`/`.mil` hosts). A host that refuses plain curl (HTTP 403 or another
   refusal, or a bot-check page instead of the content) is dropped, not worked around. Already known to refuse and
   not used: `usda.gov`, `ed.gov`, `hud.gov`, `opm.gov`, `transportation.gov`, `bls.gov`, `gao.gov`, `ssa.gov`,
   `cbo.gov`, `osha.gov`, `ftc.gov`, `www.nrc.gov/docs/`.
3. **Fixed issue, not a hand-picked one**: the issue or document **first published in September 2025** in a named
   series (September 2025 is fixed here, before any listing is read; `holdout/` used the first issue of 2025,
   `holdout2/` July 2025, `holdout3/` August 2025), taken from the publisher's own listing, reading titles and dates
   only (for kind (c) also author names and affiliations, see below). The publication date is the date the listing
   gives; where the listing gives only a reference period and no publication date, the date of the publisher's own
   release announcement (news release page) is used; where there is none, the `Last-Modified` header of the issue's
   PDF (HEAD request only). Ties go to the earliest publication time, then to the lowest series or report number
   (numbers made of several parts, such as `150/5300-13`, compared part by part as integers). An item counts as an
   issue only if the publisher offers it as a PDF; an item without an obtainable PDF is skipped in date order.
   The series for each kind, in order of preference:
   (a) 1. Federal Housing Finance Agency (FHFA), **FHFA House Price Index (HPI) monthly report**: the HPI release
          published in September 2025 (date from FHFA's news-release listing), the PDF report of that release;
       2. U.S. Railroad Retirement Board (RRB), **Monthly Benefit Statistics**;
       3. Federal Highway Administration (FHWA), **Traffic Volume Trends** (monthly).
   (b) 1. Federal Aviation Administration (FAA), **Advisory Circulars**: final circulars and changes to them, by the
          date in FAA's advisory circular listing; cancellation notices (a document that only cancels another) are
          excluded;
       2. National Aeronautics and Space Administration (NASA), **NASA Policy Directives and NASA Procedural
          Requirements** (NPD and NPR, new, revised or changed), by the effective date in the NASA Online Directives
          Information System (NODIS) listing;
       3. U.S. Department of Defense, **DoD issuances** (DoD Directives, Instructions and Manuals and changes to
          them), by the date in the DoD Issuances listing at `esd.whs.mil`.
   (c) 1. NOAA National Marine Fisheries Service (NMFS), Scientific Publications Office, **Fishery Bulletin**
          articles, by the online publication date in the journal's listing or article page;
       2. National Highway Traffic Safety Administration (NHTSA), National Center for Statistics and Analysis,
          **Traffic Safety Facts Research Notes** (the DOT HS publications that NHTSA's CrashStats listing types as
          Research Notes), by the publication date in that listing;
       3. NOAA NMFS, Scientific Publications Office, **Marine Fisheries Review** articles, by the online publication
          date in the journal's listing or article page.
       For kind (c) an item counts only if every author is a federal employee by affiliation: for NOAA, every author
       has a NOAA affiliation (an NMFS science center or regional office, or another NOAA line office or
       laboratory); for NHTSA, no author other than NHTSA (its National Center for Statistics and Analysis or named
       NHTSA staff) is credited and no contractor is named as author. Affiliations are taken from the listing or
       the article page; where these give none, from the item's rendered first page, read as an image for the
       author lines and the page layout only, before any check is written. Items that fail are skipped in date
       order. Why these series: the column condition made kind (c) fail in `holdout3/` (the NASA series were set in
       one column, too large or had non-NASA co-authors). Fishery Bulletin and Marine Fisheries Review are NOAA's
       own scientific journals, typeset in two columns as their house style, with articles of typically 5-25
       pages and a few MB at most, and many articles are written by NMFS science center staff only. NHTSA's
       Traffic Safety Facts Research Notes are short (typically 2-15 pages, well under 5 MB), written by NHTSA's
       own statistics office, and, as far as the reviewer remembers the Traffic Safety Facts layout, printed in
       two columns; this was not checked before the rule was fixed, and the column condition below decides.
   (d) 1. National Credit Union Administration (NCUA), **Quarterly Credit Union Data Summary** (the edition first
          published in September 2025);
       2. Commodity Futures Trading Commission (CFTC), **Financial Data for Futures Commission Merchants** (monthly);
       3. Federal Housing Finance Agency (FHFA), **Foreclosure Prevention Report** (also published as "Foreclosure
          Prevention and Refinance Report").
   The next series of a kind is used only if: the host refuses plain curl; the file is 5 MB or larger; the series
   has no issue (for (c): no qualifying item) first published in September 2025; for kind (c), the chosen item is
   not set in two or more columns as seen on the rendered first page of its main text (the first page with running
   text after any cover, notice, report-documentation or front-matter pages); or the series' publisher is already
   the pick of another kind (kinds are resolved in the order a, b, c, d). If every series of a kind fails, the kind
   is left out and reported; it is not replaced by a document picked by hand.
4. **Size and page range**: under 5 MB as served, checked with a HEAD request (`Content-Length`) or a one-byte
   ranged request before the full download. A document of more than 15 pages keeps pages 1 to k, where k is the
   largest page number of at most 15 at whose end a section or a table ends (the next page starts with a new section
   heading or a new table title), judged from the rendered pages' headings only; cut with pypdf
   (`PdfWriter.add_page` plus the document information dictionary, as in the earlier sets). Source URL, retrieval
   date, page range and sha256 of the served and the kept file are recorded below.
5. **No tool influence**: no document is swapped after download (other than by the conditions written above), and
   nothing about how any converter handles a document is looked up or tried. Disclosure: `SCORING.md`, read for the
   format, reports earlier results and names areas where each tool lost points (line-end hyphens in multi-column
   text, CSV-text tables, thousands separators in table cells, pipe tables built from prose, padding columns);
   `holdout3/SELECTION.md` reports which series failed there. The series above were fixed from the kinds alone,
   before any listing was read, and the generated files use ordinary features listed in the task (headings, lists,
   merged or multi-line table headers, notes, numbers with separators) without being built around any of those
   findings.

## Amendment 1 (2026-11-24, 16:44 UTC): two more series for kind (c) (DEVIATION from the rule above)

Written after the three (c) series above had failed under the rule (Fishery Bulletin: no article published online in
September 2025; NHTSA Research Notes: no research note dated September 2025 in the CrashStats listing; Marine
Fisheries Review: no article since cover date 2024; see "How the rule resolved") and **before** the listings of the
series below were read and before any (c) document was opened. Under the rule as first written, kind (c) would be
left out for the second set in a row; because a set without a column-set document loses a whole kind, two more
series are added, as `holdout3/` did in its Amendment 1. The maintainer may drop the resulting file if this amendment
is not accepted (the other files do not depend on it). Both series are on the CrashStats host, which answered plain
curl, and were chosen because they publish many items a year (the type list read for the Research Notes lookup gives
only counts: 499 fact sheets, 174 Crash•Stats), not from any item of them.

   (c) 4. NHTSA, National Center for Statistics and Analysis, **Traffic Safety Fact Sheets** (the publications that
          the CrashStats listing types as "Traffic Safety Fact Sheets"), by the date in that listing;
       5. NHTSA, National Center for Statistics and Analysis, **Crash•Stats** briefs (the publications the CrashStats
          listing types as "Crash*Stats"), by the date in that listing.
   The author, size, host, tie and column conditions of the rule apply unchanged (the date used is the listing's
   `createdOn` field, the only date it gives, as for the Research Notes); if both series fail too, kind (c) is left
   out.

## Generated documents (rule)

Six ordinary business files, one each of DOCX, PPTX, XLSX, CSV, JSON and PDF, written deterministically by
`generate_holdout4.py` (run with `uv run --with python-docx --with openpyxl --with python-pptx --with reportlab
python3 -I holdout4/generate_holdout4.py` from the benchmark folder), with new content (not reused from `holdout/`,
`holdout2/` or `holdout3/`) and features such documents commonly have: headings, lists, tables with merged or
multi-line headers, notes, numbers with separators. The script writes the files and their answer files; every check
is derived from the script's data and verified against the files read back (DOCX, XLSX, PPTX, CSV, JSON) or against
the generator's own data (PDF, never read back with a text extractor). File names start with `gen-`; public PDFs
with `pub-`.

## How the rule resolved (2026-11-24; listings read for titles and dates only, plus author lines for (c))

Every host contacted answered plain curl with HTTP 200 (`www.fhfa.gov`, `www.faa.gov`, `spo.nmfs.noaa.gov`,
`crashstats.nhtsa.dot.gov`, `ncua.gov`); no host refused. `crashstats.nhtsa.dot.gov` answers HEAD with HTTP 405 (method
not allowed) but GET with 200, so it was not treated as a refusal.

**(a) Statistical release.** Series 1, FHFA HPI monthly report: FHFA's news-release listing
(`https://www.fhfa.gov/news/news-release?items_per_page=50&page=0`, dates in the listing) has one HPI release dated in
September 2025: **September 30, 2025**, "FHFA House Price Index® Down 0.1 Percent in July; Up 2.3 Percent from Last
Year" (the only other September 2025 item is not an HPI release). The release page links one PDF, "FHFA HPI® Monthly -
September 2025" (`https://www.fhfa.gov/document/d/hpi/fhfa-hpi-monthly-september-2025`; HEAD: `application/pdf`,
1,139,256 bytes). Picked. Disclosure: the file served has Last-Modified April 10, 2026 and a PDF creation date of
October 9, 2025, so it is a later upload of that release's report (its cover says "Released on September 30, 2025");
there is no other copy on FHFA's site.

**(b) Agency guidance.** Series 1, FAA Advisory Circulars: the CSV exports of FAA's listing
(`https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.exportAll/statusID/2` for active and
`/statusID/3` for cancelled circulars) list for September 2025: 2025-09-08 `20-167B`, `33-12` and `33.15-1A` (active)
and `33.15-1` (in the cancelled list, dated 2025-09-08, presumably the day `33.15-1A` replaced it; it is an old circular,
not one first published that month, and not a cancellation notice), 2025-09-11 `120-53C`, 2025-09-22 `43-9D`,
2025-09-25 `21-32C`, 2025-09-29 `20-135A`. The listing gives dates without times, so the 2025-09-08 tie went to the
lowest number compared part by part: **AC 20-167B**, "Airworthiness Approval of Enhanced Vision System, Enhanced Flight
Vision System, and Combined Vision System Equipment" (20 before 33, so `33.15-1` could not have changed the pick). Its
detail page (`.../document.information/documentID/1044323`, "Date issued 2025-09-08") links
`https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_20-167B.pdf` (HEAD: `application/pdf`, 3,235,870
bytes). Picked.

**(c) Column-set technical report.** Series 1, Fishery Bulletin: the journal listing (`https://spo.nmfs.noaa.gov/fb.htm`;
`fisherybulletin.nmfs.noaa.gov` redirects there) and the issue pages of 123(2), 123(3), 123(4) and 124(1-2) with
their article pages ("Published online" dates): 123(4) articles were published online on 27 August, 14 November, 26
November, 12 December and 29 December 2025, and 124(1-2) from 24 February 2026; **no article was published online in
September 2025**, so the series has no issue. Series 2, NHTSA Research Notes: the CrashStats listing
(`https://crashstats.nhtsa.dot.gov/api/Public/getByType/9`, the JSON behind the site; its only date is `createdOn`)
dates its 2025 research notes 15 January, 10 March, 26 March, 12 May, 9 December and 10 December 2025; **none in
September 2025**. Series 3, Marine Fisheries Review: the latest issue, MFR 86(1-4), holds one article with cover date
2024 and no online date; **none in September 2025**. Amendment 1 (written after these three failed, before the
listings below were read): series 4, NHTSA Traffic Safety Fact Sheets (`.../getByType/11`): the only item between 15
August and 15 October 2025 is dated 14 October 2025 (DOT HS 813 762); **none in September 2025**. Series 5, NHTSA
Crash•Stats (`.../getByType/3`): one item dated in September 2025, DOT HS 813 756, "Early Estimate of Motor Vehicle
Traffic Fatalities for the First Half (January–June) of 2025" (`createdOn` 2025-09-11). A one-byte ranged GET gave its
size (722,948 bytes); it was downloaded (sha256 `f379857436ccb5bdd676bf51dd7dd5c11f4ef24d89879ddf5ee5e413fe0e670e`, 6
pages) and its first page rendered at 70 dpi: **it is set in one column**, so the series failed on the column condition
(its authorship was not examined further). The file and its render were deleted. **Kind (c) is therefore left out; no
document was picked by hand.** Lesson for a next attempt: these short-note series are column-set but publish too
rarely for a single fixed month; a rule for (c) would need a wider fixed window (fixed before any listing is read).

**(d) Financial statement.** Series 1, NCUA Quarterly Credit Union Data Summary: NCUA's listing
(`https://ncua.gov/analysis/credit-union-corporate-call-report-data/quarterly-data-summary-reports`) gives quarters,
not dates, so the date came from NCUA's own release announcement, as the rule says: the press-release listing
(`https://ncua.gov/newsroom/press-releases?page=1`) dates "NCUA Releases Second Quarter 2025 Credit Union System
Performance Data" **September 11, 2025**, and that release links "Second Quarter 2025 NCUA Quarterly Data Summary
Report" (`https://ncua.gov/files/publications/analysis/quarterly-data-summary-2025-Q2.pdf`; HEAD: `application/pdf`,
no Content-Length, Last-Modified September 18, 2025; size 570,488 bytes, see the slip below). No other edition was
announced in September 2025. Picked. Disclosure: the PDF's modification date (September 18, 2025) is a week after the
announcement, so the file served may be a corrected re-issue; there is no other copy.

Publishers: FHFA (a), FAA (b), NCUA (d), all different and none used before. Hosts that refused plain curl: none.

## Public documents (US federal works, public domain under 17 U.S.C. 105)

| file | kind | publisher | URL | why |
|---|---|---|---|---|
| `pub-fhfa-hpi-202509.pdf` | (a) monthly statistical release | Federal Housing Finance Agency | https://www.fhfa.gov/document/d/hpi/fhfa-hpi-monthly-september-2025 | The FHFA HPI monthly report of the HPI release published in September 2025 (September 30, 2025; July 2025 data) |
| `pub-faa-ac-20-167b.pdf` | (b) agency guidance | Federal Aviation Administration | https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_20-167B.pdf | The advisory circular first issued in September 2025 with the earliest date and lowest number (AC 20-167B, 09/08/2025) |
| `pub-ncua-qcuds-2025q2.pdf` | (d) financial statistics made mostly of tables | National Credit Union Administration | https://ncua.gov/files/publications/analysis/quarterly-data-summary-2025-Q2.pdf | The Quarterly Credit Union Data Summary edition published in September 2025 (2025 Q2, announced September 11, 2025) |

### Download record (2026-11-24, plain curl, each file into its own empty folder under `.work/` first)

| file | served file sha256 | pages served | kept | file in this folder (sha256) |
|---|---|---|---|---|
| `pub-fhfa-hpi-202509.pdf` | `4406c5c0b689138eaaba812eaa1b0d1c2b5b343f0c18b3dd0888f1294cbdbb2c` (1,139,256 bytes, Last-Modified 10 Apr 2026, tagged) | 23 | pages 1-13 (cover, contents, news release, divider, the two data tables, divider, two chart pages, divider, overview, release calendars 2025 and 2026, the 'Appendix' divider); page 14 starts the table 'Monthly House Price Index for U.S. from January 1991 - Present', which pages 15-16 continue without a new title, so 13 is the largest k at whose end a section ends | `5295554ca1ca7da36598aa16cb711d72e04e118714b94a81f6e2c714ce92492c` |
| `pub-faa-ac-20-167b.pdf` | `ad8743daeb2fa95567714da8612111cd5e7fdd09cec3f88b8b1f23ee7fda6174` (3,235,870 bytes, Last-Modified 3 Oct 2025, untagged) | 84 | pages 1-14 (cover page with subject block and signature, contents, Chapters 1-3); page 15 starts 'CHAPTER 4. SYSTEM CRITERIA'; page 16 continues Chapter 4 with paragraph 4.1.3.2 (no new heading), so 14 is the largest k | `3c37b6cad5830b38c54b49c7b286edbed744cfc3dec56f05b3b999ff800b9899` |
| `pub-ncua-qcuds-2025q2.pdf` | `64d67261a712394f1d9ccfcffa55813c95912fdfb69c383e16ee5d1d4a7ec8fd` (570,488 bytes, Last-Modified 18 Sep 2025, tagged) | 20 | pages 1-14 (cover, narrative, notes, and the first four table pages); page 14 ends the 'Income and Expense (... Percent of Average Assets)' section and page 15 starts the 'Balance Sheet' section; page 16 repeats the table title and the 'Balance Sheet' band and continues that section under an 'Addenda' sub-heading, so page 15 was judged not to end a section (judgement disclosed; reading 'Addenda' as a new section would have given k = 15) | `05192e89dc5c8fbc4fc256d6ca65ffa6a763a1a1d4a8a1ea192625217f295337` |

Each page range was judged from 30-40 dpi renders of the pages around page 15 (headings and table titles only). All
three were cut with pypdf 7.1.1 (`uv run --with pypdf python3 -I cut_pages.py <served.pdf> <out.pdf> 1 k`, a throwaway
script: `PdfWriter.add_page` for each kept page plus the document information dictionary, as in the earlier sets); two
runs gave the same bytes for each file. The cut drops document-level structures: the FHFA and NCUA files, tagged as
served, are untagged after the cut; the FAA file loses its AcroForm, so poppler prints 'SubType on non-terminal field'
for the kept signature widget on page 1 (the page renders as served). The served originals, the cut copies and all
renders were deleted after use; only the kept files are in this folder.

## Generated documents

Written by `generate_holdout4.py` (deterministic; new content, not reused from `holdout/`, `holdout2/` or `holdout3/`),
run as `uv run --with python-docx --with openpyxl --with python-pptx --with reportlab python3 -I
holdout4/generate_holdout4.py` from the benchmark folder. Rule: one ordinary business document per format, using
features such documents commonly have; nothing was designed around any converter's known strengths or weaknesses. The
script's helpers (normalization, validation, read-back verification, OOXML pinning) are copied from
`holdout3/generate_holdout3.py`; the documents, data and checks are new. Running the script twice gives byte-identical
files and answer files (python-docx 1.2.0, openpyxl 3.1.5, python-pptx 1.0.2, lxml 6.1.3, reportlab 5.1.1, Python
3.14.6). The script also checks the three public answer files against the same validation rules and their sha256
against the files in this folder. Changes made while writing, because the script's audit rules rejected a check: the
workbook's second sheet was first named `Headcount`, a word that also occurs inside its source note, so it became
`Staffing`; the CSV column `customer` occurs in the file name `gen-customer-invoices.csv` (which a converter may write
into its output), so it became `customer_name`. The PDF's actions table came out split over the two pages (header row
repeated), as intended, and was kept.

| file | what it is | sha256 |
|---|---|---|
| `gen-travel-policy.docx` | travel and expense policy: Title style, Heading 1/2/3 with typed section numbers, two-level bullets, a numbered list, a second numbered list with lettered sub-items restarting at 1, a limits table with two header rows (four cells merged down, one across three columns), two-paragraph body cells and a body cell merged across three columns, a mileage table with line breaks inside header cells and a total row whose label is merged across three columns, an italic table note, bold/italic runs, a sign-off table with empty cells and a non-ASCII name, page header and footer | `65947ba1f87be8a4c42faf3c824750fa11f75f2881f329d0feebeea2d318c84e` |
| `gen-budget-variance.xlsx` | 3 sheets: budget vs actual (merged title and note rows, two header rows with a group merged across four columns and six headers merged down, header texts with line breaks, `#,##0`, negatives in parentheses, negative `0.0%` values, 35 formula cells in the workbook saved with computed values, a total row, frozen panes, a note below the table); monthly staffing with an unreported month, `d-mmm-yyyy` dates and formula totals; cost centers with text codes keeping leading zeros, booleans, `mm/dd/yyyy` dates, percentages, autofilter | `2340b735ec2a7f7bbc72338290818e8e38eb0b071074e1dbe1fa8fe581d42a70` |
| `gen-sales-review.pptx` | 7-slide sales review: title slide, auto-numbered agenda, native table with two header rows (merged down and across) and signed percentages, Two Content slide with two-level bullets, Title Only slide with two free text boxes, Section Header slide, two-level bullets, speaker notes on 3 slides | `a3093bf21fa4428a62a2a6a5855431f3bdd1770071be05cd5defce3c5ac53ee2` |
| `gen-customer-invoices.csv` | invoice export as Excel's 'CSV UTF-8' writes it: UTF-8 with a byte order mark, comma delimiter, minimal quoting, CRLF record ends with bare LF inside 6 quoted multi-line fields, commas, semicolons and doubled quotes in fields, amounts with thousands separators, ISO dates, zero tax amounts, empty fields, non-ASCII names | `7ea0920a0732e7cdba9c53e7cafc68039a4621a749364d278a280c3929cee1c0` |
| `gen-product-catalog.json` | product catalog export: pretty-printed (2-space indent), top-level object with a metadata object and an array of 8 products, nested objects, arrays of objects and of strings, keys that differ between records, nulls, booleans, empty arrays, escaped quotes, non-ASCII text | `a8b08e29f522d8c10b2a5ae3f572a1be9100d859906f648039dfde486a148caf` |
| `gen-ops-report.pdf` | ReportLab monthly operations report, 2 pages: title and headings by font size, key-value table without a header row, a table with two header rows (spans across and down) and a total row, a numbered list, an actions table with wrapped cells continuing onto page 2 with its header repeated, a bulleted list, an italic note, running header and footer ('Page N of 2') | `e7d5f323217d2f22ff75bf99294490dbaf04597200208f3bb42237c9efe7de79` |

`generate_holdout4.py` itself: sha256 `fe1ec59990c43eadf2cde0acb743474a295d8dd34c9608dfb790ae1252b07f02` at freeze.

## Checks per file

| file | must_contain | ordered | headings | tables (non-empty cells) | noise | absent |
|---|---|---|---|---|---|---|
| `gen-travel-policy.docx` | 28 | 8 | 9 | 3 (71) | 0 | 0 |
| `gen-budget-variance.xlsx` | 16 | 6 | 0 | 3 (180) | 0 | 0 |
| `gen-sales-review.pptx` | 18 | 7 | 7 | 1 (31) | 0 | 0 |
| `gen-customer-invoices.csv` | 18 | 5 | 0 | 1 (361) | 0 | 0 |
| `gen-product-catalog.json` | 15 | 5 | 0 | 0 | 0 | 0 |
| `gen-ops-report.pdf` | 18 | 7 | 6 | 3 (58) | 3 | 0 |
| `pub-fhfa-hpi-202509.pdf` | 34 | 8 | 9 | 5 (439; all complete) | 0 | 0 |
| `pub-faa-ac-20-167b.pdf` | 42 | 8 | 20 | 0 (the kept pages have no table) | 2 | 0 |
| `pub-ncua-qcuds-2025q2.pdf` | 44 | 8 | 12 | 5 (880; the page-6 part of the changes table and the page-11 and page-13 data tables are partial) | 0 | 0 |

## Answers and audit

- Public PDFs: answers typed from the rendered pages (pdftoppm, 100 dpi full pages, 140-300 dpi crops of every
  transcribed table and of the text the phrases come from, read as images). Every transcribed table was checked with
  the arithmetic the document implies, by a throwaway script (not committed) that reads the answer files: FHFA every
  1-month change of the price-change table recomputed from the index table (six month pairs, all ten columns) and the
  12-month change (July 2025 vs July 2024) within 0.1 point, and every date of both release calendars a Tuesday; NCUA
  page 11 federal + state-chartered = federally insured credit unions in all 14 quarter columns, every four-quarter
  change = 2025.2 minus 2024.2 and every percent change = that change over 2024.2 (to the printed rounding), and the
  four growth rows equal to the year-on-year change of their total rows wherever both quarters are printed; page 12
  and page 13 change columns likewise; page 13 gross income = total interest income + total non-interest income and
  total non-interest income = fee income + other income + gains (within 0.2). The only remaining mismatch is the
  percent change of page 13's gains row (-46.7 printed, -45.7 from the rounded 1.9 and 3.5; -46.6 from the printed
  change -1.63), the publication's own rounding of small values; the row was re-read at 300 dpi and is as printed.
  The three data tables of NCUA pages 11-13 were then re-read digit by digit against 300 dpi crops, and a second pass
  re-read the phrases, anchors and headings against 110-150 dpi renders: all of the NCUA narrative pages (2-5 and
  7-10), every FAA page a phrase comes from (all 42 FAA phrases and the two body occurrences behind its noise maximum),
  and the two FHFA text pages (3 and 10, which hold 31 of its 34 phrases; the FHFA phrases of pages 1, 2 and 5 and its
  calendar cells had been typed from 100-200 dpi renders and were not read a second time). No check string changed in
  that pass; one FAA note was extended.
- Generated files: `generate_holdout4.py` reads each DOCX/XLSX/PPTX/CSV/JSON file back (heading styles, list
  numbering and levels, merged cells, line breaks in cells, cached formula values, text-stored codes, merged pptx table
  cells, text boxes, auto-numbered paragraphs and speaker notes, the CSV byte order mark and record ends) and verifies
  every check against it, plus the audit rules of the earlier sets (no file name or converter-added text in a check,
  prose phrases of 6+ words that occur once, data-file items that are whole fields not inside another field, ordered
  anchors unique, in reading order and never from speaker notes). The generated PDF is not read back with any text
  extractor: its checks come from the generator's data in reading order, its 2 pages were rendered (70 dpi) and looked
  at, and `pdffonts` was used once to confirm its font names (Helvetica, Helvetica-Bold, Helvetica-Oblique; base-14,
  not embedded).
- `score.mjs` was not run. Its `validateGroundTruth` rules (errors and warnings) are re-implemented in
  `generate_holdout4.py` (`validate_ground_truth`); all nine answer files pass them with no error and no warning, and
  the sha256 in every answer file matches the file in this folder. The public answer files were also checked (by the
  throwaway script) to have no non-ASCII character, quotation mark, apostrophe or in-word hyphen in any must_contain
  phrase or ordered anchor, and no dash, hyphen or quote in any heading.

## Known limits (also in each file's notes)

- The PDF text layer was never read, so invisible text-layer content is not checked, and characters whose code point
  cannot be seen are avoided in phrases, anchors and headings. Where table cells or noise texts must contain them, the
  assumption is stated and applies to every tool alike: ASCII hyphen-minus for negative numbers and for hyphens in
  cells and in the noise text 'AC 20-167B'; NCUA cells printed '--' are left empty (not scored); superscript note marks
  in NCUA row labels written as ¹ ² ³ ⁴ (NFKC makes them digits).
- FHFA: the charts (pages 7-8) and the check marks of the page-10 table are not checked; check-mark cells are empty.
- FAA: the signature appearance on page 1 is not checked; the kept pages have no table, so the file has no table check;
  three underlined run-in titles are too short to be listed as headings.
- NCUA: the cover may be an image and is not checked; page 14 (income rows as percent of average assets) is not
  transcribed; the section bands of the data tables are expected as table rows with text in the first cell.
- No public file has an absent check: none of the three has one-word hyphenation (their line-end hyphens are in
  compounds, identifiers or URLs). Only the FAA file has visible running page furniture longer than a page number.

## Disclosures

- No converter, text extractor or OCR was run on any file in this folder, and nothing about how a converter handles
  any of these documents was looked up. No git command was run. Nothing was written to `/tmp`; temporary files were
  kept in `holdout4/.work/` and deleted at the end.
- Read before writing the rule (format and method only): `SCORING.md`, `score.mjs`, `holdout3/SELECTION.md`,
  `holdout3/generate_holdout3.py` and two `holdout3` answer files (DOE, FDIC). `SCORING.md` reports earlier results,
  including areas where each tool lost points; see rule 5. `README.md`, `results/`, `corpus/`, `holdout/`,
  `holdout2/` and the converter code were not opened.
- Deviations from the rule as first written: (1) Amendment 1 added two series for kind (c) after the three listed ones
  had failed; both failed too, so it changed no pick, and kind (c) is left out. (2) The NCUA page-range end (k = 14)
  rests on a judgement about the 'Addenda' sub-heading (see the download record). (3) The FHFA and NCUA files served
  are later uploads or re-issues of the September 2025 editions (see "How the rule resolved"); the rule takes the
  publication date from the listing or announcement, and the files are the publishers' only copies.
- Incidental reading beyond titles and dates while parsing listings: the FAA listing rows include a one-sentence
  summary, one was printed (AC 20-167B's); the NHTSA research-note records carry an abstract in their `description`
  field, two December 2025 abstracts were printed; one Fishery Bulletin article page's abstract (a February 2025
  article) was printed while finding where the dates are. None of these items was a candidate, and none affected a
  pick.
- Slips: (1) for the NCUA PDF, HEAD gave no Content-Length and a one-byte ranged request was answered with the whole
  file (HTTP 200, range ignored); the body went to `/dev/null`, nothing was stored or read, and the size was then
  measured with a stream capped at 5,000,001 bytes (570,488 bytes, under the limit). (2) One cleanup command (`rm` of
  render images through a relative glob) was refused by a safety check and did nothing; the images were deleted later
  with the rest of `.work/`.
