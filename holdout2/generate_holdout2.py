#!/usr/bin/env python3
"""Generate the synthetic part of the SECOND held-out doc-to-markdown test set (holdout2/).

Writes six ordinary business documents to holdout2/ and one ground-truth JSON per document to
holdout2/ground-truth/<file>.json (same schema as corpus/ and holdout/, checked by score.mjs):

    gen-expense-policy.docx      Word policy: Title and Subtitle styles, auto-numbered Heading 1/2 (the numbers come
                                from Word numbering, not from the text), a key-value table without a header row, a
                                three-level numbered list (1. / a. / i.), a second numbered list that restarts at 1,
                                two-level bullets, a table whose header cells are merged across and down, a table with
                                row-group cells merged down in the body, a hyperlink, a soft line break, bold/italic
                                runs, page header and footer.
    gen-revenue-tracker.xlsx     Workbook with three sheets: monthly revenue with a two-row header (quarter groups
                                merged across, three headers merged down), negative currency, formulas saved with their
                                computed values, percent shares; a CRM pipeline list (US dates, currency with cents,
                                percent, booleans, account numbers stored as text with leading zeros, a formula
                                column, autofilter, frozen header); an assumptions sheet.
    gen-qbr-deck.pptx           Seven-slide quarterly review deck: title slide, section header slide, auto-numbered
                                list, native table, a process diagram made of grouped shapes plus a free text box, a
                                Comparison slide (two headings, two bodies), two-level bullets, speaker notes.
    gen-support-tickets.csv     Help-desk export: comma-delimited, every field quoted, LF line ends, UTF-8 without BOM,
                                fields with embedded line breaks, commas, doubled quotes, numbers with thousands
                                separators inside quotes, empty fields, ISO 8601 timestamps, non-ASCII names.
    gen-product-catalog.json    Product catalog API export: minified (one line, no spaces), top-level array, nested
                                objects and arrays (arrays of arrays, arrays of objects), nulls, booleans, empty
                                arrays and objects, timestamps with UTC offsets, non-ASCII text.
    gen-price-list.pdf          ReportLab price list: title, headings, numbered and bulleted lists, a 45-row table that
                                runs over two pages with its header row repeated on page 2, running header and
                                footer ('Page N of M') on every page.

The content is new (not reused from generate_corpus.py or holdout/generate_holdout.py). Everything is fixed in this
file: no randomness, no clock. Every ground-truth item is derived from the same Python data that is written into the
document. After writing, the DOCX, XLSX, PPTX, CSV and JSON files are read back (python-docx, openpyxl, python-pptx,
csv, json) and every check is verified against the read-back text, with the audit rules of holdout/ (no file name or
converter-added text in a check; prose phrases of at least 6 words that occur once; data-file items are whole,
distinctive fields; ordered anchors unique and in reading order). The PDF is NOT read back with any text extractor
(blind protocol): its checks are verified against the generator's own data in reading order, and its pages were only
rendered to images (pdftoppm) and looked at. Any mismatch aborts with exit status 1.

No converter (PackForAI, MarkItDown or other) is run here or was run while writing the answers.

Run from the benchmark folder (ephemeral environment, no global installs):

    uv run --with python-docx --with openpyxl --with python-pptx --with reportlab \
        python3 -I holdout2/generate_holdout2.py

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
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from openpyxl.styles import Alignment, Font
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.oxml.ns import qn as pqn
from pptx.util import Emu, Inches
from pptx.util import Pt as PPt
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph as RLParagraph, SimpleDocTemplate, Spacer, Table, \
    TableStyle

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground-truth"
ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)
LICENSE = ("Synthetic document written for the second held-out benchmark set and generated by "
           "holdout2/generate_holdout2.py; no third-party material. All organisations, people, addresses, phone "
           "numbers, e-mail domains and figures are fictitious.")
LIBS = ("python-docx", "openpyxl", "python-pptx", "lxml", "reportlab")
MIN_PHRASE_WORDS = 6
COMPANY = "Halden & Pryce Distribution, Inc."


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


def verify(name, fmt, gt, reading_text, *, body_text=None, headings_found=None, tables_found=None, fields=None,
           furniture=None):
    """Checks a ground truth against the text of the written file.

    reading_text: all text a reader sees, in reading order (body, then footnotes or speaker notes).
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
        "notes": notes + f" Generated by holdout2/generate_holdout2.py with {lib_versions()}; no converter was run "
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
# 1. gen-expense-policy.docx
# ===========================================================================

DOCX_TITLE = "Travel and Expense Policy"
DOCX_SUBTITLE = "Policy FIN-07, version 3.1, effective March 1, 2027"
DOCX_HEADER = COMPANY
DOCX_FOOTER = "FIN-07 Travel and Expense Policy, version 3.1"
LINK_URL = "https://intranet.haldenpryce.example/finance/travel"
DOCX_CONTROL = [
    ["Policy owner", "Finance Operations"],
    ["Approved by", "Chief Financial Officer"],
    ["Applies to", "All employees and contractors who travel on company business"],
    ["Next review", "February 2028"],
]
DOCX_T1 = [
    ["City tier", "Hotel cap per night", "", "Daily meal allowance"],
    ["", "Standard", "Peak season", ""],
    ["Tier 1: New York, San Francisco, Boston", "$325", "$410", "$95"],
    ["Tier 2: Chicago, Seattle, Denver", "$260", "$320", "$80"],
    ["Tier 3: all other U.S. cities", "$190", "$230", "$70"],
    ["International", "$280", "$350", "$90"],
]
DOCX_T1_MERGES = [(0, 0, 1, 0), (0, 1, 0, 2), (0, 3, 1, 3)]
DOCX_T2 = [
    ["Category", "Expense type", "Up to $500", "$501 to $5,000", "Over $5,000"],
    ["Travel", "Airfare", "Manager", "Director", "Vice President"],
    ["", "Lodging", "Manager", "Director", "Vice President"],
    ["", "Car rental", "Manager", "Manager", "Director"],
    ["Entertainment", "Client meals", "Director", "Vice President", "Chief Financial Officer"],
    ["", "Events", "Vice President", "Chief Financial Officer", "Chief Executive Officer"],
    ["Other", "Training and conferences", "Manager", "Director", "Vice President"],
]
DOCX_T2_MERGES = [(1, 0, 3, 0), (4, 0, 5, 0)]

# (kind, payload). Runs: (text, "" | "b" | "i"), ("@link", text) or ("@br",).
DOCX_BLOCKS = [
    ("title", DOCX_TITLE),
    ("subtitle", DOCX_SUBTITLE),
    ("table", "control"),
    ("h1", "Purpose and Scope"),
    ("para", [("This policy sets out how employees book business travel, which costs the company pays and how "
               "expenses are reported and approved.", "")]),
    ("para", [("It applies to travel paid with the company card and to expenses that employees pay personally and "
               "claim back.", "")]),
    ("h1", "Booking Travel"),
    ("para", [("All flights, hotels and rental cars must be booked through the corporate travel portal unless the "
               "travel desk confirms in writing that the portal cannot be used.", "")]),
    ("h2", "Air Travel"),
    ("number", (0, "Book economy class for flights shorter than six hours.")),
    ("number", (1, "Premium economy may be booked for flights of six hours or more.")),
    ("number", (1, "Business class requires prior approval by a vice president.")),
    ("number", (2, "Attach the written approval to the booking request.")),
    ("number", (0, "Book at least 14 days before departure whenever possible.")),
    ("number", (0, "Choose the lowest logical fare within two hours of the preferred departure time.")),
    ("h2", "Hotels and Meals"),
    ("para", [("Hotel rates may not exceed the nightly cap for the city tier shown in Table 1.", "")]),
    ("caption", "Table 1. Hotel caps and meal allowances by city tier (USD)"),
    ("table", 1),
    ("para", [("Peak season caps apply during the trade show weeks listed on the travel portal.", "")]),
    ("h2", "Ground Transportation"),
    ("bullet", (0, "Use public transport or a shared shuttle when it is practical.")),
    ("bullet", (0, "Rental cars must be intermediate size or smaller.")),
    ("bullet", (1, "Decline the optional collision damage waiver in the United States.")),
    ("bullet", (1, "Return the car with a full tank to avoid refueling charges.")),
    ("bullet", (0, "Mileage for personal vehicles is reimbursed at the published IRS rate.")),
    ("h1", "Expense Reporting"),
    ("para", [("Submit each expense report within ", ""), ("30 days", "b"), (" of returning from the trip. Receipts "
               "are required for every item over ", ""), ("$25", "i"), (".", "")]),
    ("number2", (0, "Photograph each receipt in the expense app on the day you receive it.")),
    ("number2", (0, "Assign every line to a project code or cost center.")),
    ("number2", (0, "Submit the report to your manager for the first approval.")),
    ("h2", "Approval Limits"),
    ("caption", "Table 2. Approval limits by expense type"),
    ("table", 2),
    ("h1", "Non-Reimbursable Expenses"),
    ("bullet", (0, "Upgrades to airline seats, hotel rooms or rental cars paid for personal comfort.")),
    ("bullet", (0, "Traffic fines, parking tickets and towing charges.")),
    ("bullet", (0, "Minibar items, in-room movies and spa services.")),
    ("bullet", (0, "Travel costs of family members or guests who join the trip.")),
    ("h1", "Questions"),
    ("para", [("Questions about this policy should be sent to Finance Operations at travel@haldenpryce.example. ", ""),
              ("The current version is always available on the ", ""), ("@link", "finance intranet page"), (".", "")]),
    ("para", [("Travel desk hours: Monday to Friday, 7:00 a.m. to 7:00 p.m. Central Time", ""), ("@br",),
              ("After-hours emergency line: +1 312 555 0147", "")]),
]

