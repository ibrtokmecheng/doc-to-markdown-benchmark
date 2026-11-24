#!/usr/bin/env python3
"""Generate the synthetic part of the FIFTH held-out doc-to-markdown test set (holdout5/).

Writes six ordinary business documents to holdout5/ and one ground-truth JSON per document to
holdout5/ground-truth/<file>.json (same schema as the earlier sets, checked by score.mjs):

    gen-migration-sow.docx     Word statement of work: Title style, headings at three levels with typed section numbers,
                               two-level bullets, a numbered list with lettered sub-items, a second numbered list that
                               restarts at 1, a payment table with two header rows (cells merged down and across), body
                               cells holding two paragraphs and a total row whose label is merged across two columns, a rate
                               table with header cells broken by a line break and a total row merged across three columns,
                               captions, an italic note, bold and italic runs, a signature table with empty cells, page
                               header and footer.
    gen-asset-register.xlsx    Workbook with three sheets: a fixed asset register (merged title and note rows, two header
                               rows with groups merged across two and three columns and five headers merged down, header
                               text with line breaks, asset tags stored as text with leading zeros, ISO dates, amounts with
                               two decimals and thousands separators, formulas saved with computed values, a total row,
                               frozen panes, a note below the table); disposals with mm/dd/yyyy dates and gains or losses in
                               parentheses; locations with booleans, d-mmm-yyyy dates, percentages and an autofilter.
    gen-support-review.pptx    Seven-slide customer support review: title slide, bulleted agenda, a native table with two
                               header rows (merged across and down) and a total row, a Comparison slide (two headings, two
                               bulleted bodies with second-level items), a Title Only slide with two free text boxes, a
                               Section Header slide, two-level bullets, speaker notes.
    gen-shipment-log.csv       Shipment log export: UTF-8 without a byte order mark, every field quoted, LF record ends,
                               fields with commas, doubled quotes and line breaks, decimals without thousands separators,
                               ISO dates and timestamps, empty fields, non-ASCII place names.
    gen-event-agenda.json      Event agenda export: pretty-printed with 4-space indentation, a top-level object with an
                               event object and an array of 8 sessions, nested objects and arrays of objects, keys that
                               differ between records, nulls, booleans, empty arrays, escaped quotes, non-ASCII text,
                               timestamps with UTC offsets.
    gen-safety-report.pdf      ReportLab quarterly safety report, 2 pages: title and subtitle, a key-value table without a
                               header row, headings by font size, an incidents table with two header rows (cells spanning
                               across and down) and a total row, a numbered list with lettered sub-items, a findings table
                               with wrapped cells that continues on page 2 with its header repeated, a bulleted list, an
                               italic note, running header and footer.

The content is new (not reused from holdout4/; the generators of the earlier sets were not opened). Everything is fixed
in this file: no randomness, no clock. Every ground-truth item is derived from the same Python data that is written into
the document. After writing, the DOCX, XLSX, PPTX, CSV and JSON files are read back (python-docx, openpyxl, python-pptx,
csv, json) and every check is verified against the read-back text, with the audit rules of the earlier sets (no file
name or converter-added text in a check; prose phrases of at least 6 words that occur once; data-file items are whole,
distinctive fields; ordered anchors unique and in reading order, never from speaker notes). The PDF is NOT read back with
any text extractor (blind protocol): its checks are verified against the generator's own data in reading order, and its
pages were only rendered to images (pdftoppm) and looked at. Every answer file, including the three public ones, is
checked against the validation rules of score.mjs validateGroundTruth (re-implemented below; score.mjs is not run). Any
mismatch aborts with exit status 1.

No converter (PackForAI, MarkItDown or other) is run here or was run while writing the answers.

Run from the benchmark folder (ephemeral environment, no global installs):

    uv run --with python-docx --with openpyxl --with python-pptx --with reportlab \
        python3 -I holdout5/generate_holdout5.py

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
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from openpyxl.styles import Alignment, Font
from pptx import Presentation
from pptx.util import Inches
from pptx.util import Pt as PPt
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph as RLParagraph, SimpleDocTemplate, Spacer, Table, \
    TableStyle

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground-truth"
ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)
LICENSE = ("Synthetic document written for the fifth held-out benchmark set and generated by "
           "holdout5/generate_holdout5.py; no third-party material. All organisations, people, addresses, phone "
           "numbers, e-mail domains and figures are fictitious.")
LIBS = ("python-docx", "openpyxl", "python-pptx", "lxml", "reportlab")
MIN_PHRASE_WORDS = 6
COMPANY = "Northgate Precision Components, LLC"
CHECK_KEYS = ("must_contain", "ordered", "headings", "tables", "noise", "absent")
FORMATS = ("pdf", "docx", "xlsx", "pptx", "csv", "json")


def lib_versions() -> str:
    return ", ".join(f"{n} {metadata.version(n)}" for n in LIBS) + f", Python {sys.version.split()[0]}"


# ---------------------------------------------------------------------------
# Matching rules (normalize() of score.mjs) and self-checks
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
        "notes": notes + f" Generated by holdout5/generate_holdout5.py with {lib_versions()}; no converter was run "
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


def one_decimal(d: Decimal) -> Decimal:
    """Rounds to one decimal; refuses values on a rounding boundary."""
    scaled = d * 10
    frac = abs(scaled - scaled.to_integral_value(rounding="ROUND_FLOOR"))
    require(abs(frac - Decimal("0.5")) > Decimal("1e-6"), f"value {d} on a rounding boundary")
    return d.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


# ===========================================================================
# 1. gen-migration-sow.docx
# ===========================================================================

DOCX_TITLE = "Statement of Work: ERP Data Migration"
DOCX_HEADER = COMPANY
DOCX_FOOTER = "SOW-2029-014, version 2, issued March 5, 2029"
SOW_FEE = Decimal("185000")
MILESTONES = [  # (code, description, target date, percent of fee, accepted by)
    ("M1", "Mapping workbook approved", "April 20, 2029", 15, "Data owners"),
    ("M2", "First test load reconciled", "May 25, 2029", 20, "Finance controller"),
    ("M3", "Third test load reconciled", "July 13, 2029", 25, "Finance controller"),
    ("M4", "Production cutover complete", "August 6, 2029", 30, "Chief Operating Officer"),
    ("M5", "Final report signed", "August 31, 2029", 10, "Project sponsor"),
]


def docx_payment_table():
    rows = [["Milestone", "Target date", "Payment", "", "Accepted by"],
            ["", "", "Percent", "Amount (USD)", ""]]
    total = Decimal(0)
    for code, text, when, pct, who in MILESTONES:
        amount = money(SOW_FEE * pct / 100)
        total += amount
        rows.append([f"{code}\n{text}", when, f"{pct}%", f"${amount:,.2f}", who])
    require(total == SOW_FEE and sum(m[3] for m in MILESTONES) == 100, "docx: payment schedule does not add up")
    rows.append(["Total", "", "100%", f"${total:,.2f}", ""])
    return rows


DOCX_T1 = docx_payment_table()
DOCX_T1_MERGES = [(0, 0, 1, 0), (0, 1, 1, 1), (0, 2, 0, 3), (0, 4, 1, 4), (len(DOCX_T1) - 1, 0, len(DOCX_T1) - 1, 1)]
RATES = [  # (role, hourly rate, estimated hours per change)
    ("Data architect", "210.00", 12),
    ("Migration developer", "165.00", 30),
    ("Quality analyst", "120.00", 16),
    ("Project manager", "185.00", 6),
]


def docx_rate_table():
    rows = [["Role", "Hourly rate\n(USD)", "Estimated hours\n(per change)", "Example cost\n(USD)"]]
    total = Decimal(0)
    for role, rate, hours in RATES:
        cost = money(Decimal(rate) * hours)
        total += cost
        rows.append([role, f"{Decimal(rate):,.2f}", str(hours), f"{cost:,.2f}"])
    rows.append(["Total of the example costs", "", "", f"{total:,.2f}"])
    return rows


DOCX_T2 = docx_rate_table()
DOCX_T2_MERGES = [(len(DOCX_T2) - 1, 0, len(DOCX_T2) - 1, 2)]
DOCX_SIGN = [
    ["Party", "Name and title", "Signature", "Date"],
    ["Northgate Precision Components", "Marguerite Okafor, Chief Operating Officer", "", ""],
    ["Halvorsen Data Services", "Søren Halvorsen, Managing Director", "", ""],
]

# (kind, payload). Runs: (text, "" | "b" | "i").
DOCX_BLOCKS = [
    ("title", DOCX_TITLE),
    ("para", [("Prepared by the Information Technology Department for the vendor Halvorsen Data Services", "i")]),
    ("para", [("Project sponsor: ", "b"), ("Chief Operating Officer, Northgate Precision Components", "")]),
    ("h1", "1. Background"),
    ("para", [("Northgate is replacing its legacy order and inventory system with a cloud ERP platform during 2029.",
               "")]),
    ("para", [("This statement of work describes the data migration services, the deliverables, the schedule and the "
               "payment terms.", "")]),
    ("h1", "2. Scope of Services"),
    ("h2", "2.1 In Scope"),
    ("bullet", (0, "Extract customer, supplier, item and open order records from the legacy system")),
    ("bullet", (1, "Include inactive customers that placed an order in the last three years")),
    ("bullet", (0, "Remove duplicate item masters and standardize the units of measure")),
    ("bullet", (0, "Load the cleansed records into the test and production environments of the new platform")),
    ("bullet", (1, "Every load is followed by a written reconciliation report")),
    ("h2", "2.2 Out of Scope"),
    ("para", [("The following work is excluded from this statement of work:", "")]),
    ("bullet", (0, "Migration of closed purchase orders dated before January 1, 2026")),
    ("bullet", (0, "Development of custom reports and training of end users")),
    ("h1", "3. Deliverables"),
    ("number", (0, "A data mapping workbook that covers every migrated field.")),
    ("number", (1, "Approved by the Northgate data owners before the first test load.")),
    ("number", (1, "Updated by the vendor after each test load.")),
    ("number", (0, "Three test loads, each with a reconciliation report.")),
    ("number", (0, "A production cutover plan that includes a rollback procedure.")),
    ("number", (1, "Rehearsed once on a weekend chosen by Northgate.")),
    ("number", (0, "A final migration report signed by both project managers.")),
    ("h1", "4. Schedule and Payments"),
    ("para", [("Each milestone payment is due within 30 days of the written acceptance of that milestone.", "")]),
    ("caption", "Table 1. Milestones and payment schedule"),
    ("table", 1),
    ("note", "Note: Amounts exclude sales tax. Travel is billed separately at cost and must be approved in advance."),
    ("h2", "4.1 Rate Card for Change Requests"),
    ("para", [("Work outside the scope above is priced from the hourly rates in Table 2 and needs a signed change "
               "request.", "")]),
    ("caption", "Table 2. Hourly rates for change requests"),
    ("table", 2),
    ("h3", "4.1.1 Approval of Change Requests"),
    ("number2", (0, "The vendor submits a written estimate within five business days.")),
    ("number2", (0, "The Northgate project manager approves or rejects the estimate in writing.")),
    ("number2", (0, "Approved changes are added to the invoice of the next milestone.")),
    ("h1", "5. Acceptance"),
    ("para", [("Northgate reviews each deliverable within ", ""), ("ten business days", "b"),
              (" of delivery. A deliverable that is not rejected in writing within ", ""),
              ("fifteen business days", "i"), (" is deemed accepted.", "")]),
    ("h1", "6. Signatures"),
    ("para", [("Authorized representatives of both parties sign below to accept this statement of work.", "")]),
    ("table", 3),
]

DOCX_MUST = [
    "Prepared by the Information Technology Department for the vendor Halvorsen Data Services",
    "Project sponsor: Chief Operating Officer, Northgate Precision Components",
    "Northgate is replacing its legacy order and inventory system with a cloud ERP platform during 2029.",
    "This statement of work describes the data migration services, the deliverables, the schedule and the payment "
    "terms.",
    "Extract customer, supplier, item and open order records from the legacy system",
    "Include inactive customers that placed an order in the last three years",
    "Remove duplicate item masters and standardize the units of measure",
    "Load the cleansed records into the test and production environments of the new platform",
    "Every load is followed by a written reconciliation report",
    "The following work is excluded from this statement of work:",
    "Migration of closed purchase orders dated before January 1, 2026",
    "Development of custom reports and training of end users",
    "A data mapping workbook that covers every migrated field.",
    "Approved by the Northgate data owners before the first test load.",
    "Updated by the vendor after each test load.",
    "Three test loads, each with a reconciliation report.",
    "A production cutover plan that includes a rollback procedure.",
    "Rehearsed once on a weekend chosen by Northgate.",
    "A final migration report signed by both project managers.",
    "Each milestone payment is due within 30 days of the written acceptance of that milestone.",
    "Table 1. Milestones and payment schedule",
    "Note: Amounts exclude sales tax. Travel is billed separately at cost and must be approved in advance.",
    "Work outside the scope above is priced from the hourly rates in Table 2 and needs a signed change request.",
    "Table 2. Hourly rates for change requests",
    "The vendor submits a written estimate within five business days.",
    "The Northgate project manager approves or rejects the estimate in writing.",
    "Approved changes are added to the invoice of the next milestone.",
    "Northgate reviews each deliverable within ten business days of delivery.",
    "A deliverable that is not rejected in writing within fifteen business days is deemed accepted.",
    "Authorized representatives of both parties sign below to accept this statement of work.",
]
DOCX_ORDERED = [
    DOCX_TITLE,
    "Northgate is replacing its legacy order and inventory system",
    "Include inactive customers that placed an order",
    "Rehearsed once on a weekend chosen by Northgate",
    "Production cutover complete",
    "Migration developer",
    "Approved changes are added to the invoice",
    "Authorized representatives of both parties sign below",
]

BULLET_NUM_ID, NUMBER_NUM_ID, NUMBER2_NUM_ID = 71, 72, 73


def _docx_numbering(document):
    """A two-level bullet list, a 1./a. list and a second instance of it that restarts at 1."""
    numbering = document.part.numbering_part.element
    lvl = ('<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text}"/>'
           '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{left}" w:hanging="{hang}"/></w:pPr>{rpr}</w:lvl>')
    sym = '<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr>'
    cour = '<w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:hint="default"/></w:rPr>'
    abstracts = [
        (BULLET_NUM_ID, lvl.format(i=0, fmt="bullet", text="", left=720, hang=360, rpr=sym)
         + lvl.format(i=1, fmt="bullet", text="o", left=1440, hang=360, rpr=cour)),
        (NUMBER_NUM_ID, lvl.format(i=0, fmt="decimal", text="%1.", left=720, hang=360, rpr="")
         + lvl.format(i=1, fmt="lowerLetter", text="%2.", left=1440, hang=360, rpr="")),
    ]
    first_num = numbering.find(qn("w:num"))
    for aid, levels in abstracts:
        first_num.addprevious(parse_xml(
            f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{aid}"><w:multiLevelType w:val="hybridMultilevel"/>'
            f'{levels}</w:abstractNum>'))
    for num_id in (BULLET_NUM_ID, NUMBER_NUM_ID):
        numbering.append(parse_xml(
            f'<w:num {nsdecls("w")} w:numId="{num_id}"><w:abstractNumId w:val="{num_id}"/></w:num>'))
    numbering.append(parse_xml(
        f'<w:num {nsdecls("w")} w:numId="{NUMBER2_NUM_ID}"><w:abstractNumId w:val="{NUMBER_NUM_ID}"/>'
        '<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'))


def _set_num(p, num_id, level):
    num_pr = p._p.get_or_add_pPr().get_or_add_numPr()
    num_pr.get_or_add_ilvl().val = level
    num_pr.get_or_add_numId().val = num_id


def _docx_table(document, grid, merges, header_rows, right_from=None, two_paragraph_cells=False, bold_last=False):
    rows, cols = len(grid), len(grid[0])
    table = document.add_table(rows=rows, cols=cols)
    table.style = "Table Grid"
    covered = set()
    for r0, c0, r1, c1 in merges:
        table.cell(r0, c0).merge(table.cell(r1, c1))
        covered |= {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)} - {(r0, c0)}
    for ri, row in enumerate(grid):
        if ri < header_rows:
            table.rows[ri]._tr.get_or_add_trPr().append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        for ci, value in enumerate(row):
            if (ri, ci) in covered:
                require(value == "", f"docx: covered cell ({ri},{ci}) has text")
                continue
            cell = table.cell(ri, ci)
            if two_paragraph_cells and ri >= header_rows and "\n" in value:
                first, second = value.split("\n")
                cell.text = first
                cell.add_paragraph(second)
            else:
                cell.text = value  # a '\n' becomes a line break (w:br) inside one paragraph
            for para in cell.paragraphs:
                if ri < header_rows or (bold_last and ri == rows - 1):
                    for run in para.runs:
                        run.bold = True
                if ri < header_rows:
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif right_from is not None and ci >= right_from:
                    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def build_docx(path: Path):
    document = docx.Document()
    for needed in ("Title", "Heading 1", "Heading 2", "Heading 3", "List Paragraph", "Table Grid", "Caption"):
        require(needed in {s.name for s in document.styles}, f"docx: template lacks style {needed!r}")
    _docx_numbering(document)
    section = document.sections[0]
    section.header.paragraphs[0].text = DOCX_HEADER
    section.footer.paragraphs[0].text = DOCX_FOOTER
    for kind, payload in DOCX_BLOCKS:
        if kind == "title":
            document.add_paragraph(payload, style="Title")
        elif kind in ("h1", "h2", "h3"):
            document.add_heading(payload, level=int(kind[1]))
        elif kind == "caption":
            document.add_paragraph(payload, style="Caption")
        elif kind == "note":
            p = document.add_paragraph()
            run = p.add_run(payload)
            run.italic = True
            run.font.size = Pt(9)
        elif kind == "para":
            p = document.add_paragraph()
            for text, style in payload:
                run = p.add_run(text)
                run.bold = style == "b" or None
                run.italic = style == "i" or None
        elif kind in ("bullet", "number", "number2"):
            level, text = payload
            p = document.add_paragraph(text, style="List Paragraph")
            _set_num(p, {"bullet": BULLET_NUM_ID, "number": NUMBER_NUM_ID, "number2": NUMBER2_NUM_ID}[kind], level)
        elif kind == "table":
            if payload == 1:
                _docx_table(document, DOCX_T1, DOCX_T1_MERGES, 2, right_from=2, two_paragraph_cells=True,
                            bold_last=True)
            elif payload == 2:
                _docx_table(document, DOCX_T2, DOCX_T2_MERGES, 1, right_from=1, bold_last=True)
            else:
                _docx_table(document, DOCX_SIGN, [], 1)
        else:
            raise ValueError(kind)
    for para in document.paragraphs:
        if para.style.name == "Normal":
            para.paragraph_format.space_after = Pt(6)
    props = document.core_properties
    props.title = DOCX_TITLE
    props.subject = "ERP data migration services"
    props.author = "Information Technology"
    props.last_modified_by = "Information Technology"
    props.comments = ""
    props.keywords = ""
    props.category = ""
    props.revision = 2
    props.created = dt.datetime(2029, 2, 12, 10, 0, 0)
    props.modified = dt.datetime(2029, 3, 5, 15, 40, 0)
    document.save(path)
    pin_ooxml(path, "2029-02-12T10:00:00Z", "2029-03-05T15:40:00Z")


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
    texts, headings, tables, items, br_cells, two_para_cells = [], [], [], [], 0, 0
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, document)
            text = _para_text(child)
            texts.append(text)
            num_pr = child.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
            if p.style.name.startswith("Heading"):
                require(num_pr is None, "docx: heading with list numbering")
                headings.append(text)
            elif num_pr is not None:
                items.append((int(num_pr.find(qn("w:numId")).get(qn("w:val"))),
                              int(num_pr.find(qn("w:ilvl")).get(qn("w:val"))), text))
        elif child.tag == qn("w:tbl"):
            grid = []
            for tr in child.iter(qn("w:tr")):
                row = []
                for tc in tr.iter(qn("w:tc")):
                    pr = tc.find(qn("w:tcPr"))
                    span = pr.find(qn("w:gridSpan")) if pr is not None else None
                    vmerge = pr.find(qn("w:vMerge")) if pr is not None else None
                    paras = list(tc.iter(qn("w:p")))
                    br_cells += any(p.find(f".//{qn('w:br')}") is not None for p in paras)
                    two_para_cells += len([p for p in paras if _para_text(p)]) == 2
                    text = "\n".join(_para_text(p) for p in paras)
                    if vmerge is not None and vmerge.get(qn("w:val")) != "restart":
                        text = ""  # continuation of a vertically merged cell
                    n = int(span.get(qn("w:val"))) if span is not None else 1
                    row += [text] + [""] * (n - 1)
                grid.append(row)
            tables.append(grid)
            texts += [" ".join(row) for row in grid]
    header = document.sections[0].header.paragraphs[0].text
    footer = document.sections[0].footer.paragraphs[0].text
    return "\n".join(texts), headings, tables, items, header, footer, br_cells, two_para_cells


def make_docx():
    path = HERE / "gen-migration-sow.docx"
    build_docx(path)
    headings = [p for k, p in DOCX_BLOCKS if k in ("h1", "h2", "h3")]
    checks = {
        "must_contain": DOCX_MUST,
        "ordered": DOCX_ORDERED,
        "headings": headings,
        "tables": [
            {"name": "Table 1. Milestones and payment schedule (two header rows: 'Milestone', 'Target date' and "
                     "'Accepted by' merged down, 'Payment' merged across 'Percent' and 'Amount (USD)'; milestone cells "
                     "with two paragraphs; total row with its label merged across two columns)", "rows": DOCX_T1},
            {"name": "Table 2. Hourly rates for change requests (header cells broken by a line break; total row with "
                     "its label merged across three columns)", "rows": DOCX_T2},
            {"name": "Signature table (header row, two parties, empty signature and date cells)", "rows": DOCX_SIGN},
        ],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="docx", title=DOCX_TITLE, pages_or_sheets=None,
        stresses=["Title style, then an italic line and a line with a bold label run",
                  "Heading 1 / Heading 2 / Heading 3 with typed section numbers in the heading text (1., 2.1, 4.1.1)",
                  "two-level bulleted list; a numbered list with lettered second-level items; a second numbered list "
                  "that restarts at 1 (a new w:num with startOverride); a one-level bulleted list",
                  "payment table with two header rows: three header cells merged down (vMerge), one merged across two "
                  "columns (gridSpan 2); milestone cells holding two paragraphs; a bold total row whose label is "
                  "merged across two columns; amounts with thousands separators and a currency sign, percentages",
                  "rate table whose header cells contain a line break (w:br), a bold total row whose label is merged "
                  "across three columns",
                  "Caption-style table titles, an italic 9-point note under a table",
                  "bold and italic runs inside a sentence; a signature table with empty cells; a non-ASCII name",
                  "page header and footer text"],
        checks=checks,
        notes=("The headings are Word Heading 1/2/3 paragraphs whose section numbers are typed as text ('4.1.1 "
               "Approval of Change Requests'), not list numbering, so the expected headings include the numbers. The "
               "document title uses the Title style and is the first ordered anchor, not a heading (as in the earlier "
               "sets). Tables: in Table 1 'Milestone', 'Target date' and 'Accepted by' are merged down over both header "
               "rows and 'Payment' across 'Percent' and 'Amount (USD)'; each milestone cell holds two paragraphs (code "
               "and description), written with '\\n' between them (normalization makes it a space); the Total row has "
               "its label merged across the first two columns. Table 2's header cells ('Hourly rate' / '(USD)', ...) "
               "are broken by a line break inside one paragraph, also written with '\\n'; its last row has 'Total of "
               "the example costs' merged across the first three columns. A merged cell's text is in its top-left grid "
               "position and the covered positions are empty strings (not scored). Amounts are text as typed "
               "('$27,750.00', '4,950.00'); the table rule compares them with the thousands commas removed on both "
               "sides. The signature table's signature and date cells are empty. Lists: the In Scope list has two "
               "levels; the Deliverables list is numbered 1-4 with lettered sub-items (a., b.); the Approval of Change "
               "Requests list is a second instance of the same numbering that restarts at 1; the Out of Scope list is "
               "a one-level bulleted list; list numbers and bullets are drawn by Word, not typed. must_contain keeps "
               "every paragraph, list item, caption and note of at least 6 words, the paragraph with bold 'ten "
               "business days' and italic 'fifteen business days' split at its sentences (normalization deletes '*' "
               "and '_'). Page header ('" + DOCX_HEADER + "') and footer ('" + DOCX_FOOTER + "') are stored once "
               "each and are not checked; including or dropping them are both faithful. No footnotes, comments, "
               "tracked changes, hyperlinks or hyphenation: noise and absent are empty."))
    text, found_headings, tables, items, header, footer, br_cells, two_para = read_docx(path)
    require(header == DOCX_HEADER and footer == DOCX_FOOTER, "docx: header/footer")
    num_of = {"bullet": BULLET_NUM_ID, "number": NUMBER_NUM_ID, "number2": NUMBER2_NUM_ID}
    require(items == [(num_of[k], lvl, t) for k, p in DOCX_BLOCKS if k in num_of for lvl, t in [p]],
            "docx: list items/levels read back differ")
    require(br_cells == 3, f"docx: expected 3 header cells with a line break, got {br_cells}")
    require(two_para == len(MILESTONES), f"docx: expected {len(MILESTONES)} two-paragraph cells, got {two_para}")
    verify(path.name, "docx", gt, text, headings_found=found_headings, tables_found=tables)
    require(normalize(DOCX_FOOTER) not in normalize(text), "docx: footer text also in the body")
    return gt


# ===========================================================================
# 2. gen-asset-register.xlsx
# ===========================================================================

SHEET1 = "Fixed Assets"
XLSX_TITLE = "Fixed Asset Register, Plant 2, as of December 31, 2029"
XLSX_NOTE = "Costs in U.S. dollars. Straight-line depreciation over the useful life, no salvage value."
XLSX_AFTER = "Assets that cost less than $5,000 are expensed when bought and are not listed in this register."
FMT_MONEY = "#,##0.00"
FMT_SIGNED = "#,##0.00;(#,##0.00)"
FMT_INT = "#,##0"
FMT_PCT1 = "0.0%"
FMT_ISO = "yyyy-mm-dd"
FMT_DMY = "d-mmm-yyyy"
FMT_MDY = "mm/dd/yyyy"
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ASSETS = [  # (tag stored as text, description, location, acquired, cost, life in years, full years to 2029-12-31, status)
    ("00412", "CNC lathe, 8-axis", "Machining bay A", (2024, 3, 18), "286500.00", 10, 5, "In service"),
    ("00418", "Coordinate measuring machine", "Quality lab", (2025, 1, 9), "142800.00", 8, 4, "In service"),
    ("00431", "Heat treatment furnace", "Heat treatment", (2019, 6, 3), "418250.00", 10, 10, "Fully depreciated"),
    ("00457", "Electric forklift, 3 t", "Warehouse", (2027, 9, 14), "38975.50", 6, 2, "In service"),
    ("00463", "Laser marking station", "Assembly line 2", (2028, 2, 27), "61420.00", 7, 1, "Idle"),
    ("00470", "Air compressor, 75 kW", "Utility room", (2026, 11, 2), "47360.00", 12, 3, "In service"),
    ("00488", "Robotic welding cell", "Assembly line 1", (2029, 4, 22), "512900.00", 10, 0, "Commissioning"),
]
DISPOSALS = [  # (tag, description, date, proceeds, net book value at disposal, method)
    ("00297", "Manual milling machine", (2029, 2, 14), "6500.00", "4180.00", "Sold to a dealer"),
    ("00305", "Diesel forklift, 2.5 t", (2029, 5, 30), "3200.00", "5875.25", "Trade-in"),
    ("00352", "Paint booth fans", (2029, 8, 7), "0.00", "1240.00", "Scrapped"),
    ("00366", "Office copier", (2029, 11, 19), "450.00", "0.00", "Sold to an employee"),
]
DISP_HEADER = ["Asset tag", "Description", "Disposal date", "Proceeds (USD)", "Net book value (USD)",
               "Gain or (loss) (USD)", "Method"]
LOCATIONS = [  # (code stored as text, name, square feet, insured, last inspection); share of cost is computed
    ("0101", "Machining bay A", 18400, True, (2029, 9, 12)),
    ("0102", "Quality lab", 2650, True, (2029, 6, 3)),
    ("0205", "Heat treatment", 6100, True, (2029, 10, 28)),
    ("0310", "Warehouse", 24750, False, (2028, 12, 5)),
    ("0420", "Assembly line 1", 15200, True, (2029, 11, 4)),
    ("0421", "Assembly line 2", 14800, True, (2029, 11, 4)),
    ("0590", "Utility room", 1900, False, (2027, 7, 21)),
]
LOC_HEADER = ["Code", "Location", "Square feet", "Insured", "Last inspection", "Share of register cost"]


def xlsx_display(value, fmt) -> str:
    """Cell text as Excel (en-US) shows it, for the number formats used here."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if fmt == FMT_ISO:
        return f"{value.year}-{value.month:02d}-{value.day:02d}"
    if fmt == FMT_DMY:
        return f"{value.day}-{MONTH_ABBR[value.month - 1]}-{value.year}"
    if fmt == FMT_MDY:
        return f"{value.month:02d}/{value.day:02d}/{value.year}"
    d = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if fmt in (FMT_MONEY, FMT_SIGNED):
        q = money(d)
        require(q == d, f"xlsx: value {d} has more than two decimals")
        if q < 0:
            require(fmt == FMT_SIGNED, "xlsx: negative value without a negative section")
            return f"({-q:,.2f})"
        return f"{q:,.2f}"
    if fmt == FMT_INT:
        require(d == d.to_integral_value() and d >= 0, "xlsx: whole-number cell")
        return f"{d:,.0f}"
    if fmt == FMT_PCT1:
        return f"{pct1(d)}%"
    if fmt == "General":
        require(d == d.to_integral_value(), "xlsx: integer cell")
        return str(int(d))
    raise ValueError(f"unexpected cell {value!r} with format {fmt!r}")


