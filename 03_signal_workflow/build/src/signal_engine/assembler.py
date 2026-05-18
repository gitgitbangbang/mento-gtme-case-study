"""Draft Assembly Agent.

Merges the chosen hook with the per-signal template and returns a
Draft ready for the SDR HITL terminal. The Claude API call here is a
final voice/cleanup pass — the structural merge is deterministic.

Template file layout:

    Subject: <subject line>

    <body with {prospect_first_name}, {ai_hook}, {sdr_signature} placeholders>

The first line is parsed as the subject; everything below the first
blank line is the body that gets `str.format()`-substituted.

The polish step is wrapped in a deterministic word-count check: drafts
that come back over MAX_EMAIL_WORDS get one retry with explicit
feedback before we ship the best attempt. The Mento brand-voice rule
("Under 70 words total") is enforced here rather than left to the
model's discretion.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from anthropic import Anthropic

from signal_engine.constants import (
    ANTHROPIC_MAX_TOKENS,
    ANTHROPIC_MODEL,
    DEFAULT_SDR_SIGNATURE,
    GATE_TEMPERATURE,
    MAX_EMAIL_WORDS,
    MAX_POLISH_RETRIES,
    POLISH_TARGET_WORDS,
)
from signal_engine.models import Company, Contact, Draft, HookCandidate, Signal

logger = logging.getLogger(__name__)

TEMPLATES_ROOT = Path(__file__).resolve().parent / "templates"

_POLISH_SYSTEM_PROMPT = """You are a copy editor for Mento, a coaching company. You receive a finished cold email draft and return it trimmed to fit the brand-voice rules.

PRIMARY DIRECTIVE 1 (WORD COUNT):
The body (everything after the Subject line) MUST be {max_words} words or fewer. Target {target_words} words to leave a safety margin. Count carefully. If the input is over budget, trim verbosity, redundancy, and any "filler" sentences while preserving every named fact (companies, dollar amounts, headcount figures, exact titles, prospect first name).

PRIMARY DIRECTIVE 2 (NO DASHES):
Do not use em dashes ('—') or en dashes ('–') anywhere in the body. Use periods, commas, or semicolons instead. Hyphens ('-') inside compound words like "first-investment" or "high-growth" or date ranges like "3-9" are acceptable; those are not dashes. If the input contains em or en dashes, replace them with appropriate punctuation while preserving the sentence meaning.

Secondary rules:
- British English consistency
- No exclamation marks, no emojis
- No salesy hedging
- Keep the subject line exactly as given
- Do not change the structure (Hi <Name>, / hook paragraph / insight paragraph / soft CTA / signoff)
- Do not change named companies or numbers
- Do not add new claims

Return the email exactly in this shape:

Subject: <subject line>

<body>

Nothing else. No preamble, no commentary, no word count."""


_POLISH_RETRY_TEMPLATE = """{system_base}

