# 3.2 Workflow Architecture (Text)

Four stages. Monitor, Enrich, Score, Route + Draft. The SDR is the only human in the loop and they are the one who decides whether to send. The workflow does not send automatically.

## Workflow

```
┌────────────────────────────────────────────────────────────┐
│ 1. Monitor                                                 │
│    Clay polls signal sources on per-type schedules.        │
│    Each detection writes a row to the Signals table.       │
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Enrich                                                  │
│    Lookup Company + key contacts. Pull funding amount,     │
│    headcount, exec details, job description text.          │
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Score                                                   │
│    signal_score = base_weight × recency_decay × ICP_fit.   │
│    Combined with company.icp_total = P1, P2, or P3.        │
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│ 4. Route + Draft (HITL terminal)                           │
│    Slack DM to assigned SDR with pre-populated draft.      │
│    Buttons: [Send via Smartlead] [Edit] [Skip].            │
│    SDR decides. Workflow does NOT auto-send.               │
└────────────────────────────────────────────────────────────┘
```

## Stage Detail

### 1. Monitor

| Signal | Tool | Refresh |
|---|---|---|
| Series B/C funding (last 30d) | Clay (Crunchbase API) | Every 12h |
| Headcount growth 20%+ in 6 months | Clay (Clearbit, PDL, LinkedIn) | Every 7 days |
| New CHRO/CPO/VP People (last 60d) | Clay (LinkedIn via Apify) | Every 24h |
| L&D job posting | Clay (Greenhouse, Lever, Firecrawl) | Every 24h |

Each detected event writes a new row to the **Signals table** in the Part 2 Clay board.

### 2. Enrich

Clay lookup against Companies + Contacts tables. If the Company is new, fire the full Part 2 enrichment first (Apollo, Ocean.io, Clearbit, ZoomInfo, PDL, Crunchbase). Pull signal-specific context per type: funding amount + investor list, exec's prior role and tenure, job description text.

### 3. Score

signal_score = `base_weight × recency_decay × ICP_fit_multiplier`.

| Signal | Base Weight |
|---|---|
| Series B/C funding | 4 |
| New CHRO/CPO/VP People | 3 |
| L&D job posting | 3 |
| Headcount growth 20%+ | 2 |

Combined with `company.icp_total` (from Part 2) gives the routing tier:

| Priority | Trigger | Action |
|---|---|---|
| **P1** | signal_score >= 3 AND icp_total >= 11 | SDR direct DM (60s SLA) |
| **P2** | signal_score 2-3 OR (signal_score < 2 AND icp_total >= 16) | Daily digest at 9am ET |
| **P3** | signal_score < 2 AND icp_total 11-15 | Weekly digest Monday 9am ET |

### 4. Route + Draft

Routing fires a Slack message to the assigned SDR. The message includes:

- One-line signal context ("Anthropic raised $300M Series C 4 days ago")
- Pre-populated email subject + body
- Target contact name and role
- Three buttons: `[Send via Smartlead]` `[Edit]` `[Skip]`

The draft is built by a Claude AI agent that:

1. Generates 3 personalisation hooks from signal context, LinkedIn activity, tech stack, company news
2. Tags each hook strong (specific, timely) or lite (generic)
3. If no strong hook exists, routes the signal to a manual review queue and **does not deliver a draft to the SDR**
4. Otherwise merges the best hook with the per-signal template (Part 3.5) and Mento brand voice rules

SDR clicks Send to fire the email through Smartlead. Edit opens a modal. Skip captures a reason and decays the signal.

## AI vs Deterministic

**Deterministic** for the parts that need to be auditable: signal detection thresholds, scoring formulas, routing tiers.

**Agentic** for the parts that need context: personalisation hook generation, strong-hook gating, draft assembly.

**Human (SDR)** for the send decision in this workflow's scope.

## Human-in-the-Loop

One checkpoint, terminal. The SDR receives the draft in Slack and clicks Send, Edit, or Skip.

**Why here.** The brief defines the workflow ending at SDR review ("doesn't send it automatically"). Mento sells coaching to senior People execs, and the first touch is irreversible, so SDR review on the first batch is sensible regardless of whether the brief mandated it.

**Why this works operationally.** P1 volume is ~5-15 signals per week. Two SDRs reviewing one draft each per day is sustainable.

## Beyond the Brief (Suggestion)

The workflow above stops where the brief stops. If we were building the full end-state system, the natural next move is **governed auto-send with manual rep review on exception**.

The trigger to move from "SDR approves every send" to "SDR reviews exceptions" would be a measured floor on draft quality:

- Strong-hook gate clears at >90% on the active signal mix
- SDR Skip rate sits below 10% for 30 consecutive days
- SDR Edit rate sits below 25% for 30 consecutive days
- Brand voice review (sample audit by Marketing) passes on a rolling 50-email sample

Once those clear, the system could auto-send for P1 signals where strong-hook + ICP fit + buyer-role proximity all hit high thresholds, and only flag the SDR for ambiguous cases (emoji-reaction approval). Replies would then route to a separate post-send agent.

That is for a future scope, not this case study.
