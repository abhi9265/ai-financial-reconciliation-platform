# Architecture Diagrams

## Runtime topology

```mermaid
flowchart LR
    U[Client / Tenant] --> A[FastAPI]
    A --> AUTH[Tenant Auth]
    AUTH --> O[(Object Storage)]
    AUTH --> DB[(PostgreSQL)]
    A --> R[(Redis)]
    R --> C[Celery Workers]
    C --> O
    C --> DB
    C --> P[Validation + Normalization]
    P --> M[Reconciliation Engine]
    M --> X[Anomaly Detection]
    X --> H[Human Review]
    H -. ambiguous only .-> AI[AI Reviewer]
    M --> AUD[(Audit Events)]
    A --> OBS[Metrics + Logs]
```

## Reconciliation decision flow

```mermaid
flowchart TD
    S[Source transaction] --> V{Valid contract?}
    V -- No --> Q[Quarantine / reject]
    V -- Yes --> C[Canonical transaction]
    C --> D{Deterministic evidence}
    D -- Strong unique match --> M[Auto-match]
    D -- Reference conflict --> R[Review]
    D -- No match --> F{Conservative fuzzy candidate}
    F -- Unique and above threshold --> M2[Auto-match]
    F -- Ambiguous / weak --> R
    F -- None --> U[Unmatched]
    R --> AI{AI escalation enabled?}
    AI -- No --> H[Human review]
    AI -- Yes --> AIV[Structured AI evidence]
    AIV --> H
    M --> AUD[Audit + metrics]
    M2 --> AUD
    U --> AUD
    H --> AUD
```

## Async execution sequence

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Redis
    participant Worker as Celery Worker
    participant Store as Object Storage
    participant AI as AI Reviewer

    Client->>API: POST /v1/reconcile/async
    API->>API: Authenticate + validate tenant/file
    API->>Redis: Rate-limit tenant
    API->>Store: Persist raw files
    API->>DB: Create queued job
    API->>Redis: Enqueue task
    API-->>Client: 202 + job_id

    Redis->>Worker: Deliver job
    Worker->>DB: Mark running
    Worker->>Store: Read raw files
    Worker->>Worker: Validate + normalize
    Worker->>Worker: Deterministic reconciliation
    Worker->>AI: Review ambiguous cases
    AI-->>Worker: Structured evidence
    Worker->>DB: Persist result + review cases
    Worker->>DB: Mark succeeded
    Client->>API: GET /v1/reconcile/jobs/{job_id}
    API->>DB: Read tenant-scoped state
    API-->>Client: Job status + result
```

## Data contract boundary

```mermaid
flowchart LR
    RAW[Raw source file] --> SC[Source contract]
    SC --> N[Normalizer]
    N --> CT[CanonicalTransaction]
    CT --> RH[Deterministic record hash]
    CT --> REC[Reconciliation]
    CT --> LIN[Lineage]
```

These diagrams are aligned with the executable implementation in the source tree.