DOCX_MUST = [
    DOCX_SUBTITLE,
    "This policy sets out how employees book business travel, which costs the company pays",
    "It applies to travel paid with the company card and to expenses that employees pay personally and claim back.",
    "All flights, hotels and rental cars must be booked through the corporate travel portal",
    "Book economy class for flights shorter than six hours.",
    "Premium economy may be booked for flights of six hours or more.",
    "Business class requires prior approval by a vice president.",
    "Attach the written approval to the booking request.",
    "Book at least 14 days before departure whenever possible.",
    "Choose the lowest logical fare within two hours of the preferred departure time.",
    "Hotel rates may not exceed the nightly cap for the city tier shown in Table 1.",
    "Table 1. Hotel caps and meal allowances by city tier (USD)",
    "Peak season caps apply during the trade show weeks listed on the travel portal.",
    "Use public transport or a shared shuttle when it is practical.",
    "Rental cars must be intermediate size or smaller.",
    "Decline the optional collision damage waiver in the United States.",
    "Return the car with a full tank to avoid refueling charges.",
    "Mileage for personal vehicles is reimbursed at the published IRS rate.",
    "Submit each expense report within 30 days of returning from the trip.",
    "Receipts are required for every item over $25.",
    "Photograph each receipt in the expense app on the day you receive it.",
    "Assign every line to a project code or cost center.",
    "Submit the report to your manager for the first approval.",
    "Table 2. Approval limits by expense type",
    "Upgrades to airline seats, hotel rooms or rental cars paid for personal comfort.",
    "Traffic fines, parking tickets and towing charges.",
    "Minibar items, in-room movies and spa services.",
    "Travel costs of family members or guests who join the trip.",
    "Questions about this policy should be sent to Finance Operations at travel@haldenpryce.example.",
    "Travel desk hours: Monday to Friday, 7:00 a.m. to 7:00 p.m. Central Time",
    "After-hours emergency line: +1 312 555 0147",
]
DOCX_ORDERED = [
    DOCX_TITLE,
    "This policy sets out how employees book business travel",
    "Book economy class for flights shorter than six hours",
    "Hotel cap per night",
    "Submit each expense report within 30 days",
    "Traffic fines, parking tickets and towing charges",
    "Questions about this policy should be sent to Finance Operations",
]

HEADING_NUM_ID, BULLET_NUM_ID, NUMBER_NUM_ID, NUMBER2_NUM_ID = 40, 41, 42, 43


def _docx_numbering(document):
    """Heading numbering (1. / 1.1), a two-level bullet list, a 1./a./i. list and a restarted second list."""
    numbering = document.part.numbering_part.element
    lvl = ('<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text}"/>'
           '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{left}" w:hanging="{hang}"/></w:pPr>{rpr}</w:lvl>')
    sym = '<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr>'
    cour = '<w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:hint="default"/></w:rPr>'
    abstracts = [
        (HEADING_NUM_ID, "multilevel",
         lvl.format(i=0, fmt="decimal", text="%1.", left=432, hang=432, rpr="")
         + lvl.format(i=1, fmt="decimal", text="%1.%2", left=576, hang=576, rpr="")),
        (BULLET_NUM_ID, "hybridMultilevel",
         lvl.format(i=0, fmt="bullet", text="", left=720, hang=360, rpr=sym)
         + lvl.format(i=1, fmt="bullet", text="o", left=1440, hang=360, rpr=cour)),
        (NUMBER_NUM_ID, "hybridMultilevel",
         lvl.format(i=0, fmt="decimal", text="%1.", left=720, hang=360, rpr="")
         + lvl.format(i=1, fmt="lowerLetter", text="%2.", left=1440, hang=360, rpr="")
         + lvl.format(i=2, fmt="lowerRoman", text="%3.", left=2160, hang=180, rpr="")),
    ]
    first_num = numbering.find(qn("w:num"))
    for aid, kind, levels in abstracts:
        first_num.addprevious(parse_xml(
            f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{aid}"><w:multiLevelType w:val="{kind}"/>{levels}'
            '</w:abstractNum>'))
    for num_id in (HEADING_NUM_ID, BULLET_NUM_ID, NUMBER_NUM_ID):
        numbering.append(parse_xml(
            f'<w:num {nsdecls("w")} w:numId="{num_id}"><w:abstractNumId w:val="{num_id}"/></w:num>'))
    # A second instance of the decimal list that restarts at 1, as Word writes "Restart at 1".
    numbering.append(parse_xml(
        f'<w:num {nsdecls("w")} w:numId="{NUMBER2_NUM_ID}"><w:abstractNumId w:val="{NUMBER_NUM_ID}"/>'
        '<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'))


def _set_num(p, num_id, level):
    num_pr = p._p.get_or_add_pPr().get_or_add_numPr()
    num_pr.get_or_add_ilvl().val = level
    num_pr.get_or_add_numId().val = num_id


def _docx_link(document, p, text):
    r_id = document.part.relate_to(LINK_URL, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    link.append(parse_xml(f'<w:r {nsdecls("w")}><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr>'
                          f'<w:t xml:space="preserve">{text}</w:t></w:r>'))
    p._p.append(link)


def _docx_table(document, grid, merges, header_rows, bold_first_col=False, align_right_from=None):
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
            cell.text = value
            para = cell.paragraphs[0]
            if ri < header_rows:
                for run in para.runs:
                    run.bold = True
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif bold_first_col and ci == 0:
                for run in para.runs:
                    run.bold = True
            elif align_right_from is not None and ci >= align_right_from:
                para.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def build_docx(path: Path):
    document = docx.Document()
    for needed in ("Title", "Subtitle", "Heading 1", "Heading 2", "List Paragraph", "Table Grid", "Caption"):
        require(needed in {s.name for s in document.styles}, f"docx: template lacks style {needed!r}")
    _docx_numbering(document)
    section = document.sections[0]
    section.header.paragraphs[0].text = DOCX_HEADER
    section.footer.paragraphs[0].text = DOCX_FOOTER
    for kind, payload in DOCX_BLOCKS:
        if kind == "title":
            document.add_paragraph(payload, style="Title")
        elif kind == "subtitle":
            document.add_paragraph(payload, style="Subtitle")
        elif kind in ("h1", "h2"):
            p = document.add_heading(payload, level=1 if kind == "h1" else 2)
            _set_num(p, HEADING_NUM_ID, 0 if kind == "h1" else 1)
        elif kind == "caption":
            document.add_paragraph(payload, style="Caption")
        elif kind == "para":
            p = document.add_paragraph()
            for item in payload:
                if item[0] == "@link":
                    _docx_link(document, p, item[1])
                elif item[0] == "@br":
                    p.add_run().add_break()
                else:
                    run = p.add_run(item[0])
                    run.bold = item[1] == "b" or None
                    run.italic = item[1] == "i" or None
        elif kind in ("bullet", "number", "number2"):
            level, text = payload
            p = document.add_paragraph(text, style="List Paragraph")
            _set_num(p, {"bullet": BULLET_NUM_ID, "number": NUMBER_NUM_ID, "number2": NUMBER2_NUM_ID}[kind], level)
        elif kind == "table":
            if payload == "control":
                _docx_table(document, DOCX_CONTROL, [], 0, bold_first_col=True)
            elif payload == 1:
                _docx_table(document, DOCX_T1, DOCX_T1_MERGES, 2, align_right_from=1)
            else:
                _docx_table(document, DOCX_T2, DOCX_T2_MERGES, 1)
        else:
            raise ValueError(kind)
    for para in document.paragraphs:
        if para.style.name == "Normal":
            para.paragraph_format.space_after = Pt(6)
    props = document.core_properties
    props.title = DOCX_TITLE
    props.subject = "Travel and expense policy"
    props.author = "Finance Operations"
    props.last_modified_by = "Finance Operations"
    props.comments = ""
    props.keywords = ""
    props.category = ""
    props.revision = 7
    props.created = dt.datetime(2026, 11, 2, 9, 30, 0)
    props.modified = dt.datetime(2026, 12, 15, 16, 5, 0)
    document.save(path)
    pin_ooxml(path, "2026-11-02T09:30:00Z", "2026-12-15T16:05:00Z")


def _para_text(p_el):
    """Paragraph text with soft line breaks as '\\n' (hyperlink runs included)."""
    out = []
    for el in p_el.iter(qn("w:t"), qn("w:br"), qn("w:tab")):
        if el.tag == qn("w:t"):
            out.append(el.text or "")
        else:
            out.append("\n" if el.tag == qn("w:br") else "\t")
    return "".join(out)


def read_docx(path: Path):
    document = docx.Document(path)
    texts, headings, tables, items, heading_nums = [], [], [], [], []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, document)
            text = _para_text(child)
            texts.append(text)
            num_pr = child.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
            num = None if num_pr is None else (int(num_pr.find(qn("w:numId")).get(qn("w:val"))),
                                               int(num_pr.find(qn("w:ilvl")).get(qn("w:val"))))
            if p.style.name.startswith("Heading"):
                headings.append(text)
                heading_nums.append(num)
            elif num is not None:
                items.append(num + (text,))
        elif child.tag == qn("w:tbl"):
            grid = []
            for tr in child.iter(qn("w:tr")):
                row = []
                for tc in tr.iter(qn("w:tc")):
                    pr = tc.find(qn("w:tcPr"))
                    span = pr.find(qn("w:gridSpan")) if pr is not None else None
                    vmerge = pr.find(qn("w:vMerge")) if pr is not None else None
                    text = "\n".join(_para_text(p) for p in tc.iter(qn("w:p")))
                    if vmerge is not None and vmerge.get(qn("w:val")) != "restart":
                        text = ""  # continuation of a vertically merged cell
                    n = int(span.get(qn("w:val"))) if span is not None else 1
                    row += [text] + [""] * (n - 1)
                grid.append(row)
            tables.append(grid)
            texts += [" ".join(row) for row in grid]
    header = document.sections[0].header.paragraphs[0].text
    footer = document.sections[0].footer.paragraphs[0].text
    return "\n".join(texts), headings, heading_nums, tables, items, header, footer


