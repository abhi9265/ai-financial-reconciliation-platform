"""Generate the deterministic seed dataset used by the repository."""
from __future__ import annotations
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20260919
ROWS = 100
OUT = Path("data/synthetic/seed")
VENDORS = [
    ("Apex Office Solutions", "24ABCDE1234F1Z5"),
    ("Bharat Cloud Services", "27BCDEF2345G1Z6"),
    ("Cedar Industrial Supplies", "29CDEFG3456H1Z7"),
    ("Delta Business Systems", "07DEFGH4567J1Z8"),
    ("Evergreen Packaging", "06EFGHI5678K1Z9"),
]

def main() -> None:
    rng = random.Random(SEED)
    start = date(2026, 7, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    banks, invoices, truth = [], [], []

    for i in range(1, ROWS + 1):
        vendor, gstin = VENDORS[(i - 1) % len(VENDORS)]
        amount = round(rng.uniform(850, 95000), 2)
        tx_date = start + timedelta(days=rng.randint(0, 30))
        invoice_no = f"INV-26-{i:05d}"
        bank_id = f"BANK-{i:05d}"
        invoice_id = f"INVREC-{i:05d}"

        banks.append({
            "transaction_id": bank_id, "transaction_date": tx_date.isoformat(),
            "value_date": tx_date.isoformat(), "debit": f"{amount:.2f}",
            "credit": "", "amount": f"{amount:.2f}", "narration": vendor,
            "reference": invoice_no, "account_number": "XXXXXX1234",
        })
        taxable = round(amount / 1.18, 2)
        tax = round(amount - taxable, 2)
        invoices.append({
            "invoice_record_id": invoice_id, "invoice_number": invoice_no,
            "invoice_date": tx_date.isoformat(), "vendor_name": vendor,
            "gstin": gstin, "taxable_value": f"{taxable:.2f}",
            "cgst": f"{tax/2:.2f}", "sgst": f"{tax/2:.2f}",
            "igst": "0.00", "total": f"{amount:.2f}",
        })
        truth.append({
            "bank_transaction_id": bank_id, "invoice_record_id": invoice_id,
            "relationship": "MATCH", "defect_type": "",
        })

    for i in range(0, 10):
        banks[i]["narration"] = banks[i]["narration"].replace("Solutions", "Solns")
        truth[i]["defect_type"] = "VENDOR_NAME_VARIATION"
    for i in range(10, 15):
        invoices[i]["invoice_date"] = (date.fromisoformat(invoices[i]["invoice_date"]) - timedelta(days=2)).isoformat()
        truth[i]["defect_type"] = "DATE_DIFFERENCE"
    for i in range(15, 20):
        changed = float(banks[i]["amount"]) + 1250.00
        banks[i]["amount"] = f"{changed:.2f}"
        banks[i]["debit"] = f"{changed:.2f}"
        truth[i]["relationship"] = "UNMATCHED"
        truth[i]["defect_type"] = "AMOUNT_MISMATCH"
    for i in range(20, 25):
        invoices[i] = None
        truth[i]["relationship"] = "UNMATCHED"
        truth[i]["defect_type"] = "MISSING_INVOICE"

    invoices = [row for row in invoices if row is not None]

    def write(name: str, rows: list[dict]) -> None:
        with (OUT / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    write("bank_transactions.csv", banks)
    write("purchase_invoices.csv", invoices)
    write("ground_truth.csv", truth)

if __name__ == "__main__":
    main()
