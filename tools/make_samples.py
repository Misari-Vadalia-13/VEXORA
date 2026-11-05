"""
VEXORA — Demonstration Dataset Generator (Phase G / Phase 1 Expanded)
Programmatically generates a comprehensive benchmark dataset consisting of:
- 15 Genuine Documents (invoices, bank statements, POs, contracts, receipts, IDs, leases, requisitions)
- 20 Tampered Documents (font shifts, white-box redactions, reversed dates, duplicate references,
  cross-document financial contradictions, editing tool metadata, copy-move cloning, future timelines,
  overwritten text patches, baseline disparities, superimposed signatures, multi-page total conflicts)
- demo_dataset/labels.csv ground truth annotation table.
- demo_dataset/cases.csv cross-document evaluation scenarios.
"""

import os
import io
import csv
from pathlib import Path
import pymupdf as fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

DATASET_DIR = Path(__file__).resolve().parent.parent / 'demo_dataset'


def ensure_dataset_dir():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# 1. Genuine Document Generators
# =====================================================================

def make_genuine_pdf(filename, title, lines, metadata=None):
    filepath = DATASET_DIR / filename
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Document Header
    page.insert_text(fitz.Point(50, 70), title, fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.draw_line(fitz.Point(50, 85), fitz.Point(545, 85), color=(0.7, 0.7, 0.7), width=1)

    # Document Body Lines
    y = 120
    for line in lines:
        if isinstance(line, tuple):
            label, val = line
            page.insert_text(fitz.Point(50, y), label, fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
            page.insert_text(fitz.Point(220, y), str(val), fontsize=10, fontname="helv", color=(0.0, 0.0, 0.0))
        else:
            page.insert_text(fitz.Point(50, y), str(line), fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))
        y += 26

    # Footer
    page.draw_line(fitz.Point(50, 780), fitz.Point(545, 780), color=(0.8, 0.8, 0.8), width=0.5)
    page.insert_text(fitz.Point(50, 795), "VEXORA Verified Document Registry — Ground Truth Genuine", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc_meta = {
        'creator': 'Enterprise Accounting ERP v4.2',
        'producer': 'Certified Document Engine',
        'creationDate': 'D:20260115100000Z',
        'modDate': 'D:20260115100000Z'
    }
    if metadata:
        doc_meta.update(metadata)
    doc.set_metadata(doc_meta)

    doc.save(str(filepath))
    doc.close()
    return filepath


def make_genuine_image(filename, title, lines):
    filepath = DATASET_DIR / filename
    img = Image.new('RGB', (600, 450), color=(248, 249, 250))
    draw = ImageDraw.Draw(img)

    # Header banner
    draw.rectangle([0, 0, 600, 50], fill=(26, 54, 93))
    draw.text((30, 15), title, fill=(255, 255, 255))

    y = 80
    for line in lines:
        if isinstance(line, tuple):
            label, val = line
            draw.text((40, y), f"{label}: {val}", fill=(30, 41, 59))
        else:
            draw.text((40, y), str(line), fill=(30, 41, 59))
        y += 30

    # Border
    draw.rectangle([10, 10, 590, 440], outline=(203, 213, 225), width=2)
    img.save(str(filepath))
    return filepath


# =====================================================================
# 2. Tampered Document Generators
# =====================================================================

def make_tampered_font_shift(filename):
    """Tampering: Total amount inserted with an anomalous font size and position."""
    filepath = DATASET_DIR / filename
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(fitz.Point(50, 70), "TAX INVOICE - APEX DYNAMICS", fontsize=16, fontname="helv")
    page.insert_text(fitz.Point(50, 120), "Invoice Number: INV-2026-0091", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 150), "Issue Date: 2026-03-10", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 180), "Due Date: 2026-04-10", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 210), "Subtotal: $1,250.00", fontsize=10, fontname="helv")

    # Tampered total: huge disparate font size and altered typographic baseline
    page.insert_text(fitz.Point(50, 260), "Grand Total: ", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(140, 258), "$98,750.00", fontsize=24, fontname="times-bold", color=(0.8, 0, 0))

    doc.save(str(filepath))
    doc.close()
    return filepath


