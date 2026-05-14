"""Unit tests for `scorer.compute`.

Locks down:
- base weights for all four signal types
- recency_decay math (exponential, half-life 30 days)
- buyer_proximity table (economic engaged / unengaged / champion / op / none)
- the formula composes correctly
- icp_total is NOT consumed by the scorer
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import date, timedelta

import pytest

from signal_engine import scorer
from signal_engine.constants import (
    BASE_WEIGHTS,
    BUYER_PROXIMITY,
    RECENCY_HALF_LIFE_DAYS,
)
from signal_engine.models import Company, Contact, Signal


def test_linear_funding_scores_p1(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    score = scorer.compute(linear_signal, company, contact, reference_date=reference_date)

    assert score.base_weight == 4
    assert 0.85 <= score.recency_decay <= 0.90  # ~4 days old
    assert score.buyer_proximity == 1.0  # CEO with engagement
    assert score.signal_score >= 3.0
    assert score.days_since_signal == 4


@pytest.mark.parametrize(
    ("signal_type", "expected_weight"),
    [
        ("funding", 4.0),
        ("exec_hire", 3.0),
        ("ld_posting", 3.0),
        ("headcount_growth", 2.0),
    ],
)
def test_base_weight_per_signal_type(
    signal_type: str,
    expected_weight: float,
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    twisted = replace(linear_signal, signal_type=signal_type)  # type: ignore[arg-type]
    s = scorer.compute(twisted, company, contact, reference_date=reference_date)
    assert s.base_weight == expected_weight
    assert expected_weight == BASE_WEIGHTS[signal_type]


def test_recency_decay_zero_days_is_one(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    company, contact = linear_company_contact
    s = scorer.compute(
        linear_signal,
        company,
        contact,
        reference_date=linear_signal.signal_date,
    )
    assert s.days_since_signal == 0
    assert s.recency_decay == pytest.approx(1.0)


def test_recency_decay_half_life(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    """At 30 days, the multiplier equals exp(-1) ≈ 0.368."""
    company, contact = linear_company_contact
    later = linear_signal.signal_date + timedelta(days=RECENCY_HALF_LIFE_DAYS)
    s = scorer.compute(linear_signal, company, contact, reference_date=later)
    assert s.recency_decay == pytest.approx(math.exp(-1.0))


def test_recency_decay_clamped_to_today_for_future_signals(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    """Signals dated in the future shouldn't yield decay > 1."""
    company, contact = linear_company_contact
    past = linear_signal.signal_date - timedelta(days=10)
    s = scorer.compute(linear_signal, company, contact, reference_date=past)
    assert s.days_since_signal == 0
    assert s.recency_decay == pytest.approx(1.0)


def test_buyer_proximity_economic_engaged(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    s = scorer.compute(linear_signal, company, contact, reference_date=reference_date)
    assert s.buyer_proximity == BUYER_PROXIMITY["economic_engaged"] == 1.0


def test_buyer_proximity_economic_unengaged(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    quiet = replace(contact, engagement_score=2)
    s = scorer.compute(linear_signal, company, quiet, reference_date=reference_date)
    assert s.buyer_proximity == BUYER_PROXIMITY["economic_unengaged"] == 0.9


def test_buyer_proximity_champion_role(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    head_of_ld = replace(contact, buyer_role="champion", engagement_score=9)
    s = scorer.compute(linear_signal, company, head_of_ld, reference_date=reference_date)
    assert s.buyer_proximity == BUYER_PROXIMITY["champion"] == 0.75


def test_buyer_proximity_operational_role(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    hr_manager = replace(contact, buyer_role="operational", engagement_score=0)
    s = scorer.compute(linear_signal, company, hr_manager, reference_date=reference_date)
    assert s.buyer_proximity == BUYER_PROXIMITY["operational"] == 0.6


def test_buyer_proximity_none_zeros_score(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    no_buyer = replace(contact, buyer_role="none", engagement_score=0)
    s = scorer.compute(linear_signal, company, no_buyer, reference_date=reference_date)
    assert s.buyer_proximity == 0.0
    assert s.signal_score == 0.0


def test_formula_composes_correctly(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    s = scorer.compute(linear_signal, company, contact, reference_date=reference_date)
    assert s.signal_score == pytest.approx(
        s.base_weight * s.recency_decay * s.buyer_proximity
    )


def test_icp_total_does_not_affect_score(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    """icp_total gates routing, not scoring — changing it must not move the score."""
    company, contact = linear_company_contact
    low_icp = replace(company, icp_total=11)
    high_icp = replace(company, icp_total=19)
    s_low = scorer.compute(linear_signal, low_icp, contact, reference_date=reference_date)
    s_high = scorer.compute(linear_signal, high_icp, contact, reference_date=reference_date)
    assert s_low.signal_score == pytest.approx(s_high.signal_score)
