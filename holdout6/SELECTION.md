# Held-out test set 6: selection record

This folder is the sixth held-out test set (the seventh frozen set, after `corpus/`, `holdout/`, `holdout2/`,
`holdout3/`, `holdout4/` and `holdout5/`) for the doc-to-Markdown benchmark (PackForAI vs Microsoft MarkItDown), built
with the method of `holdout5/`. Same layout: documents here, answers in `ground-truth/<file>.json`, scored with

```
node score.mjs holdout6 <outDir>
```

Status: FROZEN (2026-11-25, 09:27 UTC). The selection rule below was written at 08:35 UTC on 2026-11-25, before any
document, listing or catalogue page of this set was downloaded or opened; Amendment 1 was added at 08:41 UTC and
Amendment 2 at 08:45 UTC (see there); picks, download record, answers and audit follow. **This set has 8 files, not 10:
kinds (a) (statistical release) and (b) (agency guidance) are left out, because every series listed for them,
including the two added by each amendment, failed under the rule (most had nothing in October 2025, the month of the
lapse in federal appropriations; see "How the rule resolved"). The kind (c) file (MSMR, September 2025) comes from
series 2 of its list, because series 1's host could not be reached from the reviewer's machine.**

## Blind protocol

The documents are chosen and the answers written **before** any converter touches them:

- PackForAI, MarkItDown and every other document converter or text extractor (pdftotext, pdfminer, pdfplumber,
  pypdf text extraction, OCR) are **not** run on these files. pypdf is used only to keep a page range and to count
  pages; `pdfinfo` only for page count and page size; `pdftoppm` only to render pages to images for reading;
  `pdffonts` only once, on the generated PDF, to confirm its font names.
- The conversion engine code (`aireadydoc/services/`, `packforai-motor*`), earlier results (`results/`), the folders
  `corpus/`, `holdout/`, `holdout2/`, `holdout3/` and `holdout4/`, the documents and outputs of `holdout5/`,
  `README.md`, scratchpad folders and earlier development outputs are not opened. No git command is run. The only
  files read outside this folder are `SCORING.md`, `score.mjs` (read, not run), `holdout5/SELECTION.md`,
  `holdout5/generate_holdout5.py` and three answer files of `holdout5/ground-truth/` (`pub-nasa-npr-1600-3b.pdf.json`
  in full; `pub-cftc-fcm-202504.pdf.json` and `pub-usbr-24ms-202506.pdf.json` for their metadata, notes, table names
  and first table rows) as format examples.
- Public PDFs: every check is typed from the rendered pages (read as images), never copied from a text layer.
- Generated files: every check is derived from the data in `generate_holdout6.py`, which also writes the files.
- `score.mjs` is not run on this folder by the reviewer; its validation rules (`validateGroundTruth`) are applied by
  reading them and re-implementing them in the generator's self-check, which also checks the public answer files.
- Temporary files are kept in `holdout6/.work/` only and deleted at the end; nothing is written to `/tmp`.

## Selection rule for the public PDFs (fixed before any document was downloaded or opened)

1. **Kinds**: one document of each of these kinds, each from a publisher not used before (not the Office of the
   Federal Register/GPO, the Senate or the Census Bureau of `corpus/`; not BEA, CDC (any CDC series), IRS or NIST of
   `holdout/`; not the Department of Labor, FDA, USGS or Treasury/Bureau of the Fiscal Service of `holdout2/`; not
   the Federal Reserve Board, the Department of Energy (including its offices, administrations and laboratories) or
   FDIC of `holdout3/`; not FHFA, FAA or NCUA of `holdout4/`; not the Bureau of Reclamation, NASA or CFTC of
   `holdout5/`), and a different publisher for each kind. As in the earlier sets, the publisher is the issuing agency
   (bureau, administration or operating administration), not the cabinet department:
   (a) a weekly or monthly statistical release with data tables,
   (b) an agency guidance document, directive or regulatory guide with numbered headings and lists,
   (c) a technical or scientific report set in two or more columns, authored by federal employees,
   (d) a financial or budget statement or report made mostly of tables.
2. **Works and hosts**: U.S. federal government works only (public domain under 17 U.S.C. 105). Official `.gov` or
   `.mil` hosts only, fetched with plain `curl` (default user agent, no browser emulation, no cookies; redirects
   followed only while they stay on `.gov`/`.mil` hosts). A host that refuses plain curl (HTTP 403 or another
   refusal, or a bot-check page instead of the content) is dropped, not worked around. Already known to refuse and
   not used: `usda.gov`, `ed.gov`, `hud.gov`, `opm.gov`, `transportation.gov`, `bls.gov`, `gao.gov`, `ssa.gov`,
   `cbo.gov`, `osha.gov`, `ftc.gov`, `www.nrc.gov/docs/`, and (from `holdout5/`) `highways.dot.gov`,
   `travel.state.gov` and `crsreports.congress.gov`. A host that resets the connection on a HEAD request but answers a
   one-byte ranged GET is not treated as refusing (as in `holdout5/`).
