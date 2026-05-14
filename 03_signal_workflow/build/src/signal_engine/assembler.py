"""Draft Assembly Agent.

Merges the chosen hook with the per-signal template and returns a
Draft ready for the SDR HITL terminal. The Claude API call here is a
final voice/cleanup pass — the structural merge is deterministic.

Template file layout:

    Subject: <subject line>

    <body with {prospect_first_name}, {ai_hook}, {sdr_signature} placeholders>

The first line is parsed as the subject; everything below the first
blank line is the body that gets `str.format()`-substituted.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from anthropic import Anthropic

from signal_engine.constants import (
    ANTHROPIC_MAX_TOKENS,
    ANTHROPIC_MODEL,
    DEFAULT_SDR_SIGNATURE,
    GATE_TEMPERATURE,
)
from signal_engine.models import Company, Contact, Draft, HookCandidate, Signal

logger = logging.getLogger(__name__)

TEMPLATES_ROOT = Path(__file__).resolve().parent / "templates"

_POLISH_SYSTEM_PROMPT = """You are a copy editor for Mento, a coaching company. You receive a finished cold email draft and return it with light edits only:
- British English consistency
- No exclamation marks, no emojis
- Remove any salesy hedging or filler (kept under 70 words ideally, never over 80)
- Keep the subject line exactly as given

Do not change the structure, do not change named companies or numbers, and do not add new claims. Return the email exactly in this shape:

Subject: <subject line>

<body>

Nothing else."""


def assemble(
    *,
    signal: Signal,
    company: Company,
    contact: Contact,
    selected_hook: HookCandidate,
    template_name: str | None = None,
    sdr_signature: str = DEFAULT_SDR_SIGNATURE,
    client: Anthropic | None = None,
    polish: bool = True,
) -> Draft:
    """Return a Draft for one (signal, company, contact, hook) tuple."""
    name = template_name or signal.signal_type
    subject, body_template = _load_template(name)
    body = body_template.format(
        prospect_first_name=contact.first_name,
        ai_hook=selected_hook.text,
        sdr_signature=sdr_signature,
    )

    if polish:
        body = _polish(subject=subject, body=body, client=client)

    logger.info("assembler: built draft for %s / %s", company.company_name, contact.first_name)
    return Draft(
        signal_id=signal.signal_id,
        company_id=company.company_id,
        contact_id=contact.contact_id,
        subject=subject,
        body=body,
        selected_hook=selected_hook.text,
        template_name=name,
    )


def _load_template(name: str) -> tuple[str, str]:
    """Return (subject, body_template) for a named template."""
    path = TEMPLATES_ROOT / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"No template at {path}")
    raw = path.read_text()
    lines = raw.splitlines()
    if not lines or not lines[0].lower().startswith("subject:"):
        raise ValueError(f"Template {name} missing 'Subject:' header")
    subject = lines[0].split(":", 1)[1].strip()
    # Skip the blank line after the subject if present.
    body_start = 1
    while body_start < len(lines) and lines[body_start].strip() == "":
        body_start += 1
    body = "\n".join(lines[body_start:])
    return subject, body


def _polish(*, subject: str, body: str, client: Anthropic | None) -> str:
    """Run the assembled draft through a Claude voice pass.

    Strictly editorial — voice clean-up, no structural rewrites. If the
    model returns something we can't parse, fall back to the unpolished
    body so the demo never produces a broken draft.
    """
    api_client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    raw_draft = f"Subject: {subject}\n\n{body}"
    response = api_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        temperature=GATE_TEMPERATURE,
        system=_POLISH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_draft}],
    )
    polished = "".join(block.text for block in response.content if block.type == "text").strip()
    if "\n\n" not in polished or not polished.lower().startswith("subject:"):
        logger.warning("assembler: polish output unparseable, returning unpolished body")
        return body
    _subject_line, polished_body = polished.split("\n\n", 1)
    return polished_body
