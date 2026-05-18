"""End-to-end integration test for the CLI orchestrator.

Stubs `anthropic.Anthropic` inside each module that calls it
(personaliser, gate, assembler) so the test exercises the full
pipeline — detector → enricher → scorer → router → drafting → HITL →
audit — with zero network. Confirms:

- the CLI returns exit code 0
- every pipeline stage prints to stdout
- the audit JSON lands with the expected structure
- the audit captures the (stubbed) hooks, draft, and SDR decision

Coverage win: bumps run.py from 0% to ~80%.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from signal_engine import assembler, auditor, gate, personaliser, run, scorer

# ----------------------------------------------------------------------
# Stub Anthropic client + canned responses per call type
# ----------------------------------------------------------------------


@dataclass
class _Block:
    """Mimics anthropic.types.TextBlock."""

    type: str
    text: str


@dataclass
class _Response:
    """Mimics anthropic.types.Message."""

    content: list[_Block]


class _StubMessages:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Response:
        self.calls.append(kwargs)
        return _Response(content=[_Block(type="text", text=self.payload)])


class _StubClient:
    def __init__(self, payload: str = "", **_kwargs: Any) -> None:
        self.messages = _StubMessages(payload)


# Canned payloads tuned to the expected output shape of each module.

_HOOKS_JSON = json.dumps(
    [
        "Saw Linear's $82M Series C from Accel close last week. With the agent-triage "
        "rollout in parallel, your headcount math probably gets interesting fast.",
        "Congrats on the Accel-led $82M — the rate at which Linear is shipping right "
        "now means the manager bench question is about to get loud.",
        "Linear's $82M from Accel landed last week; the post-funding manager-bench gap "
        "is usually the first thing to break.",
    ]
)

_GATE_PASS_JSON = json.dumps(
    {
        "specificity": True,
        "buyer_context": True,
        "voice_ok": True,
        "reason": "Names Accel and the funding amount; relates to Karri's role.",
    }
)

_POLISHED_DRAFT = """Subject: manager bench

Hi Karri,

Saw Linear's $82M Series C from Accel close last week. With the agent-triage rollout in parallel, your headcount math probably gets interesting fast.

Pattern post-funding: hiring outpaces the manager bench by 90 days. Performance dips at the team-lead layer. Brex and Vercel saw it.

Happy to share the playbook. Worth 15 minutes?

