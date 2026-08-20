# Final Deployment Readiness Checklist

Status: **pre-deployment checklist only**. No AWS resource has been created. Do not run any command marked **DEPLOYMENT COMMAND** until manual account checks, local PostgreSQL validation, change-set review, and explicit approval are complete.

## 1. Manual AWS Account Checks

Record screenshots or notes for every row. Any STOP result blocks all deployment commands.

| Check | AWS console location | Expected wording/status | PASS condition | STOP condition |
|---|---|---|---|---|
| Account plan | Account menu → **Billing and Cost Management** → **Billing home** | `Free plan` or clearly identified `Paid plan`, with credit balance and plan/end-date information | Free Plan remains active through the demo/marking period, or Paid Plan has sufficient unexpired eligible credits and the user explicitly accepts its pay-as-you-go risk | Plan is unclear, Free Plan expires before cleanup, or Paid Plan has inadequate credits |
| Credits | Billing → **Credits** | Positive **Amount remaining**, future **Expiration date**, and applicable AWS-service scope | Credits cover Aurora/ECR/S3/API/CloudFront usage for the complete deployment window | Zero/expired credits, excluded services, or expiry before cleanup |
| Current bill | Billing → **Bills** → current month; expand every service and Region | No unexplained current charges | Starting charges are understood and acceptable; assignment resources can be distinguished | Existing unexplained charge or existing resources likely to consume shared allowances |
| Free Tier use | Billing → **Free Tier** | Entries/usage for Lambda, API Gateway, S3, CloudFront, ECR, CloudWatch, RDS/Aurora | Forecast remains comfortably below relevant limits | Limit is already exhausted or forecast shows overage during the assignment |
| Cost Explorer | Billing → **Cost Explorer** → month-to-date → group by **Service**, then **Region** | No hidden active usage in Singapore or global services | Existing usage is identified and does not invalidate the estimate | Unknown RDS, ECR, CloudFront, S3, Lambda, IPv4, NAT, or logging usage |
| Organization status | Account menu → **Organizations**, or AWS Organizations console | Account is not a member/management account, unless Paid Plan implications are already accepted | Account remains eligible under the verified plan | Joining/creating an Organization would upgrade/alter the Free Plan or expire credits |
| Billing alerts | Billing → **Billing preferences** | Free Tier usage and CloudWatch billing alerts enabled; verified email | Both alerts enabled and recipient correct | Alerts disabled or inaccessible |
| Region | Region selector → **Asia Pacific (Singapore) `ap-southeast-1`** | Region opens normally and RDS, Lambda, API Gateway, S3, ECR, CloudWatch, SSM are available | Singapore selected and Aurora express dialog is present | Wrong Region, service unavailable, permission errors, or express option absent; do not deploy |
| Aurora express eligibility | RDS → **Databases** → **Create with express configuration in seconds** → open review dialog only | Explicit `Aurora PostgreSQL Serverless`, `express configuration`, and Free Tier/Free Plan indication | Console explicitly offers the Free Plan express path for this account/Region; capacity is within displayed coverage; close dialog without creating | Only full/standard configuration is offered, Free Tier wording absent, or estimated cost/coverage is ambiguous |
| Aurora limits | Same express review dialog and Billing Free Tier details | Current account limits consistent with up to 4 ACUs/cluster and 1 GiB storage; AWS-selected covered topology | Project can remain below 1 GiB; no manually added instances/readers/options | Required configuration exceeds displayed allowance or adds paid topology/features |
| Aurora networking/authentication | RDS express review/help text | Managed **internet access gateway** and **IAM authentication** | Express gateway and IAM-only authentication are present; no customer VPC requested | Dialog asks for VPC, subnet, public IPv4, password/Secrets Manager, NAT, or full configuration |
| Aurora options | Express review dialog | Aurora Standard; no optional log exports/Data API/advanced insights/extra replicas | Defaults remain within covered express configuration; no paid add-on selected | I/O-Optimized, extra instances, Data API, paid insights, Extended Support, or other unapproved option selected |
| RDS fallback | RDS → **Create database** → Standard create → PostgreSQL → Free tier template, inspect only | Exact eligible instance/storage identified and estimated cost covered | Treat only as evidence for a separate architecture review; cancel dialog | Do not deploy conventional RDS under the current no-VPC stack; any selection requires a new review |
| CloudFront plan | CloudFront → pricing/plan selection or account plan page | Eligibility for `$0` flat-rate Free plan, or adequate standard Free Tier/credits | Selected account plan and expected traffic support $0 expectation | No applicable allowance/credits or plan would create an unacceptable charge |
| Budget allowance | Billing → **Budgets** | Existing budget count leaves one no-additional-cost budget available | Bootstrap budget with $1/$3/$5 notifications remains within the account allowance | Creating the budget itself is shown as billable or duplicates an existing equivalent budget |

