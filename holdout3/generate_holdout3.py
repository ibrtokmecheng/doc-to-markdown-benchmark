#!/usr/bin/env python3
"""Generate the synthetic part of the THIRD held-out doc-to-markdown test set (holdout3/).

Writes six ordinary business documents to holdout3/ and one ground-truth JSON per document to
holdout3/ground-truth/<file>.json (same schema as corpus/, holdout/ and holdout2/, checked by score.mjs):

    gen-maintenance-sow.docx     Word statement of work: Title style, headings at three levels with typed section
                                numbers (1., 2.1, 2.2.1), a two-level bulleted list, a numbered list, a second
                                numbered list with lettered sub-items that restarts at 1, a table with two header rows
                                (cells merged down and across) and body cells holding two paragraphs, a price table
                                with header cells broken by a line break and a total row merged across four columns,
                                an italic table note, bold and italic runs, a sign-off table with empty cells, page
                                header and footer.
    gen-capex-register.xlsx    Workbook with three sheets: a capital projects register (merged title and note rows,
                                two header rows with a group merged across three columns and six headers merged down,
                                header text with explicit line breaks, thousands separators, negatives in
                                parentheses, a percent column, d-mmm-yyyy dates, formulas saved with their computed
                                values, a total row, frozen panes, a note below the table); monthly spend by project
                                with empty months and formula totals; a vendor list with text phone numbers, mm/dd/yyyy
                                dates, booleans and one-decimal ratings.
    gen-facilities-update.pptx   Seven-slide committee deck: title slide, auto-numbered agenda, a native table with two
                                header rows (merged across and down), a Two Content slide with two-level bullets, a
                                Title Only slide with two free text boxes, a Section Header slide, two-level bullets,
                                speaker notes.
    gen-work-orders.csv          Maintenance work-order export: comma-delimited, minimal quoting (only fields that need
                                it), CRLF record ends, UTF-8 without BOM, quoted fields with embedded line breaks,
                                commas, semicolons and doubled quotes, amounts with thousands separators, US
                                date-times, empty fields, non-ASCII names.
    gen-asset-register.json      Equipment register export: pretty-printed (2-space indent), a top-level object with a
                                metadata object and an array of 8 assets, nested objects and arrays, objects whose keys
                                differ, nulls, booleans, empty arrays, an escaped quote, non-ASCII text.
    gen-inspection-report.pdf    ReportLab inspection report, 2 pages: title, key-value table without a header row,
                                headings by font size, a table with two header rows (cells spanning across and down)
                                and a total row, a numbered list, a table with wrapped multi-line cells, a bulleted
                                list, an italic note, running header and footer ('Page N of 2').

The content is new (not reused from holdout/generate_holdout.py or holdout2/generate_holdout2.py). Everything is
fixed in this file: no randomness, no clock. Every ground-truth item is derived from the same Python data that is
written into the document. After writing, the DOCX, XLSX, PPTX, CSV and JSON files are read back (python-docx,
openpyxl, python-pptx, csv, json) and every check is verified against the read-back text, with the audit rules of
holdout/ and holdout2/ (no file name or converter-added text in a check; prose phrases of at least 6 words that occur
once; data-file items are whole, distinctive fields; ordered anchors unique and in reading order, never from speaker
notes). The PDF is NOT read back with any text extractor (blind protocol): its checks are verified against the
generator's own data in reading order, and its pages were only rendered to images (pdftoppm) and looked at. Every
answer file is also checked against the validation rules of score.mjs validateGroundTruth (re-implemented below,
score.mjs is not run). Any mismatch aborts with exit status 1.

No converter (PackForAI, MarkItDown or other) is run here or was run while writing the answers.

Run from the benchmark folder (ephemeral environment, no global installs):

    uv run --with python-docx --with openpyxl --with python-pptx --with reportlab \
        python3 -I holdout3/generate_holdout3.py

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
from pptx.oxml.ns import qn as pqn
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
LICENSE = ("Synthetic document written for the third held-out benchmark set and generated by "
           "holdout3/generate_holdout3.py; no third-party material. All organisations, people, addresses, phone "
           "numbers, e-mail domains and figures are fictitious.")
LIBS = ("python-docx", "openpyxl", "python-pptx", "lxml", "reportlab")
MIN_PHRASE_WORDS = 6
COMPANY = "Corvane Facility Services, LLC"
CLIENT = "Larkspur Business Park Owners Association"
SITE = "Larkspur Business Park"
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
    if gt["file"] + ".json" != gt_name:
        warnings.append("file name")
    if gt["format"] not in FORMATS:
        errors.append("format")
    if Path(gt["file"]).suffix[1:].lower() != gt["format"]:
        warnings.append("extension")
    if gt.get("origin") not in ("generated", "public"):
        warnings.append("origin")
    if not re.fullmatch(r"[0-9a-f]{64}", str(gt.get("sha256", ""))):
        warnings.append("sha256")
    c = gt["checks"]
    for key in CHECK_KEYS:
        if key not in c:
            errors.append(f"checks.{key} missing")
    for key in c:
        if key not in CHECK_KEYS:
            warnings.append(f"unknown check {key}")
    for key in ("must_contain", "ordered", "headings", "absent"):
        seen = set()
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
        if not t.get("name"):
            warnings.append("table name")
        rows = t["rows"]
        if not rows or any(not r or any(not isinstance(x, str) for x in r) for r in rows):
            errors.append("table rows")
            continue
        if len({len(r) for r in rows}) > 1:
            warnings.append(f"table {t['name'][:40]!r} has rows of different lengths")
        if not any(normalize(x) for r in rows for x in r):
            errors.append("table without a non-empty cell")
        if len(rows) < 2:
            warnings.append("table with only a header row")
    for n in c["noise"]:
        if not isinstance(n.get("max"), int) or n["max"] < 0 or not normalize(n.get("text", "")):
            errors.append("noise entry")
        elif len(normalize(n["text"])) < 3:
            warnings.append("short noise text")
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
        "notes": notes + f" Generated by holdout3/generate_holdout3.py with {lib_versions()}; no converter was run "
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


# ===========================================================================
# 1. gen-maintenance-sow.docx
# ===========================================================================

DOCX_TITLE = "Statement of Work: Preventive Maintenance Services"
DOCX_HEADER = COMPANY
DOCX_FOOTER = "SOW 4 to master services agreement MSA-2026-118"
DOCX_T1 = [
    ["System", "Main tasks", "Planned effort", "", "Responsible"],
    ["", "", "Visits per year", "Hours per visit", ""],
    ["HVAC air handlers", "Replace filters\nCheck belts and bearings", "12", "6", "Corvane"],
    ["Chillers and cooling towers", "Inspect and log operating data\nClean condenser tubes", "4", "16", "Corvane"],
    ["Boilers", "Combustion analysis\nSafety valve test", "2", "8", "Corvane"],
    ["Fire alarm and sprinklers", "Annual inspection and testing", "1", "40", "Licensed subcontractor"],
    ["Emergency generators", "Load bank test\nFluid and battery checks", "4", "5", "Corvane"],
    ["Elevators", "Monthly safety check", "12", "3", "Elevator contractor"],
]
DOCX_T1_MERGES = [(0, 0, 1, 0), (0, 1, 1, 1), (0, 2, 0, 3), (0, 4, 1, 4)]
PRICE_ITEMS = [  # (item, basis, quantity, unit price)
    ("Preventive maintenance labor", "per hour", 1416, "96.50"),
    ("Fire alarm and sprinkler inspection", "per building", 4, "3850.00"),
    ("Elevator safety checks", "per elevator per month", 96, "145.00"),
    ("Consumables (filters, belts, lubricants)", "lump sum", 1, "18750.00"),
    ("Emergency call-out allowance", "per call-out", 24, "425.00"),
]


def docx_price_table():
    rows = [["Item", "Basis", "Quantity", "Unit price\n(USD)", "Annual amount\n(USD)"]]
    total = Decimal(0)
    for item, basis, qty, unit in PRICE_ITEMS:
        amount = money(Decimal(unit) * qty)
        total += amount
        rows.append([item, basis, f"{qty:,}", f"${Decimal(unit):,.2f}", f"${amount:,.2f}"])
    rows.append(["Total", "", "", "", f"${total:,.2f}"])
    return rows


DOCX_T2 = docx_price_table()
DOCX_T2_MERGES = [(len(DOCX_T2) - 1, 0, len(DOCX_T2) - 1, 3)]
DOCX_SIGN = [
    ["Party", "Name and title", "Signature", "Date"],
    [CLIENT, "Maria Okonkwo, Board President", "", ""],
    [COMPANY, "Daniel Hirsch, Regional Director", "", ""],
]

# (kind, payload). Runs: (text, "" | "b" | "i").
DOCX_BLOCKS = [
    ("title", DOCX_TITLE),
    ("para", [("Prepared for " + CLIENT + " by " + COMPANY, "i")]),
    ("para", [("Agreement reference: ", "b"), ("MSA-2026-118, statement of work 4, version 2", "")]),
    ("h1", "1. Purpose"),
    ("para", [("This statement of work describes the preventive maintenance services that " + COMPANY + " will "
               "provide at " + SITE + " from April 1, 2027 to March 31, 2028.", "")]),
    ("para", [("It forms part of the master services agreement and uses the terms defined there.", "")]),
    ("h1", "2. Scope of Services"),
    ("para", [("Corvane will maintain the mechanical, electrical and life safety systems of the four buildings "
               "listed below.", "")]),
    ("h2", "2.1 Buildings Covered"),
    ("bullet", (0, "Building A, 2200 Larkspur Drive: offices, 48,500 square feet")),
    ("bullet", (1, "Includes the rooftop chiller plant that serves Buildings A and B")),
    ("bullet", (0, "Building B, 2210 Larkspur Drive: offices and a fitness center, 36,200 square feet")),
    ("bullet", (0, "Building C, 2300 Larkspur Drive: light industrial, 61,750 square feet")),
    ("bullet", (1, "The tenant maintains its own process equipment and compressed air")),
    ("bullet", (0, "Building D, 2310 Larkspur Drive: data center and offices, 29,900 square feet")),
    ("h2", "2.2 Maintenance Schedule"),
    ("para", [("Table 1 lists the planned visits and labor hours for each building system.", "")]),
    ("caption", "Table 1. Planned preventive maintenance by system"),
    ("table", 1),
    ("note", "Note: Hours per visit are averages for all four buildings; actual hours are reported monthly."),
    ("h3", "2.2.1 Seasonal Tasks"),
    ("number", (0, "Switch the cooling towers to winter operation in October.")),
    ("number", (0, "Flush and test the heating water loops before November 15.")),
    ("number", (0, "Inspect roof drains and gutters after the leaves have fallen.")),
    ("h1", "3. Deliverables"),
    ("para", [("Corvane will deliver the following documents to the owners association:", "")]),
    ("number2", (0, "A monthly service report by the fifth business day of each month.")),
    ("number2", (1, "Completed and overdue work orders listed by building.")),
    ("number2", (1, "Labor hours compared with the plan in Table 1.")),
    ("number2", (0, "An annual condition assessment of all major equipment.")),
    ("number2", (0, "Updated equipment records in the owner's maintenance system.")),
    ("h1", "4. Pricing and Payment"),
    ("para", [("Prices are fixed for the term of this statement of work. Invoices are issued monthly in arrears.",
               "")]),
    ("caption", "Table 2. Annual price summary (USD)"),
    ("table", 2),
    ("para", [("Payment is due within ", ""), ("30 days", "b"), (" of the invoice date. Late payments accrue "
               "interest at ", ""), ("1.5 percent", "i"), (" per month.", "")]),
    ("h1", "5. Assumptions and Exclusions"),
    ("bullet", (0, "The owner provides access to all plant rooms and roofs during business hours.")),
    ("bullet", (0, "Repairs found during maintenance are quoted separately and need written approval.")),
    ("bullet", (0, "Tenant equipment, furniture and IT systems are excluded from this scope.")),
    ("h1", "6. Acceptance"),
    ("para", [("Each party signs below to accept this statement of work.", "")]),
    ("table", 3),
]

DOCX_MUST = [
    "Prepared for " + CLIENT + " by " + COMPANY,
    "Agreement reference: MSA-2026-118, statement of work 4, version 2",
    "This statement of work describes the preventive maintenance services",
    "from April 1, 2027 to March 31, 2028.",
    "It forms part of the master services agreement and uses the terms defined there.",
    "Corvane will maintain the mechanical, electrical and life safety systems of the four buildings listed below.",
    "Building A, 2200 Larkspur Drive: offices, 48,500 square feet",
    "Includes the rooftop chiller plant that serves Buildings A and B",
    "Building B, 2210 Larkspur Drive: offices and a fitness center, 36,200 square feet",
    "Building C, 2300 Larkspur Drive: light industrial, 61,750 square feet",
    "The tenant maintains its own process equipment and compressed air",
    "Building D, 2310 Larkspur Drive: data center and offices, 29,900 square feet",
    "Table 1 lists the planned visits and labor hours for each building system.",
    "Table 1. Planned preventive maintenance by system",
    "Note: Hours per visit are averages for all four buildings; actual hours are reported monthly.",
    "Switch the cooling towers to winter operation in October.",
    "Flush and test the heating water loops before November 15.",
    "Inspect roof drains and gutters after the leaves have fallen.",
    "Corvane will deliver the following documents to the owners association:",
    "A monthly service report by the fifth business day of each month.",
    "Completed and overdue work orders listed by building.",
    "Labor hours compared with the plan in Table 1.",
    "An annual condition assessment of all major equipment.",
    "Updated equipment records in the owner's maintenance system.",
    "Prices are fixed for the term of this statement of work.",
    "Invoices are issued monthly in arrears.",
    "Table 2. Annual price summary (USD)",
    "Payment is due within 30 days of the invoice date.",
    "Late payments accrue interest at 1.5 percent per month.",
    "The owner provides access to all plant rooms and roofs during business hours.",
    "Repairs found during maintenance are quoted separately and need written approval.",
    "Tenant equipment, furniture and IT systems are excluded from this scope.",
    "Each party signs below to accept this statement of work.",
]
DOCX_ORDERED = [
    DOCX_TITLE,
    "This statement of work describes the preventive maintenance services",
    "Building C, 2300 Larkspur Drive",
    "Planned effort",
    "Flush and test the heating water loops",
    "A monthly service report by the fifth business day",
    "Emergency call-out allowance",
    "Each party signs below to accept this statement of work",
]

BULLET_NUM_ID, NUMBER_NUM_ID, NUMBER2_NUM_ID = 51, 52, 53


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


def _docx_table(document, grid, merges, header_rows, right_from=None, two_paragraph_cells=False):
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
                if ri < header_rows or row[0] == "Total":
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
                _docx_table(document, DOCX_T1, DOCX_T1_MERGES, 2, right_from=2, two_paragraph_cells=True)
            elif payload == 2:
                _docx_table(document, DOCX_T2, DOCX_T2_MERGES, 1, right_from=2)
            else:
                _docx_table(document, DOCX_SIGN, [], 1)
        else:
            raise ValueError(kind)
    for para in document.paragraphs:
        if para.style.name == "Normal":
            para.paragraph_format.space_after = Pt(6)
    props = document.core_properties
    props.title = DOCX_TITLE
    props.subject = "Preventive maintenance statement of work"
    props.author = "Contracts Team"
    props.last_modified_by = "Contracts Team"
    props.comments = ""
    props.keywords = ""
    props.category = ""
    props.revision = 4
    props.created = dt.datetime(2027, 2, 8, 10, 0, 0)
    props.modified = dt.datetime(2027, 3, 1, 15, 20, 0)
    document.save(path)
    pin_ooxml(path, "2027-02-08T10:00:00Z", "2027-03-01T15:20:00Z")


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
    texts, headings, tables, items, br_cells = [], [], [], [], 0
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
    return "\n".join(texts), headings, tables, items, header, footer, br_cells


def make_docx():
    path = HERE / "gen-maintenance-sow.docx"
    build_docx(path)
    headings = [p for k, p in DOCX_BLOCKS if k in ("h1", "h2", "h3")]
    checks = {
        "must_contain": DOCX_MUST,
        "ordered": DOCX_ORDERED,
        "headings": headings,
        "tables": [
            {"name": "Table 1. Planned preventive maintenance by system (two header rows: 'System', 'Main tasks' and "
                     "'Responsible' merged down, 'Planned effort' merged across two columns; task cells with two "
                     "paragraphs)", "rows": DOCX_T1},
            {"name": "Table 2. Annual price summary (header cells broken by a line break; total row with 'Total' "
                     "merged across four columns)", "rows": DOCX_T2},
            {"name": "Sign-off table (header row, two parties, empty signature and date cells)", "rows": DOCX_SIGN},
        ],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="docx", title=DOCX_TITLE, pages_or_sheets=None,
        stresses=["Title style, then an italic line and a line with a bold label run",
                  "Heading 1 / Heading 2 / Heading 3 with typed section numbers in the heading text (1., 2.1, 2.2.1)",
                  "two-level bulleted list; a numbered list; a second numbered list with lettered sub-items that "
                  "restarts at 1 (a new w:num with startOverride)",
                  "table with two header rows: three header cells merged down (vMerge), one merged across "
                  "(gridSpan 2); body cells holding two paragraphs",
                  "price table whose header cells contain a line break (w:br), currency and quantities with "
                  "thousands separators, a total row with 'Total' merged across four columns",
                  "Caption-style table titles, an italic 9-point note under a table",
                  "bold and italic runs inside a sentence; a sign-off table with empty cells",
                  "page header and footer text"],
        checks=checks,
        notes=("The headings are Word Heading 1/2/3 paragraphs whose section numbers are typed as text ('2.2.1 "
               "Seasonal Tasks'), not list numbering, so the expected headings include the numbers. The document "
               "title uses the Title style and is the first ordered anchor, not a heading (as in holdout/ and "
               "holdout2/). Tables: in Table 1 'System', 'Main tasks' and 'Responsible' are merged down over both "
               "header rows and 'Planned effort' across 'Visits per year' and 'Hours per visit'; the 'Main tasks' "
               "body cells hold two paragraphs, written with '\\n' between them (normalization makes it a space); "
               "Table 2's header cells 'Unit price' / '(USD)' and 'Annual amount' / '(USD)' are broken by a line "
               "break inside one paragraph, also written with '\\n'; its last row has 'Total' merged across the "
               "first four columns. A merged cell's text is in its top-left grid position and the covered positions "
               "are empty strings (not scored), as in the corpus. Amounts are text as typed ('$136,644.00', "
               "quantities '1,416'); the table rule compares them with the thousands commas removed on both sides. "
               "The sign-off table's signature and date cells are empty. Lists: the Buildings Covered list has two "
               "levels; the Seasonal Tasks list is numbered 1-3; the Deliverables list is a second instance of the "
               "same numbering that restarts at 1, with lettered sub-items. must_contain keeps every paragraph, list "
               "item, caption and note of at least 6 words, long paragraphs split at their sentences or clauses; the "
               "bold '30 days' and italic '1.5 percent' fall inside phrases (normalization deletes '*' and '_'). Page "
               "header ('" + DOCX_HEADER + "') and footer ('" + DOCX_FOOTER + "') are stored once each and are not "
               "checked; including or dropping them are both faithful. No footnotes, comments, tracked changes, "
               "hyperlinks or hyphenation: noise and absent are empty."))
    text, found_headings, tables, items, header, footer, br_cells = read_docx(path)
    require(header == DOCX_HEADER and footer == DOCX_FOOTER, "docx: header/footer")
    num_of = {"bullet": BULLET_NUM_ID, "number": NUMBER_NUM_ID, "number2": NUMBER2_NUM_ID}
    require(items == [(num_of[k], lvl, t) for k, p in DOCX_BLOCKS if k in num_of for lvl, t in [p]],
            "docx: list items/levels read back differ")
    require(br_cells == 2, f"docx: expected 2 header cells with a line break, got {br_cells}")
    verify(path.name, "docx", gt, text, headings_found=found_headings, tables_found=tables)
    for s in (DOCX_HEADER, DOCX_FOOTER):
        require(normalize(s) not in normalize(text) or s == COMPANY, f"docx: furniture {s!r} also in the body")
    return gt


# ===========================================================================
# 2. gen-capex-register.xlsx
# ===========================================================================

SHEET1 = "Project List"
XLSX_TITLE = f"{SITE} - Capital Projects Register, FY2027"
XLSX_NOTE = "Amounts in U.S. dollars. Committed includes signed purchase orders that are not yet invoiced."
XLSX_AFTER = "Remaining is negative when spending exceeds the approved budget."
FMT_INT = "#,##0"
FMT_PAREN = "#,##0;(#,##0)"
FMT_PCT1 = "0.0%"
FMT_DMY = "d-mmm-yyyy"
FMT_MDY = "mm/dd/yyyy"
FMT_DEC1 = "0.0"
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PROJECTS = [  # (id, project, building, approved, committed, spent, target completion, status)
    ("CP-27-01", "Chiller replacement", "Building A", 1250000, 1180400, 845300, (2027, 9, 30), "In progress"),
    ("CP-27-02", "Roof membrane renewal", "Building C", 640000, 655900, 652400, (2027, 6, 15), "Over budget"),
    ("CP-27-03", "LED lighting retrofit", "Building B", 315000, 298750, 121600, (2027, 11, 30), "In progress"),
    ("CP-27-04", "Parking lot resurfacing", "All buildings", 480000, 0, 0, (2028, 5, 31), "Not started"),
    ("CP-27-05", "Elevator modernization", "Building D", 910000, 905000, 410250, (2028, 2, 28), "In progress"),
    ("CP-27-06", "Fire alarm panel upgrade", "Building A", 185000, 179800, 179800, (2027, 4, 30), "Complete"),
    ("CP-27-07", "Data center UPS batteries", "Building D", 96500, 94200, 94200, (2027, 3, 15), "Complete"),
    ("CP-27-08", "Lobby accessibility upgrades", "Building B", 220000, 61300, 18900, (2028, 1, 31), "Design"),
]
MONTHLY = [  # (id, project, Jan..Jun spend; None = no spend that month)
    ("CP-27-01", "Chiller replacement", [None, 120400, 210300, 182600, 168000, 164000]),
    ("CP-27-02", "Roof membrane renewal", [88500, 141200, 196300, 226400, None, None]),
    ("CP-27-03", "LED lighting retrofit", [None, None, 24800, 31900, 30400, 34500]),
    ("CP-27-05", "Elevator modernization", [102000, None, 98750, None, 104500, 105000]),
    ("CP-27-06", "Fire alarm panel upgrade", [61200, 58700, 59900, None, None, None]),
    ("CP-27-07", "Data center UPS batteries", [47100, 47100, None, None, None, None]),
    ("CP-27-08", "Lobby accessibility upgrades", [None, None, None, 6300, 6300, 6300]),
]
MONTHLY_SOURCE = "Source: accounts payable ledger, closed through June 30, 2027."
VENDORS = [  # (vendor id, vendor, trade, phone, insurance expires, preferred, rating)
    ("V-0042", "Brightline Mechanical, Inc.", "HVAC", "(510) 555-0142", (2028, 3, 31), True, 4.6),
    ("V-0057", "Keystone Fire Protection", "Fire and life safety", "(510) 555-0188", (2027, 9, 30), True, 4.8),
    ("V-0063", "Ridgeway Roofing Co.", "Roofing", "(925) 555-0119", (2027, 7, 15), False, 3.9),
    ("V-0071", "Summit Vertical Transport", "Elevators", "(510) 555-0175", (2028, 1, 31), True, 4.2),
    ("V-0088", "Clearwater Electric", "Electrical", "(408) 555-0163", (2027, 12, 31), False, 4.0),
    ("V-0094", "Ötztal Paving & Sealcoat", "Paving", "(925) 555-0131", (2028, 6, 30), False, 3.7),
]
VENDOR_HEADER = ["Vendor ID", "Vendor", "Trade", "Phone", "Insurance expires", "Preferred", "Rating"]


def xlsx_display(value, fmt) -> str:
    """Cell text as Excel (en-US) shows it, for the number formats used here."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if fmt == FMT_DMY:
        return f"{value.day}-{MONTH_ABBR[value.month - 1]}-{value.year}"
    if fmt == FMT_MDY:
        return f"{value.month:02d}/{value.day:02d}/{value.year}"
    d = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if fmt in (FMT_INT, FMT_PAREN):
        require(d == d.to_integral_value(), "xlsx: non-integer in a whole-number cell")
        if d < 0:
            require(fmt == FMT_PAREN, "xlsx: negative value without a negative section")
            return f"({-d:,.0f})"
        return f"{d:,.0f}"
    if fmt == FMT_PCT1:
        return f"{pct1(d)}%"
    if fmt == FMT_DEC1:
        return f"{d.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}"
    if fmt == "General":
        require(d == d.to_integral_value(), "xlsx: integer cell")
        return str(int(d))
    raise ValueError(f"unexpected cell {value!r} with format {fmt!r}")