3. **Fixed issue, not a hand-picked one**: for kinds (a), (b) and (d), the issue or document **first published in
   October 2025** in a named series (October 2025 is fixed here, before any listing is read; `holdout/` used the first
   issue of 2025, `holdout2/` July 2025, `holdout3/` August 2025, `holdout4/` September 2025, `holdout5/` June 2025).
   For kind (c) only, the window is the second half of 2025, **July 1 to December 31, 2025**, and the **earliest**
   qualifying item in that window is taken (kind (c) found no qualifying item in a single month in `holdout3/` and
   `holdout4/`, nor in a quarter in `holdout5/`). Items are taken from the publisher's own listing, reading titles and
   dates only (for kind (c) also author names and affiliations, see below). The publication date is the date the
   listing gives; where the listing gives only a reference period (or only a month label that does not say it is the
   publication month) and no publication date, the date of the publisher's own release announcement (news release
   page) is used; where there is none, the `Last-Modified` header of the issue's PDF (HEAD request, or a one-byte
   ranged GET, only). Ties go to the earliest publication time, then to the lowest series or report number (numbers
   made of several parts compared part by part as integers), then to the item listed first in the publisher's listing.
   An item counts as an issue only if the publisher offers it as a PDF; an item without an obtainable PDF is skipped
   in date order. Documents that only cancel another document, errata, covers, front matter and whole-issue
   compilations of a journal that also offers its articles separately are not items.
   Disclosure: the reviewer knows from general knowledge (not from any listing) that U.S. federal appropriations
   lapsed from October 1 to November 12, 2025, so that many series published nothing in October 2025. The series
   below were chosen from the kinds alone, with a preference for publishers whose work is funded outside annual
   appropriations or continued during the lapse (multi-year civil works funds, mandatory programs, advance
   appropriations, fee or assessment funding, the Disaster Relief Fund); whether any of them published in October
   2025 is not known to the reviewer.
   The series for each kind, in order of preference:
   (a) 1. U.S. Army Corps of Engineers (USACE), Detroit District, **Monthly Bulletin of Lake Levels for the Great
          Lakes** (also titled "Monthly Bulletin of Great Lakes Water Levels"): the bulletin first published in
          October 2025, as a PDF;
       2. Centers for Medicare & Medicaid Services (CMS), the **monthly Medicaid and CHIP enrollment report** offered
          as a PDF on CMS's "Monthly Medicaid & CHIP Application, Eligibility Determination, and Enrollment Reports &
          Data" pages (the "Medicaid & CHIP Enrollment Trend Snapshot" or the monthly enrollment report PDF under the
          title CMS gives it there): the report first published in October 2025;
       3. Federal Retirement Thrift Investment Board (FRTIB), the **Thrift Savings Plan participant activity report**
          posted with the materials of the Board's monthly meetings: the report first published in October 2025.
   (b) 1. Veterans Health Administration (VHA, Department of Veterans Affairs), **VHA Directives** (new, revised or
          amended), by the date in the VHA Publications listing (`va.gov/vhapublications`);
       2. U.S. Department of Defense (Office of the Secretary of Defense, issuances published by Washington
          Headquarters Services), **DoD issuances** (DoD Directives, Instructions and Manuals and changes to them),
          by the date in the DoD Issuances listing (`esd.whs.mil`);
       3. General Services Administration (GSA), **GSA Orders** (the GSA directives library: orders new, revised or
          changed), by the date in the directives library listing.
   (c) 1. U.S. Army Medical Center of Excellence, **The Medical Journal** (formerly the AMEDD Journal) articles, by the
          publication date the journal's listing or archive gives (or the date in the article file name where the
          listing gives none, then the rule's fallbacks); where only whole-issue PDFs are offered, the item is the
          issue, and the author condition applies to every article on the pages kept;
       2. Defense Health Agency (DHA), Armed Forces Health Surveillance Division, **Medical Surveillance Monthly
          Report (MSMR)**: by the publication date the `health.mil` listing gives; where MSMR is offered only as
          whole-issue PDFs, the item is the issue, and the author condition applies to every article on the pages
          kept;
       3. NOAA National Marine Fisheries Service (NMFS), Scientific Publications Office, **Fishery Bulletin**
          articles, by the online publication date in the journal's listing or article page.
       For kind (c) an item counts only if every author is a federal employee by affiliation: for the Medical Journal
       and MSMR, every author has a Department of Defense affiliation (a military service, DHA, or a DoD medical
       center, laboratory, school or command) or another federal one; for NOAA, every author has a NOAA affiliation
       (an NMFS science center or regional office, or another NOAA line office or laboratory). Affiliations are taken
       from the listing or the article page; items whose listed authors include a non-federal affiliation are skipped
       in date order. Where the listing and article page give no affiliations, they are taken from the item's rendered
       first page (for a whole issue: the first page of each article on the pages that would be kept), read as an
       image for the author lines and the page layout only, before any check is written. Why these series: all three
       are journal-style series set in two columns as house style with staff authors; `holdout5/SELECTION.md` records
       that their hosts (`medcoe.army.mil`, `www.health.mil`, `spo.nmfs.noaa.gov`) answered plain curl in November
       2026, that the Medical Journal offered articles as separate PDFs dated 22 September 2025 in their file names
       (their size, authors and layout are not known to the reviewer), that an MSMR issue PDF of April 2025 was
       6.4 MB, and that Fishery Bulletin articles of April-June 2025 had non-federal co-authors. This knowledge is
       disclosed; no item of the July-December 2025 window has been seen.
   (d) 1. Federal Emergency Management Agency (FEMA), **Disaster Relief Fund: Monthly Report** (the DRF monthly report
          to Congress): the report first published in October 2025;
       2. Farm Credit Administration (FCA), **Farm Credit System Major Financial Indicators** (quarterly): the edition
          first published in October 2025;
       3. U.S. Department of Defense, Office of the Under Secretary of Defense (Comptroller), **reprogramming actions**
          (prior-approval and internal reprogramming documents, DD 1415 series), by the date in the Comptroller's
          reprogramming listing: the action first published in October 2025.
   The next series of a kind is used only if: the host refuses plain curl; the file is 5 MB or larger; the series has
   no issue (for (c): no qualifying item) first published in the window; for kind (c), the chosen item (the earliest
   qualifying one) is not set in two or more columns as seen on the rendered first page of its main text (the first
   page with running text after any cover, notice, report-documentation or front-matter pages), or its rendered first
   page shows an author who is not a federal employee by affiliation (when the listing and article page gave none);
   or the series' publisher is already the pick of another kind (kinds are resolved in the order a, b, c, d). If every
   series of a kind fails, the kind is left out and reported; it is not replaced by a document picked by hand, and no
   series is added after a listing has been read unless it is recorded below as a dated amendment and a deviation.
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
   `holdout5/SELECTION.md` reports which series failed there and some listing facts (see (c) above). The series above
   were fixed from the kinds alone, before any listing was read, and the generated files use ordinary features of
   such documents without being built around any of those findings.

