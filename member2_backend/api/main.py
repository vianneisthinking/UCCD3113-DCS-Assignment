"""
Backend API & Business Logic — Member 2.

The hub of the system: it authenticates users, validates and stores complaints,
asks Member 3's AI service to classify them, routes them to a department with a
response deadline, and serves both Member 1's customer site and Member 5's staff
dashboard.

Reliability guarantee: a complaint is stored even when the AI service is down.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from api import ai_client, routing
from api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_staff,
    verify_password,
)
from api.models import (
    OPEN_STATUSES,
    Ticket,
    User,
    get_db,
    init_db,
    utcnow,
)
from api.schemas import (
    LoginRequest,
    RegisterRequest,
    StatusUpdate,
    TicketCreate,
    TicketOut,
    TokenOut,
    UserOut,
)

load_dotenv()


app = FastAPI(
    title="Ticket Management API",
    description=(
        "Backend API and business logic for the AI customer-support ticket "
        "classification and routing system."
    ),
    version="1.0.0",
)

# Member 1's frontend host is not fixed yet, so this defaults to permissive and
# is narrowed via CORS_ORIGINS once the site is deployed.
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8080,http://localhost:8080,"
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true":
    # Convenient for SQLite development. Deployment sets this to false and
    # runs Alembic before starting the service.
    init_db()


# ============================================================
# Service information
# ============================================================


@app.get("/")
def read_root():
    return {
        "service": "Ticket Management API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    The service reports healthy whenever it can still accept and store tickets.

    An unreachable AI service is reported but does not make the system
    unhealthy — that is the point of the fallback.
    """

    try:
        db.execute(text("SELECT 1"))
        database_state = "connected"
    except SQLAlchemyError:
        database_state = "unavailable"

    return {
        "status": "healthy" if database_state == "connected" else "degraded",
        "database": database_state,
        "ai_service": (
            "reachable" if ai_client.is_reachable() else "unreachable"
        ),
    }


# ============================================================
# Authentication
# ============================================================


@app.post(
    "/auth/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Self-registration always creates a customer. Staff accounts come from
    # seed.py so the dashboard role cannot be claimed from the public form.
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        name=payload.name.strip(),
        role="customer",
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # The pre-check gives the common case a clear response, but two
        # simultaneous requests can both pass it. The database constraint is
        # authoritative, so translate that race into the same client error.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    db.refresh(user)

    return user


@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if user is None or not verify_password(
        payload.password, user.password_hash
    ):
        # One message for both cases: do not reveal which emails are registered.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return TokenOut(
        access_token=create_access_token(user),
        role=user.role,
        name=user.name,
    )


