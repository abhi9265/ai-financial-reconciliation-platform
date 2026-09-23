# AI Review Benchmark

The repository now includes a 400-case synthetic evaluation harness for the AI escalation boundary.

It creates deliberately ambiguous cases, forces them into deterministic REVIEW status, and measures:

- recommendation accuracy against synthetic ground truth
- review-case count
- average latency
- model identifier
- per-case confidence

Run it only with a real API credential:

    OPENAI_API_KEY=... python scripts/run_ai_review_benchmark.py --cases 400

The benchmark refuses to run without a credential, so the repository never presents fabricated AI accuracy or latency. AI output remains a recommendation for human review; the deterministic reconciliation result remains authoritative.

A live benchmark result has not been claimed unless this command has actually been executed with a real credential.
