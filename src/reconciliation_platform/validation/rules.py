"""Business-level data quality rules."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction, SourceSystem

@dataclass(frozen=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    source_record_id: str

def validate_transaction(transaction: CanonicalTransaction) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    if transaction.source_system is SourceSystem.BANK:
        if transaction.description and len(transaction.description) < 3:
            issues.append(QualityIssue("WARNING", "SHORT_DESCRIPTION", "Bank narration is unusually short", transaction.source_record_id))
    if transaction.taxable_amount is not None and transaction.total_tax is not None:
        expected = transaction.taxable_amount + transaction.total_tax
        if abs(expected - transaction.amount) > Decimal("0.02"):
            issues.append(QualityIssue("ERROR", "TAX_TOTAL_MISMATCH", "taxable amount plus tax does not equal total amount", transaction.source_record_id))
    return issues

def validate_transactions(transactions: list[CanonicalTransaction]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for tx in transactions:
        issues.extend(validate_transaction(tx))
    seen: set[str] = set()
    for tx in transactions:
        if tx.record_hash in seen:
            issues.append(QualityIssue("WARNING", "DUPLICATE_RECORD_HASH", "duplicate canonical business record", tx.source_record_id))
        seen.add(tx.record_hash)
    return issues
