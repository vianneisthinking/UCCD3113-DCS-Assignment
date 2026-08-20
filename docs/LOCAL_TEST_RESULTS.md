# Local Test Results

Test date: 20 August 2026

Environment: Windows, workspace-local Python 3.12 test environment, declared project dependencies, temporary SQLite database. These results do not represent an AWS deployment.

## AI Service

| Test | Result | Observed result |
|---|---|---|
| Service startup/model loading | PASS | Both Joblib pipelines loaded and Uvicorn started on port 8000. |
| Health | PASS | Service reported healthy and both models loaded. |
| Billing example | PASS | `billing_payment`, high priority. |
| Account example | PASS | `account_access`, high priority. |
| Technical example | PASS | `technical_support`, medium priority. |
| Delivery example | PASS | `delivery_order`, high priority. |
| General enquiry example | PASS | `general_enquiry`, low priority. |
| Client/API suite | PASS | 5/5 supplied prediction requests succeeded. |

The observed confidence values were relatively low (approximately 31.77%–70.90% for category and 35.84%–44.97% for priority). The API works, but these smoke tests are not a model-quality evaluation.

## Backend with AI Available

| Test | Result |
|---|---|
| Registration and duplicate rejection | PASS |
| Login and `/auth/me` | PASS |
| Missing/invalid token rejection | PASS |
| Short/whitespace complaint rejection | PASS |
| Submit → classify → route → store | PASS |
| Customer sees only own ticket | PASS |
| Staff-only authorization | PASS |
| Staff sees all tickets | PASS |
| Priority and overdue filters | PASS |
| Staff status update | PASS |
| Reclassification without workflow reset | PASS |
| Statistics consistency | PASS |

The submitted billing complaint was observed as `billing_payment` / `high`, routed to `Billing and Payment`.

## Backend with AI Unavailable

| Test | Result |
|---|---|
| Health reports AI unreachable | PASS |
| Ticket remains stored | PASS |
| Status is `pending_classification` | PASS |
| Safe default department/priority applied | PASS |
| Reclassification returns 503 | PASS |
| Failed reclassification leaves data unchanged | PASS |
| Remaining authentication/filter/update/stats checks | PASS |

## Post-fix Regression Checks

- Python source compilation: PASS.
- Customer runtime `config.js` wiring present: PASS (static inspection).
- Health response no longer contains the internal AI URL: PASS after service restart.
- Full supplied backend smoke suite after the health-response change: PASS with AI unavailable.

## Not Tested / Blocked

- Customer browser flow: not browser-tested in this pass; API calls and markup were inspected.
- Staff dashboard: cannot run because no React project exists and the component is mock-only.
- PostgreSQL: not provisioned locally; SQLite path tested.
- AWS: not attempted; no region, CLI authentication, or resources are available.