def xlsx_model():
    """{sheet: {"rows": [[(value, format, formula)]], "first": first row}} with formula values precomputed."""
    top = 3
    first_body = top + 2
    last_body = first_body + len(PROJECTS) - 1
    total_row = last_body + 1
    header1 = ["Project ID", "Project", "Building", "Budget (USD)", None, None, "Remaining\n(USD)",
               "Spent\n(% of approved)", "Target\ncompletion", "Status"]
    header2 = [None, None, None, "Approved", "Committed", "Spent to date", None, None, None, None]
    projects = [[(h, "General", None) for h in header1], [(h, "General", None) for h in header2]]
    for k, (pid, name, bldg, appr, comm, spent, target, status) in enumerate(PROJECTS):
        r = first_body + k
        projects.append([(pid, "General", None), (name, "General", None), (bldg, "General", None),
                         (appr, FMT_INT, None), (comm, FMT_INT, None), (spent, FMT_INT, None),
                         (appr - spent, FMT_PAREN, f"D{r}-F{r}"), (spent / appr, FMT_PCT1, f"F{r}/D{r}"),
                         (dt.datetime(*target), FMT_DMY, None), (status, "General", None)])
    sums = [sum(p[i] for p in PROJECTS) for i in (3, 4, 5)]
    projects.append([(None, None, None), ("Total", "General", None), (None, None, None)]
                    + [(v, FMT_INT, f"SUM({c}{first_body}:{c}{last_body})") for v, c in zip(sums, "DEF")]
                    + [(sums[0] - sums[2], FMT_PAREN, f"SUM(G{first_body}:G{last_body})"),
                       (sums[2] / sums[0], FMT_PCT1, f"F{total_row}/D{total_row}"),
                       (None, None, None), (None, None, None)])
    months = [f"{m} 2027" for m in MONTH_ABBR[:6]]
    monthly = [[(h, "General", None) for h in ["Project ID", "Project"] + months + ["H1 total"]]]
    for k, (pid, name, vals) in enumerate(MONTHLY):
        r = 2 + k
        monthly.append([(pid, "General", None), (name, "General", None)]
                       + [(v, FMT_INT, None) for v in vals]
                       + [(sum(v or 0 for v in vals), FMT_INT, f"SUM(C{r}:H{r})")])
    last = 1 + len(MONTHLY)
    col_totals = [sum(m[2][i] or 0 for m in MONTHLY) for i in range(6)]
    monthly.append([("Total", "General", None), (None, None, None)]
                   + [(t, FMT_INT, f"SUM({c}2:{c}{last})") for t, c in zip(col_totals, "CDEFGH")]
                   + [(sum(col_totals), FMT_INT, f"SUM(I2:I{last})")])
    vendors = [[(h, "General", None) for h in VENDOR_HEADER]]
    for vid, name, trade, phone, expires, preferred, rating in VENDORS:
        vendors.append([(vid, "General", None), (name, "General", None), (trade, "General", None),
                        (phone, "@", None), (dt.datetime(*expires), FMT_MDY, None), (preferred, "General", None),
                        (rating, FMT_DEC1, None)])
    return {SHEET1: {"rows": projects, "first": top}, "Monthly Spend": {"rows": monthly, "first": 1},
            "Vendors": {"rows": vendors, "first": 1}}


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
            for col in (1, 2, 3, 7, 8, 9, 10):
                ws.merge_cells(start_row=first, start_column=col, end_row=first + 1, end_column=col)
            ws.merge_cells(start_row=first, start_column=4, end_row=first, end_column=6)
            note_row = first + len(rows) + 1
            ws.cell(row=note_row, column=1, value=XLSX_AFTER).font = Font(italic=True, size=9)
            ws.freeze_panes = f"C{first + header_rows}"
        if name == "Monthly Spend":
            ws.cell(row=len(rows) + 2, column=1, value=MONTHLY_SOURCE).font = Font(italic=True, size=9)
        for r, row in enumerate(rows, start=first):
            for c, (value, fmt, formula) in enumerate(row, start=1):
                if value is None:
                    continue
                cell = ws.cell(row=r, column=c, value=f"={formula}" if formula else value)
                cell.number_format = fmt
                if formula:
                    cached[(xml_name, cell.coordinate)] = value
                if r < first + header_rows or "Total" in (row[0][0], row[1][0]):
                    cell.font = Font(bold=True)
                if r < first + header_rows:
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        widths = {SHEET1: (11, 30, 12, 13, 13, 14, 13, 15, 13, 13),
                  "Monthly Spend": (11, 30, 11, 11, 11, 11, 11, 11, 12),
                  "Vendors": (10, 28, 20, 16, 17, 10, 8)}[name]
        for col, width in zip("ABCDEFGHIJ", widths):
            ws.column_dimensions[col].width = width
        if name == "Vendors":
            ws.auto_filter.ref = f"A1:G{len(rows)}"
            ws.freeze_panes = "A2"
    wb.properties.title = "Capital projects FY2027"
    wb.properties.creator = "Asset Management"
    wb.properties.lastModifiedBy = "Asset Management"
    wb.properties.created = dt.datetime(2027, 7, 6, 9, 10, 0)
    wb.properties.modified = dt.datetime(2027, 7, 6, 9, 10, 0)
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

    pin_ooxml(path, "2027-07-06T09:10:00Z", "2027-07-06T09:10:00Z", patch=patch)
    return cached


