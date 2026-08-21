"""Narrow deterministic safety policy for clearly severe support tickets.

The statistical model remains the default priority classifier.  This module only
overrides it for a small set of business-critical patterns where a false Medium
or Low route would be unacceptable.  The public API does not expose the internal
decision source.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import os
import re
from typing import Mapping


SEVERE_FINANCIAL_AMOUNT_THRESHOLD = Decimal(
    os.getenv("SEVERE_FINANCIAL_AMOUNT_THRESHOLD", "50000")
)

# A policy match is a deterministic routing decision rather than a model
# probability.  The external confidence field therefore reports certainty in
# the final routing rule, not the probability produced for the overridden ML
# class.
PRIORITY_POLICY_CONFIDENCE = 1.0

_MONEY_PATTERN = re.compile(
    r"(?P<currency>\$|(?<![a-z])usd|(?<![a-z])rm)\s*"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<scale>million|m\b|thousand|k\b)?",
    re.IGNORECASE,
)

_FINANCIAL_ACTION_PATTERN = re.compile(
    r"\b(?:transaction|transfer|payment|charge|charged|debit|debited|"
    r"withdrawal|withdrawn|card|bank account|money)\b",
    re.IGNORECASE,
)

_UNAUTHORISED_PATTERN = re.compile(
    r"\b(?:unauthori[sz]ed|fraud(?:ulent)?|without (?:my )?permission|"
    r"did not make|didn['’]?t make|not mine|never approved|not approved|"
    r"stolen card)\b",
    re.IGNORECASE,
)

_FINANCIAL_HARM_PATTERN = re.compile(
    r"\b(?:transaction|transfer(?:red)?|charged|debited|deducted|withdrawn|"
    r"missing|stolen|lost|refund (?:was )?reversed)\b",
    re.IGNORECASE,
)

_INFORMATIONAL_FINANCE_PATTERN = re.compile(
    r"^\s*(?:what|which|how|can i|could i|do you|does the service)\b.*"
    r"\b(?:fee|fees|method|methods|accept|supported|limit|limits|exchange rate)\b",
    re.IGNORECASE,
)

_ACCOUNT_TAKEOVER_PATTERN = re.compile(
    r"(?:\baccount\b.{0,45}\b(?:hacked|taken over|compromised)\b|"
    r"\b(?:hacker|someone|another person|unknown person)\b.{0,55}"
    r"\b(?:changed|reset)\b.{0,30}\b(?:password|recovery email|login)\b|"
    r"\b(?:password|recovery email)\b.{0,35}\bchanged\b.{0,35}"
    r"\b(?:without (?:my )?permission|by someone|by another person)\b)",
    re.IGNORECASE,
)

_OUTAGE_SCOPE_PATTERN = re.compile(
    r"\b(?:all users|every user|everyone|company[- ]wide|organisation[- ]wide|"
    r"organization[- ]wide|entire (?:service|system|platform)|whole (?:service|system))\b",
    re.IGNORECASE,
)

_OUTAGE_STATE_PATTERN = re.compile(
    r"\b(?:complete outage|outage|down|offline|unavailable|cannot be accessed|"
    r"can['’]?t be accessed|stopped working)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PriorityDecision:
    """Internal priority result; only label/confidence are returned publicly."""

    label: str
    confidence: float
    overridden: bool
    reason: str | None = None


def parse_monetary_amounts(text: str) -> list[Decimal]:
    """Return normalized amounts for supported $, USD, and RM formats."""

    amounts: list[Decimal] = []
    multipliers = {
        "million": Decimal("1000000"),
        "m": Decimal("1000000"),
        "thousand": Decimal("1000"),
        "k": Decimal("1000"),
    }

    for match in _MONEY_PATTERN.finditer(text):
        try:
            number = Decimal(match.group("number").replace(",", ""))
        except InvalidOperation:
            continue

        scale = (match.group("scale") or "").lower()
        amounts.append(number * multipliers.get(scale, Decimal("1")))

    return amounts


def _policy_reason(text: str) -> str | None:
    financial_action = bool(_FINANCIAL_ACTION_PATTERN.search(text))
    unauthorised = bool(_UNAUTHORISED_PATTERN.search(text))

    if financial_action and unauthorised:
        return "unauthorised_financial_activity"

    amounts = parse_monetary_amounts(text)
    is_large_amount = any(
        amount >= SEVERE_FINANCIAL_AMOUNT_THRESHOLD for amount in amounts
    )
    if (
        is_large_amount
        and _FINANCIAL_HARM_PATTERN.search(text)
        and not _INFORMATIONAL_FINANCE_PATTERN.search(text)
    ):
        return "large_financial_harm"

    if _ACCOUNT_TAKEOVER_PATTERN.search(text):
        return "account_takeover"

    if _OUTAGE_SCOPE_PATTERN.search(text) and _OUTAGE_STATE_PATTERN.search(text):
        return "complete_multi_user_outage"

    return None


def apply_priority_policy(
    complaint: str,
    model_label: str,
    model_probabilities: Mapping[str, float],
) -> PriorityDecision:
    """Apply severe-case routing, otherwise preserve the model decision."""

    reason = _policy_reason(complaint)
    if reason is not None:
        return PriorityDecision(
            label="high",
            confidence=PRIORITY_POLICY_CONFIDENCE,
            overridden=True,
            reason=reason,
        )

    return PriorityDecision(
        label=model_label,
        confidence=float(model_probabilities[model_label]),
        overridden=False,
    )
