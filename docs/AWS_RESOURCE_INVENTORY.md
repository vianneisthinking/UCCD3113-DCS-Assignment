# Planned AWS Resource Inventory — Nothing Created Yet

Classification means: **expected $0** under published monthly usage; **free-plan dependent** requires the current account offer/credits; **potentially billable** can accrue storage or usage charges if coverage is absent/exceeded.

| Resource | Count | Classification | Zero-traffic charge risk / control |
|---|---:|---|---|
| CloudFormation/SAM application stack | 1 | expected $0 | CloudFormation has no stack fee for these resource types; child resources can bill |
| CloudFormation bootstrap stack | 1 | expected $0 | Same caveat |
| Lambda backend function, versions/code storage | 1 | expected $0 | No provisioned concurrency; 256 MB; reserved concurrency is a free limit, not warm capacity |
| Lambda AI image function | 1 | expected $0 | 256 MB initially; no provisioned concurrency; maximum reserved concurrency 2 |
| One-time Alembic migration Lambda | 1 | expected $0 | No trigger; invoke manually with confirmation payload, then it remains idle until stack deletion |
| Lambda execution roles | 3 | expected $0 | IAM roles/policies have no direct charge |
| Lambda permissions generated for HTTP API | 1+ | expected $0 | No direct charge |
| API Gateway HTTP API, `$default` stage, routes/integration | 1 | free-plan dependent | Requests can bill after allowance/credits; throttled to 10 requests/s, burst 20 |
| Frontend S3 bucket | 1 | potentially billable | Tiny storage/requests expected within allowance; no versioning; delete objects after demo |
| SAM deployment-artifact S3 bucket | 1 | potentially billable | Backend artifact storage; seven-day lifecycle; empty during cleanup |
| S3 bucket policy | 1 | expected $0 | No direct charge |
| CloudFront distribution | 1 | free-plan dependent | Confirm flat-rate/standard plan eligibility; generated domain only |
| CloudFront Origin Access Control | 1 | expected $0 | No separate charge |
| ECR private repository | 1 | free-plan dependent / potentially billable | One AI image; lifecycle keeps at most two; storage bills outside allowance |
| CloudWatch log groups | 3 | potentially billable | Three-day retention; Lambda log ingestion/storage metered outside allowance |
| Standard SSM String parameters | 7 | expected $0 | DB host/port/name/user/CA path, IAM mode, JWT expiry; do not enable advanced tier/high throughput |
| Standard SSM SecureString parameter | 1 | expected $0 | JWT secret using AWS-managed SSM key; no customer KMS key |
| AWS-managed SSM KMS key | shared | expected $0 | Do not create a customer-managed KMS key |
| Monthly AWS Budget with $1/$3/$5 email alerts | 1 | expected $0 if within AWS budget allowance | Warning only; does not stop spend; confirm email subscription |
| Aurora PostgreSQL Serverless express cluster and AWS-selected covered instance topology | 1 cluster | **free-plan dependent and potentially billable** | Primary gating resource; add no instances; monitor plan/credits, ACUs, storage, I/O, backup and snapshots |
| Aurora-managed internet access gateway | 1, part of express cluster | free-plan dependent | Managed part of express configuration; confirm console coverage; no customer VPC/NAT/endpoints |
| RDS service-linked role | 0–1, AWS-created | expected $0 | IAM role has no direct charge |

## Explicitly not created

No VPC, subnet, route table, internet gateway, egress-only gateway, NAT Gateway, VPC endpoint, public IPv4 allocation, load balancer, ECS/Fargate service, EC2, RDS Proxy, Secrets Manager secret, Data API, custom KMS key, Route 53 resource, custom domain, ACM custom certificate, WAF, provisioned concurrency, paid dashboard, custom metric, database replica, or Multi-AZ add-on.
