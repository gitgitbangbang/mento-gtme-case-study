"""Pretty-print one audit JSON for terminal reading.

Usage:

    uv run python -m signal_engine.inspect_audit audit/<file>.json
    uv run python -m signal_engine.inspect_audit --latest

The audit log is the durable trace of one signal-engine run — signal
payload, enrichment, score breakdown, every hook candidate with its
gate verdict, the selected hook, the final draft, and the SDR
decision. The JSON file is fine for machines; this module renders it
for humans.

Direct prints are intentional — this is a CLI surface.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger(__name__)

AUDIT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent / "audit"
_RULE: Final[str] = "─" * 64
_SECTION: Final[str] = "━" * 64


def main(argv: list[str] | None = None) -> int:
    """Pretty-print one audit JSON. Returns a shell exit code."""
    parser = argparse.ArgumentParser(
        prog="signal_engine.inspect_audit",
        description="Pretty-print one audit JSON written by run.py.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Path to the audit JSON file.",
    )
    group.add_argument(
        "--latest",
        action="store_true",
        help="Inspect the most recently written audit/ file.",
    )
    args = parser.parse_args(argv)

    target = _resolve_target(args)
    if target is None:
        print("No audit files found in audit/.", file=sys.stderr)
        return 1
    if not target.exists():
        print(f"Audit file not found: {target}", file=sys.stderr)
        return 1

    data = json.loads(target.read_text())
    _render(data, target)
    return 0


def _resolve_target(args: argparse.Namespace) -> Path | None:
    """Resolve the audit file path from --latest or the positional arg."""
    if args.latest:
        candidates = sorted(AUDIT_ROOT.glob("*.json"))
        return candidates[-1] if candidates else None
    return args.path  # type: ignore[no-any-return]


def _render(data: dict[str, Any], path: Path) -> None:
    """Print one audit entry as a readable terminal report."""
    _header(f"AUDIT  {path.name}")
    print(f"run_id:        {data.get('run_id', '?')}")
    print(f"started_at:    {data.get('started_at', '?')}")
    print(f"completed_at:  {data.get('completed_at', '?')}")

    _section("SIGNAL")
    sig = data.get("signal", {})
    print(f"  id:      {sig.get('signal_id', '?')}")
    print(f"  type:    {sig.get('signal_type', '?')}")
    print(f"  date:    {sig.get('signal_date', '?')}")
    print(f"  source:  {sig.get('signal_source', '?')}")
    payload = sig.get("signal_payload", {})
    if payload:
        print("  payload:")
        for k, v in payload.items():
            print(f"    {k}: {_short(v)}")

    _section("COMPANY / CONTACT")
    co = data.get("company", {})
    ct = data.get("contact", {})
    print(f"  company:        {co.get('company_name', '?')} ({co.get('domain', '?')})")
    print(f"  headcount:      {co.get('headcount', '?')}")
    print(f"  funding stage:  {co.get('funding_stage', '?')}")
    print(f"  icp_total:      {co.get('icp_total', '?')}")
    print(
        f"  contact:        {ct.get('first_name', '?')} {ct.get('last_name', '')} "
        f"({ct.get('title', '?')})"
    )
    print(f"  buyer_role:     {ct.get('buyer_role', '?')}")
    print(f"  engagement:     {ct.get('engagement_score', '?')}")

    _section("SCORE & TIER")
    score = data.get("score", {})
    if score:
        print(f"  base_weight       {score.get('base_weight', 0):.3f}")
        print(
            f"  recency_decay     {score.get('recency_decay', 0):.3f}  "
            f"({score.get('days_since_signal', '?')} days, half-life 30)"
        )
        print(f"  buyer_proximity   {score.get('buyer_proximity', 0):.3f}")
        print(f"  signal_score      {score.get('signal_score', 0):.3f}")
    else:
        print("  (no score recorded — Park exit?)")
    print(f"  tier:           {data.get('tier', '?')}")

    candidates = data.get("hook_candidates", [])
    if candidates:
        _section(f"HOOK CANDIDATES ({len(candidates)})")
        for i, cand in enumerate(candidates, start=1):
            marker = "✓ pass" if cand.get("passed") else "✗ fail"
            print(f"  [{i}] {marker} ({cand.get('word_count', '?')}w)")
            print(f"      reason: {cand.get('reason', '')}")
            print(f"      text:   {_indent(cand.get('text', ''), 14)}")
    else:
        print()
        print("(no hook candidates — short-circuit before agentic layer)")

    selected = data.get("selected_hook", "")
    if selected:
        _section("SELECTED HOOK")
        print(f"  {selected}")

    draft = data.get("draft", {})
    if draft:
        _section("DRAFT")
        print(f"  subject:        {draft.get('subject', '?')}")
        print(f"  template_name:  {draft.get('template_name', '?')}")
        print()
        print(_indent(draft.get("body", ""), 2))

    _section("SDR DECISION")
    decision = data.get("sdr_decision", "")
    if decision:
        print(f"  decision:  {decision}")
        if decision == "edit" and data.get("sdr_edited_body"):
            print()
            print("  edited body:")
            print(_indent(data["sdr_edited_body"], 4))
    else:
        print("  (no HITL decision recorded — early exit)")

    print()
    print(_RULE)


def _header(text: str) -> None:
    print(_SECTION)
    print(f"  {text}")
    print(_SECTION)


def _section(title: str) -> None:
    print()
    print(f"── {title} ".ljust(64, "─"))


def _short(value: Any, limit: int = 80) -> str:
    """Single-line representation of a payload value, truncated to `limit`."""
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


if __name__ == "__main__":  # pragma: no cover — module-entry shim
    sys.exit(main())