— Alex
"""


def _make_stub_factory(payload: str) -> type[_StubClient]:
    """Return a subclass of _StubClient that pre-binds the canned payload."""

    class _Bound(_StubClient):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(payload=payload, **kwargs)

    return _Bound


# ----------------------------------------------------------------------
# Fixtures and helpers
# ----------------------------------------------------------------------


@pytest.fixture
def stubbed_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    """Patch the three Anthropic-using modules and redirect audit/ to tmp."""
    # Ensure the personaliser/gate/assembler can construct their clients
    # — they look up ANTHROPIC_API_KEY from the environment.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Replace each module's reference to the Anthropic class with a stub
    # that returns the right canned payload for that call.
    monkeypatch.setattr(personaliser, "Anthropic", _make_stub_factory(_HOOKS_JSON))
    monkeypatch.setattr(gate, "Anthropic", _make_stub_factory(_GATE_PASS_JSON))
    monkeypatch.setattr(assembler, "Anthropic", _make_stub_factory(_POLISHED_DRAFT))

    # Redirect audit/ to a tmp directory so the test doesn't pollute the
    # real audit log.
    audit_dir = tmp_path / "audit"
    monkeypatch.setattr(auditor, "AUDIT_ROOT", audit_dir)
    return audit_dir


def _pin_today(monkeypatch: pytest.MonkeyPatch, today: date) -> None:
    """Pin date.today() inside scorer and run for deterministic recency_decay."""
    import datetime as _dt

    class _PinnedDate(_dt.date):
        @classmethod
        def today(cls) -> _dt.date:
            return today

    monkeypatch.setattr(scorer, "date", _PinnedDate)
    monkeypatch.setattr(run, "datetime", _dt.datetime)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def test_run_funding_linear_end_to_end(
    stubbed_pipeline: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full pipeline with stubbed Claude: exit 0, audit written, stages printed."""
    _pin_today(monkeypatch, date(2026, 5, 14))

    exit_code = run.main(
        ["--signal", "funding", "--company", "linear", "--non-interactive"]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    out = captured.out

    # Every stage banner prints in order.
    for marker in [
        "[1/5] Detecting",
        "[2/5] Enriching",
        "[3/5] Scoring",
        "[4/5] Routing: P1",
        "[5/5] Drafting",
        "[STUB] Would have triggered Smartlead",
        "[AUDIT]",
    ]:
        assert marker in out, f"missing marker in CLI output: {marker!r}"

    # The polished draft body should land in stdout.
    assert "Hi Karri," in out
    assert "manager bench" in out

    # An audit JSON must be written into the patched audit root.
    audits = list(stubbed_pipeline.glob("*.json"))
    assert len(audits) == 1, f"expected exactly one audit file, got {audits}"

    payload = json.loads(audits[0].read_text())
    assert payload["tier"] == "P1"
    assert payload["sdr_decision"] == "send"
    assert payload["company"]["company_name"] == "Linear"
    assert payload["contact"]["first_name"] == "Karri"
    assert len(payload["hook_candidates"]) == 3
    assert any(c["passed"] for c in payload["hook_candidates"])
    assert payload["selected_hook"]
    assert payload["draft"]["subject"] == "manager bench"
    assert "Series C" in payload["draft"]["body"] or "Accel" in payload["draft"]["body"]


def test_run_invokes_smartlead_stub_on_send(
    stubbed_pipeline: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI should reference the correct Smartlead campaign id on send."""
    _pin_today(monkeypatch, date(2026, 5, 14))

    exit_code = run.main(
        [
            "--signal", "exec_hire",
            "--company", "vanta",
            "--non-interactive",
            "--no-polish",
        ]
    )
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "mento-signal-exec-hire" in out


def test_run_no_polish_skips_assembler_claude_call(
    stubbed_pipeline: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With --no-polish, the assembler should not instantiate its Anthropic stub."""
    _pin_today(monkeypatch, date(2026, 5, 14))

    # Replace assembler.Anthropic with a sentinel that records construction.
    constructed: list[bool] = []

    class _Sentinel:
        def __init__(self, **_kwargs: Any) -> None:
            constructed.append(True)

    monkeypatch.setattr(assembler, "Anthropic", _Sentinel)

    exit_code = run.main(
        [
            "--signal", "funding",
            "--company", "linear",
            "--non-interactive",
            "--no-polish",
        ]
    )
    assert exit_code == 0
    assert constructed == [], "assembler should not have constructed an Anthropic client"


def test_run_all_processes_four_pairs(
    stubbed_pipeline: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--all runs all four canonical pairs and prints a summary table."""
    _pin_today(monkeypatch, date(2026, 5, 14))

    exit_code = run.main(["--all"])
    assert exit_code == 0

    out = capsys.readouterr().out

    # Each pair fires its own pipeline. The detect line per pair must appear.
    for signal_type, company_id in [
        ("funding", "linear"),
        ("exec_hire", "vanta"),
        ("ld_posting", "ramp"),
        ("headcount_growth", "retool"),
    ]:
        assert f"Detecting signal: {signal_type} @ {company_id}" in out, (
            f"missing pipeline run for {signal_type} @ {company_id}"
        )

    # Summary table sentinels.
    assert "BATCH SUMMARY" in out
    assert "4/4" in out or "4 signals" in out, "expected summary count line"

    # Four audit files written to the patched root.
    audits = list(stubbed_pipeline.glob("*.json"))
    assert len(audits) == 4, f"expected 4 audit files, got {len(audits)}: {audits}"


def test_all_is_mutually_exclusive_with_signal_company(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--all + --signal should error rather than run with mixed arguments."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(SystemExit):
        run.main(["--all", "--signal", "funding", "--company", "linear"])


def test_missing_signal_and_company_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without --all, --signal AND --company are both required."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(SystemExit):
        run.main([])
    with pytest.raises(SystemExit):
        run.main(["--signal", "funding"])
    with pytest.raises(SystemExit):
        run.main(["--company", "linear"])


def test_api_key_flag_overrides_environment(
    stubbed_pipeline: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--api-key flag should win over the ANTHROPIC_API_KEY shell env var."""
    _pin_today(monkeypatch, date(2026, 5, 14))
    # Seed the env var with one value; the flag should override it.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key-should-lose")

    # Capture the api_key the stubbed Anthropic constructor sees so we can
    # verify the flag value reached the SDK call site.
    captured_keys: list[str] = []

    class _RecordingStub:
        def __init__(self, *, api_key: str = "", **_kwargs: Any) -> None:
            captured_keys.append(api_key)
            self.messages = _StubMessages(_HOOKS_JSON)

    monkeypatch.setattr(personaliser, "Anthropic", _RecordingStub)
    monkeypatch.setattr(gate, "Anthropic", _make_stub_factory(_GATE_PASS_JSON))
    monkeypatch.setattr(assembler, "Anthropic", _make_stub_factory(_POLISHED_DRAFT))

    flag_key = "flag-key-should-win-sk-ant-api03-test"
    exit_code = run.main(
        [
            "--signal", "funding",
            "--company", "linear",
            "--non-interactive",
            "--api-key", flag_key,
        ]
    )
    assert exit_code == 0
    # The personaliser instantiated _RecordingStub with the flag value, not
    # the env-var value.
    assert flag_key in captured_keys, (
        f"--api-key flag did not reach Anthropic constructor; "
        f"saw keys={captured_keys!r}"
    )
    assert "env-key-should-lose" not in captured_keys
