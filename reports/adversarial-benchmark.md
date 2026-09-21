# Adversarial Benchmark Report

This file records measured reconciliation and scalability evidence. Do not replace measured
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
| Peak Python memory | pending |
| Candidate reduction ratio | pending |

## Interpretation

A lower score is not automatically a bad result. The important questions are:

1. Which cases failed?
2. Were failures false matches or safe reviews?
3. Did blocking exclude a valid candidate?
4. Did complexity grow as expected?
5. What engineering change should address the dominant failure mode?

The report should be updated only with results produced by the benchmark.

## Scalability evidence

Run the deterministic scale benchmark with one or more dataset sizes:

~~~bash
python scripts/run_scale_benchmark.py --cases 10000 100000 250000 500000 1000000 --seed 42 --output scale-results.json
~~~

The planned evidence ladder is **10K → 100K → 250K → 500K → 1M**. Record the observed runtime,
peak memory, throughput, candidate-pair count, candidate reduction ratio, and correctness
metrics only after each run completes. No dataset size is considered production-supported merely
because it is a benchmark target.
