# System Audit

Audit date: 20 August 2026

Scope: all application source, configuration, dependency, test, model, and dataset files supplied in the workspace. The assignment PDF and report template are reference artifacts, not executable application components. No secret files or credentials were found or inspected.

## Current Technology Stack

| Area | Actual implementation |
|---|---|
| Customer frontend | Single static HTML document, Tailwind CSS CDN, Font Awesome CDN, vanilla JavaScript |
| Staff dashboard | One React JSX component using Recharts, Lucide React, and Tailwind utility classes; no React project/build configuration |
| Backend | Python FastAPI, Uvicorn, Pydantic, SQLAlchemy 2, HTTPX |
| AI service | Separate Python FastAPI service, scikit-learn Joblib pipelines |
| Authentication | Backend-issued HS256 JWT bearer tokens; bcrypt password hashes; `customer` and `staff` roles |
| Local database | SQLite (`sqlite:///./tickets.db`) |
| Intended cloud database | PostgreSQL via `DATABASE_URL` and `psycopg2-binary` |
| Tests | Script-based HTTP smoke tests; no pytest suite |
| Containers/IaC | Not found |
| AWS configuration | Not found |

## Current Project Structure

- `member2_backend/index.html`: complete customer-facing static page colocated beside the backend `api/` directory, with registration, login, ticket submission, listing, details, and local drafts. Deployment still publishes it as `/customer/index.html` through S3 and CloudFront.
- `member2_backend/`: independently runnable FastAPI backend, SQLAlchemy models, JWT/bcrypt authentication, routing/SLA logic, seed script, API contract, and HTTP smoke test.
- `Member3_AI_Backend_/Member3_AI_Backend/`: independently runnable FastAPI inference service, two trained Joblib models, a 300-row synthetic CSV dataset, contract, and client test.
- `member5_staff_dashboard.jsx`: visually substantial but isolated React component backed entirely by generated mock data.
- `docs/`: initially contained backend component documentation only; no system-level cloud documentation.

This is a loose collection of separately delivered components, not a configured monorepo. There is no root build command, package manifest, compose file, or unified environment configuration.

## How Components Currently Communicate

```text
Customer HTML --HTTP/JWT--> Backend FastAPI :8001
Backend FastAPI --HTTP JSON--> AI FastAPI :8000
Backend FastAPI --SQLAlchemy--> SQLite (local) or PostgreSQL (configured)
Staff JSX --X--> generated mock data only (not connected)
```

The backend is the integration hub. It sends `{ "complaint": "..." }` to `POST /predict`, receives category/priority values and confidence scores, calculates a department and SLA, then stores the result. If AI is unavailable, it stores the ticket as `pending_classification` with safe defaults. Customers use JWT bearer authentication and only receive their own tickets. Staff-only backend endpoints support all-ticket access, filtering, status changes, reclassification, and statistics.

## Member 1 Audit

| Requirement | Status | Evidence / issue |
|---|---|---|
| Customer-facing website | PASS | Complete static page is present. |
| Login page | PASS | Calls `POST /auth/login`, stores JWT, handles errors. |
| Registration page | PASS | Calls `POST /auth/register`. |
| Ticket submission | PASS | Authenticated `POST /tickets` using the correct `{complaint}` contract. |
| Ticket status page | PASS | Lists own tickets and retrieves ticket detail. |
| Form validation | PASS | Visible-character check, password checks, browser input constraints. The frontend's email-domain allowlist is stricter than the backend and is a product-policy mismatch. |
| Responsive design | PASS | Responsive Tailwind layout is present. |
| Correct API integration | PARTIAL | Backend routes and fields match, but API base URL is hardcoded to localhost. Suspension/deletion exists only in localStorage and is not a server operation. |
| Loading/error handling | PARTIAL | Submission has a loading state and errors are displayed; ticket list/detail loading states are limited. |

## Member 2 Audit

