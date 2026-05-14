"""Stage 4 (routing half): Assign a P1/P2/P3/Discovery/Park tier.

Pure deterministic mapping of (ScoreBreakdown, Company.icp_total) to a
tier per the table in 03_signal_scoring_framework.md.

| Tier | Trigger |
|---|---|
| P1 | signal_score >= 3 AND icp_total >= 11 |
| P2 | signal_score in [1.5, 3) OR (signal_score < 1.5 AND icp_total >= 16) |
| P3 | signal_score < 1.5 AND icp_total 11-15 |
| Discovery | signal_score == 0 AND icp_total >= 11 |
| Park | icp_total < 11 |

Discovery is checked before P2/P3 because signal_score = 0 means
buyer_proximity = 0 (no buyer contact), and the right next action is to
fire Find Contacts at Company rather than route to an SDR.
"""

from __future__ import annotations

import logging

from signal_engine.constants import (
    DISCOVERY_ICP_MIN,
    P1_ICP_MIN,
    P1_SIGNAL_SCORE_MIN,
    P2_ICP_OVERRIDE_MIN,
    P2_SIGNAL_SCORE_MAX,
    P2_SIGNAL_SCORE_MIN,
    P3_ICP_MAX,
    P3_ICP_MIN,
)
from signal_engine.models import Company, ScoreBreakdown, Tier

logger = logging.getLogger(__name__)


def assign(score: ScoreBreakdown, company: Company) -> Tier:
    """Return the routing tier for this scored signal."""
    icp = company.icp_total
    s = score.signal_score

    # Park: company is below ICP floor regardless of score.
    if icp < P1_ICP_MIN:
        tier: Tier = "Park"
    # Discovery: signal_score is exactly zero (no buyer contact) but
    # company is otherwise in ICP. Fire Find Contacts at Company.
    elif s == 0 and icp >= DISCOVERY_ICP_MIN:
        tier = "Discovery"
    # P1: strong score AND in-ICP.
    elif s >= P1_SIGNAL_SCORE_MIN and icp >= P1_ICP_MIN:
        tier = "P1"
    # P2: mid score, OR low score with very high ICP override.
    elif P2_SIGNAL_SCORE_MIN <= s < P2_SIGNAL_SCORE_MAX:
        tier = "P2"
    elif s < P2_SIGNAL_SCORE_MIN and icp >= P2_ICP_OVERRIDE_MIN:
        tier = "P2"
    # P3: low score with mid ICP.
    elif s < P2_SIGNAL_SCORE_MIN and P3_ICP_MIN <= icp <= P3_ICP_MAX:
        tier = "P3"
    else:
        # Fallback should not be reachable given the constants, but keep
        # the type narrow rather than raising mid-pipeline.
        tier = "P3"

    logger.info(
        "router: signal_score=%.3f icp_total=%d -> %s",
        s,
        icp,
        tier,
    )
    return tier


def channel_for(tier: Tier) -> str:
    """Return the human-readable destination channel for an assigned tier.

    STUB: production replacement posts a Slack DM (P1) or threaded message
    to `#sdr-priority-p2` / `#sdr-priority-p3` (P2/P3 digests). Here we
    return a label that the CLI prints alongside the draft.
    """
    return {
        "P1": "SDR direct DM (would post to #sdr-priority, 60s SLA)",
        "P2": "P2 daily digest (would post to #sdr-priority-p2, 9am ET daily)",
        "P3": "P3 weekly digest (would post to #sdr-priority-p3, Monday 9am ET)",
        "Discovery": "No SDR alert; fires Find Contacts at Company (6h SLA)",
        "Park": "No alert; rescore monthly",
    }[tier]