def xlsx_model():
    """{sheet: {"rows": [[(value, format, formula)]], "first": first row}} with formula values precomputed."""
    top = 3
    first_body = top + 2
    last_body = first_body + len(ASSETS) - 1
    header1 = ["Asset tag", "Description", "Location", "Acquisition", None, "Depreciation", None, None,
               "Net book value\n(USD)", "Status"]
    header2 = [None, None, None, "Date", "Cost\n(USD)", "Life\n(years)", "Annual expense\n(USD)",
               "Accumulated\n(USD)", None, None]
    register = [[(h, "General", None) for h in header1], [(h, "General", None) for h in header2]]
    sums = [Decimal(0)] * 4
    for k, (tag, desc, loc, acq, cost, life, years, status) in enumerate(ASSETS):
        r = first_body + k
        cost_d = Decimal(cost)
        annual = money(cost_d / life)
        accumulated = min(cost_d, annual * years)
        nbv = cost_d - accumulated
        for i, v in enumerate((cost_d, annual, accumulated, nbv)):
            sums[i] += v
        register.append([(tag, "@", None), (desc, "General", None), (loc, "General", None),
                         (dt.datetime(*acq), FMT_ISO, None), (cost_d, FMT_MONEY, None), (life, "General", None),
                         (annual, FMT_MONEY, f"ROUND(E{r}/F{r},2)"),
                         (accumulated, FMT_MONEY, f"MIN(E{r},G{r}*{years})"),
                         (nbv, FMT_MONEY, f"E{r}-H{r}"), (status, "General", None)])
    total = [("Total", "General", None), (None, None, None), (None, None, None), (None, None, None)]
    total += [(sums[0], FMT_MONEY, f"SUM(E{first_body}:E{last_body})"), (None, None, None),
              (sums[1], FMT_MONEY, f"SUM(G{first_body}:G{last_body})"),
              (sums[2], FMT_MONEY, f"SUM(H{first_body}:H{last_body})"),
              (sums[3], FMT_MONEY, f"SUM(I{first_body}:I{last_body})"), (None, None, None)]
    register.append(total)
    disposals = [[(h, "General", None) for h in DISP_HEADER]]
    for k, (tag, desc, when, proceeds, nbv, method) in enumerate(DISPOSALS):
        r = 2 + k
        gain = Decimal(proceeds) - Decimal(nbv)
        disposals.append([(tag, "@", None), (desc, "General", None), (dt.datetime(*when), FMT_MDY, None),
                          (Decimal(proceeds), FMT_MONEY, None), (Decimal(nbv), FMT_MONEY, None),
                          (gain, FMT_SIGNED, f"D{r}-E{r}"), (method, "General", None)])
    locations = [[(h, "General", None) for h in LOC_HEADER]]
    total_cost = sum(Decimal(a[4]) for a in ASSETS)
    for code, name, sqft, insured, inspected in LOCATIONS:
        share = (sum(Decimal(a[4]) for a in ASSETS if a[2] == name) / total_cost).quantize(Decimal("0.000001"))
        locations.append([(code, "@", None), (name, "General", None), (sqft, FMT_INT, None), (insured, "General", None),
                          (dt.datetime(*inspected), FMT_DMY, None), (share, FMT_PCT1, None)])
    return {SHEET1: {"rows": register, "first": top}, "Disposals": {"rows": disposals, "first": 1},
            "Locations": {"rows": locations, "first": 1}}


