"""
VEXORA — Benchmark Dataset Generator
Programmatically synthesizes 10 genuine and 10 tampered documents for empirical evaluation:
- 10 Genuine: Authentic invoices, bank statements, payslips, POs, and receipts.
- 10 Tampered: Whiteout masking, incremental %%EOF saves, Canva metadata, arithmetic mismatch,
  font injection, conflicting currencies, overlapping text, and chronological inversion.
"""

import os
import json
from pathlib import Path
import pymupdf

DATASET_DIR = Path(__file__).resolve().parent / "benchmark_dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

def create_genuine_docs():
    """Generates 10 pristine, authentic documents without forensic anomalies."""
    genuine_files = []

    # 1. GEN-001: Acme Consulting Invoice
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "ACME CONSULTING SERVICES LLC", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    p.insert_text((50, 90), "Invoice Number: INV-2026-101\nDate: 15-Jan-2026\nDue Date: 15-Feb-2026", fontsize=10, fontname="helv")
    p.insert_text((50, 160), "Billed To: Global Logistics Corp\nAddress: 450 Enterprise Way, Suite 200", fontsize=10, fontname="helv")
    p.insert_text((50, 230), "Itemized Services:\n1. Cloud Architecture Review    $1,200.00\n2. Security Compliance Audit    $2,400.00", fontsize=10, fontname="helv")
    p.insert_text((50, 310), "Subtotal: $3,600.00\nTax (10%): $360.00\nTotal Amount Due: $3,960.00", fontsize=11, fontname="helv")
    path1 = DATASET_DIR / "GEN-001-invoice-acme.pdf"
    doc.save(str(path1))
    doc.close()
    genuine_files.append("GEN-001-invoice-acme.pdf")

    # 2. GEN-002: Chase Bank Monthly Statement
    doc = pymupdf.open()
    doc.set_metadata({'producer': 'ReportLab 3.5.2', 'creator': 'Bank Statement Engine v4'})
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "CHASE COMMERCIAL BANKING", fontsize=15, fontname="times-bold", color=(0, 0.2, 0.5))
    p.insert_text((50, 90), "Account Statement • Period: 01-Jan-2026 to 31-Jan-2026\nAccount Number: 8492019482", fontsize=10, fontname="times-roman")
    p.insert_text((50, 140), "Opening Balance: $45,200.00\nDeposits: $12,400.00\nWithdrawals: $8,150.00\nClosing Balance: $49,450.00", fontsize=10, fontname="times-roman")
    path2 = DATASET_DIR / "GEN-002-bank-statement-chase.pdf"
    doc.save(str(path2))
    doc.close()
    genuine_files.append("GEN-002-bank-statement-chase.pdf")

    # 3. GEN-003: Salary Slip Aarav
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "VERITAS ENTERPRISES — PAYSLIP", fontsize=14, fontname="courier-bold")
    p.insert_text((50, 90), "Employee Name: Aarav Mehta\nDesignation: Senior Architect\nPay Period: January 2026", fontsize=10, fontname="courier")
    p.insert_text((50, 150), "Basic Pay: $4,500.00\nAllowances: $1,200.00\nDeductions: $700.00\nNet Disbursed: $5,000.00", fontsize=10, fontname="courier")
    path3 = DATASET_DIR / "GEN-003-payslip-aarav.pdf"
    doc.save(str(path3))
    doc.close()
    genuine_files.append("GEN-003-payslip-aarav.pdf")

    # 4. GEN-004: Tax Assessment Receipt
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "INTERNAL REVENUE DEPARTMENT", fontsize=14, fontname="helv", color=(0.2, 0.2, 0.2))
    p.insert_text((50, 90), "Tax Compliance Acknowledgment • Assessment Year: 2025-2026\nPAN: ABCDE1234F\nStatus: Paid in Full ($2,150.00)", fontsize=10, fontname="helv")
    path4 = DATASET_DIR / "GEN-004-tax-receipt-irs.pdf"
    doc.save(str(path4))
    doc.close()
    genuine_files.append("GEN-004-tax-receipt-irs.pdf")

    # 5. GEN-005: Supply Purchase Order
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "PURCHASE ORDER: PO-2026-781", fontsize=14, fontname="helv")
    p.insert_text((50, 90), "Vendor: Silicon Depot Inc\nOrder Date: 10-Jan-2026\nDelivery Date: 20-Jan-2026", fontsize=10, fontname="helv")
    p.insert_text((50, 150), "Line Items:\n10x High-Speed Optical Cable @ $45.00 = $450.00\nTotal Order Value: $450.00", fontsize=10, fontname="helv")
    path5 = DATASET_DIR / "GEN-005-purchase-order-supply.pdf"
    doc.save(str(path5))
    doc.close()
    genuine_files.append("GEN-005-purchase-order-supply.pdf")

    # 6. GEN-006: Consulting Services Agreement
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "PROFESSIONAL SERVICES MASTER AGREEMENT", fontsize=13, fontname="times-bold")
    p.insert_text((50, 90), "Dated: 05-Jan-2026\nBetween Vertex Corp and Apex Analytics", fontsize=10, fontname="times-roman")
    p.insert_text((50, 200), "Authorized Signatory: David Vance\nSignature: Signed digitally via DocuSign", fontsize=10, fontname="times-roman")
    path6 = DATASET_DIR / "GEN-006-consulting-contract.pdf"
    doc.save(str(path6))
    doc.close()
    genuine_files.append("GEN-006-consulting-contract.pdf")

    # 7. GEN-007: Utility Electric Invoice
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "METROPOLITAN ELECTRIC UTILITY", fontsize=14, fontname="helv")
    p.insert_text((50, 90), "Account ID: ELEC-99210\nBilling Cycle: 01-Dec-2025 to 31-Dec-2025\nTotal Due: $320.50", fontsize=10, fontname="helv")
    path7 = DATASET_DIR / "GEN-007-utility-bill-electric.pdf"
    doc.save(str(path7))
    doc.close()
    genuine_files.append("GEN-007-utility-bill-electric.pdf")

    # 8. GEN-008: Commercial Lease Agreement
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "COMMERCIAL REAL ESTATE LEASE", fontsize=14, fontname="helv")
    p.insert_text((50, 90), "Premises: 120 Innovation Parkway\nMonthly Rent: $5,500.00\nTerm: 12 Months", fontsize=10, fontname="helv")
    path8 = DATASET_DIR / "GEN-008-lease-agreement.pdf"
    doc.save(str(path8))
    doc.close()
    genuine_files.append("GEN-008-lease-agreement.pdf")

    # 9. GEN-009: Medical Pharmacy Receipt
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "CENTRAL PHARMACEUTICAL CARE", fontsize=14, fontname="helv")
    p.insert_text((50, 90), "Receipt Number: RX-4421\nPatient: Elena Rostova\nTotal Charged: $85.00", fontsize=10, fontname="helv")
    path9 = DATASET_DIR / "GEN-009-medical-reimbursement.pdf"
    doc.save(str(path9))
    doc.close()
    genuine_files.append("GEN-009-medical-reimbursement.pdf")

    # 10. GEN-010: Hardware Retail Cash Receipt
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "FASTENERS & TOOLS SUPPLY CO.", fontsize=14, fontname="courier-bold")
    p.insert_text((50, 90), "Terminal #04\nCash Transaction: $142.80\nTax Included: $12.80", fontsize=10, fontname="courier")
    path10 = DATASET_DIR / "GEN-010-vendor-receipt-hardware.pdf"
    doc.save(str(path10))
    doc.close()
    genuine_files.append("GEN-010-vendor-receipt-hardware.pdf")

    return genuine_files

