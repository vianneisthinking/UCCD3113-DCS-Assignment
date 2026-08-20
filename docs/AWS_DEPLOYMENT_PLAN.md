# AWS Serverless Deployment Plan — Awaiting Approval

No AWS resources have been created. The cost/eligibility gate is `AWS_ZERO_COST_PLAN.md`.

## Candidate deployment

- Private S3 origin plus CloudFront-generated URL for both static frontends.
- API Gateway **HTTP API** to backend Lambda.
- Existing FastAPI through Mangum at 256 MB.
- Private synchronous backend-to-AI Lambda invocation with least-privilege IAM.
- AI Lambda container image; test 256 MB, then 512 MB only if required.
- Backend-only TLS/IAM access to an eligibility-confirmed Aurora express database through its managed internet access gateway; neither Lambda is VPC-attached.
- SSM standard parameters and three-day CloudWatch log retention.

## Deployment gates

1. Complete the account checklist and capture evidence.
2. Confirm the exact database configuration is covered; otherwise stop.
3. Confirm Aurora express configuration and IAM authentication are present; otherwise stop for a separate networking review.
4. Build Linux artifacts and rerun all tests with PostgreSQL.
5. Review a simple single-stack IaC change set and all cost-bearing resources.
6. Obtain explicit approval before applying it.

Backend configuration: `DATABASE_URL`, `JWT_SECRET_KEY`, `AI_INVOCATION_MODE=lambda`, `AI_LAMBDA_FUNCTION_NAME`, `AWS_REGION`, and restrictive `CORS_ORIGINS`. AI models remain embedded in its image. Secrets are never committed.

Post-deployment acceptance tests: registration, login/JWT, `/auth/me`, customer isolation, create/list/filter tickets, `/stats`, staff update, reclassification, malformed requests, AI invocation, forced AI failure and `pending_classification`, both frontends, three-day logs, and an unchanged Billing estimate.

Rollback is deletion of the single IaC stack plus any retained bucket objects, ECR images, logs, database snapshots, and parameters listed in `AWS_CLEANUP.md`.