def make_docx():
    path = HERE / "gen-expense-policy.docx"
    build_docx(path)
    headings = [p for k, p in DOCX_BLOCKS if k in ("h1", "h2")]
    checks = {
        "must_contain": DOCX_MUST,
        "ordered": DOCX_ORDERED,
        "headings": headings,
        "tables": [
            {"name": "Document control (key-value table without a header row)", "rows": DOCX_CONTROL},
            {"name": "Table 1. Hotel caps and meal allowances by city tier (two header rows; 'City tier' and 'Daily "
                     "meal allowance' merged down, 'Hotel cap per night' merged across)", "rows": DOCX_T1},
            {"name": "Table 2. Approval limits by expense type ('Travel' merged down over three body rows, "
                     "'Entertainment' over two)", "rows": DOCX_T2},
        ],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="docx", title=DOCX_TITLE, pages_or_sheets=None,
        stresses=["Title and Subtitle styles above the first heading",
                  "Heading 1 / Heading 2 numbered automatically by a multilevel list (1., 1.1): the numbers are not "
                  "in the heading text",
                  "key-value table without a header row, first column bold",
                  "three-level numbered list 1. / a. / i. (decimal, lowerLetter, lowerRoman)",
                  "second numbered list that restarts at 1 (a new w:num with startOverride)",
                  "two-level bulleted list",
                  "table with two header rows: two header cells merged down (vMerge), one merged across (gridSpan 2)",
                  "table with row-group label cells merged down over body rows",
                  "currency amounts in table cells, bold and italic runs inside a sentence",
                  "external hyperlink, an e-mail address, a soft line break (w:br) inside a paragraph",
                  "page header and footer text"],
        checks=checks,
        notes=("The headings are Word Heading 1/2 paragraphs numbered by a multilevel list attached to each heading "
               "(Word shows '1. Purpose and Scope', '2.1 Air Travel'); the numbers are list numbering, not text, so "
               "the expected headings are the heading texts and match with or without the numbers. The document title "
               "uses the Title style and the policy line the Subtitle style; as in holdout/ the title is the first "
               "ordered anchor and not a heading. Tables: the document-control table has no header row (its first "
               "row is data); in Table 1 'City tier' and 'Daily meal allowance' are merged down over both header rows "
               "and 'Hotel cap per night' across 'Standard' and 'Peak season'; in Table 2 the Category cells 'Travel' "
               "(3 rows) and 'Entertainment' (2 rows) are merged down in the body. A merged cell's text is in its "
               "top-left grid position and the positions it also covers are empty strings (not scored), as in the "
               "corpus. Lists: the Air Travel list has levels 0-2 (1. / a. / i.); the Expense Reporting list is a "
               "second instance of the same numbering that restarts at 1. must_contain keeps every paragraph, "
               "list item and caption of at least 6 words (long paragraphs as their first sentence or clause), "
               "never crossing the soft line break in the last paragraph: its two lines are two phrases. The "
               "bold '30 days' and italic '$25' fall inside phrases; normalization "
               "deletes '*' and '_'. The hyperlink text 'finance intranet page' is not part of any phrase. Page "
               "header ('Halden & Pryce Distribution, Inc.') and footer ('FIN-07 Travel and Expense Policy, version "
               "3.1') are stored once each and are not checked; including or dropping them are both faithful. No "
               "footnotes, comments, tracked changes or hyphenation: noise and absent are empty."))
    text, found_headings, heading_nums, tables, items, header, footer = read_docx(path)
    require(header == DOCX_HEADER and footer == DOCX_FOOTER, "docx: header/footer")
    require(heading_nums == [(HEADING_NUM_ID, 0 if k == "h1" else 1) for k, _ in DOCX_BLOCKS if k in ("h1", "h2")],
            "docx: heading numbering")
    num_of = {"bullet": BULLET_NUM_ID, "number": NUMBER_NUM_ID, "number2": NUMBER2_NUM_ID}
    require(items == [(num_of[k], lvl, t) for k, p in DOCX_BLOCKS if k in num_of for lvl, t in [p]],
            "docx: list items/levels read back differ")
    require("finance intranet page" in text and "Central Time\nAfter-hours" in text, "docx: link / soft break")
    verify(path.name, "docx", gt, text, headings_found=found_headings,
           tables_found=tables)
    for s in (DOCX_HEADER, DOCX_FOOTER):
        require(normalize(s) not in normalize(text), f"docx: furniture {s!r} also in the body")
    return gt


# ===========================================================================
# 2. gen-revenue-tracker.xlsx
# ===========================================================================

XLSX_TITLE = f"{COMPANY} - Revenue by Product Line, H1 2026 (USD)"
XLSX_NOTE = "Credits for returned goods are shown as negative revenue. Shares are of the H1 total."
FMT_USD0 = '"$"#,##0;-"$"#,##0'
FMT_USD2 = '"$"#,##0.00'
FMT_PCT1 = "0.0%"
FMT_PCT0 = "0%"
FMT_DATE = "m/d/yyyy"
FMT_INT = "0"
FMT_TEXT = "@"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
REVENUE = [
    ("Food Service Disposables", [412350, 398720, 431905, 425610, 447280, 452930]),
    ("Janitorial and Sanitation", [286400, 279150, 301220, 295870, 308440, 312075]),
    ("Medical and Dental Supplies", [518230, 504610, 536790, 541380, 559020, 566415]),
    ("Packaging and Shipping", [198760, 187340, 205610, 211980, 219470, 224105]),
    ("Office and Breakroom", [94215, 90880, 97340, 95120, 99860, 101245]),
    ("Returns and Credits", [-8450, -7920, -9135, -8710, -9480, -10025]),
]
HEADER_TOP = 3  # rows 3-4 hold the two header rows; row 1 title, row 2 note
STAGE_PROB = {"Prospecting": Decimal("0.10"), "Qualification": Decimal("0.25"), "Proposal": Decimal("0.50"),
              "Negotiation": Decimal("0.75"), "Closed Won": Decimal("1"), "Closed Lost": Decimal("0")}
PIPELINE = [  # (opportunity, account, account no, stage, close date, amount, owner)
    ("OPP-2611", "Lakeshore Medical Group", "004127", "Negotiation", (2026, 10, 30), 186400, "Dana Whitfield"),
    ("OPP-2614", "Pinecrest School District", "011583", "Proposal", (2026, 11, 13), 92750, "Marcus Ortega"),
    ("OPP-2620", "Copper Valley Hotels", "002961", "Closed Won", (2026, 9, 30), 48250, "Priya Raman"),
    ("OPP-2623", "Bayview Senior Living", "007404", "Qualification", (2026, 12, 18), 134000, "Dana Whitfield"),
    ("OPP-2627", "Redstone Dental Partners", "015220", "Prospecting", (2026, 12, 11), 27300, "Marcus Ortega"),
    ("OPP-2631", "Harbor Point Marina Cafe", "009818", "Closed Lost", (2026, 10, 9), 15600, "Priya Raman"),
    ("OPP-2635", "Summit Ridge Orthopedics", "003375", "Proposal", (2026, 11, 20), 71400, "Dana Whitfield"),
    ("OPP-2638", "Greenfield Food Bank", "012046", "Negotiation", (2026, 11, 6), 39800, "Lena Kowalski"),
    ("OPP-2642", "Northgate Animal Hospital", "006689", "Qualification", (2027, 1, 15), 22900, "Lena Kowalski"),
    ("OPP-2645", "Silver Creek Casino Resort", "001752", "Closed Won", (2026, 10, 2), 254000, "Marcus Ortega"),
    ("OPP-2649", "Westbrook Charter Academy", "014311", "Prospecting", (2027, 1, 29), 18650, "Priya Raman"),
    ("OPP-2652", "Mesa Verde Urgent Care", "008907", "Proposal", (2026, 12, 4), 56300, "Lena Kowalski"),
    ("OPP-2656", "Riverside Catering Co.", "010254", "Closed Lost", (2026, 9, 25), 33900, "Dana Whitfield"),
    ("OPP-2660", "Juniper Hills Golf Club", "005538", "Negotiation", (2026, 11, 24), 44200, "Marcus Ortega"),
]
PIPELINE_HEADER = ["Opportunity ID", "Account", "Account No", "Stage", "Close Date", "Amount", "Probability",
                   "Weighted", "Owner", "Won"]
ASSUMPTIONS = [  # (parameter, value, format, note)
    ("Snapshot date", dt.datetime(2026, 10, 15), FMT_DATE, "Taken from the CRM at 6:00 a.m. Pacific Time"),
    ("Win rate (trailing 12 months)", 0.31, FMT_PCT0, "Closed won divided by all closed opportunities"),
    ("Average deal size", 38500, FMT_USD0, "Closed won deals in the last four quarters"),
    ("Sales cycle (days)", 74, FMT_INT, "Median days from creation to close"),
    ("Discount allowance", -0.05, FMT_PCT0, "Largest discount without director approval"),
    ("Currency", "USD", "General", "All amounts in U.S. dollars"),
    ("Prepared by", "Revenue Operations", "General", None),
]


