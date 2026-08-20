# AWS Cleanup — Actual Singapore Deployment

Run cleanup only after all screenshots and demonstrations are complete. Use profile `dcs-assignment` and Region `ap-southeast-1`. Aurora deletion and S3 emptying are irreversible; do not proceed if evidence or data must be retained.

## Safe removal order

1. Empty the frontend bucket `dcs-ticket-system-frontendbucket-91qyboxobxvi`.
2. Delete CloudFormation stack `dcs-ticket-system` and wait for `DELETE_COMPLETE`. This removes CloudFront, OAC, the frontend bucket/policy, API Gateway, Lambda functions, IAM roles/permissions, and four log groups.
3. Delete all eight parameters under `/dcs-ticket-system/prod`, including the JWT `SecureString`.
4. Delete Aurora cluster `dcs-ticket-system-db` without a final snapshot only after confirming its assignment data is no longer needed. Verify the generated DB instance, automated backups, and any snapshots are gone.
5. Empty the deployment artifact bucket shown by the bootstrap stack output. Its lifecycle is seven days, but empty it immediately for cleanup.
6. Delete CloudFormation stack `dcs-ticket-system-bootstrap`. Its ECR repository uses `EmptyOnDelete`; verify both AI image tags, repository, artifact bucket, and Budget are removed.
7. Check ECR, S3, RDS clusters/instances/snapshots, Lambda, API Gateway, CloudFront, CloudWatch Logs, SSM, IAM roles, and Budgets for leftovers.
8. Check NAT Gateways, public IPv4 addresses, VPC endpoints, EC2, ECS, load balancers, Route 53, WAF, SageMaker, and provisioned concurrency. None was intentionally created.
9. Review Bills, Cost Explorer, Free Tier usage, and credits until delayed usage has appeared. If the deployment Budget was deleted with the bootstrap stack, use the account's billing notifications during this final monitoring window.

## Failure handling

If application-stack deletion fails because the frontend bucket is not empty, empty only the exact bucket above and retry stack deletion. If CloudFront is still disabling, wait and retry; do not manually delete unrelated resources. If Aurora deletion is blocked, inspect deletion protection and snapshot options, and do not enable a paid retained snapshot accidentally.

