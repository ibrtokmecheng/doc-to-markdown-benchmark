# Held-out test set 5: selection record

This folder is the fifth held-out test set (the sixth frozen set, after `corpus/`, `holdout/`, `holdout2/`,
`holdout3/` and `holdout4/`) for the doc-to-Markdown benchmark (PackForAI vs Microsoft MarkItDown), built with the
method of `holdout4/`. Same layout: documents here, answers in `ground-truth/<file>.json`, scored with

```
node score.mjs holdout5 <outDir>
```

Status: FROZEN (2026-11-24, 20:14 UTC). The selection rule below was written at 19:37 UTC on 2026-11-24, before any
document, listing or catalogue page was downloaded or opened; Amendment 1 was added at 19:40 UTC and Amendment 2 at
19:49 UTC (see there); picks, download record, answers and audit follow. **This set has 9 files, not 10: kind (c) (a
column-set technical report) is left out for the third set in a row, because every series listed for it, including
the two added by Amendment 2, failed under the rule (see "How the rule resolved"). The kind (a) file comes from a
series added by Amendment 1.**

## Blind protocol

The documents are chosen and the answers written **before** any converter touches them:

- PackForAI, MarkItDown and every other document converter or text extractor (pdftotext, pdfminer, pdfplumber,
  pypdf text extraction, OCR) are **not** run on these files. pypdf is used only to keep a page range and to count
  pages; `pdfinfo` only for page count and page size; `pdftoppm` only to render pages to images for reading;
  `pdffonts` only once, on the generated PDF, to confirm its font names.
- The conversion engine code (`aireadydoc/services/`, `packforai-motor*`), earlier results (`results/`), the folders
  `corpus/`, `holdout/`, `holdout2/` and `holdout3/`, the documents of `holdout4/`, `README.md`, scratchpad folders and
  earlier development outputs are not opened. No git command is run. The only files read outside this folder are
  `SCORING.md`, `score.mjs` (read, not run), `holdout4/SELECTION.md`, `holdout4/generate_holdout4.py` and three answer
  files of `holdout4/ground-truth/` (`pub-faa-ac-20-167b.pdf.json` in full; `pub-fhfa-hpi-202509.pdf.json` and
  `pub-ncua-qcuds-2025q2.pdf.json` for their metadata, notes, table names and first table rows) as format examples.
- Public PDFs: every check is typed from the rendered pages (read as images), never copied from a text layer.
- Generated files: every check is derived from the data in `generate_holdout5.py`, which also writes the files.
- `score.mjs` is not run on this folder by the reviewer; its validation rules (`validateGroundTruth`) are applied by
  reading them and re-implementing them in the generator's self-check, which also checks the public answer files.
- Temporary files are kept in `holdout5/.work/` only and deleted at the end; nothing is written to `/tmp`.

## Selection rule for the public PDFs (fixed before any document was downloaded or opened)

