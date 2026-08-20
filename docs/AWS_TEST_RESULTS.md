# AWS Test Results

Test date: **20 August 2026**  
Region: **Singapore (`ap-southeast-1`)**

## Deployment and infrastructure

| Check | Result |
|---|---|
| Bootstrap stack | PASS — `CREATE_COMPLETE` |
| Application stack | PASS — stack and later updates complete |
| Prohibited infrastructure | PASS — none present |
| Aurora express configuration | PASS — 0–4 ACUs, 1 GiB, one writer, no reader, no VPC, no Multi-AZ |
| Alembic | PASS — revision `20260820_01` / `head` |
| Frontend files | PASS — both CloudFront pages returned HTTP 200 |
| Deployed localhost references | PASS — none |

## Functional workflow

- PASS: backend health, PostgreSQL connection, and backend-to-AI invocation.
- PASS: customer registration, duplicate rejection, login, `/auth/me`, missing/invalid JWT rejection, and complaint validation.
- PASS: ticket creation with real AI category and priority prediction. The billing sample classified as `billing_payment` and routed to Billing and Payment.
- PASS: PostgreSQL persistence and customer ownership isolation.
- PASS: staff login, all-ticket retrieval, priority filtering, statistics, status update, invalid-status rejection, and reclassification without resetting workflow status.
- PASS: customer retrieved the staff-updated `in_progress` status.
- PASS: AI failure stored the complaint as `pending_classification`; reclassification returned 503 and left the ticket unchanged.
- PASS: AI recovery health returned `healthy` after restoration.
- PASS: staff login returned HTTP 200 with the exact CloudFront CORS origin and an access token after deploying a bounded database-connection retry for Aurora 0-ACU wake-up. The original browser `Failed to fetch` symptom was an API 500 caused by the first 10-second connection timing out during resume, not a frontend or CORS defect.

## Runtime measurements

| Component | Memory | Observed peak | Example duration |
|---|---:|---:|---:|
| Backend Lambda | 256 MB | 200 MB | 212–1,936 ms in sampled requests |
| AI Lambda | 256 MB | 217 MB | 14–18 ms warm; 3,338 ms measured cold invocation |

The original 15-second AI timeout failed during first cold initialization. Timeout was changed to 30 seconds while memory remained 256 MB. The supplied model artifacts emit an expected scikit-learn serialization-version warning; the compatibility field was previously regression-tested across all 300 supplied rows.

## CloudWatch

- Backend, AI, migration, and API Gateway log groups exist with three-day retention.
- API access logs recorded HTTP 200 health and the intentionally generated HTTP 404.
- Earlier expected records include an unconfirmed migration rejection, Aurora auto-pause wake-up timeout, AI cold-start timeout, and deliberate AI throttling during failure testing. Subsequent operations passed.

## Cost evidence

- AWS Budget limit: `$5.00`.
- Recorded actual spend at review time: `$0.00`.
- Cost Explorer returned `DataUnavailableException` because billing data had not yet been ingested. Therefore `$0.00` is the current Budget record, not a guarantee of final billed cost.

## Screenshot order

1. Budget and account Free Plan/credits.
2. Both CloudFormation stacks and resource tabs.
3. Aurora configuration and connectivity method.
4. Backend, AI, and migration Lambda configuration.
5. API Gateway routes, default stage, throttling, and access logs.
6. Private frontend S3 bucket and CloudFront distribution/OAC.
7. ECR immutable AI image.
8. SSM parameter names and IAM policies without revealing values.
9. CloudWatch backend/AI/API success records and memory reports.
10. Customer registration, ticket submission, AI result, and updated status.
11. Staff login, ticket list/filter/statistics, and status update.