@app.get("/auth/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)):
    return user


# ============================================================
# Classification and routing
# ============================================================


def apply_classification(ticket, complaint):
    """
    Classify and route a ticket in place.

    Returns True if the AI service answered, False if the safe default was
    applied instead. The ticket is usable either way — this function never
    raises, because losing the complaint is not an acceptable outcome.
    """

    now = utcnow()

    try:
        result = ai_client.classify(complaint)

    except ai_client.AIServiceUnavailable:
        ticket.status = "pending_classification"
        ticket.department = routing.DEFAULT_DEPARTMENT
        ticket.priority = routing.DEFAULT_PRIORITY
        ticket.sla_due_at = routing.sla_due_at(
            routing.DEFAULT_PRIORITY, ticket.created_at or now
        )
        ticket.updated_at = now
        return False

    ticket.category = result["category"]
    ticket.category_confidence = result["category_confidence"]
    ticket.priority = result["priority"]
    ticket.priority_confidence = result["priority_confidence"]
    ticket.model_version = result["model_version"]
    ticket.classified_at = now

    ticket.status = "open"
    ticket.department = routing.department_for(result["category"])
    ticket.sla_due_at = routing.sla_due_at(
        result["priority"], ticket.created_at or now
    )
    ticket.updated_at = now

    return True


# ============================================================
# Tickets
# ============================================================


@app.post(
    "/tickets",
    response_model=TicketOut,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    payload: TicketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a complaint. Always stored, classified when possible."""

    complaint = payload.complaint.strip()

    # Pydantic checked the raw string; whitespace-only input survives that.
    if len(complaint) < 3:
        # Literal 422 rather than the status constant: Starlette renamed it, and
        # the literal works on every version in requirements.txt.
        raise HTTPException(
            status_code=422,
            detail="Complaint must contain at least three visible characters.",
        )

    now = utcnow()
    ticket = Ticket(
        user_id=user.id,
        complaint=complaint,
        created_at=now,
        updated_at=now,
    )

    apply_classification(ticket, complaint)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@app.get("/tickets", response_model=list[TicketOut])
def list_tickets(
    ticket_status: Optional[str] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    overdue: Optional[bool] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Customers see their own tickets. Staff see everything, with filters."""

    query = db.query(Ticket)

    if user.role != "staff":
        query = query.filter(Ticket.user_id == user.id)

    if ticket_status:
        query = query.filter(Ticket.status == ticket_status)

    if department:
        query = query.filter(Ticket.department == department)

    if priority:
        query = query.filter(Ticket.priority == priority)

    if overdue is not None:
        # Overdue means the deadline has passed while the ticket is still live.
        # A resolved ticket is never overdue.
        breached = (Ticket.sla_due_at < utcnow()) & (
            Ticket.status.in_(OPEN_STATUSES)
        )
        query = query.filter(breached if overdue else ~breached)

    return query.order_by(Ticket.id.desc()).all()


def get_visible_ticket(ticket_id, user, db):
    """
    Fetch a ticket the caller is allowed to see.

    A customer asking for someone else's ticket gets 404 rather than 403, so the
    API does not confirm that other customers' tickets exist.
    """

    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    if user.role != "staff" and ticket.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    return ticket


@app.get("/tickets/{ticket_id}", response_model=TicketOut)
def read_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_visible_ticket(ticket_id, user, db)


@app.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket_status(
    ticket_id: int,
    payload: StatusUpdate,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Move a ticket through its lifecycle. Staff only."""

    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    ticket.status = payload.status
    ticket.updated_at = utcnow()

    db.commit()
    db.refresh(ticket)

    return ticket


@app.post("/tickets/{ticket_id}/reclassify", response_model=TicketOut)
def reclassify_ticket(
    ticket_id: int,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Retry classification for a ticket stored while the AI service was down.

    On failure the ticket is left exactly as it was and can be retried later.
    """

    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    previous_status = ticket.status
    classified = apply_classification(ticket, ticket.complaint)

    if not classified:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unavailable. The ticket is unchanged.",
        )

    # A ticket already being worked on keeps its place in the workflow; only a
    # pending one advances to open.
    if previous_status != "pending_classification":
        ticket.status = previous_status

    db.commit()
    db.refresh(ticket)

    return ticket


# ============================================================
# Statistics for the staff dashboard
# ============================================================


def count_by(db, column):
    """Group tickets by one column. Aggregation belongs on the server."""

    rows = db.query(column, func.count(Ticket.id)).group_by(column).all()
    return {key: count for key, count in rows if key is not None}


@app.get("/stats")
def read_stats(
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    overdue = (
        db.query(func.count(Ticket.id))
        .filter(Ticket.sla_due_at < utcnow())
        .filter(Ticket.status.in_(OPEN_STATUSES))
        .scalar()
    )

    by_status = count_by(db, Ticket.status)

    return {
        "total_tickets": db.query(func.count(Ticket.id)).scalar(),
        "by_status": by_status,
        "by_category": count_by(db, Ticket.category),
        "by_priority": count_by(db, Ticket.priority),
        "by_department": count_by(db, Ticket.department),
        "overdue": overdue,
        "pending_classification": by_status.get("pending_classification", 0),
    }
