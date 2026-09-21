# Adversarial Reconciliation Benchmark

## Purpose

The original seed benchmark is intentionally simple and remains useful as a regression
test. This benchmark adds deliberately difficult financial reconciliation cases so the
matching engine is evaluated against failure modes that occur in real workflows.

The benchmark does **not** claim production accuracy. It measures the current implementation
against generated ground truth.

## Cases

The generator can produce:

- exact one-to-one matches
- reference/amount mismatches that should escalate
- vendor-name variants
- date shifts
- one payment covering multiple invoices
- partial payments that must not prematurely consume an invoice
- ambiguous candidates

Ground truth is generated with the case rather than inferred from the engine output.

## Complex matching contract

### One-to-many

A payment may reconcile against a bounded combination of up to three invoices when:

1. all records are transaction-type compatible;
2. the candidate set survives blocking;
3. the invoice amounts sum to the payment within the configured tolerance.

### Partial payment

A payment can be allocated against a uniquely identified invoice without marking
the invoice as fully consumed. The remaining balance is returned explicitly.

This preserves the state required for subsequent payments.

## Candidate blocking

The expensive matcher does not compare every bank transaction with every invoice.

Candidates are first reduced using:

- date window
- amount bucket
- normalized counterparty name
- shared counterparty tokens

The blocking layer is intentionally permissive. It may admit extra candidates, but it
should not exclude candidates that satisfy the configured matching window.

## Running

~~~bash
python scripts/run_adversarial_benchmark.py --cases 250 --seed 42
~~~

For a scale run:

~~~bash
python scripts/run_adversarial_benchmark.py --cases 10000 --seed 42
python scripts/run_adversarial_benchmark.py --cases 100000 --seed 42
~~~

For measured scalability evidence, use the dedicated runner. It records peak Python
memory in addition to runtime, throughput, and candidate-pair reduction:

~~~bash
python scripts/run_scale_benchmark.py --cases 10000 100000 --seed 42 --output scale-results.json
~~~

The GitHub Actions **Scalability Benchmark** workflow can run the same measurement
manually with larger sizes. The planned evidence ladder is 10K → 100K → 250K → 500K → 1M.
Do not describe any size as supported until the benchmark has actually completed at that size.

The script reports measured:

- full-match recall
- auto-match precision
- partial-payment accuracy
- false auto-matches
- elapsed time
- rows/second

No performance or accuracy numbers are stored as constants in the benchmark.

## Failure analysis

The benchmark is deliberately expected to expose limitations. In particular, the current
complex matcher uses bounded subset search rather than a general optimization solver.
Large ambiguous candidate sets are escalated to review instead of being forced into an
automatic match.

That behavior is intentional: financial reconciliation should prefer an explicit exception
over an unsupported allocation.

## Verification status

The benchmark workflow is required to pass before this milestone is merged.

## Next scale milestone

The next benchmark iteration should compare candidate-pair counts and runtime for:

10K → 100K → 250K → 500K → 1M

and record memory usage alongside runtime. The purpose is to establish a measured scalability
curve rather than advertise a scale number without evidence.