def make_xlsx():
    path = HERE / "gen-capex-register.xlsx"
    model = xlsx_model()
    cached = build_xlsx(path, model)
    shown = {name: [[xlsx_display(v, f) for v, f, _ in row] for row in sheet["rows"]] for name, sheet in model.items()}
    projects, monthly, vendors = shown[SHEET1], shown["Monthly Spend"], shown["Vendors"]
    checks = {
        # Locale-independent text cells and sheet names only; numbers, dates and booleans are checked by the tables.
        "must_contain": [XLSX_TITLE, XLSX_NOTE, XLSX_AFTER, MONTHLY_SOURCE, SHEET1, "Monthly Spend", "Vendors",
                         "Budget (USD)", "Spent to date", "Chiller replacement", "Lobby accessibility upgrades",
                         "Over budget", "Brightline Mechanical, Inc.", "Ötztal Paving & Sealcoat",
                         "Fire and life safety", "(510) 555-0175"],
        "ordered": [XLSX_TITLE, "Parking lot resurfacing", XLSX_AFTER, MONTHLY_SOURCE, "Keystone Fire Protection",
                    "Ridgeway Roofing Co."],
        "headings": [],
        "tables": [{"name": "Project List (the two header rows 3-4 to the Total row 13; title and note rows 1-2 and the note "
                             "in row 15 not included; 'Budget (USD)' merged across three columns, six headers merged "
                             "down, three header texts with a line break)", "rows": projects},
                   {"name": "Monthly Spend (all 9 rows; empty months are empty cells)", "rows": monthly},
                   {"name": "Vendors (all 7 rows)", "rows": vendors}],
        "noise": [],
        "absent": [],
    }
    n_formula = len(cached)
    gt = write_ground_truth(
        path, fmt="xlsx", title="Capital projects register, monthly spend and vendors, FY2027", pages_or_sheets=3,
        stresses=["three visible worksheets (Project List, Monthly Spend, Vendors)",
                  "merged title row A1:J1 and merged italic note row A2:J2 above a table that starts at row 3; an "
                  "italic note two rows below the table",
                  "two header rows: 'Budget (USD)' merged across three columns, six headers merged down over both "
                  "rows; three header texts contain a line break (Alt+Enter) and wrap",
                  f"{n_formula} formula cells saved with their computed (cached) values, as Excel saves them",
                  "thousands separators (#,##0), a negative value shown in parentheses (#,##0;(#,##0)), one-decimal "
                  "percent, dates as d-mmm-yyyy and mm/dd/yyyy, booleans TRUE/FALSE, one-decimal ratings",
                  "empty cells inside a numeric table (months without spend)",
                  "phone numbers stored as text (format @); frozen panes; autofilter on the Vendors sheet"],
        checks=checks,
        notes=("Expected cells are the text Excel shows in an en-US locale: amounts as '1,250,000' (#,##0), the "
               "negative remaining amount of CP-27-02 as '(12,400)' (#,##0;(#,##0)), percentages as '67.6%' (0.0%), "
               "dates as '30-Sep-2027' (d-mmm-yyyy) and '03/31/2028' (mm/dd/yyyy), booleans as 'TRUE'/'FALSE', "
               "ratings as '4.0' (0.0); zero amounts as '0'. Separators, date order and boolean words follow the "
               "viewer's locale, so (as in the earlier sets) must_contain lists only text cells, notes and the three "
               "sheet names, and number and date display is measured by the tables. The Project List table starts at its "
               "first header row (row 3): 'Project ID', 'Project', 'Building', 'Remaining (USD)', 'Spent (% of "
               "approved)', 'Target completion' and 'Status' are merged down over rows 3-4 and 'Budget (USD)' across "
               "'Approved', 'Committed' and 'Spent to date'; three header texts hold a line break, written with '\\n' "
               "(normalization makes it a space); a merged cell's text is in its top-left position and the covered "
               "positions are empty strings (not scored). The Total row has its label in column B and no values in "
               "A, I and J. Formulas (" f"{n_formula} cells: G5 '=D5-F5', H5 '=F5/D5', D13 '=SUM(D5:D12)', Monthly "
               "Spend I2 '=SUM(C2:H2)', ...) are saved with their computed values, so the expected cell is the value. "
               "Monthly Spend leaves months without spend empty (empty strings, not scored). The merged title and "
               "note rows and the notes below the Project List and Monthly Spend tables are checked by must_contain and "
               "ordered, not as table rows. Sheet names are tab labels: checked by must_contain, not as headings. No "
               "hidden sheets, comments, charts or print headers/footers: noise and absent are empty."))

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
                if cv.number_format in (FMT_DMY, FMT_MDY) and cv.value is not None:
                    require(isinstance(cv.value, dt.datetime), "xlsx: date cell is not a real date")
                if cv.number_format == "@" and cv.value is not None:
                    require(cv.data_type == "s", "xlsx: phone number is not stored as text")
                out.append(xlsx_display(cv.value, cv.number_format))
            grid.append(out)
        grids[ws_v.title] = grid
        texts.append(ws_v.title + "\n" + "\n".join(" ".join(r) for r in grid))
        fields += [c for r in grid for c in r if c]
    g = grids[SHEET1]
    require(g[0][0] == XLSX_TITLE and g[1][0] == XLSX_NOTE and len(g[0]) == 10, "xlsx: title/note rows")
    require(g[-1][0] == XLSX_AFTER and all(c == "" for c in g[-2]), "xlsx: note below the table")
    require(sorted(str(r) for r in wb_v[SHEET1].merged_cells.ranges)
            == sorted(["A1:J1", "A2:J2", "A3:A4", "B3:B4", "C3:C4", "G3:G4", "H3:H4", "I3:I4", "J3:J4", "D3:F3"]),
            "xlsx: merged ranges")
    require(sum(1 for ws in wb_f.worksheets for row in ws.iter_rows() for c in row if c.data_type == "f")
            == n_formula, "xlsx: formula count")
    require(g[5][0] == "CP-27-02" and g[5][6] == "(12,400)", "xlsx: negative in parentheses")
    m = grids["Monthly Spend"]
    require(m[-1][0] == MONTHLY_SOURCE and all(c == "" for c in m[-2]), "xlsx: monthly source note")
    tables_found = [g[2:2 + len(projects)], m[:len(monthly)], grids["Vendors"]]
    verify(path.name, "xlsx", gt, "\n".join(texts), tables_found=tables_found, fields=fields)
    return gt


