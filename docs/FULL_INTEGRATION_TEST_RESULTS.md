# Full Local Integration Test Results

Test date: 20 August 2026. Database: disposable SQLite integration database. No AWS resources were used.

| Test | Result | Evidence observed |
|---|---|---|
| Customer registration | PASS (API) | New unique customer returned 201. |
| Customer login | PASS (API) | JWT returned; `/auth/me` previously verified. |
| Ticket submission | PASS (API) | Ticket 15 created from the demonstration complaint. |
| Real AI category | PASS | `billing_payment`. |
| Real AI priority | PASS | `medium`. |
| Staff login | PASS (API) | Existing staff role token returned. |
| Staff ticket retrieval | PASS (API) | Ticket 15 appeared in authorized all-ticket response. |
| Statistics | PASS (API) | Staff-only `/stats` returned 200. |
| Staff status update | PASS (API) | Ticket 15 changed to `in_progress`. |
| Customer sees updated status | PASS (API) | Same customer's authorized GET returned `in_progress`. |
| AI unavailable submission | PASS | Ticket 16 persisted as `pending_classification` with null category. |
| AI recovery/reclassification | PASS | After AI restart, ticket 16 became `open`, `delivery_order`, `medium`. |
| Customer isolation | PASS | Supplied regression test proves Customer A cannot list/read Customer B ticket. |
| Customer blocked from staff API | PASS | PATCH, stats, and reclassification return 403. |
| Invalid/missing JWT | PASS | Returns 401. |
| Staff production build | PASS | Vite transformed 2,371 modules and produced deployable `dist/`. |
| Customer browser UI | BLOCKED | Browser-control runtime failed local initialization because access to `AppData` was denied. Services were reachable; UI source/config was inspected. |
| Staff browser UI | BLOCKED | Same browser-control environment failure. Authentication/API behavior was tested directly, but visual interaction is not claimed. |
| Docker workflow | BLOCKED | Docker executable is not installed/on PATH. Dockerfiles and compose configuration exist but are unexecuted. |
| PostgreSQL runtime | BLOCKED | No local PostgreSQL/Docker runtime. Alembic lifecycle passed on fresh SQLite; PostgreSQL compatibility remains to be run. |

## Required Local Gate

| Component/gate | Status |
|---|---|
| Customer frontend | PARTIAL — browser test blocked |
| Backend | PASS |
| AI inference | PASS |
| Staff dashboard | PARTIAL — builds and API contract passes; browser test blocked |
| Authentication | PASS at API level |
| Authorization | PASS |
| Ticket creation/retrieval/update | PASS |
| Customer status | PASS at API level |
| AI failure handling | PASS |
| End-to-end integration | PARTIAL — complete service/API path passed; browser UI execution blocked |

AWS deployment remains blocked because the required gate is not fully PASS.