1. **Kinds**: one document of each of these kinds, each from a publisher not used before (not the Office of the
   Federal Register/GPO, the Senate or the Census Bureau of `corpus/`; not BEA, CDC (any CDC series), IRS or NIST of
   `holdout/`; not the Department of Labor, FDA, USGS or Treasury/Bureau of the Fiscal Service of `holdout2/`; not
   the Federal Reserve Board, the Department of Energy (including its offices, administrations and laboratories) or
   FDIC of `holdout3/`; not FHFA, FAA or NCUA of `holdout4/`), and a different publisher for each kind. As in the
   earlier sets, the publisher is the issuing agency (bureau or operating administration), not the cabinet
   department:
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
3. **Fixed issue, not a hand-picked one**: for kinds (a), (b) and (d), the issue or document **first published in
   June 2025** in a named series (June 2025 is fixed here, before any listing is read; `holdout/` used the first issue
   of 2025, `holdout2/` July 2025, `holdout3/` August 2025, `holdout4/` September 2025). For kind (c) only, the window
   is the whole second quarter, **April 1 to June 30, 2025**, and the **earliest** qualifying item in that window is
   taken, because a single month gave no qualifying item in `holdout3/` and `holdout4/` (`holdout4/SELECTION.md`:
   "these short-note series are column-set but publish too rarely for a single fixed month; a rule for (c) would need
   a wider fixed window"). Items are taken from the publisher's own listing, reading titles and dates only (for kind
   (c) also author names and affiliations, see below). The publication date is the date the listing gives; where the
   listing gives only a reference period (or only a month label that does not say it is the publication month) and
   no publication date, the date of the publisher's own release announcement (news release page) is used; where there
   is none, the `Last-Modified` header of the issue's PDF (HEAD request, or a one-byte ranged GET, only). Ties go to
   the earliest publication time, then to the lowest series or report number (numbers made of several parts compared
   part by part as integers). An item counts as an issue only if the publisher offers it as a PDF; an item without an
   obtainable PDF is skipped in date order. Documents that only cancel another document, errata, covers, front matter
   and whole-issue compilations of a journal that also offers its articles separately are not items.
   The series for each kind, in order of preference:
   (a) 1. U.S. Railroad Retirement Board (RRB), **Monthly Benefit Statistics**: the issue first published in June
          2025, as a PDF;
       2. Federal Highway Administration (FHWA), Office of Highway Policy Information, **Traffic Volume Trends**
          (monthly report), the PDF of the issue first published in June 2025;
       3. U.S. Department of State, Bureau of Consular Affairs, **Monthly Immigrant Visa Issuance Statistics**: the
          PDF table of issuances by post and visa class of the month whose tables were first published in June 2025.
   (b) 1. National Aeronautics and Space Administration (NASA), **NASA Policy Directives and NASA Procedural
          Requirements** (NPD and NPR: new, revised, or changed), by the effective date in the NASA Online Directives
          Information System (NODIS) listing;
       2. U.S. Department of Defense (Office of the Secretary of Defense, issuances published by Washington
          Headquarters Services), **DoD issuances** (DoD Directives, Instructions and Manuals and changes to them),
          by the date in the DoD Issuances listing at `esd.whs.mil`;
       3. Department of the Army, Army Publishing Directorate, **Army Regulations** (new, revised, or changed), by the
          publication date in the Army Publishing Directorate's listing (`armypubs.army.mil`).
   (c) 1. NOAA National Marine Fisheries Service (NMFS), Scientific Publications Office, **Fishery Bulletin**
          articles, by the online publication date in the journal's listing or article page;
       2. National Highway Traffic Safety Administration (NHTSA), National Center for Statistics and Analysis,
          **Traffic Safety Fact Sheets** (the publications the CrashStats listing types as "Traffic Safety Fact
          Sheets"), by the date in that listing;
       3. Defense Health Agency (DHA), Armed Forces Health Surveillance Division, **Medical Surveillance Monthly
          Report (MSMR)** articles, by the publication date the `health.mil` listing gives; if MSMR is offered only
          as whole-issue PDFs, the item is the issue, and the author condition applies to every article on the pages
          kept.
       For kind (c) an item counts only if every author is a federal employee by affiliation: for NOAA, every author
       has a NOAA affiliation (an NMFS science center or regional office, or another NOAA line office or
       laboratory); for NHTSA, no author other than NHTSA (its National Center for Statistics and Analysis or named
       NHTSA staff) is credited and no contractor is named as author; for MSMR, every author has a Department of
       Defense affiliation (DHA, a military service or a DoD laboratory, school or command) or another federal one.
       Affiliations are taken from the listing or the article page; items whose listed authors include a non-federal
       affiliation are skipped in date order. Where the listing and article page give no affiliations, they are taken
       from the item's rendered first page, read as an image for the author lines and the page layout only, before
       any check is written. Why these series: Fishery Bulletin is NOAA's own scientific journal, typeset in two
       columns as its house style, with articles of typically 5-25 pages and a few MB at most, many of them written by
       NMFS science center staff only; its host answered plain curl for `holdout4/`, whose record shows that
       volume 123 issues 2 and 3 appeared in 2025 (the dates of their articles are not known to the reviewer, and
       `holdout4/` found none published online in September 2025). NHTSA's Traffic Safety Fact Sheets are short
       annual-data sheets credited to NCSA alone and, as far as the reviewer remembers their layout, set in two
       columns beside their tables (not checked; the column condition below decides); `holdout4/` found that this
       series had no item in September 2025, and nothing is known about the second quarter. MSMR is DHA's
       peer-reviewed monthly journal, set in two columns, written mainly by surveillance and public-health staff of
       DHA and the military services; whether `health.mil` answers plain curl is not known.
   (d) 1. Commodity Futures Trading Commission (CFTC), **Financial Data for Futures Commission Merchants** (monthly),
          the PDF of the edition first published in June 2025;
       2. Farm Credit Administration (FCA), **Farm Credit System Major Financial Indicators** (quarterly), the PDF of
          the edition first published in June 2025;
       3. Federal Emergency Management Agency (FEMA), **The Watermark** (the National Flood Insurance Program's
          quarterly financial and statistical report), the edition first published in June 2025.
   The next series of a kind is used only if: the host refuses plain curl; the file is 5 MB or larger; the series
   has no issue (for (c): no qualifying item) first published in the window; for kind (c), the chosen item (the
   earliest qualifying one) is not set in two or more columns as seen on the rendered first page of its main text
   (the first page with running text after any cover, notice, report-documentation or front-matter pages), or its
   rendered first page shows an author who is not a federal employee by affiliation (when the listing and article
   page gave none); or the series' publisher is already the pick of another kind (kinds are resolved in the order a,
   b, c, d). If every series of a kind fails, the kind is left out and reported; it is not replaced by a document
   picked by hand, and no series is added after a listing has been read unless it is recorded below as a dated
   amendment and a deviation.