# ===========================================================================
# 3. gen-facilities-update.pptx
# ===========================================================================

PPTX_TABLE = [
    ["Building", "Work orders", "", "Average days to close", "Tenant rating"],
    ["", "Opened", "Closed", "", ""],
    ["Building A", "412", "398", "2.4", "4.5 of 5"],
    ["Building B", "287", "281", "1.9", "4.7 of 5"],
    ["Building C", "1,064", "1,021", "3.1", "4.1 of 5"],
    ["Building D", "198", "196", "1.2", "4.8 of 5"],
    ["All buildings", "1,961", "1,896", "2.6", "4.4 of 5"],
]
PPTX_TABLE_MERGES = [(0, 0, 1, 0), (0, 1, 0, 2), (0, 3, 1, 3), (0, 4, 1, 4)]
ENERGY_BOX = ["Electricity use fell 6.8 percent compared with the first quarter of 2026.",
              "Natural gas use rose 3.1 percent because February was colder than usual.",
              "Water use was flat after the irrigation controllers were replaced."]
ENERGY_CALLOUT = "Savings to date: $48,300"
PPTX_SLIDES = [
    {"layout": 0, "title": "Facilities Committee Update", "subtitle": f"{SITE}, first quarter 2027"},
    {"layout": 1, "title": "Agenda", "numbered": True,
     "bullets": [(0, "Service performance in the first quarter"), (0, "Status of the capital projects"),
                 (0, "Energy use and utility costs"), (0, "Decisions requested from the committee")]},
    {"layout": 5, "title": "Work Orders by Building", "table": True,
     "notes": "Building C has the most work orders because its loading docks and roll-up doors see heavy use."},
    {"layout": 3, "title": "Capital Projects",
     "left": [(0, "Completed: fire alarm panels and data center batteries"),
              (0, "In progress: chiller, lighting retrofit and elevators"),
              (1, "Chiller replacement is 67.6 percent spent")],
     "right": [(0, "Roof renewal closed 1.9 percent over budget"),
               (0, "Parking lot resurfacing moves to spring 2028"),
               (1, "Design work starts in the third quarter")],
     "notes": "The roof overrun came from replacing wet insulation that was found after the old membrane came off."},
    {"layout": 5, "title": "Energy Use", "energy": True},
    {"layout": 2, "title": "Decisions", "body": "Two items need a committee vote today"},
    {"layout": 1, "title": "Decisions Requested",
     "bullets": [(0, "Approve $96,000 for the parking lot design phase"),
                 (1, "Construction would follow in spring 2028 after a separate vote"),
                 (0, "Extend the elevator maintenance contract by one year"),
                 (1, "The current contract ends on June 30, 2027")],
     "notes": "Both items were reviewed by the finance subcommittee on March 18 and are recommended for approval."},
]


