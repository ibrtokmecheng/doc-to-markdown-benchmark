#!/usr/bin/env python3
"""Generate the synthetic part of the SIXTH held-out doc-to-markdown test set (holdout6/).

Writes six ordinary business documents to holdout6/ and one ground-truth JSON per document to
holdout6/ground-truth/<file>.json (same schema as the earlier sets, checked by score.mjs):

    gen-cash-audit.docx        Word internal audit report: Title and Subtitle styles, a document-control table without a
                               header row (first column bold and shaded), Heading 1 / Heading 2 paragraphs numbered by
                               Word list numbering (the numbers are not typed), a shaded and bordered call-out paragraph,
                               a bulleted list, a hyperlink whose text differs from its address, a rating-scale table, a
                               findings table with a repeated header row, group-label rows merged across all six columns,
                               cells holding two paragraphs (bold title + text) and cells holding a two-item bulleted list,
                               a second numbered list, an Intense Quote paragraph, a landscape section with an eight-column
                               results table and a total row, captions, an italic note, page header and footer.
    gen-labor-hours.xlsx       Workbook with three sheets: a summary sheet with two tables side by side separated by an
                               empty column (cross-sheet SUMIF and SUMPRODUCT formulas, month labels that are real dates
                               shown as 'Apr 2031', percentages), a detail sheet whose table starts in column B under a
                               title and a note, two header rows (four month or quarter groups merged across two columns,
                               three headers merged down, month headers that are real dates shown as 'April 2031'), region
                               and hotel labels merged down over their body rows, subtotal and total rows with labels
                               merged across three columns, row outline groups, frozen panes; and an Excel table object
                               (ListObject) with currency formats, a formula column and dates shown as 'April 1, 2031'.
    gen-renovation-update.pptx Eight-slide board update: title slide, an agenda numbered by PowerPoint auto-numbering, a
                               Title Only slide with a group shape of three tiles (two paragraphs each) and a free text
                               box, a native seven-column table with a total row and a footnote text box, a Two Content
                               slide with two-level bullets in both placeholders, a Content with Caption slide, a Section
                               Header slide, a bullet with a hyperlink run, speaker notes on three slides.
    gen-utility-meters.csv     European utility export: UTF-8 with a byte order mark, semicolon delimiter, CRLF record
                               ends, minimal quoting (only fields with a semicolon or a quote are quoted, doubled quotes),
                               decimal commas, dd.mm.yyyy dates, empty fields, non-ASCII site names and the unit 'm³'.
    gen-work-orders.json       Maintenance work-order API response written minified (no whitespace, one line, no final
                               newline): a meta object, an array of 10 work orders with nested objects and arrays of
                               objects, keys that differ between records, nulls, booleans, decimals, escaped quotes,
                               non-ASCII names, ISO timestamps, a links object with a null.
    gen-linen-billing.pdf      ReportLab two-page invoice: letterhead beside a large 'INVOICE' title and a ruled details
                               table, bill-to and ship-to blocks side by side, a line-item table with wrapped description
                               cells that continues on page 2 with its header repeated, a right-aligned totals table, two
                               section headings with a payment table and a numbered list with a lettered sub-item, a
                               dashed cut line above a remittance slip table, running footer ('Page N of 2').

The content is new (not reused from holdout5/; the generators of the sets before it were not opened). Everything is fixed
in this file: no randomness, no clock. Every ground-truth item is derived from the same Python data that is written into
the document. After writing, the DOCX, XLSX, PPTX, CSV and JSON files are read back (python-docx, openpyxl, python-pptx,
csv, json) and every check is verified against the read-back text, with the audit rules of the earlier sets (no file
name or converter-added text in a check; prose phrases of at least 6 words that occur once; data-file items are whole,
distinctive fields; ordered anchors unique and in reading order, never from speaker notes). The PDF is NOT read back with
any text extractor (blind protocol): its checks are verified against the generator's own data in reading order, and its
pages were only rendered to images (pdftoppm) and looked at. Every answer file, including the two public ones, is
checked against the validation rules of score.mjs validateGroundTruth (re-implemented below; score.mjs is not run). Any
mismatch aborts with exit status 1.

No converter (PackForAI, MarkItDown or other) is run here or was run while writing the answers.

Run from the benchmark folder (ephemeral environment, no global installs):

    uv run --with python-docx --with openpyxl --with python-pptx --with reportlab \
        python3 -I holdout6/generate_holdout6.py

Only the twelve files named above are written. Same library versions => byte-identical files (ZIP entry times,
document dates and the PDF's creation date and ID are pinned).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
import unicodedata
import zipfile
from decimal import ROUND_HALF_UP, Decimal
from importlib import metadata
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import docx
import openpyxl
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table as XTable, TableStyleInfo
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.util import Inches
from pptx.util import Pt as PPt
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, ListFlowable, ListItem, Paragraph as RLParagraph, SimpleDocTemplate, \
    Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground-truth"
ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)
LICENSE = ("Synthetic document written for the sixth held-out benchmark set and generated by "
           "holdout6/generate_holdout6.py; no third-party material. All organisations, people, addresses, phone "
           "numbers, e-mail domains, URLs and figures are fictitious.")
LIBS = ("python-docx", "openpyxl", "python-pptx", "lxml", "reportlab")
MIN_PHRASE_WORDS = 6
COMPANY = "Halcyon Harbor Hotels, Inc."
CHECK_KEYS = ("must_contain", "ordered", "headings", "tables", "noise", "absent")
FORMATS = ("pdf", "docx", "xlsx", "pptx", "csv", "json")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def lib_versions() -> str:
    return ", ".join(f"{n} {metadata.version(n)}" for n in LIBS) + f", Python {sys.version.split()[0]}"


# ---------------------------------------------------------------------------
# Matching rules (normalize() of score.mjs) and self-checks (copied from holdout5/generate_holdout5.py)
# ---------------------------------------------------------------------------

def normalize(text) -> str:
    t = unicodedata.normalize("NFKC", str(text)).lower()
    t = re.sub(r"[*_\\`]", "", t)
    t = t.replace("|", " ")
    t = unicodedata.normalize("NFKC", t)
    return re.sub(r"[\s﻿]+", " ", t).strip()


class CheckError(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise CheckError(msg)


def table_cells(checks):
    return [c for t in checks["tables"] for row in t["rows"] for c in row if normalize(c)]


def validate_ground_truth(gt, gt_name):
    """The error and warning rules of validateGroundTruth in score.mjs 1.2.0, re-implemented (score.mjs not run)."""
    errors, warnings = [], []
    if not isinstance(gt, dict):
        return ["not an object"], []
    if not isinstance(gt.get("file"), str) or not gt["file"].strip() or re.search(r"[\\/\0]", gt["file"]) \
            or gt["file"] in (".", ".."):
        errors.append("file")
    elif gt["file"] + ".json" != gt_name:
        warnings.append("file name")
    if gt.get("format") not in FORMATS:
        errors.append("format")
    elif Path(gt["file"]).suffix[1:].lower() != gt["format"]:
        warnings.append("extension")
    if gt.get("origin") not in ("generated", "public"):
        warnings.append("origin")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(gt.get("sha256", ""))):
        warnings.append("sha256")
    c = gt.get("checks")
    if not isinstance(c, dict):
        return errors + ["checks"], warnings
    for key in CHECK_KEYS:
        if key not in c:
            errors.append(f"checks.{key} missing")
    for key in c:
        if key not in CHECK_KEYS:
            warnings.append(f"unknown check {key}")
    for key in ("must_contain", "ordered", "headings", "absent"):
        seen = set()
        if not isinstance(c.get(key), list):
            errors.append(f"{key} is not an array")
            continue
        for s in c[key]:
            if not isinstance(s, str) or normalize(s) == "":
                errors.append(f"{key}: empty or not a string")
                continue
            n = normalize(s)
            if n in seen:
                (errors if key == "ordered" else warnings if key != "headings" else []).append(f"{key} duplicate {s!r}")
            seen.add(n)
    o = c["ordered"]
    if o and not 4 <= len(o) <= 8:
        warnings.append("ordered count")
    for a in o:
        for b in o:
            if normalize(a) != normalize(b) and normalize(a) in normalize(b):
                warnings.append(f"anchor {a!r} inside {b!r}")
    for t in c["tables"]:
        if not isinstance(t, dict):
            errors.append("table not an object")
            continue
        if not isinstance(t.get("name"), str) or not t["name"].strip():
            warnings.append("table name")
        rows = t.get("rows")
        if not isinstance(rows, list) or not rows or any(not isinstance(r, list) or not r
                                                         or any(not isinstance(x, str) for x in r) for r in rows):
            errors.append("table rows")
            continue
        if len({len(r) for r in rows}) > 1:
            warnings.append(f"table {t['name'][:40]!r} has rows of different lengths")
        if not any(normalize(x) for r in rows for x in r):
            errors.append("table without a non-empty cell")
        if len(rows) < 2:
            warnings.append("table with only a header row")
    for n in c["noise"]:
        if not isinstance(n, dict) or not isinstance(n.get("max"), int) or isinstance(n.get("max"), bool) \
                or n["max"] < 0 or not isinstance(n.get("text"), str) or not normalize(n["text"]):
            errors.append("noise entry")
        elif len(normalize(n["text"])) < 3:
            warnings.append("short noise text")
    if not errors:
        required = (list(c["must_contain"]) + list(c["ordered"]) + list(c["headings"]) + table_cells(c))
        for a in c["absent"]:
            for s in required:
                if normalize(a) in normalize(s):
                    errors.append(f"absent {a!r} inside required {s!r}")
        for n in c["noise"]:
            if n["max"] == 0:
                for s in required:
                    if normalize(n["text"]) in normalize(s):
                        errors.append(f"noise {n['text']!r} (max 0) inside required {s!r}")
    return errors, warnings


def verify(name, fmt, gt, reading_text, *, body_text=None, headings_found=None, tables_found=None, fields=None,
           furniture=None):
    """Checks a ground truth against the text of the written file.

    reading_text: all text a reader sees, in reading order (body, then speaker notes).
    body_text: the main text without notes; ordered anchors must come from it (default: reading_text).
    fields: for data formats, every key, value or cell as displayed (see the audit rules in the module doc).
    furniture: page furniture text (running header/footer lines), for the noise checks of the PDF.
    """
    c = gt["checks"]
    norm = normalize(reading_text)
    body = normalize(body_text if body_text is not None else reading_text)
    for p in c["must_contain"]:
        require(normalize(p) in norm, f"{name}: must_contain not found: {p!r}")
    require(4 <= len(c["ordered"]) <= 8, f"{name}: ordered must hold 4-8 anchors")
    positions = []
    for a in c["ordered"]:
        na = normalize(a)
        require(norm.count(na) == 1, f"{name}: ordered anchor {a!r} occurs {norm.count(na)} times (must be 1)")
        require(na in body, f"{name}: ordered anchor {a!r} is not main text")
        positions.append(norm.index(na))
        for b in c["ordered"]:
            require(a == b or na not in normalize(b), f"{name}: anchor {a!r} occurs inside anchor {b!r}")
    require(positions == sorted(positions), f"{name}: ordered anchors are not in reading order")
    for h in c["headings"]:
        require(normalize(h) in norm, f"{name}: heading not in text: {h!r}")
    if headings_found is not None:
        require(list(headings_found) == list(c["headings"]),
                f"{name}: headings read back {headings_found!r} != ground truth {c['headings']!r}")
    for cell in table_cells(c):
        require(normalize(cell) in norm, f"{name}: table cell not in text: {cell!r}")
    if tables_found is not None:
        require([t["rows"] for t in c["tables"]] == tables_found, f"{name}: tables read back differ")
    required = list(c["must_contain"]) + list(c["ordered"]) + list(c["headings"]) + table_cells(c)
    for a in c["absent"]:
        require(normalize(a) not in norm, f"{name}: absent {a!r} occurs in the text")
        require(all(normalize(a) not in normalize(s) for s in required), f"{name}: absent {a!r} inside required text")
    for n in c["noise"]:
        nt = normalize(n["text"])
        require(nt not in body, f"{name}: noise text {n['text']!r} also occurs in the body")
        require(furniture is not None and nt in normalize(furniture), f"{name}: noise text {n['text']!r} not furniture")
        require(all(nt not in normalize(s) for s in required), f"{name}: noise {n['text']!r} inside required text")
    # Audit rules: no file name and no converter-added line can satisfy a check.
    stem = normalize(Path(name).stem)
    added = normalize(f"# {name}\nSource file: {name}\nSource type: {fmt}\nSource: {name}")
    every = required + list(c["absent"]) + [n["text"] for n in c["noise"]] + [t["name"] for t in c["tables"]]
    for s in every:
        require(stem not in normalize(s), f"{name}: check text {s!r} contains the file name")
    for s in required:
        require(normalize(s) not in added, f"{name}: check text {s!r} occurs in converter-added lines")
    if fields is None:
        for p in c["must_contain"]:
            require(len(p.split()) >= MIN_PHRASE_WORDS, f"{name}: must_contain {p!r} has < {MIN_PHRASE_WORDS} words")
            require(norm.count(normalize(p)) == 1, f"{name}: must_contain {p!r} occurs {norm.count(normalize(p))}x")
    else:
        nf = [normalize(f) for f in fields if normalize(f)]
        for p in list(c["must_contain"]) + list(c["ordered"]):
            n = normalize(p)
            require(n in nf, f"{name}: {p!r} is not one complete field")
            inside = sorted({f for f in nf if n in f and f != n})
            require(not inside, f"{name}: {p!r} also occurs inside other fields {inside[:3]}")
    errors, warnings = validate_ground_truth(gt, f"{name}.json")
    require(not errors and not warnings, f"{name}: validateGroundTruth rules: {errors + warnings}")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin_ooxml(path: Path, created: str, modified: str, patch=None) -> None:
    """Rewrites an OOXML zip with fixed entry times and core dates; patch(name, bytes) may rewrite a part."""
    with zipfile.ZipFile(path) as zin:
        entries = [(info.filename, zin.read(info.filename)) for info in zin.infolist()]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zout:
        for name, data in entries:
            if name == "docProps/core.xml":
                text = data.decode("utf-8")
                for tag, when in (("dcterms:created", created), ("dcterms:modified", modified)):
                    text = re.sub(rf"(<{tag}\b[^>]*>)[^<]*(</{tag}>)", rf"\g<1>{when}\g<2>", text)
                data = text.encode("utf-8")
            if patch is not None:
                data = patch(name, data)
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0
            zout.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    path.write_bytes(buf.getvalue())


def write_ground_truth(path: Path, *, fmt, title, pages_or_sheets, stresses, checks, notes):
    gt = {
        "file": path.name,
        "format": fmt,
        "origin": "generated",
        "source_url": None,
        "title": title,
        "publisher": None,
        "license": LICENSE,
        "sha256": sha256_of(path),
        "pages_or_sheets": pages_or_sheets,
        "stresses": stresses,
        "checks": checks,
        "notes": notes + f" Generated by holdout6/generate_holdout6.py with {lib_versions()}; no converter was run "
                         "on the file before these answers were frozen.",
    }
    GT_DIR.mkdir(parents=True, exist_ok=True)
    (GT_DIR / f"{path.name}.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return gt


def money(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pct1(d: Decimal) -> Decimal:
    """Rounds a fraction to one decimal of a percent; refuses values on a rounding boundary."""
    scaled = d * 1000
    frac = abs(scaled - scaled.to_integral_value(rounding="ROUND_FLOOR"))
    require(abs(frac - Decimal("0.5")) > Decimal("1e-6"), f"percent {d} on a rounding boundary")
    return (d * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def pct0(d: Decimal) -> Decimal:
    """Rounds a fraction to a whole percent; refuses values on a rounding boundary."""
    scaled = d * 100
    frac = abs(scaled - scaled.to_integral_value(rounding="ROUND_FLOOR"))
    require(abs(frac - Decimal("0.5")) > Decimal("1e-6"), f"percent {d} on a rounding boundary")
    return scaled.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def usd(d: Decimal, parens=False) -> str:
    q = money(d)
    if q < 0:
        require(parens, "negative amount without parentheses")
        return f"({-q:,.2f})"
    return f"{q:,.2f}"


# ===========================================================================
# 1. gen-cash-audit.docx
# ===========================================================================

DOCX_TITLE = "Internal Audit Report: Front Desk Cash Handling"
DOCX_SUBTITLE = "Halcyon Harbor Hotels, Inc., Internal Audit Department, final report issued June 18, 2031"
DOCX_HEADER = "Halcyon Harbor Hotels, Inc. | Internal Audit"
DOCX_FOOTER = "Confidential: prepared for the Audit Committee and hotel management"
DOCX_LINK_TEXT = "Audit IA-2031-07 test plan"
DOCX_LINK_URL = "https://intranet.halcyon-harbor.example/audit/ia-2031-07/test-plan"
DOCX_CONTROL = [
    ["Audit number", "IA-2031-07"],
    ["Audit period", "January 1 to March 31, 2031"],
    ["Hotels visited", "Seattle Waterfront, Portland Pearl, Tacoma Narrows"],
    ["Lead auditor", "Renata Oyelaran, CIA"],
    ["Distribution", "Audit Committee; Chief Financial Officer; hotel general managers"],
]
DOCX_RATINGS = [
    ["Rating", "Meaning", "Expected action"],
    ["High", "A control is missing or does not work, and a loss is likely", "Correct within 30 days"],
    ["Medium", "A control works only part of the time", "Correct within 90 days"],
    ["Low", "A minor weakness with little exposure", "Correct at the next policy review"],
]
# Findings: (group label) or (no., title, text, rating, response (str or list of bullet texts), owner, due date)
DOCX_FINDINGS = [
    "Cash drawers and safes",
    ("1", "Blind counts not performed",
     "At two hotels the closing clerk saw the expected drawer balance before counting.", "High",
     ["Remove the expected balance from the closing screen", "Train all clerks on blind counts by August 15"],
     "Director of Rooms", "August 15, 2031"),
    ("2", "Safe key log incomplete", "The key log for the back office safe had no entries for 9 of 90 days tested.",
     "Medium", "A daily sign-off of the key log has been added to the night audit checklist.", "Hotel controllers",
     "July 31, 2031"),
    ("3", "Change fund over the approved limit",
     "The Portland Pearl change fund held $2,400 against an approved limit of $1,500.", "Low",
     "The excess was deposited on April 2 and the limit was confirmed in writing.", "General manager, Portland Pearl",
     "Completed"),
    "Deposits and reconciliation",
    ("4", "Late bank deposits", "Deposits were made more than one business day after receipt in 23 of 156 cases.",
     "High", ["Use the armored car pickup on Saturdays", "Report late deposits weekly to the area controller"],
     "Area controller", "September 30, 2031"),
    ("5", "Unexplained variances", "Variances above $50 were cleared without a written explanation in 7 cases.",
     "Medium", "Variances above $25 now require a written explanation signed by the controller.",
     "Hotel controllers", "June 30, 2031"),
    ("6", "Duplicate deposit slip numbers", "The same slip number was used twice at Tacoma Narrows in February.", "Low",
     "Numbered deposit slip books are now issued by the area office.", "Area controller", "November 30, 2031"),
]
DOCX_DEPOSITS = [  # hotel, tested, on time, missing slip, net variance, largest single variance, result
    ("Seattle Waterfront", 58, 47, 1, "-312.40", "184.10", "Needs improvement"),
    ("Portland Pearl", 52, 47, 0, "96.25", "61.00", "Satisfactory"),
    ("Tacoma Narrows", 46, 39, 2, "-1045.80", "870.00", "Needs improvement"),
]


def docx_findings_rows():
    rows = [["No.", "Finding", "Rating", "Management response", "Owner", "Due date"]]
    for f in DOCX_FINDINGS:
        if isinstance(f, str):
            rows.append([f, "", "", "", "", ""])
        else:
            no, title, text, rating, resp, owner, due = f
            rows.append([no, f"{title}\n{text}", rating, resp if isinstance(resp, str) else "\n".join(resp), owner,
                         due])
    return rows


def docx_deposit_rows():
    rows = [["Hotel", "Deposits tested", "On time", "Late", "Missing slip", "Net variance (USD)",
             "Largest single variance (USD)", "Result"]]
    tot = [0, 0, 0, 0, Decimal(0)]
    for hotel, tested, on_time, missing, net, largest, result in DOCX_DEPOSITS:
        late = tested - on_time
        rows.append([hotel, str(tested), str(on_time), str(late), str(missing), usd(Decimal(net), parens=True),
                     usd(Decimal(largest)), result])
        tot = [tot[0] + tested, tot[1] + on_time, tot[2] + late, tot[3] + missing, tot[4] + Decimal(net)]
    rows.append(["Total", str(tot[0]), str(tot[1]), str(tot[2]), str(tot[3]), usd(tot[4], parens=True), "", ""])
    require(tot[0] == 156 and tot[2] == 23, "docx: deposit totals differ from finding 4")
    highs = sum(1 for f in DOCX_FINDINGS if not isinstance(f, str) and f[3] == "High")
    require(highs == 2 and sum(1 for f in DOCX_FINDINGS if not isinstance(f, str)) == 6, "docx: finding counts")
    return rows


DOCX_T_FINDINGS = docx_findings_rows()
DOCX_T_DEPOSITS = docx_deposit_rows()
DOCX_CALLOUT = [("Overall rating: ", "b"), ("Needs improvement. Two of the six findings are rated high.", "")]
DOCX_BLOCKS = [
    ("title", DOCX_TITLE),
    ("subtitle", DOCX_SUBTITLE),
    ("table", "control"),
    ("h1", "Executive Summary"),
    ("para", [("Internal Audit reviewed how front desk cash is received, counted, stored and deposited at three hotels "
               "during the first quarter of 2031.", "")]),
    ("callout", DOCX_CALLOUT),
    ("para", [("Management agreed with every finding and has set target dates for all corrective actions, the last of "
               "them in November 2031.", "")]),
    ("h1", "Scope and Approach"),
    ("para", [("The audit covered the following procedures at each hotel:", "")]),
    ("bullet", "Opening and closing counts of each cash drawer"),
    ("bullet", "Access to the back office safe and its key log"),
    ("bullet", "Preparation and timeliness of bank deposits"),
    ("bullet", "Reconciliation of deposits to the property management system"),
    ("linkpara", [("The detailed test steps are described in the ", ""), (DOCX_LINK_TEXT, "link"),
                  (", which is available to hotel controllers.", "")]),
    ("h1", "Findings"),
    ("para", [("Each finding is rated using the scale in Table 1.", "")]),
    ("caption", "Table 1. Rating scale"),
    ("table", "ratings"),
    ("caption", "Table 2. Findings and management responses"),
    ("table", "findings"),
    ("h2", "Repeat Findings from 2030"),
    ("para", [("Two findings from the 2030 audit were found again:", "")]),
    ("number", "Blind counts were not performed at the Seattle Waterfront hotel."),
    ("number", "Late deposits exceeded the target of 5 percent of all deposits."),
    ("quote", "Management response: we accept the findings and will report progress to the Audit Committee every "
              "quarter until all actions are closed."),
    ("section", "landscape"),
    ("h1x", "Appendix: Deposit Testing Results"),
    ("para", [("Deposits tested from January 1 to March 31, 2031, by hotel.", "")]),
    ("para", [("Variances are the net difference between each deposit and the system record.", "")]),
    ("caption", "Table 3. Deposit testing results by hotel"),
    ("table", "deposits"),
    ("note", "Note: Negative variances, shown in parentheses, mean the deposit was smaller than the system record."),
]
DOCX_TABLES = {"control": DOCX_CONTROL, "ratings": DOCX_RATINGS, "findings": DOCX_T_FINDINGS,
               "deposits": DOCX_T_DEPOSITS}
DOCX_MUST = [
    DOCX_SUBTITLE,
    "Internal Audit reviewed how front desk cash is received, counted, stored and deposited at three hotels during "
    "the first quarter of 2031.",
    "Overall rating: Needs improvement. Two of the six findings are rated high.",
    "Management agreed with every finding and has set target dates for all corrective actions, the last of them in "
    "November 2031.",
    "The audit covered the following procedures at each hotel:",
    "Opening and closing counts of each cash drawer",
    "Access to the back office safe and its key log",
    "Preparation and timeliness of bank deposits",
    "Reconciliation of deposits to the property management system",
    "The detailed test steps are described in the Audit IA-2031-07 test plan, which is available to hotel controllers.",
    "Each finding is rated using the scale in Table 1.",
    "Table 2. Findings and management responses",
    "Two findings from the 2030 audit were found again:",
    "Blind counts were not performed at the Seattle Waterfront hotel.",
    "Late deposits exceeded the target of 5 percent of all deposits.",
    "Management response: we accept the findings and will report progress to the Audit Committee every quarter until "
    "all actions are closed.",
    "Deposits tested from January 1 to March 31, 2031, by hotel.",
    "Variances are the net difference between each deposit and the system record.",
    "Table 3. Deposit testing results by hotel",
    "Note: Negative variances, shown in parentheses, mean the deposit was smaller than the system record.",
]
DOCX_ORDERED = [DOCX_TITLE, "Internal Audit reviewed how front desk cash is received",
                "Access to the back office safe", "Blind counts not performed", "Duplicate deposit slip numbers",
                "Late deposits exceeded the target", "Largest single variance (USD)"]
DOCX_HEADINGS = ["Executive Summary", "Scope and Approach", "Findings", "Repeat Findings from 2030",
                 "Appendix: Deposit Testing Results"]
HEAD_NUM_ID, BULLET_NUM_ID, LIST_NUM_ID = 91, 92, 93


def _docx_numbering(document):
    """Heading numbering (1. / 1.1), a bullet list and a 1) list."""
    numbering = document.part.numbering_part.element
    lvl = ('<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text}"/>'
           '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{left}" w:hanging="{hang}"/></w:pPr>{rpr}</w:lvl>')
    sym = '<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr>'
    abstracts = [
        (HEAD_NUM_ID, lvl.format(i=0, fmt="decimal", text="%1.", left=432, hang=432, rpr="")
         + lvl.format(i=1, fmt="decimal", text="%1.%2", left=576, hang=576, rpr="")),
        (BULLET_NUM_ID, lvl.format(i=0, fmt="bullet", text="", left=720, hang=360, rpr=sym)),
        (LIST_NUM_ID, lvl.format(i=0, fmt="decimal", text="%1)", left=720, hang=360, rpr="")),
    ]
    first_num = numbering.find(qn("w:num"))
    for aid, levels in abstracts:
        el = parse_xml(f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{aid}"><w:multiLevelType '
                       f'w:val="hybridMultilevel"/>{levels}</w:abstractNum>')
        if first_num is not None:
            first_num.addprevious(el)
        else:
            numbering.append(el)
    for num_id in (HEAD_NUM_ID, BULLET_NUM_ID, LIST_NUM_ID):
        numbering.append(parse_xml(
            f'<w:num {nsdecls("w")} w:numId="{num_id}"><w:abstractNumId w:val="{num_id}"/></w:num>'))


def _set_num(p, num_id, level):
    num_pr = p._p.get_or_add_pPr().get_or_add_numPr()
    num_pr.get_or_add_ilvl().val = level
    num_pr.get_or_add_numId().val = num_id


def _shade(cell, fill):
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{fill}"/>'))


def _bold_runs(paragraph):
    for run in paragraph.runs:
        run.bold = True


def _docx_fill_cell(cell, value, *, bold=False, title_first=False, bullets=False):
    parts = value.split("\n")
    cell.text = parts[0]
    paragraphs = [cell.paragraphs[0]] + [cell.add_paragraph(t) for t in parts[1:]]
    for k, para in enumerate(paragraphs):
        if bold or (title_first and k == 0):
            _bold_runs(para)
        if bullets:
            _set_num(para, BULLET_NUM_ID, 0)


def _docx_table(document, key):
    grid = DOCX_TABLES[key]
    rows, cols = len(grid), len(grid[0])
    table = document.add_table(rows=rows, cols=cols)
    table.style = "Table Grid"
    if key == "findings":
        for ri, row in enumerate(grid):
            if ri > 0 and all(v == "" for v in row[1:]):
                table.cell(ri, 0).merge(table.cell(ri, cols - 1))
    if key == "control":
        for ri, (label, value) in enumerate(grid):
            _docx_fill_cell(table.cell(ri, 0), label, bold=True)
            _shade(table.cell(ri, 0), "E7EEF6")
            _docx_fill_cell(table.cell(ri, 1), value)
        return
    header = table.rows[0]._tr.get_or_add_trPr()
    header.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    responses = {f[0]: isinstance(f[4], list) for f in DOCX_FINDINGS if not isinstance(f, str)}
    for ri, row in enumerate(grid):
        group = key == "findings" and ri > 0 and all(v == "" for v in row[1:])
        last = key == "deposits" and ri == rows - 1
        for ci, value in enumerate(row):
            if group and ci > 0:
                continue
            cell = table.cell(ri, ci)
            if ri == 0:
                _docx_fill_cell(cell, value, bold=True)
                _shade(cell, "D9E2F3")
            elif group:
                _docx_fill_cell(cell, value, bold=True)
                _shade(cell, "F2F2F2")
            elif key == "findings" and ci == 1:
                _docx_fill_cell(cell, value, title_first=True)
            elif key == "findings" and ci == 3:
                _docx_fill_cell(cell, value, bullets=responses[row[0]])
            else:
                _docx_fill_cell(cell, value, bold=last)
                if key == "deposits" and 1 <= ci <= 6:
                    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _docx_hyperlink(paragraph, text, url):
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    paragraph._p.append(parse_xml(
        f'<w:hyperlink {nsdecls("w", "r")} r:id="{r_id}"><w:r><w:rPr><w:color w:val="0563C1"/>'
        f'<w:u w:val="single"/></w:rPr><w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r></w:hyperlink>'))


def build_docx(path: Path):
    document = docx.Document()
    styles = {s.name for s in document.styles}
    for needed in ("Title", "Subtitle", "Heading 1", "Heading 2", "List Paragraph", "Table Grid", "Caption",
                   "Intense Quote"):
        require(needed in styles, f"docx: template lacks style {needed!r}")
    _docx_numbering(document)
    section = document.sections[0]
    section.header.paragraphs[0].text = DOCX_HEADER
    section.footer.paragraphs[0].text = DOCX_FOOTER
    for kind, payload in DOCX_BLOCKS:
        if kind == "title":
            document.add_paragraph(payload, style="Title")
        elif kind == "subtitle":
            document.add_paragraph(payload, style="Subtitle")
        elif kind in ("h1", "h2", "h1x"):
            p = document.add_heading(payload, level=2 if kind == "h2" else 1)
            if kind != "h1x":
                _set_num(p, HEAD_NUM_ID, 1 if kind == "h2" else 0)
        elif kind == "caption":
            document.add_paragraph(payload, style="Caption")
        elif kind == "note":
            p = document.add_paragraph()
            run = p.add_run(payload)
            run.italic = True
            run.font.size = Pt(9)
        elif kind == "quote":
            document.add_paragraph(payload, style="Intense Quote")
        elif kind in ("para", "callout", "linkpara"):
            p = document.add_paragraph()
            for text, style in payload:
                if style == "link":
                    _docx_hyperlink(p, text, DOCX_LINK_URL)
                    continue
                run = p.add_run(text)
                run.bold = style == "b" or None
            if kind == "callout":
                ppr = p._p.get_or_add_pPr()
                side = '<w:{0} w:val="single" w:sz="8" w:space="4" w:color="2E5C8A"/>'
                ppr.append(parse_xml(f'<w:pBdr {nsdecls("w")}>' + "".join(side.format(s) for s in
                                                                         ("top", "left", "bottom", "right"))
                                     + '</w:pBdr>'))
                ppr.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="E7EEF6"/>'))
        elif kind in ("bullet", "number"):
            p = document.add_paragraph(payload, style="List Paragraph")
            _set_num(p, BULLET_NUM_ID if kind == "bullet" else LIST_NUM_ID, 0)
        elif kind == "table":
            _docx_table(document, payload)
        elif kind == "section":
            old = document.sections[-1]
            new = document.add_section(WD_SECTION.NEW_PAGE)
            new.orientation = WD_ORIENT.LANDSCAPE
            new.page_width, new.page_height = old.page_height, old.page_width
        else:
            raise ValueError(kind)
    for para in document.paragraphs:
        if para.style.name == "Normal":
            para.paragraph_format.space_after = Pt(6)
    props = document.core_properties
    props.title = DOCX_TITLE
    props.subject = "Front desk cash handling audit"
    props.author = "Internal Audit"
    props.last_modified_by = "Internal Audit"
    props.comments = ""
    props.keywords = ""
    props.category = ""
    props.revision = 4
    props.created = dt.datetime(2031, 5, 20, 9, 0, 0)
    props.modified = dt.datetime(2031, 6, 18, 16, 5, 0)
    document.save(path)
    pin_ooxml(path, "2031-05-20T09:00:00Z", "2031-06-18T16:05:00Z")


def _para_text(p_el):
    """Paragraph text with line breaks as '\\n' (hyperlink runs included)."""
    out = []
    for el in p_el.iter(qn("w:t"), qn("w:br"), qn("w:tab")):
        if el.tag == qn("w:t"):
            out.append(el.text or "")
        else:
            out.append("\n" if el.tag == qn("w:br") else "\t")
    return "".join(out)


def read_docx(path: Path):
    document = docx.Document(path)
    texts, headings, tables, items, cell_items, numbered_headings = [], [], [], [], 0, 0
    orientations = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, document)
            text = _para_text(child)
            texts.append(text)
            num_pr = child.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
            if p.style.name.startswith("Heading"):
                headings.append(text)
                numbered_headings += num_pr is not None
            elif num_pr is not None:
                items.append((int(num_pr.find(qn("w:numId")).get(qn("w:val"))), text))
            sect = child.find(f"{qn('w:pPr')}/{qn('w:sectPr')}")
            if sect is not None:
                orientations.append(sect.find(qn("w:pgSz")).get(qn("w:orient")))
        elif child.tag == qn("w:tbl"):
            grid = []
            for tr in child.iter(qn("w:tr")):
                row = []
                for tc in tr.iter(qn("w:tc")):
                    pr = tc.find(qn("w:tcPr"))
                    span = pr.find(qn("w:gridSpan")) if pr is not None else None
                    paras = list(tc.iter(qn("w:p")))
                    cell_items += sum(1 for q in paras if q.find(f"{qn('w:pPr')}/{qn('w:numPr')}") is not None)
                    n = int(span.get(qn("w:val"))) if span is not None else 1
                    row += ["\n".join(_para_text(q) for q in paras)] + [""] * (n - 1)
                grid.append(row)
            tables.append(grid)
            texts += [" ".join(row) for row in grid]
        elif child.tag == qn("w:sectPr"):
            orientations.append(child.find(qn("w:pgSz")).get(qn("w:orient")))
    links = document.element.body.findall(f".//{qn('w:hyperlink')}")
    targets = [document.part.rels[h.get(qn("r:id"))].target_ref for h in links]
    header = document.sections[0].header.paragraphs[0].text
    footer = document.sections[0].footer.paragraphs[0].text
    return dict(text="\n".join(texts), headings=headings, tables=tables, items=items, cell_items=cell_items,
                numbered_headings=numbered_headings, orientations=orientations, link_targets=targets,
                header=header, footer=footer, linked=[s.header.is_linked_to_previous for s in document.sections])


def make_docx():
    path = HERE / "gen-cash-audit.docx"
    build_docx(path)
    checks = {
        "must_contain": DOCX_MUST,
        "ordered": DOCX_ORDERED,
        "headings": DOCX_HEADINGS,
        "tables": [
            {"name": "Document control table (no header row; first column bold and shaded)", "rows": DOCX_CONTROL},
            {"name": "Table 1. Rating scale (header row and 3 rows)", "rows": DOCX_RATINGS},
            {"name": "Table 2. Findings and management responses (repeated header row; two group-label rows merged "
                     "across all six columns; finding cells with a bold title paragraph and a text paragraph; four "
                     "response cells hold one paragraph, two hold a two-item bulleted list)", "rows": DOCX_T_FINDINGS},
            {"name": "Table 3. Deposit testing results by hotel (landscape section; header row, 3 rows and a total "
                     "row)", "rows": DOCX_T_DEPOSITS},
        ],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="docx", title=DOCX_TITLE, pages_or_sheets=None,
        stresses=["Title and Subtitle styles; a document-control table without a header row whose first column is "
                  "bold and shaded",
                  "Heading 1 / Heading 2 paragraphs numbered by Word list numbering attached to the headings (1., 2., "
                  "3., 3.1; the numbers are drawn by Word, not typed); a last Heading 1 without numbering",
                  "a call-out paragraph with a border on four sides and shading, holding a bold label run",
                  "a one-level bulleted list and a separate '1)' numbered list",
                  "a hyperlink run whose display text differs from its address",
                  "a findings table with a repeated header row (tblHeader), two group-label rows merged across all six "
                  "columns, finding cells with a bold first paragraph, response cells holding a bulleted list",
                  "an Intense Quote paragraph",
                  "a section break to a landscape section holding an eight-column table with negative amounts in "
                  "parentheses and a bold total row; captions; an italic 9-point note",
                  "page header and footer (stored once; the landscape section's are linked to the first)"],
        checks=checks,
        notes=("The headings are Word Heading 1 / Heading 2 paragraphs; the first four carry list numbering (numId "
               f"{HEAD_NUM_ID}: '1.', '2.', '3.', '3.1') drawn by Word, so the expected headings hold the text only "
               "('Executive Summary'); a converter may or may not print the numbers, and both match. The appendix "
               "heading has no numbering. The document title uses the Title style and is the first ordered anchor, "
               "not a heading, and the Subtitle-style line is a phrase (as in the earlier sets). The call-out "
               "paragraph (bold 'Overall rating: ' then plain text) is checked as one phrase; normalization deletes "
               "'*' and '_'. The hyperlink's display text 'Audit IA-2031-07 test plan' is part of the checked "
               "phrase; its address is not checked (a converter may print it or not). Tables: the document-control "
               "table has no header row; in Table 2 each group-label row ('Cash drawers and safes', 'Deposits and "
               "reconciliation') is one cell merged across six columns (the covered positions are empty strings, not "
               "scored), each finding cell holds two paragraphs (bold title, then text) and responses 1 and 4 hold "
               "two bulleted paragraphs; paragraphs inside a cell are written with '\\n' between them (normalization "
               "makes it a space). Table 3 is in a landscape section; amounts are text as typed ('(1,045.80)'), "
               "compared without the thousands comma. must_contain keeps every body paragraph, list item, caption "
               "and note of at least 6 words; the short caption 'Table 1. Rating scale' is not a phrase. Page header "
               "('" + DOCX_HEADER + "') and footer ('" + DOCX_FOOTER + "') are stored once each and are not checked. "
               "No footnotes, comments, tracked changes or hyphenation: noise and absent are empty."))
    rb = read_docx(path)
    require(rb["header"] == DOCX_HEADER and rb["footer"] == DOCX_FOOTER and rb["linked"] == [False, True],
            "docx: header/footer")
    require(rb["numbered_headings"] == 4, f"docx: numbered headings {rb['numbered_headings']}")
    want_items = [(BULLET_NUM_ID if k == "bullet" else LIST_NUM_ID, t) for k, t in DOCX_BLOCKS if k in ("bullet",
                                                                                                         "number")]
    require(rb["items"] == want_items, f"docx: list items {rb['items']}")
    require(rb["cell_items"] == 4, f"docx: bulleted cell paragraphs {rb['cell_items']}")
    require(rb["orientations"] == [None, "landscape"], f"docx: section orientations {rb['orientations']}")
    require(rb["link_targets"] == [DOCX_LINK_URL], f"docx: hyperlink {rb['link_targets']}")
    verify(path.name, "docx", gt, rb["text"], headings_found=rb["headings"], tables_found=rb["tables"])
    require(normalize(DOCX_FOOTER) not in normalize(rb["text"]), "docx: footer text also in the body")
    return gt


# ===========================================================================
# 2. gen-labor-hours.xlsx
# ===========================================================================

S_SUM, S_DET, S_RATE = "Summary", "Hotel Detail", "Rate Table"
XLSX_TITLE = "Labor Hours and Overtime, Second Quarter 2031"
XLSX_NOTE = "Hours come from the detail sheet; overtime cost uses the overtime rate of each department."
XLSX_NOTE2 = "Overtime share is overtime hours divided by all hours worked."
DET_TITLE = "Labor hours by hotel and department, April to June 2031"
DET_NOTE = "Approved hours from the timekeeping system, rounded to a tenth of an hour."
RATE_NOTE = "Multipliers follow the 2031 labor agreement for hourly staff."
HOTELS = [("Coastal", "Seattle Waterfront"), ("Coastal", "Tacoma Narrows"), ("Inland", "Spokane Riverside"),
          ("Inland", "Boise Foothills")]
DEPTS = ["Front office", "Housekeeping", "Food and beverage"]
RATES = [("Front office", "24.40", (2031, 4, 1)), ("Housekeeping", "21.80", (2031, 1, 15)),
         ("Food and beverage", "23.20", (2031, 4, 1))]
MULT = Decimal("1.5")
Q_MONTHS = [(2031, 4, 1), (2031, 5, 1), (2031, 6, 1)]
F_HOURS, F_COST, F_PCT, F_USD, F_MULT = "#,##0.0", "#,##0.00", "0.0%", "$#,##0.00", "0.0"
F_MON_LONG, F_MON_SHORT, F_DATE_LONG = "mmmm yyyy", "mmm yyyy", "mmmm d, yyyy"


def hours(i, j, m):
    reg = Decimal(1760 + 290 * i + 515 * j + 41 * m) + Decimal((i * 3 + j * 7 + m * 5) % 10) / 10
    ot = Decimal(58 + 23 * i + 37 * j + 19 * m + (i * j * m) % 13) + Decimal((i * 7 + j * 3 + m) % 10) / 10
    return reg, ot


def xlsx_display(value, fmt) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if isinstance(value, dt.datetime):
        if fmt == F_MON_LONG:
            return f"{MONTHS[value.month - 1]} {value.year}"
        if fmt == F_MON_SHORT:
            return f"{MONTHS[value.month - 1][:3]} {value.year}"
        if fmt == F_DATE_LONG:
            return f"{MONTHS[value.month - 1]} {value.day}, {value.year}"
        raise ValueError(fmt)
    d = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if fmt in (F_HOURS, F_MULT):
        q = d.quantize(Decimal("0.1"))
        require(q == d, f"xlsx: {d} has more than one decimal")
        return f"{q:,.1f}" if fmt == F_HOURS else f"{q:.1f}"
    if fmt in (F_COST, F_USD):
        q = money(d)
        require(q == d and q >= 0, f"xlsx: amount {d}")
        return ("$" if fmt == F_USD else "") + f"{q:,.2f}"
    if fmt == F_PCT:
        return f"{pct1(d)}%"
    if fmt == "General":
        require(d == d.to_integral_value(), "xlsx: integer cell")
        return str(int(d))
    raise ValueError(f"unexpected cell {value!r} with format {fmt!r}")


def xlsx_model():
    """{sheet: {(row, col): (value, fmt, formula)}} plus merges, with every formula value precomputed."""
    det, merges_det = {}, []
    det[(1, 2)] = (DET_TITLE, "General", None)
    det[(2, 2)] = (DET_NOTE, "General", None)
    for col, text in ((2, "Region"), (3, "Hotel"), (4, "Department")):
        det[(3, col)] = (text, "General", None)
        merges_det.append((3, col, 4, col))
    for k, ym in enumerate(Q_MONTHS + [None]):
        col = 5 + 2 * k
        det[(3, col)] = ((dt.datetime(*ym), F_MON_LONG, None) if ym else ("Quarter total", "General", None))
        merges_det.append((3, col, 3, col + 1))
        det[(4, col)] = ("Regular", "General", None)
        det[(4, col + 1)] = ("Overtime", "General", None)
    row = 5
    sub_rows, values = [], {}
    for region in ("Coastal", "Inland"):
        first = row
        for i, (reg_name, hotel) in enumerate(HOTELS):
            if reg_name != region:
                continue
            det[(row, 3)] = (hotel, "General", None)
            merges_det.append((row, 3, row + len(DEPTS) - 1, 3))
            for j, dept in enumerate(DEPTS):
                det[(row, 4)] = (dept, "General", None)
                tot = [Decimal(0), Decimal(0)]
                for m in range(3):
                    reg_h, ot_h = hours(i, j, m)
                    det[(row, 5 + 2 * m)] = (reg_h, F_HOURS, None)
                    det[(row, 6 + 2 * m)] = (ot_h, F_HOURS, None)
                    values[(dept, m)] = values.get((dept, m), Decimal(0)) + ot_h
                    tot = [tot[0] + reg_h, tot[1] + ot_h]
                det[(row, 11)] = (tot[0], F_HOURS, f"E{row}+G{row}+I{row}")
                det[(row, 12)] = (tot[1], F_HOURS, f"F{row}+H{row}+J{row}")
                row += 1
        det[(first, 2)] = (region, "General", None)
        merges_det.append((first, 2, row - 1, 2))
        det[(row, 2)] = (f"{region} subtotal", "General", None)
        merges_det.append((row, 2, row, 4))
        for col in range(5, 13):
            letter_ = "ABCDEFGHIJKL"[col - 1]
            s = sum(det[(r, col)][0] for r in range(first, row))
            det[(row, col)] = (s, F_HOURS, f"SUM({letter_}{first}:{letter_}{row - 1})")
        sub_rows.append(row)
        row += 1
    det[(row, 2)] = ("All hotels", "General", None)
    merges_det.append((row, 2, row, 4))
    for col in range(5, 13):
        letter_ = "ABCDEFGHIJKL"[col - 1]
        det[(row, col)] = (sum(det[(r, col)][0] for r in sub_rows), F_HOURS,
                           "+".join(f"{letter_}{r}" for r in sub_rows))
    total_row, last_body = row, row - 1
    require(total_row == 19 and sub_rows == [11, 18], "xlsx: detail layout")

    rates = {}
    for k, h in enumerate(["Department", "Base rate (USD)", "Overtime multiplier", "Overtime rate (USD)",
                           "Effective from"]):
        rates[(1, k + 1)] = (h, "General", None)
    ot_rate = {}
    for k, (dept, base, eff) in enumerate(RATES):
        r = 2 + k
        ot_rate[dept] = Decimal(base) * MULT
        require(ot_rate[dept] == ot_rate[dept].quantize(Decimal("0.1")), "xlsx: overtime rate needs <= 1 decimal")
        rates[(r, 1)] = (dept, "General", None)
        rates[(r, 2)] = (Decimal(base), F_USD, None)
        rates[(r, 3)] = (MULT, F_MULT, None)
        rates[(r, 4)] = (ot_rate[dept], F_USD, f"B{r}*C{r}")
        rates[(r, 5)] = (dt.datetime(*eff), F_DATE_LONG, None)
    rates[(6, 1)] = (RATE_NOTE, "General", None)

    summ = {(1, 1): (XLSX_TITLE, "General", None), (2, 1): (XLSX_NOTE, "General", None),
            (10, 1): (XLSX_NOTE2, "General", None)}
    for k, h in enumerate(["Department", "Regular hours", "Overtime hours", "Overtime share"]):
        summ[(4, 1 + k)] = (h, "General", None)
    for k, h in enumerate(["Month", "Total hours", "Overtime cost (USD)"]):
        summ[(4, 6 + k)] = (h, "General", None)
    rng = f"'{S_DET}'!$D$5:$D${last_body}"
    tot_reg = tot_ot = Decimal(0)
    for j, dept in enumerate(DEPTS):
        r = 5 + j
        reg = sum(det[(rr, 11)][0] for rr in range(5, last_body + 1) if det.get((rr, 4), (None,))[0] == dept)
        ot = sum(det[(rr, 12)][0] for rr in range(5, last_body + 1) if det.get((rr, 4), (None,))[0] == dept)
        summ[(r, 1)] = (dept, "General", None)
        summ[(r, 2)] = (reg, F_HOURS, f"SUMIF({rng},$A{r},'{S_DET}'!$K$5:$K${last_body})")
        summ[(r, 3)] = (ot, F_HOURS, f"SUMIF({rng},$A{r},'{S_DET}'!$L$5:$L${last_body})")
        summ[(r, 4)] = (ot / (reg + ot), F_PCT, f"C{r}/(B{r}+C{r})")
        tot_reg, tot_ot = tot_reg + reg, tot_ot + ot
    summ[(8, 1)] = ("All departments", "General", None)
    summ[(8, 2)] = (tot_reg, F_HOURS, "SUM(B5:B7)")
    summ[(8, 3)] = (tot_ot, F_HOURS, "SUM(C5:C7)")
    summ[(8, 4)] = (tot_ot / (tot_reg + tot_ot), F_PCT, "C8/(B8+C8)")
    tot_h = tot_c = Decimal(0)
    for m, ym in enumerate(Q_MONTHS):
        r = 5 + m
        rc, oc = "EGI"[m], "FHJ"[m]
        th = det[(total_row, 5 + 2 * m)][0] + det[(total_row, 6 + 2 * m)][0]
        cost = sum(values[(dept, m)] * ot_rate[dept] for dept in DEPTS)
        require(cost == money(cost), "xlsx: overtime cost has more than two decimals")
        summ[(r, 6)] = (dt.datetime(*ym), F_MON_SHORT, None)
        summ[(r, 7)] = (th, F_HOURS, f"'{S_DET}'!{rc}{total_row}+'{S_DET}'!{oc}{total_row}")
        summ[(r, 8)] = (cost, F_COST, f"SUMPRODUCT(SUMIF({rng},'{S_RATE}'!$A$2:$A$4,'{S_DET}'!{oc}$5:{oc}${last_body}),"
                                      f"'{S_RATE}'!$D$2:$D$4)")
        tot_h, tot_c = tot_h + th, tot_c + cost
    summ[(8, 6)] = ("Quarter", "General", None)
    summ[(8, 7)] = (tot_h, F_HOURS, "SUM(G5:G7)")
    summ[(8, 8)] = (tot_c, F_COST, "SUM(H5:H7)")
    require(tot_h == tot_reg + tot_ot, "xlsx: summary tables disagree")
    return {S_SUM: (summ, []), S_DET: (det, merges_det), S_RATE: (rates, [])}


def _grid(cells, r0, c0, r1, c1):
    return [[xlsx_display(*cells[(r, c)][:2]) if (r, c) in cells else "" for c in range(c0, c1 + 1)]
            for r in range(r0, r1 + 1)]


def build_xlsx(path: Path, model):
    wb = openpyxl.Workbook()
    cached = {}
    bold_rows = {S_SUM: {4, 8}, S_DET: {3, 4, 11, 18, 19}, S_RATE: {1}}
    for index, (name, (cells, merges)) in enumerate(model.items()):
        ws = wb.active if index == 0 else wb.create_sheet(name)
        ws.title = name
        xml_name = f"xl/worksheets/sheet{index + 1}.xml"
        for (r, c), (value, fmt, formula) in sorted(cells.items()):
            v = float(value) if isinstance(value, Decimal) else value
            cell = ws.cell(row=r, column=c, value=f"={formula}" if formula else v)
            cell.number_format = fmt
            if formula:
                cached[(xml_name, cell.coordinate)] = float(value)
            if r in bold_rows[name]:
                cell.font = Font(bold=True)
        for r0, c0, r1, c1 in merges:
            ws.merge_cells(start_row=r0, start_column=c0, end_row=r1, end_column=c1)
            ws.cell(row=r0, column=c0).alignment = Alignment(horizontal="center" if r0 <= 4 else "left",
                                                             vertical="center" if r0 <= 4 else "top",
                                                             wrap_text=True)
        if name == S_SUM:
            ws["A1"].font = Font(bold=True, size=14)
            for ref in ("A2", "A10"):
                ws[ref].font = Font(italic=True, size=9)
            for col, width in zip("ABCDEFGH", (20, 15, 15, 15, 4, 12, 13, 20)):
                ws.column_dimensions[col].width = width
        elif name == S_DET:
            ws["B1"].font = Font(bold=True, size=13)
            ws["B2"].font = Font(italic=True, size=9)
            for col, width in zip("ABCDEFGHIJKL", (3, 11, 20, 19, 11, 11, 11, 11, 11, 11, 12, 12)):
                ws.column_dimensions[col].width = width
            ws.row_dimensions.group(5, 10, outline_level=1, hidden=False)
            ws.row_dimensions.group(12, 17, outline_level=1, hidden=False)
            ws.freeze_panes = "E5"
            fill = PatternFill("solid", fgColor="F2F2F2")
            for r in (11, 18, 19):
                for c in range(2, 13):
                    ws.cell(row=r, column=c).fill = fill
        else:
            table = XTable(displayName="OvertimeRates", ref="A1:E4")
            table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
            ws.add_table(table)
            ws["A6"].font = Font(italic=True, size=9)
            for col, width in zip("ABCDE", (20, 16, 19, 19, 18)):
                ws.column_dimensions[col].width = width
    wb.properties.title = "Labor hours and overtime, second quarter 2031"
    wb.properties.creator = "Hotel Finance"
    wb.properties.lastModifiedBy = "Hotel Finance"
    wb.properties.created = dt.datetime(2031, 7, 9, 8, 30, 0)
    wb.properties.modified = dt.datetime(2031, 7, 9, 8, 30, 0)
    wb.save(path)

    def patch(part, data):
        """Writes each formula's computed value into its empty <v/>, as Excel saves it."""
        refs = {ref: v for (sheet, ref), v in cached.items() if sheet == part}
        if not refs:
            return data
        text = data.decode("utf-8")
        for ref, value in refs.items():
            pattern = rf'(<c r="{ref}"[^>]*><f>[^<]*</f>)<v\s*/?>(?:</v>)?'
            text, n = re.subn(pattern, rf"\g<1><v>{value!r}</v>", text)
            require(n == 1, f"xlsx: could not write the cached value of {part} {ref}")
        return text.encode("utf-8")

    pin_ooxml(path, "2031-07-09T08:30:00Z", "2031-07-09T08:30:00Z", patch=patch)
    return cached