4. **Size and page range**: under 5 MB as served, checked with a HEAD request (`Content-Length`) or a one-byte
   ranged request before the full download; a file whose size cannot be learned that way is fetched with
   `--max-filesize` so that curl stops before 5 MB. A document of more than 15 pages keeps pages 1 to k, where k is the
   largest page number of at most 15 at whose end a section or a table ends (the next page starts with a new section
   heading or a new table title), judged from the rendered pages' headings only; if no page of 1-15 qualifies, pages
   1-15 are kept and this is reported as a deviation. Cut with pypdf (`PdfWriter.add_page` plus the document
   information dictionary, as in the earlier sets). Source URL, retrieval date, page range and sha256 of the served
   and the kept file are recorded below.
5. **No tool influence**: no document is swapped after download (other than by the conditions written above), and
   nothing about how any converter handles a document is looked up or tried. Disclosure: `SCORING.md`, read for the
   format, reports earlier results and names areas where each tool lost points (line-end hyphens in multi-column
   text, CSV-text tables, thousands separators in table cells, pipe tables built from prose, padding columns);
   `holdout4/SELECTION.md` reports which series failed there and some listing dates (FHFA, FAA, NMFS, NHTSA). The
   series above were fixed from the kinds alone, before any listing was read, and the generated files use ordinary
   features listed in the task (headings, numbered and lettered lists, merged or multi-line table headers, notes,
   numbers with separators) without being built around any of those findings.

## Amendment 1 (2026-11-24, 19:40 UTC): two more series for kind (a) (DEVIATION from the rule above)

Written after the three (a) series above had failed under the rule (RRB: no series of that name in RRB's listing,
and the monthly benefit report RRB does list, "Benefit and Beneficiaries", ended with the December 2024 report;
FHWA: the listing redirects to `highways.dot.gov`, which refused plain curl with HTTP 403; State Department:
`travel.state.gov` refused plain curl with a Cloudflare block page, HTTP 403; see "How the rule resolved") and
**before** the listings of the series below were read and before any (a) document was opened, and before any
listing of kinds (b), (c) or (d) was read. Under the rule as first written, kind (a) would be left out; because a set
without a statistical release loses a whole kind, two more series are added, as `holdout4/` did for kind (c). The
maintainer may drop the resulting file if this amendment is not accepted (the other files do not depend on it).
Both were chosen from the kind alone (monthly releases with data tables from agencies not named anywhere above, so
that they cannot take a publisher of another kind), not from any item of them:

   (a) 4. Bureau of Reclamation (Department of the Interior), **24-Month Study** (the monthly operations study of
          the Colorado River system reservoirs, "Most Probable" run), the PDF of the study first published in June
          2025;
       5. U.S. Army Corps of Engineers, Detroit District, **Monthly Bulletin of Lake Levels for the Great Lakes**, the
          bulletin first published in June 2025.
   The size, host, date, tie and page-range conditions of the rule apply unchanged; if both series fail too, kind (a)
   is left out.

## Amendment 2 (2026-11-24, 19:49 UTC): two more series for kind (c) (DEVIATION from the rule above)

Written after the three (c) series above had failed under the rule (Fishery Bulletin: the four articles published
online in the window had non-federal authors or a file of 5 MB or more; NHTSA fact sheets: the earliest item in the
window is set in one text column beside a sidebar box; MSMR: articles are web pages only, and the earliest issue PDF
in the window is 6.4 MB; see "How the rule resolved") and **before** the listings of the series below were read and
before any of their documents was opened. Kind (a) was resolved before this amendment and kind (b) had been resolved
too (its pick is recorded below); the listings of kind (d) had not been read. Under the rule as first written, kind
(c) would be left out for the third set in a row; two more series are added, as `holdout4/` did. The maintainer may
drop the resulting file if this amendment is not accepted (the other files do not depend on it). Chosen from the kind
alone, not from any item of them:

   (c) 4. Congressional Research Service (CRS, Library of Congress), **In Focus** briefs (product type "IF"), by the
          date the CRS listing (`crsreports.congress.gov`) gives for the first version of each product (a product
          first published before April 1, 2025 and only updated in the window does not count); authors are CRS
          analysts, federal (legislative branch) employees by affiliation. Why: In Focus briefs are two-page research
          notes typeset in two columns, written by CRS staff only, small files, published many times a month.
          Disclosure: In Focus briefs are policy and research analyses, often not scientific in subject; the kind
          (c) condition kept is the layout and the federal authorship, not the subject;
       5. U.S. Army Medical Center of Excellence, **Medical Journal** articles (the journal formerly titled the AMEDD
          Journal), by the publication date the journal's listing gives; if it is offered only as whole-issue PDFs,
          the item is the issue, and the author condition applies to every article on the pages kept. Why: a
          journal-style series set in two columns, written mainly by Army Medical Department staff; whether its host
          answers plain curl is not known.
   The author, size, host, tie, window and column conditions of the rule apply unchanged; if both series fail too,
   kind (c) is left out.

## Generated documents (rule)

