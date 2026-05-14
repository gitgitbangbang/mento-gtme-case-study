"""Shared fixtures for the deterministic-core tests.

Pins a reference date so recency_decay is stable across CI runs. The
detector and scorer both default to date.today() in production — the
override is only for tests, threaded through detect(reference_date=...)
so fixture-derived signal_dates land deterministically.
"""

from __future__ import annotations

from datetime import date

import pytest

from signal_engine.detector import detect
from signal_engine.enricher import enrich
from signal_engine.models import Company, Contact, Signal


@pytest.fixture
def reference_date() -> date:
    """Pin 'today' to the day the fixtures were authored against."""
    return date(2026, 5, 14)


@pytest.fixture
def linear_signal(reference_date: date) -> Signal:
    return detect("funding", "linear", reference_date=reference_date)


@pytest.fixture
def vanta_signal(reference_date: date) -> Signal:
    return detect("exec_hire", "vanta", reference_date=reference_date)


@pytest.fixture
def ramp_signal(reference_date: date) -> Signal:
    return detect("ld_posting", "ramp", reference_date=reference_date)


@pytest.fixture
def retool_signal(reference_date: date) -> Signal:
    return detect("headcount_growth", "retool", reference_date=reference_date)


@pytest.fixture
def linear_company_contact(linear_signal: Signal) -> tuple[Company, Contact]:
    return enrich(linear_signal)


@pytest.fixture
def vanta_company_contact(vanta_signal: Signal) -> tuple[Company, Contact]:
    return enrich(vanta_signal)


@pytest.fixture
def ramp_company_contact(ramp_signal: Signal) -> tuple[Company, Contact]:
    return enrich(ramp_signal)


@pytest.fixture
def retool_company_contact(retool_signal: Signal) -> tuple[Company, Contact]:
    return enrich(retool_signal)