def make_tampered_whitebox_receipt(filename):
    """Tampering: A white rectangular patch pasted over original text creating ELA anomaly."""
    filepath = DATASET_DIR / filename
    img = Image.new('RGB', (600, 400), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)

    for x in range(0, 600, 10):
        draw.line([(x, 0), (x, 400)], fill=(235, 235, 235))

    draw.text((50, 40), "OFFICIAL SALES RECEIPT", fill=(0, 0, 0))
    draw.text((50, 90), "Date: 2026-04-12", fill=(0, 0, 0))
    draw.text((50, 130), "Item: Server Hardware Component", fill=(0, 0, 0))
    draw.text((50, 170), "Original Total: $450.00", fill=(0, 0, 0))

    # White box patch altering amount
    draw.rectangle([45, 165, 300, 195], fill=(255, 255, 255))
    draw.text((50, 170), "Tampered Amount: $9,450.00", fill=(0, 0, 0))

    img.save(str(filepath), quality=85)
    return filepath


def make_tampered_reversed_dates(filename):
    """Tampering: Due date precedes invoice issue date."""
    lines = [
        ("Invoice Number", "INV-2026-7741"),
        ("Counterparty", "Solas Renewable Systems"),
        ("Issue Date", "2026-06-25"),
        ("Payment Due Date", "2026-05-10"),  # Reversed date!
        ("Subtotal", "$14,500.00"),
        ("Total Amount", "$14,500.00")
    ]
    return make_genuine_pdf(filename, "TAX INVOICE - REVERSED TIMELINE", lines)


def make_tampered_photoshop_metadata(filename):
    """Tampering: PDF with Adobe Photoshop in Creator metadata."""
    lines = [
        ("Document Title", "Commercial Lease Agreement"),
        ("Lessor", "Prime Properties LLC"),
        ("Lessee", "Apex Technologies"),
        ("Monthly Rent", "$8,500.00"),
        ("Execution Date", "2026-02-01")
    ]
    meta = {
        'creator': 'Adobe Photoshop 2024 (Macintosh)',
        'producer': 'Adobe PDF Library 17.0'
    }
    return make_genuine_pdf(filename, "COMMERCIAL LEASE AGREEMENT", lines, metadata=meta)


def make_tampered_future_date(filename):
    """Tampering: Document dated in the distant future."""
    lines = [
        ("Certification #", "CERT-88192"),
        ("Issued To", "Veridian Bio Research"),
        ("Effective Date", "2038-11-20"),  # Future date!
        ("Inspector", "Dr. Alex Turner"),
        ("Total Fee", "$3,200.00")
    ]
    return make_genuine_pdf(filename, "CERTIFICATE OF COMPLIANCE", lines)


def make_tampered_copymove_image(filename):
    """Tampering: Duplicate security stamp cloned across two distinct locations."""
    filepath = DATASET_DIR / filename
    img = Image.new('RGB', (600, 450), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)

    draw.text((50, 40), "OFFICIAL NOTARIZED DECLARATION", fill=(20, 30, 50))
    draw.text((50, 90), "Affidavit ID: AFF-2026-092", fill=(50, 50, 50))
    draw.text((50, 130), "Declared before Notary Public on 2026-03-01", fill=(50, 50, 50))

    stamp_pattern = [350, 250, 450, 350]
    draw.rectangle(stamp_pattern, outline=(180, 40, 40), width=3)
    draw.text((360, 290), "VERIFIED NOTARY", fill=(180, 40, 40))

    stamp_pattern_clone = [100, 250, 200, 350]
    draw.rectangle(stamp_pattern_clone, outline=(180, 40, 40), width=3)
    draw.text((110, 290), "VERIFIED NOTARY", fill=(180, 40, 40))

    img.save(str(filepath))
    return filepath


def make_tampered_overwritten_text(filename):
    """Tampering: White vector rectangle drawn over original amount with altered amount printed over it."""
    filepath = DATASET_DIR / filename
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 70), "TAX INVOICE - LOGISTICS SERVICES", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.draw_line(fitz.Point(50, 85), fitz.Point(545, 85), color=(0.7, 0.7, 0.7), width=1)
    page.insert_text(fitz.Point(50, 120), "Invoice Number: INV-2026-8812", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 150), "Issue Date: 2026-03-15", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 180), "Due Date: 2026-04-15", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 210), "Subtotal: $450.00", fontsize=10, fontname="helv")

    page.insert_text(fitz.Point(50, 260), "Total Amount: $450.00", fontsize=10, fontname="helv")
    page.draw_rect(fitz.Rect(115, 248, 220, 268), color=(1, 1, 1), fill=(1, 1, 1))
    page.insert_text(fitz.Point(120, 260), "$14,450.00", fontsize=10, fontname="helv", color=(0, 0, 0))

    doc.save(str(filepath))
    doc.close()
    return filepath


