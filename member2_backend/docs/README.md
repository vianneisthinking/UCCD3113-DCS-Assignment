# Backend API — Documentation

This is the backend for the AI Customer Support Ticket Classification and Routing
System. It is the hub of the whole project: the customer website and the staff
dashboard both talk to it, and it is the only component that talks to the database
and to the AI classification service.

If you read nothing else, read [Request lifecycle](#request-lifecycle) below. Every
other document is a zoom-in on one step of it.

---

## Where this fits in the system

```
   Member 1                                                     Member 3
   Customer site  ──┐                                       AI service :8000
                    │                                        POST /predict
                    ├──►  THIS BACKEND  :8001  ──────────────────►
                    │     auth, validation,   ◄──────────────────
   Member 5         │     routing, storage        category + priority
   Staff dashboard ─┘             │
                                  │
                                  ▼
                            Member 4's database
                          (SQLite now, cloud Postgres later)
```

Four responsibilities live here and nowhere else:

1. **Authentication** — who is calling, and are they a customer or staff?
2. **Validation** — is this complaint acceptable before anything else happens?
3. **Routing** — which department handles this ticket, and by when? (business logic)
4. **Integration** — call the AI service, survive it being down, persist everything.

The AI service decides *what a complaint is about*. This backend decides *what to do
about it*. Keeping those two ideas separate is the main design idea of the system.

---

## Module map

| File | Documentation | What it owns |
|---|---|---|
| `api/main.py` | [main.md](main.md) | Every HTTP endpoint, and the classify-or-fallback decision |
| `api/models.py` | [models.md](models.md) | Database tables, connection, session handling |
| `api/schemas.py` | [schemas.md](schemas.md) | The shapes of JSON coming in and going out |
| `api/auth.py` | [auth.md](auth.md) | Password hashing, JWT tokens, endpoint guards |
| `api/ai_client.py` | [ai_client.md](ai_client.md) | Talking to Member 3's service and surviving its failures |
| `api/routing.py` | [routing.md](routing.md) | Category → department, priority → deadline |
| `seed.py` | [seed.md](seed.md) | Demo data for the dashboard and the presentation |
| `test_backend.py` | [test_backend.md](test_backend.md) | The end-to-end smoke test |

`api/__init__.py` is empty on purpose. Its presence makes `api` a Python *package*,
which is what lets every file say `from api.models import ...` and lets uvicorn start
the app with `api.main:app`.

The dependency direction is worth noticing, because it never reverses:

```
main.py  ──►  auth.py  ──►  models.py
   │
   ├────────►  ai_client.py        (no imports from the rest of the app)
   ├────────►  routing.py          (no imports from the rest of the app)
   ├────────►  schemas.py
   └────────►  models.py
```

`routing.py` and `ai_client.py` know nothing about HTTP or the database. That is why
they can be tested by themselves, and why you can read either one in a minute.

---

## Request lifecycle

Follow one complaint from the customer's browser to the database. This is the story to
tell when you walk through the architecture in the presentation.

**1. The request arrives.**
`POST /tickets` with a JSON body and an `Authorization: Bearer <token>` header.

**2. CORS middleware** decides whether a browser on Member 1's domain is allowed to
call this API at all. Configured by `CORS_ORIGINS`. See [main.md](main.md#cors).

**3. Authentication.** `get_current_user` in [auth.md](auth.md) reads the token,
verifies its signature, and loads the `User` row. No token, expired token, or tampered
token → `401` and the request stops here.

**4. Validation.** Pydantic checks the body against `TicketCreate`
([schemas.md](schemas.md)) *before your endpoint function runs*. Wrong shape, missing
field, complaint under 3 characters → `422`, automatically.

**5. Classification.** `ai_client.classify()` posts the complaint to Member 3's service
with a 5-second timeout ([ai_client.md](ai_client.md)).

**6. Routing.** `routing.department_for()` and `routing.sla_due_at()` turn the AI's
category and priority into a department and a deadline ([routing.md](routing.md)).

**7. Fallback, if step 5 failed.** The ticket is *still created*, with status
`pending_classification`, routed to General Enquiry, medium priority, 24-hour deadline.
This is the reliability guarantee of the system.

**8. Persistence.** The `Ticket` row is committed ([models.md](models.md)).

**9. Response.** SQLAlchemy object → `TicketOut` → JSON, `201 Created`.

Steps 3, 4, 8 and 9 are things FastAPI does *for* you once you declare them. Steps 5, 6
and 7 are the code you actually wrote. That ratio is the point of using a framework.

---

## Running it

**First time**

```
setup_backend.bat
```

Creates `.venv`, installs `requirements.txt`, copies `.env.example` to `.env`, and loads
demo data.

**Every time**

```
start_backend.bat
```

Serves on `http://127.0.0.1:8001`. Port 8001 because Member 3's AI service owns 8000.

| URL | What it is |
|---|---|
| `http://127.0.0.1:8001/docs` | Interactive API explorer, generated from the code |
| `http://127.0.0.1:8001/health` | Is the database up? Is the AI service reachable? |

**Demo accounts** (created by `seed.py`):

| Role | Email | Password |
|---|---|---|
| staff | `staff@support.com` | `staff1234` |
| customer | `alice@example.com` | `alice1234` |

---

## Running the tests

```
.venv\Scripts\python.exe test_backend.py
```

The backend must already be running. **Run it twice: once with Member 3's AI service
started, and once with it stopped.** Both runs must pass — the second run is what proves
the reliability design works. See [test_backend.md](test_backend.md).

There is also a self-check inside the routing module, which needs no server at all:

```
.venv\Scripts\python.exe -m api.routing
```

---

## Configuration

Everything environment-specific is read from `.env`. Nothing is hardcoded, which is why
moving to the cloud is a configuration change rather than a code change.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./tickets.db` | Member 4 replaces with a Postgres URL |
| `AI_SERVICE_URL` | `http://127.0.0.1:8000` | Member 3's deployed URL after deployment |
| `AI_TIMEOUT_SECONDS` | `5.0` | How long a customer waits before the fallback |
| `JWT_SECRET` | dev placeholder | **Must** change before deployment |
| `JWT_EXPIRE_MINUTES` | `1440` | 24 hours |
| `CORS_ORIGINS` | `*` | Narrow to Member 1's domain once deployed |

`.env` is never shared. `.env.example` is the version teammates receive.

---

## The API contract

`API_CONTRACT.md` in the project root is the document Members 1, 4 and 5 read. It
specifies every endpoint, every error code, and the database schema.

These `docs/` explain *how the code works*. `API_CONTRACT.md` specifies *what the API
promises*. When they disagree, the contract wins and the code is wrong.
