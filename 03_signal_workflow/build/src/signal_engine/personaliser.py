"""Personalisation Agent — Stage 4 hook generation via Claude API.

Generates three personalisation hook candidates per signal event. Uses
the Claude API directly (the production version runs the same prompt
through Clay's Use AI column; the wire shape is identical).

The agent prompt below is lifted verbatim from 03_outreach_drafts.md
Section "Agent Prompt" so the demo and the case-study spec stay one
source of truth.
"""

from __future__ import annotations

import json
import logging
import os
import re

from anthropic import Anthropic

from signal_engine.constants import (
    ANTHROPIC_MAX_TOKENS,
    ANTHROPIC_MODEL,
    HOOK_CANDIDATES_PER_RUN,
    HOOK_GEN_TEMPERATURE,
)
from signal_engine.models import Company, Contact, HookCandidate, Signal

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are writing opening lines for cold emails sent by an SDR at Mento, a coaching company selling to senior People execs (CHRO / CPO / VP People) at venture-backed B2B SaaS companies between 200 and 2000 headcount.

Voice rules:
- Operator-to-operator. Read like a peer noticed something.
- Specific over generic. Named investor, named prior company, exact title.
- Lower the stakes. No salesy hedging, no jargon.
- British English. No exclamation marks. No emojis.
- Each hook 1-2 sentences, under 50 words.

Banned phrases: "hope this finds you well", "wanted to reach out", "leverage", "synergy", "circle back", "touch base".

Every candidate MUST satisfy BOTH of these in the same hook:

A. SPECIFICITY — reference at least one named fact from the signal payload:
   - Named investor or dollar amount (funding signal)
   - Named prior company or prior exact role (exec_hire signal)
   - Exact job title posted (ld_posting signal)
   - Specific headcount numbers (headcount_growth signal)

B. BUYER CONTEXT — reference at least one specific fact about the prospect's role or background:
   - The prospect's exact current title at the company (e.g. "CHRO", "VP People")
   - A named prior company AND prior role together (e.g. "VP People at Coda for 4 years")
   - A specific concrete detail from their LinkedIn summary or recent posts
   - Their stated focus area (e.g. "scaling the manager bench", "leadership development")

Generic "congrats on the round" or pure pattern observations ("post-Series C usually means...") will be rejected. The hook must read like it could only be written to THIS prospect, not anyone else at the company.

Worked example (funding signal, CHRO target):
  "Welcome to Vanta, Sarah. Coda to a Series B compliance scale-up is an interesting move. The 80-to-600 scale you ran at Coda is rare context for what's coming here."
  -> Specificity: named "Coda", "80-to-600" headcount.
  -> Buyer context: her exact prior role tenure + named prior company + her unique scale experience.

Output strictly as a JSON array of exactly {n_candidates} strings. Each string is one hook. No prose, no preamble, no markdown fences."""

_USER_PROMPT_TEMPLATE = """Prospect: {prospect_first_name} {prospect_last_name}, {prospect_title} at {company_name}
Signal type: {signal_type}
Signal date: {signal_date}
Signal payload: {signal_payload_json}
LinkedIn summary: {linkedin_summary}
Recent posts: {recent_posts}
Company recent news: {company_recent_news}

Write {n_candidates} hook candidates. Each candidate MUST contain BOTH:

A. SPECIFICITY — at least one named fact from the signal payload (investor, dollar amount, prior company, exact title, headcount numbers).

B. BUYER CONTEXT — at least one specific fact about this prospect's role, prior role at a named company, or a concrete detail from their LinkedIn summary or recent posts. NOT a generic "congrats" or pattern observation that could be sent to anyone at the company.

If you cannot find buyer-context material in the inputs, anchor on the prospect's exact current title combined with the signal payload's specificity.

Return a JSON array of {n_candidates} strings only."""


def generate_hooks(
    signal: Signal,
    company: Company,
    contact: Contact,
    *,
    client: Anthropic | None = None,
    n_candidates: int = HOOK_CANDIDATES_PER_RUN,
) -> list[HookCandidate]:
    """Call Claude and return `n_candidates` hook candidates.

    Real API call. No fallback to hardcoded strings — if Claude errors,
    the exception propagates and the CLI surfaces it. The point of the
    demo is to prove the agentic layer is real.
    """
    api_client = client or Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        prospect_first_name=contact.first_name,
        prospect_last_name=contact.last_name,
        prospect_title=contact.title,
        company_name=company.company_name,
        signal_type=signal.signal_type,
        signal_date=signal.signal_date.isoformat(),
        signal_payload_json=json.dumps(signal.signal_payload),
        linkedin_summary=contact.linkedin_summary,
        recent_posts=json.dumps(contact.recent_posts),
        company_recent_news=company.recent_news,
        n_candidates=n_candidates,
    )

    logger.info("personaliser: calling Claude for %d hook candidates", n_candidates)
    response = api_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        temperature=HOOK_GEN_TEMPERATURE,
        system=_SYSTEM_PROMPT.format(n_candidates=n_candidates),
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    hooks = _parse_hooks(raw, n_candidates)
    logger.info("personaliser: parsed %d hook candidates", len(hooks))
    return [HookCandidate(text=h, word_count=_count_words(h)) for h in hooks]


def _parse_hooks(raw: str, n_candidates: int) -> list[str]:
    """Parse Claude output into a list of `n_candidates` hook strings.

    Tries strict JSON first. Falls back to extracting a JSON array from
    inside markdown fences. Last resort: split on blank lines so the
    pipeline doesn't die if the model adds prose.
    """
    candidates: list[str] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            candidates = [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    candidates = [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

    if not candidates:
        candidates = [chunk.strip() for chunk in raw.split("\n\n") if chunk.strip()]

    if not candidates:
        raise RuntimeError(f"Personaliser could not parse hook output: {raw!r}")

    # Trim or pad-by-truncating to exactly n_candidates (never above).
    return candidates[:n_candidates]


def _count_words(text: str) -> int:
    """Whitespace-tokenised word count for the gate length check."""
    return len(text.split())