Six ordinary business files, one each of DOCX, PPTX, XLSX, CSV, JSON and PDF, written deterministically by
`generate_holdout5.py` (run with `uv run --with python-docx --with openpyxl --with python-pptx --with reportlab
python3 -I holdout5/generate_holdout5.py` from the benchmark folder), with new content (not reused from
`holdout4/`; the generators of the earlier sets are not opened, so their content is avoided only by choosing subjects
that the earlier records name for none of their files) and features such documents commonly have: headings, numbered
and lettered lists, tables with merged or multi-line headers, notes, numbers with separators. The script writes the
files and their answer files; every check is derived from the script's data and verified against the files read back
(DOCX, XLSX, PPTX, CSV, JSON) or against the generator's own data (PDF, never read back with a text extractor). File
names start with `gen-`; public PDFs with `pub-`.

## How the rule resolved (2026-11-24, 19:37-19:52 UTC; listings read for titles and dates only, plus author lines for (c))

Hosts that answered plain curl: `www.rrb.gov`, `www.usbr.gov`, `nodis3.gsfc.nasa.gov`, `spo.nmfs.noaa.gov`,
`crashstats.nhtsa.dot.gov`, `www.health.mil`, `medcoe.army.mil` and `www.cftc.gov`. Hosts that refused:
`highways.dot.gov` (HTTP 403 'Access Denied'; `www.fhwa.dot.gov/policyinformation/travel_monitoring/tvt.cfm` answers
301 to it), `travel.state.gov` (HTTP 403, Cloudflare block page) and `crsreports.congress.gov` (HTTP 403, Cloudflare
'Just a moment...' challenge). `www.usbr.gov` reset the connection on a HEAD request for a PDF but answered a one-byte
ranged GET (HTTP 206), which was used instead; this was not treated as a refusal.

**(a) Statistical release.** Series 1, RRB Monthly Benefit Statistics: RRB's listing of monthly and quarterly data
(`https://www.rrb.gov/FinancialReporting/FinancialActuarialStatistical/MonthlyQuarterly` and its 'Historical Data'
page) has no series of that name (RRB's site search for it returns no results); its monthly benefit report, "Benefit
and Beneficiaries", says "The December 2024 report is the final release" and has no 2025 issue; the other series there
are quarterly or are not the named series. **No issue in June 2025.** Series 2, FHWA Traffic Volume Trends: the listing
redirects to `highways.dot.gov`, which **refused plain curl**. Series 3, State Department Monthly Immigrant Visa
Issuance Statistics: `travel.state.gov` **refused plain curl**. Amendment 1 (written at 19:40 UTC, after these three
failed and before the listings below were read): series 4, Reclamation 24-Month Study: the listing
(`https://www.usbr.gov/lc/region/g4000/24mo/index.html`) is a year/month selector whose script builds the PDF address
of each month's study (`.../24mo/<year>/<MON><yy>.pdf` for the Most Probable run); it gives month labels only. A
release announcement could not be read: Reclamation's news-release listing loads its items by script, so plain curl
returns no items. The date is therefore the `Last-Modified` header (one-byte ranged GETs): May 2025 study 15 May 2025,
**June 2025 study 17 June 2025**, July 2025 study 15 July 2025; the June study also carries the footer date June 17,
2025. **Picked: the June 2025 Most Probable 24-Month Study** (`https://www.usbr.gov/lc/region/g4000/24mo/2025/JUN25.pdf`,
761,298 bytes). Series 5 (USACE Great Lakes bulletin) was not needed and its listing was not read.

**(b) Agency guidance.** Series 1, NASA NPD/NPR: the NODIS master list of current directives
(`https://nodis3.gsfc.nasa.gov/Rpt_current_directives.cfm`) gives effective dates; June 2025 entries: NPR 1600.3B
(6/6/25), NPD 2540.1K updated with Change 3 (6/17/25), NPD 1850.1A and NPR 1850.1A (6/19/25), NPR 1450.4H (6/23/25), NPR
1040.1A (6/26/25). The NODIS historical-documents search (cancelled NPDs and NPRs) lists no directive effective in June 2025
that was cancelled later (the NPDs and NPRs cancelled from June 2025 on are NPR 1450.4G, NPR 1040.1 and NPR 9660.1A,
all effective years before 2025, NPR 3711.1B, revalidated November 15, 2024, and NPD 5000.2D, effective August 12,
2016). Earliest: **NPR 1600.3B, Personnel Security, effective
June 6, 2025**; its 'View all pages in PDF' link redirects (by a script line) to
`https://nodis3.gsfc.nasa.gov/npg_img/N_PR_1600_003B_/N_PR_1600_003B_.pdf` (158,652 bytes, Last-Modified 4 September
2025, a later regeneration by NODIS; there is no other copy). **Picked.** NODIS shows only each directive's latest
effective date, so a change made in June 2025 to a directive changed again later would not be visible; none can be
known from the listing.

**(c) Column-set technical report.** Window April 1 - June 30, 2025. Series 1, Fishery Bulletin: the journal listing
(`https://spo.nmfs.noaa.gov/fb.htm`) and the issue pages of 123(1)-123(4) with their article pages ('Published online'
dates; author names only, no affiliations) give four articles in the window: 7 May 2025 (1233_02, Anaya et al.),
9 May 2025 (1233_03, Spanik et al.), 2 June 2025 (1233_04, Lee et al.), 30 June 2025 (1233_05, Kroetz et al.). As the
rule says, affiliations were taken from each rendered first page (80 dpi, author lines and layout only): 1233_02
Washington State University; 1233_03 South Carolina Department of Natural Resources; 1233_04 NOAA SWFSC with the
Inter-American Tropical Tuna Commission, the Center for the Advancement of Population Assessment Methodology and a
Japanese institute; all three skipped (non-federal authors). 1233_05 is 6,003,670 bytes (HEAD), 5 MB or more, so it
could not be used (and its authors could not be checked). **No qualifying item.** Series 2, NHTSA Traffic Safety Fact
Sheets (CrashStats `https://crashstats.nhtsa.dot.gov/api/Public/getByType/11`, `createdOn` dates): the earliest item in
the window is DOT HS 813 713, "2023 Alcohol-Impaired Driving Traffic Safety Facts" (2025-04-09; 1,239,950 bytes); its
first page, rendered at 80 dpi, sets the running text in **one column** beside a shaded contents box (a sidebar), which
was judged not to be text set in two columns (judgement disclosed; the same family's Crash-Stats brief was judged one
column in `holdout4/`). **Failed on the column condition.** Series 3, MSMR: articles are web pages (with separate
table attachments); PDFs are offered per issue only, so the item is the issue. The archive
(`.../Medical-Surveillance-Monthly-Report/View-Past-Reports`) dates the April 2025 issue 2025/04/01, the first in the
window; its PDF is 6,442,003 bytes (5 MB or more). **Failed on size.** Amendment 2 (written at 19:49 UTC, after these
three failed and before the listings below were read): series 4, CRS In Focus: `crsreports.congress.gov` **refused
plain curl**. Series 5, Army Medical Center of Excellence Medical Journal: the archive
(`https://medcoe.army.mil/the-medical-journal-archive/`) offers the 2025 issues 'Jan-Mar' and 'Apr-Jun (250th
Edition)' as whole-issue PDFs (21,995,538 and 20,014,458 bytes, both Last-Modified November 20, 2026) and later
articles as separate PDFs dated 22 September 2025 in their file names; the item in the window, the Apr-Jun issue, is
5 MB or more. **Failed on size.** **Kind (c) is therefore left out for the third set in a row; no document was picked
by hand and no further series was added.**

