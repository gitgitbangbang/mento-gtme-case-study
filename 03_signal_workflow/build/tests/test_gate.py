"""Tests for the deterministic portion of `gate.py`.

The LLM verdict (specificity / buyer_context / voice) is not exercised
here — that would require a real Claude API key in CI. We test the
length, banned-phrase, and timeliness checks plus `pick_strongest`
through the public surface using a stubbed Claude client.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from signal_engine import gate
from signal_engine.constants import HOOK_MAX_WORDS, SIGNAL_FRESHNESS_DAYS
from signal_engine.models import Contact, GateVerdict, HookCandidate, Signal

# --- Test doubles -------------------------------------------------------


@dataclass
class _StubResponse:
    """Mimics the shape of anthropic.types.Message used in gate._llm_verdict."""

    content: list[Any]


@dataclass
class _StubBlock:
    type: str
    text: str


class _StubMessages:
    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _StubResponse:
        self.calls.append(kwargs)
        return _StubResponse(content=[_StubBlock(type="text", text=self._payload)])


class _StubClient:
    """Stand-in for anthropic.Anthropic that returns a fixed verdict."""

    def __init__(self, payload: str) -> None:
        self.messages = _StubMessages(payload)


# --- Direct deterministic checks ---------------------------------------


def test_banned_phrase_detection() -> None:
    assert gate._contains_banned_phrase("Hope this finds you well, Jen.") is True
    assert gate._contains_banned_phrase("Wanted to reach out about your Series C.") is True
    assert gate._contains_banned_phrase("Saw Linear's $82M Series C close last week.") is False


def test_parse_verdict_handles_markdown_fences() -> None:
    raw = '```json\n{"specificity": true, "buyer_context": true, "voice_ok": true, "reason": "ok"}\n```'
    parsed = gate._parse_verdict_json(raw)
    assert parsed["specificity"] is True
    assert parsed["voice_ok"] is True


def test_parse_verdict_fills_missing_keys() -> None:
    parsed = gate._parse_verdict_json('{"specificity": true}')
    assert parsed["specificity"] is True
    assert parsed["buyer_context"] is False
    assert parsed["voice_ok"] is False
    assert parsed["reason"] == ""


# --- End-to-end gate.evaluate via stubbed Claude ------------------------


def test_evaluate_passes_clean_hook(
    linear_signal: Signal,
    linear_company_contact: tuple[Any, Contact],
    reference_date: date,
) -> None:
    _company, contact = linear_company_contact
    candidate = HookCandidate(
        text=(
            "Saw Linear's $82M Series C from Accel close last week. With agent-triage "
            "rolling out, your headcount math probably gets interesting fast."
        ),
        word_count=27,
    )
    client = _StubClient(
        '{"specificity": true, "buyer_context": true, "voice_ok": true, "reason": "named investor + role"}'
    )
    verdicts = gate.evaluate(
        [candidate], linear_signal, contact, client=client, reference_date=reference_date
    )
    assert len(verdicts) == 1
    assert verdicts[0].passed is True
    assert verdicts[0].length_ok is True
    assert verdicts[0].timeliness is True


def test_evaluate_rejects_too_long(
    linear_signal: Signal,
    linear_company_contact: tuple[Any, Contact],
    reference_date: date,
) -> None:
    _company, contact = linear_company_contact
    long_text = " ".join(["word"] * (HOOK_MAX_WORDS + 5))
    candidate = HookCandidate(text=long_text, word_count=HOOK_MAX_WORDS + 5)
    client = _StubClient(
        '{"specificity": true, "buyer_context": true, "voice_ok": true, "reason": "ok"}'
    )
    verdicts = gate.evaluate(
        [candidate], linear_signal, contact, client=client, reference_date=reference_date
    )
    assert verdicts[0].length_ok is False
    assert verdicts[0].passed is False
    assert "length" in verdicts[0].reason


def test_evaluate_rejects_banned_phrase(
    linear_signal: Signal,
    linear_company_contact: tuple[Any, Contact],
    reference_date: date,
) -> None:
    _company, contact = linear_company_contact
    candidate = HookCandidate(text="Hope this finds you well, Karri.", word_count=7)
    client = _StubClient(
        '{"specificity": true, "buyer_context": true, "voice_ok": true, "reason": "ok"}'
    )
    verdicts = gate.evaluate(
        [candidate], linear_signal, contact, client=client, reference_date=reference_date
    )
    assert verdicts[0].voice_ok is False
    assert verdicts[0].passed is False
    assert "banned phrase" in verdicts[0].reason


def test_evaluate_rejects_stale_signal(
    linear_signal: Signal,
    linear_company_contact: tuple[Any, Contact],
) -> None:
    _company, contact = linear_company_contact
    way_later = linear_signal.signal_date + timedelta(days=SIGNAL_FRESHNESS_DAYS + 1)
    candidate = HookCandidate(text="Saw Linear's $82M Series C.", word_count=5)
    client = _StubClient(
        '{"specificity": true, "buyer_context": true, "voice_ok": true, "reason": "ok"}'
    )
    verdicts = gate.evaluate(
        [candidate], linear_signal, contact, client=client, reference_date=way_later
    )
    assert verdicts[0].timeliness is False
    assert verdicts[0].passed is False


def test_pick_strongest_returns_first_passing() -> None:
    failing = GateVerdict(
        candidate=HookCandidate(text="x", word_count=1),
        passed=False,
        specificity=False,
        timeliness=True,
        buyer_context=False,
        length_ok=True,
        voice_ok=True,
        reason="failed",
    )
    passing = GateVerdict(
        candidate=HookCandidate(text="y", word_count=1),
        passed=True,
        specificity=True,
        timeliness=True,
        buyer_context=True,
        length_ok=True,
        voice_ok=True,
        reason="ok",
    )
    assert gate.pick_strongest([failing, passing]) is passing
    assert gate.pick_strongest([failing, failing]) is None