def xlsx_display(value, fmt) -> str:
    """Cell text as Excel (en-US) shows it, for the number formats used here."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if fmt == FMT_DATE:
        return f"{value.month}/{value.day}/{value.year}"
    d = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if fmt == FMT_USD0:
        require(d == d.to_integral_value(), "xlsx: non-integer in a whole-dollar cell")
        return f"-${-d:,.0f}" if d < 0 else f"${d:,.0f}"
    if fmt == FMT_USD2:
        return f"${money(d):,.2f}"
    if fmt == FMT_PCT1:
        return f"{pct1(d)}%"
    if fmt == FMT_PCT0:
        scaled = d * 100
        require(scaled == scaled.to_integral_value(), "xlsx: whole-percent cell is not a whole percent")
        return f"{int(scaled)}%"
    if fmt in (FMT_INT, "General"):
        require(d == d.to_integral_value(), "xlsx: integer cell")
        return str(int(d))
    raise ValueError(f"unexpected cell {value!r} with format {fmt!r}")


def xlsx_model():
    """{sheet: {"rows": [[(value, format, formula)]], "first": first row}} with formula values precomputed."""
    top = HEADER_TOP
    first_body = top + 2
    last_body = first_body + len(REVENUE) - 1
    total_row = last_body + 1
    h_total = sum(sum(v) for _, v in REVENUE)
    monthly = [
        [("Product line", "General", None), ("Q1 2026", "General", None), (None, None, None), (None, None, None),
         ("Q2 2026", "General", None), (None, None, None), (None, None, None), ("H1 total", "General", None),
         ("Share of H1", "General", None)],
        [(None, None, None)] + [(m, "General", None) for m in MONTHS] + [(None, None, None), (None, None, None)],
    ]
    for k, (line, vals) in enumerate(REVENUE):
        r = first_body + k
        monthly.append([(line, "General", None)] + [(v, FMT_USD0, None) for v in vals]
                       + [(sum(vals), FMT_USD0, f"SUM(B{r}:G{r})"),
                          (sum(vals) / h_total, FMT_PCT1, f"H{r}/H${total_row}")])
    col_totals = [sum(v[i] for _, v in REVENUE) for i in range(6)]
    monthly.append([("Total", "General", None)]
                   + [(t, FMT_USD0, f"SUM({c}{first_body}:{c}{last_body})") for t, c in zip(col_totals, "BCDEFG")]
                   + [(h_total, FMT_USD0, f"SUM(H{first_body}:H{last_body})"),
                      (1.0, FMT_PCT1, f"H{total_row}/H${total_row}")])
    pipeline = [[(h, "General", None) for h in PIPELINE_HEADER]]
    for k, (opp, acct, acct_no, stage, close, amount, owner) in enumerate(PIPELINE):
        r = 2 + k
        prob = STAGE_PROB[stage]
        weighted = Decimal(amount) * prob
        require(weighted == money(weighted), "xlsx: weighted amount has more than 2 decimals")
        pipeline.append([(opp, "General", None), (acct, "General", None), (acct_no, FMT_TEXT, None),
                         (stage, "General", None), (dt.datetime(*close), FMT_DATE, None),
                         (amount, FMT_USD2, None), (float(prob), FMT_PCT0, None),
                         (float(weighted), FMT_USD2, f"F{r}*G{r}"), (owner, "General", None),
                         (stage == "Closed Won", "General", None)])
    assumptions = [[("Parameter", "General", None), ("Value", "General", None), ("Notes", "General", None)]]
    for name, value, fmt, note in ASSUMPTIONS:
        assumptions.append([(name, "General", None), (value, fmt, None), (note, "General", None)])
    return {"Monthly Revenue": {"rows": monthly, "first": top}, "Pipeline": {"rows": pipeline, "first": 1},
            "Assumptions": {"rows": assumptions, "first": 1}}


def build_xlsx(path: Path, model):
    wb = openpyxl.Workbook()
    cached = {}
    for index, (name, sheet) in enumerate(model.items()):
        ws = wb.active if index == 0 else wb.create_sheet(name)
        ws.title = name
        xml_name = f"xl/worksheets/sheet{index + 1}.xml"
        first, rows = sheet["first"], sheet["rows"]
        if name == "Monthly Revenue":
            ws.cell(row=1, column=1, value=XLSX_TITLE).font = Font(bold=True, size=13)
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)
            ws["A1"].alignment = Alignment(horizontal="center")
            ws.cell(row=2, column=1, value=XLSX_NOTE).font = Font(italic=True, size=9)
            for c0, c1 in ((1, 1), (8, 8), (9, 9)):
                ws.merge_cells(start_row=HEADER_TOP, start_column=c0, end_row=HEADER_TOP + 1, end_column=c1)
            for c0, c1 in ((2, 4), (5, 7)):
                ws.merge_cells(start_row=HEADER_TOP, start_column=c0, end_row=HEADER_TOP, end_column=c1)
        for r, row in enumerate(rows, start=first):
            for c, (value, fmt, formula) in enumerate(row, start=1):
                if value is None:
                    continue
                cell = ws.cell(row=r, column=c, value=f"={formula}" if formula else value)
                cell.number_format = fmt
                if formula:
                    cached[(xml_name, cell.coordinate)] = value
                header_rows = 2 if name == "Monthly Revenue" else 1
                if r < first + header_rows or row[0][0] == "Total":
                    cell.font = Font(bold=True)
                if r < first + header_rows:
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        widths = {"Monthly Revenue": (28, 12, 12, 12, 12, 12, 12, 13, 11),
                  "Pipeline": (14, 26, 11, 13, 12, 13, 11, 13, 16, 7),
                  "Assumptions": (30, 14, 46)}[name]
        for col, width in zip("ABCDEFGHIJ", widths):
            ws.column_dimensions[col].width = width
        if name == "Pipeline":
            ws.auto_filter.ref = f"A1:J{len(rows)}"
            ws.freeze_panes = "A2"
    wb.properties.title = "Revenue and pipeline H1 2026"
    wb.properties.creator = "Revenue Operations"
    wb.properties.lastModifiedBy = "Revenue Operations"
    wb.properties.created = dt.datetime(2026, 10, 15, 7, 45, 0)
    wb.properties.modified = dt.datetime(2026, 10, 15, 7, 45, 0)
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

    pin_ooxml(path, "2026-10-15T07:45:00Z", "2026-10-15T07:45:00Z", patch=patch)
    return cached


def make_xlsx():
    path = HERE / "gen-revenue-tracker.xlsx"
    model = xlsx_model()
    cached = build_xlsx(path, model)
    shown = {name: [[xlsx_display(v, f) for v, f, _ in row] for row in sheet["rows"]] for name, sheet in model.items()}
    monthly, pipe, assumptions = shown["Monthly Revenue"], shown["Pipeline"], shown["Assumptions"]
    checks = {
        # Locale-independent text cells and sheet names only; numbers, dates and booleans are checked by the tables.
        "must_contain": [XLSX_TITLE, XLSX_NOTE, "Monthly Revenue", "Pipeline", "Assumptions",
                         "Medical and Dental Supplies", "Returns and Credits", "Share of H1", "Opportunity ID",
                         "Lakeshore Medical Group", "Silver Creek Casino Resort", "Riverside Catering Co.",
                         pipe[1][0], pipe[-1][0], "Taken from the CRM at 6:00 a.m. Pacific Time",
                         "Largest discount without director approval"],
        "ordered": [XLSX_TITLE, "Food Service Disposables", "Office and Breakroom", pipe[1][0], pipe[-1][0],
                    "Win rate (trailing 12 months)", "Revenue Operations"],
        "headings": [],
        "tables": [{"name": "Monthly Revenue (the two header rows 3-4 to the Total row 11; title, note and blank "
                             "rows above it not included; 'Q1 2026' and 'Q2 2026' merged across three months, "
                             "'Product line', 'H1 total' and 'Share of H1' merged down)", "rows": monthly},
                   {"name": "Pipeline (all 15 rows)", "rows": pipe},
                   {"name": "Assumptions (all 8 rows)", "rows": assumptions}],
        "noise": [],
        "absent": [],
    }
    n_formula = len(cached)
    gt = write_ground_truth(
        path, fmt="xlsx", title="Revenue by product line and sales pipeline, H1 2026", pages_or_sheets=3,
        stresses=["three visible worksheets (Monthly Revenue, Pipeline, Assumptions)",
                  "merged title row A1:I1 and an italic note row above a table that starts at row 3",
                  "two header rows: quarter groups merged across three month columns, three headers merged down",
                  f"{n_formula} formula cells saved with their computed (cached) values, as Excel saves them",
                  "negative currency with a leading minus: \"$\"#,##0;-\"$\"#,##0 shows -$8,450",
                  "currency with cents, whole percent, one-decimal percent, US dates m/d/yyyy, booleans TRUE/FALSE",
                  "account numbers stored as text with leading zeros (format @)",
                  "autofilter and frozen header row on the Pipeline sheet"],
        checks=checks,
        notes=("Expected cells are the text Excel shows in an en-US locale: whole dollars as '$412,350' and negatives "
               "as '-$8,450' (format \"$\"#,##0;-\"$\"#,##0), amounts with cents as '$186,400.00', probabilities as "
               "'75%', shares as '28.1%' (0.0%), dates as '10/30/2026' (m/d/yyyy), booleans as 'TRUE'/'FALSE' (Excel's "
               "display; normalization lowercases, so 'True' also matches), account numbers as text with their "
               "leading zeros ('004127'). Separators, date order and boolean words follow the viewer's locale, so (as "
               "in the corpus and holdout/) must_contain lists only text cells and the three sheet names, and number "
               "and date display is measured by the tables. The Monthly Revenue table starts at its first header row "
               "(row 3): 'Product line', 'H1 total' and 'Share of H1' are merged down over rows 3-4 and 'Q1 2026' / "
               "'Q2 2026' across their three months; a merged cell's text is in its top-left position and the covered "
               f"positions are empty strings (not scored). Formulas ({n_formula} cells: H5 '=SUM(B5:G5)', I5 "
               "'=H5/H$11', B11 '=SUM(B5:B10)', Pipeline H2 '=F2*G2', ...) are saved with their computed values, so "
               "the expected cell is the value, not the formula. The merged title (row 1) and note (row 2) are checked "
               "by must_contain and ordered, not as table rows. Sheet names are tab labels: checked by must_contain "
               "and by sheet order in ordered, not as headings. No hidden sheets, comments, charts or print "
               "headers/footers: noise and absent are empty."))

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
                if cv.number_format == FMT_DATE and cv.value is not None:
                    require(isinstance(cv.value, dt.datetime), "xlsx: date cell is not a real date")
                if cv.number_format == FMT_TEXT and cv.value is not None:
                    require(cv.data_type == "s", "xlsx: account number is not stored as text")
                out.append(xlsx_display(cv.value, cv.number_format))
            grid.append(out)
        grids[ws_v.title] = grid
        texts.append(ws_v.title + "\n" + "\n".join(" ".join(r) for r in grid))
        fields += [c for r in grid for c in r if c]
    m = grids["Monthly Revenue"]
    require(m[0][0] == XLSX_TITLE and m[1][0] == XLSX_NOTE and len(m[0]) == 9, "xlsx: title/note rows")
    require(sorted(str(r) for r in wb_v["Monthly Revenue"].merged_cells.ranges)
            == sorted(["A1:I1", "A3:A4", "H3:H4", "I3:I4", "B3:D3", "E3:G3"]), "xlsx: merged ranges")
    require(sum(1 for ws in wb_f.worksheets for row in ws.iter_rows() for c in row if c.data_type == "f")
            == n_formula, "xlsx: formula count")
    require(any(isinstance(c.value, bool) for row in wb_v["Pipeline"].iter_rows() for c in row), "xlsx: booleans")
    tables_found = [m[HEADER_TOP - 1:], grids["Pipeline"], grids["Assumptions"]]
    verify(path.name, "xlsx", gt, "\n".join(texts), tables_found=tables_found, fields=fields)
    return gt


# ===========================================================================
# 3. gen-qbr-deck.pptx
# ===========================================================================

PPTX_TABLE = [
    ["Region", "Q3 2026 revenue", "Plan", "Variance", "Variance %"],
    ["Midwest", "$5.12M", "$4.95M", "+$0.17M", "+3.4%"],
    ["Mountain", "$3.48M", "$3.30M", "+$0.18M", "+5.5%"],
    ["Pacific", "$4.06M", "$4.10M", "-$0.04M", "-1.0%"],
    ["Southwest", "$1.94M", "$1.77M", "+$0.17M", "+9.6%"],
    ["Total", "$14.60M", "$14.12M", "+$0.48M", "+3.4%"],
]
PROCESS = ["Order received through EDI or the web portal", "Picked and packed within 24 hours",
           "Delivered on our own trucks the next day"]
PROCESS_NOTE = "Average order-to-delivery time in Q3 was 1.6 days."
PPTX_SLIDES = [
    {"layout": 0, "title": "Q3 2026 Business Review", "subtitle": f"{COMPANY}, October 14, 2026"},
    {"layout": 2, "title": "Results", "body": "Third quarter 2026 compared with plan"},
    {"layout": 1, "title": "Quarter Highlights", "numbered": True,
     "bullets": [(0, "Revenue reached $14.6 million, 3.4 percent above plan"),
                 (0, "Gross margin improved to 22.8 percent from 21.9 percent"),
                 (0, "Order fill rate held at 98.1 percent across all warehouses"),
                 (0, "Two new hospital group contracts started in September")],
     "notes": "Stress that the margin gain came from freight savings, not price increases. The hospital contracts "
              "are worth about $3 million a year."},
    {"layout": 5, "title": "Revenue by Region", "table": True,
     "notes": "Pacific was below plan because the Portland warehouse move delayed two large deliveries into October."},
    {"layout": 5, "title": "Order-to-Delivery Process", "process": True},
    {"layout": 4, "title": "Reno Warehouse Options",
     "left_head": "Option A: Expand the current site",
     "left": [(0, "Adds 40,000 square feet by the end of 2027"), (0, "Estimated cost of $6.2 million"),
              (1, "Includes new racking and two dock doors")],
     "right_head": "Option B: Move to a new building",
     "right": [(0, "New lease of 120,000 square feet from mid-2028"),
               (0, "Estimated move cost of $2.9 million plus higher rent"), (1, "Rent rises by about $410,000 a year")],
     "notes": "Ask the committee to choose an option at the November meeting so that the lease talks can start."},
    {"layout": 1, "title": "Priorities for Q4",
     "bullets": [(0, "Complete the Portland warehouse move by November 15"),
                 (1, "Keep fill rate above 97 percent during the move"),
                 (0, "Renew the three largest food service contracts"),
                 (0, "Launch online ordering for clinics and dental offices"),
                 (1, "Pilot with 25 customers in the Denver area")]},
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
                el = ppr.makeelement(pqn(tag), attrs)
                ppr.append(el)


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
            require(layout.name == "Comparison", "pptx: layout 4 is not Comparison")
            slide.placeholders[1].text = spec["left_head"]
            _pptx_fill(slide.placeholders[2].text_frame, spec["left"])
            slide.placeholders[3].text = spec["right_head"]
            _pptx_fill(slide.placeholders[4].text_frame, spec["right"])
        if spec.get("table"):
            shape = slide.shapes.add_table(len(PPTX_TABLE), len(PPTX_TABLE[0]), Inches(0.5), Inches(1.8), Inches(9.0),
                                           Inches(0.45) * len(PPTX_TABLE))
            for r, row in enumerate(PPTX_TABLE):
                for c, value in enumerate(row):
                    cell = shape.table.cell(r, c)
                    cell.text = value
                    for para in cell.text_frame.paragraphs:
                        for run in para.runs:
                            run.font.size = PPt(16)
                            run.font.bold = r in (0, len(PPTX_TABLE) - 1) or None
        if spec.get("process"):
            group = slide.shapes.add_group_shape()
            left, top, w, h, gap = Inches(0.4), Inches(2.4), Inches(2.5), Inches(1.5), Inches(0.5)
            for k, text in enumerate(PROCESS):
                x = left + k * (w + gap)
                box = group.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top, w, h)
                box.text_frame.text = text
                box.text_frame.word_wrap = True
                if k < len(PROCESS) - 1:
                    group.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Emu(x + w + Inches(0.08)), Emu(top + Inches(0.55)),
                                           Emu(gap - Inches(0.16)), Inches(0.4))
            note = slide.shapes.add_textbox(Inches(0.4), Inches(4.6), Inches(9.0), Inches(0.6))
            note.text_frame.text = PROCESS_NOTE
        if "notes" in spec:
            slide.notes_slide.notes_text_frame.text = spec["notes"]
    props = prs.core_properties
    props.title = PPTX_SLIDES[0]["title"]
    props.author = "Strategy and Planning"
    props.last_modified_by = "Strategy and Planning"
    props.comments = ""
    props.revision = 5
    props.created = dt.datetime(2026, 10, 6, 13, 0, 0)
    props.modified = dt.datetime(2026, 10, 13, 18, 40, 0)
    prs.save(path)
    pin_ooxml(path, "2026-10-06T13:00:00Z", "2026-10-13T18:40:00Z")


def _shape_texts(shape, out, tables, kinds):
    """Text of a shape in document order, recursing into groups."""
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        kinds.append("group")
        for s in shape.shapes:
            _shape_texts(s, out, tables, kinds)
        return
    if shape.has_text_frame:
        out += [p.text for p in shape.text_frame.paragraphs if p.text]
    if getattr(shape, "has_table", False) and shape.has_table:
        grid = [[cell.text for cell in row.cells] for row in shape.table.rows]
        tables.append(grid)
        out += [" ".join(r) for r in grid]


def make_pptx():
    path = HERE / "gen-qbr-deck.pptx"
    build_pptx(path)
    paragraphs = ([PPTX_SLIDES[0]["subtitle"], PPTX_SLIDES[1]["body"]]
                  + [t for s in PPTX_SLIDES for key in ("bullets", "left", "right") for _, t in s.get(key, [])]
                  + [s[k] for s in PPTX_SLIDES for k in ("left_head", "right_head") if k in s]
                  + PROCESS + [PROCESS_NOTE])
    notes = [s["notes"] for s in PPTX_SLIDES if "notes" in s]
    must = [p for p in paragraphs if len(p.split()) >= MIN_PHRASE_WORDS] + notes
    short = [p for p in paragraphs if len(p.split()) < MIN_PHRASE_WORDS]
    checks = {
        "must_contain": must,
        "ordered": ["Q3 2026 Business Review", "Revenue reached $14.6 million", "Q3 2026 revenue",
                    PROCESS_NOTE, "Adds 40,000 square feet by the end of 2027",
                    "New lease of 120,000 square feet from mid-2028",
                    "Launch online ordering for clinics and dental offices"],
        "headings": [s["title"] for s in PPTX_SLIDES],
        "tables": [{"name": "Slide 4: Revenue by Region", "rows": PPTX_TABLE}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pptx", title=PPTX_SLIDES[0]["title"], pages_or_sheets=len(PPTX_SLIDES),
        stresses=["slide titles (title placeholders) as headings",
                  "title slide with a subtitle; Section Header slide with a text placeholder",
                  "auto-numbered list (a:buAutoNum arabicPeriod): the numbers are not in the text",
                  "native 6x5 table with signed currency and percent cells",
                  "process diagram: a group shape holding three rounded rectangles with text and two arrows, then a "
                  "free text box (not a placeholder)",
                  "Comparison layout: two headings and two bodies, left then right",
                  "two-level bullets; speaker notes on slides 3, 4 and 6"],
        checks=checks,
        notes=("Seven slides from python-pptx's default 4:3 template: 1 Title Slide, 2 Section Header, 3 and 7 Title "
               "and Content, 4 and 5 Title Only, 6 Comparison. Slide 3's list is numbered by PowerPoint auto-numbering "
               "(1. 2. 3. 4. are drawn, not typed), so phrases do not include the numbers. Slide 5's three process "
               "steps are text in shapes inside one group shape (box, arrow, box, arrow, box, left to right in both "
               "file order and position), followed by a separate text box; the steps are must_contain phrases only "
               "(no ordered anchor is taken from inside the group), and the text box below the group is an anchor. "
               "Slide 6 (Comparison) is read left heading, left body, right heading, right body, as in shape order "
               "and as placed. The table has a plain header row and a bold Total row; its cells are text as typed "
               "('+$0.17M', '-1.0%'; ASCII signs). Speaker notes (slides 3, 4 and 6) are in must_contain (3 phrases), "
               "never ordered anchors. headings are the seven slide titles. must_contain keeps every slide paragraph "
               f"of at least {MIN_PHRASE_WORDS} words; the {len(short)} shorter ones ({'; '.join(short)}) are not "
               "phrases. No footers, slide numbers, dates, hidden slides, charts or comments: noise and absent are "
               "empty."))
    prs = Presentation(path)
    titles, texts, body, tables, read_notes, groups = [], [], [], [], [], []
    for slide in prs.slides:
        titles.append(slide.shapes.title.text)
        out = []
        for shape in slide.shapes:
            _shape_texts(shape, out, tables, groups)
        texts += out
        body += out
        if slide.has_notes_slide:
            read_notes.append(slide.notes_slide.notes_text_frame.text)
            texts.append(read_notes[-1])
    require(read_notes == notes, "pptx: notes differ")
    require(groups == ["group"], "pptx: expected exactly one group shape")
    auto = [p for p in prs.slides[2].placeholders[1].text_frame.paragraphs
            if p._p.pPr is not None and p._p.pPr.find(pqn("a:buAutoNum")) is not None]
    require(len(auto) == 4, "pptx: auto-numbered paragraphs")
    verify(path.name, "pptx", gt, "\n".join(texts), body_text="\n".join(body), headings_found=titles,
           tables_found=tables)
    return gt


# ===========================================================================
# 4. gen-support-tickets.csv
# ===========================================================================

CSV_HEADER = ["ticket_id", "created_at", "channel", "priority", "status", "customer", "subject", "description",
              "assignee", "first_response_min", "csat", "order_value_usd", "tags"]
CSV_CUSTOMERS = ["Café Lumière", "Peña Family Dental", "Lakeshore Medical Group", "Zoë's Bakery",
                 "Pinecrest School District", "Bayview Senior Living", "Mesa Verde Urgent Care",
                 "Silver Creek Casino Resort", "Greenfield Food Bank", "Northgate Animal Hospital"]
CSV_CHANNELS = ["email", "phone", "web form", "chat"]
CSV_PRIORITIES = ["normal", "high", "normal", "low", "urgent"]
CSV_AGENTS = ["Ana Lucía Torres", "Ben Okafor", "Chloe Nguyen", "Diego Marchetti"]
# (subject, description, tags); descriptions hold commas, doubled quotes and two embedded line breaks.
CSV_ISSUES = [
    ("Short delivery on invoice 5581203", "Received 18 cases of 12 oz cups, invoice shows 20.", "delivery;shortage"),
    ("Damaged case of nitrile gloves", 'Outer box marked "THIS SIDE UP" arrived upside down, two boxes crushed.',
     "damage;claim"),
    ("Request copy of W-9", "Accounts payable needs the current W-9 before paying the open invoices.", "billing"),
    ("Change delivery window", "Please deliver after 10:00 a.m. on Tuesdays and Fridays; the dock is closed earlier.",
     "delivery;schedule"),
    ("Price on quote does not match invoice", "Quote Q-77812 says $41.20 per case, invoice billed $44.80.",
     "billing;pricing"),
    ("Online portal login fails", "Password reset email never arrives.\nTried twice on Monday.", "portal;access"),
    ("Substitute product received", "Ordered compostable lids, received plastic lids instead, please advise.",
     "delivery;substitution"),
    ("Credit memo not applied", 'Credit memo CM-2209 for $312.40 still shows as "open" on the statement.',
     "billing;credit"),
    ("Add new ship-to address", "New clinic opens on October 1:\n4410 Alder Street, Suite 200, Denver, CO 80216",
     "account;address"),
    ("Backorder status for sanitizer", "When will item JS-4471 be back in stock? We are down to two cases.",
     "inventory;backorder"),
]


def csv_rows():
    rows = []
    for i in range(30):
        subject, desc, tags = CSV_ISSUES[(i * 7) % len(CSV_ISSUES)]
        created = dt.datetime(2026, 9, 1, 8, 0, 0) + dt.timedelta(hours=7 * i + (i * 13) % 5, minutes=(i * 37) % 60)
        status = "open" if i % 6 == 4 else ("pending" if i % 7 == 3 else "solved")
        first_resp = "" if i % 9 == 5 else str(12 + (i * 23) % 170)
        csat = str(5 - (i * 3) % 3) if status == "solved" and i % 4 != 1 else ""
        value = Decimal(180 + (i * 4513) % 9000) + Decimal((i * 29) % 100) / 100
        rows.append([f"HP-{48120 + i * 3}", created.strftime("%Y-%m-%dT%H:%M:%SZ"), CSV_CHANNELS[i % 4],
                     CSV_PRIORITIES[i % 5], status, CSV_CUSTOMERS[(i * 3) % len(CSV_CUSTOMERS)], subject, desc,
                     CSV_AGENTS[(i * 5) % len(CSV_AGENTS)], first_resp, csat, f"{money(value):,.2f}", tags])
    return rows


def make_csv():
    path = HERE / "gen-support-tickets.csv"
    rows = csv_rows()
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    path.write_bytes(buf.getvalue().encode("utf-8"))
    multi = [r for r in rows if "\n" in r[7]]
    big = [r[11] for r in rows if "," in r[11]]
    checks = {
        "must_contain": ["first_response_min", "order_value_usd", "Café Lumière", "Peña Family Dental",
                         "Zoë's Bakery",
                         "Ana Lucía Torres", "Short delivery on invoice 5581203",
                         'Outer box marked "THIS SIDE UP" arrived upside down, two boxes crushed.',
                         "Quote Q-77812 says $41.20 per case, invoice billed $44.80.",
                         'Credit memo CM-2209 for $312.40 still shows as "open" on the statement.',
                         "Please deliver after 10:00 a.m. on Tuesdays and Fridays; the dock is closed earlier.",
                         rows[0][0], rows[14][0], rows[-1][0], rows[0][1], rows[-1][1], big[0], big[-1]],
        "ordered": [rows[0][0], rows[7][0], rows[14][0], rows[21][0], rows[-1][0]],
        "headings": [],
        "tables": [{"name": "Tickets: header row and all 30 data rows", "rows": [CSV_HEADER] + rows}],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="csv", title="Help-desk ticket export, September 2026", pages_or_sheets=None,
        stresses=["every field quoted (QUOTE_ALL), comma delimiter, LF line ends, UTF-8 without BOM",
                  f"{len(multi)} fields (two different texts) with an embedded line break inside quotes, so those "
                  "records span two physical lines",
                  "fields with commas, semicolons and doubled double quotes",
                  "numbers with thousands separators inside quoted fields (order_value_usd '1,234.56')",
                  "empty quoted fields (first_response_min, csat)",
                  "ISO 8601 UTC timestamps, non-ASCII names (é, ñ, ë, í), a straight apostrophe"],
        checks=checks,
        notes=("RFC 4180 CSV as many SaaS exports write it: every field in double quotes (empty fields as \"\"), "
               "comma delimiter, LF line ends, UTF-8 without BOM. The ten issue types repeat over the 30 tickets; six "
               "description fields (two different texts) contain a line break inside the quotes, so those records "
               "span two physical lines; the expected cell keeps the line break "
               "(normalization turns it into a space). order_value_usd values are text with a comma thousands "
               "separator ('1,234.56'), which the table rule compares with the comma removed on both sides; "
               "tags hold ';'-separated values inside one field. Expected cell and phrase text is the parsed field "
               "value (quotes unescaped). The expected table is the whole file (header + 30 rows, 13 columns); empty "
               "fields are empty strings and are not scored. must_contain items are whole fields that never occur "
               "inside another field (ticket ids and timestamps of rows 1, 15 and 30, two order values with a "
               "thousands separator, three descriptions with quotes or commas); no phrase is a multi-line field. "
               "ordered: the ticket ids of rows 1, 8, 15, 22 and 30. A CSV has no headings, page furniture or "
               "hyphenation: headings, noise and absent are empty."))
    raw = path.read_bytes()
    require(not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw, "csv: BOM / CRLF")
    text = raw.decode("utf-8")
    parsed = list(csv.reader(io.StringIO(text, newline=""), delimiter=","))
    require(parsed[0] == CSV_HEADER and parsed[1:] == rows and len(parsed) == 31, "csv: read-back differs")
    require(all(len(r) == len(CSV_HEADER) for r in parsed), "csv: ragged rows")
    require(len(multi) == 6 and len({r[7] for r in multi}) == 2 and len(big) >= 2
            and all(text.count(f'"{r[0]}"') == 1 for r in rows), "csv: features")
    require('""THIS SIDE UP""' in text and '""""' not in text and '""' in text, "csv: quoting")
    verify(path.name, "csv", gt, "\n".join(" ".join(r) for r in parsed), tables_found=[parsed],
           fields=[c for r in parsed for c in r])
    return gt


