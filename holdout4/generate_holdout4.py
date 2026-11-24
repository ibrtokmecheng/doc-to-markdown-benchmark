#!/usr/bin/env python3
"""Generate the synthetic part of the FOURTH held-out doc-to-markdown test set (holdout4/).

Writes six ordinary business documents to holdout4/ and one ground-truth JSON per document to
holdout4/ground-truth/<file>.json (same schema as corpus/, holdout/, holdout2/ and holdout3/, checked by score.mjs):

    gen-travel-policy.docx      Word travel and expense policy: Title style, headings at three levels with typed
                                section numbers, two-level bullets, a numbered list, a second numbered list with
                                lettered sub-items that restarts at 1, a limits table with two header rows (cells merged
                                down and across), two-paragraph body cells and a body cell merged across three columns, a
                                mileage table with header cells broken by a line break and a total row merged across three
                                columns, an italic table note, bold and italic runs, a sign-off table with empty cells,
                                page header and footer.
    gen-budget-variance.xlsx    Workbook with three sheets: a budget-versus-actual sheet (merged title and note rows, two
                                header rows with a group merged across four columns and six headers merged down, header
                                text with line breaks, thousands separators, negatives in parentheses, negative
                                one-decimal percentages, formulas saved with their computed values, a total row, frozen
                                panes, a note below the table); monthly headcount with empty cells, d-mmm-yyyy dates and
                                formula totals; a cost-center list with codes stored as text with leading zeros,
                                booleans, mm/dd/yyyy dates and percentages, autofilter.
    gen-sales-review.pptx       Seven-slide sales review deck: title slide, auto-numbered agenda, a native table with two
                                header rows (merged across and down), a Two Content slide with two-level bullets, a Title
                                Only slide with two free text boxes, a Section Header slide, two-level bullets, speaker
                                notes.
    gen-customer-invoices.csv   Invoice export as Excel writes 'CSV UTF-8': UTF-8 with a byte order mark, comma
                                delimiter, minimal quoting, CRLF record ends, quoted fields with line breaks, commas,
                                semicolons and doubled quotes, amounts with thousands separators, ISO dates, empty
                                fields, non-ASCII names.
    gen-product-catalog.json    Product catalog export: pretty-printed (2-space indent), a top-level object with a
                                metadata object and an array of 8 products, nested objects and arrays of objects, keys that
                                differ between records, nulls, booleans, empty arrays, escaped quotes, non-ASCII text.
    gen-ops-report.pdf          ReportLab monthly operations report, 2 pages: title, key-value table without a header row,
                                headings by font size, a table with two header rows (cells spanning across and down) and
                                a total row, a numbered list, a table with wrapped multi-line cells that continues on page
                                2 with its header repeated, a bulleted list, an italic note, running header and footer.

The content is new (not reused from the generators of holdout/, holdout2/ or holdout3/). Everything is fixed in this
file: no randomness, no clock. Every ground-truth item is derived from the same Python data that is written into the
document. After writing, the DOCX, XLSX, PPTX, CSV and JSON files are read back (python-docx, openpyxl, python-pptx,
csv, json) and every check is verified against the read-back text, with the audit rules of the earlier sets (no file
name or converter-added text in a check; prose phrases of at least 6 words that occur once; data-file items are whole,
distinctive fields; ordered anchors unique and in reading order, never from speaker notes). The PDF is NOT read back
with any text extractor (blind protocol): its checks are verified against the generator's own data in reading order,
and its pages were only rendered to images (pdftoppm) and looked at. Every answer file is also checked against the
validation rules of score.mjs validateGroundTruth (re-implemented below, score.mjs is not run). Any mismatch aborts
with exit status 1.

No converter (PackForAI, MarkItDown or other) is run here or was run while writing the answers.

Run from the benchmark folder (ephemeral environment, no global installs):

    uv run --with python-docx --with openpyxl --with python-pptx --with reportlab \
        python3 -I holdout4/generate_holdout4.py

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
LICENSE = ("Synthetic document written for the fourth held-out benchmark set and generated by "
           "holdout4/generate_holdout4.py; no third-party material. All organisations, people, addresses, phone "
           "numbers, e-mail domains and figures are fictitious.")
LIBS = ("python-docx", "openpyxl", "python-pptx", "lxml", "reportlab")
MIN_PHRASE_WORDS = 6
COMPANY = "Brightwater Provisions, Inc."
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
    if not isinstance(gt.get("file"), str) or not gt["file"].strip() or re.search(r"[\\/\0]", gt["file"]):
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
        if not isinstance(t.get("name"), str) or not t["name"].strip():
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
        if not isinstance(n.get("max"), int) or isinstance(n.get("max"), bool) or n["max"] < 0 \
                or not normalize(n.get("text", "")):
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
        "notes": notes + f" Generated by holdout4/generate_holdout4.py with {lib_versions()}; no converter was run "
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
# 1. gen-travel-policy.docx
# ===========================================================================

DOCX_TITLE = "Travel and Expense Policy"
DOCX_HEADER = COMPANY
DOCX_FOOTER = "Policy FIN-07, revision 3, effective January 1, 2028"
DOCX_T1 = [
    ["City tier", "Example cities", "Hotel per night", "Daily meal allowance", "", "", "Incidentals per day"],
    ["", "", "", "Breakfast", "Lunch", "Dinner", ""],
    ["Tier 1", "New York\nSan Francisco", "$325", "$22", "$28", "$55", "$15"],
    ["Tier 2", "Chicago\nSeattle", "$245", "$18", "$24", "$45", "$12"],
    ["Tier 3", "Denver\nPhoenix", "$185", "$16", "$20", "$38", "$10"],
    ["Tier 4", "All other U.S. cities", "$150", "$14", "$18", "$32", "$8"],
    ["International", "Set by the travel desk", "Actual cost", "Per diem of the destination country", "", "",
     "$20"],
]
DOCX_T1_MERGES = [(0, 0, 1, 0), (0, 1, 1, 1), (0, 2, 1, 2), (0, 3, 0, 5), (0, 6, 1, 6), (6, 3, 6, 5)]
MILEAGE = [  # (vehicle, rate per mile, example trip miles)
    ("Car or van", "0.67", 1240),
    ("Motorcycle", "0.52", 310),
    ("Electric vehicle", "0.67", 2085),
    ("Bicycle", "0.20", 145),
]


def docx_mileage_table():
    rows = [["Vehicle", "Rate per mile\n(USD)", "Example trip\n(miles)", "Example claim\n(USD)"]]
    total = Decimal(0)
    for vehicle, rate, miles in MILEAGE:
        amount = money(Decimal(rate) * miles)
        total += amount
        rows.append([vehicle, f"${Decimal(rate):,.2f}", f"{miles:,}", f"${amount:,.2f}"])
    rows.append(["Total of the example claims", "", "", f"${total:,.2f}"])
    return rows


DOCX_T2 = docx_mileage_table()
DOCX_T2_MERGES = [(len(DOCX_T2) - 1, 0, len(DOCX_T2) - 1, 2)]
DOCX_SIGN = [
    ["Role", "Name", "Signature", "Date"],
    ["Policy owner", "Priya Raman, Corporate Controller", "", ""],
    ["Approver", "Tomás Herrera, Chief Financial Officer", "", ""],
]

# (kind, payload). Runs: (text, "" | "b" | "i").
DOCX_BLOCKS = [
    ("title", DOCX_TITLE),
    ("para", [("Issued by the Finance Department of " + COMPANY + " for all employees and contractors", "i")]),
    ("para", [("Policy owner: ", "b"), ("Corporate Controller, Finance Department", "")]),
    ("h1", "1. Purpose and Scope"),
    ("para", [("This policy explains how employees book business travel, which costs Brightwater Provisions "
               "reimburses and how expense reports are approved.", "")]),
    ("para", [("It applies to every trip taken on company business, including customer visits, supplier audits and "
               "training courses.", "")]),
    ("h1", "2. Booking Travel"),
    ("h2", "2.1 Air and Rail"),
    ("bullet", (0, "Book economy class through the company travel portal at least 14 days before departure")),
    ("bullet", (1, "Premium economy is allowed on flights longer than six hours")),
    ("bullet", (0, "Choose rail instead of air for trips under 250 miles when the rail journey takes less than "
                   "five hours")),
    ("bullet", (0, "Keep the booking confirmation and the boarding pass for the expense report")),
    ("bullet", (1, "Electronic copies are accepted in place of paper receipts")),
    ("h2", "2.2 Hotels and Daily Allowances"),
    ("para", [("Table 1 shows the maximum nightly hotel rate and the meal allowance for each city tier.", "")]),
    ("caption", "Table 1. Hotel and meal limits by city tier (USD)"),
    ("table", 1),
    ("note", "Note: Hotel taxes are reimbursed in addition to the nightly limit; room service and minibar charges "
             "are not."),
    ("h3", "2.2.1 Extended Stays"),
    ("number", (0, "Ask the travel desk for a corporate apartment when a stay is longer than 14 nights.")),
    ("number", (0, "Compare the apartment rate with the hotel limit for the same city tier.")),
    ("number", (0, "Attach the approved comparison to the first expense report of the stay.")),
    ("h1", "3. Personal Car Use"),
    ("para", [("Employees who drive their own vehicle on company business are reimbursed per mile at the rates in "
               "Table 2.", "")]),
    ("caption", "Table 2. Mileage rates and example claims"),
    ("table", 2),
    ("para", [("Mileage claims must be submitted within ", ""), ("60 days", "b"), (" of the trip. Claims older than ",
              ""), ("90 days", "i"), (" are not paid.", "")]),
    ("h1", "4. Submitting Expense Reports"),
    ("number2", (0, "Enter every expense in the expense system within 30 days of returning from the trip.")),
    ("number2", (1, "Photograph each receipt of $25 or more and attach it to the expense line.")),
    ("number2", (1, "Explain any expense that is above the limits in this policy.")),
    ("number2", (0, "Submit the completed report to your manager for approval.")),
    ("number2", (0, "Finance reviews approved reports and pays them with the next payroll run.")),
    ("h1", "5. Expenses Not Reimbursed"),
    ("bullet", (0, "Fines for traffic or parking violations, even when the vehicle was used for work.")),
    ("bullet", (0, "Upgrades to business or first class that were not approved in advance.")),
    ("bullet", (0, "Travel costs of family members or friends who join the trip.")),
    ("h1", "6. Approval"),
    ("para", [("The policy owner and the chief financial officer sign below to approve this revision.", "")]),
    ("table", 3),
]

DOCX_MUST = [
    "Issued by the Finance Department of " + COMPANY + " for all employees and contractors",
    "Policy owner: Corporate Controller, Finance Department",
    "This policy explains how employees book business travel, which costs Brightwater Provisions reimburses and how "
    "expense reports are approved.",
    "It applies to every trip taken on company business, including customer visits, supplier audits and training "
    "courses.",
    "Book economy class through the company travel portal at least 14 days before departure",
    "Premium economy is allowed on flights longer than six hours",
    "Choose rail instead of air for trips under 250 miles when the rail journey takes less than five hours",
    "Keep the booking confirmation and the boarding pass for the expense report",
    "Electronic copies are accepted in place of paper receipts",
    "Table 1 shows the maximum nightly hotel rate and the meal allowance for each city tier.",
    "Table 1. Hotel and meal limits by city tier (USD)",
    "Note: Hotel taxes are reimbursed in addition to the nightly limit; room service and minibar charges are not.",
    "Ask the travel desk for a corporate apartment when a stay is longer than 14 nights.",
    "Compare the apartment rate with the hotel limit for the same city tier.",
    "Attach the approved comparison to the first expense report of the stay.",
    "Employees who drive their own vehicle on company business are reimbursed per mile at the rates in Table 2.",
    "Table 2. Mileage rates and example claims",
    "Mileage claims must be submitted within 60 days of the trip.",
    "Claims older than 90 days are not paid.",
    "Enter every expense in the expense system within 30 days of returning from the trip.",
    "Photograph each receipt of $25 or more and attach it to the expense line.",
    "Explain any expense that is above the limits in this policy.",
    "Submit the completed report to your manager for approval.",
    "Finance reviews approved reports and pays them with the next payroll run.",
    "Fines for traffic or parking violations, even when the vehicle was used for work.",
    "Upgrades to business or first class that were not approved in advance.",
    "Travel costs of family members or friends who join the trip.",
    "The policy owner and the chief financial officer sign below to approve this revision.",
]
DOCX_ORDERED = [
    DOCX_TITLE,
    "This policy explains how employees book business travel",
    "Premium economy is allowed on flights longer than six hours",
    "Incidentals per day",
    "Compare the apartment rate with the hotel limit",
    "Electric vehicle",
    "Explain any expense that is above the limits",
    "The policy owner and the chief financial officer sign below",
]

BULLET_NUM_ID, NUMBER_NUM_ID, NUMBER2_NUM_ID = 61, 62, 63


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
                _docx_table(document, DOCX_T1, DOCX_T1_MERGES, 2, right_from=2, two_paragraph_cells=True)
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
    props.subject = "Travel and expense rules"
    props.author = "Finance Department"
    props.last_modified_by = "Finance Department"
    props.comments = ""
    props.keywords = ""
    props.category = ""
    props.revision = 3
    props.created = dt.datetime(2027, 10, 4, 9, 30, 0)
    props.modified = dt.datetime(2027, 11, 22, 16, 5, 0)
    document.save(path)
    pin_ooxml(path, "2027-10-04T09:30:00Z", "2027-11-22T16:05:00Z")


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
    path = HERE / "gen-travel-policy.docx"
    build_docx(path)
    headings = [p for k, p in DOCX_BLOCKS if k in ("h1", "h2", "h3")]
    checks = {
        "must_contain": DOCX_MUST,
        "ordered": DOCX_ORDERED,
        "headings": headings,
        "tables": [
            {"name": "Table 1. Hotel and meal limits by city tier (two header rows: 'City tier', 'Example cities', "
                     "'Hotel per night' and 'Incidentals per day' merged down, 'Daily meal allowance' merged across "
                     "three columns; example-city cells with two paragraphs; the International row's meal cell merged "
                     "across three columns)", "rows": DOCX_T1},
            {"name": "Table 2. Mileage rates and example claims (header cells broken by a line break; total row with "
                     "its label merged across three columns)", "rows": DOCX_T2},
            {"name": "Sign-off table (header row, two roles, empty signature and date cells)", "rows": DOCX_SIGN},
        ],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="docx", title=DOCX_TITLE, pages_or_sheets=None,
        stresses=["Title style, then an italic line and a line with a bold label run",
                  "Heading 1 / Heading 2 / Heading 3 with typed section numbers in the heading text (1., 2.1, 2.2.1)",
                  "two-level bulleted list; a numbered list; a second numbered list with lettered sub-items that "
                  "restarts at 1 (a new w:num with startOverride); a second bulleted list",
                  "limits table with two header rows: four header cells merged down (vMerge), one merged across three "
                  "columns (gridSpan 3); body cells holding two paragraphs; a body cell merged across three columns",
                  "mileage table whose header cells contain a line break (w:br), rates and miles with thousands "
                  "separators, a bold total row whose label is merged across three columns",
                  "Caption-style table titles, an italic 9-point note under a table",
                  "bold and italic runs inside a sentence; a sign-off table with empty cells; a non-ASCII name",
                  "page header and footer text"],
        checks=checks,
        notes=("The headings are Word Heading 1/2/3 paragraphs whose section numbers are typed as text ('2.2.1 "
               "Extended Stays'), not list numbering, so the expected headings include the numbers. The document "
               "title uses the Title style and is the first ordered anchor, not a heading (as in the earlier sets). "
               "Tables: in Table 1 'City tier', 'Example cities', 'Hotel per night' and 'Incidentals per day' are "
               "merged down over both header rows and 'Daily meal allowance' across 'Breakfast', 'Lunch' and "
               "'Dinner'; the example-city cells of tiers 1-3 hold two paragraphs, written with '\\n' between them "
               "(normalization makes it a space); in the International row 'Per diem of the destination country' is "
               "merged across the three meal columns. Table 2's header cells ('Rate per mile' / '(USD)', ...) are "
               "broken by a line break inside one paragraph, also written with '\\n'; its last row has 'Total of the "
               "example claims' merged across the first three columns. A merged cell's text is in its top-left grid "
               "position and the covered positions are empty strings (not scored), as in the corpus. Amounts are "
               "text as typed ('$1,396.95', miles '2,085'); the table rule compares them with the thousands commas "
               "removed on both sides. The sign-off table's signature and date cells are empty. Lists: the Air and "
               "Rail list has two levels; the Extended Stays list is numbered 1-3; the Submitting Expense Reports "
               "list is a second instance of the same numbering that restarts at 1, with lettered sub-items; the "
               "Expenses Not Reimbursed list is a one-level bulleted list. must_contain keeps every paragraph, list "
               "item, caption and note of at least 6 words, the paragraph with bold '60 days' and italic '90 days' "
               "split at its sentences (normalization deletes '*' and '_'). Page header ('" + DOCX_HEADER + "') and "
               "footer ('" + DOCX_FOOTER + "') are stored once each and are not checked; including or dropping them "
               "are both faithful. No footnotes, comments, tracked changes, hyperlinks or hyphenation: noise and "
               "absent are empty."))
    text, found_headings, tables, items, header, footer, br_cells = read_docx(path)
    require(header == DOCX_HEADER and footer == DOCX_FOOTER, "docx: header/footer")
    num_of = {"bullet": BULLET_NUM_ID, "number": NUMBER_NUM_ID, "number2": NUMBER2_NUM_ID}
    require(items == [(num_of[k], lvl, t) for k, p in DOCX_BLOCKS if k in num_of for lvl, t in [p]],
            "docx: list items/levels read back differ")
    require(br_cells == 3, f"docx: expected 3 header cells with a line break, got {br_cells}")
    verify(path.name, "docx", gt, text, headings_found=found_headings, tables_found=tables)
    require(normalize(DOCX_FOOTER) not in normalize(text), "docx: footer text also in the body")
    return gt


# ===========================================================================
# 2. gen-budget-variance.xlsx
# ===========================================================================

SHEET1 = "Q1 Variance"
XLSX_TITLE = "Operating Budget vs Actual, First Quarter FY2028"
XLSX_NOTE = "Amounts in U.S. dollars. Actual figures are unaudited and include accruals posted through April 10, 2028."
XLSX_AFTER = "Negative variances (in parentheses) mean that spending exceeded the budget."
FMT_INT = "#,##0"
FMT_PAREN = "#,##0;(#,##0)"
FMT_PCT1 = "0.0%"
FMT_DMY = "d-mmm-yyyy"
FMT_MDY = "mm/dd/yyyy"
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
OWNERS = {"Warehouse": "Dana Kowalczyk", "Transportation": "Luis Ortega", "Sales": "Mei-Ling Cho",
          "Administration": "Zoë Whitfield"}
COST_LINES = [  # (department, cost line, Q1 budget, January, February, March actuals)
    ("Warehouse", "Hourly wages", 1860000, 598400, 611250, 642980),
    ("Warehouse", "Forklift leases", 126000, 42000, 42000, 42000),
    ("Transportation", "Diesel fuel", 948000, 331900, 318450, 352775),
    ("Transportation", "Truck maintenance", 284500, 88140, 79960, 102315),
    ("Sales", "Travel and meals", 96000, 27480, 35120, 41905),
    ("Sales", "Trade shows", 150000, 0, 0, 118600),
    ("Administration", "Software subscriptions", 72600, 24200, 24200, 25010),
    ("Administration", "Office rent", 210000, 70000, 70000, 70000),
]
HEADCOUNT = [  # (department, Jan, Feb, Mar (None = not reported), open positions, last hire date or None)
    ("Warehouse", 142, 145, 151, 6, (2028, 3, 18)),
    ("Transportation", 58, 58, 61, 2, (2028, 3, 4)),
    ("Sales", 23, 24, None, 1, (2028, 1, 22)),
    ("Customer Service", 17, 17, 18, 0, (2028, 2, 12)),
    ("Administration", 12, 12, 12, 1, None),
]
HEADCOUNT_SOURCE = "Source: HR information system, headcount at month end; Sales March figure not yet reported."
COST_CENTERS = [  # (code stored as text, name, manager, active, opened, share of Q1 budget)
    ("0410", "Warehouse operations", "Dana Kowalczyk", True, (2014, 5, 1), "0.4884"),
    ("0420", "Fleet and transportation", "Luis Ortega", True, (2014, 5, 1), "0.3229"),
    ("0510", "Field sales", "Mei-Ling Cho", True, (2016, 9, 12), "0.0636"),
    ("0590", "Trade marketing (closed)", "Mei-Ling Cho", False, (2019, 2, 4), "0.0000"),
    ("0710", "Finance and administration", "Zoë Whitfield", True, (2014, 5, 1), "0.0751"),
    ("0720", "Information technology", "Ravi Subramanian", True, (2021, 7, 19), "0.0500"),
]
CC_HEADER = ["Cost center", "Name", "Manager", "Active", "Opened", "Share of Q1 budget"]


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
    if fmt == "General":
        require(d == d.to_integral_value(), "xlsx: integer cell")
        return str(int(d))
    raise ValueError(f"unexpected cell {value!r} with format {fmt!r}")


def xlsx_model():
    """{sheet: {"rows": [[(value, format, formula)]], "first": first row}} with formula values precomputed."""
    top = 3
    first_body = top + 2
    last_body = first_body + len(COST_LINES) - 1
    total_row = last_body + 1
    header1 = ["Department", "Cost line", "Q1 budget\n(USD)", "Actual (USD)", None, None, None, "Variance\n(USD)",
               "Variance\n(% of budget)", "Budget owner"]
    header2 = [None, None, None, "January", "February", "March", "Q1 total", None, None, None]
    variance = [[(h, "General", None) for h in header1], [(h, "General", None) for h in header2]]
    for k, (dept, line, budget, jan, feb, mar) in enumerate(COST_LINES):
        r = first_body + k
        actual = jan + feb + mar
        variance.append([(dept, "General", None), (line, "General", None), (budget, FMT_INT, None),
                         (jan, FMT_INT, None), (feb, FMT_INT, None), (mar, FMT_INT, None),
                         (actual, FMT_INT, f"SUM(D{r}:F{r})"), (budget - actual, FMT_PAREN, f"C{r}-G{r}"),
                         (Decimal(budget - actual) / Decimal(budget), FMT_PCT1, f"H{r}/C{r}"),
                         (OWNERS[dept], "General", None)])
    sums = [sum(line[i] for line in COST_LINES) for i in (2, 3, 4, 5)]
    actual_total = sum(sums[1:])
    variance.append([("Total", "General", None), (None, None, None)]
                    + [(v, FMT_INT, f"SUM({c}{first_body}:{c}{last_body})") for v, c in zip(sums, "CDEF")]
                    + [(actual_total, FMT_INT, f"SUM(G{first_body}:G{last_body})"),
                       (sums[0] - actual_total, FMT_PAREN, f"SUM(H{first_body}:H{last_body})"),
                       (Decimal(sums[0] - actual_total) / Decimal(sums[0]), FMT_PCT1, f"H{total_row}/C{total_row}"),
                       (None, None, None)])
    months = [f"{m} 2028" for m in MONTH_ABBR[:3]]
    head = [[(h, "General", None) for h in ["Department"] + months + ["Open positions", "Last hire"]]]
    for k, (dept, jan, feb, mar, open_, last) in enumerate(HEADCOUNT):
        head.append([(dept, "General", None), (jan, FMT_INT, None), (feb, FMT_INT, None), (mar, FMT_INT, None),
                     (open_, FMT_INT, None), (dt.datetime(*last) if last else None, FMT_DMY, None)])
    last = 1 + len(HEADCOUNT)
    col_totals = [sum((h[i] or 0) for h in HEADCOUNT) for i in (1, 2, 3, 4)]
    head.append([("Total", "General", None)]
                + [(t, FMT_INT, f"SUM({c}2:{c}{last})") for t, c in zip(col_totals, "BCDE")]
                + [(None, None, None)])
    centers = [[(h, "General", None) for h in CC_HEADER]]
    for code, name, manager, active, opened, share in COST_CENTERS:
        centers.append([(code, "@", None), (name, "General", None), (manager, "General", None),
                        (active, "General", None), (dt.datetime(*opened), FMT_MDY, None),
                        (Decimal(share), FMT_PCT1, None)])
    return {SHEET1: {"rows": variance, "first": top}, "Staffing": {"rows": head, "first": 1},
            "Cost Centers": {"rows": centers, "first": 1}}


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
            for col in (1, 2, 3, 8, 9, 10):
                ws.merge_cells(start_row=first, start_column=col, end_row=first + 1, end_column=col)
            ws.merge_cells(start_row=first, start_column=4, end_row=first, end_column=7)
            note_row = first + len(rows) + 1
            ws.cell(row=note_row, column=1, value=XLSX_AFTER).font = Font(italic=True, size=9)
            ws.freeze_panes = f"C{first + header_rows}"
        if name == "Staffing":
            ws.cell(row=len(rows) + 2, column=1, value=HEADCOUNT_SOURCE).font = Font(italic=True, size=9)
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
        widths = {SHEET1: (15, 24, 13, 12, 12, 12, 13, 13, 13, 17),
                  "Staffing": (18, 11, 11, 11, 15, 13),
                  "Cost Centers": (12, 28, 20, 9, 12, 18)}[name]
        for col, width in zip("ABCDEFGHIJ", widths):
            ws.column_dimensions[col].width = width
        if name == "Cost Centers":
            ws.auto_filter.ref = f"A1:F{len(rows)}"
            ws.freeze_panes = "A2"
    wb.properties.title = "Budget vs actual Q1 FY2028"
    wb.properties.creator = "Financial Planning"
    wb.properties.lastModifiedBy = "Financial Planning"
    wb.properties.created = dt.datetime(2028, 4, 12, 8, 45, 0)
    wb.properties.modified = dt.datetime(2028, 4, 12, 8, 45, 0)
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

    pin_ooxml(path, "2028-04-12T08:45:00Z", "2028-04-12T08:45:00Z", patch=patch)
    return cached


def make_xlsx():
    path = HERE / "gen-budget-variance.xlsx"
    model = xlsx_model()
    cached = build_xlsx(path, model)
    shown = {name: [[xlsx_display(v if not isinstance(v, Decimal) else v, f) for v, f, _ in row]
                    for row in sheet["rows"]] for name, sheet in model.items()}
    variance, head, centers = shown[SHEET1], shown["Staffing"], shown["Cost Centers"]
    checks = {
        # Locale-independent text cells and sheet names only; numbers, dates and booleans are checked by the tables.
        "must_contain": [XLSX_TITLE, XLSX_NOTE, XLSX_AFTER, HEADCOUNT_SOURCE, SHEET1, "Staffing", "Cost Centers",
                         "Actual (USD)", "Budget owner", "Truck maintenance", "Software subscriptions",
                         "Zoë Whitfield", "Customer Service", "Trade marketing (closed)", "Ravi Subramanian",
                         "Share of Q1 budget"],
        "ordered": [XLSX_TITLE, "Diesel fuel", XLSX_AFTER, HEADCOUNT_SOURCE, "Fleet and transportation",
                    "Information technology"],
        "headings": [],
        "tables": [{"name": "Q1 Variance (the two header rows 3-4 to the Total row 13; title and note rows 1-2 and "
                             "the note in row 15 not included; 'Actual (USD)' merged across four columns, six headers "
                             "merged down, four header texts with a line break)", "rows": variance},
                   {"name": "Staffing (all 7 rows; a month not yet reported and a missing date are empty cells)",
                    "rows": head},
                   {"name": "Cost Centers (all 7 rows)", "rows": centers}],
        "noise": [],
        "absent": [],
    }
    n_formula = len(cached)
    gt = write_ground_truth(
        path, fmt="xlsx", title="Operating budget vs actual, headcount and cost centers, Q1 FY2028", pages_or_sheets=3,
        stresses=["three visible worksheets (Q1 Variance, Staffing, Cost Centers)",
                  "merged title row A1:J1 and merged italic note row A2:J2 above a table that starts at row 3; an "
                  "italic note two rows below the table",
                  "two header rows: 'Actual (USD)' merged across four columns, six headers merged down over both rows; "
                  "four header texts contain a line break (Alt+Enter) and wrap",
                  f"{n_formula} formula cells saved with their computed (cached) values, as Excel saves them",
                  "thousands separators (#,##0), negatives shown in parentheses (#,##0;(#,##0)), one-decimal percents "
                  "including negative ones, zero amounts, dates as d-mmm-yyyy and mm/dd/yyyy, booleans TRUE/FALSE",
                  "empty cells inside a numeric table (a month not yet reported, a missing date)",
                  "codes stored as text with leading zeros (format @); frozen panes; autofilter on the Cost Centers "
                  "sheet; a non-ASCII name"],
        checks=checks,
        notes=("Expected cells are the text Excel shows in an en-US locale: amounts as '1,860,000' (#,##0), negative "
               "variances as '(55,125)' (#,##0;(#,##0)), percentages as '-5.8%' and '0.4%' (0.0%), dates as "
               "'18-Mar-2028' (d-mmm-yyyy) and '05/01/2014' (mm/dd/yyyy), booleans as 'TRUE'/'FALSE', cost-center "
               "codes as typed ('0410'); zero amounts as '0'. Separators, date order and boolean words follow the "
               "viewer's locale, so (as in the earlier sets) must_contain lists only text cells, notes and the three "
               "sheet names, and number and date display is measured by the tables. The Q1 Variance table starts at "
               "its first header row (row 3): 'Department', 'Cost line', 'Q1 budget (USD)', 'Variance (USD)', "
               "'Variance (% of budget)' and 'Budget owner' are merged down over rows 3-4 and 'Actual (USD)' across "
               "'January', 'February', 'March' and 'Q1 total'; four header texts hold a line break, written with "
               "'\\n' (normalization makes it a space); a merged cell's text is in its top-left position and the "
               "covered positions are empty strings (not scored). The Total row has its label in column A and no "
               "values in B and J. Formulas (" f"{n_formula} cells: G5 '=SUM(D5:F5)', H5 '=C5-G5', I5 '=H5/C5', C13 "
               "'=SUM(C5:C12)', Staffing B7 '=SUM(B2:B6)', ...) are saved with their computed values, so the "
               "expected cell is the value. Staffing (monthly headcount) leaves the Sales March figure and the Administration last-hire "
               "date empty (empty strings, not scored); its Total row sums the reported figures. The merged title and "
               "note rows and the notes below the Q1 Variance and Staffing tables are checked by must_contain and "
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
            == sorted(["A1:J1", "A2:J2", "A3:A4", "B3:B4", "C3:C4", "H3:H4", "I3:I4", "J3:J4", "D3:G3"]),
            "xlsx: merged ranges")
    require(sum(1 for ws in wb_f.worksheets for row in ws.iter_rows() for c in row if c.data_type == "f")
            == n_formula, "xlsx: formula count")
    require(g[6][1] == "Diesel fuel" and g[6][7] == "(55,125)" and g[6][8] == "-5.8%", "xlsx: negative variance")
    h = grids["Staffing"]
    require(h[-1][0] == HEADCOUNT_SOURCE and all(c == "" for c in h[-2]), "xlsx: headcount source note")
    require(grids["Cost Centers"][1][0] == "0410", "xlsx: leading zeros kept")
    tables_found = [g[2:2 + len(variance)], h[:len(head)], grids["Cost Centers"]]
    verify(path.name, "xlsx", gt, "\n".join(texts), tables_found=tables_found, fields=fields)
    return gt


# ===========================================================================
# 3. gen-sales-review.pptx
# ===========================================================================

REGIONS = [  # (region, Q4 2026 revenue, Q4 2027 revenue in USD thousands, gross margin 2027 in tenths of a percent)
    ("Northeast", 4812, 5236, 214),
    ("Southeast", 3945, 4102, 198),
    ("Midwest", 2618, 2540, 186),
    ("West", 3307, 3764, 229),
]


def pptx_table():
    rows = [["Region", "Revenue (USD thousands)", "", "Change", "Gross margin"],
            ["", "Q4 2026", "Q4 2027", "", ""]]

    def change(a, b):
        p = pct1(Decimal(b) / Decimal(a) - 1)
        return f"+{p}%" if p > 0 else f"{p}%"

    for name, a, b, gm in REGIONS:
        rows.append([name, f"{a:,}", f"{b:,}", change(a, b), f"{Decimal(gm) / 10}%"])
    ta, tb = sum(r[1] for r in REGIONS), sum(r[2] for r in REGIONS)
    margin = sum(Decimal(r[2]) * r[3] for r in REGIONS) / Decimal(tb) / 1000
    rows.append(["All regions", f"{ta:,}", f"{tb:,}", change(ta, tb), f"{pct1(margin)}%"])
    return rows


PPTX_TABLE = pptx_table()
PPTX_TABLE_MERGES = [(0, 0, 1, 0), (0, 1, 0, 2), (0, 3, 1, 3), (0, 4, 1, 4)]
TREND_BOX = ["Frozen seafood sales grew 15.2 percent on new restaurant accounts.",
             "Dairy sales were flat because milk prices fell during the quarter.",
             "Bakery sales fell 4.6 percent after a supplier recall in November."]
TREND_CALLOUT = "Fresh produce share of revenue: 31.7%"
PPTX_SLIDES = [
    {"layout": 0, "title": "Quarterly Sales Review", "subtitle": "Brightwater Provisions, fourth quarter 2027"},
    {"layout": 1, "title": "Agenda", "numbered": True,
     "bullets": [(0, "Results by region"), (0, "Top customer accounts"), (0, "Product line trends"),
                 (0, "Plan for the first quarter")]},
    {"layout": 5, "title": "Revenue by Region", "table": True,
     "notes": "The Midwest decline came from the loss of two school district contracts in October."},
    {"layout": 3, "title": "Top Customer Accounts",
     "left": [(0, "Harbor Point Grocers renewed its contract for three years"),
              (1, "Its volume commitment rises 12 percent in 2028"),
              (0, "Valle Verde Restaurants added four new locations")],
     "right": [(0, "Two hospital accounts moved to a competitor"),
               (0, "Credit terms were tightened for three accounts"),
               (1, "Days sales outstanding fell from 41 to 36")],
     "notes": "Both hospital accounts cited a group purchasing agreement that we could not match on price."},
    {"layout": 5, "title": "Product Line Trends", "trends": True},
    {"layout": 2, "title": "Looking Ahead", "body": "Targets and actions for the first quarter of 2028"},
    {"layout": 1, "title": "Plan for the First Quarter",
     "bullets": [(0, "Open the new Tampa cross-dock by February 15"),
                 (1, "Hire eight drivers and two dispatchers before opening"),
                 (0, "Launch online ordering for independent restaurants"),
                 (1, "Pilot with 40 customers in the Northeast region")],
     "notes": "The cross-dock lease was signed on December 3 and the racking is being installed this month."},
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
        if spec.get("trends"):
            box = slide.shapes.add_textbox(Inches(0.6), Inches(1.8), Inches(8.8), Inches(2.4))
            box.text_frame.word_wrap = True
            for i, text in enumerate(TREND_BOX):
                p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
                p.text = text
                p.runs[0].font.size = PPt(20)
            callout = slide.shapes.add_textbox(Inches(5.2), Inches(4.8), Inches(4.2), Inches(0.8))
            callout.text_frame.text = TREND_CALLOUT
            callout.text_frame.paragraphs[0].runs[0].font.size = PPt(22)
            callout.text_frame.paragraphs[0].runs[0].font.bold = True
        if "notes" in spec:
            slide.notes_slide.notes_text_frame.text = spec["notes"]
    props = prs.core_properties
    props.title = PPTX_SLIDES[0]["title"]
    props.author = "Sales Operations"
    props.last_modified_by = "Sales Operations"
    props.comments = ""
    props.revision = 5
    props.created = dt.datetime(2028, 1, 9, 14, 0, 0)
    props.modified = dt.datetime(2028, 1, 12, 10, 25, 0)
    prs.save(path)
    pin_ooxml(path, "2028-01-09T14:00:00Z", "2028-01-12T10:25:00Z")


def make_pptx():
    path = HERE / "gen-sales-review.pptx"
    build_pptx(path)
    paragraphs = ([PPTX_SLIDES[0]["subtitle"], PPTX_SLIDES[5]["body"]]
                  + [t for s in PPTX_SLIDES for key in ("bullets", "left", "right") for _, t in s.get(key, [])]
                  + TREND_BOX + [TREND_CALLOUT])
    notes = [s["notes"] for s in PPTX_SLIDES if "notes" in s]
    must = [p for p in paragraphs if len(p.split()) >= MIN_PHRASE_WORDS] + notes
    short = [p for p in paragraphs if len(p.split()) < MIN_PHRASE_WORDS]
    checks = {
        "must_contain": must,
        "ordered": ["Brightwater Provisions, fourth quarter 2027", "Results by region",
                    "Revenue (USD thousands)", "Credit terms were tightened for three accounts",
                    "Dairy sales were flat", TREND_CALLOUT,
                    "Launch online ordering for independent restaurants"],
        "headings": [s["title"] for s in PPTX_SLIDES],
        "tables": [{"name": "Slide 3: Revenue by Region (two header rows: 'Region', 'Change' and 'Gross margin' "
                             "merged down, 'Revenue (USD thousands)' merged across 'Q4 2026' and 'Q4 2027')",
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
                  "amounts with thousands separators, signed percentages",
                  "Two Content layout: two bulleted bodies with second-level items, left then right",
                  "Title Only slide with two free text boxes (not placeholders): a three-paragraph box and a bold "
                  "callout",
                  "two-level bullets; speaker notes on slides 3, 4 and 7"],
        checks=checks,
        notes=("Seven slides from python-pptx's default 4:3 template: 1 Title Slide, 2 and 7 Title and Content, 3 and "
               "5 Title Only, 4 Two Content, 6 Section Header. Slide 2's agenda is numbered by PowerPoint "
               "auto-numbering (1. 2. 3. 4. are drawn, not typed), so its items do not include the numbers. Slide 3's "
               "table has two header rows: 'Region', 'Change' and 'Gross margin' are merged down over both rows and "
               "'Revenue (USD thousands)' across 'Q4 2026' and 'Q4 2027'; a merged cell's text is in its top-left "
               "position and the covered positions are empty strings (not scored); amounts are text as typed "
               "('5,236'), changes carry a sign ('+8.8%', '-3.0%'). Slide 4 is read left body then right body, as in "
               "shape order and as placed. Slide 5 holds two text boxes, the three-paragraph box first and the "
               "callout below it on the right, in shape order and position. Speaker notes (slides 3, 4 and 7) are in "
               "must_contain (3 phrases), never ordered anchors. headings are the seven slide titles. must_contain "
               f"keeps every slide paragraph of at least {MIN_PHRASE_WORDS} words; the {len(short)} shorter ones "
               f"({'; '.join(short)}) are not phrases (the subtitle and the agenda item 'Results by region' are ordered anchors). No "
               "footers, slide numbers, dates, hidden slides, charts or comments: noise and absent are empty."))
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
    require(PPTX_TABLE[-1][1:4] == ["14,682", "15,642", "+6.5%"], f"pptx: total row {PPTX_TABLE[-1]}")
    verify(path.name, "pptx", gt, "\n".join(texts), body_text="\n".join(body), headings_found=titles,
           tables_found=tables)
    return gt


# ===========================================================================
# 4. gen-customer-invoices.csv
# ===========================================================================

CSV_HEADER = ["invoice_no", "invoice_date", "customer_name", "ship_to", "sales_rep", "net_amount", "tax_amount",
              "total_amount", "currency", "terms", "status", "notes"]
CSV_CUSTOMERS = [  # (customer, ship-to city)
    ("Harbor Point Grocers", "Tampa, FL"),
    ("Valle Verde Restaurants, LLC", "Orlando, FL"),
    ("Café Lumière", "Sarasota, FL"),
    ('The "Corner" Deli', "Lakeland, FL"),
    ("Søndergaard Foods", "Savannah, GA"),
    ("Mercado Doña Rosa", "Miami, FL"),
    ("St. Brendan School District", "Gainesville, FL"),
]
CSV_REPS = ["Aisha Bello", "Jonas Lindqvist", "Renée Dubois", "Kwame Asante"]
CSV_TERMS = ["Net 30", "Net 15", "Net 30", "Due on receipt"]
CSV_NOTES = [
    "",
    "Delivered in two drops\nSecond drop on Friday",
    "Price adjusted per contract 2027-114; see credit memo",
    'Customer asked for "no substitutions"',
    "",
    "Short-shipped 3 cases, backorder created",
    "Dock closes at 2 pm\nCall ahead",
    "",
    "Pallet deposit refunded",
]


def csv_rows():
    rows = []
    start = dt.date(2028, 1, 3)
    for i in range(30):
        customer, city = CSV_CUSTOMERS[(i * 5) % len(CSV_CUSTOMERS)]
        issued = start + dt.timedelta(days=(i * 3) + (i % 4))
        net = money(Decimal(850 + (i * 4637) % 23000) + Decimal((i * 53) % 100) / 100)
        tax = money(net * Decimal("0.07")) if customer != "St. Brendan School District" else Decimal("0.00")
        total = net + tax
        status = "paid" if i < 18 else ("credited" if i % 9 == 2 else ("overdue" if i % 5 == 1 else "open"))
        rows.append([f"INV-28-{2101 + i * 3}", issued.isoformat(), customer, city, CSV_REPS[(i * 3) % 4],
                     f"{net:,.2f}", f"{tax:,.2f}", f"{total:,.2f}", "USD", CSV_TERMS[i % 4], status,
                     CSV_NOTES[(i * 7) % len(CSV_NOTES)]])
    return rows


def make_csv():
    path = HERE / "gen-customer-invoices.csv"
    rows = csv_rows()
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    path.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))
    multi = [r for r in rows if "\n" in r[11]]
    big = [r[7] for r in rows if "," in r[7]]
    exempt = [r for r in rows if r[6] == "0.00"]
    checks = {
        "must_contain": ["net_amount", "total_amount", "Valle Verde Restaurants, LLC", 'The "Corner" Deli',
                         "Café Lumière", "Søndergaard Foods", "Mercado Doña Rosa", "Renée Dubois",
                         "Price adjusted per contract 2027-114; see credit memo", 'Customer asked for "no substitutions"',
                         "Short-shipped 3 cases, backorder created", rows[0][0], rows[14][0], rows[-1][0],
                         rows[0][1], rows[-1][1], big[0], big[-1]],
        "ordered": [rows[0][0], rows[7][0], rows[14][0], rows[21][0], rows[-1][0]],
        "headings": [],
        "tables": [{"name": "Invoices: header row and all 30 data rows", "rows": [CSV_HEADER] + rows}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="csv", title="Customer invoice export, January to March 2028", pages_or_sheets=None,
        stresses=["UTF-8 with a byte order mark (as Excel's 'CSV UTF-8' writes it), comma delimiter, minimal quoting "
                  "(only fields with a comma, quote or line break are quoted), CRLF record ends",
                  f"{len(multi)} notes fields (two different texts) with an embedded line feed inside quotes, so "
                  "those records span two physical lines",
                  "fields with commas, a semicolon and doubled double quotes (customer 'The \"Corner\" Deli', a note "
                  "with a quoted phrase)",
                  "amounts with thousands separators in quoted fields ('12,345.67'), zero tax amounts, empty notes",
                  "ISO dates YYYY-MM-DD, non-ASCII names (é, è, ø, ñ)"],
        checks=checks,
        notes=("RFC 4180 CSV as Excel writes it with 'CSV UTF-8': a UTF-8 byte order mark before the first header "
               "field, comma delimiter, a field is quoted only when it holds a comma, a double quote or a line break, "
               "CRLF between records, a bare LF inside the quoted multi-line notes. The expected first header cell is "
               "'invoice_no' without the byte order mark: score.mjs turns U+FEFF into whitespace, so an output that "
               "keeps the mark still matches. The seven customers repeat over the 30 invoices; "
               f"{len(multi)} notes fields (two different texts) contain a line break inside the quotes, so those "
               "records span two physical lines; the expected cell keeps the line break (normalization turns it into "
               "a space). Amounts with a comma thousands separator are quoted ('\"12,345.67\"'); the table rule "
               "compares them with the comma removed on both sides. The school district is tax exempt "
               f"({len(exempt)} invoices with tax '0.00'). Expected cell and phrase text is the parsed field value "
               "(quotes unescaped). The expected table is the whole file (header + 30 rows, 12 columns); empty fields "
               "are empty strings and are not scored. must_contain items are whole fields that never occur inside "
               "another field (invoice numbers and dates of rows 1, 15 and 30, the first and last total with a "
               "thousands separator, five customer names with a comma, quotes or non-ASCII letters, a sales "
               "representative, three notes with a semicolon, quotes or commas, two column names); no phrase is a "
               "multi-line field. ordered: the invoice numbers of rows 1, 8, 15, 22 and 30. A CSV has no headings, "
               "page furniture or hyphenation: headings, noise and absent are empty."))
    raw = path.read_bytes()
    require(raw.startswith(b"\xef\xbb\xbf") and raw.count(b"\r\n") == 31, "csv: BOM / CRLF records")
    text = raw.decode("utf-8-sig")
    parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=","))
    require(parsed[0] == CSV_HEADER and parsed[1:] == rows and len(parsed) == 31, "csv: read-back differs")
    require(all(len(r) == len(CSV_HEADER) for r in parsed), "csv: ragged rows")
    require(len(multi) >= 4 and len({r[11] for r in multi}) == 2 and len(big) >= 2 and exempt, "csv: features")
    require('"The ""Corner"" Deli"' in text and '"' + rows[0][0] not in text, "csv: quoting")
    verify(path.name, "csv", gt, "\n".join(" ".join(r) for r in parsed), tables_found=[parsed],
           fields=[c for r in parsed for c in r])
    return gt


# ===========================================================================
# 5. gen-product-catalog.json
# ===========================================================================

JSON_PRODUCTS = [
    {"sku": "FZ-SAL-0412", "name": "Atlantic salmon fillets, skin on", "category": "Frozen seafood",
     "pack": {"units": 10, "unit_size": "2 lb", "case_weight_lb": 21.5},
     "pricing": {"list": 189.9, "tiers": [{"min_cases": 10, "price": 182.4}, {"min_cases": 40, "price": 176.25}]},
     "storage": "frozen", "allergens": ["fish"], "origin": {"country": "Norway", "plant": "Ålesund"},
     "discontinued": False, "replaced_by": None},
    {"sku": "DY-MLK-1001", "name": "Whole milk, half gallon", "category": "Dairy",
     "pack": {"units": 9, "unit_size": "64 fl oz", "case_weight_lb": 40.2},
     "pricing": {"list": 27.15, "tiers": []}, "storage": "refrigerated", "allergens": ["milk"],
     "origin": {"country": "USA", "plant": "Plant City"}, "discontinued": False, "replaced_by": None,
     "shelf_life_days": 18},
    {"sku": "BK-BRD-0207", "name": "Brioche burger buns, 4 inch", "category": "Bakery",
     "pack": {"units": 72, "unit_size": "3 oz", "case_weight_lb": 14.0},
     "pricing": {"list": 38.6, "tiers": [{"min_cases": 25, "price": 36.9}]}, "storage": "frozen",
     "allergens": ["wheat", "milk", "egg"], "origin": {"country": "USA", "plant": "Atlanta"},
     "discontinued": True, "replaced_by": "BK-BRD-0219",
     "notes": 'Recall lot 27-311 closed; ships in 12" sleeves'},
    {"sku": "PR-AVO-0050", "name": "Hass avocados, size 48", "category": "Fresh produce",
     "pack": {"units": 48, "unit_size": "each", "case_weight_lb": 25.0},
     "pricing": {"list": 61.75, "tiers": [{"min_cases": 20, "price": 58.5}]}, "storage": "ambient until ripe",
     "allergens": [], "origin": {"country": "Mexico", "plant": "Uruapan, Michoacán"}, "discontinued": False,
     "replaced_by": None, "seasonal": True},
    {"sku": "DG-OIL-0330", "name": "Canola frying oil, jug", "category": "Dry grocery",
     "pack": {"units": 1, "unit_size": "35 lb", "case_weight_lb": 36.1},
     "pricing": {"list": 44.2, "tiers": [{"min_cases": 50, "price": 41.05}, {"min_cases": 200, "price": 39.8}]},
     "storage": "ambient", "allergens": [], "origin": {"country": "Canada", "plant": "Saskatoon"},
     "discontinued": False, "replaced_by": None},
    {"sku": "FZ-SHR-0921", "name": "White shrimp 16/20, peeled and deveined", "category": "Frozen seafood",
     "pack": {"units": 5, "unit_size": "2 lb", "case_weight_lb": 10.8},
     "pricing": {"list": 112.0, "tiers": [{"min_cases": 15, "price": 107.35}]}, "storage": "frozen",
     "allergens": ["shellfish"], "origin": {"country": "Ecuador", "plant": "Guayaquil"}, "discontinued": False,
     "replaced_by": None, "certifications": ["BAP 2-star", "ASC"]},
    {"sku": "DY-CHS-0415", "name": "Queso fresco, \"Doña Rosa\" brand", "category": "Dairy",
     "pack": {"units": 12, "unit_size": "10 oz", "case_weight_lb": 8.3},
     "pricing": {"list": 46.8, "tiers": []}, "storage": "refrigerated", "allergens": ["milk"],
     "origin": {"country": "USA", "plant": "Hialeah"}, "discontinued": False, "replaced_by": None,
     "shelf_life_days": 45},
    {"sku": "PR-LET-0120", "name": "Romaine hearts, 3 count", "category": "Fresh produce",
     "pack": {"units": 12, "unit_size": "3 ct bag", "case_weight_lb": 18.4},
     "pricing": {"list": 33.25, "tiers": [{"min_cases": 30, "price": 31.6}]}, "storage": "refrigerated",
     "allergens": [], "origin": {"country": "USA", "plant": "Salinas"}, "discontinued": False, "replaced_by": None,
     "seasonal": True},
]


def json_model():
    return {"catalog": {"supplier": COMPANY, "generated": "2028-02-01T06:30:00Z", "currency": "USD",
                        "product_count": len(JSON_PRODUCTS), "schema": "catalog export 2.1",
                        "price_list": "Foodservice 2028 Q1"},
            "products": JSON_PRODUCTS}


def make_json():
    path = HERE / "gen-product-catalog.json"
    obj = json_model()
    raw = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.write_text(raw, encoding="utf-8")
    checks = {
        "must_contain": ["case_weight_lb", "replaced_by", "FZ-SAL-0412", "PR-LET-0120",
                         "White shrimp 16/20, peeled and deveined", 'Queso fresco, "Doña Rosa" brand',
                         'Recall lot 27-311 closed; ships in 12" sleeves', "Uruapan, Michoacán", "Ålesund",
                         "ambient until ripe", "BAP 2-star", "2028-02-01T06:30:00Z", "Foodservice 2028 Q1",
                         "176.25", "107.35"],
        "ordered": ["FZ-SAL-0412", "Brioche burger buns, 4 inch", "PR-AVO-0050", "Queso fresco, \"Doña Rosa\" brand",
                    "PR-LET-0120"],
        "headings": [],
        "tables": [],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="json", title="Product catalog export (8 products), February 2028", pages_or_sheets=None,
        stresses=["pretty-printed JSON with 2-space indentation and a final newline",
                  "top-level object holding a metadata object and an array of 8 product objects",
                  "nested objects (pack, pricing, origin) and arrays of objects (pricing tiers), arrays of strings "
                  "(allergens, certifications)",
                  "null values, booleans, empty arrays (no tiers, no allergens)",
                  "objects whose keys differ from one record to the next (shelf_life_days, notes, seasonal, "
                  "certifications)",
                  "non-ASCII text kept as UTF-8 (Å, á, ñ), escaped double quotes inside strings, decimal and integer "
                  "numbers, a UTC timestamp"],
        checks=checks,
        notes=("UTF-8 JSON written by json.dumps(..., ensure_ascii=False, indent=2) plus a final newline: one key or "
               "value per line, key order as written, non-ASCII characters as-is. A converter may keep it as JSON, "
               "fence it as code, or render it as text, lists or tables; no Markdown structure is expected, so "
               "headings and tables are empty. must_contain items are whole keys or scalar values that never occur "
               "inside another key or value (numbers as JSON writes them: tier prices 176.25 and 107.35); the two "
               "strings with escaped quotes match their raw JSON form too, because matching deletes backslashes, and "
               "case_weight_lb and replaced_by match without underscores because matching deletes them. ordered "
               "follows document order: the SKUs of products 1, 4 and 8 and the names of products 3 and 7. The "
               "supplier and all products, plants and figures are fictitious."))
    text = path.read_text(encoding="utf-8")
    require(json.loads(text) == obj and text.endswith("}\n") and '\n  "products": [' in text, "json: read-back differs")
    require('\\"' in text and "Ålesund" in text and "Michoacán" in text, "json: escaping")
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
    require([] in [p["pricing"]["tiers"] for p in JSON_PRODUCTS] and [] in [p["allergens"] for p in JSON_PRODUCTS]
            and None in [p["replaced_by"] for p in JSON_PRODUCTS], "json: empty arrays / nulls")
    verify(path.name, "json", gt, text, fields=fields)
    return gt


# ===========================================================================
# 6. gen-ops-report.pdf (not read back with a text extractor; see the module doc)
# ===========================================================================

PDF_TITLE = "Distribution Center Operations Report"
PDF_SUBTITLE = "Lakeland distribution center, March 2028, prepared on April 6, 2028"
PDF_HEADER_LEFT = COMPANY
PDF_HEADER_RIGHT = "Monthly operations report OPS-2028-03"
PDF_FOOTER = "Internal use only: distribution and transportation managers"
PDF_KV = [
    ["Reporting period", "March 1 to March 31, 2028"],
    ["Site manager", "Keisha Odum"],
    ["Shifts", "Day, swing and night"],
    ["Overall status", "On target except night shift accuracy"],
]
PDF_SUMMARY = ["The Lakeland center shipped 41,862 orders in March, 2.6 percent more than planned.",
               "Pick accuracy was 99.6 percent on the day and swing shifts but fell to 99.1 percent at night.",
               "Two dock doors were closed for repairs for nine days, which delayed inbound receiving."]
PDF_SHIFTS = [  # (shift, planned orders, shipped orders, cases picked, accuracy in tenths of a percent)
    ("Day", 18500, 19214, 236480, 996),
    ("Swing", 14200, 14533, 171905, 996),
    ("Night", 8100, 8115, 92740, 991),
]
PDF_TABLE1_CAPTION = "Table 1. Orders, cases and pick accuracy by shift"
PDF_ISSUES = ["New pickers on the night shift made most of the picking errors in the frozen aisles.",
              "Dock doors 7 and 8 were out of service from March 11 to March 19.",
              "Inbound trailers waited an average of 74 minutes for a door during that period.",
              "Fuel surcharges rose for the third month in a row."]
PDF_ACTIONS_HEADER = ["No.", "Action", "Owner", "Due date"]
PDF_ACTIONS = [
    ["1", "Pair each new night shift picker with an experienced picker for the first two weeks and audit their "
          "orders daily.", "Night shift supervisor", "April 15, 2028"],
    ["2", "Replace the hydraulic levelers of dock doors 7 and 8 and add both doors to the quarterly inspection "
          "route.", "Facilities", "May 1, 2028"],
    ["3", "Book inbound appointments in 30 minute slots and publish the daily schedule to carriers by 6 am.",
     "Inbound coordinator", "April 10, 2028"],
    ["4", "Renegotiate the fuel surcharge table with the two largest carriers.", "Transportation manager",
     "April 30, 2028"],
    ["5", "Review the frozen aisle slotting so that the fastest items sit at waist height.", "Inventory control",
     "May 15, 2028"],
]
PDF_NOTES = ["Order counts exclude internal transfers between distribution centers.",
             "Accuracy is measured by audits of one order in every fifty.",
             "Cases are counted when they leave the pick zone."]
PDF_NOTE = ("The April report will add the new Tampa cross-dock; its first shipments are planned for the week of "
            "April 17.")


def pdf_shifts_table():
    rows = [["Shift", "Orders", "", "Cases picked", "Pick accuracy"], ["", "Planned", "Shipped", "", ""]]
    tp = ts = tc = 0
    weighted = 0
    for name, planned, shipped, cases, acc in PDF_SHIFTS:
        rows.append([name, f"{planned:,}", f"{shipped:,}", f"{cases:,}", f"{Decimal(acc) / 10}%"])
        tp, ts, tc = tp + planned, ts + shipped, tc + cases
        weighted += shipped * acc
    overall = pct1(Decimal(weighted) / Decimal(ts) / 1000)
    rows.append(["Total", f"{tp:,}", f"{ts:,}", f"{tc:,}", f"{overall}%"])
    require(ts == 41862 and pct1(Decimal(ts) / Decimal(tp) - 1) == Decimal("2.6"),
            "pdf: totals differ from the summary text")
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
    shifts = pdf_shifts_table()
    t1 = Table(shifts, colWidths=[1.6 * inch, 1.1 * inch, 1.1 * inch, 1.3 * inch, 1.3 * inch], hAlign="LEFT")
    t1.setStyle(TableStyle(grid + [
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (1, 0), (2, 0)), ("SPAN", (3, 0), (3, 1)), ("SPAN", (4, 0), (4, 1)),
        ("FONT", (0, 0), (-1, 1), "Helvetica-Bold", 9), ("FONT", (0, 2), (-1, -2), "Helvetica", 9),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#DDE3EA")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("ALIGN", (1, 2), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    actions = [PDF_ACTIONS_HEADER] + [[r[0], RLParagraph(xml_escape(r[1]), cell), RLParagraph(xml_escape(r[2]), cell),
                                       r[3]] for r in PDF_ACTIONS]
    t2 = Table(actions, colWidths=[0.5 * inch, 3.6 * inch, 1.3 * inch, 1.1 * inch], hAlign="LEFT", repeatRows=1)
    t2.setStyle(TableStyle(grid + [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                                   ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE3EA")),
                                   ("ALIGN", (0, 0), (0, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story = [para(PDF_TITLE, title), para(PDF_SUBTITLE, sub), kv, para("Summary", h2)]
    story += [para(s) for s in PDF_SUMMARY]
    story += [para("Throughput by Shift", h2), para(PDF_TABLE1_CAPTION, cap), t1, para("Issues", h2),
              ListFlowable([ListItem(para(t)) for t in PDF_ISSUES], bulletType="1", bulletFormat="%s.",
                           leftIndent=18),
              para("Open Actions", h2), t2, para("Notes", h2),
              ListFlowable([ListItem(para(t)) for t in PDF_NOTES], bulletType="bullet", start="•",
                           leftIndent=18),
              Spacer(1, 4), para(PDF_NOTE, note)]
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.9 * inch, bottomMargin=0.85 * inch, title=PDF_TITLE, author="Operations",
                            subject="Monthly distribution center operations", creator="Operations", invariant=1)
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return max(pages)


def make_pdf():
    path = HERE / "gen-ops-report.pdf"
    n = _pdf_build(path, 0)
    require(_pdf_build(path, n) == n, "pdf: page count changed between passes")
    require(n == 2, f"pdf: expected 2 pages, got {n}")
    shifts = pdf_shifts_table()
    actions = [PDF_ACTIONS_HEADER] + PDF_ACTIONS
    body_parts = ([PDF_TITLE, PDF_SUBTITLE] + [" ".join(r) for r in PDF_KV] + ["Summary"] + PDF_SUMMARY
                  + ["Throughput by Shift", PDF_TABLE1_CAPTION] + [" ".join(r) for r in shifts] + ["Issues"]
                  + PDF_ISSUES + ["Open Actions"] + [" ".join(r) for r in actions] + ["Notes"] + PDF_NOTES
                  + [PDF_NOTE])
    furniture_text = "\n".join(f"{PDF_HEADER_LEFT} {PDF_HEADER_RIGHT} {PDF_FOOTER} Page {k} of {n}"
                               for k in range(1, n + 1))
    checks = {
        "must_contain": ([PDF_SUBTITLE] + PDF_SUMMARY + [PDF_TABLE1_CAPTION] + PDF_ISSUES
                         + [PDF_ACTIONS[0][1], PDF_ACTIONS[1][1], PDF_ACTIONS[2][1], PDF_ACTIONS[4][1]]
                         + PDF_NOTES + ["The April report will add the new Tampa cross-dock;",
                                        "its first shipments are planned for the week of April 17."]),
        "ordered": [PDF_TITLE, "On target except night shift accuracy", "The Lakeland center shipped 41,862 orders",
                    "Cases picked", "Dock doors 7 and 8 were out of service",
                    "Renegotiate the fuel surcharge table", "Cases are counted when they leave the pick zone"],
        "headings": [PDF_TITLE, "Summary", "Throughput by Shift", "Issues", "Open Actions", "Notes"],
        "tables": [{"name": "Report details (key-value table without a header row)", "rows": PDF_KV},
                   {"name": "Table 1. Orders, cases and pick accuracy by shift (two header rows: 'Shift', 'Cases "
                            "picked' and 'Pick accuracy' span both rows, 'Orders' spans two columns; total row)",
                    "rows": shifts},
                   {"name": "Open actions (one table over two pages, header row repeated on page 2; complete: header "
                            "row and 5 rows; action and owner cells wrap over several lines)", "rows": actions}],
        "noise": [{"text": PDF_HEADER_LEFT, "max": 1}, {"text": PDF_HEADER_RIGHT, "max": 1},
                  {"text": PDF_FOOTER, "max": 1}],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pdf", title=PDF_TITLE, pages_or_sheets=n,
        stresses=["generated single-column PDF (ReportLab, standard Helvetica fonts, untagged)",
                  "title, a grey subtitle line and section headings set by font size and Helvetica-Bold only",
                  "key-value table without a header row, first column shaded and bold",
                  "table with two header rows: 'Shift', 'Cases picked' and 'Pick accuracy' span both rows, 'Orders' "
                  "spans two columns; counts with thousands separators, percentages, a bold total row",
                  "numbered list (1.-4.) and bulleted list drawn as list flowables",
                  "table whose action and owner cells wrap over two or three lines (Paragraph cells); it runs from "
                  "page 1 to page 2 with its header row repeated at the top of page 2",
                  "italic closing note; running header (left and right text with a rule) and footer ('Page N of 2') "
                  "on every page"],
        checks=checks,
        notes=("ReportLab 'invariant' mode pins the creation date and document ID, so the file is reproducible. The "
               "checks come from the generator's data in reading order; the file was NOT read back with any text "
               "extractor (blind protocol), only rendered to images with pdftoppm and looked at, and its font list "
               "was checked once with pdffonts (Helvetica, Helvetica-Bold and Helvetica-Oblique, base-14, not "
               "embedded; the local poppler render draws the bold and oblique faces in regular weight, but the PDF "
               "names them). Headings: the 19-point title and the five 13.5-point section "
               "headings, all set in Helvetica-Bold; the subtitle line is regular weight and is a phrase, not a "
               "heading. Tables: the report-details table has no header row (its first row is data); in Table 1 "
               "'Shift', 'Cases picked' and 'Pick accuracy' span both header rows and 'Orders' spans 'Planned' and "
               "'Shipped' (spanned positions are empty strings, not scored); counts are '19,214'-style text (compared "
               "without the comma) and accuracies one-decimal percentages ('99.6%'); the open-actions table's action "
               "and owner cells wrap inside the cell, and each expected cell is the whole text with single spaces; "
               "that table starts on page 1 (header row and rows 1-4) and continues on page 2 with its header row "
               "repeated (repeatRows=1) and row 5, so "
               "the expected table is the header row and all 5 rows once, and a repeated header row inside a "
               "converted table costs precision only. must_contain: the subtitle, every summary sentence, the table "
               "caption, every issue, four of the five actions, every note and both clauses of the closing note "
               "(table cells are otherwise checked by the tables). ordered: title, overall status, summary, a Table 1 "
               "header, an issue, an action, a note. Noise: the running header's two parts ('" + PDF_HEADER_LEFT +
               "', '" + PDF_HEADER_RIGHT + "') and the footer ('" + PDF_FOOTER + "') are printed once per page "
               "(twice) and occur nowhere in the body, max 1 each; 'Page N of 2' is not counted (it differs per "
               "page). No hyphenation (ReportLab does not hyphenate by default): absent is empty."))
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
        print(f"{gt['file']:28s} {gt['sha256']}  answer file passes the validation rules")
    print(f"libraries: {lib_versions()}")


if __name__ == "__main__":
    try:
        main()
    except CheckError as exc:
        print(f"CHECK FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
