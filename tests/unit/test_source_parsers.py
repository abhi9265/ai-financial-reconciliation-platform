from reconciliation_platform.ingestion.parsers import SourceParseError, parse_source
from reconciliation_platform.models.canonical_transaction import SourceSystem


def test_bank_parser_maps_common_export_headers():
    content = (
        "Txn ID,Date,Withdrawal,Deposit,Description,Ref No,Account No\n"
        "B-1,2026-08-01,1250.00,,ACME SUPPLIES,INV-1,XXXX1234\n"
    ).encode()

    parsed = parse_source(
        content,
        source_system=SourceSystem.BANK,
        filename="bank-statement.csv",
    )

    assert parsed.columns == (
        "transaction_id",
        "transaction_date",
        "debit",
        "credit",
        "narration",
        "reference",
        "account_number",
        "amount",
    )
    assert parsed.rows[0]["transaction_id"] == "B-1"
    assert parsed.rows[0]["debit"] == "1250.00"
    assert parsed.rows[0]["amount"] == "1250.00"


def test_purchase_parser_maps_vendor_export_headers():
    content = (
        "Invoice No,Bill Date,Supplier Name,Supplier GSTIN,Taxable Amount,CGST,SGST,IGST,Invoice Total,Record ID\n"
        "INV-1,2026-08-01,ACME,24ABCDE1234F1Z5,1000,90,90,0,1180,R-1\n"
    ).encode()

    parsed = parse_source(
        content,
        source_system=SourceSystem.PURCHASE_REGISTER,
        filename="purchases.csv",
    )

    assert parsed.rows[0]["invoice_number"] == "INV-1"
    assert parsed.rows[0]["vendor_name"] == "ACME"
    assert parsed.rows[0]["gstin"] == "24ABCDE1234F1Z5"
    assert parsed.rows[0]["total"] == "1180"


def test_gst_json_parser_accepts_invoice_list():
    content = b'''{
      "invoices": [
        {
          "invoice_number": "INV-1",
          "invoice_date": "2026-08-01",
          "amount": 1180,
          "supplier_gstin": "24ABCDE1234F1Z5",
          "source_record_id": "GST-1"
        }
      ]
    }'''

    parsed = parse_source(
        content,
        source_system=SourceSystem.GST,
        filename="gst.json",
    )

    assert parsed.columns == (
        "invoice_number",
        "invoice_date",
        "amount",
        "counterparty_gstin",
        "source_record_id",
    )
    assert parsed.rows[0]["amount"] == 1180


def test_parser_rejects_unknown_format():
    try:
        parse_source(
            b"hello",
            source_system=SourceSystem.BANK,
            filename="bank.xlsx",
        )
    except SourceParseError as exc:
        assert "unsupported file format" in str(exc)
    else:
        raise AssertionError("expected unsupported format error")


def test_parser_rejects_duplicate_mapped_columns():
    content = (
        "Txn ID,Transaction ID,Date,Debit,Credit,Amount,Narration,Reference,Account Number\n"
        "B-1,B-1,2026-08-01,100,,,ACME,INV-1,XXXX1234\n"
    ).encode()

    try:
        parse_source(
            content,
            source_system=SourceSystem.BANK,
            filename="bank.csv",
        )
    except SourceParseError as exc:
        assert "duplicate canonical columns" in str(exc)
    else:
        raise AssertionError("expected duplicate-header failure")


def test_tally_parser_maps_common_ledger_export_headers():
    content = (
        "Date,Amount,Type,Record ID,Reference No,Ledger,Narration,Debit,Credit\n"
        "2026-08-01,1250,PAYMENT,T-1,INV-1,ACME SUPPLIES,Office purchase,1250,\n"
    ).encode()

    parsed = parse_source(
        content,
        source_system=SourceSystem.TALLY,
        filename="tally-ledger.csv",
    )

    assert parsed.rows[0]["source_record_id"] == "T-1"
    assert parsed.rows[0]["transaction_type"] == "PAYMENT"
    assert parsed.rows[0]["account_name"] == "ACME SUPPLIES"
