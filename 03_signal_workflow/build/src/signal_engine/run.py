"""Signal-engine CLI entry point.

Usage:

    # one focused signal end-to-end
    uv run python -m signal_engine.run --signal funding --company linear

    # all four signal/company pairs in sequence, with a summary table
    uv run python -m signal_engine.run --all --non-interactive

Walks one signal end to end through detect -> enrich -> score -> route
-> personaliser -> gate -> assembler -> HITL terminal -> audit log.
`--all` runs the canonical four pairs (funding/linear, exec_hire/vanta,
ld_posting/ramp, headcount_growth/retool) back to back; HITL is
auto-skipped (treated as Send) so the batch can finish unattended.

Direct prints are intentional here — this is the user-facing surface.
Every other module logs through `logging`.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from signal_engine import auditor, detector, enricher, gate, personaliser, router, scorer
from signal_engine.assembler import assemble
from signal_engine.constants import SMARTLEAD_CAMPAIGNS
from signal_engine.models import (
    AuditEntry,
    Draft,
    GateVerdict,
    HookCandidate,
    ScoreBreakdown,
)

_SIGNAL_CHOICES: Final[list[str]] = ["funding", "exec_hire", "ld_posting", "headcount_growth"]
_COMPANY_CHOICES: Final[list[str]] = ["linear", "vanta", "ramp", "retool"]

# Canonical pairs for --all. Matches detector._SIGNAL_FILE_MAP one-for-one.
_ALL_PAIRS: Final[list[tuple[str, str]]] = [
    ("funding", "linear"),
    ("exec_hire", "vanta"),
    ("ld_posting", "ramp"),
    ("headcount_growth", "retool"),
]

_BANNER: Final[str] = "─" * 60


@dataclass
class _RunResult:
    """Captures the outcome of one signal run for the batch summary table."""

    signal_type: str
    company_id: str
    tier: str
    candidates_total: int
    candidates_passed: int
    draft_subject: str  # empty string if no draft produced
    sdr_decision: str  # "send" / "edit" / "skip" / "" (early exit)
    audit_path: Path | None
    outcome: str  # human-readable: "draft sent", "manual review", "discovery", "park"


def main(argv: list[str] | None = None) -> int:
    """Run one signal (or all four with --all). Returns shell exit code."""
    parser = argparse.ArgumentParser(
        prog="signal_engine",
        description="Mento signal engine — runs one buying signal end to end.",
    )
    parser.add_argument(
        "--signal",
        choices=_SIGNAL_CHOICES,
        help="Signal type to detect. Required unless --all is set.",
    )
    parser.add_argument(
        "--company",
        choices=_COMPANY_CHOICES,
        help="Company to target. Required unless --all is set.",
    )
    parser.add_argument(
        "--all",
        dest="run_all",
        action="store_true",
        help=(
            "Run all four canonical (signal, company) pairs in sequence. "
            "Implies --non-interactive. Prints a summary table at the end."
        ),
    )
    parser.add_argument(
        "--no-polish",
        action="store_true",
        help="Skip the assembler's final Claude voice pass (saves one API call per signal).",
    )
    parser.add_argument(
        "--sdr-signature",
        default="Alex",
        help="Name used in the signoff line (default: Alex).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip the HITL prompt; auto-treat as 'send'. Always on under --all.",
    )
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help=(
            "Anthropic API key. If set, overrides both the ANTHROPIC_API_KEY "
            "shell environment variable and any value in .env. Highest "
            "precedence."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Echo INFO-level logs from each pipeline stage to stderr.",
    )
    args = parser.parse_args(argv)

    if args.run_all:
        if args.signal or args.company:
            parser.error("--all is mutually exclusive with --signal / --company.")
        args.non_interactive = True  # batch mode never prompts
    else:
        if not args.signal or not args.company:
            parser.error("Either pass --all, or pass both --signal and --company.")

    # override=True so a value in .env wins over an empty ANTHROPIC_API_KEY
    # that some shells / launchers export by default.
    load_dotenv(override=True)
    # --api-key beats both .env and the shell env var. Done after load_dotenv
    # so the override always wins, never gets clobbered.
    if args.api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.api_key
    _configure_logging(verbose=args.verbose)

    if args.run_all:
        return _run_all(args)
    _run_single(args.signal, args.company, args)
    return 0


def _run_all(args: argparse.Namespace) -> int:
    """Iterate the canonical pairs, collect results, print a summary table."""
    results: list[_RunResult] = []
    for idx, (signal_type, company_id) in enumerate(_ALL_PAIRS, start=1):
        print()
        print(_BANNER)
        print(f" BATCH {idx}/{len(_ALL_PAIRS)}  {signal_type} @ {company_id}")
        print(_BANNER)
        result = _run_single(signal_type, company_id, args)
        results.append(result)

    print()
    print(_BANNER)
    print(" BATCH SUMMARY")
    print(_BANNER)
    print(f"{'signal':<18} {'company':<8} {'tier':<10} {'gate':<10} {'outcome'}")
    print("─" * 60)
    drafted = 0
    for r in results:
        gate_str = f"{r.candidates_passed}/{r.candidates_total}" if r.candidates_total else "—"
        if r.outcome == "draft sent":
            drafted += 1
        print(
            f"{r.signal_type:<18} {r.company_id:<8} {r.tier:<10} {gate_str:<10} {r.outcome}"
        )
    print()
    print(f"{drafted}/{len(results)} signals produced drafts.")
    audits = [str(r.audit_path) for r in results if r.audit_path]
    print(f"Audit files written: {len(audits)}")
    for a in audits:
        print(f"  {a}")
    return 0


def _run_single(
    signal_type: str,
    company_id: str,
    args: argparse.Namespace,
) -> _RunResult:
    """Run one (signal, company) pair end-to-end. Returns a summary record."""
    started_at = datetime.now(UTC)
    run_id = started_at.strftime("%Y%m%dT%H%M%SZ")

    # --- Stage 1 ---------------------------------------------------------
    print(f"[1/5] Detecting signal: {signal_type} @ {company_id}...")
    signal = detector.detect(signal_type, company_id)
    print(
        f"      {signal.signal_id} ({signal.signal_source}, "
        f"fired {signal.signal_date.isoformat()})"
    )

    # --- Stage 2 ---------------------------------------------------------
    print("[2/5] Enriching (mocked Clay waterfall)...")
    company, contact = enricher.enrich(signal)
    print(
        f"      company={company.company_name} icp_total={company.icp_total} | "
        f"contact={contact.first_name} {contact.last_name} ({contact.title})"
    )

    audit = auditor.new_entry(
        run_id=run_id,
        started_at=started_at,
        signal=signal,
        company=company,
        contact=contact,
    )

    # --- Stage 3 ---------------------------------------------------------
    print("[3/5] Scoring...")
    score = scorer.compute(signal, company, contact)
    _record_score(audit, score)
    print(f"      base_weight       {score.base_weight:.3f}  ({signal.signal_type} signal)")
    print(
        f"      recency_decay     {score.recency_decay:.3f}  "
        f"({score.days_since_signal} days, half-life 30)"
    )
    print(
        f"      buyer_proximity   {score.buyer_proximity:.3f}  ({contact.title}, "
        f"engagement={contact.engagement_score})"
    )
    print(f"      signal_score      {score.signal_score:.3f}")

    # --- Stage 4 ---------------------------------------------------------
    tier = router.assign(score, company)
    channel = router.channel_for(tier)
    audit.tier = tier
    print(f"[4/5] Routing: {tier}")
    print(f"      # STUB: {channel}")

    if tier in {"Discovery", "Park"}:
        print(
            f"      tier={tier} → no draft generated. "
            "Production would fire Find Contacts at Company or park the lead."
        )
        audit_path = _finalise_and_write(audit)
        return _RunResult(
            signal_type=signal_type,
            company_id=company_id,
            tier=tier,
            candidates_total=0,
            candidates_passed=0,
            draft_subject="",
            sdr_decision="",
            audit_path=audit_path,
            outcome=tier.lower(),
        )

    # --- Stage 5 ---------------------------------------------------------
    print("[5/5] Drafting via Claude API...")
    print("      Personalisation Agent: generating 3 hook candidates...")
    candidates = personaliser.generate_hooks(signal, company, contact)
    for idx, cand in enumerate(candidates, start=1):
        print(f"        [{idx}] ({cand.word_count}w) {_truncate(cand.text, 90)}")

    print("      Strong-Hook Gate: evaluating candidates...")
    verdicts = gate.evaluate(candidates, signal, contact)
    chosen = gate.pick_strongest(verdicts)
    _record_hooks(audit, candidates, verdicts)
    for idx, verdict in enumerate(verdicts, start=1):
        marker = "✓" if verdict.passed else "✗"
        print(f"        [{idx}] {marker} {verdict.reason}")

    passed_count = sum(1 for v in verdicts if v.passed)

    if chosen is None:
        print("      All candidates failed gate. Routing to manual review queue.")
        print("      # STUB: would create a ticket in #signal-manual-review")
        audit.gate_decision = {"passed": False, "reason": "no candidate cleared the gate"}
        audit_path = _finalise_and_write(audit)
        return _RunResult(
            signal_type=signal_type,
            company_id=company_id,
            tier=tier,
            candidates_total=len(candidates),
            candidates_passed=passed_count,
            draft_subject="",
            sdr_decision="",
            audit_path=audit_path,
            outcome="manual review",
        )

    selected_idx = verdicts.index(chosen) + 1
    print(f"      Selected hook: candidate {selected_idx}")
    print("      Draft Assembly Agent: merging template + hook...")
    draft = assemble(
        signal=signal,
        company=company,
        contact=contact,
        selected_hook=chosen.candidate,
        sdr_signature=args.sdr_signature,
        polish=not args.no_polish,
    )
    audit.selected_hook = chosen.candidate.text
    audit.gate_decision = {"passed": True, "reason": chosen.reason}
    audit.draft = {
        "subject": draft.subject,
        "body": draft.body,
        "template_name": draft.template_name,
    }

    # --- HITL ------------------------------------------------------------
    if args.non_interactive:
        _print_draft_noninteractive(draft)
        decision, final_body = "send", draft.body
        print("(non-interactive: treating as send)")
    else:
        from signal_engine.hitl import review

        decision, final_body = review(draft)

    audit.sdr_decision = decision
    audit.sdr_edited_body = final_body

    campaign = SMARTLEAD_CAMPAIGNS.get(signal_type, "(unknown)")
    if decision == "send":
        print(
            f"[STUB] Would have triggered Smartlead campaign {campaign!r} "
            "with personalised_first_email custom variable populated."
        )
    elif decision == "edit":
        print(
            f"[STUB] Would have sent EDITED body via Smartlead campaign {campaign!r}."
        )
    else:
        print("[STUB] Skipped. Production would decay the signal and capture a reason.")

    audit_path = _finalise_and_write(audit)
    return _RunResult(
        signal_type=signal_type,
        company_id=company_id,
        tier=tier,
        candidates_total=len(candidates),
        candidates_passed=passed_count,
        draft_subject=draft.subject,
        sdr_decision=decision,
        audit_path=audit_path,
        outcome="draft sent" if decision in {"send", "edit"} else "skipped",
    )


def _record_score(audit: AuditEntry, score: ScoreBreakdown) -> None:
    """Copy ScoreBreakdown fields into the audit entry."""
    audit.score = {
        "base_weight": score.base_weight,
        "recency_decay": score.recency_decay,
        "buyer_proximity": score.buyer_proximity,
        "signal_score": score.signal_score,
        "days_since_signal": score.days_since_signal,
    }


def _record_hooks(
    audit: AuditEntry,
    candidates: list[HookCandidate],
    verdicts: list[GateVerdict],
) -> None:
    """Capture every hook candidate with its gate verdict for audit."""
    audit.hook_candidates = [
        {
            "text": cand.text,
            "word_count": cand.word_count,
            "passed": v.passed,
            "reason": v.reason,
            "specificity": v.specificity,
            "buyer_context": v.buyer_context,
            "voice_ok": v.voice_ok,
            "length_ok": v.length_ok,
            "timeliness": v.timeliness,
        }
        for cand, v in zip(candidates, verdicts, strict=True)
    ]


def _finalise_and_write(audit: AuditEntry) -> Path:
    """Stamp completed_at, write the audit JSON, print the path, return it."""
    audit.completed_at = datetime.now(UTC)
    path = auditor.write(audit)
    print(f"[AUDIT] {path}")
    return path


def _print_draft_noninteractive(draft: Draft) -> None:
    """Render the draft to stdout without prompting (smoke tests / CI)."""
    print()
    print(_BANNER)
    print(" DRAFT (Claude-generated)")
    print(_BANNER)
    print(f"Subject: {draft.subject}")
    print()
    print(draft.body)
    print(_BANNER)


def _truncate(text: str, limit: int) -> str:
    """Shorten a hook candidate for the candidate-list preview."""
    cleaned = text.replace("\n", " ").strip()
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"


def _configure_logging(*, verbose: bool) -> None:
    """Wire stdlib logging to stderr at INFO if --verbose, else WARN."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


if __name__ == "__main__":  # pragma: no cover — module-entry shim
    sys.exit(main())