If any AWS wording is ambiguous, stop and use **Support Center → Account and billing support** to request confirmation for the exact account, Region, Aurora express configuration, ACU/storage limits, credits, and planned duration. Do not infer eligibility from a general marketing page.

## 2. PostgreSQL Validation

Minimum remaining gate: execute the actual Alembic migration and complete backend workflow against PostgreSQL 16, once with AI available and once with AI unavailable. SQLite success is not a substitute. Docker Desktop/Engine with Compose is sufficient.

Run from the repository root in PowerShell.

### Start disposable PostgreSQL

```powershell
docker compose pull database
docker compose up -d database
docker compose ps
docker compose exec -T database pg_isready -U tickets_app -d tickets
```

PASS: `database` is healthy and `pg_isready` reports accepting connections.

### Run Alembic explicitly

```powershell
docker compose build backend
docker compose run --rm --no-deps --entrypoint python backend -m alembic upgrade head
docker compose exec -T database psql -U tickets_app -d tickets -c "SELECT version_num FROM alembic_version;"
docker compose exec -T database psql -U tickets_app -d tickets -c "\dt"
```

PASS: revision `20260820_01` is current and `users`, `tickets`, and `alembic_version` exist.

### Start AI and backend

```powershell
docker compose build ai backend
docker compose up -d ai backend
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8001/health
```

PASS: both containers run; backend reports database connected and AI reachable.

### Seed and run full integration test with AI available

```powershell
docker compose exec -T backend python seed.py --reset
& .\.venv-test\Scripts\python.exe .\member2_backend\test_backend.py
```

PASS: every assertion passes, including registration, JWT, customer isolation, classification, routing, filtering, statistics, staff update, and reclassification.

### Verify persistence across backend restart

```powershell
$before = docker compose exec -T database psql -U tickets_app -d tickets -tAc "SELECT count(*) FROM tickets;"
docker compose restart backend
docker compose exec -T backend python -c "from api.models import SessionLocal, Ticket; d=SessionLocal(); print(d.query(Ticket).count()); d.close()"
$after = docker compose exec -T database psql -U tickets_app -d tickets -tAc "SELECT count(*) FROM tickets;"
"before=$($before.Trim()) after=$($after.Trim())"
```

PASS: count is non-zero and unchanged after backend restart.

### Verify AI failure fallback

```powershell
docker compose stop ai
& .\.venv-test\Scripts\python.exe .\member2_backend\test_backend.py
docker compose start ai
```

PASS: ticket is stored as `pending_classification`, reclassification returns 503 without changing the stored ticket, and all remaining authorization/data checks pass.

### Remove disposable PostgreSQL and volume

```powershell
docker compose down -v --remove-orphans
docker compose ps -a
docker volume ls --filter name=postgres_data
```

PASS: assignment containers are absent and the Compose PostgreSQL volume is removed. This deliberately deletes only disposable local test data.

## 3. AI Container Validation

The Lambda image uses `Member3_AI_Backend_/Member3_AI_Backend/Dockerfile.lambda` and the AWS Lambda Python 3.12 base image.

### Docker build and size inspection