def _xlsx_value(value):
    return float(value) if isinstance(value, Decimal) else value


def build_xlsx(path: Path, model):
    wb = openpyxl.Workbook()
    cached = {}
    for index, (name, sheet) in enumerate(model.items()):
        ws = wb.active if index == 0 else wb.create_sheet(name)
        ws.title = name
        xml_name = f"xl/worksheets/sheet{index + 1}.xml"
        first, rows = sheet["first"], sheet["rows"]
        header_rows = 2 if name == SHEET1 else 1
        if name == SHEET1:
            ws.cell(row=1, column=1, value=XLSX_TITLE).font = Font(bold=True, size=14)
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)
            ws.cell(row=2, column=1, value=XLSX_NOTE).font = Font(italic=True, size=9)
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=10)
            for col in (1, 2, 3, 9, 10):
                ws.merge_cells(start_row=first, start_column=col, end_row=first + 1, end_column=col)
            ws.merge_cells(start_row=first, start_column=4, end_row=first, end_column=5)
            ws.merge_cells(start_row=first, start_column=6, end_row=first, end_column=8)
            note_row = first + len(rows) + 1
            ws.cell(row=note_row, column=1, value=XLSX_AFTER).font = Font(italic=True, size=9)
            ws.freeze_panes = f"C{first + header_rows}"
        for r, row in enumerate(rows, start=first):
            for c, (value, fmt, formula) in enumerate(row, start=1):
                if value is None:
                    continue
                cell = ws.cell(row=r, column=c, value=f"={formula}" if formula else _xlsx_value(value))
                cell.number_format = fmt
                if formula:
                    cached[(xml_name, cell.coordinate)] = _xlsx_value(value)
                if r < first + header_rows or row[0][0] == "Total":
                    cell.font = Font(bold=True)
                if r < first + header_rows:
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        widths = {SHEET1: (11, 30, 18, 12, 14, 9, 15, 15, 16, 16),
                  "Disposals": (11, 26, 14, 15, 20, 20, 22),
                  "Locations": (8, 20, 13, 9, 15, 14)}[name]
        for col, width in zip("ABCDEFGHIJ", widths):
            ws.column_dimensions[col].width = width
        if name == "Locations":
            ws.auto_filter.ref = f"A1:F{len(rows)}"
            ws.freeze_panes = "A2"
    wb.properties.title = "Fixed asset register, Plant 2"
    wb.properties.creator = "Plant Accounting"
    wb.properties.lastModifiedBy = "Plant Accounting"
    wb.properties.created = dt.datetime(2030, 1, 8, 9, 15, 0)
    wb.properties.modified = dt.datetime(2030, 1, 8, 9, 15, 0)
    wb.save(path)

    def patch(name, data):
        """Writes each formula's computed value into its empty <v/>, as Excel saves it."""
        refs = {ref: v for (sheet, ref), v in cached.items() if sheet == name}
        if not refs:
            return data
        text = data.decode("utf-8")
        for ref, value in refs.items():
            pattern = rf'(<c r="{ref}"[^>]*><f>[^<]*</f>)<v\s*/?>(?:</v>)?'
            num = repr(float(value)) if isinstance(value, float) else str(value)
            text, n = re.subn(pattern, rf"\g<1><v>{num}</v>", text)
            require(n == 1, f"xlsx: could not write the cached value of {name} {ref}")
        return text.encode("utf-8")

    pin_ooxml(path, "2030-01-08T09:15:00Z", "2030-01-08T09:15:00Z", patch=patch)
    return cached


