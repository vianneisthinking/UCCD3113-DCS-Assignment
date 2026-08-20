# `api/schemas.py` — request and response shapes

## Role

This file owns the boundary between JSON and Python. Every piece of data entering the API
is checked against a class here before any endpoint code runs, and every piece of data
leaving is filtered through one on the way out. It is the API's contract expressed as
code — and because FastAPI reads these classes, it is also what generates the interactive
documentation at `/docs` that Members 1 and 5 use.

## Concepts

**Two kinds of "model", and they are not the same thing.** This is the single most
common confusion when learning FastAPI:

| | `models.py` (SQLAlchemy) | `schemas.py` (Pydantic) |
|---|---|---|
| Represents | a database table | a JSON shape |
| Used for | storage | validation and serialisation |
| Example | `Ticket` | `TicketCreate`, `TicketOut` |

They are separate on purpose. `User` has a `password_hash` column; `UserOut` does not
have that field, so a password hash can never be returned to a browser *even if someone
writes a careless endpoint*. The safety comes from the shapes being different, not from
remembering to be careful.

**Validation at the boundary.** Pydantic checks the request body *before* your endpoint
function is called. If the body is wrong, FastAPI returns `422` with a description of
what was wrong and your code never runs. This means endpoint bodies can assume their
input is already valid — a large part of why they are short.

**Serialisation.** `response_model=TicketOut` on an endpoint means: take whatever the
function returned, keep only the fields declared in `TicketOut`, convert them to JSON
types, and send that. Extra attributes are dropped silently. Declaring the response
model is therefore a security measure as much as a documentation one.

## The substance

### `RegisterRequest`

```python
email:    EmailStr
password: str = Field(..., min_length=8, max_length=72)
name:     str = Field(..., min_length=1, max_length=100)
```

`EmailStr` validates the address format using the `email-validator` library (installed
as part of `fastapi[standard]`). `...` as the first argument to `Field` means *required*.

**`max_length=72` on the password is not arbitrary.** bcrypt only hashes the first 72
bytes of input, and modern versions raise a `ValueError` on longer input rather than
silently truncating. Without this cap, a user with a 100-character password would trigger
an unhandled exception and receive a confusing `500`. Capping here converts that into a
clear `422` describing the real problem. This is a good example of validation preventing
a crash rather than merely rejecting bad data.

### `LoginRequest`

```python
email:    EmailStr
password: str = Field(..., min_length=1, max_length=72)
```

`min_length=1` rather than `8`: the login endpoint must accept *any* string and check it,
including old passwords that no longer meet current rules. Enforcing the registration
policy at login would lock out legitimate users after a policy change. The `max_length`
cap is kept for the same bcrypt reason.

### `UserOut`

```python
model_config = ConfigDict(from_attributes=True)

id: int
email: str
name: str
role: str
```

`from_attributes=True` (Pydantic v2; called `orm_mode` in v1) tells Pydantic it may read
values as *attributes* — `user.email` — instead of dictionary keys. That is what lets an
endpoint `return user`, a SQLAlchemy object, and have FastAPI convert it automatically.

Note the absence of `password_hash`. That absence is a security control.

### `TokenOut`

```python
access_token: str
token_type:   str = "bearer"
role:         str
name:         str
```

`role` and `name` are included so Member 1's frontend can render the right interface
immediately after login without a second request to `/auth/me`.

**This is a convenience, not a security boundary.** The frontend can use `role` to decide
which buttons to show; it must never be the thing that decides what is *allowed*. The
server re-derives the role from the token on every request (see [auth.md](auth.md)) —
anyone can edit what their browser believes.

### `TicketCreate`

```python
complaint: str = Field(..., min_length=3, max_length=2000, examples=[...])
```

The bounds match Member 3's API contract exactly, so a complaint this API accepts is one
his service will also accept. The `examples` list is what pre-fills the "Try it out" box
at `/docs` — a small thing that makes the interactive docs immediately usable for
teammates.

### `TicketOut`

Mirrors the `Ticket` table, with the AI-supplied fields typed as `Optional`:

```python
category:            Optional[str]   = None
category_confidence: Optional[float] = None
priority:            str
priority_confidence: Optional[float] = None
model_version:       Optional[str]   = None
classified_at:       Optional[datetime] = None
```

`Optional[X]` means the field may be `null` in the JSON. This is the reliability design
surfacing in the public API: Member 1's frontend can see from the generated documentation
alone that `category` might be null, and must handle it.

`priority` is deliberately not optional — the fallback always supplies one.

### `StatusUpdate`

```python
status: Literal["pending_classification", "open", "in_progress", "resolved", "closed"]
```

`Literal` restricts the value to exactly these five strings. Anything else is rejected
with `422` before the endpoint runs, and the five valid values appear in the generated
documentation automatically. This is the only guard preventing an invalid status reaching
the database — see the note in [models.md](models.md#gotchas--known-ceilings).

## Gotchas / known ceilings

**The status list appears twice** — here as a `Literal`, and in `models.STATUSES` as a
tuple. They must be edited together. Deriving one from the other is possible but reads
worse than the duplication for five values that have not changed since they were written.

**Whitespace is not stripped by Pydantic.** A complaint of `"      "` is six characters
and passes `min_length=3`. `main.py` strips and re-checks it, which is why that second
check exists and why `test_backend.py` asserts on it specifically. A Pydantic validator
could handle it here instead; the current split keeps schemas purely declarative.

**No response schema for `/stats`.** That endpoint returns a plain dictionary, so its
shape is documented in `API_CONTRACT.md` rather than enforced by code. The keys are
dynamic — `by_category` contains whichever categories actually exist — which a fixed
Pydantic model would describe poorly. The cost is that `/docs` shows no example for it.

**`EmailStr` checks format, not existence.** `nobody@nowhere.invalid` passes. Confirming
an address requires sending a verification email, which is out of scope.

## Tests

`test_backend.py` exercises these shapes as observable API behaviour rather than
importing them:

- registering twice with the same email → `400`
- a 2-character complaint → `422` (Pydantic's `min_length`)
- a whitespace-only complaint → `422` (the manual re-check in `main.py`)
- `PATCH /tickets/{id}` with `"not_a_status"` → `422` (the `Literal`)
- every ticket response is checked for the fields `TicketOut` promises, including that
  `category` is `None` — not missing — when the AI service was down