## Amendment 1 (2026-11-25, 08:41 UTC): two more series for kind (a) (DEVIATION from the rule above)

Written after the three (a) series above had failed under the rule (USACE: `www.lre.usace.army.mil` could not be
reached with plain curl from the reviewer's machine, twice, minutes apart; CMS: the listing dates no monthly
enrollment report in October 2025; FRTIB: the site offers no participant activity report as a document, only Board
meeting minutes; see "How the rule resolved") and **before** the listings of the series below were read, before any
(a) document was opened, and before any listing of kinds (b), (c) or (d) was read. Under the rule as first written,
kind (a) would be left out; as `holdout5/` did, two more series are added. The maintainer may drop the resulting file if
this amendment is not accepted (the other files do not depend on it). Both were chosen from the kind alone (weekly or
monthly releases with data tables), not from any item of them, from publishers not named anywhere above, so that they
cannot take a publisher of another kind (the Veterans Benefits Administration is a different administration of the
Department of Veterans Affairs from the Veterans Health Administration of (b) 1; this is disclosed):

   (a) 4. Veterans Benefits Administration (VBA, Department of Veterans Affairs), **Monday Morning Workload Report**
          (weekly report of claims and appeals workload): the report first published in October 2025, as a PDF;
       5. Government National Mortgage Association (Ginnie Mae), **Global Markets Analysis Report** (monthly): the
          edition first published in October 2025, as a PDF; it counts only if the document shows it is prepared by
          Ginnie Mae (a federal work), not by a named outside firm.
   The size, host, date, tie and page-range conditions of the rule apply unchanged; if both series fail too, kind (a)
   is left out.

## Amendment 2 (2026-11-25, 08:45 UTC): two more series for kind (b) (DEVIATION from the rule above)

Written after both series of Amendment 1 had failed too (so that kind (a) is left out; see "How the rule resolved") and
after the three (b) series above had failed under the rule (VHA: the Directives listing gives no Issue Date in October
2025; DoD: `esd.whs.mil` refused plain curl with HTTP 403 'Access Denied'; GSA: the directives library gives no Issue
Date in October 2025), and **before** the listings of the series below were read, before any (b) document was opened,
and before any listing of kinds (c) or (d) was read. Under the rule as first written, kind (b) would be left out; two
more series are added, as for (a). The maintainer may drop the resulting file if this amendment is not accepted (the
other files do not depend on it). Both were chosen from the kind alone (directives with numbered paragraphs and lists,
issued by agencies whose work continued during the lapse in appropriations of October 2025: the military services and
federal law enforcement), not from any item of them, from publishers not named anywhere above:

   (b) 4. Department of the Navy, **DON Issuances** (SECNAV and OPNAV instructions, new, revised or changed; notices
          excluded), by the date in the DON Issuances listing (`secnav.navy.mil`);
       5. Federal Bureau of Prisons (BOP, Department of Justice), **Program Statements** (new, revised or changed), by
          the date in BOP's policy listing (`bop.gov`).
   The size, host, date, tie and page-range conditions of the rule apply unchanged; if both series fail too, kind (b)
   is left out.

## How the rule resolved (2026-11-25, 08:35-08:53 UTC; listings read for titles and dates only, plus author lines for (c))

Hosts that answered plain curl: `www.medicaid.gov`, `www.frtib.gov`, `www.benefits.va.gov`, `www.ginniemae.gov`,
`www.va.gov`, `www.gsa.gov`, `www.bop.gov`, `www.health.mil` and `www.fema.gov`. Hosts that refused: `www.esd.whs.mil`
(HTTP 403 'Access Denied', Akamai, for the home page, `/Directives/issuances/dodi/` and `/DD/`) and `www.secnav.navy.mil`
(a 'Request Rejected' block page, served with HTTP 200, for `/doni/default.aspx` and `/doni/allinstructions.aspx`).
Hosts that could not be reached: `www.lre.usace.army.mil` and `medcoe.army.mil`: on the reviewer's machine the system
resolver (`getaddrinfo`, inside and outside the command sandbox) failed for both names on every attempt (08:35, 08:38,
08:40, 08:46 and 08:49 UTC: curl 'Could not resolve host'), while a direct DNS query (`host`, Google DNS) returned
addresses for them. One diagnostic request was made with curl `--resolve` to the address `host` returned for
`www.lre.usace.army.mil` (an Akamai edge): TLS failed because the certificate served there (CN `www.usace.army.mil`)
does not name that host. Nothing further was tried (no `--resolve` for `medcoe.army.mil`, no `-k`); both hosts were
treated as not answering plain curl and their series as failed. **Disclosure**: this is a failure of name resolution on
the reviewer's machine, not an HTTP refusal by the hosts; `holdout5/` reached `medcoe.army.mil` on 2026-11-24. The
maintainer may re-run series (a) 1 and (c) 1 from a machine whose resolver resolves `army.mil` names; if either yields an
item, that item and not the picks below is what the rule selects for its kind.

