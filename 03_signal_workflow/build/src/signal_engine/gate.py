"""Strong-Hook Gate.

Evaluates each hook candidate against the five criteria from
03_outreach_drafts.md:

| Criterion    | Pass                                                    |
|--------------|---------------------------------------------------------|
| Specificity  | Names investor / dollar / prior company / title / count |
| Timeliness   | Trigger within last SIGNAL_FRESHNESS_DAYS               |
| Buyer context| References prospect role or activity                    |
| Length       | Under HOOK_MAX_WORDS                                    |
| Voice        | Operator tone, no hedging, no banned phrases            |

Length, banned-phrase, and timeliness checks are deterministic and
inline. Specificity, buyer context, and voice are evaluated by a
second Claude call (temperature 0) returning a strict JSON verdict.

If all candidates fail, the caller routes the signal to manual review
and no draft reaches the SDR.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date
from typing import Any

from anthropic import Anthropic

from signal_engine.constants import (
    ANTHROPIC_MAX_TOKENS,
    ANTHROPIC_MODEL,
    BANNED_PHRASES,
    GATE_TEMPERATURE,
    HOOK_MAX_WORDS,
    SIGNAL_FRESHNESS_DAYS,
)
from signal_engine.models import Contact, GateVerdict, HookCandidate, Signal

logger = logging.getLogger(__name__)

_GATE_SYSTEM_PROMPT = """You audit cold-email opening hooks written by an SDR at Mento (coaching for senior People execs at B2B SaaS companies).

For the hook you receive, judge three criteria:
- specificity: does it reference a named investor, dollar amount, prior company, exact job title, or specific headcount number?
- buyer_context: does it relate to the prospect's role or recent activity, not a generic mention of the company?
- voice_ok: does it sound like one operator writing to another — direct, no salesy hedging, no jargon?

Return strict JSON with exactly these keys: {"specificity": bool, "buyer_context": bool, "voice_ok": bool, "reason": str}. The reason is one short sentence. No prose, no markdown."""


_GATE_USER_PROMPT_TEMPLATE = """Hook to audit:
\"\"\"
{hook}
\"\"\"

Prospect: {prospect_first_name}, {prospect_title}
Signal context: {signal_type} on {signal_date}
Signal payload: {signal_payload_json}

Return JSON only."""


def evaluate(
    candidates: list[HookCandidate],
    signal: Signal,
    contact: Contact,
    *,
    client: Anthropic | None = None,
    reference_date: date | None = None,
) -> list[GateVerdict]:
    """Audit every candidate. Return one GateVerdict per candidate, in order."""
    today = reference_date or date.today()
    timely = (today - signal.signal_date).days <= SIGNAL_FRESHNESS_DAYS

    api_client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    verdicts: list[GateVerdict] = []
    for idx, candidate in enumerate(candidates, start=1):
        verdict = _evaluate_one(
            candidate=candidate,
            signal=signal,
            contact=contact,
            timely=timely,
            client=api_client,
        )
        logger.info(
            "gate: candidate %d/%d passed=%s reason=%s",
            idx,
            len(candidates),
            verdict.passed,
            verdict.reason,
        )
        verdicts.append(verdict)
    return verdicts


def pick_strongest(verdicts: list[GateVerdict]) -> GateVerdict | None:
    """Return the first passing verdict, or None if all candidates failed."""
    for v in verdicts:
        if v.passed:
            return v
    return None


def _evaluate_one(
    *,
    candidate: HookCandidate,
    signal: Signal,
    contact: Contact,
    timely: bool,
    client: Anthropic,
) -> GateVerdict:
    """Run the five-criterion gate for one hook."""
    length_ok = candidate.word_count <= HOOK_MAX_WORDS
    banned_hit = _contains_banned_phrase(candidate.text)

    llm = _llm_verdict(candidate=candidate, signal=signal, contact=contact, client=client)
    specificity = llm["specificity"]
    buyer_context = llm["buyer_context"]
    voice_ok = bool(llm["voice_ok"]) and not banned_hit
    reason_parts: list[str] = []
    if not length_ok:
        reason_parts.append(f"length {candidate.word_count}>{HOOK_MAX_WORDS}")
    if banned_hit:
        reason_parts.append("banned phrase")
    if not specificity:
        reason_parts.append("not specific")
    if not buyer_context:
        reason_parts.append("no buyer context")
    if not voice_ok:
        reason_parts.append("voice off")
    if not timely:
        reason_parts.append(f"stale (>{SIGNAL_FRESHNESS_DAYS}d)")

    passed = length_ok and timely and specificity and buyer_context and voice_ok
    reason = ", ".join(reason_parts) if reason_parts else "pass: " + llm["reason"]

    return GateVerdict(
        candidate=candidate,
        passed=passed,
        specificity=specificity,
        timeliness=timely,
        buyer_context=buyer_context,
        length_ok=length_ok,
        voice_ok=voice_ok,
        reason=reason,
    )


def _llm_verdict(
    *,
    candidate: HookCandidate,
    signal: Signal,
    contact: Contact,
    client: Anthropic,
) -> dict[str, Any]:
    """Ask Claude to judge specificity / buyer_context / voice for one hook."""
    user_prompt = _GATE_USER_PROMPT_TEMPLATE.format(
        hook=candidate.text,
        prospect_first_name=contact.first_name,
        prospect_title=contact.title,
        signal_type=signal.signal_type,
        signal_date=signal.signal_date.isoformat(),
        signal_payload_json=json.dumps(signal.signal_payload),
    )
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        temperature=GATE_TEMPERATURE,
        system=_GATE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    return _parse_verdict_json(raw)


def _parse_verdict_json(raw: str) -> dict[str, Any]:
    """Tolerant JSON parser for the gate verdict.

    Some models wrap JSON in markdown fences even when told not to;
    strip that before parsing.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise RuntimeError(f"Gate could not parse verdict JSON: {raw!r}") from None
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Gate verdict was not a JSON object: {raw!r}")
    parsed.setdefault("specificity", False)
    parsed.setdefault("buyer_context", False)
    parsed.setdefault("voice_ok", False)
    parsed.setdefault("reason", "")
    return parsed


def _contains_banned_phrase(text: str) -> bool:
    """True if the candidate uses any phrase on the brand-voice blacklist."""
    lowered = text.lower()
    return any(phrase in lowered for phrase in BANNED_PHRASES)