def create_tampered_docs():
    """Generates 10 tampered documents incorporating specific forensic anomalies."""
    tampered_files = []

    # 1. TAM-001: Covert White Rectangle Masking (PDF-R101)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "OFFICIAL BILLING RECORD — TAMPERED VIA WHITEOUT", fontsize=14, fontname="helv")
    p.insert_text((50, 120), "Subtotal Amount: $4,500.00", fontsize=11, fontname="helv")
    # Draw an opaque white rectangle directly over the text span
    p.draw_rect(pymupdf.Rect(45, 110, 250, 135), color=None, fill=(1.0, 1.0, 1.0))
    # Write new text over white rectangle
    p.insert_text((50, 120), "Subtotal Amount: $9,500.00", fontsize=11, fontname="helv")
    path1 = DATASET_DIR / "TAM-001-whiteout-invoice.pdf"
    doc.save(str(path1))
    doc.close()
    tampered_files.append("TAM-001-whiteout-invoice.pdf")

    # 2. TAM-002: Incremental Save (Multiple %%EOF) (PDF-R102)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "FINANCIAL STATEMENT — POST-CREATION INCREMENTAL SAVE", fontsize=14, fontname="helv")
    p.insert_text((50, 120), "Initial Balance: $10,000.00", fontsize=11, fontname="helv")
    path2 = DATASET_DIR / "TAM-002-incremental-save-bank.pdf"
    doc.save(str(path2))
    doc.close()
    # Append incremental revision with secondary %%EOF
    with open(path2, 'ab') as f:
        f.write(b"\n% Incremental revision edit appended post-signing\n")
        f.write(b"4 0 obj\n<< /Type /Annot /Subtype /Text >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 5 >>\nstartxref\n500\n%%EOF\n")
    tampered_files.append("TAM-002-incremental-save-bank.pdf")

    # 3. TAM-003: Producer Software Mismatch (Canva on Official Tax Form) (PDF-R103)
    doc = pymupdf.open()
    doc.set_metadata({'producer': 'Canva PDF Generator v2.4', 'creator': 'Canva Design Cloud'})
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "STATE DEPARTMENT OF REVENUE — OFFICIAL TAX ASSESSMENT", fontsize=14, fontname="helv")
    p.insert_text((50, 120), "Tax Exemption Certificate #TX-9901\nDeclared Annual Turnover: $2,500,000.00", fontsize=11, fontname="helv")
    path3 = DATASET_DIR / "TAM-003-canva-tax-receipt.pdf"
    doc.save(str(path3))
    doc.close()
    tampered_files.append("TAM-003-canva-tax-receipt.pdf")

    # 4. TAM-004: Contextual Arithmetic Discrepancy (LLM-CTX-101)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "COMMERCIAL INVOICE — ARITHMETIC RECONCILIATION DISCREPANCY", fontsize=13, fontname="helv")
    p.insert_text((50, 90), "Invoice Number: INV-9902\nDate: 04-Feb-2026", fontsize=10, fontname="helv")
    p.insert_text((50, 140), "Line Items:\nSecurity Firewall License     1  $800.00   $800.00\nEndpoint Protection Package   1  $650.00   $650.00", fontsize=10, fontname="helv")
    p.insert_text((50, 220), "Subtotal: $1,450.00\nTax: $0.00\nTotal Amount Due: $3,950.00", fontsize=11, fontname="helv")
    path4 = DATASET_DIR / "TAM-004-arithmetic-mismatch-invoice.pdf"
    doc.save(str(path4))
    doc.close()
    tampered_files.append("TAM-004-arithmetic-mismatch-invoice.pdf")

    # 5. TAM-005: Typographic Font Overwrite (RULE-VIS-001)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "EMPLOYEE EARNINGS STATEMENT", fontsize=14, fontname="courier-bold")
    p.insert_text((50, 90), "Employee: Rahul Sen\nDesignation: Analyst\nDepartment: Operations", fontsize=10, fontname="courier")
    p.insert_text((50, 150), "Standard Monthly Salary Rate: ", fontsize=10, fontname="courier")
    # Insert modified total in Arial (diverging font)
    p.insert_text((260, 150), "$18,500.00", fontsize=13, fontname="helv", color=(0.8, 0, 0))
    path5 = DATASET_DIR / "TAM-005-font-overwrite-salary.pdf"
    doc.save(str(path5))
    doc.close()
    tampered_files.append("TAM-005-font-overwrite-salary.pdf")

    # 6. TAM-006: Conflicting Currencies (RULE-CTX-004)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "INTERNATIONAL BILLING STATEMENT — CONFLICTING CURRENCIES", fontsize=13, fontname="helv")
    p.insert_text((50, 90), "Invoice Ref: INV-7721\nIssuer: EuroTrans Logistics", fontsize=10, fontname="helv")
    p.insert_text((50, 150), "Line Item: Freight Container Handling   $4,200.00\nCustoms Clearance Handling Fees        EUR 3,800.00", fontsize=10, fontname="helv")
    p.insert_text((50, 220), "Total Payable: $8,000.00", fontsize=11, fontname="helv")
    path6 = DATASET_DIR / "TAM-006-conflicting-currencies.pdf"
    doc.save(str(path6))
    doc.close()
    tampered_files.append("TAM-006-conflicting-currencies.pdf")

    # 7. TAM-007: Overlapping Text Elements (RULE-VIS-002)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "PURCHASE VOUCHER — DOUBLE STAMP OVERPRINT", fontsize=14, fontname="helv")
    p.insert_text((50, 120), "Approved Quantity: 50 Units Total", fontsize=11, fontname="helv")
    # Duplicate overprint at same coordinate
    p.insert_text((52, 121), "Approved Quantity: 950 Units Total", fontsize=11, fontname="helv")
    path7 = DATASET_DIR / "TAM-007-overlapping-text-po.pdf"
    doc.save(str(path7))
    doc.close()
    tampered_files.append("TAM-007-overlapping-text-po.pdf")

    # 8. TAM-008: Chronological Timeline Inversion (RULE-CTX-003)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "INVOICE WITH INVERTED PAYMENT DUE DATE", fontsize=14, fontname="helv")
    p.insert_text((50, 90), "Invoice Number: INV-8812", fontsize=10, fontname="helv")
    p.insert_text((50, 120), "Issue Date: 15-Jun-2026", fontsize=10, fontname="helv")
    p.insert_text((50, 150), "Payment Due Date: 10-Jan-2024", fontsize=10, fontname="helv")
    p.insert_text((50, 200), "Total Amount: $1,250.00", fontsize=10, fontname="helv")
    path8 = DATASET_DIR / "TAM-008-chronological-inversion.pdf"
    doc.save(str(path8))
    doc.close()
    tampered_files.append("TAM-008-chronological-inversion.pdf")

    # 9. TAM-009: Out-of-Bounds Text Placement (RULE-VIS-003)
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "SECURITY AUDIT FORM — OUT OF PRINTABLE BOUNDS", fontsize=14, fontname="helv")
    # Draw text outside standard margins (e.g. at x=575 on a 595 width page)
    p.insert_text((572, 300), "Confidential Code Alteration Insertion", fontsize=8, fontname="helv")
    path9 = DATASET_DIR / "TAM-009-out-of-bounds-text.pdf"
    doc.save(str(path9))
    doc.close()
    tampered_files.append("TAM-009-out-of-bounds-text.pdf")

    # 10. TAM-010: Metadata vs Body Timestamp Mismatch (RULE-CTX-005)
    doc = pymupdf.open()
    # Metadata set to 2026, content claims 2017
    doc.set_metadata({'creationDate': 'D:20260301120000', 'modDate': 'D:20260301120000'})
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "HISTORICAL PARTNERSHIP AGREEMENT", fontsize=14, fontname="helv")
    p.insert_text((50, 90), "Agreement Date: 14-Aug-2017\nEffective Execution Date: 14-Aug-2017", fontsize=10, fontname="helv")
    p.insert_text((50, 150), "Initial Capital Commitment: $250,000.00", fontsize=10, fontname="helv")
    path10 = DATASET_DIR / "TAM-010-post-dated-metadata.pdf"
    doc.save(str(path10))
    doc.close()
    tampered_files.append("TAM-010-post-dated-metadata.pdf")

    return tampered_files