def make_xlsx():
    path = HERE / "gen-labor-hours.xlsx"
    model = xlsx_model()
    cached = build_xlsx(path, model)
    summ, det, rates = model[S_SUM][0], model[S_DET][0], model[S_RATE][0]
    t_left, t_right = _grid(summ, 4, 1, 8, 4), _grid(summ, 4, 6, 8, 8)
    t_det, t_rate = _grid(det, 3, 2, 19, 12), _grid(rates, 1, 1, 4, 5)
    checks = {
        # Locale-independent text cells, notes and sheet names only; numbers and dates are checked by the tables.
        "must_contain": [XLSX_TITLE, XLSX_NOTE, XLSX_NOTE2, DET_TITLE, DET_NOTE, RATE_NOTE, S_SUM, S_DET, S_RATE,
                         "Overtime cost (USD)", "All departments", "Seattle Waterfront", "Boise Foothills",
                         "Coastal subtotal", "Quarter total", "Overtime rate (USD)", "Effective from"],
        "ordered": [XLSX_TITLE, XLSX_NOTE2, "Tacoma Narrows", "Inland subtotal", "Overtime multiplier"],
        "headings": [],
        "tables": [
            {"name": "Summary, left table A4:D8 (department hours and overtime share; header row, 3 rows and a total "
                     "row; values from cross-sheet SUMIF formulas)", "rows": t_left},
            {"name": "Summary, right table F4:H8 beside the left one after the empty column E (month, total hours, "
                     "overtime cost; month cells are dates shown as 'Apr 2031'; SUMPRODUCT formulas)",
             "rows": t_right},
            {"name": "Hotel Detail B3:L19 (column A empty; two header rows: 'Region', 'Hotel' and 'Department' merged "
                     "down, three month groups and 'Quarter total' merged across two columns; region and hotel labels "
                     "merged down over their rows; subtotal and total labels merged across B-D)", "rows": t_det},
            {"name": "Rate Table A1:E4 (Excel table object 'OvertimeRates'; formula column; dates shown as 'April 1, "
                     "2031')", "rows": t_rate},
        ],
        "noise": [],
        "absent": [],
    }
    n_formula = len(cached)
    gt = write_ground_truth(
        path, fmt="xlsx", title="Labor hours and overtime by hotel and department, second quarter 2031",
        pages_or_sheets=3,
        stresses=["three visible worksheets (Summary, Hotel Detail, Rate Table)",
                  "two tables side by side on one sheet, separated by an empty column, under an unmerged title and "
                  "note; a note below them",
                  "a table that starts in column B (column A empty) under a title and a note, with two header rows: "
                  "three month groups and a quarter group merged across two columns, three headers merged down",
                  "month headers that are real dates shown as 'April 2031' (mmmm yyyy) and 'Apr 2031' (mmm yyyy); "
                  "dates shown as 'April 1, 2031' (mmmm d, yyyy)",
                  "body labels merged down over several rows (region over six rows, hotel over three), subtotal and "
                  "total labels merged across three columns, row outline groups (not collapsed), frozen panes",
                  f"{n_formula} formula cells (SUMIF and SUMPRODUCT across sheets, sums, products) saved with their "
                  "computed values, as Excel saves them",
                  "an Excel table object (ListObject) with a table style, currency formats ($#,##0.00) and a formula "
                  "column; hours with one decimal and thousands separators (#,##0.0), percentages (0.0%)"],
        checks=checks,
        notes=("Expected cells are the text Excel shows in an en-US locale: hours as '2,140.5' (#,##0.0), costs as "
               "'12,345.67' (#,##0.00), rates as '$24.40' ($#,##0.00), the multiplier as '1.5' (0.0), shares as "
               "'7.9%' (0.0%), month headers as 'April 2031' and 'Apr 2031', effective dates as 'April 1, 2031'. "
               "Separators, date words and order follow the viewer's locale, so (as in the earlier sets) must_contain "
               "lists only text cells, notes and the three sheet names, and number and date display is measured by "
               "the tables. The Summary sheet holds two tables on rows 4-8, A4:D8 and F4:H8, with column E empty "
               "between them; they are listed as two tables (a converter that prints them as one wide table still "
               "pairs their columns by header text). The Hotel Detail table starts at its first header row (row 3) "
               "and column B; merged cells keep their text in the top-left position and the covered positions are "
               "empty strings (not scored): 'Region', 'Hotel' and 'Department' are merged down over rows 3-4, each "
               "month group and 'Quarter total' across 'Regular' and 'Overtime', 'Coastal' and 'Inland' down over six "
               "body rows, each hotel down over its three department rows, and the 'Coastal subtotal', 'Inland "
               "subtotal' and 'All hotels' labels across B-D. Formulas (" + str(n_formula) + " cells, e.g. Summary B5 "
               "'=SUMIF('Hotel Detail'!$D$5:$D$17,$A5,'Hotel Detail'!$K$5:$K$17)', H5 '=SUMPRODUCT(SUMIF(...))', "
               "Hotel Detail K5 '=E5+G5+I5', Rate Table D2 '=B2*C2') are saved with their computed values, so the "
               "expected cell is the value. The title and note rows of the first two sheets and the notes below the "
               "tables are checked by must_contain and ordered, not as table rows. Sheet names are tab labels: "
               "checked by must_contain, not as headings. The Rate Table sheet's table is an Excel table object; its "
               "header row is checked like any other. No hidden rows, columns or sheets, comments, charts or print "
               "headers/footers: noise and absent are empty."))

    wb_f = openpyxl.load_workbook(path)
    wb_v = openpyxl.load_workbook(path, data_only=True)
    require([ws.title for ws in wb_v.worksheets] == list(model), "xlsx: sheet names/order")
    texts, grids, fields = [], {}, list(model)
    for ws_v, ws_f in zip(wb_v.worksheets, wb_f.worksheets):
        require(ws_v.sheet_state == "visible", f"xlsx: {ws_v.title} hidden")
        grid = {}
        for row_v, row_f in zip(ws_v.iter_rows(), ws_f.iter_rows()):
            for cv, cf in zip(row_v, row_f):
                if cf.data_type == "f":
                    require(cv.value is not None, f"xlsx: formula {ws_v.title}!{cv.coordinate} has no cached value")
                if cv.value is None:
                    continue
                if cv.number_format in (F_MON_LONG, F_MON_SHORT, F_DATE_LONG):
                    require(isinstance(cv.value, dt.datetime), "xlsx: date cell is not a real date")
                grid[(cv.row, cv.column)] = xlsx_display(cv.value, cv.number_format)
        grids[ws_v.title] = grid
        lines = []
        for r in range(1, ws_v.max_row + 1):
            lines.append(" ".join(grid.get((r, c), "") for c in range(1, ws_v.max_column + 1)))
        texts.append(ws_v.title + "\n" + "\n".join(lines))
        fields += [v for v in grid.values() if v]

    def back(sheet, r0, c0, r1, c1):
        return [[grids[sheet].get((r, c), "") for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]

    require(sorted(str(r) for r in wb_v[S_DET].merged_cells.ranges) == sorted(
        f"{get_column_letter(c0)}{r0}:{get_column_letter(c1)}{r1}"
        for r0, c0, r1, c1 in model[S_DET][1]), "xlsx: merged ranges")
    require(len(model[S_DET][1]) == 16, f"xlsx: {len(model[S_DET][1])} merged ranges")
    require(list(wb_f[S_RATE].tables) == ["OvertimeRates"] and wb_f[S_RATE].tables["OvertimeRates"].ref == "A1:E4",
            "xlsx: table object")
    require(wb_f[S_DET].row_dimensions[5].outline_level == 1 and wb_f[S_DET].freeze_panes == "E5", "xlsx: outline")
    require(sum(1 for ws in wb_f.worksheets for row in ws.iter_rows() for c in row if c.data_type == "f")
            == n_formula, "xlsx: formula count")
    require(all(grids[S_SUM].get((r, 5)) is None for r in range(1, 11)) and all(
        grids[S_DET].get((r, 1)) is None for r in range(1, 20)), "xlsx: spacer column not empty")
    tables_found = [back(S_SUM, 4, 1, 8, 4), back(S_SUM, 4, 6, 8, 8), back(S_DET, 3, 2, 19, 12),
                    back(S_RATE, 1, 1, 4, 5)]
    verify(path.name, "xlsx", gt, "\n".join(texts), tables_found=tables_found, fields=fields)
    return gt


# ===========================================================================
# 3. gen-renovation-update.pptx
# ===========================================================================

PPTX_PROPS = [  # hotel, rooms, completed, budget (USD m), spent (USD m), status
    ("Seattle Waterfront", 320, 320, "9.2", "9.0", "Closed out"),
    ("Tacoma Narrows", 240, 92, "6.1", "4.1", "In construction"),
    ("Portland Pearl", 210, 0, "5.4", "0.6", "In design"),
    ("Spokane Riverside", 200, 0, "5.1", "3.4", "Furniture ordered"),
    ("Boise Foothills", 180, 0, "5.2", "1.5", "In construction"),
]
PPTX_LINK_URL = "https://board.halcyon-harbor.example/meetings/2031-05/renovation"


def pptx_table():
    rows = [["Hotel", "Rooms", "Completed", "Budget (USD m)", "Spent (USD m)", "Complete", "Status"]]
    t = [0, 0, Decimal(0), Decimal(0)]
    for hotel, rooms, done, budget, spent, status in PPTX_PROPS:
        rows.append([hotel, f"{rooms:,}", f"{done:,}", budget, spent, f"{pct0(Decimal(done) / rooms)}%", status])
        t = [t[0] + rooms, t[1] + done, t[2] + Decimal(budget), t[3] + Decimal(spent)]
    rows.append(["Total", f"{t[0]:,}", f"{t[1]:,}", f"{t[2]}", f"{t[3]}", f"{pct0(Decimal(t[1]) / t[0])}%", ""])
    require(t[:2] == [1150, 412] and t[2] == Decimal("31.0") and t[3] == Decimal("18.6"), "pptx: totals")
    require(sum(1 for p in PPTX_PROPS if p[5] in ("In construction", "Furniture ordered")) == 3, "pptx: tiles")
    return rows


PPTX_TABLE = pptx_table()
PPTX_TILES = [("412", "rooms completed of 1,150"), ("$18.6 million", "spent of the $31.0 million budget"),
              ("3", "hotels in construction or ordering")]
PPTX_SLIDES = [
    {"layout": 0, "title": "Guest Room Renovation Program", "subtitle": "Board of Directors update, May 2031"},
    {"layout": 1, "title": "Agenda", "numbered": ["Where the program stands", "Status of each hotel",
                                                  "Main risks and how we manage them", "Board decisions needed today"]},
    {"layout": 5, "title": "Program at a Glance", "tiles": True,
     "box": "Figures as of April 30, 2031; spending includes committed purchase orders.",
     "notes": "The furniture order for Spokane Riverside was placed early to lock in the 2031 price."},
    {"layout": 5, "title": "Status by Hotel", "table": True,
     "box": "USD m: millions of U.S. dollars. Complete: share of rooms handed back to operations.",
     "notes": "Work at the second hotel lost two weeks in March because a sprinkler inspection was delayed."},
    {"layout": 3, "title": "Risks and Mitigations",
     "left": [(0, "Furniture lead times have grown to 22 weeks"), (1, "Orders for the 2032 hotels go out in October"),
              (0, "The union agreement limits weekend work at Portland Pearl")],
     "right": [(0, "Fixed-price contracts cover 80 percent of the remaining budget"),
               (1, "Change orders above $50,000 need committee approval"),
               (0, "A 6 percent contingency is held at program level")]},
    {"layout": 7, "title": "Lessons from the Pilot Hotel",
     "bullets": [(0, "Guest complaints about noise fell after work hours moved to 10 am"),
                 (0, "Opening rooms floor by floor kept occupancy above 82 percent"),
                 (0, "Early mock-up rooms caught three design errors before ordering")],
     "caption": "Seattle Waterfront was the pilot hotel and finished two weeks ahead of schedule."},
    {"layout": 2, "title": "Next Steps", "body": "Decisions for the board and the schedule for the remaining hotels"},
    {"layout": 1, "title": "Decisions Requested",
     "bullets": [(0, "Approve the revised program budget of $31.0 million"),
                 (0, "Approve the start of construction at Portland Pearl in July"),
                 (1, [("The design package for this decision is posted in the ", None), ("board portal", PPTX_LINK_URL)])],
     "notes": "Voting materials were sent to directors on May 9 together with the meeting agenda."},
]
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _pptx_fill(tf, items):
    for i, (level, content) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if isinstance(content, str):
            p.text = content
        else:
            for text, url in content:
                run = p.add_run()
                run.text = text
                if url:
                    run.hyperlink.address = url
        p.level = level


def _ptext(p):
    return "".join(r.text for r in p.runs)


def build_pptx(path: Path):
    prs = Presentation()
    for spec in PPTX_SLIDES:
        layout = prs.slide_layouts[spec["layout"]]
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = spec["title"]
        if "subtitle" in spec:
            slide.placeholders[1].text = spec["subtitle"]
        if "body" in spec:
            require(layout.name == "Section Header", "pptx: layout 2 is not Section Header")
            slide.placeholders[1].text = spec["body"]
        if "numbered" in spec:
            tf = slide.placeholders[1].text_frame
            _pptx_fill(tf, [(0, t) for t in spec["numbered"]])
            for p in tf.paragraphs:
                p._p.get_or_add_pPr().append(parse_xml(f'<a:buAutoNum xmlns:a="{A_NS}" type="arabicPeriod"/>'))
        if "left" in spec:
            require(layout.name == "Two Content", "pptx: layout 3 is not Two Content")
            _pptx_fill(slide.placeholders[1].text_frame, spec["left"])
            _pptx_fill(slide.placeholders[2].text_frame, spec["right"])
        if "caption" in spec:
            require(layout.name == "Content with Caption", "pptx: layout 7 is not Content with Caption")
            _pptx_fill(slide.placeholders[1].text_frame, spec["bullets"])
            slide.placeholders[2].text = spec["caption"]
        elif "bullets" in spec:
            _pptx_fill(slide.placeholders[1].text_frame, spec["bullets"])
        if spec.get("tiles"):
            group = slide.shapes.add_group_shape()
            for k, (big, label) in enumerate(PPTX_TILES):
                tile = group.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5 + 3.05 * k), Inches(1.8),
                                              Inches(2.85), Inches(2.3))
                tf = tile.text_frame
                tf.word_wrap = True
                tf.paragraphs[0].text = big
                tf.paragraphs[0].runs[0].font.size = PPt(34)
                tf.paragraphs[0].runs[0].font.bold = True
                p = tf.add_paragraph()
                p.text = label
                p.runs[0].font.size = PPt(16)
        if spec.get("table"):
            shape = slide.shapes.add_table(len(PPTX_TABLE), len(PPTX_TABLE[0]), Inches(0.3), Inches(1.6),
                                           Inches(9.4), Inches(0.45) * len(PPTX_TABLE))
            for r, row in enumerate(PPTX_TABLE):
                for c, value in enumerate(row):
                    cell = shape.table.cell(r, c)
                    cell.text = value
                    for para in cell.text_frame.paragraphs:
                        for run in para.runs:
                            run.font.size = PPt(13)
                            run.font.bold = r == 0 or r == len(PPTX_TABLE) - 1 or None
        if "box" in spec:
            top = Inches(4.5) if spec.get("tiles") else Inches(5.0)
            box = slide.shapes.add_textbox(Inches(0.5), top + Inches(0.4), Inches(9.0), Inches(0.6))
            box.text_frame.word_wrap = True
            box.text_frame.text = spec["box"]
            box.text_frame.paragraphs[0].runs[0].font.size = PPt(12)
            box.text_frame.paragraphs[0].runs[0].font.italic = True
        if "notes" in spec:
            slide.notes_slide.notes_text_frame.text = spec["notes"]
    props = prs.core_properties
    props.title = PPTX_SLIDES[0]["title"]
    props.author = "Program Management Office"
    props.last_modified_by = "Program Management Office"
    props.comments = ""
    props.revision = 6
    props.created = dt.datetime(2031, 5, 2, 14, 0, 0)
    props.modified = dt.datetime(2031, 5, 8, 17, 45, 0)
    prs.save(path)
    pin_ooxml(path, "2031-05-02T14:00:00Z", "2031-05-08T17:45:00Z")