def _pptx_fill(tf, items, numbered=False):
    for i, (level, text) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.level = level
        if numbered:
            ppr = p._p.get_or_add_pPr()
            ppr.set("marL", "457200")
            ppr.set("indent", "-457200")
            for tag, attrs in (("a:buFont", {"typeface": "+mj-lt"}), ("a:buAutoNum", {"type": "arabicPeriod"})):
                ppr.append(ppr.makeelement(pqn(tag), attrs))


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
            _pptx_fill(slide.placeholders[1].text_frame, spec["bullets"], numbered=spec.get("numbered", False))
        if "left" in spec:
            require(layout.name == "Two Content", "pptx: layout 3 is not Two Content")
            _pptx_fill(slide.placeholders[1].text_frame, spec["left"])
            _pptx_fill(slide.placeholders[2].text_frame, spec["right"])
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
        if spec.get("energy"):
            box = slide.shapes.add_textbox(Inches(0.6), Inches(1.8), Inches(8.8), Inches(2.4))
            box.text_frame.word_wrap = True
            for i, text in enumerate(ENERGY_BOX):
                p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
                p.text = text
                p.runs[0].font.size = PPt(20)
            callout = slide.shapes.add_textbox(Inches(5.6), Inches(4.8), Inches(3.8), Inches(0.8))
            callout.text_frame.text = ENERGY_CALLOUT
            callout.text_frame.paragraphs[0].runs[0].font.size = PPt(24)
            callout.text_frame.paragraphs[0].runs[0].font.bold = True
        if "notes" in spec:
            slide.notes_slide.notes_text_frame.text = spec["notes"]
    props = prs.core_properties
    props.title = PPTX_SLIDES[0]["title"]
    props.author = "Asset Management"
    props.last_modified_by = "Asset Management"
    props.comments = ""
    props.revision = 3
    props.created = dt.datetime(2027, 3, 22, 11, 0, 0)
    props.modified = dt.datetime(2027, 3, 24, 17, 45, 0)
    prs.save(path)
    pin_ooxml(path, "2027-03-22T11:00:00Z", "2027-03-24T17:45:00Z")


