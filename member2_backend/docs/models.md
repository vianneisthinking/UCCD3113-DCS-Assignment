# `api/models.py` — database tables and session handling

## Role

This file owns everything about persistence: which database to connect to, what the
tables look like, and how each request gets a database session and gives it back. It is
the only file that knows whether the data lives in a SQLite file on your laptop or in
Member 4's cloud Postgres — and it learns that from an environment variable, so nothing
else in the codebase has to care.

## Concepts

**ORM (Object-Relational Mapper).** SQLAlchemy lets you work with Python classes and
objects instead of writing SQL strings. `Ticket` is a class; a row in the `tickets`
table is an instance of it. `db.add(ticket)` becomes an `INSERT`, `ticket.status = "open"`
followed by `db.commit()` becomes an `UPDATE`. The benefit that matters here: the *same*
Python code generates valid SQLite SQL and valid PostgreSQL SQL, which is what makes the
switch to the cloud a configuration change.

**Declarative base.** `Base = declarative_base()` creates a registry. Every class
inheriting from `Base` is recorded in it, which is how `Base.metadata.create_all()` knows
which tables to create — and how `--reset` in `seed.py` knows what to drop.

**Session.** A session is a workspace for one unit of work: it tracks the objects you
have loaded or added, and writes them all at `commit()`. Sessions are *not* thread-safe
and must not be shared between requests, which is exactly what `get_db()` guarantees.

**Engine vs. session.** The engine is the connection pool — created once when the app
starts, expensive. A session is a cheap short-lived conversation borrowed from that pool.
One engine per process, one session per request.

## The substance

