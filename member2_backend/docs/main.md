# `api/main.py` — the API endpoints

## Role

This file owns every HTTP endpoint the system exposes, and one piece of genuine logic:
`apply_classification`, the function that decides whether a ticket gets classified by the
AI service or falls back to safe defaults. Everything else here is assembly — taking the
capabilities defined in the other five modules and wiring them to URLs.

That is the intended shape. When an endpoint body is three lines long, it is because
authentication, validation, routing and persistence each live somewhere they can be
understood on their own. If you find yourself adding real logic to this file, check
whether it belongs in `routing.py` instead.

## Concepts

**Decorators as routing.** `@app.post("/tickets")` above a function registers it as the
handler for that method and path. The function name is irrelevant to the URL.

**Dependency injection.** A parameter declared as `db: Session = Depends(get_db)` is not
passed by the caller — FastAPI calls `get_db()` and supplies the result. Same for
`user: User = Depends(get_current_user)`. This is why an endpoint's *signature* tells you
what it needs and who may call it, before you read a single line of its body.

Read these three signatures and you already know the permission model:

```python
def read_ticket(..., user: User = Depends(get_current_user))    # any logged-in user
def update_ticket_status(..., staff: User = Depends(require_staff))  # staff only
def health_check(db: Session = Depends(get_db))                 # no login at all
```

**Declared responses.** `response_model=TicketOut` filters the return value through that
schema. `status_code=201` sets the success code. Both appear in the generated
documentation, so `/docs` cannot drift out of date with the code.

## The substance

### Application setup

```python
app = FastAPI(title=..., description=..., version="1.0.0")
```

The title and description are what teammates see at `/docs`.

<a name="cors"></a>
**CORS.** Browsers block a page served from one origin from calling an API on another,
unless the API explicitly permits it. Member 1's site and this API are different origins,
so without CORS every request from his pages fails — with a browser console error, while
the same request from `/docs` or a test script works fine. That asymmetry makes it a
confusing bug to meet for the first time.

```python
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","), ...)
```

Defaults to `*` (any origin) because Member 1's domain does not exist yet. Narrow it to
his deployed URL once it does — an open CORS policy on a real API is a finding in a
security review.

```python
init_db()
```

Called at import time, so the tables exist before the first request. A fresh cloud
database needs no manual SQL.

### `GET /` and `GET /health`

`/` returns service name, version and a pointer to `/docs`.

`/health` is the one to understand:

```json
{ "status": "healthy", "database": "connected",
  "ai_service": "reachable", "ai_service_url": "http://127.0.0.1:8000" }
```

`database` is checked with `SELECT 1` — the cheapest query that proves a connection can
be obtained and used. `ai_service` uses `ai_client.is_reachable()`.

**The important design decision: an unreachable AI service does not make this service
unhealthy.** `status` is `"healthy"` whenever the database is connected, because the
backend can still accept and store complaints. Only a database failure produces
`"degraded"`.

This is not a technicality. Cloud platforms restart services that report unhealthy. If
this endpoint reported unhealthy whenever Member 3's service was down, the platform would
restart a perfectly functional backend during someone else's outage — turning one
service's failure into two. Health checks should report *this* service's ability to do
*its* job.

### `POST /auth/register` → `201`

Lowercases and strips the email, rejects duplicates with `400`, hashes the password,
creates the user with `role="customer"` — always, regardless of what the request
contained, because `RegisterRequest` has no role field to send.

### `POST /auth/login` → `200`

Looks up by email, verifies the password, returns a token.

```python
if user is None or not verify_password(payload.password, user.password_hash):
    raise HTTPException(401, "Incorrect email or password")
```

One condition, one message, for both "no such user" and "wrong password". Distinct
messages would let an attacker discover which email addresses are registered by reading
the error — *user enumeration*.

### `GET /auth/me` → `200`

Returns the current user. One line, because `get_current_user` did the work.

