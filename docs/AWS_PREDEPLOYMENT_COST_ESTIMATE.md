# Pre-deployment Cost Estimate

The rejected Fargate/ALB estimate has been superseded by the serverless analysis in `AWS_ZERO_COST_PLAN.md`.

Current conclusion: the tiny compute and request workload should fit published Lambda/API allowances, but PostgreSQL, CloudFront plan, ECR storage, and account eligibility must be confirmed in Billing before claiming an actual `$0` bill. No resource may be deployed merely on the assumption that promotional credits will cover it.