def make_pptx():
    path = HERE / "gen-facilities-update.pptx"
    build_pptx(path)
    paragraphs = ([PPTX_SLIDES[0]["subtitle"], PPTX_SLIDES[5]["body"]]
                  + [t for s in PPTX_SLIDES for key in ("bullets", "left", "right") for _, t in s.get(key, [])]
                  + ENERGY_BOX + [ENERGY_CALLOUT])
    notes = [s["notes"] for s in PPTX_SLIDES if "notes" in s]
    must = [p for p in paragraphs if len(p.split()) >= MIN_PHRASE_WORDS] + notes
    short = [p for p in paragraphs if len(p.split()) < MIN_PHRASE_WORDS]
    checks = {
        "must_contain": must,
        "ordered": ["Facilities Committee Update", "Service performance in the first quarter",
                    "Average days to close", "Roof renewal closed 1.9 percent over budget",
                    "Electricity use fell 6.8 percent", ENERGY_CALLOUT,
                    "Extend the elevator maintenance contract by one year"],
        "headings": [s["title"] for s in PPTX_SLIDES],
        "tables": [{"name": "Slide 3: Work Orders by Building (two header rows: 'Building', 'Average days to close' "
                             "and 'Tenant rating' merged down, 'Work orders' merged across 'Opened' and 'Closed')",
                    "rows": PPTX_TABLE}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pptx", title=PPTX_SLIDES[0]["title"], pages_or_sheets=len(PPTX_SLIDES),
        stresses=["slide titles (title placeholders) as headings",
                  "title slide with a subtitle; Section Header slide with a text placeholder",
                  "auto-numbered agenda (a:buAutoNum arabicPeriod): the numbers are not in the text",
                  "native 7x5 table with two header rows: three cells merged down, one merged across two columns; "
                  "counts with thousands separators",
                  "Two Content layout: two bulleted bodies with second-level items, left then right",
                  "Title Only slide with two free text boxes (not placeholders): a three-paragraph box and a bold "
                  "callout",
                  "two-level bullets; speaker notes on slides 3, 4 and 7"],
        checks=checks,
        notes=("Seven slides from python-pptx's default 4:3 template: 1 Title Slide, 2 and 7 Title and Content, 3 and "
               "5 Title Only, 4 Two Content, 6 Section Header. Slide 2's agenda is numbered by PowerPoint "
               "auto-numbering (1. 2. 3. 4. are drawn, not typed), so phrases do not include the numbers. Slide 3's "
               "table has two header rows: 'Building', 'Average days to close' and 'Tenant rating' are merged down "
               "over both rows and 'Work orders' across 'Opened' and 'Closed'; a merged cell's text is in its "
               "top-left position and the covered positions are empty strings (not scored); counts are text as typed "
               "('1,064'). Slide 4 is read left body then right body, as in shape order and as placed. Slide 5 holds "
               "two text boxes, the three-paragraph box first and the callout below it on the right, in shape order "
               "and position. Speaker notes (slides 3, 4 and 7) are in must_contain (3 phrases), never ordered "
               "anchors. headings are the seven slide titles. must_contain keeps every slide paragraph of at least "
               f"{MIN_PHRASE_WORDS} words; the {len(short)} shorter ones ({'; '.join(short)}) are not phrases (the "
               "callout is an ordered anchor). No footers, slide numbers, dates, hidden slides, charts or comments: "
               "noise and absent are empty."))
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
    auto = [p for p in prs.slides[1].placeholders[1].text_frame.paragraphs
            if p._p.pPr is not None and p._p.pPr.find(pqn("a:buAutoNum")) is not None]
    require(len(auto) == 4, "pptx: auto-numbered paragraphs")
    verify(path.name, "pptx", gt, "\n".join(texts), body_text="\n".join(body), headings_found=titles,
           tables_found=tables)
    return gt


# ===========================================================================
# 4. gen-work-orders.csv
# ===========================================================================

CSV_HEADER = ["wo_number", "opened", "building", "asset_tag", "category", "priority", "description", "technician",
              "labor_hours", "parts_cost", "status", "closed"]
CSV_TECHS = ["Søren Lindqvist", "Inés Ocampo", "Marcus Bell", "Jürgen Weiß", "Chidi Okafor"]
CSV_PRIORITIES = ["P3", "P2", "P3", "P4", "P1"]
# (category, asset tag prefix, description); descriptions hold commas, a semicolon, doubled quotes and line breaks.
CSV_ISSUES = [
    ("HVAC", "AHU", "Changed filters on all rooftop air handlers"),
    ("Plumbing", "DW", 'Replaced 2" ball valve on domestic water riser'),
    ("Electrical", "PNL", "Breaker trips in panel L2, traced to an overloaded circuit, loads rebalanced"),
    ("Elevators", "ELV", "Car 2 stops one inch below floor level at the lobby"),
    ("Life safety", "FACP", "Trouble signal on fire alarm panel\nGround fault cleared on loop 3"),
    ("HVAC", "CH", "Chiller high head pressure alarm; condenser coil cleaned"),
    ("Doors and locks", "DR", "Badge reader at east entrance not unlocking, reader replaced"),
    ("Lighting", "LT", "Pole lights out in parking row F"),
    ("Plumbing", "RR", "Leaking flush valve in third floor restroom\nDiaphragm kit replaced"),
    ("Roofing", "RF", "Ponding water near roof drain 4 after the storm, debris cleared"),
]


def csv_rows():
    rows = []
    for i in range(30):
        category, prefix, desc = CSV_ISSUES[(i * 3) % len(CSV_ISSUES)]
        letter_ = "ABCD"[(i * 3) % 4]
        opened = dt.datetime(2027, 3, 1, 7, 0) + dt.timedelta(hours=9 * i + (i * 5) % 7, minutes=(i * 23) % 60)
        status = "open" if i % 7 == 3 else ("on hold" if i % 11 == 6 else "closed")
        closed = "" if status != "closed" else (opened + dt.timedelta(hours=3 + (i * 13) % 50,
                                                                       minutes=(i * 17) % 60)).strftime("%m/%d/%Y %H:%M")
        hours = Decimal(1 + (i * 7) % 9) / 2
        cost = Decimal((i * 7919) % 4200) + Decimal((i * 37) % 100) / 100
        rows.append([f"WO-27-{1040 + i * 7}", opened.strftime("%m/%d/%Y %H:%M"), f"Bldg {letter_}",
                     f"{prefix}-{letter_}-{(i * 11) % 40 + 1:02d}", category, CSV_PRIORITIES[i % 5], desc,
                     CSV_TECHS[(i * 2) % 5], f"{hours:.1f}", "" if cost == 0 else f"{money(cost):,.2f}", status,
                     closed])
    return rows


def make_csv():
    path = HERE / "gen-work-orders.csv"
    rows = csv_rows()
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    path.write_bytes(buf.getvalue().encode("utf-8"))
    multi = [r for r in rows if "\n" in r[6]]
    big = [r[9] for r in rows if "," in r[9]]
    checks = {
        "must_contain": ["labor_hours", "parts_cost", "Søren Lindqvist", "Inés Ocampo", "Jürgen Weiß",
                         'Replaced 2" ball valve on domestic water riser',
                         "Breaker trips in panel L2, traced to an overloaded circuit, loads rebalanced",
                         "Chiller high head pressure alarm; condenser coil cleaned",
                         "Ponding water near roof drain 4 after the storm, debris cleared",
                         rows[0][0], rows[14][0], rows[-1][0], rows[0][1], rows[-1][1], big[0], big[-1]],
        "ordered": [rows[0][0], rows[7][0], rows[14][0], rows[21][0], rows[-1][0]],
        "headings": [],
        "tables": [{"name": "Work orders: header row and all 30 data rows", "rows": [CSV_HEADER] + rows}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="csv", title="Maintenance work-order export, March 2027", pages_or_sheets=None,
        stresses=["comma delimiter, minimal quoting (only fields with a comma, quote or line break are quoted), CRLF "
                  "record ends, UTF-8 without BOM",
                  f"{len(multi)} fields (two different texts) with an embedded line feed inside quotes, so those "
                  "records span two physical lines",
                  "fields with commas, a semicolon and a doubled double quote ('2\"\" ball valve')",
                  "amounts with thousands separators in quoted fields (parts_cost '1,234.56'), empty fields "
                  "(parts_cost, closed)",
                  "US date-times MM/DD/YYYY HH:MM, non-ASCII names (ø, é, ü, ß)"],
        checks=checks,
        notes=("RFC 4180 CSV as Excel and many maintenance systems write it: comma delimiter, a field is quoted only "
               "when it holds a comma, a double quote or a line break, CRLF between records, a bare LF inside the "
               "quoted multi-line descriptions, UTF-8 without BOM. The ten issue types repeat over the 30 work "
               f"orders; {len(multi)} description fields (two different texts) contain a line break inside the "
               "quotes, so those records span two physical lines; the expected cell keeps the line break "
               "(normalization turns it into a space). parts_cost values with a comma thousands separator are "
               "quoted ('\"1,234.56\"'); the table rule compares them with the comma removed on both sides. Open and "
               "on-hold work orders have an empty closed field; zero part costs are empty. Expected cell and phrase "
               "text is the parsed field value (quotes unescaped). The expected table is the whole file (header + 30 "
               "rows, 12 columns); empty fields are empty strings and are not scored. must_contain items are whole "
               "fields that never occur inside another field (work-order numbers and opening times of rows 1, 15 and "
               "30, two part costs with a thousands separator, four descriptions with a quote, commas or a semicolon, "
               "three non-ASCII names, two column names); no phrase is a multi-line field. ordered: the work-order "
               "numbers of rows 1, 8, 15, 22 and 30. A CSV has no headings, page furniture or hyphenation: headings, "
               "noise and absent are empty."))
    raw = path.read_bytes()
    require(not raw.startswith(b"\xef\xbb\xbf") and raw.count(b"\r\n") == 31, "csv: BOM / CRLF records")
    text = raw.decode("utf-8")
    parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=","))
    require(parsed[0] == CSV_HEADER and parsed[1:] == rows and len(parsed) == 31, "csv: read-back differs")
    require(all(len(r) == len(CSV_HEADER) for r in parsed), "csv: ragged rows")
    require(len(multi) >= 4 and len({r[6] for r in multi}) == 2 and len(big) >= 2, "csv: features")
    require('"Replaced 2"" ball valve on domestic water riser"' in text and '"' + rows[0][0] not in text,
            "csv: quoting")
    verify(path.name, "csv", gt, "\n".join(" ".join(r) for r in parsed), tables_found=[parsed],
           fields=[c for r in parsed for c in r])
    return gt


# ===========================================================================
# 5. gen-asset-register.json
# ===========================================================================