### `apply_classification(ticket, complaint) -> bool`

The heart of the file. Called by both `POST /tickets` and `POST /tickets/{id}/reclassify`.

```python
try:
    result = ai_client.classify(complaint)
except ai_client.AIServiceUnavailable:
    ticket.status      = "pending_classification"
    ticket.department  = routing.DEFAULT_DEPARTMENT
    ticket.priority    = routing.DEFAULT_PRIORITY
    ticket.sla_due_at  = routing.sla_due_at(routing.DEFAULT_PRIORITY, ticket.created_at or now)
    ticket.updated_at  = now
    return False

ticket.category   = result["category"]
...
ticket.status     = "open"
ticket.department = routing.department_for(result["category"])
ticket.sla_due_at = routing.sla_due_at(result["priority"], ticket.created_at or now)
return True
```

Three properties worth noticing:

**It never raises.** Both paths leave the ticket in a complete, storable state. That is
what makes the guarantee "a complaint is never lost" true by construction rather than by
the caller remembering to handle an error.

**It returns a boolean instead of raising.** `POST /tickets` ignores the return value —
either outcome is a success from the customer's point of view. `reclassify` checks it,
because a staff member who asked to retry needs to know whether it worked. One function
serving two callers with different needs.

**It modifies the ticket in place and commits nothing.** The caller owns the transaction.
This is what lets `reclassify` call `db.rollback()` and leave the ticket untouched.

Note `ticket.created_at or now`: on a brand-new ticket the deadline is measured from
submission time; on reclassify, from the *original* submission. A ticket that sat pending
for two hours does not get a fresh two hours added to its deadline.

### `POST /tickets` → `201`

```python
complaint = payload.complaint.strip()
if len(complaint) < 3:
    raise HTTPException(422, "Complaint must contain at least three visible characters.")
```

Pydantic already enforced `min_length=3` on the raw string — but `"      "` is six
characters and passes it. This second check runs after stripping. A literal `422` is used
rather than the Starlette constant, which was renamed between versions.

Then: build the `Ticket`, call `apply_classification`, `add` / `commit` / `refresh`,
return it. `refresh` reloads the row so the response carries the database-assigned `id`.

The endpoint has no error handling for the AI service, because `apply_classification`
cannot fail.

### `GET /tickets` → `200`

Builds a query in steps:

```python
query = db.query(Ticket)

if user.role != "staff":
    query = query.filter(Ticket.user_id == user.id)
```

**That conditional is the entire access control for listing.** A customer's query is
permanently scoped to their own rows; a staff query is not. There is no way for a
customer to widen it, because the filters below can only narrow further.

Optional filters — `status`, `department`, `priority` — are applied only when provided.
`ticket_status` is the Python parameter name with `alias="status"` as the query
parameter, because `status` is already the imported FastAPI module in this file.

The `overdue` filter:

```python
breached = (Ticket.sla_due_at < utcnow()) & (Ticket.status.in_(OPEN_STATUSES))
query = query.filter(breached if overdue else ~breached)
```

Overdue means *the deadline passed while the ticket was still live*. A resolved ticket
whose deadline has passed is not overdue — it was dealt with. `OPEN_STATUSES` comes from
`models.py`, shared with `/stats` so the two counts cannot disagree.

`&` and `~` rather than `and` and `not`: these are SQLAlchemy expression objects being
composed into SQL, not Python booleans being evaluated. Python's keywords cannot be
overloaded; the operators can.

### `get_visible_ticket(ticket_id, user, db) -> Ticket`

A plain helper, not a dependency, shared by `GET /tickets/{id}`.

```python
if user.role != "staff" and ticket.user_id != user.id:
    raise HTTPException(404, "Ticket not found")
```

**`404`, not `403`.** A `403` would confirm the ticket exists — telling a customer
something true about another customer's data. Identical responses for "does not exist"
and "not yours" reveal nothing. This is a real pattern in production APIs and a good
detail to mention if asked about security in the Q&A.

