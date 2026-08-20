# Lambda Feasibility Results

Test date: 2026-08-20. These are local compatibility measurements, not CloudWatch measurements; no AWS function was created.

## Backend — PASS locally / cloud measurement pending

- Added Mangum and `lambda_handler.py`; API Gateway HTTP API v2-shaped events exercised the unchanged FastAPI routes.
- Linux Python 3.12 artifact: **48.76 MiB ZIP**, **114.51 MiB uncompressed**, 6,894 files. It fits the 50 MiB direct-ZIP and 250 MiB uncompressed limits narrowly; uploading through S3 is safer than console/direct upload.
- Start at **256 MB**, based on the previous approximately 76 MB local process measurement. Actual Lambda `Max Memory Used`, cold start, and request duration require cloud testing.
- Passed registration, login, JWT, `/auth/me`, AI-backed ticket creation/retrieval, and invalid-JWT checks through Mangum.

## AI — PASS using Lambda container / cloud measurement pending

- Direct event handler accepts health and prediction events; no public FastAPI endpoint is required.
- Linux dependency tree is **304.07 MiB uncompressed** before source/models. It exceeds the combined 250 MiB ZIP/layer uncompressed ceiling, so ZIP and Layer options are rejected. A Lambda container image is the selected method (10 GB image ceiling).
- Dependencies include scikit-learn 1.7.2, NumPy, SciPy, Joblib, and the approximately 100 KB supplied model artifacts.
- Local import/model-load time was **1.224 s**; first direct handler call **7.23 ms**; warm median **1.01 ms**. These are only cold-start indicators, not AWS latency promises.
- Previous local working set was approximately **137 MB**. Test 256 MB first; move to 512 MB only if CloudWatch shows insufficient headroom or failures.
- Five HTTP predictions passed. Direct event invocation, health, and malformed-request validation passed. The 300-row portability comparison produced identical labels/probabilities to 12 decimal places without retraining.

## Integration and degradation — PASS locally

The backend supports `AI_INVOCATION_MODE=lambda` and synchronous AWS SDK invocation. A mocked successful Lambda response was processed. A mocked invoke failure became `AIServiceUnavailable`, which the existing ticket service treats as `pending_classification`; later reclassification remains available.

## Remaining blockers

- Docker is absent, so the AI image cannot be built or measured as a compressed OCI image here.
- Docker/PostgreSQL/`psql`/`winget` are absent, so Alembic and full integration have not run against real PostgreSQL.
- AWS memory, init duration, normal duration, timeout behavior, and regional IPv6 service access are unmeasured because deployment is intentionally prohibited in this phase.