**(a) Statistical release.** Series 1, USACE Great Lakes bulletin: **host not reachable** (see above). Series 2, CMS:
the Trend Snapshot page (`https://www.medicaid.gov/medicaid/national-medicaid-chip-program-information/medicaid-chip-enrollment-data/medicaid-and-chip-enrollment-trend-snapshot`)
says the series is phased out (its last issue is of 2024) and replaced by the monthly "Medicaid and CHIP Eligibility
Operations and Enrollment Snapshot"; the monthly-reports page
(`.../monthly-medicaid-chip-application-eligibility-determination-and-enrollment-reports-data`) offers its monthly data
on data.medicaid.gov only (no report PDF after 2017) and links that successor, whose listing
(`https://www.medicaid.gov/medicaid-and-chip-eligibility-operations-and-enrollment-snapshot`) gives release dates: June
2025 snapshot released September 26, 2025, July 2025 snapshot released November 17, 2025, **none in October 2025**
(judgement: the successor was taken as the monthly enrollment report the rule names; the Trend Snapshot itself has no
2025 issue either way). Series 3, FRTIB: `www.frtib.gov` offers Board meeting minutes (`/meeting-minutes/`, one PDF per
meeting) and reading-room reports, but **no participant activity report as a document**; the minutes were not opened.
Amendment 1 (08:41 UTC): series 4, VBA Monday Morning Workload Report: the listing
(`https://www.benefits.va.gov/REPORTS/detailed_claims_data.asp`) offers the October 2025 reports (MMWR-10-04-2025,
-10-11-, -10-18- and -10-25-2025) as Excel `.xlsm` files only; **no PDF** (the page's only PDF is a 2023 walk-through).
Series 5, Ginnie Mae Global Markets Analysis Report: `www.ginniemae.gov` is a script-built application, so the listing
was read from the site's own JSON endpoints that its script calls (`/router/translate-path?path=/disclosure/reports/ginnie-mae-global-markets-analysis-report`,
then the view `/api/v1/global-markets-analysis-report-2025`): month labels January-September, November and December
2025, no October label, no publication dates; the `Last-Modified` of the August, September, November and December 2025
PDFs is June 23, 2026 (a site migration), so their publication dates could not be determined, and all four are 10.3 to
12.2 MB, so whichever edition was first published in October 2025 **fails on size**. **Kind (a) is therefore left out.**

**(b) Agency guidance.** Series 1, VHA Directives: the listing (`https://www.va.gov/vhapublications/publications.cfm?pub=1`,
'Issue Date' column) has no directive issued in October 2025 (September 3, 10, 10, 18 and 30, 2025, then June 23, 2026);
it lists current directives only and offers no archive of rescinded ones, so a directive issued in October 2025 and
rescinded since could not be seen. **No item.** Series 2, DoD issuances: `www.esd.whs.mil` **refused plain curl**.
Series 3, GSA Orders: the eleven series pages of the directives library
(`https://www.gsa.gov/directives-library/by-number?num_series=...`, 242 directives, 'Issue Date' column) list September
8, 11, 17, 19 and 30, 2025 and November 3, 17 and 26, 2025, **none in October 2025** (current directives only).
Amendment 2 (08:45 UTC): series 4, DON Issuances: `www.secnav.navy.mil` **refused plain curl**. Series 5, BOP Program
Statements: the policy listing (`https://www.bop.gov/PublicInfo/execute/policysearch?todo=query`, 353 rows: 292
program statements, 54 Spanish versions, 6 operations memoranda; 'Date' column) has no item dated in 2025 after July 31,
2025 and before January 15, 2026: **none in October 2025**. **Kind (b) is therefore left out; no further series was
added.**

