# `api/routing.py` — ticket routing business logic

## Role

This file owns the two decisions that make this a *ticket routing system* rather than a
form that saves text: **which department handles a complaint**, and **when they must
respond by**. It converts the AI service's output (a category, a priority) into
operational facts a support desk can act on (a department, a deadline).

It is the smallest file in the project and the most important one to understand, because
it is the only place where your own business rules live. Everything else is plumbing.

It imports nothing from the rest of the application — no database, no HTTP, no FastAPI.
That is deliberate: pure logic with no dependencies is logic you can read in one sitting
and test without starting a server.

## Concepts

**Business logic vs. infrastructure.** Member 3's model answers a *classification*
question: "what kind of complaint is this?" It has no opinion about your company's
org chart. Deciding that billing complaints go to the Billing team, and that urgent
ones need an answer within 4 hours, is a *policy* decision your organisation makes.
Those two things change for completely different reasons — the model changes when it is
retrained, the policy changes when management reorganises — so they live in different
files.

**SLA (Service Level Agreement).** A promise about response time. "High priority
complaints get a reply within 4 hours" is an SLA. Storing the resulting deadline on the
ticket (rather than computing it when someone looks) means the staff dashboard can sort
and filter by it directly, and the promise is preserved even if the policy changes later.

**Pure functions.** Both functions here take arguments and return a value, touching
nothing else. Call `sla_due_at("high", t)` a thousand times and you get the same answer
with no side effects. This is why the self-check at the bottom of the file is four lines
instead of a test framework.

## The substance

### Constants

```python
DEFAULT_DEPARTMENT = "General Enquiry"
DEFAULT_PRIORITY   = "medium"
```

Applied when the AI service could not be reached. They exist so that an unclassifiable
ticket still has somewhere to go — the alternative is a ticket with no owner, which is
how complaints get lost.

```python
CATEGORY_TO_DEPARTMENT = {
    "technical_support":  "Technical Support",
    "account_access":     "Account Access",
    "billing_payment":    "Billing and Payment",
    "delivery_order":     "Delivery and Order",
    "general_enquiry":    "General Enquiry",
}
```

The five keys are exactly the five categories Member 3's model can output. If he ever
adds a sixth, this dictionary is the one place that needs editing.

```python
SLA_HOURS = {"high": 4, "medium": 24, "low": 72}
```

### `department_for(category) -> str`

Returns the department that handles this category.

```python
department_for("billing_payment")   # "Billing and Payment"
department_for(None)                # "General Enquiry"
department_for("nonsense")          # "General Enquiry"
```

Uses `dict.get(category, DEFAULT_DEPARTMENT)`, so an unknown or missing category never
raises — it falls back. A `KeyError` here would mean a customer's complaint vanished
because a model was retrained, which is not an acceptable trade.

### `sla_due_at(priority, created_at) -> datetime`

Returns the response deadline: `created_at` plus the hours for that priority.

```python
sla_due_at("high",   datetime(2026, 8, 10, 12, 0))  # 2026-08-10 16:00
sla_due_at("medium", datetime(2026, 8, 10, 12, 0))  # 2026-08-11 12:00
sla_due_at(None,     datetime(2026, 8, 10, 12, 0))  # treated as medium
```

`created_at` is passed in rather than read from the clock inside the function. That is
what lets `seed.py` create tickets dated hours in the past — some of which are therefore
already overdue, so the dashboard has realistic data to display.

## Gotchas / known ceilings

**The department map is 1:1 with the categories today, and it is still a dictionary.**
You could produce "Billing and Payment" from `"billing_payment"` with a string
transformation and delete the dictionary. It stays because a real support desk changes
its org chart without asking the AI team to rename model labels — routing two categories
to one team, or splitting one across two, is a one-line edit here. A string
transformation would have to be torn out and replaced by exactly this dictionary the
first time that happened.

**Timezones are ignored.** Everything is naive UTC (see
[models.md](models.md#why-naive-utc)). A real system serving customers in several
countries would store the timezone and compute deadlines in local business hours —
"4 hours" should probably not span a weekend. Out of scope here; worth naming in the
report's limitations section.

**SLA hours are constants in the source.** Changing them requires a code edit and a
redeploy. If support managers needed to adjust them, they would move into a database
table with an admin screen. For a system with three fixed priorities, that would be
machinery serving nobody.

**Existing tickets keep their old deadline if the policy changes.** `sla_due_at` is
evaluated once at submission and stored. This is intentional: the deadline is a promise
made to that customer at that moment, not a value that should silently move.

## Tests

The file has a self-check at the bottom, runnable with no server and no database:

```
.venv\Scripts\python.exe -m api.routing
```

It asserts:

- known categories map to their departments
- `None` and an unknown category both fall back to General Enquiry
- each priority produces the right deadline arithmetic (4h / 24h / 72h)
- an unclassified ticket gets the medium deadline, not "no deadline"

`test_backend.py` covers the same logic through the API — it imports
`CATEGORY_TO_DEPARTMENT` from this module and asserts that a real classified ticket
landed in the department this table says it should.
