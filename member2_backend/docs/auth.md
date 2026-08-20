# `api/auth.py` — passwords, tokens, and endpoint guards

## Role

This file owns identity. It answers two questions the rest of the application relies on
and never asks itself: **who is making this request** (authentication), and **are they
allowed to** (authorization). It stores passwords in a form that cannot be reversed,
issues tokens that prove a login happened, and exposes two dependencies —
`get_current_user` and `require_staff` — that endpoints attach to guard themselves.

## Concepts

**Hashing is not encryption.** Encryption is reversible with a key; hashing is not
reversible at all. Passwords are hashed, so the database never contains a password even
if it is stolen. Login works by hashing the attempt and comparing hashes — the original
is never recovered, only re-derived.

**Salting.** Two users with the password `hunter2` must not produce the same hash, or an
attacker who cracks one has cracked both. bcrypt generates a random *salt* per password
and mixes it in, then stores the salt inside the hash string. This is why the same
password hashed twice gives two different outputs, and why `bcrypt.checkpw` — not `==` —
must be used to compare.

**Deliberate slowness.** bcrypt is designed to be slow, around 100ms per hash. For one
login that is imperceptible; for an attacker trying millions of guesses it is
prohibitive. A fast hash like MD5 or SHA-256 is *wrong* for passwords precisely because
it is fast.

**JWT (JSON Web Token).** A string with three dot-separated parts:
`header.payload.signature`. The payload is readable by anyone — it is base64, not
encryption — and the signature proves it was issued by this server and has not been
altered. Change one character of the payload and the signature no longer matches.

The consequence: **a JWT is proof of authorship, not a secret box.** Never put anything
confidential in the payload. `sub` (the user id) and `role` are fine; a password would
not be.

**Stateless authentication.** The server stores no session. It reads the token, verifies
the signature with `JWT_SECRET`, and trusts what is inside. This matters for a
*distributed* system: run three copies of this backend behind a load balancer and any of
them can serve any request, because none of them needs a shared session store. That is a
strong point to make in the architecture walkthrough.

**401 vs 403.** `401 Unauthorized` means *I do not know who you are* — no token, bad
token, expired token. `403 Forbidden` means *I know exactly who you are, and you may
not*. A customer calling a staff endpoint gets `403`: their identity is fine, their
permission is not.

## The substance

### Configuration

```python
JWT_SECRET         = os.getenv("JWT_SECRET", "dev-secret-change-before-deployment")
JWT_ALGORITHM      = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
```

`HS256` signs with a shared secret — the same key signs and verifies. Anyone holding
`JWT_SECRET` can mint valid tokens for any user, so **the default must be replaced before
deployment**. It is a placeholder that lets the project run out of the box, not a value
to ship.

### `hash_password(plain_password) -> str`

```python
bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
```

`gensalt()` produces a fresh random salt each call. The result is a string like
`$2b$12$...` containing the algorithm, cost factor, salt and hash together — which is why
only one column is needed to store it.

### `verify_password(plain_password, password_hash) -> bool`

Wraps `bcrypt.checkpw`, which re-extracts the salt from the stored hash, re-hashes the
attempt with it, and compares in constant time. Constant-time comparison prevents *timing
attacks*, where an attacker measures how long a rejection takes to learn how many
characters matched.

The `except ValueError: return False` matters: bcrypt raises if the stored hash is
malformed — a corrupted row, or data imported from another system. Letting that propagate
would turn a bad row into a `500`. A hash that cannot be checked is a login that fails,
not a server error.

### `create_access_token(user) -> str`

```python
payload = {
    "sub":  str(user.id),
    "role": user.role,
    "exp":  utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
}
```

`sub` ("subject") and `exp` ("expiry") are standard JWT claim names. `exp` is enforced by
the JWT library automatically on decode — an expired token raises before your code sees
it.

`sub` is a string because the JWT specification requires it, even though the id is an
integer. `get_current_user` converts it back.

### `get_current_user(credentials, db) -> User`

The dependency that guards every authenticated endpoint. Four failure paths, all `401`:

1. **No credentials.** `HTTPBearer(auto_error=False)` returns `None` instead of raising,
   so this file controls the error message and the `WWW-Authenticate` header.
2. **`ExpiredSignatureError`** → "Token has expired", so the frontend can distinguish
   "log in again" from "something is wrong".
3. **Any other `PyJWTError`** → "Invalid token". Covers tampering, wrong signature,
   malformed structure.
4. **User no longer exists.** The token is valid but the account was deleted. Checking
   this on every request is what makes deletion take effect immediately, rather than when
   the token happens to expire.

On success it returns the `User` object. Because it is declared as
`user: User = Depends(get_current_user)`, the endpoint body receives a real user and can
use `user.id` and `user.role` without any checks of its own.

### `require_staff(user) -> User`

```python
def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role != "staff":
        raise HTTPException(403, "Staff access required")
    return user
```

A dependency that depends on another dependency. FastAPI resolves `get_current_user`
first, then applies this check. An endpoint written as
`staff: User = Depends(require_staff)` is authenticated *and* authorized by its own
signature — there is no permission check to forget inside the function body, because the
check is part of the declaration.

This is the pattern worth taking away from the file: **security enforced by declaration
rather than by remembering.**

## Gotchas / known ceilings

**Tokens cannot be revoked.** Statelessness has a cost: a stolen token stays valid until
`exp`. Logging out only deletes the token from the browser; the token itself still works.
Real systems solve this with short-lived access tokens plus refresh tokens, or a
revocation list — both of which reintroduce shared state. The 24-hour expiry is the
mitigation here. Worth naming in the report's limitations.

**No password reset, no email verification.** Forgetting a password means asking someone
to reseed the database. Both features need an email service, which is beyond scope.

**No rate limiting on login.** Nothing stops thousands of password guesses. bcrypt's
slowness helps considerably — roughly 10 attempts per second per core rather than
millions — but a real deployment would add lockout after repeated failures, and the
cloud platform's own rate limiting in front of the service.

**Role is fixed at registration.** `/auth/register` always creates a `customer`; there is
no endpoint that promotes anyone. Staff accounts come from `seed.py` only. This is a
deliberate simplification *and* a security property: the public form cannot be used to
grant staff access. Adding an admin user-management screen is the natural extension.

**The role inside the token can go stale.** If a user's role changed in the database,
their existing token still carries the old value. `require_staff` reads
`user.role` from the freshly loaded database row, not from the token payload, so the
guard is always current — but be aware the two can disagree.

## Tests

`test_backend.py` covers the authentication surface directly:

| Check | Expected |
|---|---|
| register, then register the same email | `201`, then `400` |
| login with correct credentials | `200` with a token |
| `GET /auth/me` with that token | `200`, correct email |
| any protected endpoint with **no** token | `401` |
| any protected endpoint with `"not-a-real-token"` | `401` |
| customer calling `PATCH /tickets/{id}` | `403` |
| customer calling `GET /stats` | `403` |
| customer calling `POST /tickets/{id}/reclassify` | `403` |
| customer reading another customer's ticket | `404` (see below) |

That last row is the deliberate exception. A customer requesting a ticket that exists but
belongs to someone else receives `404`, not `403`. A `403` would confirm the ticket
exists — leaking information about other customers' data through the choice of status
code. The logic lives in `get_visible_ticket` in [main.md](main.md).

Expiry is not tested: it would require either waiting 24 hours or reconfiguring the
service mid-run. The behaviour is entirely inside PyJWT's `decode`.