**(c) Column-set technical report.** Window July 1 - December 31, 2025. Series 1, Medical Journal: **host not
reachable** (see above). Series 2, MSMR: the archive
(`https://www.health.mil/Military-Health-Topics/Health-Readiness/Public-Health/AFHSD/Reports-and-Publications/Medical-Surveillance-Monthly-Report/View-Past-Reports`)
dates the issues by their path (`/Reference-Center/Reports/2025/07/01/MSMR-Vol-32-No-7-July-2025`, ... `2025/12/01/...`);
each issue link serves the issue PDF itself, and the articles have no separate PDFs, so the item is the issue. The
listing gives no affiliations; MSMR prints them in an 'Author Affiliations' paragraph at the end of each article, not on
its first page, so they were read there (as images, the affiliation lines only; a deviation in where the rule says to
look, disclosed). July 2025 (2025/07/01; 2,102,742 bytes; 22 pages; page 16 starts a new article, so pages 1-15 would
be kept, holding three articles): the Brief Report on the Millennium Cohort Study (pages 9-12) lists 'Leidos, Inc., San
Diego, CA' for three of its five authors; **skipped** (non-federal author). August 2025 (2025/08/01; 2,836,557 bytes;
26 pages; page 13 starts with a new table title, so at least pages 1-12 would be kept): the report on arbovirus exposure
in Papua New Guinea (pages 9-17) lists the Australian Defence Force Malaria and Infectious Disease Institute, QIMR
Berghofer Medical Research Institute (Brisbane) and the Papua New Guinea Defence Force; **skipped** (no U.S. federal
affiliation). September 2025 (2025/09/01; 4,199,552 bytes; 62 pages): page 16 starts with the section heading 'Most
frequent diagnoses', so pages 1-15 are kept; they hold the cover, the two-page table of contents and two AFHSD 'Update'
reports (absolute and relative morbidity burdens, pages 4-12; hospitalizations, pages 13-20, of which 13-15 are kept),
which carry no byline and no affiliation lines: they are credited only to the publisher (DHA's Armed Forces Health
Surveillance Division), which meets the federal-authorship condition (judgement disclosed); the first page of main text
(page 4) sets its running text in two columns beside a shaded findings box. **Picked: MSMR Vol. 32 No. 9, September
2025, pages 1-15.** Series 3 (Fishery Bulletin) was not needed and its listing was not read.

**(d) Financial statement.** Series 1, FEMA DRF monthly report: the listing
(`https://www.fema.gov/about/reports-and-data/disaster-relief-fund-monthly-reports`) gives a date for each report;
the only item dated in October 2025 is the **'September 2025 Disaster Relief Fund Report', October 23, 2025** (the
August 2025 report is dated September 16, 2025 and the October 2025 report November 23, 2025; the listing's pager links
return the same list). `https://www.fema.gov/sites/default/files/documents/fema_ocfo_disaster-relief-fund-report_102025.pdf`,
2,310,239 bytes, Last-Modified October 23, 2025; its cover is dated October 22, 2025. **Picked.** Series 2 and 3 were not
needed and their listings were not read.

Publishers: Defense Health Agency (c) and FEMA (d), different and none used before. This set therefore has two public
files, not four.

## Generated documents (rule)

Six ordinary business files, one each of DOCX, PPTX, XLSX, CSV, JSON and PDF, written deterministically by
`generate_holdout6.py` (run with `uv run --with python-docx --with openpyxl --with python-pptx --with reportlab
python3 -I holdout6/generate_holdout6.py` from the benchmark folder), with new subjects and new layouts (not reused
from `holdout5/`; the generators of the sets before it are not opened, so their content is avoided only by choosing
subjects and layouts that the records read here name for none of their files) and features such documents commonly
have. The script writes the files and their answer files; every check is derived from the script's data and verified
against the files read back (DOCX, XLSX, PPTX, CSV, JSON) or against the generator's own data (PDF, never read back with
a text extractor). File names start with `gen-`; public PDFs with `pub-`.

## Public documents (US federal works, public domain under 17 U.S.C. 105)

| file | kind | publisher | URL | why |
|---|---|---|---|---|
| `pub-dha-msmr-202509.pdf` | (c) technical/scientific report set in two or more columns, federal authors | Defense Health Agency (Armed Forces Health Surveillance Division) | https://www.health.mil/Reference-Center/Reports/2025/09/01/MSMR-Vol-32-No-9-Sep-2025 | Series 2 of (c): the earliest MSMR issue of July-December 2025 whose kept pages hold only federally authored articles (July and August 2025 skipped for non-federal co-authors) |
| `pub-fema-drf-202509.pdf` | (d) financial report made mostly of tables | Federal Emergency Management Agency | https://www.fema.gov/sites/default/files/documents/fema_ocfo_disaster-relief-fund-report_102025.pdf | Series 1 of (d): the only DRF monthly report the FEMA listing dates in October 2025 (September 2025 report, October 23, 2025) |

No (a) or (b) file: both kinds are left out (see "How the rule resolved").

### Download record (2026-11-25, 08:47-08:52 UTC, plain curl with `--max-filesize` after a HEAD request, each file into its own empty folder under `.work/` first)

| file | served file sha256 | pages served | kept | file in this folder (sha256) |
|---|---|---|---|---|
| `pub-dha-msmr-202509.pdf` | `31e1ab2012b64db9bf5f4ca2757e0598cee78bdacc9a8b2fe1a8a0f6f0929ede` (4,199,552 bytes, InDesign / Adobe PDF Library 17, tagged) | 62 | pages 1-15 (cover, contents, the morbidity-burden report of pages 4-12, the first three pages of the hospitalizations report); page 16 starts with the subsection heading 'Most frequent diagnoses', so 15 is the largest k | `638338b1f77de1d57eaa0295b3fdecd1d3e183b703d920235be27529fd08aef3` (1,915,694 bytes, untagged after the cut) |
| `pub-fema-drf-202509.pdf` | `1c4e630a1069df3d7504c91ebe35644fb3becd8f5434826172e1164ac28539f6` (2,310,239 bytes, Last-Modified 23 Oct 2025, PScript5 / Acrobat Distiller 25 modified with iText 7.1.10, tagged) | 23 | pages 1-15 (front matter, sections I-II, Appendices A-C and the first page of Appendix D); page 16 repeats the Appendix D running head and date and starts new chart and table titles, as the table pages of the Reclamation file of `holdout5/` did, so 15 is the largest k at whose end a table ends (judgement; page 14 ends Appendix C) | `2792e6ea3322c2cb53e29cd87bf6325acc3b1ab524ea905f0a76be01588b2cba` (1,059,876 bytes, untagged after the cut) |