# ===========================================================================
# 5. gen-product-catalog.json
# ===========================================================================

JSON_PRODUCTS = [
    # (sku, name, category path, active, list price, tiers, dims, weight, attributes, inventory, images, updated, notes)
    ("HP-10442", "Compostable hot cup, 12 oz", ["Food Service", "Disposables", "Cups"], True, "48.90",
     [(10, "46.50"), (50, "44.20")], [45.5, 31.0, 38.0], 6.8, {"material": "PLA-lined paper", "compostable": True,
                                                                 "color": "kraft"},
     [("RNO", 1250, 40, ["A-04-2", "A-04-3"]), ("DEN", 380, 0, ["C-11-1"])],
     ["https://cdn.haldenpryce.example/p/10442.jpg"],
     "2026-10-02T09:15:00-07:00", None),
    ("HP-10458", "Crème brûlée ramekin, 4 oz", ["Food Service", "Disposables", "Bakeware"], True, "62.40",
     [(10, "59.90")], [40.0, 30.0, 22.5], 9.1, {"material": "aluminum", "compostable": False, "color": None},
     [("RNO", 214, 12, ["A-07-1"])], [], "2026-09-28T16:40:12-07:00", "Lids sold separately (HP-10459)."),
    ("HP-20311", "Nitrile exam gloves, size M", ["Medical", "Gloves"], True, "11.75",
     [(20, "11.20"), (100, "10.60"), (500, "9.95")], [24.0, 12.5, 9.0], 0.95,
     {"material": "nitrile", "powder_free": True, "count_per_box": 100},
     [("RNO", 8400, 600, ["M-01-1", "M-01-2", "M-01-3"]), ("PDX", 0, 0, [])], [], "2026-10-05T08:00:00-07:00",
     "Ships from Reno until the Portland move is complete."),
    ("HP-20377", "Surface disinfectant wipes, 160 ct", ["Janitorial", "Disinfectants"], True, "7.35",
     [(12, "6.95")], [20.3, 13.0, 13.0], 1.1, {"epa_registration": "8383-12", "scent": "lemon"},
     [("DEN", 2210, 150, ["J-02-4"])], ["https://cdn.haldenpryce.example/p/20377.jpg"],
     "2026-10-01T11:22:47-06:00", None),
    ("HP-30904", "Corrugated shipping box 18 x 12 x 10 in", ["Packaging", "Boxes"], True, "1.42",
     [(250, "1.28"), (1000, "1.17")], [45.7, 30.5, 25.4], 0.48, {"edge_crush_test": "32 ECT", "recycled_pct": 40},
     [("RNO", 15800, 2500, ["P-20-1", "P-20-2"]), ("DEN", 6400, 0, ["P-05-3"])], [], "2026-09-30T07:05:00-07:00",
     None),
    ("HP-31120", "Packing tape, clear, 2 in x 110 yd", ["Packaging", "Tape"], False, "3.10", [], [10.5, 10.5, 5.0],
     0.32, {}, [], [], "2026-08-19T14:30:00-07:00", "Discontinued; replaced by HP-31125 \"heavy duty\"."),
    ("HP-40215", "Coffee filters, 12-cup basket", ["Breakroom", "Coffee"], True, "18.60", [(10, "17.80")],
     [28.0, 22.0, 18.0], 2.4, {"count_per_case": 1000, "compostable": True},
     [("PDX", 96, 0, ["B-03-2"])], [], "2026-09-12T10:00:00-07:00", None),
    ("HP-50072", "Søndergaard dental bib, blue", ["Medical", "Dental"], True, "24.25", [(5, "23.10")],
     [33.0, 25.0, 15.0], 3.6, {"ply": 3, "size_in": [13, 18]}, [("DEN", 640, 80, ["D-09-1"])],
     ["https://cdn.haldenpryce.example/p/50072-front.jpg", "https://cdn.haldenpryce.example/p/50072-back.jpg"],
     "2026-10-06T13:45:30-06:00", None),
]