JSON_ASSETS = [
    {"tag": "AHU-A-03", "description": "Air handling unit, rooftop", "category": "HVAC",
     "location": {"building": "A", "floor": "Roof", "room": None}, "manufacturer": "Nordvent Systems",
     "model": "NV-4200", "serial": "NV42-19-00871", "installed": "2019-06-14", "in_service": True,
     "specs": {"airflow_cfm": 12000, "motor_hp": 15, "filter_size": "24 x 24 x 4 in"},
     "warranty": None,
     "service_history": [
         {"date": "2027-01-12", "work_order": "WO-27-0112", "summary": "Belt replaced, bearings greased",
          "cost_usd": 412.5},
         {"date": "2027-03-01", "work_order": "WO-27-1040", "summary": "Quarterly filter change", "cost_usd": 286.0}],
     "replacement_cost_usd": 86500, "tags": ["critical", "rooftop"]},
    {"tag": "CH-A-01", "description": "Centrifugal chiller, 400 tons", "category": "HVAC",
     "location": {"building": "A", "floor": "Roof", "room": "Chiller plant"},
     "manufacturer": "Kessler & Mohr Kältetechnik GmbH", "model": "KM-C400", "serial": "C400-2027-0016",
     "installed": "2027-05-20", "in_service": False, "specs": {"capacity_tons": 400, "refrigerant": "R-1233zd"},
     "warranty": {"provider": "Kessler & Mohr Kältetechnik GmbH", "expires": "2032-05-19", "parts_only": False},
     "service_history": [], "replacement_cost_usd": 1150000, "tags": ["critical", "capital project CP-27-01"]},
    {"tag": "GEN-D-01", "description": "Diesel emergency generator, 750 kW", "category": "Electrical",
     "location": {"building": "D", "floor": "Ground", "room": "Generator yard"}, "manufacturer": "Halvorsen Power",
     "model": "HP-750D", "serial": "HP750-17-3321", "installed": "2017-11-02", "in_service": True,
     "specs": {"output_kw": 750, "fuel_tank_gal": 1200, "runtime_hours": 1843.6},
     "warranty": None,
     "service_history": [
         {"date": "2027-02-17", "work_order": "WO-27-0388", "summary": "Load bank test, 2 hours at 75 percent",
          "cost_usd": 1980.0}],
     "replacement_cost_usd": 412000, "tags": ["critical", "life safety"]},
    {"tag": "ELV-B-02", "description": "Traction elevator, car 2", "category": "Elevators",
     "location": {"building": "B", "floor": "All", "room": None}, "manufacturer": "Summit Vertical Transport",
     "model": "ST-3500", "serial": "ST35-09-7710", "installed": "2009-08-28", "in_service": True,
     "specs": {"capacity_lb": 3500, "speed_fpm": 350, "stops": 4},
     "warranty": None,
     "service_history": [
         {"date": "2027-03-04", "work_order": "WO-27-0952", "summary": "Releveling adjusted at lobby",
          "cost_usd": 0}],
     "replacement_cost_usd": 365000, "tags": ["capital project CP-27-05"]},
    {"tag": "FACP-A-01", "description": "Fire alarm control panel", "category": "Life safety",
     "location": {"building": "A", "floor": "Ground", "room": "Fire command room"},
     "manufacturer": "Keystone Fire Protection", "model": "KF-8000", "serial": "KF8-27-0451",
     "installed": "2027-04-26", "in_service": True, "specs": {"loops": 4, "devices": 612},
     "warranty": {"provider": "Keystone Fire Protection", "expires": "2030-04-25", "parts_only": True},
     "service_history": [], "replacement_cost_usd": 92500, "tags": ["life safety"]},
    {"tag": "WH-C-02", "description": "Gas water heater, 100 gal", "category": "Plumbing",
     "location": {"building": "C", "floor": "Ground", "room": "Café kitchen"}, "manufacturer": "Aquafort",
     "model": "AF-100G", "serial": "AF1-21-55870", "installed": "2021-03-09", "in_service": True,
     "specs": {"capacity_gal": 100, "input_btu": 199900, "setpoint": "60 °C"},
     "warranty": {"provider": "Aquafort", "expires": "2027-03-08", "parts_only": True},
     "service_history": [
         {"date": "2026-12-03", "work_order": "WO-26-9917", "summary": 'Replaced 3/4" relief valve',
          "cost_usd": 168.4}],
     "replacement_cost_usd": 14800, "tags": []},
    {"tag": "UPS-D-01", "description": "Uninterruptible power supply, 300 kVA", "category": "Electrical",
     "location": {"building": "D", "floor": "Ground", "room": "Data hall 1"}, "manufacturer": "Halvorsen Power",
     "model": "HP-UPS300", "serial": "U300-18-0042", "installed": "2018-10-15", "in_service": True,
     "specs": {"rating_kva": 300, "battery_strings": 4, "battery_install": "2027-03-12"},
     "warranty": None, "service_history": [], "replacement_cost_usd": 238000,
     "tags": ["critical", "capital project CP-27-07"]},
    {"tag": "RTU-B-05", "description": "Packaged rooftop unit, fitness center", "category": "HVAC",
     "location": {"building": "B", "floor": "Roof", "room": None}, "manufacturer": "Nordvent Systems",
     "model": "NV-RTU15", "serial": "NVR15-14-2209", "installed": "2014-07-01", "in_service": True,
     "specs": {"cooling_tons": 15, "heating": "gas", "economizer": True},
     "warranty": None, "service_history": [], "replacement_cost_usd": 47250, "tags": ["rooftop"]},
]


def json_model():
    return {"register": {"site": SITE, "exported_at": "2027-04-02T08:15:00-07:00", "asset_count": len(JSON_ASSETS),
                         "source": "CMMS export, schema 3.2", "currency": "USD"},
            "assets": JSON_ASSETS}


def make_json():
    path = HERE / "gen-asset-register.json"
    obj = json_model()
    raw = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.write_text(raw, encoding="utf-8")
    checks = {
        "must_contain": ["service_history", "replacement_cost_usd", "AHU-A-03", "RTU-B-05",
                         "Centrifugal chiller, 400 tons", "Kessler & Mohr Kältetechnik GmbH", "Café kitchen",
                         'Replaced 3/4" relief valve', "Load bank test, 2 hours at 75 percent", "capital project CP-27-01",
                         "2027-04-02T08:15:00-07:00", "NV42-19-00871", "60 °C", "1843.6", "1150000"],
        "ordered": ["AHU-A-03", "Centrifugal chiller, 400 tons", "ELV-B-02", "Gas water heater, 100 gal",
                    "RTU-B-05"],
        "headings": [],
        "tables": [],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="json", title="Equipment asset register export (8 assets), April 2027", pages_or_sheets=None,
        stresses=["pretty-printed JSON with 2-space indentation and a final newline",
                  "top-level object holding a metadata object and an array of 8 asset objects",
                  "nested objects (location, specs, warranty) and arrays of objects (service_history), arrays of "
                  "strings (tags)",
                  "null values, booleans, empty arrays, an object that is null in some records and an object in "
                  "others",
                  "objects whose keys differ from one record to the next (specs)",
                  "non-ASCII text kept as UTF-8 (ä, é, °), an escaped double quote, decimal and integer numbers, a "
                  "timestamp with a UTC offset"],
        checks=checks,
        notes=("UTF-8 JSON written by json.dumps(..., ensure_ascii=False, indent=2) plus a final newline: one key or "
               "value per line, key order as written, non-ASCII characters as-is. A converter may keep it as JSON, "
               "fence it as code, or render it as text, lists or tables; no Markdown structure is expected, so "
               "headings and tables are empty. must_contain items are whole keys or scalar values that never occur "
               "inside another key or value (numbers as JSON writes them: a runtime of 1843.6 hours and a "
               "replacement cost of 1150000); the summary with an escaped quote matches its raw JSON form too, "
               "because matching deletes backslashes, and service_history matches servicehistory because it deletes "
               "underscores. ordered follows document order: the tags of assets 1, 4 and 8 and the descriptions of "
               "assets 2 and 6. Tags such as 'capital project CP-27-01' refer to the capital projects of the other "
               "generated files; the domains and companies are fictitious."))
    text = path.read_text(encoding="utf-8")
    require(json.loads(text) == obj and text.endswith("}\n") and '\n  "assets": [' in text, "json: read-back differs")
    require('\\"' in text and "Kältetechnik" in text and "°C" in text, "json: escaping")
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
    require([] in [a["service_history"] for a in JSON_ASSETS] and [] in [a["tags"] for a in JSON_ASSETS]
            and None in [a["warranty"] for a in JSON_ASSETS], "json: empty arrays / null objects")
    verify(path.name, "json", gt, text, fields=fields)
    return gt


# ===========================================================================
# 6. gen-inspection-report.pdf (not read back with a text extractor; see the module doc)
# ===========================================================================

PDF_TITLE = "Annual Fire and Life Safety Inspection"
PDF_SUBTITLE = "Building C, 2300 Larkspur Drive, inspected on March 9, 2027"
PDF_HEADER_LEFT = COMPANY
PDF_HEADER_RIGHT = "Inspection report FLS-2027-031"
PDF_FOOTER = "Confidential: prepared for the owners association and its insurer"
PDF_KV = [
    ["Report number", "FLS-2027-031"],
    ["Inspector", "Rafael Quintero, NICET Level III"],
    ["Standard", "NFPA 72 and NFPA 25, current editions"],
    ["Overall result", "Passed with deficiencies"],
]
PDF_SUMMARY = ["All fire alarm, sprinkler and emergency lighting systems in Building C were inspected and tested.",
               "Eighteen of 5,493 devices failed, and none of the failures prevents the building from being "
               "occupied.",
               "The deficiencies listed below must be corrected within 30 days and confirmed in writing."]
PDF_SYSTEMS = [  # (system, inspected, passed)
    ("Fire alarm control panels", 2, 2),
    ("Smoke detectors", 1248, 1241),
    ("Heat detectors", 186, 186),
    ("Sprinkler heads", 3615, 3612),
    ("Emergency lights", 214, 209),
    ("Exit signs", 132, 131),
    ("Fire extinguishers", 96, 94),
]
PDF_TABLE1_CAPTION = "Table 1. Devices inspected, passed and failed by system"
PDF_FINDINGS = ["Seven smoke detectors on the second floor failed the sensitivity test and must be replaced.",
                "Three sprinkler heads in the loading dock are painted over and must be replaced.",
                "Five emergency lights did not stay on for the full 90 minutes.",
                "One exit sign above the east stairwell door is not illuminated.",
                "Two fire extinguishers in the warehouse are overdue for their annual service."]