def _pptx_shapes(shapes):
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield shape
            yield from _pptx_shapes(shape.shapes)
        else:
            yield shape


def make_pptx():
    path = HERE / "gen-renovation-update.pptx"
    build_pptx(path)
    paragraphs = []
    for s in PPTX_SLIDES:
        paragraphs += [s.get("subtitle", ""), s.get("body", ""), s.get("box", ""), s.get("caption", "")]
        paragraphs += s.get("numbered", [])
        for key in ("left", "right", "bullets"):
            for _, content in s.get(key, []):
                paragraphs.append(content if isinstance(content, str) else "".join(t for t, _ in content))
    paragraphs = [p for p in paragraphs if p]
    notes = [s["notes"] for s in PPTX_SLIDES if "notes" in s]
    must = [p for p in paragraphs if len(p.split()) >= MIN_PHRASE_WORDS] + notes
    short = [p for p in paragraphs if len(p.split()) < MIN_PHRASE_WORDS]
    checks = {
        "must_contain": must,
        "ordered": ["Board of Directors update, May 2031", "Where the program stands", "rooms completed of 1,150",
                    "Furniture ordered", "Furniture lead times have grown to 22 weeks",
                    "Opening rooms floor by floor kept occupancy", "Approve the start of construction at Portland Pearl"],
        "headings": [s["title"] for s in PPTX_SLIDES],
        "tables": [{"name": "Slide 4: Status by Hotel (native 7-column table: header row, 5 rows and a total row with "
                             "an empty status cell)", "rows": PPTX_TABLE}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pptx", title=PPTX_SLIDES[0]["title"], pages_or_sheets=len(PPTX_SLIDES),
        stresses=["slide titles (title placeholders) as headings",
                  "title slide with a subtitle; a Section Header slide with a text placeholder",
                  "an agenda numbered by PowerPoint auto-numbering (a:buAutoNum arabicPeriod; numbers not typed)",
                  "a group shape holding three rounded-rectangle tiles, each with a large first paragraph and a "
                  "second paragraph, followed by a free italic text box",
                  "a native 7-column table with counts with thousands separators, one-decimal amounts, whole "
                  "percentages, a bold total row with an empty cell, and a footnote text box under it",
                  "a Two Content slide with two-level bullets in both placeholders, left then right",
                  "a Content with Caption slide (bullets in the content placeholder, a caption placeholder)",
                  "a second-level bullet that ends in a hyperlink run; speaker notes on slides 3, 4 and 8"],
        checks=checks,
        notes=("Eight slides from python-pptx's default 4:3 template: 1 Title Slide, 2 and 8 Title and Content, 3 and "
               "4 Title Only, 5 Two Content, 6 Content with Caption, 7 Section Header. The agenda items are numbered "
               "by auto-numbering in the paragraph properties, so the numbers '1.'-'4.' are drawn by PowerPoint and "
               "are not part of the checked text. Slide 3's three tiles are shapes inside one group shape, in group "
               "order left to right; each holds two paragraphs (e.g. '412' and 'rooms completed of 1,150'); the "
               "tiles are short and checked through one ordered anchor, the italic text box below them is a phrase. "
               "Slide 4's table has one header row, no merged cells, counts as typed ('1,150'), amounts in millions "
               "('9.2'), whole percentages ('38%') and a total row whose status cell is empty (not scored). Slide 5 "
               "is read left placeholder, then right placeholder. On slide 8 the second-level bullet is two runs, the "
               "second ('board portal') a hyperlink; the checked text is the paragraph text, the address is not "
               "checked. Speaker notes (slides 3, 4 and 8) are in must_contain (3 phrases), never ordered anchors. "
               "headings are the eight slide titles. must_contain keeps every slide paragraph of at least "
               f"{MIN_PHRASE_WORDS} words; the {len(short)} shorter ones ({'; '.join(short)}) are not phrases (the "
               "agenda item 'Where the program stands' and the tile line 'rooms completed of 1,150' are ordered "
               "anchors). No footers, slide numbers, dates, hidden slides, charts or comments: noise and absent are "
               "empty."))
    prs = Presentation(path)
    titles, texts, body, tables, read_notes, autonum, groups, links = [], [], [], [], [], 0, 0, []
    for slide in prs.slides:
        titles.append(slide.shapes.title.text)
        out = []
        for shape in _pptx_shapes(slide.shapes):
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                groups += 1
                continue
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    if _ptext(p):
                        out.append(_ptext(p))
                    autonum += p._p.find(f"{{{A_NS}}}pPr/{{{A_NS}}}buAutoNum") is not None
                    links += [r.hyperlink.address for r in p.runs if r.hyperlink.address]
            if getattr(shape, "has_table", False) and shape.has_table:
                grid = [[cell.text for cell in row.cells] for row in shape.table.rows]
                tables.append(grid)
                out += [" ".join(r) for r in grid]
        texts += out
        body += out
        if slide.has_notes_slide:
            read_notes.append(slide.notes_slide.notes_text_frame.text)
            texts.append(read_notes[-1])
    require(read_notes == notes, "pptx: notes differ")
    require(autonum == 4 and groups == 1 and links == [PPTX_LINK_URL], f"pptx: autonum {autonum}, groups {groups}, "
                                                                       f"links {links}")
    group = [s for s in prs.slides[2].shapes if s.shape_type == MSO_SHAPE_TYPE.GROUP][0]
    require([[_ptext(p) for p in g.text_frame.paragraphs] for g in group.shapes] == [list(t) for t in PPTX_TILES],
            "pptx: tiles")
    require([layout_name(s) for s in prs.slides] == ["Title Slide", "Title and Content", "Title Only", "Title Only",
                                                     "Two Content", "Content with Caption", "Section Header",
                                                     "Title and Content"], "pptx: layouts")
    verify(path.name, "pptx", gt, "\n".join(texts), body_text="\n".join(body), headings_found=titles,
           tables_found=tables)
    return gt


def layout_name(slide):
    return slide.slide_layout.name


# ===========================================================================
# 4. gen-utility-meters.csv
# ===========================================================================

CSV_HEADER = ["site_code", "site_name", "meter_id", "medium", "reading_date", "reading", "unit", "consumption",
              "cost_eur", "estimated", "comment"]
CSV_SITES = [("DE-LIN", "Hotel Seeblick Lindau"), ("FR-ANN", "Hôtel du Lac Annecy"),
             ("NO-BGO", "Hotel Fjordgården Bergen"), ("PL-GDN", "Hotel Złota Brama Gdańsk")]
CSV_MEDIA = [("electricity", "E", "kWh", "0.2675"), ("gas", "G", "m³", "1.1390"), ("water", "W", "m³", "4.0420")]
CSV_DATES = [dt.date(2031, 1, 31), dt.date(2031, 2, 28), dt.date(2031, 3, 31)]
CSV_COMMENTS = {
    (0, 0, 1): 'Reading taken by "Stadtwerke" technician',
    (1, 1, 0): "Meter replaced; new serial 44-118-207",
    (2, 2, 2): "Estimated: plant room locked during the visit",
    (3, 0, 2): "Includes the conference wing; see note on invoice",
    (1, 0, 1): "Photo of the display attached",
}
CSV_ESTIMATED = {(2, 2, 2), (3, 1, 0)}


def dec_comma(d: Decimal, places: int) -> str:
    q = d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return f"{q:.{places}f}".replace(".", ",")


def csv_rows():
    rows = []
    for s, (code, name) in enumerate(CSV_SITES):
        for m, (medium, letter_, unit, tariff) in enumerate(CSV_MEDIA):
            start = Decimal({0: 48210, 1: 15320, 2: 3870}[m] + 9173 * s) + Decimal((s * 3 + m) % 10) / 10
            prev = start
            for k, day in enumerate(CSV_DATES):
                base = {0: 21000 + 3700 * s, 1: 5200 + 1450 * s, 2: 610 + 175 * s}[m]
                use = Decimal(base + (k * 977 + s * 131 + m * 53) % (base // 6)) + Decimal((k * 7 + s + m * 3) % 10) / 10
                reading = prev + use
                rows.append([code, name, f"{code[3:]}-{letter_}-0{m + 1}", medium, day.strftime("%d.%m.%Y"),
                             dec_comma(reading, 1), unit, dec_comma(use, 1),
                             dec_comma(money(use * Decimal(tariff)), 2),
                             "yes" if (s, m, k) in CSV_ESTIMATED else "no", CSV_COMMENTS.get((s, m, k), "")])
                prev = reading
    return rows


def make_csv():
    path = HERE / "gen-utility-meters.csv"
    rows = csv_rows()
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    path.write_bytes(buf.getvalue().encode("utf-8-sig"))
    commented = [r for r in rows if r[10]]
    checks = {
        "must_contain": ["reading_date", "cost_eur", "Hotel Seeblick Lindau", "Hôtel du Lac Annecy",
                         "Hotel Fjordgården Bergen", "Hotel Złota Brama Gdańsk", "electricity",
                         'Reading taken by "Stadtwerke" technician', "Meter replaced; new serial 44-118-207",
                         "Estimated: plant room locked during the visit",
                         "Includes the conference wing; see note on invoice", rows[0][4], rows[-1][4], rows[0][5],
                         rows[-1][8]],
        "ordered": [rows[0][5], rows[9][5], rows[18][5], rows[27][5], rows[-1][5]],
        "headings": [],
        "tables": [{"name": "Meter readings: header row and all 36 data rows", "rows": [CSV_HEADER] + rows}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="csv", title="Utility meter readings of four European hotels, first quarter 2031",
        pages_or_sheets=None,
        stresses=["UTF-8 with a byte order mark, semicolon delimiter, CRLF record ends (a typical European "
                  "spreadsheet export)",
                  "minimal quoting: only the fields holding a semicolon or a double quote are quoted; a doubled "
                  "double quote inside a quoted field",
                  "decimal commas ('48213,6'), no thousands separators; dates as dd.mm.yyyy",
                  "empty comment fields; yes/no flags",
                  "non-ASCII site names (ô, å, ł, ń) and the unit 'm³'"],
        checks=checks,
        notes=("RFC 4180-style CSV as written by Python's csv module with delimiter ';', QUOTE_MINIMAL and CRLF record "
               "ends, encoded as UTF-8 with a byte order mark (utf-8-sig). Only "
               f"{sum(1 for r in rows for f in r if ';' in f or chr(34) in f)} fields are quoted (two with a "
               "semicolon, one with a doubled double quote); commas are decimal separators, not delimiters, so a "
               "reader that splits on commas or ignores the semicolon delimiter will not find the columns. Expected "
               "cell and phrase text is the parsed field value (quotes unescaped), exactly as written ('48213,6', "
               "'31.01.2031'); the table rule leaves decimal-comma numbers unchanged (no field has a comma followed by "
               "three digits). The byte order mark is not part of the first field. The expected table is the whole "
               "file (header + 36 rows, 11 columns); empty comments are empty strings and are not scored. 'm³' "
               "normalizes to 'm3' on both sides (NFKC). must_contain items are whole fields that never occur inside "
               "another field (two column names, the four site names, a medium, the four comments, the first and last "
               "dates, the first reading and the last cost); ordered: the readings of rows 1, 10, 19, 28 and 36. A "
               "CSV has no headings, page furniture or hyphenation: headings, noise and absent are empty."))
    raw = path.read_bytes()
    require(raw.startswith(b"\xef\xbb\xbf") and raw.count(b"\r\n") == len(rows) + 1
            and raw.count(b"\n") == len(rows) + 1, "csv: BOM / CRLF")
    text = raw.decode("utf-8-sig")
    parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=";"))
    require(parsed[0] == CSV_HEADER and parsed[1:] == rows and len(parsed) == 37, "csv: read-back differs")
    require(all(len(r) == len(CSV_HEADER) for r in parsed), "csv: ragged rows")
    require('"Reading taken by ""Stadtwerke"" technician"' in text and '"Meter replaced; new serial 44-118-207"' in text,
            "csv: quoting")
    require(len(commented) == 5 and sum(1 for r in rows if r[9] == "yes") == 2, "csv: features")
    require(not any(re.fullmatch(r"\d{1,3}(?:,\d{3})+", f) for r in rows for f in r), "csv: a field looks grouped")
    require(text.count('"') == 10, f"csv: {text.count(chr(34))} quote characters, expected 10")
    verify(path.name, "csv", gt, "\n".join(" ".join(r) for r in parsed), tables_found=[parsed],
           fields=[c for r in parsed for c in r])
    return gt


# ===========================================================================
# 5. gen-work-orders.json
# ===========================================================================

JSON_ORDERS = [
    {"id": "WO-31-05812", "type": "corrective", "priority": "urgent", "status": "completed",
     "location": {"building": "Tower", "floor": 7, "room": "712"},
     "asset": {"tag": "HVAC-0712", "category": "PTAC unit"}, "reported_by": {"role": "guest", "channel": "phone"},
     "opened_at": "2031-05-03T22:14:00Z", "closed_at": "2031-05-03T23:40:00Z",
     "labor": [{"technician": "Mateus Andrade", "hours": 1.25}],
     "parts": [{"sku": "THM-220", "description": "Thermistor, 10 kOhm", "qty": 1, "unit_cost": 18.4}],
     "guest_impact": True, "notes": "Unit tripped its breaker; replaced the \"room sensor\" lead."},
    {"id": "WO-31-05815", "type": "preventive", "priority": "routine", "status": "completed",
     "location": {"building": "Tower", "floor": 1, "room": None},
     "asset": {"tag": "BLR-02", "category": "Hot water boiler"}, "reported_by": None,
     "opened_at": "2031-05-04T07:00:00Z", "closed_at": "2031-05-04T10:30:00Z",
     "labor": [{"technician": "Zoë Lindqvist", "hours": 2.5}, {"technician": "Mateus Andrade", "hours": 1.0}],
     "parts": [], "guest_impact": False, "checklist": {"template": "PM-BLR-Q", "items": 14, "failed": 0}},
    {"id": "WO-31-05821", "type": "corrective", "priority": "high", "status": "on_hold",
     "location": {"building": "Garden Wing", "floor": 2, "room": "214"},
     "asset": {"tag": "PLB-214-TUB", "category": "Bathtub drain"}, "reported_by": {"role": "housekeeping",
                                                                                   "channel": "app"},
     "opened_at": "2031-05-05T09:42:00Z", "closed_at": None, "labor": [], "parts": [],
     "guest_impact": True, "hold_reason": "Waiting for a replacement drain body from the supplier",
     "room_out_of_order": True},
    {"id": "WO-31-05826", "type": "inspection", "priority": "routine", "status": "completed",
     "location": {"building": "Tower", "floor": 12, "room": None},
     "asset": {"tag": "ELV-03", "category": "Passenger elevator"}, "reported_by": None,
     "opened_at": "2031-05-06T13:00:00Z", "closed_at": "2031-05-06T14:15:00Z",
     "labor": [{"technician": "Tadeusz Wróbel", "hours": 1.25}], "parts": [], "guest_impact": False,
     "contractor": {"name": "Cascade Lift Services", "permit": "ELV-2031-118"}},
    {"id": "WO-31-05830", "type": "corrective", "priority": "urgent", "status": "completed",
     "location": {"building": "Podium", "floor": 0, "room": "Kitchen"},
     "asset": {"tag": "KIT-WIC-1", "category": "Walk-in cooler"}, "reported_by": {"role": "chef", "channel": "radio"},
     "opened_at": "2031-05-07T05:51:00Z", "closed_at": "2031-05-07T08:05:00Z",
     "labor": [{"technician": "Zoë Lindqvist", "hours": 2.25}],
     "parts": [{"sku": "GSK-WIC-36", "description": "Door gasket, 36 x 80 in", "qty": 1, "unit_cost": 96.0},
               {"sku": "HNG-HD-2", "description": "Heavy-duty hinge", "qty": 2, "unit_cost": 41.75}],
     "guest_impact": False, "temperature_log": [41.2, 39.8, 37.9, 36.5]},
    {"id": "WO-31-05834", "type": "corrective", "priority": "high", "status": "completed",
     "location": {"building": "Garden Wing", "floor": 3, "room": "305"},
     "asset": {"tag": "LCK-305", "category": "Guest room door lock"}, "reported_by": {"role": "front desk",
                                                                                      "channel": "app"},
     "opened_at": "2031-05-08T19:20:00Z", "closed_at": "2031-05-08T19:55:00Z",
     "labor": [{"technician": "Tadeusz Wróbel", "hours": 0.5}],
     "parts": [{"sku": "BAT-AA-4", "description": "AA batteries, pack of 4", "qty": 1, "unit_cost": 3.6}],
     "guest_impact": True, "notes": None},
    {"id": "WO-31-05839", "type": "project", "priority": "planned", "status": "in_progress",
     "location": {"building": "Tower", "floor": 9, "room": None},
     "asset": None, "reported_by": None, "opened_at": "2031-05-09T08:00:00Z", "closed_at": None,
     "labor": [{"technician": "Mateus Andrade", "hours": 6.0}, {"technician": "Ngozi Eze", "hours": 6.0}],
     "parts": [], "guest_impact": False, "project": {"code": "RNV-SEA-09", "phase": "punch list"}},
    {"id": "WO-31-05843", "type": "corrective", "priority": "routine", "status": "cancelled",
     "location": {"building": "Tower", "floor": 4, "room": "418"},
     "asset": {"tag": "TV-418", "category": "Television"}, "reported_by": {"role": "guest", "channel": "phone"},
     "opened_at": "2031-05-10T21:03:00Z", "closed_at": "2031-05-10T21:20:00Z", "labor": [], "parts": [],
     "guest_impact": False, "cancel_reason": "Guest found the input button; no fault"},
    {"id": "WO-31-05847", "type": "preventive", "priority": "routine", "status": "scheduled",
     "location": {"building": "Podium", "floor": -1, "room": "Pool plant"},
     "asset": {"tag": "POOL-PMP-1", "category": "Pool circulation pump"}, "reported_by": None,
     "opened_at": "2031-05-11T06:00:00Z", "closed_at": None, "labor": [], "parts": [], "guest_impact": False,
     "due_by": "2031-05-18"},
    {"id": "WO-31-05851", "type": "corrective", "priority": "urgent", "status": "completed",
     "location": {"building": "Garden Wing", "floor": 1, "room": "Lobby"},
     "asset": {"tag": "DR-LBY-AUTO", "category": "Automatic sliding door"},
     "reported_by": {"role": "security", "channel": "radio"},
     "opened_at": "2031-05-12T23:48:00Z", "closed_at": "2031-05-13T01:10:00Z",
     "labor": [{"technician": "Ngozi Eze", "hours": 1.5}],
     "parts": [{"sku": "SNS-MW-1", "description": "Motion sensor, microwave type", "qty": 1, "unit_cost": 212.5}],
     "guest_impact": True, "notes": "Door stuck open; lobby staffed by security until repaired."},
]


def json_model():
    return {"meta": {"api_version": "2.3", "generated_at": "2031-05-14T06:00:12Z",
                     "property": {"code": "HHH-SEA", "name": "Halcyon Harbor Seattle Waterfront"},
                     "page": 1, "per_page": 10, "total": len(JSON_ORDERS)},
            "data": JSON_ORDERS,
            "links": {"self": "https://api.halcyon-harbor.example/v2/work-orders?page=1", "next": None}}


def make_json():
    path = HERE / "gen-work-orders.json"
    obj = json_model()
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    path.write_bytes(raw.encode("utf-8"))
    checks = {
        "must_contain": ["generated_at", "room_out_of_order", "Halcyon Harbor Seattle Waterfront", "Zoë Lindqvist",
                         "Tadeusz Wróbel", "Unit tripped its breaker; replaced the \"room sensor\" lead.",
                         "Waiting for a replacement drain body from the supplier", "Cascade Lift Services",
                         "Walk-in cooler", "Door gasket, 36 x 80 in", "Guest found the input button; no fault",
                         "Pool circulation pump", "2031-05-12T23:48:00Z",
                         "https://api.halcyon-harbor.example/v2/work-orders?page=1", "RNV-SEA-09"],
        "ordered": ["Halcyon Harbor Seattle Waterfront", "WO-31-05815", "Passenger elevator", "WO-31-05839",
                    "Automatic sliding door"],
        "headings": [],
        "tables": [],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="json", title="Maintenance work orders API response (10 orders), May 2031", pages_or_sheets=None,
        stresses=["minified JSON: no spaces or line breaks, the whole document on one line, no final newline",
                  "a top-level object with meta, data and links; nested objects (location, asset, property, project)",
                  "arrays of objects (labor, parts) and of numbers (temperature_log), empty arrays",
                  "null values (asset, reported_by, closed_at, room, notes, next), booleans, integers including 0 and "
                  "a negative floor, decimals",
                  "objects whose keys differ from one record to the next (checklist, hold_reason, contractor, "
                  "temperature_log, project, cancel_reason, due_by)",
                  "non-ASCII names kept as UTF-8 (ë, ó); escaped double quotes inside a string; URLs"],
        checks=checks,
        notes=("UTF-8 JSON written by json.dumps(..., ensure_ascii=False, separators=(',', ':')) with no final newline: "
               "the whole file is one line of about " + str(len(raw) // 100 * 100) + " characters, key order as "
               "written. A converter may keep it as JSON, pretty-print it, fence it as code or render it as text, "
               "lists or tables; no Markdown structure is expected, so headings and tables are empty. must_contain "
               "items are whole keys or scalar values that never occur inside another key or value; the string with "
               "escaped quotes matches its raw JSON form too, because matching deletes backslashes, and the two keys "
               "with underscores match without them because matching deletes underscores. ordered follows document "
               "order: the property name in meta, the ids of orders 2 and 7 and the asset categories of orders 4 and "
               "10. The organisations, people and URLs (.example) are fictitious."))
    text = path.read_text(encoding="utf-8")
    require(json.loads(text) == obj and "\n" not in text and text.endswith("}"), "json: read-back / minified")
    require(not re.search(r'[,:]\s', re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)), "json: whitespace outside strings")
    require('\\"' in text and "Zoë" in text and "Wróbel" in text, "json: escaping")
    fields = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                fields.append(key)
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            fields.append(node)
        else:
            fields.append(json.dumps(node))

    walk(json.loads(text))
    require(None in [o["asset"] for o in JSON_ORDERS] and [] in [o["parts"] for o in JSON_ORDERS]
            and len({tuple(o) for o in JSON_ORDERS}) > 5, "json: nulls / empty arrays / varying keys")
    verify(path.name, "json", gt, text, fields=fields)
    return gt


# ===========================================================================
# 6. gen-linen-billing.pdf (not read back with a text extractor; see the module doc)
# ===========================================================================

VENDOR = "Larkspur Commercial Linen Services, LLC"
VENDOR_ADDR = "2210 Millrace Avenue, Tacoma, WA 98421"
VENDOR_CONTACT = "Phone (253) 555-0148, billing@larkspur-linen.example"
PDF_FOOTER = "Remit questions to billing@larkspur-linen.example"
INVOICE_NO = "INV-31-04417"
PDF_DETAILS = [["Invoice number", INVOICE_NO], ["Invoice date", "May 31, 2031"], ["Due date", "June 30, 2031"],
               ["Customer account", "HHH-0093"], ["Purchase order", "PO-77120"],
               ["Service period", "May 1 to May 31, 2031"]]
PDF_BILL = ["Bill to", COMPANY, "Accounts Payable", "1800 Alaskan Way, Suite 400", "Seattle, WA 98101"]
PDF_SHIP = ["Ship to", "Halcyon Harbor Seattle Waterfront", "Receiving dock, level B1", "1810 Alaskan Way",
            "Seattle, WA 98101"]
PDF_INTRO = "Commercial linen rental and laundry service for May 2031, delivered three times a week."
PDF_ITEMS = [  # item, description, quantity, unit, unit price
    ("SHT-KF", "King flat sheet, 300 thread count, white", 1840, "each", "0.62"),
    ("SHT-QF", "Queen flat sheet, 300 thread count, white", 1265, "each", "0.58"),
    ("PLC-KG", "King pillowcase, 300 thread count", 2410, "each", "0.21"),
    ("PLC-ST", "Standard pillowcase, 300 thread count", 1980, "each", "0.19"),
    ("DUV-KG", "King duvet cover with button closure", 620, "each", "1.45"),
    ("DUV-QN", "Queen duvet cover with button closure", 430, "each", "1.35"),
    ("TWL-BA", "Bath towel, 27 x 54 in, 16 lb per dozen", 3150, "each", "0.34"),
    ("TWL-HD", "Hand towel, 16 x 30 in", 2890, "each", "0.18"),
    ("TWL-WC", "Washcloth, 13 x 13 in", 2760, "each", "0.09"),
    ("MAT-BT", "Bath mat, 20 x 32 in, heavy loop", 1340, "each", "0.27"),
    ("ROB-WF", "Waffle weave bathrobe, one size", 210, "each", "1.95"),
    ("POL-TW", "Pool towel, blue and white stripe, 30 x 60 in", 1120, "each", "0.41"),
    ("TBL-RD", "Round tablecloth, 120 in, banquet white", 186, "each", "2.10"),
    ("TBL-RC", "Rectangular tablecloth, 90 x 156 in, ivory", 94, "each", "2.35"),
    ("NAP-DN", "Dinner napkin, 20 x 20 in, polyester, assorted colors", 4200, "each", "0.11"),
    ("SKT-BQ", "Banquet table skirt, 17 ft, pleated, with clips", 48, "each", "4.80"),
    ("APR-BS", "Bistro apron, black, with pocket", 260, "each", "0.55"),
    ("CHF-CT", "Chef coat, white, laundered and pressed", 175, "each", "1.20"),
    ("UNF-HK", "Housekeeping tunic, laundered and folded", 340, "each", "0.95"),
    ("MOP-WT", "Wet mop head, 24 oz, cotton blend", 520, "each", "0.38"),
    ("RAG-BR", "Bar towel, ribbed, bundle of 50", 64, "bundle", "6.25"),
    ("SPT-CL", "Stain treatment for returned items, charged per pound", 380, "lb", "0.75"),
    ("RWS-NC", "Rewash of items returned as unclean, at no charge", 96, "lb", "0.00"),
    ("LOS-RP", "Replacement charge for linen reported lost in April", 1, "lot", "418.60"),
    ("DEL-EX", "Extra delivery on Sunday, May 18, requested by the hotel", 1, "trip", "95.00"),
]
PDF_ITEMS_NOTE = "Quantities are taken from the signed delivery tickets; copies are available on request."
DISCOUNT_RATE, TAX_RATE = Decimal("0.04"), Decimal("0.101")
PDF_PAY_TEXT = "Pay by ACH transfer or by check made payable to Larkspur Commercial Linen Services, LLC."
PDF_PAYMENT = [["Payment method", "ACH transfer or check"], ["Bank", "Example Commerce Bank, Tacoma branch"],
               ["Account name", VENDOR], ["Account number", "Ending in 4410"], ["Reference", INVOICE_NO]]
PDF_TERMS = [
    ("Payment is due within 30 days of the invoice date.", []),
    ("Balances unpaid after the due date accrue a late fee of 1.5 percent per month.",
     ["The fee is waived once per calendar year on request."]),
    ("Report missing or damaged items within 5 business days of delivery.", []),
    ("Lost linen is billed at the replacement prices in the service agreement.", []),
]
PDF_DETACH = "Please detach and return this portion with your payment."


def pdf_numbers():
    items = [["Item", "Description", "Qty", "Unit", "Unit price", "Amount"]]
    subtotal = Decimal(0)
    for code, desc, qty, unit, price in PDF_ITEMS:
        amount = money(Decimal(qty) * Decimal(price))
        subtotal += amount
        items.append([code, desc, f"{qty:,}", unit, price, usd(amount)])
    discount = money(subtotal * DISCOUNT_RATE)
    tax = money((subtotal - discount) * TAX_RATE)
    total = subtotal - discount + tax
    totals = [["Subtotal", usd(subtotal)], ["Volume discount (4%)", usd(-discount, parens=True)],
              ["Sales tax (10.1%)", usd(tax)], ["Total due", usd(total)], ["Payments received", "0.00"],
              ["Balance due", usd(total)]]
    slip = [["Remit to", "Invoice number", "Customer account", "Amount due", "Amount enclosed"],
            [f"{VENDOR}, {VENDOR_ADDR}", INVOICE_NO, "HHH-0093", f"${usd(total)}", ""]]
    return items, totals, slip


def _pdf_build(path: Path, total_pages):
    rl_config.invariant = 1
    pages = []

    def furniture(canvas, doc):
        pages.append(doc.page)
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.setLineWidth(0.4)
        canvas.line(0.75 * inch, 0.68 * inch, letter[0] - 0.75 * inch, 0.68 * inch)
        canvas.drawString(0.75 * inch, 0.5 * inch, PDF_FOOTER)
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page} of {total_pages}")
        canvas.restoreState()

    st = {k: ParagraphStyle(k, **v) for k, v in {
        "vendor": dict(fontName="Helvetica-Bold", fontSize=15, leading=18, spaceAfter=3),
        "small": dict(fontName="Helvetica", fontSize=9, leading=11.5),
        "inv": dict(fontName="Helvetica-Bold", fontSize=24, leading=28, alignment=TA_RIGHT, spaceAfter=6),
        "label": dict(fontName="Helvetica-Bold", fontSize=9.5, leading=12),
        "addr": dict(fontName="Helvetica", fontSize=9.5, leading=12),
        "body": dict(fontName="Helvetica", fontSize=10, leading=13.5, spaceAfter=6),
        "cell": dict(fontName="Helvetica", fontSize=8.5, leading=10.5),
        "h2": dict(fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=12, spaceAfter=6),
        "note": dict(fontName="Helvetica-Oblique", fontSize=8.5, leading=11, spaceBefore=4),
    }.items()}

    def para(text, style="body"):
        return RLParagraph(xml_escape(text), st[style])

    items, totals, slip = pdf_numbers()
    grid = ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA3AF"))
    details = Table(PDF_DETAILS, colWidths=[1.25 * inch, 1.55 * inch], hAlign="RIGHT")
    details.setStyle(TableStyle([grid, ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
                                 ("FONT", (1, 0), (1, -1), "Helvetica", 8.5),
                                 ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF1F5"))]))
    top = Table([[[para(VENDOR, "vendor"), para(VENDOR_ADDR, "small"), para(VENDOR_CONTACT, "small")],
                  [para("INVOICE", "inv"), details]]], colWidths=[3.9 * inch, 3.1 * inch])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    addresses = Table([[[para(PDF_BILL[0], "label")] + [para(t, "addr") for t in PDF_BILL[1:]],
                        [para(PDF_SHIP[0], "label")] + [para(t, "addr") for t in PDF_SHIP[1:]]]],
                      colWidths=[3.5 * inch, 3.5 * inch], hAlign="LEFT")
    addresses.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    item_rows = [items[0]] + [[r[0], RLParagraph(xml_escape(r[1]), st["cell"])] + r[2:] for r in items[1:]]
    t_items = Table(item_rows, colWidths=[0.8 * inch, 3.05 * inch, 0.7 * inch, 0.65 * inch, 0.8 * inch, 1.0 * inch],
                    repeatRows=1, hAlign="LEFT")
    t_items.setStyle(TableStyle([grid, ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
                                 ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
                                 ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE3EA")),
                                 ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    t_totals = Table(totals, colWidths=[1.7 * inch, 1.1 * inch], hAlign="RIGHT")
    t_totals.setStyle(TableStyle([grid, ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
                                  ("FONT", (0, 3), (-1, 3), "Helvetica-Bold", 9),
                                  ("FONT", (0, 5), (-1, 5), "Helvetica-Bold", 9.5),
                                  ("ALIGN", (1, 0), (1, -1), "RIGHT")]))
    t_pay = Table(PDF_PAYMENT, colWidths=[1.6 * inch, 3.9 * inch], hAlign="LEFT")
    t_pay.setStyle(TableStyle([grid, ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
                               ("FONT", (1, 0), (1, -1), "Helvetica", 9)]))
    terms = ListFlowable(
        [ListItem([para(text)] + ([ListFlowable([ListItem(para(s)) for s in subs], bulletType="a",
                                                 bulletFormat="%s.", leftIndent=18)] if subs else []))
         for text, subs in PDF_TERMS], bulletType="1", bulletFormat="%s.", leftIndent=18)
    t_slip = Table([slip[0], [RLParagraph(xml_escape(slip[1][0]), st["cell"])] + slip[1][1:]],
                   colWidths=[2.4 * inch, 1.15 * inch, 1.2 * inch, 1.05 * inch, 1.2 * inch], hAlign="LEFT")
    t_slip.setStyle(TableStyle([grid, ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
                                ("FONT", (1, 1), (-1, 1), "Helvetica", 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story = [top, Spacer(1, 14), addresses, Spacer(1, 12), para(PDF_INTRO), t_items, para(PDF_ITEMS_NOTE, "note"),
             Spacer(1, 6), t_totals, para("Payment Instructions", "h2"), para(PDF_PAY_TEXT), t_pay,
             para("Terms and Conditions", "h2"), terms,
             KeepTogether([Spacer(1, 18), HRFlowable(width="100%", thickness=0.8, dash=(4, 3),
                                                     color=colors.HexColor("#555555"), spaceAfter=4),
                           para(PDF_DETACH, "note"), Spacer(1, 4), t_slip])]
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.9 * inch, title=f"Invoice {INVOICE_NO}",
                            author=VENDOR, subject="Linen service invoice, May 2031", creator="Billing", invariant=1)
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return max(pages)


def make_pdf():
    path = HERE / "gen-linen-billing.pdf"
    n = _pdf_build(path, 0)
    require(_pdf_build(path, n) == n, "pdf: page count changed between passes")
    require(n == 2, f"pdf: expected 2 pages, got {n}")
    items, totals, slip = pdf_numbers()
    term_lines = [x for text, subs in PDF_TERMS for x in [text] + subs]
    body_parts = ([VENDOR, VENDOR_ADDR, VENDOR_CONTACT, "INVOICE"] + [" ".join(r) for r in PDF_DETAILS]
                  + [" ".join(x) for x in zip(PDF_BILL, PDF_SHIP)] + [PDF_INTRO] + [" ".join(r) for r in items]
                  + [PDF_ITEMS_NOTE] + [" ".join(r) for r in totals] + ["Payment Instructions", PDF_PAY_TEXT]
                  + [" ".join(r) for r in PDF_PAYMENT] + ["Terms and Conditions"] + term_lines + [PDF_DETACH]
                  + [" ".join(r) for r in slip])
    furniture_text = "\n".join(f"{PDF_FOOTER} Page {k} of {n}" for k in range(1, n + 1))
    checks = {
        "must_contain": ([PDF_INTRO, "Pool towel, blue and white stripe, 30 x 60 in",
                          "Dinner napkin, 20 x 20 in, polyester, assorted colors",
                          "Stain treatment for returned items, charged per pound",
                          "Rewash of items returned as unclean, at no charge",
                          "Replacement charge for linen reported lost in April",
                          "Extra delivery on Sunday, May 18, requested by the hotel", PDF_ITEMS_NOTE, PDF_PAY_TEXT]
                         + term_lines + [PDF_DETACH]),
        "ordered": ["Accounts Payable", "Commercial linen rental and laundry service", "Waffle weave bathrobe",
                    "Extra delivery on Sunday", "Volume discount (4%)", "Example Commerce Bank, Tacoma branch",
                    "The fee is waived once per calendar year", "Amount enclosed"],
        "headings": ["INVOICE", "Payment Instructions", "Terms and Conditions"],
        "tables": [{"name": "Invoice details (ruled key-value table without a header row, right of the letterhead)",
                    "rows": PDF_DETAILS},
                   {"name": "Line items (one table over two pages, header row repeated on page 2; complete: header "
                            "row and 25 rows; description cells wrap)", "rows": items},
                   {"name": "Totals (right-aligned key-value table without a header row)", "rows": totals},
                   {"name": "Payment details (key-value table without a header row)", "rows": PDF_PAYMENT},
                   {"name": "Remittance slip (below a dashed cut line; header row and one row with an empty 'Amount "
                            "enclosed' cell)", "rows": slip}],
        "noise": [{"text": PDF_FOOTER, "max": 1}],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pdf", title=f"Invoice {INVOICE_NO}, commercial linen service, May 2031", pages_or_sheets=n,
        stresses=["generated single-column PDF (ReportLab, standard Helvetica fonts, untagged), letter pages",
                  "letterhead (company name in large bold type and two small lines) beside a large right-aligned "
                  "'INVOICE' title over a ruled details table: two blocks side by side in a borderless layout table",
                  "bill-to and ship-to address blocks side by side, each with a bold label line",
                  "a line-item table whose description cells wrap, with quantities with thousands separators, unit "
                  "prices and amounts with two decimals, a zero-priced row; it runs from page 1 to page 2 with its "
                  "header row repeated",
                  "a right-aligned totals table with a negative amount in parentheses and bold rows",
                  "two headings set by font size, a payment table, a numbered list (1.-4.) with a lettered sub-item",
                  "a dashed cut line, an italic instruction and a remittance slip table with an empty cell, kept "
                  "together at the end of page 2",
                  "running footer on every page: a contact line (left) and 'Page N of 2' (right) over a rule"],
        checks=checks,
        notes=("ReportLab 'invariant' mode pins the creation date and document ID, so the file is reproducible. The "
               "checks come from the generator's data in reading order; the file was NOT read back with any text "
               "extractor (blind protocol), only rendered to images with pdftoppm and looked at, and its font list "
               "was checked once with pdffonts (see holdout6/SELECTION.md). Layout: the top of page 1 is a borderless "
               "two-cell table, the letterhead on the left and, on the right, 'INVOICE' (24-point Helvetica-Bold) "
               "over the ruled details table; the bill-to and ship-to blocks below are another borderless two-cell "
               "table and are not checked as a table (anchors only: 'Accounts Payable'). Reading order for ordered "
               "anchors uses only items at different heights of the page, so the left/right order of side-by-side "
               "blocks does not matter. Headings: 'INVOICE' and the two 13-point Helvetica-Bold section headings; the "
               "15-point company name in the letterhead is not listed (it repeats in the payment table and the slip, "
               "so it is a name, not a heading), nor the bold 'Bill to' / 'Ship to' labels. Tables: the details, "
               "totals and payment tables have no header row (their first row is data); the line-item table starts "
               "on page 1 and continues on page 2 with its header row repeated (repeatRows=1), so the expected table "
               "is the header row and all 25 rows once, and a repeated header row inside a converted table costs "
               "precision only; description cells wrap inside the cell and each expected cell is the whole text with "
               "single spaces; quantities and amounts are text as printed ('1,840', '1,140.80'), compared without the "
               "thousands comma; the discount is '(" + totals[1][1][1:-1] + ")'; the slip's 'Amount enclosed' cell is "
               "empty (not scored) and its 'Remit to' cell wraps. must_contain: the intro line, six item "
               "descriptions of at least 6 words, the note under the items, the payment sentence, every term and "
               "sub-term and the detach instruction (phrases are generator strings and may contain hyphens, which are "
               "ASCII). ordered: 8 anchors from the address block to the slip. Noise: the footer contact line ('"
               + PDF_FOOTER + "') is printed once per page (twice) and occurs nowhere in the body (the letterhead "
               "prints the address with 'Phone ...', not this line), max 1; 'Page N of 2' is not counted (it differs "
               "per page). No hyphenation (ReportLab does not hyphenate by default): absent is empty."))
    verify(path.name, "pdf", gt, "\n".join(body_parts) + "\n" + furniture_text, body_text="\n".join(body_parts),
           furniture=furniture_text)
    return gt


# ===========================================================================

def main():
    GT_DIR.mkdir(parents=True, exist_ok=True)
    for make in (make_docx, make_xlsx, make_pptx, make_csv, make_json, make_pdf):
        gt = make()
        counts = ", ".join(f"{k} {len(v)}" for k, v in gt["checks"].items())
        print(f"{gt['file']:28s} {gt['sha256']}  ok ({counts})")
    for f in sorted(GT_DIR.glob("pub-*.json")):  # the public answer files are checked against the same rules
        gt = json.loads(f.read_text(encoding="utf-8"))
        errors, warnings = validate_ground_truth(gt, f.name)
        require(not errors and not warnings, f"{f.name}: validateGroundTruth rules: {errors + warnings}")
        require(gt["sha256"] == sha256_of(HERE / gt["file"]), f"{f.name}: sha256 differs from the file")
        c = gt["checks"]
        for s in c["must_contain"] + c["ordered"]:
            require(not re.search(r"[^\x00-\x7f]|[\"']|[A-Za-z]-[A-Za-z]", s), f"{f.name}: phrase {s!r}")
        for h in c["headings"]:
            require(not re.search(r"[-–—\"'’]", h), f"{f.name}: heading {h!r}")
        print(f"{gt['file']:28s} {gt['sha256']}  answer file passes the validation rules")
    print(f"libraries: {lib_versions()}")


if __name__ == "__main__":
    try:
        main()
    except CheckError as exc:
        print(f"CHECK FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
