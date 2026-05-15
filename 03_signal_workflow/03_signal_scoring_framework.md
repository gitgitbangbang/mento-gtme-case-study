# 3.4 Signal Scoring Framework

The four brief signals are scored against three multipliers. Output is one number per signal event, combined with the company's `icp_total` (from Part 2) at the routing stage to assign a tier.

## Formula

```
signal_score = base_weight × recency_decay × buyer_proximity
```

| Component | Range | Purpose |
|---|---|---|
| base_weight | 2-4 | Predictive power of the signal type |
| recency_decay | 0-1 | EXP(-DAYS_SINCE(signal_date) / 30). Half-life 30 days. |
| buyer_proximity | 0-1 | How close the available contacts are to Mento's economic buyer (CHRO/CPO/VP People) |

Theoretical max: 4 × 1 × 1 = **4.0**.

`icp_total` is not multiplied into the score because it already gates the routing tiers. Using it twice would double-count.

## Base Weight per Signal

| Signal | Base Weight | Why |
|---|---|---|
| Series B/C funding (last 30d) | 4 | Highest single-trigger predictor of L&D budget. Funding unlocks scaling spend. |
| New CHRO/CPO/VP People (last 60d) | 3 | New People exec usually triggers an L&D program review inside 90 days. |
| L&D job posting | 3 | Direct hiring intent. Hiring an L&D leader is a 4-month leading indicator of L&D budget. |
| Headcount growth 20%+ in 6 months | 2 | Broad signal. Predicts management bench expansion but less direct than the others. |

## Buyer Proximity Scale

Lookup against the Contacts table for the highest-matching buyer role at the Company.

| Best Contact Available | Multiplier |
|---|---|
| CHRO / CPO / VP People with recent engagement (last 30d) | 1.0 |
| CHRO / CPO / VP People in HubSpot, no engagement | 0.9 |
| Head of L&D / Talent Management / Manager Development | 0.75 |
| Generic HR contact (HR Manager, People Ops Coordinator) | 0.6 |
| No relevant contact | **0** |

When buyer_proximity = 0, the signal cannot route to a rep. It goes to the **Discovery tier** instead. The Find Contacts at Company enrichment fires, the new contact lands in the Contacts table, and the signal rescores on the next pass.

## Routing Tiers

| Priority | Trigger | Action | Channel | SLA |
|---|---|---|---|---|
| **P1** | signal_score >= 3 AND icp_total >= 11 | Direct DM to assigned SDR | Slack DM | 60 seconds |
| **P2** | signal_score 1.5-3 OR (signal_score < 1.5 AND icp_total >= 16) | Daily digest to **P2 branch** | `#sdr-priority-p2` (Slack channel or threaded branch) | 9am ET daily |
| **P3** | signal_score < 1.5 AND icp_total 11-15 | Weekly digest to **P3 branch** | `#sdr-priority-p3` (Slack channel or threaded branch) | Monday 9am ET |
| **Discovery** | signal_score = 0 (no buyer contact) AND icp_total >= 11 | Trigger Find Contacts at Company. Rescore on next pass. | (no SDR alert) | Within 6h of signal fire |
| Park | icp_total < 11 | No alert | (none) | Rescore monthly |

### Digest Format (Slack)

A **digest** is a single batched Slack message containing all signals of that tier from the period, sorted by score (highest first).

- **P2 digest** posts at 9am ET to its own Slack branch (`#sdr-priority-p2` or a dedicated thread). Lists all P2 signals fired in the previous 24h.
- **P3 digest** posts at Monday 9am ET to its own Slack branch (`#sdr-priority-p3`). Lists all P3 signals fired in the previous 7 days.

Why branched, not all in one channel: SDRs can navigate to the priority level they want to work, mute lower tiers during focus blocks, and treat each branch with a different cadence. Single-channel firehose creates notification fatigue and gets ignored.

## Right Rep Assignment

Two-step logic:

1. **Primary.** If `company.assigned_owner` exists in HubSpot, route to that SDR.
2. **Fallback.** If unowned, round-robin between SDR 1 and SDR 2. On assignment, write the owner back to HubSpot so subsequent signals on the same Company route to the same SDR.

> **🚩 Open question (Week 1 discovery).** How are the two SDRs currently splitting accounts? Geography, segment (PLG vs sales-led), industry, alphabetical, or unstructured? The right-rep logic above is a sensible default for v1, but if the team already has an established split, the routing should mirror it. Asks for the discovery list in Part 1, Q2.

## Self-Improvement Loop

The four base weights are not fixed forever. They recalibrate monthly based on what the SDRs actually do at the HITL Send / Edit / Skip step in Stage 4 of the workflow.

| Behaviour Over 30 Days | Action |
|---|---|
| SDR Skip rate > 40% on a given signal type | base_weight drops by 0.5 (signal is firing too noisily) |
| SDR Send-no-edit rate > 70% | base_weight holds or rises by 0.25 (signal is producing high-quality drafts) |
| Find Contacts at Company sub-task success rate < 50% | Flag the signal source for review (might be detecting accounts where the buyer contact is genuinely hard to find) |

## Worked Examples

### Example 1: Anthropic Raises Series C, 4 Days Ago

| Component | Value |
|---|---|
| Signal | Series B/C funding |
| base_weight | 4 |
| Days since signal | 4 |
| recency_decay | EXP(-4/30) = 0.875 |
| Best contact | CHRO with engagement (opened email last week) |
| buyer_proximity | 1.0 |
| **signal_score** | 4 × 0.875 × 1.0 = **3.5** |
| icp_total | 18 |
| **Tier** | **P1** (signal_score >= 3 AND icp_total >= 11) |
| Action | Slack DM to assigned SDR in 60 seconds with funding-anchored draft |

### Example 2: Mid-Size SaaS Posted L&D Director Role, 20 Days Ago

| Component | Value |
|---|---|
| Signal | L&D job posting |
| base_weight | 3 |
| Days since signal | 20 |
| recency_decay | EXP(-20/30) = 0.513 |
| Best contact | Generic HR Manager, no engagement |
| buyer_proximity | 0.6 |
| **signal_score** | 3 × 0.513 × 0.6 = **0.92** |
| icp_total | 13 |
| **Tier** | **P3** (signal_score < 1.5 AND icp_total 11-15) |
| Action | Weekly digest in `#sdr-priority-p3` Monday 9am ET. A Find Contacts at Company sub-task also fires to add a CHRO/CPO/VP People contact for the next pass. |

### Example 3: Brex Hired New CHRO, 35 Days Ago

| Component | Value |
|---|---|
| Signal | New CHRO/CPO/VP People |
| base_weight | 3 |
| Days since signal | 35 |
| recency_decay | EXP(-35/30) = 0.311 |
| Best contact | The new CHRO is in HubSpot but no engagement yet |
| buyer_proximity | 0.9 |
| **signal_score** | 3 × 0.311 × 0.9 = **0.84** |
| icp_total | 19 |
| **Tier** | **P2** (signal_score < 1.5 BUT icp_total >= 16) |
| Action | Daily digest in `#sdr-priority-p2` at 9am ET with exec-hire-anchored draft. The icp_total override catches high-fit accounts even when the signal has decayed. |

### Example 4: Series-C-Funded Startup, No Buying-Committee Contacts

| Component | Value |
|---|---|
| Signal | Series B/C funding |
| base_weight | 4 |
| Days since signal | 8 |
| recency_decay | EXP(-8/30) = 0.766 |
| Best contact | None in HubSpot |
| buyer_proximity | 0 |
| **signal_score** | 4 × 0.766 × 0 = **0** |
| icp_total | 16 |
| **Tier** | **Discovery** (signal_score = 0 AND icp_total >= 11) |
| Action | Find Contacts at Company fires within 6h. New contact lands in Contacts table. Signal rescores on the next pass. If a CHRO is added with no engagement, recalculated score = 4 × 0.71 × 0.9 = **2.56**, routes to P2 branch. |
