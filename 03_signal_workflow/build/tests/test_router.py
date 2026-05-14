"""Unit tests for `router.assign`.

Covers every cell of the routing table from 03_signal_scoring_framework.md:
P1, P2 (mid-score), P2 (icp override), P3, Discovery, Park.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from signal_engine import router, scorer
from signal_engine.models import Company, Contact, ScoreBreakdown, Signal


def _score(value: float) -> ScoreBreakdown:
    """Build a ScoreBreakdown with `signal_score=value` and noise multipliers."""
    return ScoreBreakdown(
        base_weight=4.0,
        recency_decay=value / 4.0 if value > 0 else 0.0,
        buyer_proximity=1.0,
        signal_score=value,
        days_since_signal=0,
    )


def test_linear_fixture_routes_p1(
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = linear_company_contact
    s = scorer.compute(linear_signal, company, contact, reference_date=reference_date)
    assert router.assign(s, company) == "P1"


def test_retool_fixture_routes_p3(
    retool_signal: Signal,
    retool_company_contact: tuple[Company, Contact],
    reference_date: date,
) -> None:
    company, contact = retool_company_contact
    s = scorer.compute(retool_signal, company, contact, reference_date=reference_date)
    assert router.assign(s, company) == "P3"


def test_park_when_icp_below_floor(linear_company_contact: tuple[Company, Contact]) -> None:
    company, _ = linear_company_contact
    parked = replace(company, icp_total=8)
    assert router.assign(_score(3.5), parked) == "Park"
    # Park applies even if score is high.
    assert router.assign(_score(0.0), parked) == "Park"


def test_discovery_when_score_zero_and_icp_in_range(
    linear_company_contact: tuple[Company, Contact],
) -> None:
    company, _ = linear_company_contact
    in_icp = replace(company, icp_total=12)
    assert router.assign(_score(0.0), in_icp) == "Discovery"


@pytest.mark.parametrize("icp", [11, 14, 18, 20])
def test_p1_when_score_high_and_icp_in_range(
    icp: int,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    company, _ = linear_company_contact
    twisted = replace(company, icp_total=icp)
    assert router.assign(_score(3.0), twisted) == "P1"


@pytest.mark.parametrize("score_value", [1.5, 2.0, 2.99])
def test_p2_mid_score(
    score_value: float,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    company, _ = linear_company_contact
    twisted = replace(company, icp_total=14)
    assert router.assign(_score(score_value), twisted) == "P2"


def test_p2_icp_override(linear_company_contact: tuple[Company, Contact]) -> None:
    """Low score (<1.5) but icp_total >= 16 should still hit P2."""
    company, _ = linear_company_contact
    high_icp = replace(company, icp_total=18)
    # Use a tiny non-zero score to avoid the Discovery branch.
    assert router.assign(_score(0.5), high_icp) == "P2"


def test_p3_low_score_mid_icp(linear_company_contact: tuple[Company, Contact]) -> None:
    company, _ = linear_company_contact
    mid_icp = replace(company, icp_total=13)
    # Tiny non-zero score keeps us out of Discovery.
    assert router.assign(_score(0.5), mid_icp) == "P3"


@pytest.mark.parametrize(
    "tier",
    ["P1", "P2", "P3", "Discovery", "Park"],
)
def test_channel_for_returns_human_readable_label(tier: str) -> None:
    label = router.channel_for(tier)  # type: ignore[arg-type]
    assert isinstance(label, str)
    assert len(label) > 0
