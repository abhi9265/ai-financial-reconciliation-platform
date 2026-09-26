# Phase 4 — Live AI Evaluation

## Objective
Evaluate a real AI provider without allowing the provider to become the reconciliation authority.

The deterministic engine owns MATCHED, REVIEW and UNMATCHED. The live provider receives only already-escalated REVIEW cases and returns structured advisory evidence.

## Live provider contract
The initial adapter uses the OpenAI Responses API.

- Provider: openai
- Model: AI_MODEL or OPENAI_REVIEW_MODEL
- Credential: OPENAI_API_KEY
- Timeout: AI_TIMEOUT_SECONDS
- Input: bounded deterministic review evidence
- Output: recommendation, confidence and rationale

The adapter does not send raw uploaded files, API keys, authorization headers, tenant secrets or unrestricted source records.

## Safety gates

1. Only deterministic REVIEW cases are sent to AI.
2. A provider MATCH without a deterministic candidate is downgraded to HUMAN_REVIEW.
3. AI output is never persisted as an automatic reconciliation decision.
4. Invalid structured output fails closed.
5. Provider failures are counted as evaluation failures, never as matches.
6. The evaluation records aggregate evidence and does not persist financial source data.

## Run a real evaluation
Use an operator-controlled environment and a small case count first:

    export OPENAI_API_KEY='...'
    export AI_PROVIDER=openai
    export AI_MODEL='gpt-5.6-luna'
    export AI_TIMEOUT_SECONDS=20
    python scripts/run_live_ai_evaluation.py --cases 25 --seed 42 --output reports/live-ai-evaluation.json

The normal CI pipeline does not make external model calls.

## Evidence
The report records provider/model, deterministic REVIEW cases, recommendation distribution, provider errors, success rate, latency, unsafe auto-match count, and explicit live-provider/authority flags.

No production accuracy, SLA or permanent model-quality claim should be inferred from a small live run.

## CI
The workflow is manually dispatched. It always runs the provider-contract tests. The live job runs only when an operator has configured the OPENAI_API_KEY repository secret.

A live run should use a limited case count and be treated as dated engineering evidence.

## Cost and model drift
The harness records latency. It intentionally does not hard-code model pricing because pricing changes; calculate cost from the provider's current published pricing at evaluation time.

Model versions, rate limits, network conditions and provider behavior can change. Live reports are evidence snapshots, not permanent guarantees.