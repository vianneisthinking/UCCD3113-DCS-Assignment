# Backend API Contract — Ticket Management Service

**Member 2 — Backend API & Business Logic**
For: Member 1 (Customer Frontend), Member 4 (Database & Deployment), Member 5 (Staff Dashboard)

---

## Base URL

Local testing: `http://127.0.0.1:8001`

Port 8001 is used because Member 3's AI service occupies port 8000.
Replace with the cloud URL after deployment.

Interactive documentation: `http://127.0.0.1:8001/docs`

---

## Authentication

All ticket endpoints require a JWT bearer token. Obtain one from `POST /auth/login`,
then send it on every subsequent request:

```
Authorization: Bearer <access_token>
```

There are two roles:

| Role | Can do |
|---|---|
| `customer` | Submit tickets, view **only their own** tickets |
| `staff` | View all tickets, change status, reclassify, view statistics |

---

## 1. Register

`POST /auth/register`

Request:
```json
{
  "email": "alice@example.com",
  "password": "secret123",
  "name": "Alice Tan"
}
```

Response `201`:
```json
{
  "id": 1,
  "email": "alice@example.com",
  "name": "Alice Tan",
  "role": "customer"
}
```

Registration always creates a `customer`. Staff accounts are created by `seed.py`.

Errors: `400` email already registered · `422` invalid email or password under 8 characters.

---

## 2. Login

`POST /auth/login`

Request:
```json
{
  "email": "alice@example.com",
  "password": "secret123"
}
```

