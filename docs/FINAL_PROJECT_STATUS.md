# Final Project Status

## Outcome

- AWS deployment: **PASS** in Singapore (`ap-southeast-1`)
- Customer frontend: **PASS**, deployed through CloudFront
- Staff dashboard: **PASS**, production Vite build deployed through CloudFront
- Backend/API Gateway: **PASS**
- AI Lambda classification: **PASS**
- Aurora PostgreSQL and Alembic: **PASS**
- Authentication and authorization: **PASS**
- End-to-end integration: **PASS**
- AI failure/recovery: **PASS**
- CloudWatch logging: **PASS**, three-day retention
- Cost controls: **PASS**, with billing-ingestion caveat
- Aurora idle-resume login: **PASS** after bounded backend connection retry

## Live URLs

- Unified landing page: `https://dj3jeszo5m1yt.cloudfront.net`
- Customer: `https://dj3jeszo5m1yt.cloudfront.net/customer/index.html`
- Staff: `https://dj3jeszo5m1yt.cloudfront.net/staff/index.html`
- API: `https://rvreff5jp0.execute-api.ap-southeast-1.amazonaws.com`

## Deployed resources

- Three Lambda functions, three IAM execution roles, and two API invocation permissions.
- One API Gateway HTTP API and default stage.
- One private frontend S3 bucket, bucket policy, CloudFront distribution, and Origin Access Control.
- Four three-day CloudWatch log groups.
- One private deployment-artifact S3 bucket and one immutable ECR repository.
- Eight SSM parameters, including one `SecureString`.
- One AWS Budget with $1/$3/$5 alerts.
- One Aurora PostgreSQL express cluster with one serverless writer.

## Cost status

The Budget recorded `$0.00` actual spend at the final check. Cost Explorer data was not yet available. S3, ECR, Lambda, API Gateway, CloudFront, CloudWatch, and Aurora can charge depending on allowances, credits, and usage. Cleanup remains required after assessment evidence is complete.

## Remaining actions for the student

1. Capture the console and live-UI screenshots listed in `AWS_TEST_RESULTS.md`.
2. Keep secrets, account identifiers, tokens, and database endpoints out of the report.
3. Rotate or remove the demonstration staff credential after screenshots.
4. Delete the deployment using `AWS_CLEANUP.md` when marking/demo activity is finished.
5. Obtain the original training split if academically valid held-out model accuracy is required.
