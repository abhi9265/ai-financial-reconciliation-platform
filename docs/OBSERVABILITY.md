# Production observability

## Observability contract

The application exposes four operational signal families:

| Signal | Implementation | Purpose |
|---|---|---|
| Logs | JSON structured logs + request ID | Trace a request/job across API and worker logs |
| Metrics | Prometheus /metrics endpoint | Request, latency, job, reconciliation, AI and worker telemetry |
| Health | /health + /ready | Liveness vs dependency readiness |
| Cloud infrastructure | CloudWatch + alarms | ALB, ECS, RDS and Redis failure/saturation detection |

## Application metrics

Important metrics include:

- reconciliation_http_requests_total
- reconciliation_http_request_duration_seconds
- reconciliation_jobs_total
- reconciliation_decisions_total
- reconciliation_job_duration_seconds
- reconciliation_ai_reviews_total
- reconciliation_ai_failures_total
- reconciliation_worker_jobs_total
- reconciliation_queue_depth
- reconciliation_review_backlog

The existing /metrics/snapshot endpoint remains available as a small JSON debugging view. Prometheus should use /metrics.

### Cardinality rules

HTTP metrics use route paths rather than raw URLs, and tenant IDs, request IDs, job IDs and transaction IDs are never metric labels. This prevents unbounded metric-cardinality growth.

## Logging

Every HTTP request receives or preserves an X-Request-ID. Structured events include:

- UTC timestamp
- event name
- request ID where available
- HTTP method/path/status
- latency
- job outcome
- bounded operational metadata

Secrets, API keys and authorization headers are not logged.

For asynchronous work, the same job ID is emitted by the API/job lifecycle logs so operators can correlate enqueue, execution and failure events.

## Health semantics

- /health is a liveness check and does not require the database.
- /ready checks the configured durable store and, when Celery is enabled, Redis connectivity.
- Load balancers should use /ready.
- A readiness failure should remove the API task from traffic without implying that the process itself has crashed.

## Local observability

Run the application with the optional observability profile:

~~~bash
POSTGRES_PASSWORD=local-password RECONCILIATION_API_KEY=local-api-key docker compose --profile observability up --build
~~~

Then:

~~~bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/metrics
~~~

Prometheus is available on port 9090 and Grafana on port 3000. The repository includes the Prometheus scrape configuration at observability/prometheus.yml.

## AWS staging observability

The AWS staging Terraform stack enables ECS Container Insights and provisions CloudWatch alarms for:

- ALB 5xx responses
- application target 5xx responses
- target response latency
- unhealthy API targets
- API service running-task count
- worker service running-task count
- PostgreSQL CPU
- PostgreSQL free storage
- Redis engine CPU

All alarms publish to the generated SNS topic. Operators should subscribe an approved email, incident-management endpoint or other notification target to the topic after deployment.

CloudWatch log groups are retained for 14 days in the staging environment.

## Suggested operational thresholds

These are starting alert thresholds, not production SLAs:

- API target 5xx: >= 5 in 5 minutes for 2 periods
- API target latency: >= 2 seconds for 3 periods
- unhealthy API targets: >= 1 for 2 periods
- database CPU: >= 80% for 3 periods
- database free storage: <= 2 GiB for 2 periods
- Redis CPU: >= 80% for 3 periods
- API/worker desired running tasks: below desired count for 2 periods

Tune these using actual staging traffic before treating them as SLOs.

## Incident workflow

1. Check /health and /ready.
2. Inspect the request ID from the failing response.
3. Search structured API/worker logs by request ID and job ID.
4. Check HTTP latency/error metrics.
5. Check reconciliation outcome and review backlog metrics.
6. Check ECS, ALB, RDS and Redis CloudWatch alarms.
7. If the worker is unhealthy, inspect Celery task failures and redelivery.
8. If the database is saturated, reduce workload before scaling.
9. If the AI provider is failing, keep deterministic reconciliation authoritative and route cases to review.
10. Roll back the immutable application image when a deployment regression is identified.

## What is and is not claimed

This phase implements the observability instrumentation and deployment configuration in the repository. It does not claim that a live AWS monitoring stack has been provisioned or that any alert has fired in production. Those require an actual AWS deployment and notification subscription.