def json_model():
    products = []
    for (sku, name, path, active, price, tiers, dims, weight, attrs, inv, images, updated, notes) in JSON_PRODUCTS:
        products.append({
            "sku": sku, "name": name, "category": {"path": path, "depth": len(path)}, "active": active,
            "price": {"currency": "USD", "list": float(Decimal(price)),
                      "tiers": [{"min_qty": q, "unit": float(Decimal(u))} for q, u in tiers]},
            "dimensions_cm": dims, "weight_kg": weight, "attributes": attrs,
            "inventory": [{"warehouse": w, "on_hand": oh, "reserved": rs, "available": oh - rs, "bins": bins}
                          for w, oh, rs, bins in inv],
            "images": images, "updated_at": updated, "notes": notes,
        })
    return products


def make_json():
    path = HERE / "gen-product-catalog.json"
    obj = json_model()
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    path.write_text(raw, encoding="utf-8")
    checks = {
        "must_contain": ["dimensions_cm", "min_qty", "HP-10442", "HP-50072", "Compostable hot cup, 12 oz",
                         "Crème brûlée ramekin, 4 oz", "Søndergaard dental bib, blue",
                         "Lids sold separately (HP-10459).", 'Discontinued; replaced by HP-31125 "heavy duty".',
                         "Ships from Reno until the Portland move is complete.", "PLA-lined paper", "8383-12",
                         "2026-09-28T16:40:12-07:00", "https://cdn.haldenpryce.example/p/50072-back.jpg", "32 ECT",
                         "15800", "9.95"],
        "ordered": ["HP-10442", "Crème brûlée ramekin, 4 oz", "HP-20377", "HP-31120", "HP-50072"],
        "headings": [],
        "tables": [],
        "noise": [],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="json", title="Product catalog export (8 products), October 2026", pages_or_sheets=None,
        stresses=["minified JSON: the whole file is one line with no spaces between tokens and no final newline",
                  "top-level array of 8 objects",
                  "nested objects and arrays: arrays of objects (price tiers, inventory), arrays of arrays of "
                  "numbers, arrays of strings (bins, images)",
                  "null values, booleans, empty arrays and an empty object",
                  "objects whose keys differ from one record to the next (attributes)",
                  "non-ASCII text kept as UTF-8 (è, û, ø), an escaped double quote",
                  "timestamps with UTC offsets, decimal prices as JSON numbers"],
        checks=checks,
        notes=("UTF-8 JSON written by json.dumps(..., ensure_ascii=False, separators=(',', ':')): one line, no "
               "indentation, no trailing newline, key order as written, non-ASCII characters as-is. A converter may "
               "keep it on one line, pretty-print it or render it as text or tables; no Markdown structure is "
               "expected, so headings and tables are empty. must_contain items are whole keys or scalar values that "
               "occur once and never inside another key or value (numbers as JSON writes them: an on-hand quantity "
               "and a tier price). Matching deletes backslashes and underscores, so the note with an escaped quote "
               "also matches its raw JSON form and dimensions_cm matches dimensionscm. ordered follows document "
               "order: the SKUs of products 1, 4, 6 and 8 and the name of product 2. Inventory 'available' = on_hand "
               "- reserved. URLs and e-mail-like domains are .example domains."))
    text = path.read_text(encoding="utf-8")
    require(json.loads(text) == obj and "\n" not in text, "json: read-back differs")
    require(not text.startswith(" ") and '":' in text and '": ' not in text, "json: not minified")
    require('\\"heavy duty\\"' in text and "Søndergaard" in text, "json: escaping")
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
    require({} in [p["attributes"] for p in obj] and [] in [p["images"] for p in obj], "json: empty object/array")
    verify(path.name, "json", gt, text, fields=fields)
    return gt