def make_xlsx():
    path = HERE / "gen-asset-register.xlsx"
    model = xlsx_model()
    cached = build_xlsx(path, model)
    shown = {name: [[xlsx_display(v, f) for v, f, _ in row] for row in sheet["rows"]] for name, sheet in model.items()}
    register, disposals, locations = shown[SHEET1], shown["Disposals"], shown["Locations"]
    checks = {
        # Locale-independent text cells and sheet names only; numbers, dates and booleans are checked by the tables.
        "must_contain": [XLSX_TITLE, XLSX_NOTE, XLSX_AFTER, SHEET1, "Disposals", "Locations", "Acquisition",
                         "Share of register cost", "Coordinate measuring machine", "Robotic welding cell", "Fully depreciated",
                         "Commissioning", "Sold to an employee", "Gain or (loss) (USD)", "Heat treatment furnace",
                         "Last inspection"],
        "ordered": [XLSX_TITLE, "Laser marking station", XLSX_AFTER, "Paint booth fans", "0590"],
        "headings": [],
        "tables": [{"name": "Fixed Assets (the two header rows 3-4 to the Total row 12; title and note rows 1-2 and the "
                             "note in row 14 not included; 'Acquisition' merged across two columns and 'Depreciation' "
                             "across three, five headers merged down, five header texts with a line break)",
                    "rows": register},
                   {"name": "Disposals (all 5 rows)", "rows": disposals},
                   {"name": "Locations (all 8 rows)", "rows": locations}],
        "noise": [],
        "absent": [],
    }
    n_formula = len(cached)
    gt = write_ground_truth(
        path, fmt="xlsx", title="Fixed asset register, disposals and locations, Plant 2, 2029", pages_or_sheets=3,
        stresses=["three visible worksheets (Fixed Assets, Disposals, Locations)",
                  "merged title row A1:J1 and merged italic note row A2:J2 above a table that starts at row 3; an "
                  "italic note two rows below the table",
                  "two header rows: 'Acquisition' merged across two columns and 'Depreciation' across three, five "
                  "headers merged down over both rows; five header texts contain a line break (Alt+Enter) and wrap",
                  f"{n_formula} formula cells saved with their computed (cached) values, as Excel saves them",
                  "amounts with two decimals and thousands separators (#,##0.00), gains and losses with negatives in "
                  "parentheses (#,##0.00;(#,##0.00)), zero amounts, whole numbers with separators (#,##0), one-decimal "
                  "percents, dates as yyyy-mm-dd, mm/dd/yyyy and d-mmm-yyyy, booleans TRUE/FALSE",
                  "asset tags and location codes stored as text with leading zeros (format @); frozen panes; "
                  "autofilter on the Locations sheet"],
        checks=checks,
        notes=("Expected cells are the text Excel shows in an en-US locale: amounts as '286,500.00' (#,##0.00), "
               "losses as '(2,675.25)' (#,##0.00;(#,##0.00)), whole numbers as '18,400' (#,##0), percentages as "
               "'19.0%' (0.0%), dates as '2024-03-18' (yyyy-mm-dd), '02/14/2029' (mm/dd/yyyy) and '12-Sep-2029' "
               "(d-mmm-yyyy), booleans as 'TRUE'/'FALSE', tags and codes as typed ('00412', '0101'); zero amounts as "
               "'0.00'. Separators, date order and boolean words follow the viewer's locale, so (as in the earlier "
               "sets) must_contain lists only text cells, notes and the three sheet names, and number and date display "
               "is measured by the tables. The Fixed Assets table starts at its first header row (row 3): 'Asset tag', "
               "'Description', 'Location', 'Net book value (USD)' and 'Status' are merged down over rows 3-4, "
               "'Acquisition' across 'Date' and 'Cost (USD)' and 'Depreciation' across 'Life (years)', 'Annual expense "
               "(USD)' and 'Accumulated (USD)'; five header texts hold a line break, written with '\\n' (normalization "
               "makes it a space); a merged cell's text is in its top-left position and the covered positions are "
               "empty strings (not scored). The Total row has its label in column A, no values in B-D, F and J. "
               f"Formulas ({n_formula} cells: G5 '=ROUND(E5/F5,2)', H5 '=MIN(E5,G5*5)', I5 '=E5-H5', E12 "
               "'=SUM(E5:E11)', Disposals F2 '=D2-E2', ...) are saved with their computed values, so the expected cell "
               "is the value. The merged title and note rows and the note below the Fixed Assets table are checked by "
               "must_contain and ordered, not as table rows. Sheet names are tab labels: checked by must_contain, not "
               "as headings. No hidden sheets, comments, charts or print headers/footers: noise and absent are "
               "empty."))

    wb_f = openpyxl.load_workbook(path)
    wb_v = openpyxl.load_workbook(path, data_only=True)
    require([ws.title for ws in wb_v.worksheets] == list(model), "xlsx: sheet names/order")
    texts, grids, fields = [], {}, list(model)
    for ws_v, ws_f in zip(wb_v.worksheets, wb_f.worksheets):
        require(ws_v.sheet_state == "visible", f"xlsx: {ws_v.title} hidden")
        grid = []
        for row_v, row_f in zip(ws_v.iter_rows(), ws_f.iter_rows()):
            out = []
            for cv, cf in zip(row_v, row_f):
                if cf.data_type == "f":
                    require(cv.value is not None, f"xlsx: formula {ws_v.title}!{cv.coordinate} has no cached value")
                if cv.number_format in (FMT_DMY, FMT_MDY, FMT_ISO) and cv.value is not None:
                    require(isinstance(cv.value, dt.datetime), "xlsx: date cell is not a real date")
                if cv.number_format == "@" and cv.value is not None:
                    require(cv.data_type == "s", "xlsx: code is not stored as text")
                out.append(xlsx_display(cv.value, cv.number_format))
            grid.append(out)
        grids[ws_v.title] = grid
        texts.append(ws_v.title + "\n" + "\n".join(" ".join(r) for r in grid))
        fields += [c for r in grid for c in r if c]
    g = grids[SHEET1]
    require(g[0][0] == XLSX_TITLE and g[1][0] == XLSX_NOTE and len(g[0]) == 10, "xlsx: title/note rows")
    require(g[-1][0] == XLSX_AFTER and all(c == "" for c in g[-2]), "xlsx: note below the table")
    require(sorted(str(r) for r in wb_v[SHEET1].merged_cells.ranges)
            == sorted(["A1:J1", "A2:J2", "A3:A4", "B3:B4", "C3:C4", "I3:I4", "J3:J4", "D3:E3", "F3:H3"]),
            "xlsx: merged ranges")
    require(sum(1 for ws in wb_f.worksheets for row in ws.iter_rows() for c in row if c.data_type == "f")
            == n_formula, "xlsx: formula count")
    require(any(c.startswith("(") for r in grids["Disposals"] for c in r), "xlsx: no loss in parentheses")
    require(grids[SHEET1][4][0] == "00412" and grids["Locations"][1][0] == "0101", "xlsx: leading zeros kept")
    tables_found = [g[2:2 + len(register)], grids["Disposals"], grids["Locations"]]
    verify(path.name, "xlsx", gt, "\n".join(texts), tables_found=tables_found, fields=fields)
    return gt


