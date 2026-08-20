# Remaining Pre-deployment Validation Results

Date: 2026-08-20. No AWS account API or resource-creation call was made.

## Real PostgreSQL — BLOCKED

The host has no Docker, Podman, PostgreSQL server, `psql`, Windows Package Manager, Chocolatey, Scoop, existing PostgreSQL/Docker service, or installed product directory. Installing an unsigned/ad-hoc database bundle without a package manager or managed administrator path was not treated as a safe validation method. SQLite Alembic remains passing, but this does not satisfy the real-PostgreSQL gate.

Required continuation on a suitable machine:

```powershell
docker compose up -d postgres
$env:DATABASE_URL = "postgresql+psycopg2://support:...@127.0.0.1:5432/support"
python -m alembic upgrade head
python seed.py --reset
# start AI and backend, then run test_backend.py twice: AI up and AI down
```

Deployment approval must remain conditional on that test passing.

## Application and Lambda adaptation — PASS locally

- Full API/service test with AI available: all registration, JWT, isolation, validation, classification, routing, filters, statistics, staff update and reclassification checks passed.
- Full test with AI unavailable: complaint stored as `pending_classification`, reclassification returned 503 without corrupting the ticket, all other checks passed.
- API Gateway HTTP API v2 events through Mangum passed.
- One-time migration Lambda handler reached Alembic head locally and rejects invocation without its explicit confirmation value.
- IAM PostgreSQL factory passed mocked token generation and psycopg2 argument checks: fresh token, TLS `verify-full`, AWS RDS global CA bundle, 10-second connection timeout.
- Backend artifact after migration and CA inclusion: **48.89 MiB ZIP**, **114.77 MiB uncompressed**, 6,926 files.
- Staff production build passed: 2,371 modules; output approximately 0.49 KB HTML, 4.74 KB CSS, and 578.55 KB JavaScript (171.35 KB gzip). The chunk-size warning is acceptable for this tiny assignment.

## IaC — PASS static validation

- `infrastructure/bootstrap.yaml` and `infrastructure/template.yaml` pass `cfn-lint` 1.55.1 with no findings.
- No `sam deploy`, CloudFormation change set, AWS CLI resource call, or console creation was performed.
- Templates create no VPC, NAT, interface endpoint, load balancer, public IPv4, provisioned concurrency, or public AI endpoint.
- Aurora express creation remains a deliberate manual eligibility/approval gate because the CloudFormation DBCluster resource does not expose the express-configuration creation operation.

## Final blockers before deployment approval

1. Real PostgreSQL migration and full workflow test.
2. Actual AWS account/credit/database eligibility evidence.
3. Docker/SAM build of the AI image and measurement of the final compressed ECR image.
4. Review of a generated CloudFormation change set and cost-bearing resource inventory.
