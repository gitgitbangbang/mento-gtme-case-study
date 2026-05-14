"""Human-in-the-Loop terminal prompt.

The CLI analogue of the Slack `[Send via Smartlead] [Edit] [Skip]`
buttons described in 03_workflow_architecture_text.md. Prints the
assembled draft, then asks the SDR `[s]end / [e]dit / [k]ip > `. On
edit, opens the body in $EDITOR (default vim).

This module is allowed to print directly — it's a CLI surface.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Final

from signal_engine.models import Draft, SDRDecision

_BANNER_WIDTH: Final[int] = 60
_PROMPT: Final[str] = "[s]end / [e]dit / [k]ip > "


def review(draft: Draft) -> tuple[SDRDecision, str]:
    """Print the draft, prompt the SDR, return (decision, final_body).

    `final_body` reflects any edit the SDR makes. If decision is "skip"
    or "send" without edits, `final_body` is the original draft body.
    """
    _print_draft(draft)
    decision = _prompt_decision()

    final_body = draft.body
    if decision == "edit":
        final_body = _open_editor(draft.body)
        print()
        print("Edited draft:")
        print("─" * _BANNER_WIDTH)
        print(final_body)
        print("─" * _BANNER_WIDTH)
        print()

    return decision, final_body


def _print_draft(draft: Draft) -> None:
    """Format the draft for terminal reading."""
    print()
    print("─" * _BANNER_WIDTH)
    print(" DRAFT (Claude-generated)")
    print("─" * _BANNER_WIDTH)
    print(f"Subject: {draft.subject}")
    print()
    print(draft.body)
    print("─" * _BANNER_WIDTH)
    print()


def _prompt_decision() -> SDRDecision:
    """Loop until the SDR picks one of s/e/k."""
    while True:
        try:
            raw = input(_PROMPT).strip().lower()
        except EOFError:
            print("\n(no input; treating as skip)")
            return "skip"
        if raw in {"s", "send"}:
            return "send"
        if raw in {"e", "edit"}:
            return "edit"
        if raw in {"k", "skip"}:
            return "skip"
        print("Please enter s, e, or k.")


def _open_editor(initial_body: str) -> str:
    """Pop the body into $EDITOR. Returns the edited contents."""
    editor = os.environ.get("EDITOR", "vim")
    with tempfile.NamedTemporaryFile(
        mode="w+",
        suffix=".txt",
        prefix="mento-draft-",
        delete=False,
        encoding="utf-8",
    ) as fh:
        fh.write(initial_body)
        path = fh.name
    try:
        subprocess.run([editor, path], check=False)
        with open(path, encoding="utf-8") as fh:
            return fh.read().rstrip("\n") + "\n"
    finally:
        try:
            os.unlink(path)
        except OSError:  # pragma: no cover — cleanup best-effort
            print(f"(could not delete temp file {path})", file=sys.stderr)