```powershell
docker build --pull --file .\Member3_AI_Backend_\Member3_AI_Backend\Dockerfile.lambda --tag dcs-ticket-ai:lambda .\Member3_AI_Backend_\Member3_AI_Backend
docker image inspect dcs-ticket-ai:lambda --format '{{.Id}} {{.Size}}'
$bytes = [int64](docker image inspect dcs-ticket-ai:lambda --format '{{.Size}}')
"Image size: {0:N2} MiB" -f ($bytes / 1MB)
docker history dcs-ticket-ai:lambda
```

Record the image ID and final size. PASS: build completes for `linux/amd64`, image remains far below Lambda's 10 GB image ceiling, and no unexplained large layer appears.

### Run Lambda Runtime Interface Emulator locally

Terminal 1:

```powershell
docker run --rm --name dcs-ticket-ai-lambda --platform linux/amd64 -p 9000:8080 dcs-ticket-ai:lambda
```

Terminal 2:

```powershell
$event = @{ complaint = "My credit card was charged twice for one order." } | ConvertTo-Json -Compress
$result = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9000/2015-03-31/functions/function/invocations -ContentType application/json -Body $event
$result | ConvertTo-Json -Depth 5
if (-not $result.category -or -not $result.priority) { throw "Missing category or priority" }
```

Expected output includes a non-empty `category`, `category_confidence`, `priority`, `priority_confidence`, and `model_version`. For this complaint, verify category `billing_payment`; record the returned priority rather than hardcoding an invented result.