### Connection setup

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tickets.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine       = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base         = declarative_base()
```

`check_same_thread=False` is a SQLite-only setting. SQLite normally refuses to let a
connection be used from a thread other than the one that opened it; FastAPI runs
synchronous endpoints in a thread pool, so that restriction has to be lifted. The
conditional matters — passing this argument to Postgres is an error, so it must not be
sent when the URL is not SQLite.

`autocommit=False` means nothing is written until you call `commit()`. That is what makes
`db.rollback()` in the reclassify endpoint able to discard changes cleanly.

### Status constants

```python
STATUSES      = ("pending_classification", "open", "in_progress", "resolved", "closed")
OPEN_STATUSES = ("pending_classification", "open", "in_progress")
```

`OPEN_STATUSES` is the set of statuses where a ticket is still someone's problem. It is
used by both the `overdue` filter and the `/stats` overdue count — defining it once means
those two numbers can never disagree, which is the kind of inconsistency that makes a
dashboard untrustworthy.

### `utcnow() -> datetime`

```python
return datetime.now(timezone.utc).replace(tzinfo=None)
```

Returns the current UTC time with the timezone label stripped. Used as the default for
every timestamp column and everywhere a "now" is needed.

<a name="why-naive-utc"></a>
**Why naive UTC.** The value is UTC; it just does not carry a `tzinfo` marker. Mixing
"aware" and "naive" datetimes in Python raises `TypeError` on comparison — so a codebase
must pick one and stay consistent. Naive is chosen because SQLite has no timezone-aware
column type, so a timezone would be silently dropped on write and produce exactly that
crash on read. `datetime.utcnow()` would have been shorter, but it is deprecated in
Python 3.12+ and prints warnings.

### `class User(Base)` — table `users`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | primary key |
| `email` | String(255) | unique, indexed — the login identifier |
| `password_hash` | String(255) | bcrypt hash, never the password |
| `name` | String(100) | display name |
| `role` | String(20) | `"customer"` or `"staff"` |
| `created_at` | DateTime | defaults to `utcnow` |

`unique=True` on email makes the database itself reject duplicates, even if the
application check in `/auth/register` were somehow bypassed. `index=True` makes login
lookups fast — every single login queries by email.

### `class Ticket(Base)` — table `tickets`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | primary key |
| `user_id` | Integer FK → `users.id` | indexed; who submitted it |
| `complaint` | Text | the original customer text |
| `status` | String(30) | indexed; one of `STATUSES` |
| `department` | String(50) | indexed; from `routing.department_for()` |
| `sla_due_at` | DateTime | from `routing.sla_due_at()` |
| `category` | String(30) | **nullable** — AI result |
| `category_confidence` | Float | **nullable** — AI result |
| `priority` | String(10) | **not** nullable |
| `priority_confidence` | Float | **nullable** — AI result |
| `model_version` | String(20) | **nullable** — AI result |
| `classified_at` | DateTime | **nullable** — when the AI answered |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

**The nullability pattern is the design, not an oversight.** Every column that can only
come from the AI service is nullable, because a ticket stored during an outage has none
of them. `department`, `priority`, `status` and `sla_due_at` are *not* nullable, because
the backend can always supply those from its own defaults. Read down that table and you
can see the reliability guarantee expressed in the schema: the columns the system
controls are mandatory, the columns a remote service controls are optional.

`priority` deserves a note. It is not nullable even though the AI supplies it, because
the fallback fills in `"medium"` — a ticket with no priority could not be sorted or given
a deadline. `priority_confidence` stays null in that case, and that difference is how you
tell a predicted medium from a defaulted one.

`Text` vs `String(n)`: `Text` has no length limit at the database level, appropriate for
free-form complaints. The 2000-character cap is enforced in `schemas.py` at the API
boundary instead.

### Relationships

```python
User.tickets   ←→   Ticket.user
```

Declared with `relationship(..., back_populates=...)` on both sides. Lets you write
`ticket.user.name` instead of a manual join. Not heavily used by the endpoints — the
current queries filter on `user_id` directly — but it is what makes the ORM worth having
if the dashboard ever needs submitter names.

### `get_db()`

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

A FastAPI *dependency*. Any endpoint declaring `db: Session = Depends(get_db)` receives a
fresh session; when the response is finished, execution resumes after the `yield` and the
session is closed. The `finally` guarantees closure even if the endpoint raises — without
it, connections leak until the pool is exhausted and the service stops responding.

### `init_db()`

`Base.metadata.create_all(bind=engine)` — creates any missing tables. Called once at
import time in `main.py`, so a fresh deployment against an empty cloud database works
with no manual SQL. Existing tables are left untouched.

## Gotchas / known ceilings

**`create_all()` creates but never alters.** Add a column to a model and it will *not*
appear in an existing database — no error, just a column that is silently missing until
a query fails. Proper projects use a migration tool (Alembic) that versions each schema
change. This project deploys once from an empty database, so migrations would be
machinery for a problem it does not have. If you change a model during development, run
`python seed.py --reset`.

**`status` and `role` are strings, not database enums.** Nothing at the database level
stops `status = "banana"`. The guard is `StatusUpdate` in `schemas.py`, which rejects
anything outside the five values at the API boundary — the only door into the database.
A native enum type would add the constraint at the storage layer too, at the cost of a
migration every time the list changes.

**`updated_at` is set manually.** Every endpoint that modifies a ticket assigns it. Miss
one and the timestamp silently goes stale. `onupdate=utcnow` on the column would automate
it; it was left explicit so the write is visible where the change happens.

**No soft deletes, no audit trail.** A status change overwrites the previous value with
no record of who changed it or when. A real support system keeps that history for
accountability. Worth listing under limitations in the report.

## Tests

No dedicated test file. The models are exercised constantly by `test_backend.py`: every
register writes a `User`, every submission writes a `Ticket`, and the `/stats` assertion
(`total_tickets == sum(by_status.values())`) is effectively a consistency check on what
was persisted.

The one model-level behaviour worth knowing is verified indirectly: `test_backend.py`
asserts that no ticket with status `resolved` or `closed` ever appears in the `overdue`
filter, which is what `OPEN_STATUSES` exists to guarantee.
