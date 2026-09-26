# Security Hardening & External Validation

## Security boundary

The platform treats deterministic reconciliation as the financial decision authority. AI is advisory and is constrained to bounded deterministic review context.

Security controls currently include:

- tenant-scoped object keys and audit records
- API-key authentication with constant-time comparison
- optional tenant-to-API-key binding
- per-tenant rate limiting
- bounded CSV upload size (10 MiB per file)
- CSV filename sanitization and tenant ID validation
- local object-store path traversal protection
- secrets supplied through environment variables / AWS Secrets Manager in staging
- encrypted, private S3 staging storage
- encrypted Redis transport in AWS staging
- HTTPS-only staging ALB listener
- ECS task IAM roles with scoped S3 and Secrets Manager permissions
- security response headers including nosniff, DENY, no-referrer, and restrictive Permissions-Policy
- non-root production container user (uid 10001)
- container healthcheck
- dependency vulnerability audit with pip-audit
- Python static analysis with Bandit
- production-image HIGH/CRITICAL vulnerability scan with Trivy
- OWASP ZAP baseline DAST against the built production container

## CI gates

The security workflow runs on pushes to main and pull requests targeting main.

### Dependency audit

pip-audit --strict checks resolved Python dependencies. This is dependency-level evidence; it does not claim that the application has no undiscovered vulnerabilities.

### Static analysis

Bandit runs against src/ with high-severity/high-confidence findings treated as CI failures.

### Container validation

CI builds the production image with --pull, validates Docker Compose configuration, verifies the runtime UID is 10001, and scans the image with Trivy for HIGH/CRITICAL vulnerabilities that have fixes available.

### External DAST

CI starts the production container in an isolated local target and scans it with OWASP ZAP baseline rules. The workflow fails if the generated report contains high or critical findings.

The ZAP report is uploaded as a workflow artifact for inspection.

## What this does not prove

These checks are automated security evidence, not a penetration-test certification.

They do not prove:

- absence of zero-day vulnerabilities
- correctness of every authorization path
- security of an actual customer deployment
- compliance with a specific regulatory framework
- protection against infrastructure or identity misconfiguration outside this repository
- that AWS staging is currently running

A production deployment still requires infrastructure configuration, secret management, TLS/DNS setup, monitoring, and an independent security review appropriate to the deployment's risk.

## Operational guidance

Before exposing a deployment to real financial data:

1. use AWS Secrets Manager or an equivalent secret manager
2. keep API authentication enabled
3. keep tenant credentials isolated per tenant
4. use private database/cache networking
5. keep object storage private and encrypted
6. review CloudWatch alarms and audit logs
7. run the DAST and dependency scans against the release candidate
8. perform an independent penetration test for the production environment
