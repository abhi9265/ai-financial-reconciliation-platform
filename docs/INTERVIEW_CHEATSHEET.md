# Interview Cheat Sheet

## 30-second answer

> I built a multi-tenant financial reconciliation platform that takes messy bank, invoice and accounting data, normalizes it into a canonical transaction model, and reconciles it using deterministic evidence first. It supports exact, fuzzy, one-to-many and partial-payment matching. Ambiguous cases are escalated to a controlled AI reviewer and then remain in a human-review workflow. I also built PostgreSQL, Redis/Celery, object storage, tenant isolation, idempotency, auditability, observability, security gates and measured scale tests around it.

## 2-minute architecture

Sources -> ingestion/validation -> canonical transaction model -> candidate blocking -> deterministic reconciliation -> MATCH / REVIEW / UNMATCHED.

REVIEW -> AI advisory -> human decision -> audit.

FastAPI uses PostgreSQL for durable state, Redis/Celery for asynchronous work, and object storage for raw data.

## Data-engineering questions

### Why a canonical model?

Source systems have different field names, date semantics, identifiers and representations. Normalization creates one controlled contract so reconciliation logic does not need to understand every source format.

### How do you scale matching?

Candidate blocking narrows the search space using bounded signals such as date windows, amount buckets and normalized counterparty/name tokens. Expensive complex matching is also bounded so pathological candidate sets cannot cause combinatorial explosion.

### Why PostgreSQL + Redis + Celery?

PostgreSQL owns durable state. Redis provides queue infrastructure. Celery keeps long-running reconciliation outside the request lifecycle and allows independent worker scaling.

### How do you prevent duplicate jobs?

Tenant-scoped idempotency keys plus database-level conflict handling make concurrent retries converge on the same job.

### What happens if a worker dies?

Late acknowledgement and broker redelivery allow queued work to be retried while durable job state remains in PostgreSQL.

## AI questions

### Why not let the LLM reconcile everything?

Financial decisions need reproducible evidence and auditability. AI is useful for semantic ambiguity, but deterministic evidence remains authoritative.

### What does AI receive?

Only bounded, already-validated review context: candidate information, confidence/signals, amount/date differences and deterministic explanation.

### What if AI recommends MATCH while the deterministic engine says REVIEW?

The recommendation is validated against the safety contract and cannot silently become an automatic match. Unsafe recommendations are downgraded to human review.

## Security questions

Mention tenant-bound API authentication, constant-time API-key comparison, tenant authorization, rate limiting, non-root containers, read-only production-like runtime, dropped Linux capabilities, no-new-privileges, dependency auditing, Bandit, Trivy, OWASP ZAP, security headers and secret-manager based deployment.

## Scale evidence

| Measurement | Evidence |
|---|---:|
| Synthetic reconciliation | 500K bank rows |
| Candidate reduction | 99.9926% |
| Full-match recall | 100% |
| Auto-match precision | 100% |
| Partial-payment accuracy | 100% |
| False auto-matches | 0 |
| API load smoke | 1,199 req/s |
| API load | 1,000 requests / 25 concurrency |
| Offline AI safety | 400 adversarial cases |
| Peak Python memory | 2.81 GB |

Always describe these as controlled test-environment measurements, not production SLAs.

## Strong closing statement

> The part I focused on was not just making matching work. I separated source normalization from reconciliation, bounded the expensive search space, made asynchronous processing and tenant isolation explicit, and put AI behind a safety boundary. Then I built measurable CI gates around scale, security and deployment so the architecture is testable rather than just theoretical.
