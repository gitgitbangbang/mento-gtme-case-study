"""Tests for the JSON audit logger."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from signal_engine import auditor
from signal_engine.models import Company, Contact, Signal


def test_audit_write_emits_expected_top_level_keys(
    tmp_path: Path,
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    company, contact = linear_company_contact
    entry = auditor.new_entry(
        run_id="test-1",
        started_at=datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC),
        signal=linear_signal,
        company=company,
        contact=contact,
    )
    entry.score = {
        "base_weight": 4.0,
        "recency_decay": 0.875,
        "buyer_proximity": 1.0,
        "signal_score": 3.5,
        "days_since_signal": 4,
    }
    entry.tier = "P1"
    entry.selected_hook = "Saw Linear's $82M Series C close last week."
    entry.gate_decision = {"passed": True, "reason": "named investor"}
    entry.draft = {"subject": "manager bench", "body": "Hi Karri,...", "template_name": "funding"}
    entry.sdr_decision = "send"
    entry.completed_at = datetime(2026, 5, 14, 10, 0, 30, tzinfo=UTC)

    path = auditor.write(entry, audit_root=tmp_path)
    data = json.loads(path.read_text())

    required = {
        "run_id",
        "started_at",
        "completed_at",
        "signal",
        "company",
        "contact",
        "score",
        "tier",
        "hook_candidates",
        "selected_hook",
        "gate_decision",
        "draft",
        "sdr_decision",
        "sdr_edited_body",
    }
    assert required.issubset(data.keys())


def test_audit_filename_pattern(
    tmp_path: Path,
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    company, contact = linear_company_contact
    entry = auditor.new_entry(
        run_id="test-2",
        started_at=datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC),
        signal=linear_signal,
        company=company,
        contact=contact,
    )
    entry.completed_at = datetime(2026, 5, 14, 10, 0, 30, tzinfo=UTC)
    path = auditor.write(entry, audit_root=tmp_path)
    # Filename: <YYYYMMDDTHHMMSSZ>_<signal_id>.json
    assert path.name.startswith("20260514T100000Z_")
    assert path.name.endswith(f"_{linear_signal.signal_id}.json")


def test_audit_signal_date_is_isoformat_string(
    tmp_path: Path,
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    """The fixture loader gives us date objects; audit JSON should serialise them."""
    company, contact = linear_company_contact
    entry = auditor.new_entry(
        run_id="test-3",
        started_at=datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC),
        signal=linear_signal,
        company=company,
        contact=contact,
    )
    entry.completed_at = datetime(2026, 5, 14, 10, 0, 30, tzinfo=UTC)
    path = auditor.write(entry, audit_root=tmp_path)
    data = json.loads(path.read_text())
    assert data["signal"]["signal_date"] == linear_signal.signal_date.isoformat()


def test_audit_handles_empty_post_hitl_state(
    tmp_path: Path,
    linear_signal: Signal,
    linear_company_contact: tuple[Company, Contact],
) -> None:
    """Discovery/Park exit paths write an audit with no hooks or draft."""
    company, contact = linear_company_contact
    entry = auditor.new_entry(
        run_id="test-4",
        started_at=datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC),
        signal=linear_signal,
        company=company,
        contact=contact,
    )
    entry.tier = "Discovery"
    entry.completed_at = datetime(2026, 5, 14, 10, 0, 30, tzinfo=UTC)

    path = auditor.write(entry, audit_root=tmp_path)
    data = json.loads(path.read_text())
    assert data["tier"] == "Discovery"
    assert data["hook_candidates"] == []
    assert data["draft"] == {}
    assert data["sdr_decision"] == ""
