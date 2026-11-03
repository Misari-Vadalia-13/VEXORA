"""
VEXORA — Demonstration Dataset Generator (Phase G)
Programmatically generates a benchmark dataset consisting of:
- 10 Genuine Documents (invoices, bank statements, POs, contracts, receipts, IDs)
- 10 Tampered Documents (font shifts, white-box redactions, reversed dates, duplicate references,
  cross-document financial contradictions, editing tool metadata, copy-move cloning, future timelines)
- demo_dataset/labels.csv ground truth annotation table.
"""

import os
import csv
from pathlib import Path
import fitz  # PyMuPDF
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

    # Add realistic background texture / noise
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

    # Draw stamp pattern at pos 1
    stamp_pattern = [350, 250, 450, 350]
    draw.rectangle(stamp_pattern, outline=(180, 40, 40), width=3)
    draw.text((360, 290), "VERIFIED NOTARY", fill=(180, 40, 40))

    # Clone exact identical stamp pattern at pos 2 (Copy-Move)
    stamp_pattern_clone = [100, 250, 200, 350]
    draw.rectangle(stamp_pattern_clone, outline=(180, 40, 40), width=3)
    draw.text((110, 290), "VERIFIED NOTARY", fill=(180, 40, 40))

    img.save(str(filepath))
    return filepath


# =====================================================================
# Main Dataset Builder Routine
# =====================================================================

def generate_all_samples():
    ensure_dataset_dir()
    labels = []

    print("[VEXORA Dataset Builder] Generating 10 Genuine Documents...")

    # 1. Genuine Documents (10)
    g1 = make_genuine_pdf("genuine_01_invoice.pdf", "TAX INVOICE", [
        ("Invoice Number", "INV-2026-001"),
        ("Bill To", "Apex Global Industries"),
        ("Issue Date", "2026-01-15"),
        ("Due Date", "2026-02-15"),
        ("Total Amount", "$1,250.00")
    ])
    labels.append({"filename": "genuine_01_invoice.pdf", "is_tampered": 0, "tampering_type": "None", "expected_rules": "None"})

    # Phase J: Genuine Counterpart for cross-document clean evaluation (PO matching genuine_01_invoice.pdf)
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

    print("[VEXORA Dataset Builder] Generating 10 Tampered Documents...")

    # 2. Tampered Documents (10)
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
        ("Total Amount", "$18,500.00")
    ])
    labels.append({"filename": "tampered_05_duplicate_inv_b.pdf", "is_tampered": 1, "tampering_type": "Duplicate ID Pair B with Conflicting Total", "expected_rules": "RULE-CTX-004"})

    t6 = make_genuine_pdf("tampered_06_bank_mismatch.pdf", "BANK STATEMENT - PAYMENT DISCREPANCY", [
        ("Account Name", "Apex Operating Account"),
        ("Wire Payment Ref INV-DEMO-999", "$5,000.00"),
        ("Statement Period", "Apr 01, 2026 - Apr 30, 2026"),
        ("Closing Balance", "$88,200.00")
    ])
    labels.append({"filename": "tampered_06_bank_mismatch.pdf", "is_tampered": 1, "tampering_type": "Cross-Document Bank Payment Conflict", "expected_rules": "RULE-CTX-004"})

    t7 = make_tampered_photoshop_metadata("tampered_07_photoshop_meta.pdf")
    labels.append({"filename": "tampered_07_photoshop_meta.pdf", "is_tampered": 1, "tampering_type": "Disallowed Editing Software Metadata", "expected_rules": "PDF-003"})

    t8 = make_tampered_copymove_image("tampered_08_copymove_stamp.png")
    labels.append({"filename": "tampered_08_copymove_stamp.png", "is_tampered": 1, "tampering_type": "Copy-Move Stamp Duplication", "expected_rules": "IMG-003"})

    t9 = make_tampered_future_date("tampered_09_future_timeline.pdf")
    labels.append({"filename": "tampered_09_future_timeline.pdf", "is_tampered": 1, "tampering_type": "Futuristic Date Anomaly", "expected_rules": "RULE-CTX-001"})

    # Tampered 10: PDF with incremental update modification timestamp divergence
    meta_divergent = {
        'creationDate': 'D:20200101100000Z',
        'modDate': 'D:20261102143000Z'  # 6-year divergence
    }
    t10 = make_genuine_pdf("tampered_10_divergent_timestamps.pdf", "ARCHIVED SHAREHOLDERS MINUTES", [
        ("Meeting Date", "2020-01-01"),
        ("Corporation", "Veridian Bio Technologies"),
        ("Secretary", "Marcus Vance"),
        ("Resolution", "Approved executive stock option plan.")
    ], metadata=meta_divergent)
    labels.append({"filename": "tampered_10_divergent_timestamps.pdf", "is_tampered": 1, "tampering_type": "Historical PDF Modification Divergence", "expected_rules": "RULE-CTX-005,PDF-001"})

    # Write labels.csv
    csv_path = DATASET_DIR / 'labels.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "is_tampered", "tampering_type", "expected_rules"])
        writer.writeheader()
        writer.writerows(labels)

    print(f"[VEXORA Dataset Builder] Successfully generated {len(labels)} sample files in {DATASET_DIR}")
    print(f"[VEXORA Dataset Builder] Ground truth saved to {csv_path}")

    # Write cases.csv for cross-document case-level evaluation (Phase J)
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