**(d) Financial statement.** Series 1, CFTC Financial Data for FCMs: the listing
(`https://www.cftc.gov/MarketReports/financialfcmdata/index.htm`) gives only the as-of date of each monthly report
(reference period); CFTC announces updates of this page by e-mail alert only (as the page says), so there is no
news-release page and the date is the `Last-Modified` header: March 31, 2025 data 7 May 2025, **April 30, 2025 data
6 June 2025** (the file sits in the site's `2025-06` upload folder), May 31, 2025 data 8 July 2025. **Picked: the April
30, 2025 report**
(`https://www.cftc.gov/sites/default/files/2025-06/01%20-%20FCM%20Webpage%20Update%20-%20April%202025.pdf`, 100,385
bytes). Series 2 and 3 were not needed and their listings were not read.

Publishers: Bureau of Reclamation (a), NASA (b), CFTC (d), all different and none used before.

## Public documents (US federal works, public domain under 17 U.S.C. 105)

| file | kind | publisher | URL | why |
|---|---|---|---|---|
| `pub-usbr-24ms-202506.pdf` | (a) monthly statistical/operations release with data tables | Bureau of Reclamation | https://www.usbr.gov/lc/region/g4000/24mo/2025/JUN25.pdf | Amendment 1 series 4: the 24-Month Study (Most Probable) first published in June 2025 (June 17, 2025) |
| `pub-nasa-npr-1600-3b.pdf` | (b) agency directive | National Aeronautics and Space Administration | https://nodis3.gsfc.nasa.gov/npg_img/N_PR_1600_003B_/N_PR_1600_003B_.pdf | The NPD/NPR with the earliest effective date in June 2025 (NPR 1600.3B, June 6, 2025) |
| `pub-cftc-fcm-202504.pdf` | (d) financial data made of one large table | Commodity Futures Trading Commission | https://www.cftc.gov/sites/default/files/2025-06/01%20-%20FCM%20Webpage%20Update%20-%20April%202025.pdf | The FCM financial data report first published in June 2025 (April 30, 2025 data, posted June 6, 2025) |

### Download record (2026-11-24, 19:41-19:51 UTC, plain curl with `--max-filesize`, each file into its own empty folder under `.work/` first)

| file | served file sha256 | pages served | kept | file in this folder (sha256) |
|---|---|---|---|---|
| `pub-usbr-24ms-202506.pdf` | `753bbd01960b0834d5cd2a635d404614360e72372156ba0f489c791eacf6a084` (761,298 bytes, Last-Modified 17 Jun 2025, tagged) | 20 | pages 1-15 (two narrative pages, then one table per page: Fontenelle to Hoover Dam - Lake Mead (power)); page 16 starts a new table ('Davis Dam - Lake Mohave', power), so 15 is the largest k at whose end a table ends | `83096a2d33ee562b3dc8d18baddce2a10625bc3f38dc53a32bf8ace7a0b48db9` |
| `pub-nasa-npr-1600-3b.pdf` | `46b0801abc4ee2c5aa499b28ddcc4831d5a3315e9f67d162cea97acdd4489d78` (158,652 bytes, Last-Modified 4 Sep 2025, untagged) | 26 | pages 1-13 (contents, Preface, Chapters 1-2); page 14 starts 'Chapter 3. Personnel Security for Sensitive Positions'; pages 15 and 16 begin with the numbered paragraphs 3.1.13 and 3.4.5 (no heading), so 13 is the largest k | `07f48e74252d6bf101dd56cb1d191b597e0d183b18168cfb84c52851d4b3d5ce` |
| `pub-cftc-fcm-202504.pdf` | `b17f6e35d9f8684f51e4306bf88f49e39d594ed7c52c042197f45f32e6d60493` (100,385 bytes, untagged) | 2 | all (not cut) | same as served |

The page ranges were judged from 40 dpi contact sheets of all pages (headings and table titles only) and 110 dpi
renders of the pages around the cut. Both cuts were made with pypdf 7.1.1 (`uv run --with pypdf python3 -I
cut_pages.py <served.pdf> <out.pdf> 1 k`, a throwaway script: `PdfWriter.add_page` for each kept page plus the
document information dictionary, as in the earlier sets); two runs gave the same bytes. The Reclamation file, tagged
as served, is untagged after the cut. The served originals, the cut copies, the Fishery Bulletin and NHTSA files
downloaded only for the author and column checks (sha256 `7285171f...` 1233_02, `4750f137...` 1233_03, `369883a8...`
1233_04, `d7acc5b9...` DOT HS 813 713) and all renders were deleted after use; only the kept files are in this folder.

## Generated documents

Written by `generate_holdout5.py` (deterministic; new content), run as `uv run --with python-docx --with openpyxl
--with python-pptx --with reportlab python3 -I holdout5/generate_holdout5.py` from the benchmark folder. Rule: one
ordinary business document per format, using features such documents commonly have; nothing was designed around any
converter's known strengths or weaknesses. The script's helpers (normalization, validation, read-back verification,
OOXML pinning) are copied from `holdout4/generate_holdout4.py`; the documents, data and checks are new (fictitious
company 'Northgate Precision Components, LLC'). Running the script twice gave byte-identical files and answer files
(python-docx 1.2.0, openpyxl 3.1.5, python-pptx 1.0.2, lxml 6.1.3, reportlab 5.1.1, Python 3.14.6). The script also
checks the three public answer files against the same validation rules, the phrase rules below and their sha256
against the files in this folder. Changes made while writing, because the script's own audit rules or a look at the
rendered PDF called for them: the workbook's first sheet was planned as 'Register' (a word inside the title and the
note) and became 'Fixed Assets'; 'Depreciation' was dropped from must_contain (it occurs inside the note) and the last
workbook anchor became the code '0590' (the location name repeats); the PDF anchor 'Heat treatment' became 'Offices'
(it repeats in the findings table); the JSON material URLs were renamed so that no session id occurs inside them; the
PDF's findings table got a wider date column after the first render showed dates crossing the cell border.