# ===========================================================================
# 6. gen-price-list.pdf (not read back with a text extractor; see the module doc)
# ===========================================================================

PDF_TITLE = "2027 Wholesale Price List"
PDF_HEADER_LEFT = COMPANY
PDF_HEADER_RIGHT = "Wholesale Price List 2027"
PDF_FOOTER = "Prices in U.S. dollars, valid January 1 to December 31, 2027"
PDF_INTRO = ("This price list replaces the 2026 edition for all wholesale accounts. Prices are per unit of sale, "
             "exclude sales tax and include delivery within our standard service area.")
PDF_TERMS = ["The minimum order value is $250 per delivery.",
             "Orders received by 2:00 p.m. Central Time ship the same business day.",
             "Invoices are payable within 30 days of the invoice date.",
             "Returns are accepted within 14 days for unopened cases only."]
PDF_TABLE_INTRO = "The Unit column gives the unit of sale that the price applies to."
PDF_NOTES = ["Prices with a negative change were reduced from the 2026 list.",
             "Fuel surcharges are reviewed each quarter and shown separately on the invoice.",
             "Contract customers should refer to their agreement for net prices."]
PDF_CLOSING = ("For questions about this price list, contact your account manager or call customer service at "
               "1-800-555-0199.")
PDF_HEADER_ROW = ["SKU", "Description", "Pack", "Unit", "Price (USD)", "Change vs 2026"]
PDF_ITEMS = [  # (sku, description, pack, unit, 2026 price, change percent)
    ("HP-10442", "Compostable hot cup, 12 oz", "1,000", "case", "47.20", "3.5"),
    ("HP-10443", "Compostable hot cup, 16 oz", "1,000", "case", "55.80", "3.5"),
    ("HP-10459", "Ramekin lid, 4 oz", "500", "case", "21.40", "2.0"),
    ("HP-10501", "Kraft take-out box, No. 8", "200", "case", "38.60", "0.0"),
    ("HP-10512", "Paper napkin, 1-ply, white", "6,000", "case", "29.90", "-2.0"),
    ("HP-10530", "Wooden stir stick, 7 in", "10,000", "case", "16.75", "4.0"),
    ("HP-10544", "Plastic cutlery kit, wrapped", "250", "case", "33.10", "1.5"),
    ("HP-10560", "Foil container, half size", "100", "case", "41.25", "3.5"),
    ("HP-10577", "Deli container with lid, 16 oz", "240", "case", "36.90", "2.0"),
    ("HP-10583", "Portion cup, 2 oz", "2,500", "case", "24.30", "0.0"),
    ("HP-20311", "Nitrile exam gloves, size M", "100", "box", "11.35", "3.5"),
    ("HP-20312", "Nitrile exam gloves, size L", "100", "box", "11.35", "3.5"),
    ("HP-20340", "Procedure mask, ear loop", "50", "box", "6.20", "-2.0"),
    ("HP-20355", "Isolation gown, universal", "10", "pack", "14.80", "1.5"),
    ("HP-20377", "Surface disinfectant wipes, 160 ct", "1", "canister", "7.10", "3.5"),
    ("HP-20390", "Alcohol prep pad, medium", "200", "box", "3.95", "0.0"),
    ("HP-20402", "Gauze sponge, 4 x 4 in", "200", "pack", "8.45", "2.0"),
    ("HP-20415", "Exam table paper, 21 in", "12", "case", "52.60", "4.0"),
    ("HP-20433", "Sharps container, 1 qt", "1", "each", "4.85", "1.5"),
    ("HP-20450", "Tongue depressor, sterile", "100", "box", "5.30", "0.0"),
    ("HP-30904", "Corrugated box 18 x 12 x 10 in", "25", "bundle", "34.25", "3.5"),
    ("HP-30911", "Corrugated box 12 x 12 x 12 in", "25", "bundle", "29.80", "3.5"),
    ("HP-30930", "Bubble wrap roll, 12 in x 175 ft", "1", "roll", "22.40", "-2.0"),
    ("HP-30946", "Stretch film, 18 in x 1,500 ft", "4", "case", "71.60", "2.0"),
    ("HP-30958", "Poly mailer, 10 x 13 in", "500", "case", "39.70", "1.5"),
    ("HP-31125", "Packing tape, heavy duty, 2 in", "36", "case", "58.30", "0.0"),
    ("HP-31140", "Shipping label, 4 x 6 in", "1,000", "roll", "18.90", "4.0"),
    ("HP-31162", "Void fill paper, 15 in", "1", "roll", "44.10", "3.5"),
    ("HP-40215", "Coffee filters, 12-cup basket", "1,000", "case", "17.95", "3.5"),
    ("HP-40230", "Paper hot cup sleeve", "1,000", "case", "27.40", "2.0"),
    ("HP-40248", "Sugar packets", "2,000", "case", "21.60", "-2.0"),
    ("HP-40261", "Non-dairy creamer cups", "400", "case", "26.80", "1.5"),
    ("HP-40277", "Breakroom trash liner, 33 gal", "250", "case", "35.20", "0.0"),
    ("HP-40289", "Dish soap, 1 gal", "4", "case", "31.75", "4.0"),
    ("HP-50072", "Dental bib, 3-ply, blue", "500", "case", "23.45", "3.5"),
    ("HP-50085", "Saliva ejector, clear", "100", "bag", "6.90", "2.0"),
    ("HP-50093", "Prophy angle, soft cup", "100", "box", "19.85", "1.5"),
    ("HP-50110", "Patient towel, 2-ply", "500", "case", "28.95", "0.0"),
    ("HP-60014", "Floor cleaner concentrate, 1 gal", "4", "case", "48.30", "3.5"),
    ("HP-60027", "Glass cleaner, 32 oz spray", "12", "case", "39.60", "2.0"),
    ("HP-60039", "Microfiber cloth, 16 in", "24", "pack", "17.20", "-2.0"),
    ("HP-60052", "Hand soap refill, 1,000 ml", "6", "case", "42.90", "1.5"),
    ("HP-60066", "Roll towel, 8 in x 800 ft", "6", "case", "46.75", "4.0"),
    ("HP-60078", "Toilet tissue, 2-ply, 500 sheets", "96", "case", "63.40", "0.0"),
    ("HP-60091", "Trash liner, 55 gal, black", "100", "case", "37.85", "3.5"),
]