# ===========================================================================
# 3. gen-support-review.pptx
# ===========================================================================

CHANNELS = [  # (channel, tickets Q2, tickets Q3, median first response in tenths of an hour, CSAT in percent)
    ("Email", 2418, 2276, 65, 88),
    ("Phone", 1905, 2040, 4, 91),
    ("Web portal", 1122, 1486, 31, 86),
    ("Live chat", 0, 612, 1, 93),
]


def pptx_table():
    rows = [["Channel", "Tickets", "", "Median first response", "CSAT"],
            ["", "Q2 2029", "Q3 2029", "", ""]]
    for name, q2, q3, resp, csat in CHANNELS:
        rows.append([name, f"{q2:,}", f"{q3:,}", f"{Decimal(resp) / 10} h", f"{csat}%"])
    t2, t3 = sum(c[1] for c in CHANNELS), sum(c[2] for c in CHANNELS)
    csat = one_decimal(Decimal(sum(c[2] * c[4] for c in CHANNELS)) / t3)
    rows.append(["All channels", f"{t2:,}", f"{t3:,}", "", f"{csat}%"])
    return rows, csat


PPTX_TABLE, OVERALL_CSAT = pptx_table()
PPTX_TABLE_MERGES = [(0, 0, 1, 0), (0, 1, 0, 2), (0, 3, 1, 3), (0, 4, 1, 4)]
CSAT_BOX = ["Satisfaction rose on every channel except email, where replies slowed in August.",
            "Live chat started in July and already has the highest score of all channels.",
            "Detractors most often mentioned repeated transfers between teams."]
CSAT_CALLOUT = f"Overall CSAT in the third quarter: {OVERALL_CSAT}%"
PPTX_SLIDES = [
    {"layout": 0, "title": "Customer Support Quarterly Review", "subtitle": "Northgate Precision Components, third "
                                                                              "quarter 2029"},
    {"layout": 1, "title": "Agenda",
     "bullets": [(0, "Ticket volume and response times"), (0, "Customer satisfaction"),
                 (0, "What changed this quarter"), (0, "Priorities for the fourth quarter")]},
    {"layout": 5, "title": "Tickets by Channel", "table": True,
     "notes": "Phone volume rose because the warranty hotline moved to the main support number in July."},
    {"layout": 4, "title": "What Changed This Quarter",
     "left_head": "Improvements",
     "left": [(0, "Live chat launched for all customers on July 8"),
              (1, "Staffed by four agents during business hours"),
              (0, "Knowledge base articles were rewritten for the top 40 questions")],
     "right_head": "Open issues",
     "right": [(0, "Email backlog peaked at 312 tickets in August"),
               (0, "Warranty claims still need two handoffs"),
               (1, "A shared queue with the quality team is being tested")],
     "notes": "The August email backlog followed the loss of two senior agents; both positions are now filled."},
    {"layout": 5, "title": "Customer Satisfaction", "csat": True},
    {"layout": 2, "title": "Next Quarter", "body": "Priorities and staffing for the fourth quarter of 2029"},
    {"layout": 1, "title": "Priorities for the Fourth Quarter",
     "bullets": [(0, "Bring the median email response under four hours"),
                 (1, "Add a second shift for email on Mondays and Tuesdays"),
                 (0, "Route warranty claims directly to the quality team"),
                 (1, "Target a single handoff for every warranty claim")],
     "notes": "Budget for the second email shift was approved by the operations director on September 22."},
]


def _pptx_fill(tf, items):
    for i, (level, text) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.level = level


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
        if "bullets" in spec:
            _pptx_fill(slide.placeholders[1].text_frame, spec["bullets"])
        if "left" in spec:
            require(layout.name == "Comparison", "pptx: layout 4 is not Comparison")
            slide.placeholders[1].text = spec["left_head"]
            _pptx_fill(slide.placeholders[2].text_frame, spec["left"])
            slide.placeholders[3].text = spec["right_head"]
            _pptx_fill(slide.placeholders[4].text_frame, spec["right"])
        if spec.get("table"):
            shape = slide.shapes.add_table(len(PPTX_TABLE), len(PPTX_TABLE[0]), Inches(0.5), Inches(1.7),
                                           Inches(9.0), Inches(0.5) * len(PPTX_TABLE))
            table = shape.table
            for r0, c0, r1, c1 in PPTX_TABLE_MERGES:
                table.cell(r0, c0).merge(table.cell(r1, c1))
            for r, row in enumerate(PPTX_TABLE):
                for c, value in enumerate(row):
                    if value == "":
                        continue
                    cell = table.cell(r, c)
                    cell.text = value
                    for para in cell.text_frame.paragraphs:
                        for run in para.runs:
                            run.font.size = PPt(16)
                            run.font.bold = r < 2 or r == len(PPTX_TABLE) - 1 or None
        if spec.get("csat"):
            box = slide.shapes.add_textbox(Inches(0.6), Inches(1.8), Inches(8.8), Inches(2.4))
            box.text_frame.word_wrap = True
            for i, text in enumerate(CSAT_BOX):
                p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
                p.text = text
                p.runs[0].font.size = PPt(20)
            callout = slide.shapes.add_textbox(Inches(4.4), Inches(4.8), Inches(5.0), Inches(0.8))
            callout.text_frame.text = CSAT_CALLOUT
            callout.text_frame.paragraphs[0].runs[0].font.size = PPt(22)
            callout.text_frame.paragraphs[0].runs[0].font.bold = True
        if "notes" in spec:
            slide.notes_slide.notes_text_frame.text = spec["notes"]
    props = prs.core_properties
    props.title = PPTX_SLIDES[0]["title"]
    props.author = "Customer Support"
    props.last_modified_by = "Customer Support"
    props.comments = ""
    props.revision = 3
    props.created = dt.datetime(2029, 10, 6, 13, 30, 0)
    props.modified = dt.datetime(2029, 10, 9, 8, 50, 0)
    prs.save(path)
    pin_ooxml(path, "2029-10-06T13:30:00Z", "2029-10-09T08:50:00Z")