| file | what it is | sha256 |
|---|---|---|
| `gen-migration-sow.docx` | statement of work: Title style, Heading 1/2/3 with typed section numbers, two-level bullets, a numbered list with lettered sub-items, a second numbered list restarting at 1, a payment table with two header rows (three cells merged down, one across two columns), two-paragraph milestone cells and a total row merged across two columns, a rate table with line breaks inside header cells and a total row merged across three columns, captions, an italic note, bold/italic runs, a signature table with empty cells and a non-ASCII name, page header and footer | `345561fa79f5edeef8dea476060ce9527709c666a33d7e004ff3031e67a107c5` |
| `gen-asset-register.xlsx` | 3 sheets: fixed assets (merged title and note rows, two header rows with groups merged across two and three columns and five headers merged down, five header texts with line breaks, text tags with leading zeros, `yyyy-mm-dd` dates, `#,##0.00`, 29 formula cells in the workbook saved with computed values, a total row, frozen panes, a note below the table); disposals with `mm/dd/yyyy` dates and gains/losses in parentheses; locations with text codes, `#,##0`, booleans, `d-mmm-yyyy` dates, percentages computed from the register, autofilter | `a45011aa11f38df8ce31e357bbc013b2f4f56d12e3a4548947d94087c0b9ee2b` |
| `gen-support-review.pptx` | 7-slide support review: title slide, bulleted agenda, native table with two header rows (merged down and across) and a total row, Comparison slide (two heading placeholders over two-level bulleted bodies), Title Only slide with two free text boxes, Section Header slide, two-level bullets, speaker notes on 3 slides | `033f8f6056882ded229d1334a43f047bf115788e52c8c646e2df48c9303aa9f3` |
| `gen-shipment-log.csv` | shipment log export: UTF-8 without BOM, every field quoted, LF record ends, 7 records spanning two lines (quoted line breaks), commas, a semicolon and doubled quotes in fields, plain decimals, ISO dates and timestamps, empty fields, non-ASCII place names | `083fd6a679b543889f3353af968de4ff806f69a394590c423ca669e0043c5be4` |
| `gen-event-agenda.json` | event agenda export: 4-space indentation, an event object and an array of 8 sessions, nested objects, arrays of objects and strings, empty arrays, nulls, booleans, keys that differ between records, timestamps with offsets, escaped quotes, non-ASCII names | `aecf5f763df9d8034ff55079df2cb7071aaba490ad92c5a2d8fb32e60c380028` |
| `gen-safety-report.pdf` | ReportLab quarterly safety report, 2 pages: title and headings by font size, key-value table without a header row, a table with two header rows (spans across and down) and a total row, a numbered list with lettered sub-items, a findings table with wrapped cells continuing onto page 2 with its header repeated, a bulleted list, an italic note, running header and footer ('Page N of 2') | `04de5c131e0ed93443b495aef02568f7a417220c547488c1217d402b0a8e9b09` |

