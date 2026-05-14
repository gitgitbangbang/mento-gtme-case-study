"""Tests for `detector.detect`.

Covers the `days_ago` -> signal_date resolution that keeps the demo
fresh as the calendar moves on, plus the validation guard for
fixtures missing both `days_ago` and a literal `signal_date`.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from signal_engine import detector
from signal_engine.detector import detect


def test_days_ago_resolves_against_reference_date(reference_date: date) -> None:
    """The Linear fixture has days_ago=4, so signal_date should be ref-4."""
    sig = detect("funding", "linear", reference_date=reference_date)
    assert sig.signal_date == reference_date - timedelta(days=4)


@pytest.mark.parametrize(
    ("signal_type", "company_id", "expected_days"),
    [
        ("funding", "linear", 4),
        ("exec_hire", "vanta", 8),
        ("ld_posting", "ramp", 14),
        ("headcount_growth", "retool", 21),
    ],
)
def test_all_fixtures_resolve_days_ago(
    signal_type: str,
    company_id: str,
    expected_days: int,
    reference_date: date,
) -> None:
    sig = detect(signal_type, company_id, reference_date=reference_date)
    assert sig.signal_date == reference_date - timedelta(days=expected_days)


def test_detect_defaults_to_today_when_no_reference_date() -> None:
    """No reference_date -> use date.today() so the live CLI stays fresh."""
    sig = detect("funding", "linear")
    delta = (date.today() - sig.signal_date).days
    assert delta == 4


def test_unknown_signal_company_pair_raises() -> None:
    with pytest.raises(ValueError, match="No fixture"):
        detect("funding", "nope-not-a-real-company")


def test_fixture_with_literal_signal_date_is_used_as_is(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reference_date: date,
) -> None:
    """If a fixture sets `signal_date` literally, the detector must not override it."""
    custom_root = tmp_path / "signals"
    custom_root.mkdir()
    payload = {
        "signal_id": "sig_literal_2024_01_01",
        "signal_type": "funding",
        "signal_date": "2024-01-01",
        "company_id": "linear",
        "signal_source": "test",
        "signal_payload": {"round": "Series A"},
    }
    (custom_root / "linear_funding.json").write_text(json.dumps(payload))
    monkeypatch.setattr(detector, "FIXTURE_ROOT", custom_root)

    sig = detect("funding", "linear", reference_date=reference_date)
    assert sig.signal_date == date(2024, 1, 1)


def test_fixture_missing_both_date_fields_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fixture with neither `signal_date` nor `days_ago` must fail loudly."""
    custom_root = tmp_path / "signals"
    custom_root.mkdir()
    bad = {
        "signal_id": "sig_bad",
        "signal_type": "funding",
        "company_id": "linear",
        "signal_source": "test",
        "signal_payload": {},
    }
    (custom_root / "linear_funding.json").write_text(json.dumps(bad))
    monkeypatch.setattr(detector, "FIXTURE_ROOT", custom_root)

    with pytest.raises(ValueError, match=r"signal_date.*days_ago"):
        detect("funding", "linear")
