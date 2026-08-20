# `api/ai_client.py` — client for Member 3's AI service

## Role

This file owns every conversation with Member 3's classification service, and — more
importantly — owns *the fact that the conversation might fail*. It turns a network call
with a dozen possible failure modes into a function with exactly two outcomes: it returns
a classification, or it raises `AIServiceUnavailable`.

That reduction is the whole point of the file. The endpoint in `main.py` should not have
to know the difference between a connection refused, a read timeout, an HTTP 500, and a
response missing a field. All four mean the same thing operationally — *no classification
right now* — so they are collapsed into one exception at this boundary.

## Concepts

**A network call is not a function call.** When `main.py` calls a function in
`routing.py`, it either runs or the program has a bug. When it calls Member 3's service,
the request crosses a network to a separate process that might be starting up, out of
memory, mid-deploy, or simply not running. Anything that *can* go wrong across a network
eventually does. Code that assumes otherwise is the most common cause of outages in
distributed systems — which is precisely the subject of this course.

**Timeouts.** Without one, a hung remote service hangs *your* service too: the customer's
browser spins, the connection stays open, and if enough requests pile up your backend
stops accepting new ones. A slow dependency taking down a healthy service is called
*cascading failure*. A timeout is the cheapest defence: after 5 seconds, stop waiting and
take the fallback path.

**Trust boundaries.** Data arriving from another system is untrusted input, exactly like
data from a browser — not because Member 3 is careless, but because a mistake on his side
should degrade this service, not crash it. So the response is validated field by field,
and a contract mismatch is reported as a service failure rather than allowed to raise a
`KeyError` somewhere further up.

## The substance

### Configuration

```python
AI_SERVICE_URL      = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
AI_TIMEOUT_SECONDS  = float(os.getenv("AI_TIMEOUT_SECONDS", "5.0"))
```

`.rstrip("/")` prevents the classic bug where `http://host/` plus `/predict` becomes
`http://host//predict`.

The timeout is the length of time a customer waits before the fallback engages. Raising
it makes classification more likely to succeed and the site feel slower; lowering it does
the reverse. It is a tuning knob, which is why it is an environment variable.

### `class AIServiceUnavailable(Exception)`

The single failure signal this module raises. Its docstring states the contract:
*the ticket is still stored*.

### `classify(complaint: str) -> dict`

Returns:

```python
{
    "category":             "billing_payment",
    "category_confidence":  0.3177,
    "priority":             "high",
    "priority_confidence":  0.4453,
    "model_version":        "1.0",
}
```

Raises `AIServiceUnavailable` for **every** failure. Two `try` blocks, deliberately
separate:

**Block 1 — did the service answer at all?** Wraps the HTTP call and
`raise_for_status()`. Catches `Exception` broadly, which is normally poor practice and
correct here: the specific list would be connection refused, DNS failure, read timeout,
connect timeout, TLS error, 4xx, 5xx, invalid JSON — and any one accidentally omitted
would crash the endpoint and lose the complaint. Breadth is the safety property.

**Block 2 — did it answer with what it promised?** Reads each field explicitly and
coerces its type. A missing key, a `null`, or a string where a float belongs raises
`KeyError` / `TypeError` / `ValueError`, which is re-raised as `AIServiceUnavailable`.
`model_version` uses `.get(..., "unknown")` because it is informational — a missing
version is not a reason to discard a perfectly good classification.

Both blocks use `raise ... from error`, which preserves the original exception in the
traceback. When debugging, that is the difference between "AI service did not answer" and
knowing it was a connection refused on port 8000.

### `is_reachable() -> bool`

Used only by `GET /health`. Calls the AI service's `/health` with a 2-second timeout and
returns `True` on HTTP 200. Never raises — a health check that can crash is not a health
check. The timeout is shorter than `classify`'s because nobody is waiting on a diagnostic.

## Gotchas / known ceilings

**The calls are synchronous and block the worker.** `httpx.post` is the blocking client
inside a normal `def` endpoint, so FastAPI runs it in a thread pool. Fine at assignment
scale. Under real load you would switch to `httpx.AsyncClient` and `async def`, so a
worker waiting on the network can serve other requests meanwhile.

**A new `httpx.Client` is created per call.** That means a fresh TCP connection each
time. A module-level client with connection pooling would be faster; at this traffic
level the saving is invisible, and a shared client adds lifecycle management to worry
about.

**There is no retry.** One attempt, then fall back. A retry would help with a brief
network blip but would double or triple the customer's wait in the case that actually
matters — the service being down. Recovery is handled deliberately instead, by a staff
member calling `POST /tickets/{id}/reclassify`. If retries were ever added, they belong
here, with exponential backoff.

**There is no circuit breaker.** While the AI service is down, every submission still
pays the full 5-second timeout. A circuit breaker would remember recent failures and skip
the call for a while, making the site fast again during an outage. That is the correct
next step for a production system and clear over-engineering for a class demo — but it is
a good answer if you are asked in the Q&A how this would scale.

**Confidence scores are passed through, never acted on.** A 0.31-confidence
classification is stored and routed exactly like a 0.99 one. A real desk would flag
low-confidence tickets for human review. Worth naming in the report's future
enhancements.

## Tests

There is no dedicated unit test file. Both paths are covered end-to-end by
`test_backend.py`, which is run twice — once with Member 3's service up, once with it
stopped — and asserts different outcomes for each:

| AI service | Expected result |
|---|---|
| running | ticket `status="open"`, category in the known set, `classified_at` set |
| stopped | ticket `status="pending_classification"`, `category is None`, still HTTP 201 |

The malformed-response branch of block 2 is *not* covered by a test. Triggering it means
making Member 3's service return something wrong on demand, which would need a stub
server — more machinery than the branch is worth for this project.
