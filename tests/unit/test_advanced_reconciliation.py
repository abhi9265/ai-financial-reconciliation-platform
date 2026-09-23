from decimal import Decimal

from reconciliation_platform.evaluation.adversarial import generate_adversarial_cases
from reconciliation_platform.reconciliation.advanced import reconcile_advanced


def test_one_to_many_payment_is_reconciled():
    cases = generate_adversarial_cases(seed=7, cases=10, one_to_many_rate=1.0, partial_rate=0.0)
    case = cases[0]
    result = reconcile_advanced([case.bank], list(case.invoices))
    assert result[0].relationship == "ONE_TO_MANY"
    assert result[0].status == "MATCHED"
    assert result[0].counterparty_record_ids == case.expected_invoice_ids


def test_partial_payment_does_not_consume_invoice():
    cases = generate_adversarial_cases(seed=9, cases=10, one_to_many_rate=0.0, partial_rate=1.0)
    case = cases[0]
    result = reconcile_advanced([case.bank], list(case.invoices))
    assert result[0].relationship == "PARTIAL_PAYMENT"
    assert result[0].status == "MATCHED"
    assert result[0].amount_applied == case.bank.amount
    assert result[0].amount_remaining > Decimal("0")


def test_adversarial_generator_is_reproducible():
    left = generate_adversarial_cases(seed=42, cases=25)
    right = generate_adversarial_cases(seed=42, cases=25)
    assert [(x.bank.source_record_id, x.relationship, x.expected_invoice_ids) for x in left] == [
        (x.bank.source_record_id, x.relationship, x.expected_invoice_ids) for x in right
    ]


def test_one_to_many_three_invoice_path():
    cases = generate_adversarial_cases(seed=12, cases=1, one_to_many_rate=1.0, partial_rate=0.0)
    case = cases[0]
    first, second = case.invoices
    third_amount = (case.bank.amount * Decimal("0.10")).quantize(Decimal("0.01"))
    first_amount = (case.bank.amount * Decimal("0.30")).quantize(Decimal("0.01"))
    second_amount = case.bank.amount - first_amount - third_amount
    third = first.model_copy(
        update={
            "source_record_id": "THIRD",
            "transaction_id": "THIRD",
            "amount": third_amount,
        }
    )
    first = first.model_copy(update={"amount": first_amount})
    second = second.model_copy(update={"amount": second_amount})
    result = reconcile_advanced([case.bank], [first, second, third])
    assert result[0].status == "MATCHED"
    assert result[0].relationship == "ONE_TO_MANY"
    assert set(result[0].counterparty_record_ids) == {first.source_record_id, second.source_record_id, third.source_record_id}