The page ranges were judged from 40 dpi contact sheets of all pages (headings and table titles only) and 90-110 dpi
renders of the pages around the cut. Both cuts were made with pypdf 7.1.1 (`uv run --with pypdf python3 -I
cut_pages.py <served.pdf> <out.pdf> 1 15`, a throwaway script: `PdfWriter.add_page` for each kept page plus the
document information dictionary, as in the earlier sets); two runs gave the same bytes. The served originals, the cut
copies, the July and August 2025 MSMR issues downloaded only for the author and page checks (sha256 `14a5ac0e...`,
2,102,742 bytes, and `1fa3fd90...`, 2,836,557 bytes), the listing pages and all renders were deleted after use; only the
kept files are in this folder.

## Generated documents

Written by `generate_holdout6.py` (deterministic; new content), run as `uv run --with python-docx --with openpyxl
--with python-pptx --with reportlab python3 -I holdout6/generate_holdout6.py` from the benchmark folder. Rule: one
ordinary business document per format, using features such documents commonly have; nothing was designed around any
converter's known strengths or weaknesses. The script's helpers (normalization, validation, read-back verification,
OOXML pinning) are copied from `holdout5/generate_holdout5.py`; the documents, layouts, data and checks are new
(fictitious hotel company 'Halcyon Harbor Hotels, Inc.' and its linen supplier; subjects not named for any file in the
records read here: an internal audit report, a labor-hours workbook, a renovation board update, a European utility
meter export, a work-order API response and an invoice). Running the script twice gave byte-identical files and answer
files (python-docx 1.2.0, openpyxl 3.1.5, python-pptx 1.0.2, lxml 6.1.3, reportlab 5.1.1, Python 3.14.6). The script also
checks the two public answer files against the same validation rules, the phrase rules below and their sha256 against
the files in this folder. Changes made while writing, because the script's own audit rules called for them: the CSV was
first named `gen-meter-readings.csv` and the PDF `gen-linen-invoice.pdf`; the rule that no check may occur in a
converter's file-name lines rejected the column header 'reading' and the heading 'INVOICE', so the files were renamed
`gen-utility-meters.csv` and `gen-linen-billing.pdf` (the rejected first outputs were deleted); the workbook's sheet
names were chosen so that no note contains them; the expected count of merged ranges in the check was corrected from 18
to 16 before the first complete run.

| file | what it is | sha256 |
|---|---|---|
| `gen-cash-audit.docx` | internal audit report: Title and Subtitle styles, a document-control table without a header row (first column bold and shaded), Heading 1/2 numbered by Word list numbering (numbers not typed) and an unnumbered last Heading 1, a bordered and shaded call-out paragraph with a bold label, a bulleted list, a hyperlink whose text differs from its address, a rating-scale table, a findings table with a repeated header row, two group-label rows merged across six columns, cells with a bold title paragraph plus text and cells with a two-item bulleted list, a '1)' numbered list, an Intense Quote paragraph, a landscape section with an eight-column results table and a bold total row, captions, an italic note, page header and footer | `efef87304409076157ea2d986644216d066408f16161dd32509d893b0f7159d7` |
| `gen-labor-hours.xlsx` | 3 sheets: a summary sheet with two tables side by side separated by an empty column (cross-sheet SUMIF and SUMPRODUCT formulas, month cells that are dates shown as 'Apr 2031', percentages), a detail sheet whose table starts in column B under a title and a note (two header rows, month headers that are dates shown as 'April 2031', groups merged across, headers merged down, region and hotel labels merged down over body rows, subtotal and total labels merged across three columns, row outline groups, frozen panes), and an Excel table object with currency formats, a formula column and dates shown as 'April 1, 2031'; 71 formula cells saved with computed values | `7e57fe6608335ef1a1778f551961d416bfbdaee67060182b054f5aafd074e01f` |
| `gen-renovation-update.pptx` | 8-slide board update: title slide, agenda numbered by PowerPoint auto-numbering, a Title Only slide with a group shape of three two-paragraph tiles and a free text box, a native 7-column table with a total row and a footnote text box, a Two Content slide with two-level bullets in both placeholders, a Content with Caption slide, a Section Header slide, a bullet ending in a hyperlink run, speaker notes on 3 slides | `7a36ff6a76d25a85f04a9d16ad283df9f8119c17301e3aae01d107029f4831ce` |
| `gen-utility-meters.csv` | European utility export: UTF-8 with a byte order mark, semicolon delimiter, CRLF record ends, minimal quoting (3 quoted fields: two with a semicolon, one with doubled quotes), decimal commas, dd.mm.yyyy dates, empty fields, non-ASCII site names and the unit 'm³'; 36 records | `2c973bc92798387eaf8143302ca928d37a83d5d6e6211c2f7830cf97a2865bb0` |
| `gen-work-orders.json` | minified work-order API response (one line, no final newline): meta, an array of 10 orders and links; nested objects, arrays of objects and numbers, empty arrays, nulls, booleans, a negative integer, decimals, keys that differ between records, escaped quotes, non-ASCII names, ISO timestamps | `89453cfb4607017c166bbffb7edb89e199e3675c2bdb499606539e88f8c5f229` |
| `gen-linen-billing.pdf` | ReportLab invoice, 2 pages: letterhead beside a large 'INVOICE' title over a ruled details table (borderless layout table), bill-to and ship-to blocks side by side, a 25-row line-item table with wrapped descriptions continuing on page 2 with its header repeated, a right-aligned totals table with a negative amount in parentheses, two headings, a payment table, a numbered list with a lettered sub-item, a dashed cut line and a remittance slip table with an empty cell, running footer ('Page N of 2') | `e3594f15a1716fce30d5bd0b08a8ffc1709144a6ab930f1c2da821b822c5f556` |

