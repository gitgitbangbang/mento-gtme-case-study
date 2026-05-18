"""Tests for the assembler's 70-word brand-voice cap enforcement.

The Mento brand-voice rule says total email body must be under 70
words. The assembler enforces this deterministically: it runs the
polish pass and counts words in the result; if over the cap, it
retries up to MAX_POLISH_RETRIES more times with explicit feedback.

These tests use a programmable stubbed Anthropic client whose
.messages.create() returns canned payloads in sequence, simulating
the model returning over-budget on the first attempt and under on
the retry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pytest

from signal_engine import assembler
from signal_engine.constants import MAX_EMAIL_WORDS
from signal_engine.models import (
    BuyerRole,
    Company,
    Contact,
    HookCandidate,
    Signal,
)

# --- Fixtures -----------------------------------------------------------


@dataclass
class _Block:
    type: str
    text: str


@dataclass
class _Response:
    content: list[Any]


class _ProgrammableStub:
    """Returns canned polish payloads in order. Records each .create() call."""

    def __init__(self, payloads: list[str]) -> None:
        self._payloads = list(payloads)
        self.calls: list[dict[str, Any]] = []
        # Wire .messages.create like the real Anthropic client.
        self.messages = self  # type: ignore[assignment]

    def create(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        if not self._payloads:
            raise RuntimeError("stub ran out of payloads")
        payload = self._payloads.pop(0)
        return _Response(content=[_Block(type="text", text=payload)])


def _make_signal() -> Signal:
    from datetime import date

    return Signal(
        signal_id="sig_test",
        signal_type="exec_hire",
        signal_date=date(2026, 5, 10),
        company_id="vanta",
        signal_source="test",
        signal_payload={"role": "CHRO"},
    )


def _make_company() -> Company:
    return Company(
        company_id="vanta",
        company_name="Vanta",
        domain="vanta.com",
        linkedin_url="https://linkedin.com/company/vanta",
        headcount=720,
        industry="SaaS",
        funding_stage="Series C",
        hr_tech_stack=[],
        icp_fit=4,
        icp_timing=4,
        icp_access=4,
        icp_intent=4,
        icp_budget=3,
        icp_total=19,
        lifecycle_stage="MQL",
        recent_news="",
    )


def _make_contact() -> Contact:
    role: BuyerRole = "economic"
    return Contact(
        contact_id="vanta_sarah",
        company_id="vanta",
        first_name="Sarah",
        last_name="Chen",
        email="sarah@vanta.com",
        title="CHRO",
        linkedin_url="https://linkedin.com/in/sarahchen",
        buyer_role=role,
        engagement_score=6,
        linkedin_summary="",
        recent_posts=[],
    )


def _make_hook() -> HookCandidate:
    return HookCandidate(text="A short hook.", word_count=3)


# --- Tests --------------------------------------------------------------


def test_polish_first_attempt_under_cap_returns_immediately() -> None:
    """If the first polish attempt is within budget, no retry happens."""
    short_body = "Hi Sarah,\n\nThree-word hook here.\n\n— Alex"  # 7 words
    stub = _ProgrammableStub([f"Subject: first 90 days\n\n{short_body}"])

    draft = assembler.assemble(
        signal=_make_signal(),
        company=_make_company(),
        contact=_make_contact(),
        selected_hook=_make_hook(),
        client=stub,  # type: ignore[arg-type]
        polish=True,
    )

    assert len(draft.body.split()) <= MAX_EMAIL_WORDS
    assert len(stub.calls) == 1, "expected exactly one polish call"


def test_polish_retries_when_first_attempt_over_cap() -> None:
    """If first attempt exceeds 70 words, retry with explicit feedback."""
    # Token counts (whitespace split): "Hi Sarah," = 2, 80 placeholders = 80,
    # "— Alex" = 2; total 84 for over_body, 44 for under_body.
    over_body = "Hi Sarah,\n\n" + " ".join(["word"] * 80) + "\n\n— Alex"  # 84 words
    under_body = "Hi Sarah,\n\n" + " ".join(["word"] * 40) + "\n\n— Alex"  # 44 words
    stub = _ProgrammableStub(
        [
            f"Subject: first 90 days\n\n{over_body}",
            f"Subject: first 90 days\n\n{under_body}",
        ]
    )

    draft = assembler.assemble(
        signal=_make_signal(),
        company=_make_company(),
        contact=_make_contact(),
        selected_hook=_make_hook(),
        client=stub,  # type: ignore[arg-type]
        polish=True,
    )

    final_words = len(draft.body.split())
    assert final_words <= MAX_EMAIL_WORDS, (
        f"final body should be <= {MAX_EMAIL_WORDS} words, got {final_words}"
    )
    assert len(stub.calls) == 2, "expected one retry after first over-budget attempt"
    # The retry's system prompt should report the first-attempt word count
    # ("previous attempt was 84 words"), so Claude knows the gap.
    retry_system = stub.calls[1]["system"]
    assert "previous" in retry_system.lower()
    assert "84" in retry_system


def test_polish_keeps_shortest_attempt_if_all_attempts_over_cap(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If every attempt exceeds the cap, ship the shortest and warn."""
    # Whitespace token counts: Hi Sarah, (2) + N placeholders + — Alex (2).
    a_body = "Hi Sarah,\n\n" + " ".join(["word"] * 100) + "\n\n— Alex"  # 104 words
    b_body = "Hi Sarah,\n\n" + " ".join(["word"] * 90) + "\n\n— Alex"  # 94 words
    c_body = "Hi Sarah,\n\n" + " ".join(["word"] * 85) + "\n\n— Alex"  # 89 words
    stub = _ProgrammableStub(
        [
            f"Subject: first 90 days\n\n{a_body}",
            f"Subject: first 90 days\n\n{b_body}",
            f"Subject: first 90 days\n\n{c_body}",
        ]
    )

    with caplog.at_level(logging.WARNING):
        draft = assembler.assemble(
            signal=_make_signal(),
            company=_make_company(),
            contact=_make_contact(),
            selected_hook=_make_hook(),
            client=stub,  # type: ignore[arg-type]
            polish=True,
        )

    final_words = len(draft.body.split())
    # All three attempts were over cap; expect we shipped the shortest (c, 89 words).
    assert final_words == 89, f"expected shortest (89 words), got {final_words}"
    # Confirm a warning was logged about exceeding the cap.
    assert any(
        "exceed" in rec.message.lower() or "cap" in rec.message.lower()
        for rec in caplog.records
        if rec.levelno == logging.WARNING
    ), "expected a WARNING log about exceeding the cap"


def test_polish_passes_max_words_in_first_system_prompt() -> None:
    """The first polish system prompt must mention the {max_words} budget."""
    short_body = "Hi Sarah,\n\nShort.\n\n— Alex"
    stub = _ProgrammableStub([f"Subject: first 90 days\n\n{short_body}"])

    assembler.assemble(
        signal=_make_signal(),
        company=_make_company(),
        contact=_make_contact(),
        selected_hook=_make_hook(),
        client=stub,  # type: ignore[arg-type]
        polish=True,
    )

    system_prompt = stub.calls[0]["system"]
    assert str(MAX_EMAIL_WORDS) in system_prompt
    assert "primary directive" in system_prompt.lower() or "hard constraint" in system_prompt.lower()