def make_tampered_font_size_baseline(filename):
    """Tampering: In-line baseline offset and font family discrepancy in financial total."""
    filepath = DATASET_DIR / filename
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 70), "PURCHASE ORDER - PRECISION HARDWARE", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.draw_line(fitz.Point(50, 85), fitz.Point(545, 85), color=(0.7, 0.7, 0.7), width=1)
    page.insert_text(fitz.Point(50, 120), "PO Number: PO-2026-9021", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 150), "Vendor: Metrolab Supplies Ltd", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 180), "Order Date: 2026-02-18", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 210), "Quantity: 50 units", fontsize=10, fontname="helv")

    page.insert_text(fitz.Point(50, 260), "Grand Total Amount: ", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(170, 253), "$74,500.00", fontsize=14, fontname="courier", color=(0.1, 0.1, 0.1))

    doc.save(str(filepath))
    doc.close()
    return filepath


def make_tampered_pasted_signature_pdf(filename):
    """Tampering: Embedded raster signature stamp pasted directly overlapping underlying vector text."""
    filepath = DATASET_DIR / filename
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 70), "EXECUTIVE CONSULTING CONTRACT", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.draw_line(fitz.Point(50, 85), fitz.Point(545, 85), color=(0.7, 0.7, 0.7), width=1)
    page.insert_text(fitz.Point(50, 120), "Contract Ref: CON-2026-0044", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 150), "Client: Veridian Global Partners", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 180), "Effective Date: 2026-03-01", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 210), "Terms: Standard Binding NDA and Service Schedule.", fontsize=10, fontname="helv")

    page.insert_text(fitz.Point(50, 680), "Authorized Signature: Dr. Alex Turner, Managing Director", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 700), "Date Signed: March 01, 2026 | Signatory Title: Chief Forensic Officer", fontsize=9, fontname="helv")

    sig_img = Image.new('RGBA', (150, 50), color=(255, 255, 255, 0))
    d = ImageDraw.Draw(sig_img)
    d.line([(10, 35), (40, 15), (70, 30), (100, 10), (140, 25)], fill=(0, 20, 140, 255), width=2)
    d.line([(25, 40), (60, 20), (90, 35)], fill=(0, 20, 140, 255), width=2)
    buf = io.BytesIO()
    sig_img.save(buf, format='PNG')
    page.insert_image(fitz.Rect(50, 672, 200, 712), stream=buf.getvalue())

    doc.save(str(filepath))
    doc.close()
    return filepath


def make_tampered_signature_off_zone_image(filename):
    """Tampering: Signature stamp pasted in header/body area (y=80) instead of footer."""
    filepath = DATASET_DIR / filename
    img = Image.new('RGB', (600, 500), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 600, 45], fill=(20, 40, 80))
    draw.text((25, 12), "BOARD RESOLUTION CERTIFICATE", fill=(255, 255, 255))
    draw.text((40, 70), "Company: Apex Energy Systems Inc", fill=(30, 40, 50))
    draw.text((40, 95), "[ANOMALOUS SIGNATURE PLACEMENT]", fill=(180, 50, 50))
    for i in range(15, 120, 12):
        draw.line([(i + 40, 110 + (i % 15)), (i + 55, 125 - (i % 10))], fill=(10, 30, 160), width=2)
    draw.line([(45, 128), (170, 128)], fill=(10, 30, 160), width=1)
    draw.text((40, 180), "Resolution: Approved allocation of capital expenditure.", fill=(30, 40, 50))
    draw.text((40, 220), "Date of Resolution: 2026-02-15", fill=(30, 40, 50))
    draw.text((40, 260), "Quorum: 5 of 5 voting directors present.", fill=(30, 40, 50))
    draw.rectangle([10, 10, 590, 490], outline=(200, 210, 220), width=2)
    img.save(str(filepath))
    return filepath


def make_tampered_producer_mismatch(filename):
    """Tampering: PDF metadata indicates third-party online PDF editor (Sejda / iLovePDF) and modified timestamp."""
    lines = [
        ("Invoice Number", "INV-2026-4401"),
        ("Counterparty", "Solas Wind Turbines"),
        ("Issue Date", "2026-03-01"),
        ("Due Date", "2026-04-01"),
        ("Total Amount", "$28,500.00")
    ]
    meta = {
        'creator': 'Sejda PDF Desktop Editor v7.5',
        'producer': 'Sejda PDF Engine (Linux)',
        'creationDate': 'D:20260301100000Z',
        'modDate': 'D:20260325141500Z'
    }
    return make_genuine_pdf(filename, "TAX INVOICE - EDITED METADATA", lines, metadata=meta)


