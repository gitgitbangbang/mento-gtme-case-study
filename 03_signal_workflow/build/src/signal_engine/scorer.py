"""Stage 3: Score the signal.

Implements `signal_score = base_weight * recency_decay * buyer_proximity`
exactly as specified in 03_signal_scoring_framework.md. icp_total is NOT
folded into the score — it gates the routing tier in `router.py`.

Pure deterministic math. No external calls. No side effects.
"""

from __future__ import annotations

import logging
import math
from datetime import date

from signal_engine.constants import (
    BASE_WEIGHTS,
    BUYER_PROXIMITY,
    ENGAGEMENT_SCORE_THRESHOLD,
    RECENCY_HALF_LIFE_DAYS,
)
from signal_engine.models import Company, Contact, ScoreBreakdown, Signal

logger = logging.getLogger(__name__)


def compute(
    signal: Signal,
    company: Company,
    contact: Contact,
    *,
    reference_date: date | None = None,
) -> ScoreBreakdown:
    """Return the scored breakdown for one (signal, company, contact) tuple.

    `reference_date` defaults to today. Tests pin it so they don't drift.
    `company` is accepted for parity with the router contract — the formula
    deliberately does not consume `company.icp_total`; that lives at routing.
    """
    del company  # unused; documents the architectural choice above
    today = reference_date or date.today()
    base_weight = BASE_WEIGHTS[signal.signal_type]
    days_since = max((today - signal.signal_date).days, 0)
    recency_decay = math.exp(-days_since / RECENCY_HALF_LIFE_DAYS)
    proximity = _buyer_proximity(contact)
    score = base_weight * recency_decay * proximity

    breakdown = ScoreBreakdown(
        base_weight=base_weight,
        recency_decay=recency_decay,
        buyer_proximity=proximity,
        signal_score=score,
        days_since_signal=days_since,
    )
    logger.info(
        "scorer: type=%s base=%.3f decay=%.3f prox=%.3f score=%.3f days=%d",
        signal.signal_type,
        base_weight,
        recency_decay,
        proximity,
        score,
        days_since,
    )
    return breakdown


def _buyer_proximity(contact: Contact) -> float:
    """Map a Contact onto the buyer-proximity multiplier table."""
    role = contact.buyer_role
    if role == "none":
        return BUYER_PROXIMITY["none"]
    if role == "economic":
        if contact.engagement_score >= ENGAGEMENT_SCORE_THRESHOLD:
            return BUYER_PROXIMITY["economic_engaged"]
        return BUYER_PROXIMITY["economic_unengaged"]
    if role == "champion":
        return BUYER_PROXIMITY["champion"]
    if role in {"operational", "generic"}:
        return BUYER_PROXIMITY["operational"]
    return BUYER_PROXIMITY["none"]