PDF_ACTIONS_HEADER = ["Finding", "Corrective action", "Owner", "Due date"]
PDF_ACTIONS = [
    ["1", "Replace the seven smoke detectors and repeat the sensitivity test on the whole second floor loop.",
     "Corvane", "April 8, 2027"],
    ["2", "Replace the painted sprinkler heads with heads of the same temperature rating and protect the new heads "
          "during future painting.", "Licensed subcontractor", "April 8, 2027"],
    ["3", "Replace the batteries of the five emergency lights and repeat the 90-minute discharge test.", "Corvane",
     "March 31, 2027"],
    ["4", "Replace the LED module of the exit sign.", "Corvane", "March 19, 2027"],
    ["5", "Service and tag both extinguishers.", "Licensed subcontractor", "March 26, 2027"],
]
PDF_NOTES = ["Device counts include spare devices stored on site.",
             "Pass rates are rounded to one decimal place.",
             "Photographs of each deficiency are kept with the inspection file."]
PDF_NOTE = ("The next annual inspection is due in March 2028; the quarterly sprinkler valve inspections continue "
            "in the meantime.")


def pdf_systems_table():
    rows = [["System", "Devices", "", "", "Pass rate"], ["", "Inspected", "Passed", "Failed", ""]]
    ti = tp = 0
    for name, inspected, passed in PDF_SYSTEMS:
        rows.append([name, f"{inspected:,}", f"{passed:,}", f"{inspected - passed:,}",
                     f"{pct1(Decimal(passed) / Decimal(inspected))}%"])
        ti += inspected
        tp += passed
    rows.append(["Total", f"{ti:,}", f"{tp:,}", f"{ti - tp:,}", f"{pct1(Decimal(tp) / Decimal(ti))}%"])
    require(ti == 5493 and ti - tp == 18, "pdf: totals differ from the summary text")
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
    systems = pdf_systems_table()
    t1 = Table(systems, colWidths=[2.6 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch], hAlign="LEFT")
    t1.setStyle(TableStyle(grid + [
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (1, 0), (3, 0)), ("SPAN", (4, 0), (4, 1)),
        ("FONT", (0, 0), (-1, 1), "Helvetica-Bold", 9), ("FONT", (0, 2), (-1, -2), "Helvetica", 9),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#DDE3EA")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("ALIGN", (1, 2), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    actions = [PDF_ACTIONS_HEADER] + [[r[0], RLParagraph(xml_escape(r[1]), cell), RLParagraph(xml_escape(r[2]), cell),
                                       r[3]] for r in PDF_ACTIONS]
    t2 = Table(actions, colWidths=[0.65 * inch, 3.45 * inch, 1.2 * inch, 1.2 * inch], hAlign="LEFT", repeatRows=1)
    t2.setStyle(TableStyle(grid + [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                                   ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE3EA")),
                                   ("ALIGN", (0, 0), (0, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story = [para(PDF_TITLE, title), para(PDF_SUBTITLE, sub), kv, para("Summary", h2)]
    story += [para(s) for s in PDF_SUMMARY]
    story += [para("Systems Inspected", h2), para(PDF_TABLE1_CAPTION, cap), t1, para("Findings", h2),
              ListFlowable([ListItem(para(t)) for t in PDF_FINDINGS], bulletType="1", bulletFormat="%s.",
                           leftIndent=18),
              para("Corrective Actions", h2), t2, para("Notes", h2),
              ListFlowable([ListItem(para(t)) for t in PDF_NOTES], bulletType="bullet", start="•",
                           leftIndent=18),
              Spacer(1, 4), para(PDF_NOTE, note)]
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.9 * inch, bottomMargin=0.85 * inch, title=PDF_TITLE, author="Inspection Team",
                            subject="Fire and life safety inspection", creator="Inspection Team", invariant=1)
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return max(pages)


def make_pdf():
    path = HERE / "gen-inspection-report.pdf"
    n = _pdf_build(path, 0)
    require(_pdf_build(path, n) == n, "pdf: page count changed between passes")
    require(n == 2, f"pdf: expected 2 pages, got {n}")
    systems = pdf_systems_table()
    actions = [PDF_ACTIONS_HEADER] + PDF_ACTIONS
    body_parts = ([PDF_TITLE, PDF_SUBTITLE] + [" ".join(r) for r in PDF_KV] + ["Summary"] + PDF_SUMMARY
                  + ["Systems Inspected", PDF_TABLE1_CAPTION] + [" ".join(r) for r in systems] + ["Findings"]
                  + PDF_FINDINGS + ["Corrective Actions"] + [" ".join(r) for r in actions] + ["Notes"] + PDF_NOTES
                  + [PDF_NOTE])
    furniture_text = "\n".join(f"{PDF_HEADER_LEFT} {PDF_HEADER_RIGHT} {PDF_FOOTER} Page {k} of {n}"
                               for k in range(1, n + 1))
    checks = {
        "must_contain": ([PDF_SUBTITLE] + PDF_SUMMARY + [PDF_TABLE1_CAPTION] + PDF_FINDINGS
                         + [PDF_ACTIONS[0][1], PDF_ACTIONS[1][1], PDF_ACTIONS[2][1]]
                         + PDF_NOTES + ["The next annual inspection is due in March 2028;",
                            "the quarterly sprinkler valve inspections continue in the meantime."]),
        "ordered": [PDF_TITLE, "Passed with deficiencies", "Eighteen of 5,493 devices failed",
                    "Fire alarm control panels", "Five emergency lights did not stay on",
                    "Replace the LED module of the exit sign", "The next annual inspection is due in March 2028"],
        "headings": [PDF_TITLE, "Summary", "Systems Inspected", "Findings", "Corrective Actions", "Notes"],
        "tables": [{"name": "Report details (key-value table without a header row)", "rows": PDF_KV},
                   {"name": "Table 1. Devices inspected, passed and failed by system (two header rows: 'System' and "
                            "'Pass rate' span both rows, 'Devices' spans three columns; total row)", "rows": systems},
                   {"name": "Corrective actions (one table over two pages, header row repeated on page 2; complete: "
                            "header row and 5 rows; action and owner cells wrap over several lines)",
                    "rows": actions}],
        "noise": [{"text": PDF_HEADER_LEFT, "max": 1}, {"text": PDF_HEADER_RIGHT, "max": 1},
                  {"text": PDF_FOOTER, "max": 1}],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pdf", title=PDF_TITLE, pages_or_sheets=n,
        stresses=["generated single-column PDF (ReportLab, standard Helvetica fonts, untagged)",
                  "title, a grey subtitle line and section headings set by font size and Helvetica-Bold only",
                  "key-value table without a header row, first column shaded and bold",
                  "table with two header rows: 'System' and 'Pass rate' span both rows, 'Devices' spans three "
                  "columns; counts with thousands separators, percentages, a bold total row",
                  "numbered list (1.-5.) and bulleted list drawn as list flowables",
                  "table whose action and owner cells wrap over two or three lines (Paragraph cells); it runs from "
                  "page 1 to page 2 with its header row repeated at the top of page 2",
                  "italic closing note; running header (left and right text with a rule) and footer ('Page N of 2') "
                  "on every page"],
        checks=checks,
        notes=("ReportLab 'invariant' mode pins the creation date and document ID, so the file is reproducible. The "
               "checks come from the generator's data in reading order; the file was NOT read back with any text "
               "extractor (blind protocol), only rendered to images with pdftoppm and looked at, and its font list "
               "was checked once with pdffonts (Helvetica, Helvetica-Bold and Helvetica-Oblique, base-14, not "
               "embedded). Headings: the 19-point title and the five 13.5-point section headings, all set in "
               "Helvetica-Bold; the subtitle line is regular weight and is a phrase, not a heading. Tables: the "
               "report-details table has no header row (its first row is data); in Table 1 'System' and 'Pass rate' "
               "span both header rows and 'Devices' spans 'Inspected', 'Passed' and 'Failed' (spanned positions are "
               "empty strings, not scored); counts are '1,248'-style text (compared without the comma) and pass "
               "rates one-decimal percentages ('99.4%'); the corrective-actions table's action and owner cells wrap "
               "inside the cell, and each expected cell is the whole text with single spaces; that table starts at the "
               "foot of page 1 (header row and row 1) and continues on page 2 with its header row repeated "
               "(repeatRows=1), so the expected table is the header row and all 5 rows once, and a repeated header "
               "row inside a converted table costs precision only. In the local poppler render the bold and oblique "
               "base-14 faces were drawn in regular weight (no bold font installed); the PDF names Helvetica-Bold and "
               "Helvetica-Oblique. must_contain: the "
               "subtitle, every summary sentence, the table caption, every finding, the three longest actions, every "
               "note and both clauses of the closing note (table cells are otherwise checked by the tables). ordered: title, overall result, summary, first table row, a finding, an "
               "action, the closing note. Noise: the running header's two parts ('" + PDF_HEADER_LEFT + "', '" + PDF_HEADER_RIGHT +
               "') and the footer ('" + PDF_FOOTER + "') are printed once per page (twice) and occur nowhere in the "
               "body (the body names the company only as 'Corvane'), max 1 each; 'Page N of 2' is not "
               "counted (it differs per page). No hyphenation (ReportLab does not hyphenate by default): absent is "
               "empty."))
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
    print(f"libraries: {lib_versions()}")


if __name__ == "__main__":
    try:
        main()
    except CheckError as exc:
        print(f"CHECK FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
