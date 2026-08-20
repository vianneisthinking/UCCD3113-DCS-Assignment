"""
Ticket-routing business logic.

Member 3's AI service decides *what* a complaint is about. This module decides
*who handles it* and *by when* — that decision belongs to the backend, not to
the classifier.
"""

from datetime import datetime, timedelta


# Applied when the AI service was unavailable and the ticket could not be
# classified. A safe default beats dropping the complaint.
DEFAULT_DEPARTMENT = "General Enquiry"
DEFAULT_PRIORITY = "medium"


# An explicit map rather than a string transformation of the category name:
# a real support desk may route two categories to one team, and this is the
# seam where that change would happen.
CATEGORY_TO_DEPARTMENT = {
    "technical_support": "Technical Support",
    "account_access": "Account Access",
    "billing_payment": "Billing and Payment",
    "delivery_order": "Delivery and Order",
    "general_enquiry": "General Enquiry",
}


# Hours a department has to respond, by predicted priority.
SLA_HOURS = {
    "high": 4,
    "medium": 24,
    "low": 72,
}


def department_for(category):
    """Return the department that handles this AI category."""
    return CATEGORY_TO_DEPARTMENT.get(category, DEFAULT_DEPARTMENT)


def sla_due_at(priority, created_at):
    """Return the response deadline for a ticket of this priority."""
    hours = SLA_HOURS.get(priority, SLA_HOURS[DEFAULT_PRIORITY])
    return created_at + timedelta(hours=hours)


if __name__ == "__main__":
    now = datetime(2026, 8, 10, 12, 0, 0)

    assert department_for("billing_payment") == "Billing and Payment"
    assert department_for("technical_support") == "Technical Support"
    # Unknown and missing categories both fall back safely.
    assert department_for(None) == DEFAULT_DEPARTMENT
    assert department_for("something_the_model_invented") == DEFAULT_DEPARTMENT

    assert sla_due_at("high", now) == datetime(2026, 8, 10, 16, 0, 0)
    assert sla_due_at("medium", now) == datetime(2026, 8, 11, 12, 0, 0)
    assert sla_due_at("low", now) == datetime(2026, 8, 13, 12, 0, 0)
    # An unclassified ticket is treated as medium, not as "no deadline".
    assert sla_due_at(None, now) == sla_due_at("medium", now)

    print("routing.py: all checks passed")
