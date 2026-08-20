# `test_backend.py` — the end-to-end smoke test

## Role

One script that exercises the whole system over real HTTP: it registers users, logs them
in, submits complaints, checks that classification and routing happened, and verifies
that customers cannot reach each other's data or the staff endpoints. If it passes, the
backend works. If it fails, the message names the assertion that broke.

It is deliberately one file of plain assertions rather than a test framework. There are
no fixtures, no `conftest.py`, and no per-function unit tests — a teammate can unzip the
folder and run one command without learning pytest.

## Concepts

**Smoke test.** Not exhaustive coverage — a fast pass through the main paths that would
catch anything seriously broken. The name comes from hardware: power it on and see if
smoke comes out.

**End-to-end.** It talks to a *running server* over HTTP, exactly as Member 1's frontend
will. Nothing is mocked. That means it also verifies the pieces unit tests would miss:
that the server starts, that routes are registered at the paths the contract promises,
that JSON serialisation works, that the database accepts the writes.

**The two-run protocol.** This is the important idea, and it is unusual:

```
Run 1: Member 3's AI service RUNNING   →  must pass
Run 2: Member 3's AI service STOPPED   →  must pass
```

The script detects which situation it is in by reading `GET /health` first, then asserts
*different expected outcomes* for each. Run 2 is what proves the reliability design
works. A test suite that only ever runs with all dependencies healthy cannot tell you
anything about what happens when they are not — which, for a distributed systems
assignment, is the interesting half.

## The substance

### Setup

```python
BASE_URL       = "http://127.0.0.1:8001"
STAFF_EMAIL    = "staff@support.com"
STAFF_PASSWORD = "staff1234"
```

The staff credentials come from `seed.py`.

### `auth(token) -> dict`

Builds `{"Authorization": f"Bearer {token}"}`. Used on nearly every call.

### `register_and_login(client, label) -> (email, token)`

Creates a throwaway customer with a timestamped email:

```python
email = f"test_{label}_{int(time.time() * 1000)}@example.com"
```

**Why unique emails matter.** Emails are unique in the database, so a fixed address would
make the second run of the script fail on a `400`. Timestamping means the script can be
run repeatedly without any cleanup step — a small design choice that removes a whole class
of "it passed yesterday" confusion.

The helper also asserts that registering the same email twice returns `400`, so duplicate
rejection is covered on every call.

### The checks, in order

| # | Check | Asserts |
|---|---|---|
| 1 | `GET /health` | `200`, `database == "connected"`; records whether the AI is up |
| 2 | register / duplicate / login / `/auth/me` | `201`, `400`, `200`, correct email |
| 3 | no token, and a garbage token | `401` on `GET` and `POST /tickets` |
| 4 | `"hi"` and `"      "` as complaints | `422` both — the Pydantic rule and the strip re-check |
| 5 | submit a valid complaint | `201`; ticket has a department, a priority, a deadline |
| 6 | *(AI up)* | `status == "open"`, category in the known set, department matches `routing.department_for()`, `classified_at` set, confidence in `[0, 1]` |
| 6 | *(AI down)* | `status == "pending_classification"`, `category is None`, department is General Enquiry, priority is medium |
| 7 | list and fetch as the owner | the list contains exactly that ticket; `GET /tickets/{id}` is `200` |
| 8 | second customer reads it | `404`; their own list is `[]` |
| 9 | customer calls staff endpoints | `403` on `PATCH`, `/stats`, `reclassify` |
| 10 | staff login | `200`, `role == "staff"` |
| 11 | staff lists everything | more than one customer's tickets visible |
| 12 | staff filters | every `priority=high` result is high; no `overdue=true` result is resolved or closed |
| 13 | staff changes status | `200` and the value changed; `"not_a_status"` → `422` |
| 14 | *(AI up)* reclassify | `200`, category filled in, status still `in_progress` |
| 14 | *(AI down)* reclassify | `503`, and re-fetching proves the ticket is unchanged |
| 15 | `/stats` | all seven keys present; `total_tickets == sum(by_status.values())` |

Two of these are worth singling out.

**Check 6 imports from the application:**

```python
from api import routing
...
assert ticket["department"] == routing.department_for(ticket["category"])
```

Rather than hardcoding "billing_payment means Billing and Payment", it asserts the API's
output agrees with the routing table. Change the table and the test follows automatically;
what is being verified is that routing was *applied*, not what the table happens to say.

**Check 14 (AI down) verifies a non-effect:**

```python
assert reclassified.status_code == 503
unchanged = client.get(f"/tickets/{ticket_id}", ...).json()
assert unchanged["category"] is None
assert unchanged["status"] == "in_progress"
```

It is not enough that the call returned an error — the ticket must be *untouched*, which
is what `db.rollback()` in the endpoint exists to guarantee. Asserting the error code
alone would pass even if the rollback were removed.

### Graceful degradation

If the staff login fails, the script prints:

```
SKIPPED staff checks: no seeded staff account.
Run 'python seed.py' and try again.
```

and exits successfully after the customer-side checks. A missing seed is a setup problem,
not a code failure, and the message says how to fix it.

Similarly, `httpx.ConnectError` is caught at the bottom:

```
Could not reach the backend at http://127.0.0.1:8001.
Start it with start_backend.bat and try again.
```

Both exist because the most common failure when a teammate runs this is not a bug — it is
that they forgot a step.

## Gotchas / known ceilings

**It writes to the real database.** Every run leaves two new customers and a ticket
behind. Harmless for development, and it means the counts in `/stats` grow between runs
— which is why the assertions check *consistency* (`total == sum of parts`) rather than
exact numbers. A production suite would use a separate test database.

**Assertions stop at the first failure.** Plain `assert` means one broken check hides
everything after it. A framework would report all failures at once. For a script whose
job is "is this broken, yes or no", the first failure is the useful information.

**The malformed-AI-response path is not covered.** Making Member 3's service return
something invalid on demand would need a stub server. The branch is a few lines in
`ai_client.py` and is reviewed rather than tested.

**Token expiry is not covered.** It would mean waiting 24 hours or restarting with a
different configuration mid-run. The behaviour lives inside PyJWT.

**No concurrency testing.** Nothing checks what happens when two staff members update the
same ticket simultaneously. Real answer: last write wins, no locking. Worth naming under
limitations.

## Running it

```
.venv\Scripts\python.exe test_backend.py
```

The backend must already be running. Run it twice — once with
`Member3_AI_Backend\start_api.bat` started, once with it stopped. Both runs must pass.

Expected output (AI service down):

```
AI service: unreachable

PASS  register, duplicate rejected, login, /auth/me
PASS  missing and invalid tokens rejected with 401
PASS  short and whitespace-only complaints rejected with 422
PASS  AI service down, ticket stored as pending_classification
PASS  customer sees their own ticket
PASS  another customer cannot read or list that ticket
PASS  staff-only endpoints refuse customers with 403
PASS  staff sees all tickets
PASS  staff filters work (8 high, 9 overdue)
PASS  staff can change status, invalid status rejected
PASS  reclassify returns 503 and leaves the ticket untouched
PASS  stats consistent (18 tickets total)

All checks passed.
```

With the AI service running, lines 4 and 11 change:

```
PASS  ticket classified as billing_payment / high and routed to Billing and Payment
PASS  reclassify succeeds without resetting workflow status
```

There is one more check that needs no server, covering the routing arithmetic directly:

```
.venv\Scripts\python.exe -m api.routing
```