def make_pptx():
    path = HERE / "gen-support-review.pptx"
    build_pptx(path)
    s4 = PPTX_SLIDES[3]
    paragraphs = ([PPTX_SLIDES[0]["subtitle"], PPTX_SLIDES[5]["body"], s4["left_head"], s4["right_head"]]
                  + [t for s in PPTX_SLIDES for key in ("bullets", "left", "right") for _, t in s.get(key, [])]
                  + CSAT_BOX + [CSAT_CALLOUT])
    notes = [s["notes"] for s in PPTX_SLIDES if "notes" in s]
    must = [p for p in paragraphs if len(p.split()) >= MIN_PHRASE_WORDS] + notes
    short = [p for p in paragraphs if len(p.split()) < MIN_PHRASE_WORDS]
    checks = {
        "must_contain": must,
        "ordered": ["Northgate Precision Components, third quarter 2029", "Ticket volume and response times",
                    "Median first response", "Live chat launched for all customers",
                    "Warranty claims still need two handoffs", CSAT_CALLOUT,
                    "Route warranty claims directly to the quality team"],
        "headings": [s["title"] for s in PPTX_SLIDES],
        "tables": [{"name": "Slide 3: Tickets by Channel (two header rows: 'Channel', 'Median first response' and "
                             "'CSAT' merged down, 'Tickets' merged across 'Q2 2029' and 'Q3 2029'; total row)",
                    "rows": PPTX_TABLE}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pptx", title=PPTX_SLIDES[0]["title"], pages_or_sheets=len(PPTX_SLIDES),
        stresses=["slide titles (title placeholders) as headings",
                  "title slide with a subtitle; Section Header slide with a text placeholder",
                  "bulleted agenda (not numbered)",
                  "native 7x5 table with two header rows: three cells merged down, one merged across two columns; "
                  "counts with thousands separators, values with units ('6.5 h'), percentages, a total row with an "
                  "empty cell",
                  "Comparison layout: two heading placeholders, each above a bulleted body with second-level items, "
                  "left then right",
                  "Title Only slide with two free text boxes (not placeholders): a three-paragraph box and a bold "
                  "callout",
                  "two-level bullets; speaker notes on slides 3, 4 and 7"],
        checks=checks,
        notes=("Seven slides from python-pptx's default 4:3 template: 1 Title Slide, 2 and 7 Title and Content, 3 and "
               "5 Title Only, 4 Comparison, 6 Section Header. Slide 3's table has two header rows: 'Channel', 'Median "
               "first response' and 'CSAT' are merged down over both rows and 'Tickets' across 'Q2 2029' and 'Q3 "
               "2029'; a merged cell's text is in its top-left position and the covered positions are empty strings "
               "(not scored); counts are text as typed ('2,418'), response times carry a unit ('6.5 h'); the 'All "
               "channels' row leaves the response cell empty and its CSAT is the ticket-weighted average of Q3. Slide "
               "4 is read left heading, left body, right heading, right body, as in shape order and as placed. Slide 5 "
               "holds two text boxes, the three-paragraph box first and the callout below it on the right, in shape "
               "order and position. Speaker notes (slides 3, 4 and 7) are in must_contain (3 phrases), never ordered "
               "anchors. headings are the seven slide titles; the Comparison slide's two heading placeholders "
               "('Improvements', 'Open issues') are body text placeholders, not titles, and are not listed as "
               f"headings. must_contain keeps every slide paragraph of at least {MIN_PHRASE_WORDS} words; the "
               f"{len(short)} shorter ones ({'; '.join(short)}) are not phrases (the agenda item 'Ticket volume and "
               "response times' is an ordered anchor). No footers, slide numbers, dates, hidden slides, charts or "
               "comments: noise and absent are empty."))
    prs = Presentation(path)
    titles, texts, body, tables, read_notes, boxes = [], [], [], [], [], 0
    for slide in prs.slides:
        titles.append(slide.shapes.title.text)
        out = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                out += [p.text for p in shape.text_frame.paragraphs if p.text]
                boxes += not shape.is_placeholder
            if getattr(shape, "has_table", False) and shape.has_table:
                grid = [[cell.text for cell in row.cells] for row in shape.table.rows]
                tables.append(grid)
                out += [" ".join(r) for r in grid]
                spans = [(r, c) for r, row in enumerate(shape.table.rows) for c, cell in enumerate(row.cells)
                         if cell.is_merge_origin]
                require(spans == [(r0, c0) for r0, c0, _, _ in PPTX_TABLE_MERGES], "pptx: merged cells")
        texts += out
        body += out
        if slide.has_notes_slide:
            read_notes.append(slide.notes_slide.notes_text_frame.text)
            texts.append(read_notes[-1])
    require(read_notes == notes, "pptx: notes differ")
    require(boxes == 2, "pptx: expected two free text boxes")
    comparison = [ph.text_frame.text for ph in prs.slides[3].placeholders if ph.placeholder_format.idx in (1, 3)]
    require(comparison == [s4["left_head"], s4["right_head"]], "pptx: comparison headings")
    require(PPTX_TABLE[-1][1:3] == ["5,445", "6,414"], f"pptx: total row {PPTX_TABLE[-1]}")
    verify(path.name, "pptx", gt, "\n".join(texts), body_text="\n".join(body), headings_found=titles,
           tables_found=tables)
    return gt


# ===========================================================================
# 4. gen-shipment-log.csv
# ===========================================================================

CSV_HEADER = ["shipment_id", "ship_date", "carrier", "service_level", "origin", "destination", "pallets",
              "weight_kg", "freight_usd", "delivered_at", "status", "remarks"]
CSV_ORIGIN = "Plant 2, Dayton, OH"
CSV_DEST = ["Grand Rapids, MI", "Montréal, QC", "Querétaro, QRO", "Columbus, OH", "Saint-Étienne, FR",
            "Fort Wayne, IN", "Kraków, PL"]
CSV_CARRIERS = ["Ridgeway Freight", "Blue Heron Logistics", "Kestrel Express", "Transportes Peñasco"]
CSV_SERVICE = ["LTL", "FTL", "Expedited", "LTL", "Ocean consolidation"]
CSV_REMARKS = [
    "",
    "Liftgate required at delivery",
    'Consignee asked to "call 30 minutes ahead"',
    "Two pallets double-stacked, shrink-wrapped",
    "",
    "Customs hold at the border\nReleased the next morning",
    "Partial delivery; balance on next truck",
    "",
    "Appointment moved to 6 am\nDriver notified by phone",
]


def csv_rows():
    rows = []
    start = dt.date(2029, 7, 2)
    for i in range(30):
        ship = start + dt.timedelta(days=i * 2 + (i % 3))
        dest = CSV_DEST[(i * 3) % len(CSV_DEST)]
        carrier = CSV_CARRIERS[(i * 5) % len(CSV_CARRIERS)]
        service = CSV_SERVICE[i % len(CSV_SERVICE)]
        pallets = 1 + (i * 7) % 18
        weight = Decimal(pallets * 412 + (i * 37) % 300) + Decimal((i * 3) % 10) / 10
        freight = money(Decimal(180 + pallets * 96 + (i * 59) % 450) + Decimal((i * 17) % 100) / 100)
        if i < 24:
            transit = 1 + (i % 4) + (3 if service == "Ocean consolidation" else 0)
            arrived = dt.datetime.combine(ship, dt.time(0, 0)) + dt.timedelta(days=transit, hours=8 + (i * 5) % 9,
                                                                               minutes=(i * 13) % 60)
            delivered, status = arrived.strftime("%Y-%m-%d %H:%M"), ("delivered" if i % 11 != 4 else "damaged")
        else:
            delivered, status = "", "in transit"
        rows.append([f"SHP-29-{4117 + i * 4:05d}", ship.isoformat(), carrier, service, CSV_ORIGIN, dest,
                     str(pallets), f"{weight}", f"{freight}", delivered, status,
                     CSV_REMARKS[(i * 5) % len(CSV_REMARKS)]])
    return rows


def make_csv():
    path = HERE / "gen-shipment-log.csv"
    rows = csv_rows()
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    path.write_bytes(buf.getvalue().encode("utf-8"))
    multi = [r for r in rows if "\n" in r[11]]
    open_ = [r for r in rows if r[9] == ""]
    checks = {
        "must_contain": ["freight_usd", "delivered_at", "Transportes Peñasco", "Blue Heron Logistics",
                         "Montréal, QC", "Querétaro, QRO", "Saint-Étienne, FR", "Kraków, PL", "Ocean consolidation",
                         'Consignee asked to "call 30 minutes ahead"', "Two pallets double-stacked, shrink-wrapped",
                         "Partial delivery; balance on next truck", rows[0][0], rows[14][0], rows[-1][0],
                         rows[0][1], rows[-1][1], rows[0][9]],
        "ordered": [rows[0][0], rows[7][0], rows[14][0], rows[21][0], rows[-1][0]],
        "headings": [],
        "tables": [{"name": "Shipments: header row and all 30 data rows", "rows": [CSV_HEADER] + rows}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="csv", title="Outbound shipment log, July to September 2029", pages_or_sheets=None,
        stresses=["UTF-8 without a byte order mark, comma delimiter, every field quoted (also numbers and empty "
                  "fields), LF record ends",
                  f"{len(multi)} remarks fields (two different texts) with an embedded line feed inside quotes, so "
                  "those records span two physical lines",
                  "fields with commas (every origin and destination), a semicolon and doubled double quotes",
                  "decimals without thousands separators, ISO dates and 'YYYY-MM-DD HH:MM' timestamps, empty "
                  "timestamps and remarks",
                  "non-ASCII place and company names (é, É, ñ, ó)"],
        checks=checks,
        notes=("RFC 4180 CSV as written by Python's csv module with QUOTE_ALL: every field, including numbers and "
               "empty fields, is enclosed in double quotes, a double quote inside a field is doubled, records end with "
               "a bare LF and no byte order mark is written. Every origin ('" + CSV_ORIGIN + "') and destination "
               f"holds a comma; {len(multi)} remarks fields (two different texts) contain a line break inside the "
               "quotes, so those records span two physical lines; the expected cell keeps the line break "
               "(normalization turns it into a space). Weights and freight are plain decimals ('3333.3', '1007.17'), "
               f"no thousands separators. The last {len(open_)} shipments are in transit: their delivered_at fields "
               "are empty. Expected cell and phrase text is the parsed field value (quotes unescaped). The expected "
               "table is the whole file (header + 30 rows, 12 columns); empty fields are empty strings and are not "
               "scored. must_contain items are whole fields that never occur inside another field (shipment ids and "
               "dates of rows 1, 15 and 30, the first delivery timestamp, two carriers, four destinations with "
               "non-ASCII letters, a service level, three remarks with quotes, a hyphen, commas or a semicolon, two "
               "column names); the origin is not used because it repeats in every row. ordered: the shipment ids of "
               "rows 1, 8, 15, 22 and 30. A CSV has no headings, page furniture or hyphenation: headings, noise and "
               "absent are empty."))
    raw = path.read_bytes()
    require(not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw, "csv: BOM / CR found")
    text = raw.decode("utf-8")
    parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=","))
    require(parsed[0] == CSV_HEADER and parsed[1:] == rows and len(parsed) == 31, "csv: read-back differs")
    require(all(len(r) == len(CSV_HEADER) for r in parsed), "csv: ragged rows")
    require(len(multi) >= 4 and len({r[11] for r in multi}) == 2 and open_ and len(open_) < 10, "csv: features")
    require(text.count("\n") == 31 + len(multi) and all(line.startswith('"') for line in text.splitlines()
                                                         if line and not line[0].isalpha()), "csv: quoting/lines")
    require('"Consignee asked to ""call 30 minutes ahead"""' in text, "csv: doubled quotes")
    require(len({r[0] for r in rows}) == 30 and len({r[2] for r in rows}) == 4 and len({r[5] for r in rows}) == 7,
            "csv: variety")
    verify(path.name, "csv", gt, "\n".join(" ".join(r) for r in parsed), tables_found=[parsed],
           fields=[c for r in parsed for c in r])
    return gt


# ===========================================================================
# 5. gen-event-agenda.json
# ===========================================================================