`generate_holdout6.py` itself: sha256 `6add3a32d39bf3702c990e1ece83057f751817716dd0c9db7aac4b5b83c6533e` at freeze.

## Checks per file

| file | must_contain | ordered | headings | tables (non-empty cells) | noise | absent |
|---|---|---|---|---|---|---|
| `gen-cash-audit.docx` | 20 | 7 | 5 | 4 (104) | 0 | 0 |
| `gen-labor-hours.xlsx` | 17 | 5 | 0 | 4 (211) | 0 | 0 |
| `gen-renovation-update.pptx` | 21 | 7 | 8 | 1 (48) | 0 | 0 |
| `gen-utility-meters.csv` | 15 | 5 | 0 | 1 (376) | 0 | 0 |
| `gen-work-orders.json` | 15 | 5 | 0 | 0 | 0 | 0 |
| `gen-linen-billing.pdf` | 15 | 8 | 3 | 5 (199) | 1 | 0 |
| `pub-dha-msmr-202509.pdf` | 58 | 8 | 18 | 2 (408; one PARTIAL: header rows, Total and two of the condition groups of a four-page table; Table 1 complete) | 2 | 14 |
| `pub-fema-drf-202509.pdf` | 52 | 8 | 5 | 8 (346; one PARTIAL: the first ten rows of the 14-column Appendix B table; the other seven complete) | 0 | 0 |

## Answers and audit

- Public PDFs: answers typed from the rendered pages (pdftoppm: 100-160 dpi full pages; 200-400 dpi crops of every
  transcribed table cell and of the small landscape labels, read as images). Every transcribed table was checked with
  the arithmetic the document implies, by a throwaway script or by hand (not committed): FEMA Appendix A: every subtotal
  and balance in all three columns and Total = Major Declarations + Base, exactly; Appendix B block: Major Declarations
  + Base = Total Available in all 13 columns, and Total Available = beginning balance plus the rows between them in 10
  of 12 months (October-24 and January-25 differ by 10 from that sum; both re-read at 400 dpi and kept as printed), its
  Total column equal to the Appendix A balance; Appendix C (MARIA, COVID-19): every row and column total, exactly;
  Appendix D: every Total, exactly, and the obligations of Sandy, Harvey, Irma, Maria and COVID-19 equal Appendix C's
  totals. MSMR: the injury and mental-disorder rows sum to their group rows, exactly; in Table 1 the 18 category counts
  of each year add up to the Total row, every rate equals count / (total / total rate) within 0.06 and every rank follows
  the counts. A second pass re-read every phrase, anchor and heading against new renders (FEMA page 5 and the landscape
  labels at 150-250 dpi; MSMR pages 2, 4, 5, 7, 13 and 15 at 150 dpi). No string was found misread; one change came out
  of that pass: the MSMR serif body font sets a 'Th' ligature at the start of 'This', 'The', 'There' and 'These', a
  glyph without a Unicode code point of its own, so 14 phrases and 4 anchors were cut to begin after that word (e.g.
  'annual summary report of ...'). The phrase count in the MSMR notes was corrected (56 to 58) when the file was first
  written.
- Generated files: `generate_holdout6.py` reads each DOCX/XLSX/PPTX/CSV/JSON file back (heading styles and their list
  numbering, list items, bulleted cell paragraphs, merged cells, section orientation, the hyperlink target, cached formula
  values, merged ranges, the table object, outline levels and frozen panes, auto-numbering, the group shape and its
  tiles, slide layouts, the hyperlink run, speaker notes, the CSV's byte order mark, CRLF ends and quoting, the JSON's
  minified form) and verifies every check against it, plus the audit rules of the earlier sets (no file name or
  converter-added text in a check, prose phrases of 6+ words that occur once, data-file items that are whole fields not
  inside another field, ordered anchors unique, in reading order and never from speaker notes). The generated PDF is not
  read back with any text extractor: its checks come from the generator's data in reading order, its 2 pages were
  rendered (70 dpi) and looked at, and `pdffonts` was used once to confirm its font names (Helvetica, Helvetica-Bold,
  Helvetica-Oblique; Type 1, WinAnsi, not embedded).
- `score.mjs` was not run. Its `validateGroundTruth` rules (errors and warnings) are re-implemented in
  `generate_holdout6.py` (`validate_ground_truth`); all eight answer files pass them with no error and no warning, and
  the sha256 in every answer file matches the file in this folder. The script also checks that no public must_contain
  phrase or ordered anchor holds a non-ASCII character, a quotation mark, an apostrophe or an in-word hyphen, and that
  no public heading holds a dash, hyphen or quote.