def make_tampered_arithmetic_mismatch(filename):
    """Tampering: Subtotal + Tax arithmetic calculation does not match stated Grand Total."""
    lines = [
        ("Invoice Number", "INV-2026-5519"),
        ("Bill To", "Apex Offshore Holdings"),
        ("Issue Date", "2026-02-15"),
        ("Due Date", "2026-03-15"),
        ("Subtotal", "$3,500.00"),
        ("Tax", "$350.00"),
        ("Grand Total", "$14,850.00")
    ]
    return make_genuine_pdf(filename, "COMMERCIAL INVOICE - ARITHMETIC ANOMALY", lines)


def make_tampered_incremental_update(filename):
    """Tampering: PDF with post-creation incremental update revision appending new stream."""
    filepath = DATASET_DIR / filename
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 70), "SERVICE CONTRACT AMENDMENT", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.draw_line(fitz.Point(50, 85), fitz.Point(545, 85), color=(0.7, 0.7, 0.7), width=1)
    page.insert_text(fitz.Point(50, 120), "Contract: CON-2026-991", fontsize=10, fontname="helv")
    page.insert_text(fitz.Point(50, 150), "Original Retainer: $5,000.00", fontsize=10, fontname="helv")
    doc.save(str(filepath))
    doc.close()

    # Append valid incremental update revision with /Prev xref pointer
    with open(filepath, 'ab') as f:
        f.write(b"\n% Post-execution alteration\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 6 /Prev 1400 >>\nstartxref\n1850\n%%EOF\n")
    return filepath