JSON_SESSIONS = [
    {"id": "S-101", "title": "Opening keynote: Twelve months of the new ERP", "track": "Plenary",
     "start": "2029-10-09T09:00:00-04:00", "end": "2029-10-09T09:45:00-04:00", "room": "Ballroom A",
     "speakers": [{"name": "Marguerite Okafor", "company": COMPANY, "role": "Chief Operating Officer"}],
     "tags": ["strategy", "erp"], "capacity": 240, "recorded": True, "materials": None},
    {"id": "S-104", "title": "Forecast sharing with tier 2 suppliers", "track": "Planning",
     "start": "2029-10-09T10:15:00-04:00", "end": "2029-10-09T11:00:00-04:00", "room": "Huron",
     "speakers": [{"name": "Ingrid Sæther", "company": "Fjordline Castings AS", "role": "Supply Planner"},
                  {"name": "Daniel Mbeki", "company": COMPANY, "role": "Demand Planning Lead"}],
     "tags": ["forecasting"], "capacity": 60, "recorded": True,
     "materials": "https://example.com/summit-2029/forecast-sharing.pdf"},
    {"id": "S-107", "title": "Ask the buyers: \"What makes a preferred supplier?\"", "track": "Purchasing",
     "start": "2029-10-09T11:15:00-04:00", "end": "2029-10-09T12:00:00-04:00", "room": "Ballroom A",
     "speakers": [{"name": "José Luis Ortún", "company": COMPANY, "role": "Purchasing Manager"},
                  {"name": "Priyanka Desai", "company": COMPANY, "role": "Commodity Buyer, Castings"}],
     "tags": [], "capacity": 240, "recorded": False, "materials": None, "format": "panel"},
    {"id": "S-112", "title": "PPAP submissions without rework", "track": "Quality",
     "start": "2029-10-09T13:30:00-04:00", "end": "2029-10-09T14:30:00-04:00", "room": "Erie",
     "speakers": [{"name": "Chloé Marchand", "company": "Atelier Marchand SAS", "role": "Quality Engineer"}],
     "tags": ["ppap", "quality", "documentation"], "capacity": 45, "recorded": True, "materials": None,
     "prerequisites": ["Basic knowledge of AIAG PPAP levels"]},
    {"id": "S-118", "title": "Plant 2 tour: machining and heat treatment", "track": "Site visit",
     "start": "2029-10-09T15:00:00-04:00", "end": "2029-10-09T16:30:00-04:00", "room": None,
     "speakers": [], "tags": ["tour"], "capacity": 24, "recorded": False, "materials": None,
     "safety_gear_required": True, "meeting_point": "Main lobby, north entrance"},
    {"id": "S-201", "title": "Logistics: from LTL to milk runs", "track": "Logistics",
     "start": "2029-10-10T09:00:00-04:00", "end": "2029-10-10T09:45:00-04:00", "room": "Huron",
     "speakers": [{"name": "Tomasz Wiśniewski", "company": "Kestrel Express", "role": "Account Director"}],
     "tags": ["logistics", "cost"], "capacity": 60, "recorded": True,
     "materials": "https://example.com/summit-2029/milk-runs.pdf"},
    {"id": "S-205", "title": "Cybersecurity requirements for connected suppliers", "track": "IT",
     "start": "2029-10-10T10:00:00-04:00", "end": "2029-10-10T11:00:00-04:00", "room": "Erie",
     "speakers": [{"name": "Hana Kobayashi", "company": COMPANY, "role": "Information Security Officer"}],
     "tags": ["security", "it"], "capacity": 45, "recorded": False, "materials": None, "language": "en",
     "sponsor": {"name": "Halvorsen Data Services", "level": "silver"}},
    {"id": "S-210", "title": "Closing session and supplier awards", "track": "Plenary",
     "start": "2029-10-10T11:30:00-04:00", "end": "2029-10-10T12:15:00-04:00", "room": "Ballroom A",
     "speakers": [{"name": "Marguerite Okafor", "company": COMPANY, "role": "Chief Operating Officer"},
                  {"name": "José Luis Ortún", "company": COMPANY, "role": "Purchasing Manager"}],
     "tags": ["awards"], "capacity": 240, "recorded": True, "materials": None,
     "awards": [{"category": "Delivery performance", "winner": "Fjordline Castings AS"},
                {"category": "Quality improvement", "winner": "Atelier Marchand SAS"}]},
]


def json_model():
    return {"event": {"name": "Northgate Supplier Summit 2029", "organizer": COMPANY,
                      "venue": {"name": "Riverside Conference Center", "city": "Dayton", "state": "OH"},
                      "dates": ["2029-10-09", "2029-10-10"], "timezone": "America/New_York",
                      "registration_open": False, "attendees_registered": 187, "fee_usd": 0},
            "sessions": JSON_SESSIONS}


def make_json():
    path = HERE / "gen-event-agenda.json"
    obj = json_model()
    raw = json.dumps(obj, ensure_ascii=False, indent=4) + "\n"
    path.write_text(raw, encoding="utf-8")
    checks = {
        "must_contain": ["attendees_registered", "safety_gear_required", "Riverside Conference Center",
                         "America/New_York", "Ingrid Sæther", "Tomasz Wiśniewski", "Chloé Marchand",
                         'Ask the buyers: "What makes a preferred supplier?"', "Basic knowledge of AIAG PPAP levels",
                         "Main lobby, north entrance", "Commodity Buyer, Castings", "Quality improvement",
                         "2029-10-10T11:30:00-04:00", "https://example.com/summit-2029/milk-runs.pdf", "S-118"],
        "ordered": ["Northgate Supplier Summit 2029", "S-104", "PPAP submissions without rework", "S-201",
                    "Closing session and supplier awards"],
        "headings": [],
        "tables": [],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="json", title="Supplier summit agenda export (8 sessions), October 2029", pages_or_sheets=None,
        stresses=["pretty-printed JSON with 4-space indentation and a final newline",
                  "top-level object holding an event object (with a nested venue object and a dates array) and an "
                  "array of 8 session objects",
                  "arrays of objects (speakers, awards), arrays of strings (tags, prerequisites), an empty speakers "
                  "array and an empty tags array",
                  "null values, booleans, integers, timestamps with a UTC offset, URLs",
                  "objects whose keys differ from one record to the next (format, prerequisites, "
                  "safety_gear_required, meeting_point, language, sponsor, awards)",
                  "non-ASCII text kept as UTF-8 (æ, ś, é, ú), escaped double quotes inside a string"],
        checks=checks,
        notes=("UTF-8 JSON written by json.dumps(..., ensure_ascii=False, indent=4) plus a final newline: one key or "
               "value per line, key order as written, non-ASCII characters as-is. A converter may keep it as JSON, "
               "fence it as code, or render it as text, lists or tables; no Markdown structure is expected, so "
               "headings and tables are empty. must_contain items are whole keys or scalar values that never occur "
               "inside another key or value (keys, names with non-ASCII letters, a session id, a timestamp, a URL); "
               "the string with escaped quotes matches its raw JSON form too, because matching deletes backslashes, "
               "and the two keys with underscores match without them because matching deletes underscores. ordered "
               "follows document order: the event name, "
               "the ids of sessions 2 and 6 and the titles of sessions 4 and 8. The organisations, people, venue and "
               "URLs (example.com) are fictitious."))
    text = path.read_text(encoding="utf-8")
    require(json.loads(text) == obj and text.endswith("}\n") and '\n    "sessions": [' in text, "json: read-back")
    require('\\"' in text and "Sæther" in text and "Wiśniewski" in text, "json: escaping")
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
    require([] in [s["speakers"] for s in JSON_SESSIONS] and [] in [s["tags"] for s in JSON_SESSIONS]
            and None in [s["room"] for s in JSON_SESSIONS], "json: empty arrays / nulls")
    verify(path.name, "json", gt, text, fields=fields)
    return gt


# ===========================================================================
# 6. gen-safety-report.pdf (not read back with a text extractor; see the module doc)
# ===========================================================================

PDF_TITLE = "Quarterly Workplace Safety Report"
PDF_SUBTITLE = "Plant 2, Dayton, third quarter 2029, issued October 12, 2029"
PDF_HEADER_LEFT = COMPANY
PDF_HEADER_RIGHT = "Safety report SR-2029-Q3"
PDF_FOOTER = "Prepared by the Environmental, Health and Safety office"
PDF_KV = [
    ["Reporting period", "July 1 to September 30, 2029"],
    ["Plant manager", "Rosalind Achterberg"],
    ["Safety coordinator", "Emeka Nwosu"],
    ["Overall status", "Recordable rate below target; one lost-time injury"],
]
PDF_SUMMARY = ["Plant 2 recorded four recordable injuries in the third quarter, one fewer than in the second quarter.",
               "The only lost-time injury was a hand laceration in the machining bay on August 14.",
               "No environmental releases or regulatory inspections were reported during the quarter."]
PDF_DEPTS = [  # (department, hours worked, recordable incidents, lost-time incidents)
    ("Machining", 148320, 2, 1),
    ("Assembly", 121760, 1, 0),
    ("Heat treatment", 38240, 1, 0),
    ("Warehouse", 61980, 0, 0),
    ("Offices", 42260, 0, 0),
]
PDF_TABLE1_CAPTION = "Table 1. Hours worked and incidents by department"
PDF_ACTIONS = [  # numbered corrective actions with lettered sub-items
    ("Replace the cut-resistant gloves in the machining bay with a higher-rated model.",
     ["Order the new gloves before October 20.", "Train all machinists on the new glove sizes."]),
    ("Add a second guard interlock on the deburring station.", []),
    ("Repeat the forklift pedestrian-zone audit in the warehouse every month.",
     ["Publish the audit results on the safety board."]),
]
PDF_FINDINGS_HEADER = ["No.", "Finding", "Area", "Owner", "Due date"]
PDF_FINDINGS = [
    ["F-1", "Coolant mist above the action level at two lathes during the second shift; local exhaust to be "
            "rebalanced and air sampling repeated.", "Machining", "Maintenance supervisor", "October 31, 2029"],
    ["F-2", "Eyewash station near the quench tank was blocked by a parts cart on two inspections in a row.",
     "Heat treatment", "Area lead", "October 15, 2029"],
    ["F-3", "Three fire extinguishers were missing their monthly inspection tags for August.", "Warehouse",
     "Safety coordinator", "October 10, 2029"],
    ["F-4", "Ladder inspections are recorded on paper and two records could not be found during the audit.",
     "Assembly", "Assembly supervisor", "November 15, 2029"],
    ["F-5", "Emergency evacuation drill took six minutes longer than the plan allows; assembly point signs to be "
            "added at the east exits.", "Plant wide", "Safety coordinator", "December 1, 2029"],
    ["F-6", "Noise survey of the new compressor room is overdue after the equipment change in June.",
     "Utility room", "Environmental, Health and Safety office", "November 30, 2029"],
]
PDF_TRAINING = ["Forklift refresher training was completed by 46 of 48 operators.",
                "Lockout and tagout training for new maintenance staff is scheduled for October 22.",
                "First aid certification was renewed for 12 employees on all three shifts."]
PDF_NOTE = ("Rates are recordable incidents per 200,000 hours worked; the plant target for 2029 is a rate of 2.0 or "
            "lower.")


