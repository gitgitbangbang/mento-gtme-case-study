# Part 3.4. Signal Scoring Framework

The four brief signals are scored against four multipliers. Output is one number per signal event, combined with the company's `icp_total` (from Part 2) to assign a routing tier.

## Formula

```
signal_score = base_weight × recency_decay × icp_fit × buyer_proximity
```

| Component | Range | Purpose |
|---|---|---|
| base_weight | 2-4 | Predictive power of the signal type |
| recency_decay | 0-1 | EXP(-DAYS_SINCE(signal_date) / 30). Half-life 30 days. |
| icp_fit | 0-1 | `company.icp_total / 20`. From Part 2 scoring. |
| buyer_proximity | 0.5-1 | How close the available contacts are to Mento's economic buyer (CHRO/CPO/VP People) |

Theoretical max: 4 × 1 × 1 × 1 = **4.0**.

## Base Weight per Signal

| Signal | Base Weight | Why |
|---|---|---|
| Series B/C funding (last 30d) | 4 | Highest single-trigger predictor of L&D budget. Funding unlocks scaling spend. |
| New CHRO/CPO/VP People (last 60d) | 3 | New People exec usually triggers an L&D program review inside 90 days. |
| L&D job posting | 3 | Direct hiring intent. Hiring an L&D leader is a 4-month leading indicator of L&D budget. |
| Headcount growth 20%+ in 6 months | 2 | Broad signal. Predicts management bench expansion but less direct than the others. |

## Buyer Proximity Scale

Lookup against the Contacts table for the highest-matching buyer role at the Company.

| Best contact available | Multiplier |
|---|---|
| CHRO / CPO / VP People with recent engagement (last 30d) | 1.0 |
| CHRO / CPO / VP People in HubSpot, no engagement | 0.9 |
| Head of L&D / Talent Management / Manager Development | 0.75 |
| Generic HR contact (HR Manager, People Ops Coordinator) | 0.6 |
| No relevant contact | 0.5 (and a Find Contacts at Company sub-task fires before the SDR DM) |

## Routing Tiers

| Priority | Trigger | Action | Channel | SLA |
|---|---|---|---|---|
| **P1** | signal_score >= 3 AND icp_total >= 11 | Direct DM to assigned SDR | Slack DM | 60 seconds |
| **P2** | signal_score 2-3 OR (signal_score < 2 AND icp_total >= 16) | Daily digest | `#sdr-priority` | 9am ET daily |
| **P3** | signal_score < 2 AND icp_total 11-15 | Weekly digest | `#sdr-priority` | Monday 9am ET |
| Park | icp_total < 11 | No alert | (none) | Rescore monthly |

## Worked Examples

### Example 1: Anthropic raises Series C, 4 days ago

| Component | Value |
|---|---|
| Signal | Series B/C funding |
| base_weight | 4 |
| Days since signal | 4 |
| recency_decay | EXP(-4/30) = 0.875 |
| company.icp_total | 18 |
| icp_fit | 18/20 = 0.9 |
| Best contact | CHRO with engagement (opened email last week) |
| buyer_proximity | 1.0 |
| **signal_score** | 4 × 0.875 × 0.9 × 1.0 = **3.15** |
| icp_total | 18 |
| **Tier** | **P1** (signal_score >= 3 AND icp_total >= 11) |
| Action | Slack DM to SDR in 60 seconds with pre-populated funding-anchored draft |

### Example 2: Mid-size SaaS posted L&D Director role, 20 days ago

| Component | Value |
|---|---|
| Signal | L&D job posting |
| base_weight | 3 |
| Days since signal | 20 |
| recency_decay | EXP(-20/30) = 0.513 |
| company.icp_total | 13 |
| icp_fit | 13/20 = 0.65 |
| Best contact | Generic HR Manager, no engagement |
| buyer_proximity | 0.6 |
| **signal_score** | 3 × 0.513 × 0.65 × 0.6 = **0.6** |
| icp_total | 13 |
| **Tier** | **P3** (signal_score < 2 AND icp_total 11-15) |
| Action | Weekly digest Monday 9am ET. Find Contacts at Company sub-task fires to add a CHRO/CPO/VP People contact before next rescore. |

### Example 3: Brex hired new CHRO, 35 days ago

| Component | Value |
|---|---|
| Signal | New CHRO/CPO/VP People |
| base_weight | 3 |
| Days since signal | 35 |
| recency_decay | EXP(-35/30) = 0.311 |
| company.icp_total | 19 |
| icp_fit | 19/20 = 0.95 |
| Best contact | The new CHRO is in HubSpot but no engagement yet |
| buyer_proximity | 0.9 |
| **signal_score** | 3 × 0.311 × 0.95 × 0.9 = **0.80** |
| icp_total | 19 |
| **Tier** | **P2** (signal_score < 2 BUT icp_total >= 16) |
| Action | Daily digest 9am ET with exec-hire-anchored draft. The icp_total override catches high-fit accounts even when the signal has decayed. |

## Recalibration

Skip and Edit rates from the SDR's HITL review (Stage 4 in Part 3.2) feed back into the base weights monthly. If SDRs Skip a signal type at >40% over 30 days, that signal's base_weight drops by 0.5. If they Send a signal type with no edits at >70%, base_weight stays or rises.

Routing thresholds are config rows in Clay, not code, so they ship in minutes.