`generate_holdout5.py` itself: sha256 `deaa985c30123217fe27b4f4b9b6e06079a3d5723ee406803871f7383e6adc2f` at freeze.

## Checks per file

| file | must_contain | ordered | headings | tables (non-empty cells) | noise | absent |
|---|---|---|---|---|---|---|
| `gen-migration-sow.docx` | 30 | 8 | 10 | 3 (64) | 0 | 0 |
| `gen-asset-register.xlsx` | 16 | 5 | 0 | 3 (170) | 0 | 0 |
| `gen-support-review.pptx` | 19 | 7 | 7 | 1 (30) | 0 | 0 |
| `gen-shipment-log.csv` | 18 | 5 | 0 | 1 (356) | 0 | 0 |
| `gen-event-agenda.json` | 15 | 5 | 0 | 0 | 0 | 0 |
| `gen-safety-report.pdf` | 20 | 7 | 6 | 3 (79) | 3 | 0 |
| `pub-usbr-24ms-202506.pdf` | 46 | 8 | 1 | 2 (859; both complete) | 1 | 0 |
| `pub-nasa-npr-1600-3b.pdf` | 47 | 8 | 28 | 0 (the kept pages have no table) | 2 | 0 |
| `pub-cftc-fcm-202504.pdf` | 39 | 8 | 0 | 1 (366; PARTIAL: header rows, firm rows 1-15 and the Totals row) | 2 | 0 |

## Answers and audit

- Public PDFs: answers typed from the rendered pages (pdftoppm: 100-120 dpi full pages; 200-300 dpi crops of every
  transcribed table cell and of the page-2 notes of the CFTC file, read as images). Every transcribed table was checked
  with the arithmetic the document implies, by a throwaway script (not committed): Reclamation: Lake Mead 'Glen
  Release' = Lake Powell 'Total Release' in all 39 rows; Powell total = power plant + bypass release (3 rows off by 1,
  the publication's rounding); WY 2025 and WY 2026 totals = sums of their months in every summed column within 1
  except two values off by 2 (kept as printed after a 300 dpi re-read); monthly storage balance within 2 except one
  historical month (3); Mead release in 1000 CFS = acre-feet / (1.98347 x days) within 0.06 in every month; the two
  elevation columns (not covered by any identity) were re-read at 300 dpi. CFTC: in all 15 firm rows (d) = adjusted
  net capital - (c), (g) = (e) - (f), (k) = (i) - (j), (o) = (m) - (n), exactly, and the same three identities in the
  Totals row; columns (h), (l), (p) and (q) and the name, registration and DSRO columns were re-read at 300 dpi. A
  second pass re-read every phrase, anchor and heading of the three files against the renders; no check string
  changed in that pass (one count in the CFTC notes was corrected).
- Generated files: `generate_holdout5.py` reads each DOCX/XLSX/PPTX/CSV/JSON file back (heading styles, list numbering
  and levels, merged cells, line breaks and two-paragraph cells, cached formula values, text-stored codes, merged pptx
  table cells, Comparison placeholders, text boxes and speaker notes, CSV quoting and record ends) and verifies every
  check against it, plus the audit rules of the earlier sets (no file name or converter-added text in a check, prose
  phrases of 6+ words that occur once, data-file items that are whole fields not inside another field, ordered anchors
  unique, in reading order and never from speaker notes). The generated PDF is not read back with any text extractor:
  its checks come from the generator's data in reading order, its 2 pages were rendered (70 dpi) and looked at, and
  `pdffonts` was used once to confirm its font names (Helvetica, Helvetica-Bold, Helvetica-Oblique; Type 1, base-14,
  not embedded).