def make_tampered_conflicting_totals_multipage(filename):
    """Tampering: Multi-page invoice with contradictory totals on page 1 vs page 2."""
    filepath = DATASET_DIR / filename
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(fitz.Point(50, 70), "EQUIPMENT SUPPLY INVOICE (Page 1 of 2)", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    p1.draw_line(fitz.Point(50, 85), fitz.Point(545, 85), color=(0.7, 0.7, 0.7), width=1)
    p1.insert_text(fitz.Point(50, 120), "Invoice Number: INV-2026-6632", fontsize=10, fontname="helv")
    p1.insert_text(fitz.Point(50, 150), "Issue Date: 2026-03-01", fontsize=10, fontname="helv")
    p1.insert_text(fitz.Point(50, 200), "Total Amount: $2,500.00", fontsize=10, fontname="helv")

    p2 = doc.new_page(width=595, height=842)
    p2.insert_text(fitz.Point(50, 70), "INVOICE SUMMARY SCHEDULE (Page 2 of 2)", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    p2.draw_line(fitz.Point(50, 85), fitz.Point(545, 85), color=(0.7, 0.7, 0.7), width=1)
    p2.insert_text(fitz.Point(50, 120), "Invoice Number: INV-2026-6632", fontsize=10, fontname="helv")
    p2.insert_text(fitz.Point(50, 200), "Grand Total Amount: $12,500.00", fontsize=10, fontname="helv")
    doc.save(str(filepath))
    doc.close()
    return filepath


def make_tampered_date_reversal(filename):
    """Tampering: Requisition order where payment due date precedes invoice issue date."""
    lines = [
        ("Invoice Number", "INV-2026-7788"),
        ("Vendor", "Kroll Heavy Industries"),
        ("Issue Date", "2026-05-20"),
        ("Payment Due Date", "2026-04-10"),
        ("Subtotal", "$8,200.00"),
        ("Total Amount", "$8,200.00")
    ]
    return make_genuine_pdf(filename, "TAX INVOICE - REVERSED SCHEDULE", lines)


def make_tampered_ela_disparity(filename):
    """Tampering: Receipt image with an inserted high-contrast price badge creating Laplacian / ELA disparity."""
    filepath = DATASET_DIR / filename
    img = Image.new('RGB', (600, 450), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    for y in range(0, 450, 15):
        draw.line([(0, y), (600, y)], fill=(240, 240, 240))
    draw.rectangle([0, 0, 600, 50], fill=(30, 45, 75))
    draw.text((30, 15), "HARDWARE DEPOT STORE RECEIPT", fill=(255, 255, 255))
    draw.text((40, 80), "Transaction: TX-2026-9921", fill=(30, 30, 30))
    draw.text((40, 110), "Date: 2026-02-10", fill=(30, 30, 30))
    draw.text((40, 140), "Terminal: POS-04", fill=(30, 30, 30))
    draw.text((40, 180), "Subtotal: $120.00", fill=(30, 30, 30))
    draw.rectangle([35, 220, 280, 270], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.text((45, 235), "MODIFIED TOTAL: $8,120.00", fill=(10, 10, 10))
    draw.rectangle([10, 10, 590, 440], outline=(200, 200, 200), width=2)
    img.save(str(filepath), quality=80)
    return filepath


# =====================================================================
# Main Dataset Builder Routine
# =====================================================================

def generate_all_samples():
    ensure_dataset_dir()
    labels = []

    print("[VEXORA Dataset Builder] Generating 15 Genuine Documents...")

    # 1. Genuine Documents (15)
    g1 = make_genuine_pdf("genuine_01_invoice.pdf", "TAX INVOICE", [
        ("Invoice Number", "INV-2026-001"),
        ("Bill To", "Apex Global Industries"),
        ("Issue Date", "2026-01-15"),
        ("Due Date", "2026-02-15"),
        ("Total Amount", "$1,250.00")
    ])
    labels.append({"filename": "genuine_01_invoice.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    make_genuine_pdf("genuine_01_matching_po.pdf", "PURCHASE ORDER - APEX GLOBAL", [
        ("Purchase Order", "PO-2026-001"),
        ("Invoice Reference", "INV-2026-001"),
        ("Vendor", "Apex Global Industries"),
        ("Order Date", "2026-01-15"),
        ("Total Amount", "$1,250.00")
    ])

    g2 = make_genuine_pdf("genuine_02_invoice.pdf", "TAX INVOICE", [
        ("Invoice Number", "INV-2026-002"),
        ("Bill To", "Kroll Logistics International"),
        ("Issue Date", "2026-02-10"),
        ("Due Date", "2026-03-10"),
        ("Total Amount", "$4,800.00")
    ])
    labels.append({"filename": "genuine_02_invoice.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g3 = make_genuine_pdf("genuine_03_bank_statement.pdf", "OFFICIAL BANK STATEMENT", [
        ("Account Name", "Apex Global Industries Operating Account"),
        ("Account Number", "ACCT-9921-8842"),
        ("Statement Period", "Jan 01, 2026 - Jan 31, 2026"),
        ("Opening Balance", "$45,000.00"),
        ("Wire Transfer Ref INV-2026-001", "$1,250.00"),
        ("Closing Balance", "$46,250.00")
    ])
    labels.append({"filename": "genuine_03_bank_statement.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g4 = make_genuine_pdf("genuine_04_bank_statement.pdf", "OFFICIAL BANK STATEMENT", [
        ("Account Name", "Kroll Logistics International"),
        ("Account Number", "ACCT-5512-1029"),
        ("Statement Period", "Feb 01, 2026 - Feb 28, 2026"),
        ("Opening Balance", "$112,000.00"),
        ("Closing Balance", "$116,800.00")
    ])
    labels.append({"filename": "genuine_04_bank_statement.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g5 = make_genuine_pdf("genuine_05_purchase_order.pdf", "PURCHASE ORDER", [
        ("PO Number", "PO-2026-881"),
        ("Vendor", "Precision Actuators Corp"),
        ("Deliver To", "Facility 7A"),
        ("Order Date", "2026-03-01"),
        ("Total Amount", "$3,500.00")
    ])
    labels.append({"filename": "genuine_05_purchase_order.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g6 = make_genuine_pdf("genuine_06_contract.pdf", "EMPLOYMENT AGREEMENT", [
        ("Employer", "Veridian Biometrics Inc"),
        ("Employee", "Elena Rostova"),
        ("Compensation", "$120,000.00 per annum"),
        ("Effective Date", "2026-01-01"),
        ("Scope of Work", "Forensic Data Intelligence")
    ])
    labels.append({"filename": "genuine_06_contract.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g7 = make_genuine_pdf("genuine_07_tax_return.pdf", "INTERNAL REVENUE SERVICE - FORM 1040", [
        ("Tax Year", "2025"),
        ("Tax Payer", "Marcus Vance"),
        ("Adjusted Gross Income", "$94,500.00"),
        ("Taxable Income", "$81,200.00"),
        ("Filing Status", "Single")
    ])
    labels.append({"filename": "genuine_07_tax_return.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g8 = make_genuine_image("genuine_08_receipt.png", "RETAIL SALES RECEIPT", [
        ("Store", "Metropolitan Lab Supplies"),
        ("Receipt #", "REC-8842"),
        ("Date", "2026-02-14"),
        ("Payment", "Corporate Visa Ending 4192"),
        ("Total", "$248.50")
    ])
    labels.append({"filename": "genuine_08_receipt.png", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g9 = make_genuine_image("genuine_09_id_card.png", "OFFICIAL IDENTITY BADGE", [
        ("Holder Name", "Dr. Alex Turner"),
        ("Badge ID", "VEX-782"),
        ("Role", "Senior Forensic Specialist"),
        ("Issue Date", "2025-06-01"),
        ("Expiration Date", "2028-06-01")
    ])
    labels.append({"filename": "genuine_09_id_card.png", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g10 = make_genuine_pdf("genuine_10_audit_report.pdf", "FINANCIAL AUDIT OPINION", [
        ("Auditor", "Deloitte & Touche LLP"),
        ("Client", "Solas Renewable Energy"),
        ("Audit Opinion", "Unqualified Clean Opinion"),
        ("Reporting Period", "FY 2025"),
        ("Report Date", "2026-02-28")
    ])
    labels.append({"filename": "genuine_10_audit_report.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    # Phase 1 Additions: 5 New Diverse Genuine Documents
    g11 = make_genuine_pdf("genuine_11_consulting_invoice.pdf", "TAX INVOICE - IT CONSULTING", [
        ("Invoice Number", "INV-2026-9011"),
        ("Client", "Apex Global Industries"),
        ("Issue Date", "2026-02-01"),
        ("Due Date", "2026-03-01"),
        ("Subtotal", "$4,000.00"),
        ("Tax", "$400.00"),
        ("Grand Total", "$4,400.00")
    ])
    labels.append({"filename": "genuine_11_consulting_invoice.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g12 = make_genuine_pdf("genuine_12_equipment_lease.pdf", "COMMERCIAL EQUIPMENT LEASE", [
        ("Lessor", "Industrial Machinery Corp"),
        ("Lessee", "Apex Dynamics LLC"),
        ("Agreement Date", "2026-01-10"),
        ("Monthly Rate", "$2,200.00"),
        ("Term", "24 Months")
    ])
    labels.append({"filename": "genuine_12_equipment_lease.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g13 = make_genuine_pdf("genuine_13_payroll_summary.pdf", "PURCHASE REQUISITION VOUCHER", [
        ("PO Number", "REQ-2026-8812"),
        ("Department", "Forensic Data Analytics"),
        ("Vendor", "DataStream Software Ltd"),
        ("Order Date", "2026-02-15"),
        ("Total Amount", "$4,500.00")
    ])
    labels.append({"filename": "genuine_13_payroll_summary.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g14 = make_genuine_image("genuine_14_shipping_receipt.png", "EXPRESS COURIER RECEIPT", [
        ("Tracking #", "TRK-2026-88124"),
        ("Origin", "Logistics Facility 4B"),
        ("Destination", "Central Forensic Lab"),
        ("Date", "2026-02-20"),
        ("Amount", "$85.00")
    ])
    labels.append({"filename": "genuine_14_shipping_receipt.png", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    g15 = make_genuine_pdf("genuine_15_compliance_certificate.pdf", "ANNUAL COMPLIANCE CERTIFICATE", [
        ("Certificate ID", "CERT-2026-004"),
        ("Entity", "Veridian Biometrics Inc"),
        ("Effective Date", "2025-06-01"),
        ("Expiration Date", "2026-12-31"),
        ("Standard", "Digital Evidence Handling Guidelines")
    ])
    labels.append({"filename": "genuine_15_compliance_certificate.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    print("[VEXORA Dataset Builder] Generating 20 Tampered Documents...")

    # 2. Tampered Documents (20)
    t1 = make_tampered_font_shift("tampered_01_font_shift.pdf")
    labels.append({"filename": "tampered_01_font_shift.pdf", "is_tampered": 1, "tampering_type": "Font / Typographic Alteration", "expected_rules": "RULE-VIS-002,PDF-002"})

    t2 = make_tampered_whitebox_receipt("tampered_02_whitebox_patch.png")
    labels.append({"filename": "tampered_02_whitebox_patch.png", "is_tampered": 1, "tampering_type": "Whitebox Redaction / Patching", "expected_rules": "IMG-001"})

    t3 = make_tampered_reversed_dates("tampered_03_reversed_dates.pdf")
    labels.append({"filename": "tampered_03_reversed_dates.pdf", "is_tampered": 1, "tampering_type": "Reversed Date Timeline", "expected_rules": "RULE-CTX-003"})

    t4 = make_genuine_pdf("tampered_04_duplicate_inv_a.pdf", "TAX INVOICE - SUBMISSION A", [
        ("Invoice Number", "INV-DEMO-999"),
        ("Vendor", "Apex Technologies"),
        ("Issue Date", "2026-04-01"),
        ("Total Amount", "$5,000.00")
    ])
    labels.append({"filename": "tampered_04_duplicate_inv_a.pdf", "is_tampered": 1, "tampering_type": "Duplicate ID Pair A", "expected_rules": "RULE-CTX-004"})

    t5 = make_genuine_pdf("tampered_05_duplicate_inv_b.pdf", "TAX INVOICE - SUBMISSION B", [
        ("Invoice Number", "INV-DEMO-999"),
        ("Vendor", "Apex Offshore Holdings"),
        ("Issue Date", "2026-04-01"),
        ("Subtotal", "$5,000.00"),
        ("Total Amount", "$18,500.00")
    ])
    labels.append({"filename": "tampered_05_duplicate_inv_b.pdf", "is_tampered": 1, "tampering_type": "Altered Grand Total Arithmetic Mismatch", "expected_rules": "RULE-DOC-001"})

    meta_bank_edit = {
        'creator': 'iLovePDF Online Editor',
        'producer': 'iLovePDF Core Engine',
        'creationDate': 'D:20260401100000Z',
        'modDate': 'D:20260420150000Z'
    }
    t6 = make_genuine_pdf("tampered_06_bank_mismatch.pdf", "BANK STATEMENT - PAYMENT DISCREPANCY", [
        ("Account Name", "Apex Operating Account"),
        ("Wire Payment Ref INV-DEMO-999", "$5,000.00"),
        ("Statement Period", "Apr 01, 2026 - Apr 30, 2026"),
        ("Closing Balance", "$88,200.00")
    ], metadata=meta_bank_edit)
    labels.append({"filename": "tampered_06_bank_mismatch.pdf", "is_tampered": 1, "tampering_type": "Post-Issuance Modified Bank Statement", "expected_rules": "PDF-003"})

    t7 = make_tampered_photoshop_metadata("tampered_07_photoshop_meta.pdf")
    labels.append({"filename": "tampered_07_photoshop_meta.pdf", "is_tampered": 1, "tampering_type": "Disallowed Editing Software Metadata", "expected_rules": "PDF-003"})

    t8 = make_tampered_copymove_image("tampered_08_copymove_stamp.png")
    labels.append({"filename": "tampered_08_copymove_stamp.png", "is_tampered": 1, "tampering_type": "Copy-Move Stamp Duplication", "expected_rules": "IMG-003"})

    t9 = make_tampered_future_date("tampered_09_future_timeline.pdf")
    labels.append({"filename": "tampered_09_future_timeline.pdf", "is_tampered": 1, "tampering_type": "Futuristic Date Anomaly", "expected_rules": "RULE-CTX-001"})

    meta_divergent = {
        'creationDate': 'D:20200101100000Z',
        'modDate': 'D:20261102143000Z'
    }
    t10 = make_genuine_pdf("tampered_10_divergent_timestamps.pdf", "ARCHIVED SHAREHOLDERS MINUTES", [
        ("Meeting Date", "2020-01-01"),
        ("Corporation", "Veridian Bio Technologies"),
        ("Secretary", "Marcus Vance"),
        ("Resolution", "Approved executive stock option plan.")
    ], metadata=meta_divergent)
    labels.append({"filename": "tampered_10_divergent_timestamps.pdf", "is_tampered": 1, "tampering_type": "Historical PDF Modification Divergence", "expected_rules": "RULE-CTX-005,PDF-001"})

    # Phase 1 Additions: 10 New Diverse Tampered Documents
    t11 = make_tampered_overwritten_text("tampered_11_overwritten_text.pdf")
    labels.append({"filename": "tampered_11_overwritten_text.pdf", "is_tampered": 1, "tampering_type": "Overwritten Text Patch", "expected_rules": "PDF-001,RULE-VIS-002"})

    t12 = make_tampered_font_size_baseline("tampered_12_line_font_outlier.pdf")
    labels.append({"filename": "tampered_12_line_font_outlier.pdf", "is_tampered": 1, "tampering_type": "Font Discrepancy & Baseline Shift", "expected_rules": "RULE-VIS-001,RULE-VIS-004"})

    t13 = make_tampered_pasted_signature_pdf("tampered_13_pasted_signature.pdf")
    labels.append({"filename": "tampered_13_pasted_signature.pdf", "is_tampered": 1, "tampering_type": "Pasted Signature Superimposed Over Text", "expected_rules": "PDF-004"})

    t14 = make_tampered_signature_off_zone_image("tampered_14_signature_off_zone.png")
    labels.append({"filename": "tampered_14_signature_off_zone.png", "is_tampered": 1, "tampering_type": "Signature Box Off Expected Zone", "expected_rules": "IMG-001"})

    t15 = make_tampered_producer_mismatch("tampered_15_producer_mismatch.pdf")
    labels.append({"filename": "tampered_15_producer_mismatch.pdf", "is_tampered": 1, "tampering_type": "Producer Software Mismatch", "expected_rules": "PDF-003"})

    t16 = make_tampered_arithmetic_mismatch("tampered_16_arithmetic_amount_change.pdf")
    labels.append({"filename": "tampered_16_arithmetic_amount_change.pdf", "is_tampered": 1, "tampering_type": "Arithmetic Line Item Calculation Mismatch", "expected_rules": "RULE-DOC-001"})

    t17 = make_tampered_incremental_update("tampered_17_incremental_update_tamper.pdf")
    labels.append({"filename": "tampered_17_incremental_update_tamper.pdf", "is_tampered": 1, "tampering_type": "Post-Execution Incremental Update", "expected_rules": "PDF-002"})

    t18 = make_tampered_conflicting_totals_multipage("tampered_18_conflicting_totals_multipage.pdf")
    labels.append({"filename": "tampered_18_conflicting_totals_multipage.pdf", "is_tampered": 1, "tampering_type": "Conflicting Grand Totals Multipage", "expected_rules": "RULE-DOC-004"})

    t19 = make_tampered_date_reversal("tampered_19_date_timeline_reversal.pdf")
    labels.append({"filename": "tampered_19_date_timeline_reversal.pdf", "is_tampered": 1, "tampering_type": "Payment Due Precedes Issue Date", "expected_rules": "RULE-CTX-003,RULE-DOC-002"})

    t20 = make_tampered_ela_disparity("tampered_20_ela_noise_disparity.png")
    labels.append({"filename": "tampered_20_ela_noise_disparity.png", "is_tampered": 1, "tampering_type": "Spliced Price Badge ELA Disparity", "expected_rules": "IMG-002"})

    # Write labels.csv
    csv_path = DATASET_DIR / 'labels.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "is_tampered", "tampering_type", "expected_rules"])
        writer.writeheader()
        writer.writerows(labels)

    print(f"[VEXORA Dataset Builder] Successfully generated {len(labels)} sample files in {DATASET_DIR}")
    print(f"[VEXORA Dataset Builder] Ground truth saved to {csv_path}")

    # Write cases.csv for cross-document case-level evaluation
    cases = [
        {
            "case_id": "case_01_duplicate_invoices",
            "title": "Duplicate Invoice Submissions with Conflicting Totals",
            "filenames": "tampered_04_duplicate_inv_a.pdf;tampered_05_duplicate_inv_b.pdf",
            "is_tampered": 1,
            "tampering_type": "Primary Monetary Value / Entity Substitution",
            "expected_conflicts": "Primary Monetary Value,Vendor/Party Entity"
        },
        {
            "case_id": "case_02_bank_mismatch",
            "title": "Invoice vs Bank Settlement Mismatch",
            "filenames": "tampered_05_duplicate_inv_b.pdf;tampered_06_bank_mismatch.pdf",
            "is_tampered": 1,
            "tampering_type": "Primary Monetary Value / Payment Discrepancy",
            "expected_conflicts": "Primary Monetary Value"
        },
        {
            "case_id": "case_03_clean_procurement",
            "title": "Synchronized Genuine Procurement Records",
            "filenames": "genuine_01_invoice.pdf;genuine_01_matching_po.pdf",
            "is_tampered": 0,
            "tampering_type": "None",
            "expected_conflicts": "None"
        }
    ]
    cases_csv_path = DATASET_DIR / 'cases.csv'
    with open(cases_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "title", "filenames", "is_tampered", "tampering_type", "expected_conflicts"])
        writer.writeheader()
        writer.writerows(cases)
    print(f"[VEXORA Dataset Builder] Case evaluation scenarios saved to {cases_csv_path}")
    return labels


if __name__ == '__main__':
    generate_all_samples()
