"""Signal-engine CLI entry point.

Usage:

    uv run python -m signal_engine.run --signal funding --company linear

Walks one signal end to end through detect -> enrich -> score -> route
-> personaliser -> gate -> assembler -> HITL terminal. (Audit logging
is wired in by Step 9.)

Direct prints are intentional here — this is the user-facing surface.
Every other module logs through `logging`.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Final

from dotenv import load_dotenv

from signal_engine import detector, enricher, gate, personaliser, router, scorer
from signal_engine.assembler import assemble
from signal_engine.constants import SMARTLEAD_CAMPAIGNS
from signal_engine.models import Draft

_SIGNAL_CHOICES: Final[list[str]] = ["funding", "exec_hire", "ld_posting", "headcount_growth"]
_COMPANY_CHOICES: Final[list[str]] = ["linear", "vanta", "ramp", "retool"]
_BANNER: Final[str] = "─" * 60


def main(argv: list[str] | None = None) -> int:
    """Run one signal end to end. Returns shell exit code."""
    parser = argparse.ArgumentParser(
        prog="signal_engine",
        description="Mento signal engine — runs one buying signal end to end.",
    )
    parser.add_argument("--signal", required=True, choices=_SIGNAL_CHOICES)
    parser.add_argument("--company", required=True, choices=_COMPANY_CHOICES)
    parser.add_argument(
        "--no-polish",
        action="store_true",
        help="Skip the assembler's final Claude voice pass (saves one API call).",
    )
    parser.add_argument(
        "--sdr-signature",
        default="Alex",
        help="Name used in the signoff line (default: Alex).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip the HITL prompt; auto-treat as 'send'. For smoke tests.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Echo INFO-level logs from each pipeline stage to stderr.",
    )
    args = parser.parse_args(argv)

    load_dotenv()
    _configure_logging(verbose=args.verbose)

    # --- Stage 1 ---------------------------------------------------------
    print(f"[1/5] Detecting signal: {args.signal} @ {args.company}...")
    signal = detector.detect(args.signal, args.company)
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

    # --- Stage 3 ---------------------------------------------------------
    print("[3/5] Scoring...")
    score = scorer.compute(signal, company, contact)
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
    print(f"[4/5] Routing: {tier}")
    print(f"      # STUB: {channel}")

    if tier in {"Discovery", "Park"}:
        print(
            f"      tier={tier} → no draft generated. "
            "Production would fire Find Contacts at Company or park the lead."
        )
        return 0

    # --- Stage 5 ---------------------------------------------------------
    print("[5/5] Drafting via Claude API...")
    print("      Personalisation Agent: generating 3 hook candidates...")
    candidates = personaliser.generate_hooks(signal, company, contact)
    for idx, cand in enumerate(candidates, start=1):
        print(f"        [{idx}] ({cand.word_count}w) {_truncate(cand.text, 90)}")

    print("      Strong-Hook Gate: evaluating candidates...")
    verdicts = gate.evaluate(candidates, signal, contact)
    chosen = gate.pick_strongest(verdicts)
    for idx, verdict in enumerate(verdicts, start=1):
        marker = "✓" if verdict.passed else "✗"
        print(f"        [{idx}] {marker} {verdict.reason}")

    if chosen is None:
        print("      All candidates failed gate. Routing to manual review queue.")
        print("      # STUB: would create a ticket in #signal-manual-review")
        return 0

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

    # --- HITL ------------------------------------------------------------
    if args.non_interactive:
        _print_draft_noninteractive(draft)
        decision, final_body = "send", draft.body
        print("(non-interactive: treating as send)")
    else:
        from signal_engine.hitl import review

        decision, final_body = review(draft)

    campaign = SMARTLEAD_CAMPAIGNS.get(args.signal, "(unknown)")
    if decision == "send":
        print(
            f"[STUB] Would have triggered Smartlead campaign {campaign!r} "
            "with personalised_first_email custom variable populated."
        )
    elif decision == "edit":
        print(
            f"[STUB] Would have sent EDITED body via Smartlead campaign {campaign!r}."
        )
        _ = final_body  # consumed by Step 9 audit logging
    else:
        print("[STUB] Skipped. Production would decay the signal and capture a reason.")
    return 0


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