| Requirement | Status | Evidence / issue |
|---|---|---|
| Main backend server | PASS | FastAPI application is present. |
| Receive/validate complaints | PASS | Pydantic length bounds plus trimmed-input validation. |
| Connect frontend, AI, database | PASS | Contracts align and failures are handled. |
| REST API | PASS | Authentication, tickets, reclassification, stats, and health routes. |
| Ticket routing | PASS | Explicit category-to-department and priority-to-SLA mapping. |
| Authentication | PASS | bcrypt hashes, signed expiring JWTs, role guard. |
| Authorization | PASS | Ownership checks and staff-only dependencies. |
| Responses/error handling | PASS | Appropriate 4xx/503 behavior and an AI fallback. |
| Database transactions | PARTIAL | Commits are used, but write paths do not consistently catch/rollback database errors. |
| Production readiness | PARTIAL | Development JWT fallback and permissive default CORS are unsafe if deployment variables are omitted. Health output exposes the AI service URL. No migrations or structured logging. |

## Member 3 Audit

| Requirement | Status | Evidence / issue |
|---|---|---|
| Category classification | PASS | Persisted scikit-learn pipeline loaded at startup. |
| Priority prediction | PASS | Separate persisted pipeline and probability output. |
| Dataset | PASS | 300-row synthetic academic CSV with complaint/category/priority. |
| Model inference API | PASS | `POST /predict` contract matches backend client. |
| Input validation | PASS | 3–2000 character validation plus post-trim check. |
| Health check | PASS | Reports both models loaded and model version. |
| Evaluation/results | NOT FOUND | No training code, evaluation metrics, confusion matrix, or reproducible model-building record was supplied. |
| Model metadata | PARTIAL | Code supports `model_metadata.json`, but the file is absent and defaults are embedded. |
| Dependency/runtime reproducibility | PARTIAL | Requirements pin very new versions; no container and no Python version lock. Binary models may be sensitive to scikit-learn version. |

## Member 4 Audit

| Requirement | Status | Evidence / issue |
|---|---|---|
| Database design | PASS | Relational users/tickets schema with foreign key and useful indexes. |
| Cloud-ready DB configuration | PARTIAL | PostgreSQL URL support exists, but there are no migrations, SSL settings, or deployed database. |
| AWS infrastructure | NOT FOUND | No resources or configuration supplied. |
| Frontend/backend/AI deployment | NOT FOUND | No deployment artifacts. |
| Networking/security groups | NOT FOUND | Not yet designed/implemented. |
| Environment variable contract | PARTIAL | Backend example exists; frontend and staff configuration do not. |
| Secrets management | PARTIAL | Backend uses environment variables, but secure AWS storage is not implemented. |
| Logging/monitoring | NOT FOUND | No structured logs, CloudWatch setup, or alarms. |
| Scalability/reliability documentation | NOT FOUND | Backend AI fallback is a good implemented reliability mechanism; cloud design is absent. |

## Member 5 Audit

| Requirement | Status | Evidence / issue |
|---|---|---|
| Staff dashboard UI | PARTIAL | Rich JSX UI exists, but it is not a runnable application. |
| Display tickets | FAIL | Uses randomly generated mock tickets. |
| Search/filter | PARTIAL | Works only against mock data in the browser; fields/status/category values differ from backend. |
| Update tickets | FAIL | Optimistic mock function never calls the backend. |
| AI category/priority/status | FAIL | Displays fabricated fields. |
| Charts/statistics | PARTIAL | Client-side charts work conceptually against mock data; `/stats` is unused. |
| Staff authentication/authorization | NOT FOUND | No login or JWT handling. |
| Integration testing | NOT FOUND | No runnable project or integration tests. |

## Integration Problems

