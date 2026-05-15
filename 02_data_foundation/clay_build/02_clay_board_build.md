# Clay Board Build

One workbook. Three tables.
**Companies** is the master.
**Contacts** attaches via `hubspot_company_id`.
**Signals** supports both and associate as `engagement_id`
**Companies and Contacts** both pull from and write back to HubSpot.
**Signals** also writes back to a HubSpot custom object `Signal Event`.

#### Column Architecture by Table (Under Layers) ⚙️:
[https://github.com/gitgitbangbang/mento-gtme-case-study/blob/main/02_data_foundation/clay_build/02_clay_board_build.md](https://github.com/gitgitbangbang/mento-gtme-case-study/blob/main/02_data_foundation/clay_build/02_clay_board_build.md)

## Workbook Architecture

```
┌──────────────────────────────────────────────────────┐
│ Companies (master)                                   │
│  ↑ Source: HubSpot native pull, every 6h            │
│  ↓ Write-back: HubSpot company custom properties     │
└──────────────────────────────────────────────────────┘
        │
        │ (linked via hubspot_company_id)
        │
┌──────────────────────────────────────────────────────┐
│ Contacts                                             │
│  ↑ Source: HubSpot native pull + Find Contacts at    │
│    Company (Clay) for under-staffed ICP accounts     │
│    (icp_total ≥ 11 AND contacts < 3)                 │
│  ↓ Write-back: HubSpot contact custom properties     │
└──────────────────────────────────────────────────────┘
        ▲                              ▲
        │ lookup latest signals        │ lookup latest signals
        │ per type                     │ per type
        │                              │
┌──────────────────────────────────────────────────────┐
│ Signals (supports both)                              │
│  ↑ Source: Crunchbase, LinkedIn (Apify), Greenhouse, │
│    Lever, Firecrawl, G2 Intent, CommonRoom, RB2B     │
│  ↓ Write-back: HubSpot Signal Event (custom object), │
│    associated to Company + Contact where applicable  │
└──────────────────────────────────────────────────────┘
```

## Layered Workflow Inside Each Table

### Companies Table

| Layer | What It Does | Tools |
|---|---|---|
| Identify | Normalise domain + LinkedIn URL, dedupe key | Clay |
| Dedupe | Continuous match against existing rows | Clay |
| Enrich (firmographic, always-on) | Apollo, Ocean.io, Clearbit, ZoomInfo, People Data Labs (Clay-credit). Lusha + Claygent as conditional fallback. Claude Use AI column. | Clay |
| Enrich (funding sub-waterfall) | Crunchbase Latest Funding, Valuation, then Tracxn, Dealroom, Clearbit, Apollo, PDL fallback chain | Clay |
| Enrich (technographic) | BuiltWith + PredictLeads on HR tech stack | Clay |
| Signal lookups | Pull most recent signal per type from Signals table | Clay |
| Score | Compute icp_total across 5 dimensions (Fit, Timing, Access, Intent, Budget) | Clay |
| Assign lifecycle | Apply lifecycle rules to set lifecycle_stage | Clay |
| Write back + alert | Push enriched fields + lifecycle to HubSpot, fire Slack alerts on threshold | Clay → HubSpot, Clay → Slack |

### Contacts Table

| Layer | What It Does | Tools |
|---|---|---|
| Identify | Normalise email + LinkedIn URL | Clay |
| Enrich (LinkedIn context) | Person Current Company, Find Professional Profile (LeadMagic) | Clay |
| Map buyer role | Apply title + LinkedIn-based heuristics → buyer_role enum | Clay |
| Validate + link | Validate email (LeadMagic), link to Company record | Clay |
| Write back | Push enriched fields to HubSpot Contact record | Clay → HubSpot |

### Signals Table

| Layer | What It Does | Tools |
|---|---|---|
| Source ingestion | Pull from Crunchbase, LinkedIn (Apify), Greenhouse, Lever, Firecrawl, G2 Intent, CommonRoom, RB2B | Clay |
| Associate | Link signal to Company (and Contact if applicable) | Clay |
| Score | Compute signal_score = base_weight × recency_decay × buyer_proximity | Clay |
| Write back | Push to HubSpot custom object Signal Event | Clay → HubSpot |
| Alert | Fire Slack DM (P1) or digest (P2/P3) | Clay → Slack |
| Reflect back | Make most-recent signal per type available to Companies + Contacts tables for lookup | Clay |

## Signal Weights

| Signal Type | Source | Refresh | Base Weight |
|---|---|---|---|
| funding | Crunchbase API | Every 12h | 4 |
| exec_hire | LinkedIn via Apify | Every 24h | 3 |
| ld_job_posting | Greenhouse, Lever, Firecrawl | Every 24h | 3 |
| headcount_growth | Clearbit, PDL, LinkedIn | Every 7 days | 2 |
| g2_intent | G2 Buyer Intent API | Every 6h | 2 |
| commonroom | CommonRoom API | Every 12h | 1 |
| rb2b | RB2B webhook | Real-time | 1 |

## Error Handling and Fallback

- Every enrichment writes confidence score. Below 70 routes to manual review queue.
- All API calls have built-in retry with 60s backoff.
- Always-on Layer 3 means single-source failure does not block the row.
- Funding waterfall fires conditionals only on null, no wasted credits.
- AI tiebreaker fires only when confidence < 70.
- Systemic failure alerts (Apollo failure rate, Crunchbase quota, Clay credit burn, HubSpot rate limits) post to `#gtm-engineering`.
- Manual review queue digest at 8am ET to `#revops-review` if depth > 10.