NOTE - RETRY: Your previous attempt was {previous_words} words. The hard cap is {max_words}, target {target_words}. You must trim at least {excess} more words while preserving all named facts. Cut redundancy and adverbs first."""


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
    else:
        # Polish does its own deterministic dash strip inside the retry
        # loop. With --no-polish, strip here so the brand-voice rule
        # ("no em or en dashes") still holds.
        body = _strip_dashes(body)

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
    """Run the assembled draft through one or more Claude voice passes.

    On the first attempt, the model is told the {max_words} cap as a
    primary directive. If the result still exceeds the cap, retries up
    to MAX_POLISH_RETRIES more times with explicit "your previous
    attempt was N words, trim by N-cap" feedback. If all attempts come
    back over budget, the best (shortest) attempt is returned and a
    warning is logged so the over-budget run surfaces in the audit.

    Strictly editorial — voice clean-up, no structural rewrites. If
    the model returns something we can't parse, fall back to the
    unpolished body so the demo never produces a broken draft.
    """
    api_client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Track every parseable polished attempt so we can ship the shortest if
    # none come in under the cap. Input body is the ultimate fallback only
    # if every attempt is unparseable.
    over_cap_attempts: list[tuple[int, str]] = []
    previous_words = _word_count(body)

    base_system = _POLISH_SYSTEM_PROMPT.format(
        max_words=MAX_EMAIL_WORDS,
        target_words=POLISH_TARGET_WORDS,
    )

    for attempt in range(MAX_POLISH_RETRIES + 1):
        if attempt == 0:
            system_prompt = base_system
        else:
            system_prompt = _POLISH_RETRY_TEMPLATE.format(
                system_base=base_system,
                previous_words=previous_words,
                max_words=MAX_EMAIL_WORDS,
                target_words=POLISH_TARGET_WORDS,
                excess=previous_words - POLISH_TARGET_WORDS,
            )

        raw_draft = f"Subject: {subject}\n\n{body}"
        response = api_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            temperature=GATE_TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": raw_draft}],
        )
        raw_polished = (
            "".join(block.text for block in response.content if block.type == "text").strip()
        )
        if "\n\n" not in raw_polished or not raw_polished.lower().startswith("subject:"):
            logger.warning(
                "assembler: polish attempt %d output unparseable, retrying",
                attempt + 1,
            )
            continue

        _subject_line, polished_body = raw_polished.split("\n\n", 1)
        # Deterministic dash strip — non-negotiable brand-voice rule. The
        # polish prompt is also told to avoid em/en dashes but this is
        # the belt-and-braces guarantee regardless of model behaviour.
        polished_body = _strip_dashes(polished_body)
        polished_word_count = _word_count(polished_body)
        logger.info(
            "assembler: polish attempt %d produced %d words (cap %d, target %d)",
            attempt + 1,
            polished_word_count,
            MAX_EMAIL_WORDS,
            POLISH_TARGET_WORDS,
        )

        if polished_word_count <= MAX_EMAIL_WORDS:
            return polished_body

        over_cap_attempts.append((polished_word_count, polished_body))
        previous_words = polished_word_count

    # Every polished attempt was over cap (or unparseable). Ship the
    # shortest over-cap attempt and log loudly so it lands in the audit.
    if over_cap_attempts:
        shortest_words, shortest_body = min(over_cap_attempts, key=lambda t: t[0])
        logger.warning(
            "assembler: final draft is %d words (cap %d, excess %d). All %d polish "
            "attempts exceeded the brand-voice cap; shipping shortest attempt.",
            shortest_words,
            MAX_EMAIL_WORDS,
            shortest_words - MAX_EMAIL_WORDS,
            MAX_POLISH_RETRIES + 1,
        )
        return shortest_body

    logger.warning(
        "assembler: all %d polish attempts unparseable, returning unpolished body",
        MAX_POLISH_RETRIES + 1,
    )
    return body


def _word_count(text: str) -> int:
    """Whitespace-tokenised word count for the brand-voice 70-word cap.

    Matches the personaliser's `_count_words` so hook + body word
    counts are computed the same way.
    """
    return len(text.split())


_EM_DASH_RUN = re.compile(r"\s*—+\s*")
_EN_DASH_NUMERIC = re.compile(r"(\d)–(\d)")
_EN_DASH_GENERIC = re.compile(r"\s*–+\s*")


def _strip_dashes(text: str) -> str:
    """Remove every em dash and en dash from the body, deterministically.

    Replacements:
    - em dash (U+2014, with any surrounding whitespace) -> ". "
    - en dash inside a numeric range like "2–6" -> hyphen ("2-6")
    - any other en dash -> ". "

    Hyphens (U+002D) inside compound words ("first-investment",
    "high-growth") are deliberately left untouched. Those are
    orthographic hyphens, not dashes.
    """
    text = _EN_DASH_NUMERIC.sub(r"\1-\2", text)
    text = _EM_DASH_RUN.sub(". ", text)
    text = _EN_DASH_GENERIC.sub(". ", text)
    # Collapse any artefacts like ". . " or doubled periods left by the
    # substitutions above.
    text = re.sub(r"\s*\.\s+\.\s*", ". ", text)
    text = re.sub(r" {2,}", " ", text)
    return text