def pdf_incident_table():
    rows = [["Department", "Hours worked", "Incidents", "", "Recordable rate"], ["", "", "Recordable", "Lost time", ""]]
    th = tr = tl = 0
    for name, hours, rec, lost in PDF_DEPTS:
        rate = one_decimal(Decimal(rec) * 200000 / hours) if rec else Decimal("0.0")
        rows.append([name, f"{hours:,}", str(rec), str(lost), f"{rate}"])
        th, tr, tl = th + hours, tr + rec, tl + lost
    rows.append(["Total", f"{th:,}", str(tr), str(tl), f"{one_decimal(Decimal(tr) * 200000 / th)}"])
    require(tr == 4 and tl == 1, "pdf: incident totals differ from the summary text")
    return rows


def _pdf_build(path: Path, total_pages):
    """Builds the PDF; returns the number of pages."""
    rl_config.invariant = 1
    pages = []

    def furniture(canvas, doc):
        pages.append(doc.page)
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(0.8 * inch, letter[1] - 0.55 * inch, PDF_HEADER_LEFT)
        canvas.drawRightString(letter[0] - 0.8 * inch, letter[1] - 0.55 * inch, PDF_HEADER_RIGHT)
        canvas.setLineWidth(0.5)
        canvas.line(0.8 * inch, letter[1] - 0.62 * inch, letter[0] - 0.8 * inch, letter[1] - 0.62 * inch)
        canvas.drawString(0.8 * inch, 0.5 * inch, PDF_FOOTER)
        canvas.drawRightString(letter[0] - 0.8 * inch, 0.5 * inch, f"Page {doc.page} of {total_pages}")
        canvas.restoreState()

    title = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=19, leading=23, spaceAfter=4)
    sub = ParagraphStyle("S", fontName="Helvetica", fontSize=11, leading=14, spaceAfter=10,
                         textColor=colors.HexColor("#444444"))
    h2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13.5, leading=17, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("B", fontName="Helvetica", fontSize=10, leading=13.5, spaceAfter=6)
    cap = ParagraphStyle("C", fontName="Helvetica-Bold", fontSize=9.5, leading=12, spaceAfter=4)
    cell = ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, leading=11.5)
    note = ParagraphStyle("N", fontName="Helvetica-Oblique", fontSize=9.5, leading=12.5, spaceBefore=6)

    def para(text, style=body):
        return RLParagraph(xml_escape(text), style)

    grid = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA3AF"))]
    kv = Table(PDF_KV, colWidths=[1.6 * inch, 4.6 * inch], hAlign="LEFT")
    kv.setStyle(TableStyle(grid + [("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9.5),
                                   ("FONT", (1, 0), (1, -1), "Helvetica", 9.5),
                                   ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF1F5"))]))
    incidents = pdf_incident_table()
    t1 = Table(incidents, colWidths=[1.6 * inch, 1.2 * inch, 1.1 * inch, 1.1 * inch, 1.3 * inch], hAlign="LEFT")
    t1.setStyle(TableStyle(grid + [
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (1, 0), (1, 1)), ("SPAN", (2, 0), (3, 0)), ("SPAN", (4, 0), (4, 1)),
        ("FONT", (0, 0), (-1, 1), "Helvetica-Bold", 9), ("FONT", (0, 2), (-1, -2), "Helvetica", 9),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#DDE3EA")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("ALIGN", (1, 2), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    findings = [PDF_FINDINGS_HEADER] + [[r[0], RLParagraph(xml_escape(r[1]), cell), RLParagraph(xml_escape(r[2]), cell),
                                         RLParagraph(xml_escape(r[3]), cell), r[4]] for r in PDF_FINDINGS]
    t2 = Table(findings, colWidths=[0.45 * inch, 2.85 * inch, 0.95 * inch, 1.25 * inch, 1.3 * inch], hAlign="LEFT",
               repeatRows=1)
    t2.setStyle(TableStyle(grid + [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                                   ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE3EA")),
                                   ("ALIGN", (0, 0), (0, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    actions = ListFlowable(
        [ListItem([para(text)] + ([ListFlowable([ListItem(para(s)) for s in subs], bulletType="a",
                                                 bulletFormat="%s.", leftIndent=18)] if subs else []))
         for text, subs in PDF_ACTIONS], bulletType="1", bulletFormat="%s.", leftIndent=18)
    story = [para(PDF_TITLE, title), para(PDF_SUBTITLE, sub), kv, para("Summary", h2)]
    story += [para(s) for s in PDF_SUMMARY]
    story += [para("Incident Statistics", h2), para(PDF_TABLE1_CAPTION, cap), t1, para("Corrective Actions", h2),
              actions, para("Open Findings", h2), t2, para("Training", h2),
              ListFlowable([ListItem(para(t)) for t in PDF_TRAINING], bulletType="bullet", start="•",
                           leftIndent=18),
              Spacer(1, 4), para(PDF_NOTE, note)]
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.9 * inch, bottomMargin=0.85 * inch, title=PDF_TITLE, author="EHS office",
                            subject="Quarterly workplace safety report", creator="EHS office", invariant=1)
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return max(pages)


def make_pdf():
    path = HERE / "gen-safety-report.pdf"
    n = _pdf_build(path, 0)
    require(_pdf_build(path, n) == n, "pdf: page count changed between passes")
    require(n == 2, f"pdf: expected 2 pages, got {n}")
    incidents = pdf_incident_table()
    findings = [PDF_FINDINGS_HEADER] + PDF_FINDINGS
    action_lines = [x for text, subs in PDF_ACTIONS for x in [text] + subs]
    body_parts = ([PDF_TITLE, PDF_SUBTITLE] + [" ".join(r) for r in PDF_KV] + ["Summary"] + PDF_SUMMARY
                  + ["Incident Statistics", PDF_TABLE1_CAPTION] + [" ".join(r) for r in incidents]
                  + ["Corrective Actions"] + action_lines + ["Open Findings"] + [" ".join(r) for r in findings]
                  + ["Training"] + PDF_TRAINING + [PDF_NOTE])
    furniture_text = "\n".join(f"{PDF_HEADER_LEFT} {PDF_HEADER_RIGHT} {PDF_FOOTER} Page {k} of {n}"
                               for k in range(1, n + 1))
    checks = {
        "must_contain": ([PDF_SUBTITLE] + PDF_SUMMARY + [PDF_TABLE1_CAPTION] + action_lines
                         + [PDF_FINDINGS[1][1], PDF_FINDINGS[2][1], PDF_FINDINGS[3][1], PDF_FINDINGS[5][1]]
                         + PDF_TRAINING + ["Rates are recordable incidents per 200,000 hours worked;",
                                           "the plant target for 2029 is a rate of 2.0 or lower."]),
        "ordered": [PDF_TITLE, "Recordable rate below target", "The only lost-time injury was a hand laceration",
                    "Offices", "Add a second guard interlock on the deburring station",
                    "Three fire extinguishers were missing", "Lockout and tagout training for new maintenance staff"],
        "headings": [PDF_TITLE, "Summary", "Incident Statistics", "Corrective Actions", "Open Findings", "Training"],
        "tables": [{"name": "Report details (key-value table without a header row)", "rows": PDF_KV},
                   {"name": "Table 1. Hours worked and incidents by department (two header rows: 'Department', "
                            "'Hours worked' and 'Recordable rate' span both rows, 'Incidents' spans two columns; "
                            "total row)", "rows": incidents},
                   {"name": "Open findings (one table over two pages, header row repeated on page 2; complete: header "
                            "row and 6 rows; finding, area and owner cells wrap over several lines)", "rows": findings}],
        "noise": [{"text": PDF_HEADER_LEFT, "max": 1}, {"text": PDF_HEADER_RIGHT, "max": 1},
                  {"text": PDF_FOOTER, "max": 1}],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pdf", title=PDF_TITLE, pages_or_sheets=n,
        stresses=["generated single-column PDF (ReportLab, standard Helvetica fonts, untagged)",
                  "title, a grey subtitle line and section headings set by font size and Helvetica-Bold only",
                  "key-value table without a header row, first column shaded and bold",
                  "table with two header rows: 'Department', 'Hours worked' and 'Recordable rate' span both rows, "
                  "'Incidents' spans two columns; hours with thousands separators, one-decimal rates, a bold total row",
                  "numbered list (1.-3.) whose items 1 and 3 hold lettered sub-lists (a., b.), and a bulleted list, "
                  "drawn as list flowables",
                  "table whose finding, area and owner cells wrap over two or three lines (Paragraph cells); it runs "
                  "from page 1 to page 2 with its header row repeated at the top of page 2",
                  "italic closing note; running header (left and right text with a rule) and footer ('Page N of 2') "
                  "on every page"],
        checks=checks,
        notes=("ReportLab 'invariant' mode pins the creation date and document ID, so the file is reproducible. The "
               "checks come from the generator's data in reading order; the file was NOT read back with any text "
               "extractor (blind protocol), only rendered to images with pdftoppm and looked at, and its font list "
               "was checked once with pdffonts (see holdout5/SELECTION.md). Headings: the 19-point title and the five "
               "13.5-point section headings, all set in Helvetica-Bold; the subtitle line is regular weight and is a "
               "phrase, not a heading. Tables: the report-details table has no header row (its first row is data); "
               "in Table 1 'Department', 'Hours worked' and 'Recordable rate' span both header rows and 'Incidents' "
               "spans 'Recordable' and 'Lost time' (spanned positions are empty strings, not scored); hours are "
               "'148,320'-style text (compared without the comma) and rates one-decimal numbers per 200,000 hours "
               "('2.7'); the open-findings table's finding, area and owner cells wrap inside the cell, and each "
               "expected cell is the whole text with single spaces; that table starts on page 1 and continues on page "
               "2 with its header row repeated (repeatRows=1), so the expected table is the header row and all 6 rows "
               "once, and a repeated header row inside a converted table costs precision only. Lists: the corrective "
               "actions are numbered 1.-3. by ReportLab, with lettered sub-items a., b. under items 1 and 3; the "
               "numbers and letters are drawn, not part of the phrases. must_contain: the subtitle, every summary "
               "sentence, the table caption, every action and sub-action, four of the six findings, every training "
               "item and both clauses of the closing note (table cells are otherwise checked by the tables; the "
               "phrases are generator strings and may contain hyphens, which are ASCII). ordered: title, overall "
               "status, summary, a Table 1 row label, an action, a finding, a training item. Noise: the running "
               "header's two parts ('" + PDF_HEADER_LEFT + "', '" + PDF_HEADER_RIGHT + "') and the footer ('" +
               PDF_FOOTER + "') are printed once per page (twice) and occur nowhere in the body, max 1 each; 'Page N "
               "of 2' is not counted (it differs per page). No hyphenation (ReportLab does not hyphenate by "
               "default): absent is empty."))
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