### `PATCH /tickets/{id}` → `200`, staff only

Sets `status` and `updated_at`. The valid values are enforced by the `Literal` in
`StatusUpdate`, so no validation appears here.

Note it does **not** call `get_visible_ticket` — staff can see everything, so the
ownership branch would be dead code. The guard is `Depends(require_staff)` in the
signature.

### `POST /tickets/{id}/reclassify` → `200`, staff only

Recovery for tickets stored during an outage.

```python
previous_status = ticket.status
classified = apply_classification(ticket, ticket.complaint)

if not classified:
    db.rollback()
    raise HTTPException(503, "AI service is unavailable. The ticket is unchanged.")

if previous_status != "pending_classification":
    ticket.status = previous_status
```

`db.rollback()` discards the fallback values `apply_classification` just wrote. Without
it, a failed retry would overwrite the ticket's `updated_at` and department for no
reason. Failure must be a no-op — the staff member can simply try again later.

The status restoration handles a subtle case: reclassifying a ticket already `in_progress`
should not shove it back to `open` and undo a colleague's work. Only a ticket that was
`pending_classification` advances. This is tested explicitly.

`503 Service Unavailable` is the correct code — the failure is a dependency being down,
and `503` conventionally means "try again later".

### `GET /stats` → `200`, staff only

```python
def count_by(db, column):
    rows = db.query(column, func.count(Ticket.id)).group_by(column).all()
    return {key: count for key, count in rows if key is not None}
```

One `GROUP BY` per dimension, executed by the database. The `if key is not None` filter
drops the null-category bucket that unclassified tickets would otherwise create — those
are reported separately as `pending_classification`.

Doing this on the server rather than sending every ticket to the browser to count is a
defensible architectural point: the aggregation happens next to the data, and the
dashboard's payload stays small no matter how many tickets exist.

## Gotchas / known ceilings

**`GET /tickets` has no pagination.** With 10,000 tickets, staff would receive all of
them. `.limit()` / `.offset()` with page parameters is the fix; unnecessary at
demonstration scale but the first thing to add if the dataset grew.

**Status transitions are unvalidated.** Any status can move to any other — `closed` can
go back to `pending_classification`. A state machine rejecting invalid transitions would
be more correct; for a demo where staff are trusted, it is machinery guarding against a
problem nobody has.

**No ticket assignment to individual staff.** Tickets are routed to a *department*, not a
person. Round-robin assignment was considered and skipped: it needs staff availability
tracking to be useful, and adds no marks to the architecture.

**The AI call blocks the request.** The customer waits up to 5 seconds when the service
is down. A background task or a queue would return instantly and classify afterwards, at
the cost of the frontend needing to poll for the result. The synchronous version was
chosen because it makes the failure visible and immediate — which is exactly what you
want to demonstrate on stage.

**`init_db()` runs at import.** Simple and effective, but it means importing this module
touches the database. A `lifespan` handler is the modern FastAPI equivalent; the
difference does not matter for a single-process deployment.

## Tests

`test_backend.py` drives every endpoint in this file over real HTTP. The full list is in
[test_backend.md](test_backend.md). The checks specific to this module's logic:

- `POST /tickets` returns `201` **both** when the AI service is running and when it is
  stopped, with different resulting state — the reliability guarantee
- a classified ticket's `department` equals `routing.department_for(its category)` —
  routing is actually applied, not just stored
- `GET /tickets` as customer B returns `[]` and `GET /tickets/{A's id}` returns `404`
- the `overdue=true` filter never returns a `resolved` or `closed` ticket
- `reclassify` while the AI is down returns `503` and the ticket is verifiably unchanged
- `reclassify` while the AI is up returns `200` and does **not** reset an `in_progress`
  ticket to `open`
- `/stats`: `total_tickets == sum(by_status.values())`