def main():
    print("[*] Generating VEXORA 20-File Benchmark Dataset...")
    gen = create_genuine_docs()
    tam = create_tampered_docs()

    ground_truth = []
    for f in gen:
        ground_truth.append({
            'filename': f,
            'ground_truth': 'genuine',
            'expected_tampered': False,
            'expected_anomaly_rule': None,
            'description': 'Clean baseline document without alterations.'
        })

    tam_map = {
        'TAM-001-whiteout-invoice.pdf': ('PDF-R101', 'Opaque white rectangle masking over subtotal text.'),
        'TAM-002-incremental-save-bank.pdf': ('PDF-R102', 'Multiple %%EOF markers indicating post-creation revision edit.'),
        'TAM-003-canva-tax-receipt.pdf': ('PDF-R103', 'Official tax assessment generated via Canva consumer editing software.'),
        'TAM-004-arithmetic-mismatch-invoice.pdf': ('LLM-CTX-101', 'Line items sum to $1,450.00 but stated total is manipulated to $3,950.00.'),
        'TAM-005-font-overwrite-salary.pdf': ('RULE-VIS-001', 'Net salary figure typed in Arial Bold 13pt on Courier template.'),
        'TAM-006-conflicting-currencies.pdf': ('RULE-CTX-004', 'Conflicting $ and € currencies inside single invoice.'),
        'TAM-007-overlapping-text-po.pdf': ('RULE-VIS-002', 'Overlapping text blocks at identical coordinates.'),
        'TAM-008-chronological-inversion.pdf': ('RULE-CTX-003', 'Invoice date 2026 is chronologically after payment due date 2024.'),
        'TAM-009-out-of-bounds-text.pdf': ('RULE-VIS-003', 'Text placed outside printable boundary margins.'),
        'TAM-010-post-dated-metadata.pdf': ('RULE-CTX-005', 'Body claims 2017 while PDF creation timestamp is 2026.')
    }

    for f in tam:
        rule, desc = tam_map.get(f, ('ANOMALY', 'Tampered document'))
        ground_truth.append({
            'filename': f,
            'ground_truth': 'tampered',
            'expected_tampered': True,
            'expected_anomaly_rule': rule,
            'description': desc
        })

    gt_path = DATASET_DIR.parent / "ground_truth.json"
    with open(gt_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2)

    print(f"[✓] Created {len(gen)} genuine documents.")
    print(f"[✓] Created {len(tam)} tampered documents.")
    print(f"[✓] Saved ground truth to {gt_path}")

if __name__ == '__main__':
    main()