Response `200`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "customer",
  "name": "Alice Tan"
}
```

Errors: `401` incorrect email or password.

---

## 3. Current user

`GET /auth/me` — requires token

Response `200`:
```json
{
  "id": 1,
  "email": "alice@example.com",
  "name": "Alice Tan",
  "role": "customer"
}
```

---

## 4. Submit a complaint

`POST /tickets` — requires token

Request:
```json
{
  "complaint": "My credit card was charged twice for one order."
}
```

Response `201`:
```json
{
  "id": 14,
  "user_id": 1,
  "complaint": "My credit card was charged twice for one order.",
  "status": "open",
  "department": "Billing and Payment",
  "sla_due_at": "2026-08-10T18:30:00",
  "category": "billing_payment",
  "category_confidence": 0.3177,
  "priority": "high",
  "priority_confidence": 0.4453,
  "model_version": "1.0",
  "classified_at": "2026-08-10T14:30:00",
  "created_at": "2026-08-10T14:30:00",
  "updated_at": "2026-08-10T14:30:00"
}
```

Errors: `401` missing or invalid token · `422` complaint shorter than 3 characters
or longer than 2000.

### If the AI service is unavailable

**The ticket is still created.** This is the core reliability guarantee of the system —
a customer complaint is never lost because a downstream service is down.

The response is still `201`, but with:

```json
{
  "id": 15,
  "status": "pending_classification",
  "department": "General Enquiry",
  "sla_due_at": "2026-08-11T14:30:00",
  "category": null,
  "category_confidence": null,
  "priority": "medium",
  "priority_confidence": null,
  "model_version": null,
  "classified_at": null
}
```

A safe default is applied (General Enquiry, medium priority, 24-hour SLA) until a staff
member calls `POST /tickets/{id}/reclassify`.

**Member 1:** treat `status == "pending_classification"` as "Received — being categorised"
on the ticket status page. Do not show an error; the submission succeeded.

**Member 5:** show these tickets on the dashboard with a visible marker. They are the
clearest demonstration of the system's reliability design.

---

## 5. List tickets

`GET /tickets` — requires token

A `customer` receives only their own tickets. A `staff` user receives all tickets and may
filter using query parameters:

| Parameter | Example | Notes |
|---|---|---|
| `status` | `?status=open` | one of the five statuses |
| `department` | `?department=Billing and Payment` | exact match |
| `priority` | `?priority=high` | `high` / `medium` / `low` |
| `overdue` | `?overdue=true` | `sla_due_at` in the past and status not `resolved`/`closed` |

Filters combine: `?status=open&priority=high&overdue=true`

Response `200`: an array of ticket objects, newest first.

---

## 6. Get one ticket

`GET /tickets/{id}` — requires token

Response `200`: one ticket object.

Errors: `404` ticket does not exist, **or** it belongs to another customer.
(A customer requesting someone else's ticket receives `404`, not `403` — the existence of
other customers' tickets is not disclosed.)

---

## 7. Update ticket status

`PATCH /tickets/{id}` — **staff only**

Request:
```json
{ "status": "in_progress" }
```

Response `200`: the updated ticket object.

Errors: `403` caller is not staff · `404` ticket not found · `422` invalid status value.

---

## 8. Reclassify a ticket

`POST /tickets/{id}/reclassify` — **staff only**

Retries Member 3's AI service for a ticket that was stored while the service was
unavailable. On success the ticket is classified, re-routed to the correct department,
given a corrected SLA deadline, and moved from `pending_classification` to `open`.

Response `200`: the updated ticket object.

Errors: `403` not staff · `404` not found · `503` the AI service is still unavailable
(the ticket is left untouched and can be retried later).

---

## 9. Statistics

`GET /stats` — **staff only**

Aggregation is performed by the backend so the dashboard does not have to count in the browser.

Response `200`:
```json
{
  "total_tickets": 42,
  "by_status": { "open": 18, "in_progress": 9, "resolved": 12, "closed": 2, "pending_classification": 1 },
  "by_category": { "technical_support": 11, "account_access": 7, "billing_payment": 13, "delivery_order": 8, "general_enquiry": 3 },
  "by_priority": { "high": 9, "medium": 21, "low": 12 },
  "by_department": { "Technical Support": 11, "Account Access": 7, "Billing and Payment": 13, "Delivery and Order": 8, "General Enquiry": 3 },
  "overdue": 4,
  "pending_classification": 1
}
```

---

## 10. Health check

`GET /health` — no token required

Response `200`:
```json
{
  "status": "healthy",
  "database": "connected",
  "ai_service": "reachable"
}
```

`ai_service` is `"unreachable"` when Member 3's service is down. The backend still reports
`"status": "healthy"` in that case — it remains able to accept and store tickets.

---

## Reference tables

### Categories → departments

Categories are produced by Member 3's model. Routing is business logic owned by the backend.

| AI category | Department |
|---|---|
| `technical_support` | Technical Support |
| `account_access` | Account Access |
| `billing_payment` | Billing and Payment |
| `delivery_order` | Delivery and Order |
| `general_enquiry` | General Enquiry |
| *(unclassified)* | General Enquiry |

### Priority → SLA deadline

`sla_due_at` is calculated at submission time as `created_at` plus:

| Priority | Response deadline |
|---|---|
| `high` | 4 hours |
| `medium` | 24 hours |
| `low` | 72 hours |
| *(unclassified)* | 24 hours (treated as medium) |

### Ticket status lifecycle

```
pending_classification ──► open ──► in_progress ──► resolved ──► closed
```

| Status | Meaning |
|---|---|
| `pending_classification` | Stored successfully, but the AI service was unavailable |
| `open` | Classified and routed, awaiting a staff member |
| `in_progress` | A staff member is working on it |
| `resolved` | Fixed, awaiting closure |
| `closed` | Complete |

Only staff may change status.

---

## Error handling summary for Member 1 and Member 5

| Code | Meaning | What the frontend should do |
|---|---|---|
| `400` | Email already registered | Show it on the register form |
| `401` | No token, bad token, expired token, or wrong password | Redirect to login |
| `403` | Staff-only endpoint called by a customer | Hide the control entirely |
| `404` | Ticket not found or not yours | Show "Ticket not found" |
| `422` | Validation failed | Show the message from `detail` |
| `503` | AI service unavailable during reclassify | Show "Try again shortly" |

Error responses are FastAPI's standard shape:
```json
{ "detail": "Incorrect email or password" }
```

---

## Database schema — for Member 4

The backend creates these tables automatically on first start. Member 4 provisions the
cloud database and supplies a `DATABASE_URL`; no manual table creation is required.

**users**

| Column | Type | Notes |
|---|---|---|
| id | integer | primary key |
| email | varchar(255) | unique, indexed |
| password_hash | varchar(255) | bcrypt |
| name | varchar(100) | |
| role | varchar(20) | `customer` or `staff` |
| created_at | datetime | |

**tickets**

| Column | Type | Notes |
|---|---|---|
| id | integer | primary key |
| user_id | integer | foreign key → users.id, indexed |
| complaint | text | the original customer text |
| status | varchar(30) | indexed |
| department | varchar(50) | indexed |
| sla_due_at | datetime | |
| category | varchar(30) | nullable — null while unclassified |
| category_confidence | float | nullable |
| priority | varchar(10) | |
| priority_confidence | float | nullable |
| model_version | varchar(20) | nullable |
| classified_at | datetime | nullable |
| created_at | datetime | |
| updated_at | datetime | |

Required environment variables:

```
DATABASE_URL         postgresql://user:pass@host:5432/dbname
AI_SERVICE_URL       https://<member-3-service>
JWT_SECRET           a long random string
JWT_EXPIRE_MINUTES   1440
CORS_ORIGINS         https://<member-1-frontend>
```

---

## Notes for the team

- The backend depends on Member 3's service but does not require it to be running.
  Members 1 and 5 can develop against the backend with the AI service switched off —
  tickets simply come back as `pending_classification`.
- `127.0.0.1` works only while all services run on the same computer. Replace with the
  deployed URLs after Member 4 completes cloud deployment.
- Timestamps are ISO 8601, UTC, without a timezone suffix.
