# `seed.py` — demo data

## Role

This script fills an empty database with realistic data: one staff account, one customer
account, and fourteen tickets spread across every category, priority and status. It
exists so that Member 5's dashboard has something to render on day one instead of an
empty table, and so the presentation demo shows a support desk with real traffic rather
than a blank screen.

It is also the only way a `staff` account comes into existence — `/auth/register` always
creates customers.

## Concepts

**Seeding vs. migrating.** A migration changes the *shape* of the database (tables,
columns). Seeding puts *data* into a shape that already exists. This script only seeds;
table creation is `init_db()` from `models.py`.

**Why it does not call the AI service.** Each sample ticket is written with its category
and priority already filled in. That makes the script fast, deterministic, and runnable
whether or not Member 3's service is up. Realism is not lost — the numbers are plausible
and the shape of the data is identical to what the API produces.

**Backdating.** Tickets are created with `created_at` set hours in the past. This is what
makes some of them overdue, which is what gives the dashboard's "overdue" filter and red
badges something to show. Data that is all fresh looks fake and exercises nothing.

## The substance

### Accounts created

| Role | Email | Password |
|---|---|---|
| staff | `staff@support.com` | `staff1234` |
| customer | `alice@example.com` | `alice1234` |

These credentials are also hardcoded in `test_backend.py`, which logs in as the staff user
to run its staff-side checks.

### `SAMPLE_TICKETS`

A list of tuples: `(complaint, category, priority, status, hours_ago)`.

```python
("My credit card was charged twice for the same order.",
 "billing_payment", "high", "open", 1),
...
("The item I received is the wrong size and colour.",
 None, None, "pending_classification", 4),
```

Fourteen entries covering all five categories, all three priorities, and all five
statuses. The last two have `category=None` and `status="pending_classification"` —
they represent complaints that arrived while the AI service was down. Without them the
dashboard would never display the state that carries the reliability story.

### `get_or_create_user(db, email, password, name, role) -> User`

Returns the existing user with that email, or creates one. Makes the script safe to run
against a database that already has accounts — no duplicate-email crash.

`db.flush()` rather than `db.commit()`: flush sends the `INSERT` so the database assigns
an `id` (needed immediately for `Ticket.user_id`) but leaves the transaction open, so
everything still commits or fails together at the end.

### `main()`

```
--reset present?  →  Base.metadata.drop_all()      wipe every table
init_db()                                          (re)create tables
tickets already exist and not --reset?  →  print and exit
create staff + customer
for each sample: compute created_at, department, sla_due_at → add
commit
count overdue and print a summary
```

**Safe by default, destructive only on request.** Running `python seed.py` on a database
that already has tickets does nothing and says so. Wiping requires typing `--reset`. That
distinction matters once Member 4 points `DATABASE_URL` at a shared cloud database — an
accidental re-run must not erase everyone's test data.

Ticket fields are derived rather than hardcoded:

```python
department  = routing.department_for(category)
sla_due_at  = routing.sla_due_at(effective_priority, created_at)
```

The seed data therefore obeys the same routing rules as live tickets. Change the SLA
hours in `routing.py` and reseed, and the demo data updates to match — it cannot drift
out of sync with the real logic.

The confidence values (`0.82`, `0.77`) are placeholders, set only for classified tickets.
Unclassified tickets get `None`, exactly as the live fallback produces.

### Output

```
Loaded 14 tickets (3 overdue).

Demo accounts:
  staff     staff@support.com / staff1234
  customer  alice@example.com / alice1234
```

The overdue count is computed after the commit by reading the rows back, so it reports
what is actually in the database rather than what the script intended.

## Gotchas / known ceilings

**All tickets belong to one customer.** Every sample is submitted by Alice. The dashboard
looks right, but "tickets grouped by customer" would show a single group. `test_backend.py`
registers additional customers at runtime, so the cross-customer isolation checks still
have real data to work with.

**Passwords are weak and public.** `staff1234` is in this file, in the README, and in the
test script. Acceptable for demo accounts on a class project; it would be a serious
finding on anything real. If the system is deployed to a public URL, change them.

**`--reset` drops every table, not just tickets.** It calls `drop_all()`, so user accounts
go too. That is intended — a half-reset database with orphaned users is more confusing
than a clean one.

**No randomisation.** The same fourteen tickets every time. Deterministic data makes the
demo predictable and the test counts stable, which is worth more here than variety.

## Tests

The script has no test of its own; it is a development tool, not part of the running
service. It is exercised every time the test suite runs, because `test_backend.py`
depends on the seeded staff account and skips its entire staff section with a clear
message if that login fails:

```
SKIPPED staff checks: no seeded staff account.
Run 'python seed.py' and try again.
```

`setup_backend.bat` runs `python seed.py` automatically, so a teammate who follows the
README never meets that message.