- `score.mjs` was not run. Its `validateGroundTruth` rules (errors and warnings) are re-implemented in
  `generate_holdout5.py` (`validate_ground_truth`); all nine answer files pass them with no error and no warning, and
  the sha256 in every answer file matches the file in this folder. The script also checks that no public must_contain
  phrase or ordered anchor holds a non-ASCII character, a quotation mark, an apostrophe or an in-word hyphen, and that
  no public heading holds a dash, hyphen or quote.

## Known limits (also in each file's notes)

- The PDF text layer was never read, so invisible text-layer content is not checked, and characters whose code point
  cannot be seen are avoided in phrases, anchors and headings. Where table cells or noise texts must contain them, the
  assumption is stated and applies to every tool alike: ASCII hyphen-minus in 'Ac-Ft' (Reclamation table headers),
  ASCII apostrophe in "Customers' Assets in Seg" and "Customers' Seg Required 4d(a)(2)" (CFTC headers), two ASCII
  hyphen-minus in the NASA noise text 'NPR 1600.3B --'.
- Reclamation: 11 of the 13 tables are not transcribed (their titles are phrases); the page-1 title (with '24-Month')
  is not checked; only 'References' is a heading. NASA: the logo and the masthead words beside it are not checked.
  CFTC: firm rows 16-63 are checked only through nine firm names; the page-2 notes are checked as phrases, not as a
  table.
- Noise maxima: in this set every visible running header or footer that occurs nowhere in the body has max 1 (one
  kept copy is tolerated), as the generated PDFs of `holdout4/` and this set do; `holdout4/`'s FAA file used max =
  number of body occurrences (no kept copy tolerated). Applies to every tool alike.
- No public file has an absent check: none of the three has one-word hyphenation at a line end.

## Disclosures

- No converter, text extractor or OCR was run on any file in this folder, and nothing about how a converter handles
  any of these documents was looked up. No git command was run. Nothing was written to `/tmp`; temporary files were
  kept in `holdout5/.work/` and deleted at the end.
- Read before writing the rule (format and method only): `SCORING.md`, `score.mjs`, `holdout4/SELECTION.md`,
  `holdout4/generate_holdout4.py` and three `holdout4` answer files (FAA in full; FHFA and NCUA in part). `SCORING.md`
  reports earlier results, including areas where each tool lost points; see rule 5. `holdout4/SELECTION.md` named the
  Fishery Bulletin and NHTSA CrashStats listings and their September 2025 results, and that NHTSA research notes exist
  for 12 May 2025 (that series was not used here). `README.md`, `results/`, `corpus/`, `holdout/`, `holdout2/`,
  `holdout3/`, the `holdout4/` documents and the converter code were not opened.
- Deviations from the rule as first written: (1) Amendment 1 added two series for kind (a) after the three listed ones
  had failed; its first series gave the (a) pick, which the maintainer may drop if the amendment is not accepted.
  (2) Amendment 2 added two series for kind (c) after the three listed ones had failed; both failed too, so it changed
  no pick, and kind (c) is left out. (3) Judgements: the RRB series named in the rule does not exist under that name
  and the monthly benefit report that does exist ended in 2024; the NHTSA fact sheet's sidebar-plus-one-column page
  was judged not set in two columns; the 24-Month Study (historical data plus model projections) was treated as a
  monthly statistical release with data tables, as Amendment 1 says. (4) Dates from `Last-Modified` (no readable
  release announcement): Reclamation (news listing loaded by script) and CFTC (e-mail alerts only); the NASA file
  served is a September 2025 regeneration of a directive effective June 6, 2025, and the publisher's only copy.
- Incidental reading beyond titles and dates: rendering the first pages of three Fishery Bulletin articles and one
  NHTSA fact sheet (for author lines and layout, as the rule allows) also showed their abstracts, key findings and
  opening paragraphs; the 40 dpi contact sheets used for the page ranges showed every page of the two cut documents,
  including pages not kept; `pdfinfo` printed document metadata (title, creator, producer, tagged) besides page count
  and size; listing pages carried short descriptions (RRB, CFTC). None of this affected a pick.
- Slips: (1) for the fifth Fishery Bulletin article, a GET with `--max-filesize` was chained after the HEAD request
  that had already shown 6,003,670 bytes; curl stopped on the announced length and stored nothing. The one-byte ranged
  GET for the April 2025 MSMR issue was answered with the whole file (HTTP 200, range ignored); `--max-filesize` made
  curl stop on the announced length (6,442,003 bytes) with the body going to `/dev/null`, so nothing was stored or read. (2) Thumbnails (30 dpi)
  of all 13 pages of the NHTSA fact sheet were rendered by mistake before its first page alone was checked; they were
  deleted without being looked at.
