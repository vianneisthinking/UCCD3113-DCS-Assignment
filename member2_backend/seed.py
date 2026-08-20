"""
Load demo data so Member 5's dashboard has something to render on day one.

Tickets are written with their classification already filled in, so this script
does not need Member 3's AI service to be running.

    python seed.py           add demo data (does nothing if tickets exist)
    python seed.py --reset   wipe all data first
"""

import sys
from datetime import timedelta

from api import routing
from api.auth import hash_password
from api.models import Base, SessionLocal, Ticket, User, engine, init_db, utcnow


STAFF_EMAIL = "staff@support.com"
STAFF_PASSWORD = "staff1234"
CUSTOMER_EMAIL = "alice@example.com"
CUSTOMER_PASSWORD = "alice1234"


# (complaint, category, priority, status, hours since submission)
# Two entries have no category: they arrived while the AI service was down.
SAMPLE_TICKETS = [
    ("My credit card was charged twice for the same order.",
     "billing_payment", "high", "open", 1),
    ("I was billed for a subscription I cancelled last month.",
     "billing_payment", "medium", "in_progress", 30),
    ("The refund promised two weeks ago has still not arrived.",
     "billing_payment", "high", "open", 9),
    ("The mobile app crashes every time I open the orders page.",
     "technical_support", "high", "in_progress", 3),
    ("Images do not load on the product page in Firefox.",
     "technical_support", "low", "open", 50),
    ("The checkout button does nothing when I click it.",
     "technical_support", "high", "resolved", 96),
    ("I cannot log in, the password reset email never arrives.",
     "account_access", "high", "open", 6),
    ("My account was locked after I changed my phone number.",
     "account_access", "medium", "in_progress", 20),
    ("My parcel is marked as delivered but it never arrived.",
     "delivery_order", "high", "open", 2),
    ("The order I placed last Tuesday has not been shipped yet.",
     "delivery_order", "medium", "resolved", 80),
    ("What are your opening hours during the public holiday?",
     "general_enquiry", "low", "closed", 120),
    ("Do you ship to East Malaysia, and how long does it take?",
     "general_enquiry", "low", "open", 40),
    ("The item I received is the wrong size and colour.",
     None, None, "pending_classification", 4),
    ("I have been waiting on hold for an hour with no answer.",
     None, None, "pending_classification", 1),
]


def get_or_create_user(db, email, password, name, role):
    user = db.query(User).filter(User.email == email).first()

    if user is not None:
        return user

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        role=role,
    )
    db.add(user)
    db.flush()

    return user


def main():
    reset = "--reset" in sys.argv

    if reset:
        print("Wiping all existing data...")
        Base.metadata.drop_all(bind=engine)

    init_db()
    db = SessionLocal()

    try:
        existing = db.query(Ticket).count()

        if existing and not reset:
            print(
                f"Database already contains {existing} tickets. "
                "Nothing to do. Use --reset to wipe and reload."
            )
            return

        staff = get_or_create_user(
            db, STAFF_EMAIL, STAFF_PASSWORD, "Support Staff", "staff"
        )
        customer = get_or_create_user(
            db, CUSTOMER_EMAIL, CUSTOMER_PASSWORD, "Alice Tan", "customer"
        )

        now = utcnow()

        for complaint, category, priority, status, hours_ago in SAMPLE_TICKETS:
            created_at = now - timedelta(hours=hours_ago)
            effective_priority = priority or routing.DEFAULT_PRIORITY

            db.add(
                Ticket(
                    user_id=customer.id,
                    complaint=complaint,
                    status=status,
                    department=routing.department_for(category),
                    sla_due_at=routing.sla_due_at(
                        effective_priority, created_at
                    ),
                    category=category,
                    category_confidence=0.82 if category else None,
                    priority=effective_priority,
                    priority_confidence=0.77 if category else None,
                    model_version="1.0" if category else None,
                    classified_at=created_at if category else None,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )

        db.commit()

        overdue = sum(
            1
            for t in db.query(Ticket).all()
            if t.sla_due_at < now
            and t.status in ("pending_classification", "open", "in_progress")
        )

        print(f"Loaded {len(SAMPLE_TICKETS)} tickets ({overdue} overdue).")
        print()
        print("Demo accounts:")
        print(f"  staff     {STAFF_EMAIL} / {STAFF_PASSWORD}")
        print(f"  customer  {CUSTOMER_EMAIL} / {CUSTOMER_PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