| Severity | Problem | Impact |
|---|---|---|
| CRITICAL | Staff dashboard is mock-only and has no package/build scaffold. | Required staff workflow and end-to-end update/status demonstration cannot run. |
| HIGH | Customer API URL is hardcoded to `http://127.0.0.1:8001`. | Deployed frontend would still call the user's computer and HTTPS pages would face mixed-content blocking. |
| HIGH | No Dockerfiles, compose setup, IaC, or AWS deployment configuration. | System cannot be reproduced or deployed as requested. |
| HIGH | No database migration system. | `create_all` creates new tables but cannot safely evolve an existing deployed schema. |
| HIGH | Default JWT secret is known and CORS defaults to `*`. | Unsafe if production environment configuration is missed. |
| MEDIUM | Dashboard uses `New`, `Escalated`, title/customer/assignment fields and capitalized categories/priorities that do not exist in the backend schema. | Direct integration would render or update incorrect values. |
| MEDIUM | Customer “suspend/delete” state exists only in localStorage. | It is device-specific, invisible to staff, and misleading as a server action. |
| MEDIUM | Registration email policy differs: frontend restricts five public domains while backend accepts any valid email. | Valid backend users can be prevented from registering in the UI. |
| MEDIUM | Backend synchronous AI call occurs inside request handling. | Each ticket submission waits for inference timeout and can consume worker capacity. Acceptable for the prototype, but should be documented. |
| MEDIUM | AI evaluation/training evidence is absent. | Model quality cannot be independently verified or reproduced. |
| LOW | Health response includes the configured AI URL. | Unnecessary internal topology disclosure. |
| LOW | CDN-based customer UI needs internet access and lacks pinned/subresource-integrity-controlled assets. | Offline demo can lose styling/icons. |

## Missing Requirements

- A real integrated, authenticated staff application.
- Root-level local orchestration and consistent environment configuration.
- Production builds and container definitions for backend and AI.
- Database migrations and deployed PostgreSQL evidence.
- AWS architecture, IaC, deployment, URLs, logs, and screenshots.
- AI evaluation results and reproducible training artifacts.
- Cloud/security/cost/deployment/report/demo documentation.
- Automated full browser integration test; current backend smoke test covers the API workflow only.

## Local Testing Plan

1. Create isolated Python environments using the declared requirements.
2. Start AI on port 8000 and verify health, five representative predictions, invalid input, and model output domains.
3. Start backend on port 8001 with a temporary SQLite database and non-default JWT secret.
4. Seed a staff account, then execute registration, duplicate registration, login, ownership/authorization, submission/classification/storage, staff listing/filtering/update, customer status visibility, reclassification, and statistics checks.
5. Repeat backend ticket submission with AI stopped to verify the `pending_classification` fallback.
6. Serve the static customer page over HTTP and verify browser/API behavior.
7. Scaffold and integrate the staff dashboard, then build it and verify against the live backend.
8. Record only observed results; mark browser-only checks partial if browser automation is unavailable.

## Recommended AWS Architecture Based on Actual Code

The revised candidate is S3/CloudFront static hosting, API Gateway HTTP API, FastAPI through Mangum in a 256 MB backend Lambda, a separate private AI Lambda container invoked with IAM, and an eligibility-confirmed Aurora PostgreSQL Free Plan database. Standard SSM parameters and three-day CloudWatch logs avoid unnecessary recurring services. No AWS resources have been created.

The backend Lambda keeps the existing routes and failure behavior. The AI remains a separate distributed service without a public endpoint. Both functions stay outside a customer VPC. The backend uses direct IAM-protected Lambda invocation and TLS/IAM PostgreSQL access through the managed internet access gateway provided by Aurora Free Plan express configuration. No NAT, endpoint, subnet, or public IPv4 allocation is planned.

## Cost and deployment blockers

- The account plan, creation date, credits, current usage, CloudFront plan, and exact database coverage are unknown.
- Aurora/RDS, ECR, S3 objects, and retained logs can charge while idle or after eligibility expires.
- Docker, PostgreSQL, `psql`, and `winget` are unavailable, so the real PostgreSQL/container tests remain blocked locally.
- Browser-level tests remain pending; service/API and staff production-build tests passed.
- `AWS_ZERO_COST_PLAN.md` is the authoritative account checklist and accidental-charge analysis.
