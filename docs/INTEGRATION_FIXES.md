# Integration Fixes

> Current source location: the customer frontend now lives at `member2_backend/index.html`. Historical file lists below retain the filenames used when each fix was originally made.

## 1. Runtime-configurable customer API URL

**Problem:** The customer website always called `http://127.0.0.1:8001`.

**Cause:** The backend base URL was a JavaScript constant embedded in the HTML.

**Files changed:** `member1_index.html`, `config.js`

**Solution:** The page now reads `window.APP_CONFIG.API_BASE_URL` from a small public runtime configuration file and retains localhost only as a local-development fallback. Deployment can replace `config.js` without rebuilding the static page.

**Why required:** An AWS-hosted HTTPS page cannot reach a backend through a visitor's loopback address, and browsers can block HTTP calls from an HTTPS page as mixed content.

## 2. Remove internal AI URL from public health response

**Problem:** `GET /health` returned the configured internal AI service URL.

**Cause:** The development health response included topology useful during early integration.

**Files changed:** `member2_backend/api/main.py`, `member2_backend/API_CONTRACT.md`

**Solution:** The health response retains the actionable `reachable`/`unreachable` state but no longer returns the internal URL.

**Why required:** Public health endpoints should reveal only the minimum information needed for health monitoring.

## 3. Integrated staff dashboard

**Problem:** Member 5 supplied a standalone mock JSX component with no runnable build or backend connection.

**Cause:** The component used generated tickets and fake update functions, and expected unsupported status, assignment, customer-email, and escalation fields.

**Files changed:** new `staff-dashboard/` Vite application.

**Solution:** Preserved the dark console design, charts, filters, table, and drawer. Added staff JWT login/logout/session validation, real `/tickets` and `/stats` reads, backend priority/status filters, client-side complaint/ID/category search, real status PATCH, pending-classification display/retry, and operational loading/error/empty states.

**Why required:** The staff update and customer status-return flow is a core assignment requirement.

## 4. Removed misleading customer suspension

**Problem:** The customer portal presented ticket suspension/deletion as though it were shared system state, but stored it only in one browser's localStorage.

**Cause:** No backend endpoint or ticket lifecycle value exists for suspension/deletion.

**Files changed:** `member1_index.html`.

**Solution:** Removed the modal, local functions, local status override, and button. Drafts remain local because they are explicitly presented as unsent drafts.

**Why required:** Suspension/deletion is not a core documented requirement, and retaining the control would misrepresent database behavior during the demonstration.

## 5. Restricted default CORS

**Problem:** The backend defaulted to `*`.

**Cause:** Frontend hosts were initially unknown.

**Files changed:** `member2_backend/api/main.py`, `.env.example`.

**Solution:** Default local origins are explicit and comma-separated; deployment supplies the CloudFront origin through `CORS_ORIGINS`.

## 6. Reproducible database migrations

**Problem:** Production schema creation depended on SQLAlchemy `create_all`.

**Cause:** No migration framework was supplied.

**Files changed:** backend requirements, Alembic configuration, initial migration, startup configuration, Docker entrypoint.

**Solution:** Alembic now creates the fresh schema. Local development may retain automatic creation; deployment disables it and runs `alembic upgrade head` before the backend starts.

**Why required:** RDS initialization must be repeatable and versioned rather than manual.

## 7. Lambda runtime adaptation

**Files changed:** backend requirements, `member2_backend/lambda_handler.py`, backend Lambda Dockerfile, AI Lambda handler/Dockerfile, and AI client.

**Solution:** Mangum accepts API Gateway HTTP API v2 events without rewriting backend business logic. The backend can invoke the private AI function synchronously through the AWS SDK when `AI_INVOCATION_MODE=lambda`; HTTP mode remains available locally. Invocation errors are translated to the existing unavailable signal, so ticket persistence and later reclassification remain intact.

## 8. Reproducible AI packaging compatibility

The saved artifacts identify scikit-learn 1.9.0, for which the available Linux CPython 3.12 package index did not supply a wheel. The Lambda runtime pins scikit-learn 1.7.2 and restores the removed `LogisticRegression.multi_class="deprecated"` compatibility field after loading. No model was retrained. All 300 supplied rows produced identical labels and probabilities rounded to 12 decimals in both runtimes (SHA-256 `d535edf023204be814e3f0e6007f032427bd03cabea56d6dd9796083aa3c6e7e`).
