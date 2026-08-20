# AWS Serverless Deployment Manual

## Deployed environment

- Profile: `dcs-assignment`
- Region: `ap-southeast-1`
- Application stack: `dcs-ticket-system`
- Bootstrap stack: `dcs-ticket-system-bootstrap`
- API: `https://rvreff5jp0.execute-api.ap-southeast-1.amazonaws.com`
- Customer site: `https://dj3jeszo5m1yt.cloudfront.net`
- Staff site: `https://dj3jeszo5m1yt.cloudfront.net/staff/index.html`

## Reproducible deployment order

1. Confirm caller identity and configured Singapore Region.
2. Build the backend with `infrastructure/build-backend.ps1`.
3. Build AI as a Lambda-compatible single manifest: `docker build --provenance=false --platform linux/amd64 -f Member3_AI_Backend_/Member3_AI_Backend/Dockerfile.lambda -t dcs-ticket-ai:lambda-single Member3_AI_Backend_/Member3_AI_Backend`.
4. Validate locally and run PostgreSQL/Alembic integration tests.
5. Create and review the bootstrap change set, then create the encrypted artifact S3 bucket, immutable ECR repository, and $5 Budget.
6. Create Aurora PostgreSQL with `aws rds create-db-cluster --db-cluster-identifier dcs-ticket-system-db --engine aurora-postgresql --master-username postgres --with-express-configuration --profile dcs-assignment --region ap-southeast-1`.
7. Create the eight `/dcs-ticket-system/prod` SSM parameters. Use Lambda's system CA path `/etc/pki/tls/certs/ca-bundle.crt` for the express gateway.
8. Push the single-manifest AI image and package the backend ZIP into the artifact bucket.
9. Create and review the SAM/CloudFormation application change set, then execute it.
10. Invoke migration with `{"confirm":"upgrade-head"}`.
11. Build both frontends with the production API URL, sync them to the private frontend bucket, and invalidate CloudFront.
12. Run the customer, staff, failure/recovery, logging, and cost checks in `AWS_TEST_RESULTS.md`.

## Important deployed constraints

- AI memory remains 256 MB. Its timeout is 30 seconds; observed peak memory was 217 MB.
- The account concurrency quota does not permit reserved concurrency while preserving AWS's minimum unreserved pool. No reserved or provisioned concurrency is configured.
- Do not add NAT, VPC endpoints, replicas, paid monitoring, a custom domain, Route 53, WAF, or load balancers.
- CloudFormation attempts that failed during deployment rolled back fully. The final stacks are complete.

## Screenshot evidence locations

Capture the console pages for CloudFormation stack resources, Lambda configuration and monitoring, API Gateway routes/stage logs, RDS cluster configuration, private S3 permissions, CloudFront distribution, ECR image tag, SSM parameter names (never values), IAM role policies, CloudWatch logs, Budget status, and both live sites. Redact account IDs, tokens, secrets, and database endpoints where required.

