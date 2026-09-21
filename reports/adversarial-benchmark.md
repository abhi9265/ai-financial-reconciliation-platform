# Adversarial Benchmark Report

This file is intentionally a template for measured results.

Run:

~~~bash
python scripts/run_adversarial_benchmark.py --cases 250 --seed 42
~~~

Then copy the observed output into a dated benchmark record. Do not replace measured
values with targets or examples.

## Required evidence

| Metric | Measured result |
|---|---:|
| Cases | pending |
| Bank rows | pending |
| Invoice rows | pending |
| One-to-many accuracy | pending |
| Partial-payment accuracy | pending |
| Full-match recall | pending |
| Auto-match precision | pending |
| False auto-matches | pending |
| Runtime | pending |
| Rows/second | pending |

## Interpretation

A lower score is not automatically a bad result. The important questions are:

1. Which cases failed?
2. Were failures false matches or safe reviews?
3. Did blocking exclude a valid candidate?
4. Did complexity grow as expected?
5. What engineering change should address the dominant failure mode?

The report should be updated only with results produced by the benchmark.