def pdf_rows():
    rows = []
    for sku, desc, pack, unit, p26, chg in PDF_ITEMS:
        d = Decimal(chg)
        price = money(Decimal(p26) * (1 + d / 100))
        change = f"+{d}%" if d > 0 else (f"{d}%" if d < 0 else "0.0%")
        rows.append([sku, desc, pack, unit, f"${price:,.2f}", change])
    return rows


def _pdf_build(path: Path, rows, total_pages):
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

    title = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=20, leading=24, spaceAfter=10)
    h2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("B", fontName="Helvetica", fontSize=10, leading=13.5, spaceAfter=6, alignment=TA_LEFT)
    cell = ParagraphStyle("C", fontName="Helvetica", fontSize=8.5, leading=10.5)

    def para(text, style=body):
        return RLParagraph(xml_escape(text), style)

    story = [para(PDF_TITLE, title), para(PDF_INTRO), para("Ordering Terms", h2),
             ListFlowable([ListItem(para(t)) for t in PDF_TERMS], bulletType="1", bulletFormat="%s.", leftIndent=18),
             para("Products", h2), para(PDF_TABLE_INTRO)]
    data = [PDF_HEADER_ROW] + [[r[0], RLParagraph(xml_escape(r[1]), cell)] + r[2:] for r in rows]
    table = Table(data, colWidths=[0.85 * inch, 2.75 * inch, 0.65 * inch, 0.75 * inch, 0.9 * inch, 1.0 * inch],
                  repeatRows=1)
    style = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#B0B7C3"))]
    style += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#EEF2F7")) for r in range(2, len(data), 2)]
    table.setStyle(TableStyle(style))
    story += [table, para("Notes", h2),
              ListFlowable([ListItem(para(t)) for t in PDF_NOTES], bulletType="bullet", start="•", leftIndent=18),
              Spacer(1, 6), para(PDF_CLOSING)]
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.9 * inch, bottomMargin=0.85 * inch, title=PDF_TITLE, author="Pricing Team",
                            subject="Wholesale price list", creator="Pricing Team", invariant=1)
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return max(pages)


def make_pdf():
    path = HERE / "gen-price-list.pdf"
    rows = pdf_rows()
    n = _pdf_build(path, rows, 0)
    require(_pdf_build(path, rows, n) == n, "pdf: page count changed between passes")
    require(n == 2, f"pdf: expected 2 pages, got {n}")
    body_parts = ([PDF_TITLE, PDF_INTRO, "Ordering Terms"] + PDF_TERMS + ["Products", PDF_TABLE_INTRO]
                  + [" ".join(r) for r in [PDF_HEADER_ROW] + rows] + ["Notes"] + PDF_NOTES + [PDF_CLOSING])
    furniture_text = "\n".join(f"{PDF_HEADER_LEFT} {PDF_HEADER_RIGHT} {PDF_FOOTER} Page {k} of {n}"
                               for k in range(1, n + 1))
    checks = {
        "must_contain": ["This price list replaces the 2026 edition for all wholesale accounts.",
                         "Prices are per unit of sale, exclude sales tax and include delivery within our standard "
                         "service area."]
                        + PDF_TERMS + [PDF_TABLE_INTRO] + PDF_NOTES + [PDF_CLOSING],
        "ordered": [PDF_TITLE, "This price list replaces the 2026 edition", "The minimum order value is $250",
                    rows[0][1], rows[-1][1], "Prices with a negative change were reduced",
                    "For questions about this price list"],
        "headings": [PDF_TITLE, "Ordering Terms", "Products", "Notes"],
        "tables": [{"name": "Products (one table over two pages, header row repeated on page 2; complete: header "
                             "and all 45 rows)", "rows": [PDF_HEADER_ROW] + rows}],
        "noise": [{"text": PDF_HEADER_LEFT, "max": 1}, {"text": PDF_HEADER_RIGHT, "max": 1},
                  {"text": PDF_FOOTER, "max": 1}],
        "absent": [],
    }
    gt = write_ground_truth(
        path, fmt="pdf", title=PDF_TITLE, pages_or_sheets=n,
        stresses=["generated single-column PDF (ReportLab, standard Helvetica fonts, untagged)",
                  "title and section headings set by font size and the Helvetica-Bold font only (no tags)",
                  "numbered list (1. 2. 3. 4.) and bulleted list drawn as list flowables",
                  "one 45-row, 6-column table that continues from page 1 to page 2 with its header row repeated at "
                  "the top of page 2, zebra shading, right-aligned numbers, '+' and '-' signed percentages",
                  "running header (left and right text with a rule) and footer ('Page N of 2') on every page"],
        checks=checks,
        notes=("ReportLab 'invariant' mode pins the creation date and document ID, so the file is reproducible. The "
               "checks come from the generator's data in reading order; the file was NOT read back with any text "
               "extractor (blind protocol), only rendered to images with pdftoppm and looked at (2 pages: title, "
               "intro, Ordering Terms, Products, the table intro and the first 25 product rows on page 1; the repeated "
               "header row, the other 20 rows, Notes and the closing line on page 2), and its font list was checked "
               "with pdffonts (Helvetica and Helvetica-Bold, base-14, not embedded). Headings: the 20-point title and "
               "the three 13-point section headings, all set in Helvetica-Bold (a viewer without the base-14 bold face "
               "may draw them in regular weight; the local poppler render did). The table is one table in the "
               "source (repeatRows=1 repeats the header row at "
               "the top of page 2); the expected table is the header row and all 45 rows once, so a conversion "
               "that keeps it as one table scores best and repeated header rows inside it cost precision only. Price "
               "cells are '$48.85'-style text with thousands separators where needed; 'Change vs 2026' cells are "
               "'+3.5%', '0.0%' or '-2.0%' with ASCII signs; the Pack column has '1,000'-style counts (compared "
               "without the comma). must_contain: every paragraph sentence and list item ("
               f"{len(checks['must_contain'])} phrases). ordered: title, intro, "
               "first ordering term, the first and last product descriptions, the first note, the closing line. "
               "Noise: the running header's two parts and the footer text are printed once per page (twice) and "
               "occur nowhere in the body, max 1 each; 'Page N of 2' is not counted (it differs per page). No "
               "hyphenation (ReportLab does not hyphenate by default): absent is empty."))
    verify(path.name, "pdf", gt, "\n".join(body_parts) + "\n" + furniture_text, body_text="\n".join(body_parts),
           furniture=furniture_text)
    # Noise texts must not count inside the body: verify() checked that each one is absent from the body text.
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