## Known limits (also in each file's notes)

- **Two public files instead of four.** Kinds (a) and (b) are left out under the rule and its two amendments; most of
  their series had nothing in October 2025 (the month of the lapse in appropriations), two hosts refused plain curl and
  one (`www.lre.usace.army.mil`) could not be reached from the reviewer's machine (see "How the rule resolved"). Kind (c)
  is present (`holdout5/SELECTION.md` records it as left out of the three sets before this one), from series 2 of its
  list, because series 1's host could not be reached from the reviewer's machine.
- The PDF text layers were never read, so invisible text-layer content is not checked, and characters whose code point
  cannot be seen are avoided in phrases, anchors and headings. Where table cells or absent entries must contain them,
  the assumption is stated and applies to every tool alike: the zero dashes of FEMA Appendix C, the hyphens of
  'Full-Year' and the month headers ('October-24') and the MSMR hyphens ('COVID-19', 'non-drug') as ASCII hyphen-minus;
  the MSMR ICD-10 code ranges as EN DASH U+2013; the MSMR line-end hyphens of the 14 absent entries as ASCII hyphen-minus;
  the MSMR 'fi', 'ff' and 'ffi' ligatures as letters or U+FB00-FB06. Footnote markers printed as superscripts after a
  table label are written after one space ('Obligations (5)', 'Rank d'); a dollar sign printed at the left of an amount
  cell is written before the amount with one space ('$ 2,033').
- FEMA: the four landscape pages of Appendix B by catastrophic disaster, the activity rows of Appendix B and four of
  the six Appendix C sub-tables are not transcribed; chart text is not checked; the small appendix running heads are not
  headings. MSMR: the multi-page table is checked for its first page only; the cover's article list, the figures and
  the photographs are not checked; the second report is cut after its third page.
- Noise maxima: every visible running footer that occurs nowhere in the body has max 1 (one kept copy is tolerated),
  as in `holdout5/`. Applies to every tool alike.

## Disclosures

- No converter, text extractor or OCR was run on any file in this folder, and nothing about how a converter handles
  any of these documents was looked up. No git command was run. Nothing was written to `/tmp` by the reviewer (the
  ephemeral environments of `uv` live in its own cache outside the benchmark folder); temporary files were kept in
  `holdout6/.work/` and deleted at the end.
- Read before writing the rule (format and method only): `SCORING.md`, `score.mjs`, `holdout5/SELECTION.md`,
  `holdout5/generate_holdout5.py` and three `holdout5` answer files (NASA in full; CFTC and Reclamation in part).
  `SCORING.md` reports earlier results, including areas where each tool lost points; see rule 5. `holdout5/SELECTION.md`
  named the MSMR, Medical Journal and Fishery Bulletin listings and what it found there (disclosed in the rule).
  `README.md`, `results/`, `corpus/`, `holdout/`, `holdout2/`, `holdout3/`, `holdout4/`, the `holdout5` documents and
  the converter code were not opened.
- Deviations from the rule as first written: (1) Amendment 1 added two series for kind (a) after the three listed ones
  had failed; both failed too, so it changed nothing and kind (a) is left out. (2) Amendment 2 added two series for kind
  (b) after the three listed ones had failed; both failed too, so kind (b) is left out. (3) Name-resolution failures for
  `army.mil` hosts on the reviewer's machine were treated like a refusal of plain curl (no workaround), which decided
  series (a) 1 and (c) 1; the maintainer may re-run them from another machine (see "How the rule resolved"). (4)
  Judgements: the CMS successor report taken as the named monthly enrollment report (no October 2025 issue either way);
  the MSMR author condition read from the 'Author Affiliations' paragraphs at the end of each article instead of the
  first page (where MSMR prints none); the unsigned AFHSD reports of the September issue counted as federally authored;
  for the August issue only k >= 12 was established (enough for the author condition); the FEMA cut at 15 after a page
  of charts with data tables (page 16 starts new chart and table titles under the repeated running head). (5) Dates:
  MSMR from the archive's URL dates (2025/07/01, ...); FEMA from the listing; the Ginnie Mae dates could not be learned
  (Last-Modified is a migration date) but every candidate failed on size.
- Incidental reading beyond titles and dates: the listings carried descriptions (CMS, FRTIB, VBA, FEMA, GSA, BOP) and,
  for MSMR, the article titles of every issue; the 40 dpi contact sheets used for the page ranges showed every page of
  the July, August and September 2025 MSMR issues and of the FEMA report, including pages not kept; checking
  affiliations meant rendering whole pages at 90 dpi (July pages 7 and 12; September pages 4, 11, 12, 13 and 20) or
  crops (August pages 15 and 16), which showed the text around the affiliation lines; `pdfinfo` printed document
  metadata. None of this affected a pick.
- Slips: (1) the July 2025 MSMR issue link served the PDF itself (HTTP 200, `Content-Type: application/pdf`, no size
  check first); a script written to read an HTML page printed about 1.8 KB of the file's raw bytes (its XMP metadata:
  the article titles already shown in the listing, dates, producer, and compressed stream bytes). No text layer was
  extracted, and the file (2,102,742 bytes) was under 5 MB. (2) One diagnostic request with curl `--resolve` was made to
  the address a direct DNS query gave for `www.lre.usace.army.mil` (TLS failed; see "How the rule resolved"); it is the
  only request not made with plain curl.
