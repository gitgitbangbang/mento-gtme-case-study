"""Static configuration for the signal engine.

Keeps base weights, scoring thresholds, model names and prompt strings out
of the business logic modules. Section 3.4 of the case study calls these
out as the auditable, deterministic surface of the workflow — when Mento
tunes thresholds, they tune them here.
"""

from __future__ import annotations

from typing import Final

# --- LLM ----------------------------------------------------------------

ANTHROPIC_MODEL: Final[str] = "claude-sonnet-4-6"
ANTHROPIC_MAX_TOKENS: Final[int] = 1024
HOOK_GEN_TEMPERATURE: Final[float] = 0.7
GATE_TEMPERATURE: Final[float] = 0.0

# --- Scoring formula ----------------------------------------------------

# signal_score = base_weight * recency_decay * buyer_proximity
# Source: 03_signal_scoring_framework.md
BASE_WEIGHTS: Final[dict[str, float]] = {
    "funding": 4.0,
    "exec_hire": 3.0,
    "ld_posting": 3.0,
    "headcount_growth": 2.0,
}

# EXP(-DAYS_SINCE(signal_date) / RECENCY_HALF_LIFE_DAYS)
RECENCY_HALF_LIFE_DAYS: Final[int] = 30

# Buyer-proximity lookup against the highest-matching contact role.
BUYER_PROXIMITY: Final[dict[str, float]] = {
    "economic_engaged": 1.0,      # CHRO/CPO/VP People with recent engagement
    "economic_unengaged": 0.9,    # CHRO/CPO/VP People in HubSpot, no engagement
    "champion": 0.75,              # Head of L&D / Talent Mgmt / Manager Dev
    "operational": 0.6,            # Generic HR / People Ops Coordinator
    "none": 0.0,                   # No relevant contact — routes to Discovery
}

# Recent engagement window for the economic-buyer multiplier.
ENGAGEMENT_WINDOW_DAYS: Final[int] = 30
ENGAGEMENT_SCORE_THRESHOLD: Final[int] = 5

# --- Routing tiers ------------------------------------------------------

# Source: 03_signal_scoring_framework.md — Routing Tiers table.
P1_SIGNAL_SCORE_MIN: Final[float] = 3.0
P1_ICP_MIN: Final[int] = 11

P2_SIGNAL_SCORE_MIN: Final[float] = 1.5
P2_SIGNAL_SCORE_MAX: Final[float] = 3.0
P2_ICP_OVERRIDE_MIN: Final[int] = 16

P3_ICP_MIN: Final[int] = 11
P3_ICP_MAX: Final[int] = 15

DISCOVERY_ICP_MIN: Final[int] = 11

# --- Strong-Hook Gate ---------------------------------------------------

HOOK_MAX_WORDS: Final[int] = 50
HOOK_CANDIDATES_PER_RUN: Final[int] = 3
SIGNAL_FRESHNESS_DAYS: Final[int] = 60

# --- Draft Assembly Agent ----------------------------------------------

# Hard cap on the total body length per Mento brand-voice rule
# ("Under 70 words total | Senior People execs scan, don't read.").
# Source: 03_outreach_drafts.md, "Brand Voice Rules" table row 6.
MAX_EMAIL_WORDS: Final[int] = 70

# How many polish attempts to make before logging a warning and shipping
# whatever the model produced. First attempt + N retries = N+1 total calls.
MAX_POLISH_RETRIES: Final[int] = 2

BANNED_PHRASES: Final[tuple[str, ...]] = (
    "hope this finds you well",
    "hope this email finds you well",
    "wanted to reach out",
    "leverage",
    "synergy",
    "circle back",
    "touch base",
    "low-hanging fruit",
)

# --- Smartlead campaign IDs (stubbed) -----------------------------------

SMARTLEAD_CAMPAIGNS: Final[dict[str, str]] = {
    "funding": "mento-signal-funding",
    "exec_hire": "mento-signal-exec-hire",
    "ld_posting": "mento-signal-ld-posting",
    "headcount_growth": "mento-signal-headcount-growth",
}

# --- SDR signature placeholder used when none supplied ------------------

DEFAULT_SDR_SIGNATURE: Final[str] = "Alex"
