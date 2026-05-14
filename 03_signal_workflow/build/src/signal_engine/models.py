"""Core dataclasses passed between signal-engine stages.

Mirrors the Signals, Companies and Contacts tables described in the Part 2
data foundation, plus the agent-drafting artefacts produced in Stage 4.
Everything that flows downstream of detection is frozen so a later stage
cannot mutate upstream state by accident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

SignalType = Literal["funding", "exec_hire", "ld_posting", "headcount_growth"]
Tier = Literal["P1", "P2", "P3", "Discovery", "Park"]
BuyerRole = Literal["economic", "champion", "operational", "generic", "none"]
SDRDecision = Literal["send", "edit", "skip"]


@dataclass(frozen=True)
class Signal:
    """One detected buying signal event."""

    signal_id: str
    signal_type: SignalType
    signal_date: date
    company_id: str
    signal_source: str
    signal_payload: dict[str, Any]


@dataclass(frozen=True)
class Company:
    """Account record with ICP breakdown from Part 2 enrichment."""

    company_id: str
    company_name: str
    domain: str
    linkedin_url: str
    headcount: int
    industry: str
    funding_stage: str
    hr_tech_stack: list[str]
    icp_fit: int
    icp_timing: int
    icp_access: int
    icp_intent: int
    icp_budget: int
    icp_total: int
    lifecycle_stage: str
    recent_news: str


@dataclass(frozen=True)
class Contact:
    """Buyer-committee contact at a target Company."""

    contact_id: str
    company_id: str
    first_name: str
    last_name: str
    email: str
    title: str
    linkedin_url: str
    buyer_role: BuyerRole
    engagement_score: int
    linkedin_summary: str
    recent_posts: list[str]


@dataclass(frozen=True)
class ScoreBreakdown:
    """Multipliers and final score from `scorer.compute`."""

    base_weight: float
    recency_decay: float
    buyer_proximity: float
    signal_score: float
    days_since_signal: int


@dataclass(frozen=True)
class HookCandidate:
    """One personalisation hook produced by the Personalisation Agent."""

    text: str
    word_count: int


@dataclass(frozen=True)
class GateVerdict:
    """Strong-Hook Gate evaluation of a single hook candidate."""

    candidate: HookCandidate
    passed: bool
    specificity: bool
    timeliness: bool
    buyer_context: bool
    length_ok: bool
    voice_ok: bool
    reason: str


@dataclass(frozen=True)
class Draft:
    """Final assembled email ready for the SDR HITL terminal."""

    signal_id: str
    company_id: str
    contact_id: str
    subject: str
    body: str
    selected_hook: str
    template_name: str


@dataclass
class AuditEntry:
    """Per-run audit record. Mutable so each stage can append before write."""

    run_id: str
    started_at: datetime
    signal: dict[str, Any]
    company: dict[str, Any]
    contact: dict[str, Any]
    score: dict[str, Any] = field(default_factory=dict)
    tier: str = ""
    hook_candidates: list[dict[str, Any]] = field(default_factory=list)
    selected_hook: str = ""
    gate_decision: dict[str, Any] = field(default_factory=dict)
    draft: dict[str, Any] = field(default_factory=dict)
    sdr_decision: str = ""
    sdr_edited_body: str = ""
    completed_at: datetime | None = None
