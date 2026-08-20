# Chapter 3 — Methodology

## Architecture and implementation

The implemented application separates a customer interface, React staff dashboard, FastAPI business API, scikit-learn classification component, and PostgreSQL persistence. The deployed AWS mapping uses private S3 and CloudFront static hosting, API Gateway HTTP API, a Mangum-adapted backend Lambda, a separately invoked AI Lambda container, SSM configuration, CloudWatch Logs, and Aurora PostgreSQL Free Plan express configuration. All regional resources are in Singapore (`ap-southeast-1`).

The backend retains registration, JWT authentication and role authorization, customer isolation, ticket validation, filtering, statistics, staff updates, and reclassification. The supplied AI models were not retrained. A narrow scikit-learn 1.7.2 compatibility adaptation was verified locally across all 300 supplied rows with identical labels and rounded probabilities to the supplied 1.9.0 artifacts.

## Distributed interaction

Browsers load static assets through CloudFront and call API Gateway. API Gateway invokes the backend Lambda. During ticket creation the backend directly invokes the private AI Lambda through IAM, receives category and priority, and writes the record to Aurora using a temporary IAM database token over verified TLS. No password is stored for PostgreSQL. The express internet access gateway allows this path without a customer VPC, NAT Gateway, or paid interface endpoint.

## Validation method

Validation proceeded from local to cloud: Linux Lambda packaging, single-platform container build, disposable PostgreSQL 16 and Alembic migration, customer/staff API integration, persistence across restart, AI-down behavior, SAM validation, CloudFormation change-set review, deployed migration, live API tests, frontend HTTP checks, deployed AI failure/recovery, CloudWatch inspection, and billing review.

The live suite covered registration, login, JWT enforcement, validation, ticket creation, AI classification, persistence, customer isolation, staff authorization, retrieval, filters, statistics, status update, customer visibility of the update, reclassification, and failure recovery. Results are recorded in `AWS_TEST_RESULTS.md`.

## Scalability, reliability, and cost controls

Lambda scales on demand without provisioned concurrency. AI and backend use 256 MB. API Gateway throttling is 10 requests per second with burst 20. Aurora scales from 0 to 4 ACUs and auto-pauses after five minutes. Logs expire after three days, artifacts after seven days, ECR retains two images, and Budget alerts are set at $1, $3, and $5. No EC2, ECS, Fargate, NAT, load balancer, public EIP, VPC endpoint, paid domain, WAF, replica, or paid monitoring feature was created.

## Limitations

The classifiers' supplied-data agreement is resubstitution evidence, not held-out accuracy; the original training split is unavailable. Cost Explorer had not ingested usage at the final check. The Budget showed $0 actual spend, but final cost remains subject to Free Plan eligibility, credits, usage, and billing delay. The assignment staff account is a demonstration credential and should be removed or rotated after evidence capture.