Health and malformed-input checks:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9000/2015-03-31/functions/function/invocations -ContentType application/json -Body '{"action":"health"}'
try { Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9000/2015-03-31/functions/function/invocations -ContentType application/json -Body '{}' } catch { $_.Exception.Message }
docker stop dcs-ticket-ai-lambda
```

PASS: health reports models loaded; empty input fails validation; the prediction contains category and priority.

Optional SAM confirmation after SAM CLI is installed:

```powershell
'{"complaint":"My parcel is marked delivered but never arrived."}' | Set-Content .\infrastructure\ai-test-event.json -Encoding ascii
sam local invoke AiFunction --template .\infrastructure\template.yaml --event .\infrastructure\ai-test-event.json --parameter-overrides AiImageUri=dcs-ticket-ai:lambda DatabaseResourceId=local-placeholder
```

## 4. CloudFormation Change Set Review

Create change sets only after PostgreSQL/account gates pass. Do not execute them during review.

### Bootstrap change set — expected

- `AWS::S3::Bucket`: deployment-artifact bucket with encryption, public access blocked, seven-day lifecycle.
- `AWS::ECR::Repository`: `dcs-ticket-system-ai`, immutable tags, scan on push, keep at most two images, empty on deletion.
- `AWS::Budgets::Budget`: one monthly $5 budget with actual-cost email notifications at $1, $3, and $5.

### Application/SAM transformed change set — expected

- Three `AWS::Lambda::Function` resources: backend ZIP, private AI image, and manual migration ZIP.
- Three generated `AWS::IAM::Role` execution roles with log permissions; backend alone can invoke AI; backend/migration alone can read the SSM prefix and connect to the exact Aurora DB user.
- API Gateway v2 HTTP API, `$default` stage, routes for `/` and `/{proxy+}`, Lambda integration(s), and Lambda invoke permission(s).
- One private frontend `AWS::S3::Bucket` and one `AWS::S3::BucketPolicy` allowing only the CloudFront distribution.
- One `AWS::CloudFront::Distribution` and one `AWS::CloudFront::OriginAccessControl`.
- Three `AWS::Logs::LogGroup` resources with three-day retention.
- SAM/CloudFormation-generated helper resources required for the declared HTTP API integration.

Expected function configuration:

- Backend: 256 MB, 28 seconds, reserved concurrency 5, **no provisioned concurrency**, no VPC config.
- AI: 256 MB, 15 seconds, reserved concurrency 2, **no function URL**, no API route, no VPC config.
- Migration: 256 MB, 60 seconds, reserved concurrency 1, no trigger, no VPC config.

Reserved concurrency is a free safety ceiling; it is not warm/provisioned capacity.

### Unexpected — STOP immediately

Stop if either change set or console review includes:

- `AWS::EC2::NatGateway`, NAT Gateway, Elastic IP, or public IPv4 allocation.
- EC2 instance, launch template, Auto Scaling group, or bastion host.
- ECS cluster/service/task, Fargate, EKS, or container service other than Lambda/ECR.
- Application Load Balancer, Network Load Balancer, ALB, NLB, target group, or listener.
- VPC, subnet, route table, internet gateway, security group, or interface VPC endpoint/PrivateLink endpoint.
- SageMaker, Bedrock, OpenSearch, ElastiCache, RDS Proxy, or Secrets Manager.
- Lambda alias/version with `ProvisionedConcurrencyConfig`, provisioned Lambda concurrency, Function URL, or public AI integration.
- Aurora/RDS resource in the application stack; Aurora express is a separate, manually verified action.
- Optional paid Multi-AZ database selection, manually added reader/replica, Global Database, or cross-Region database.
- Route 53 hosted zone/record, custom domain, non-default certificate, or paid WAF/WebACL.
- Customer-managed KMS key, paid dashboard, custom metric, Data API, or unexpected log export.
- `CAPABILITY_NAMED_IAM` request or wildcard IAM actions/resources not explained by the template.
- Replacement of an existing unrelated resource or deletion/update outside the two named project stacks.

## 5. Final Expected AWS Resources

### Lambda

- `dcs-ticket-system-backend` ZIP function.
- `dcs-ticket-system-ai` container-image function.
- `dcs-ticket-system-migrate` ZIP function, manually invoked once.
- API Gateway permission for backend invocation.
- No function URLs, aliases, provisioned concurrency, layers, or VPC attachments.

### API Gateway

- One API Gateway v2 **HTTP API**.
- One `$default` stage.
- Root and greedy proxy routes/integration to backend.
- Restrictive CloudFront-origin CORS and request throttling.

### S3

- One private deployment-artifact bucket from the bootstrap stack, with seven-day lifecycle.
- One private frontend bucket with versioning suspended.
- One frontend bucket policy granting CloudFront read-only access.

### CloudFront

- One distribution using the generated CloudFront domain.
- One Origin Access Control signing S3 requests with SigV4.
- No alias, custom certificate, Route 53, or WAF.

### ECR

- One private `dcs-ticket-system-ai` repository.
- One immutable AI image for the deployment; lifecycle retains no more than two.

### SSM

Under `/dcs-ticket-system/prod/`:

- `DB_IAM_AUTH` — Standard String, `true`.
- `DB_HOST` — Standard String.
- `DB_PORT` — Standard String, `5432`.
- `DB_NAME` — Standard String, normally `postgres`.
- `DB_USER` — Standard String, normally `postgres`.
- `DB_SSL_ROOT_CERT` — Standard String, `/var/task/global-bundle.pem`.
- `JWT_EXPIRE_MINUTES` — Standard String, `1440`.
- `JWT_SECRET` — Standard SecureString using the AWS-managed SSM key.

### CloudWatch

- `/aws/lambda/dcs-ticket-system-backend`, three-day retention.
- `/aws/lambda/dcs-ticket-system-ai`, three-day retention.
- `/aws/lambda/dcs-ticket-system-migrate`, three-day retention.
- Default AWS service metrics only; no paid dashboard, custom metric, detailed API metrics, or log export.

### IAM

- Three Lambda execution roles generated by SAM.
- Backend role: logs, read only the project SSM path, connect only as the selected Aurora user, invoke only the AI function.
- Migration role: logs, read only the project SSM path, connect only as the selected Aurora user.
- AI role: logs only.
- RDS service-linked role may be created by AWS for Aurora; it has no direct IAM charge.

### Budgets

- One `dcs-ticket-system-monthly-cost` monthly cost budget.
- Actual-cost email notifications at $1, $3, and $5. An alert does not stop resources automatically.

### Aurora PostgreSQL

- One manually approved Aurora PostgreSQL Serverless cluster created exclusively through **express configuration**.
- AWS-selected covered instance topology; add no manual instance/reader.
- Aurora Standard storage, under 1 GiB assignment data.
- Managed internet access gateway and IAM-only authentication.
- No customer VPC, password, Secrets Manager, Data API, RDS Proxy, log export, Global Database, or manually selected Multi-AZ add-on.

## 6. Zero-Cost Safety Check

| Resource | Can charge while idle? | Expected assignment usage | Allowance/dependency | Required safety action |
|---|---|---:|---|---|
| Backend Lambda | Normally no compute charge; code storage contributes to account storage | <5,000 requests, ~1,250 GB-s conservative | Lambda monthly allowance/credits | 256 MB; reserved—not provisioned—concurrency; delete after marking |
| AI Lambda | Normally no compute charge; image remains in ECR | <1,000 requests, ~1,000 GB-s conservative | Lambda monthly allowance/credits | Start 256 MB; increase only after Max Memory evidence; no public endpoint/provisioned concurrency |
| Migration Lambda | No compute while idle | One or a few invocations | Lambda allowance | Invoke only with confirmation payload; inspect result; delete with stack |
| HTTP API | No request charge with no calls | <5,000 calls | API Gateway Free Tier/credits | HTTP API only; throttle 10 requests/s, burst 20; monitor `Count` and unexpected traffic |
| Frontend S3 | **Yes**, stored objects persist | <20 MB, tiny request count | S3 allowance/credits | No versioning; private; remove objects before stack deletion |
| Artifact S3 | **Yes**, artifact persists until lifecycle/deletion | ~50 MB backend package/template | S3 allowance/credits | Seven-day expiry; do not use SAM auto-resolve bucket; empty during cleanup |
| CloudFront | Depends on selected plan; distribution can receive traffic | <1 GB, <10,000 requests | Flat-rate Free plan or standard allowance/credits, account-dependent | Confirm plan first; generated domain only; disable/delete after evidence |
| ECR | **Yes**, image storage persists | One compressed AI image, maximum two retained | ECR allowance/credits | Record size; immutable tag; lifecycle max two; delete repository after marking |
| CloudWatch Logs | **Yes**, ingestion and retained bytes are metered | <100 MB | CloudWatch log allowance/credits | Three-day retention; no debug flood, custom metrics, dashboard, or exports |
| Standard SSM parameters | No additional parameter charge at standard throughput | Eight parameters | Standard Parameter Store allowance | Keep Standard tier; no higher throughput; delete project prefix during cleanup |
| IAM | No direct charge | Three roles/policies | No direct fee | Least privilege; remove with stacks |
| Budget | Depends on number/type of budgets | One cost budget | Confirm account's included budget allowance | Do not create duplicates; verify email; remember it does not stop charges |
| Aurora express | **Yes/plan-dependent**; capacity/storage/backups can meter even with no app traffic | <1 GiB, <500 tickets | Explicit Free Plan/credits are mandatory | Confirm exact console coverage/end date; no added instances/features; delete cluster and snapshots immediately after marking |
| Aurora managed gateway | Part of express service | Tiny IAM/TLS connections | Express Free Plan/credits | Do not replace with NAT, endpoint, public IPv4, or customer VPC |

## 7. Deployment Order

Every AWS-mutating step below requires later explicit authorization.

1. Complete and record every manual Billing/Free Plan/account check.
2. Confirm Singapore Region and Aurora express coverage; stop if the covered option is unavailable.
3. Complete disposable PostgreSQL 16 migration, persistence, AI-up, and AI-down tests.
4. Build/test the AI Lambda image locally; record image ID and size.
5. Run `cfn-lint infrastructure/bootstrap.yaml infrastructure/template.yaml` again.
6. Create—but do not execute—the bootstrap change set for artifact S3, ECR, and budget.
7. Review bootstrap resources; execute only after approval, then confirm the $1/$3/$5 notification subscriptions.
8. Create Aurora PostgreSQL through the verified **express configuration** dialog; change nothing outside approved limits.
9. Record Aurora endpoint, Region, database name/user, and cluster resource ID; test CloudShell/console-generated IAM connectivity.
10. Run `infrastructure/prepare-parameters.ps1` with a fresh long random JWT secret; verify all parameters are Standard and only JWT is SecureString.
11. Build/tag/push the tested AI image to the bootstrap ECR repository; use an immutable tag/digest.
12. Rebuild the backend artifact with `infrastructure/build-backend.ps1`; confirm it remains below Lambda ZIP/uncompressed limits.
13. Package the SAM template using the known bootstrap artifact bucket. Do not use `--resolve-s3` or `--resolve-image-repos`.
14. Create—but do not execute—the application CloudFormation change set with AI image URI, Aurora resource ID/user, and SSM prefix.
15. Review the complete transformed change set against Section 4 and `AWS_RESOURCE_INVENTORY.md`.
16. Execute the approved application change set.
17. Invoke `dcs-ticket-system-migrate` once with `{"confirm":"upgrade-head"}`; inspect logs and verify Alembic head.
18. Test backend health and direct private AI invocation before uploading frontends.
19. Run `infrastructure/publish-frontends.ps1` with stack outputs; verify customer root and `/staff/index.html`.
20. Run the smoke test below, including forced AI failure/recovery if practical.
21. Inspect Billing/Free Tier dashboards immediately; stop/rollback on unexpected cost or resource.
22. Capture report screenshots in Section 9 order.
23. Schedule cleanup immediately after the final demonstration/marking window.

## 8. Smoke Test

Use the CloudFormation `ApiUrl`, `FrontendUrl`, and `StaffFrontendUrl` outputs. Never include JWTs/passwords in screenshots.

1. `GET {ApiUrl}/health`: HTTP 200; database `connected`; AI `reachable`.
2. Invoke AI from the Lambda console with a private test event or through a real ticket: response contains category and priority; confirm no AI Function URL exists.
3. Customer UI/API `POST /auth/register`: HTTP 201 and role `customer`.
4. `POST /auth/login`: HTTP 200 and bearer JWT returned.
5. Authenticated `POST /tickets`: HTTP 201.
6. Created ticket contains non-empty category, priority, department, SLA, model version, and normal workflow status.
7. Staff dashboard login with securely seeded staff account: `/auth/login` and `/auth/me` succeed with staff role.
8. Staff `/tickets` and `/stats`: new customer ticket is visible; filters/statistics load.
9. Staff `PATCH /tickets/{id}`: move to `in_progress` or `resolved`; HTTP 200.
10. Customer `/tickets/{id}` or refreshed customer list: updated shared status is visible.
11. Customer isolation: a second customer receives 404/does not see the first customer's ticket.
12. AI failure safety: force one authorized test failure only if it can be done without changing infrastructure; verify stored `pending_classification`, restore AI, call `/tickets/{id}/reclassify`, and confirm classification.
13. CloudWatch: confirm duration, init duration where present, errors, and `Max Memory Used`; no secret values in logs.
14. Billing: confirm no unexpected resource/charge appears after testing.

## 9. Screenshot Capture Order

1. Billing home showing plan type, plan/credit expiry, and balance; redact account/payment identifiers.
2. Free Tier page showing relevant service usage.
3. $1/$3/$5 budget notifications and confirmed email subscription.
4. Aurora express review/coverage evidence before creation.
5. Aurora database overview after approved creation: engine, serverless/express status, IAM authentication; hide endpoint/account identifiers if required.
6. Local PostgreSQL Alembic head and passing integration summaries.
7. AI Docker image size and successful local Lambda event output.
8. Bootstrap and application CloudFormation stacks in `CREATE_COMPLETE`.
9. CloudFormation Resources tabs showing the expected inventory and no VPC/load-balancer resources.
10. Lambda backend configuration: 256 MB, timeout, no VPC, no provisioned concurrency.
11. Lambda AI configuration: image, 256 MB, no VPC, no Function URL; private invoke policy.
12. API Gateway HTTP API routes/stage and invoke URL.
13. S3 buckets showing private/public-access-block settings and artifact lifecycle; do not expose object URLs containing credentials.
14. CloudFront distribution, generated domain, enabled status, and S3 OAC origin.
15. ECR repository with one image and recorded image size/tag/digest.
16. SSM parameter names/types only; never reveal values or SecureString contents.
17. CloudWatch three-day retention and successful migration/backend/AI log summaries.
18. Customer registration/login/ticket submission and classified result.
19. Staff login, ticket table/statistics, and status update.
20. Customer page showing the updated shared status.
21. Optional AI-failure `pending_classification` and successful later reclassification.
22. Final Billing/Free Tier view after tests.
23. Architecture diagram matching the deployed serverless resources.

## 10. Rollback

If application deployment or tests fail:

1. Stop frontend upload/testing to prevent additional requests.
2. Save only sanitized CloudFormation events and CloudWatch error evidence.
3. If the application stack is still `CREATE_IN_PROGRESS`, allow CloudFormation automatic rollback; do not manually delete resources mid-rollback.
4. If rollback is disabled or the stack is `CREATE_COMPLETE`, empty the frontend bucket, then delete the application stack.
5. Verify backend, AI, migration functions; HTTP API; distribution/OAC; frontend bucket/policy; log groups; and IAM roles are gone. CloudFront deletion can take time.
6. Delete project SSM parameters.
7. If the fault is database-related, export no data unless required; delete the Aurora cluster without a final snapshot for this disposable assignment and delete any retained snapshots.
8. Delete ECR images, then the bootstrap stack after emptying its artifact bucket.
9. Inspect CloudFormation retained resources, all Regions, Billing, Cost Explorer, public IPv4, NAT Gateways, VPC endpoints, ECR, RDS snapshots, and S3.
10. Keep budget alerts until the following bill closes.

Never “fix” rollback by adding NAT, a public AI endpoint, an EC2 bastion, a load balancer, paid database topology, or broader IAM permissions without a new review and approval.

## 11. Cleanup

Final removal order after screenshots/marking:

1. Record final application evidence and current Billing/Free Tier values.
2. Disable testing and stop sharing the generated URLs.
3. Empty the frontend S3 bucket.
4. Delete the application CloudFormation stack; wait for `DELETE_COMPLETE`.
5. Confirm CloudFront distribution/OAC, HTTP API, all three Lambdas, log groups, generated Lambda permissions, and IAM roles are gone.
6. Delete all parameters under `/dcs-ticket-system/prod/`.
7. Delete Aurora express without a final snapshot; delete automated/manual snapshots and confirm no retained backup storage.
8. Delete AI image(s) from ECR.
9. Empty the bootstrap artifact bucket, including incomplete uploads if any.
10. Delete the bootstrap stack, which removes ECR, artifact bucket, and budget.
11. Check every enabled Region for Aurora/RDS, snapshots, Lambda, API Gateway, ECR, S3, CloudWatch log groups, public IPv4, NAT Gateways, load balancers, and VPC endpoints.
12. Check global CloudFront, IAM, Budgets, and Route 53 views.
13. Review Bills and Cost Explorer immediately and again after AWS billing data settles.
14. Retain a simple budget/billing alert only if its continued presence is confirmed free and desired; otherwise remove it after the next bill closes.

## Final Gate

**READY FOR DEPLOYMENT: NO**

Remaining blockers:

1. Manual AWS Free Plan, credit, CloudFront, and Aurora express coverage verification.
2. Real PostgreSQL 16 Alembic, persistence, AI-up, and AI-down integration test.
3. Final AI Lambda Docker image build, local invocation, and measured image size.
4. Generated bootstrap/application CloudFormation change-set review.
5. Explicit user authorization to create AWS resources.
