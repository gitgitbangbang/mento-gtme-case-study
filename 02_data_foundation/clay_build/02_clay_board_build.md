# Clay Board Build. Part 2 Data Foundation.

One workbook. Three tables. **Companies** is the master. **Contacts** attaches via `hubspot_company_id`. **Signals** supports both, with rows reflected back into Companies and Contacts as lookup columns. Companies and Contacts both pull from and write back to HubSpot. Signals also writes back to a HubSpot custom object `Signal Event`.

## Workbook architecture

```
                  ┌─────────────────────────┐
                  │       HubSpot CRM       │
                  └────────────┬────────────┘
                               │
              pull/write-back  │  pull/write-back
                ┌──────────────┴──────────────┐
                │                              │
        ┌───────▼────────┐            ┌────────▼────────┐
        │  Companies     │◄───────────┤   Contacts      │
        │  (master)      │  FK link   │   (attached)    │
        └───────┬────────┘            └────────┬────────┘
                │                              │
                │ lookup signals               │ lookup signals
                │                              │
                └──────────────┬───────────────┘
                               ▼
                       ┌──────────────────┐
                       │    Signals       │
                       │ (supports both)  │
                       └────────┬─────────┘
                                │ write-back as
                                ▼
                       HubSpot Signal Event
                       (custom object)
```

## Source ingestion and write-back map

| Table | Pull source | Refresh | Write-back target |
|---|---|---|---|
| Companies | HubSpot Companies (native) | Every 6h | HubSpot Company custom properties |
| Contacts | HubSpot Contacts (native) plus Find Contacts at Company on demand | Every 6h | HubSpot Contact custom properties |
| Signals | Crunchbase, LinkedIn (Apify), Greenhouse, Lever, Firecrawl, G2 Intent, CommonRoom, RB2B | Per signal type (6h to real-time) | HubSpot Signal Event custom object |

---

## Companies table: column-by-column

Columns run left to right in dependency order. Each enrichment writes a confidence score. Below 70 = manual review queue. Conflicting data triggers an AI tiebreaker via Clay's **Use AI** column calling Claude or Mistral.

### Layer 1. Identification

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 1 | hubspot_company_id | Import | HubSpot Companies | 0 |
| 2 | company_name | Import | HubSpot | 0 |
| 3 | company_website | Import | HubSpot | 0 |
| 4 | normalized_domain | Formula | Clayscript: lowercase, strip protocol, strip www, strip path | 0 |
| 5 | company_linkedin_url | Enrichment | Clay: Company Domain to LinkedIn (Sourcescrub) | 1 credit |
| 6 | dedupe_key | Formula | Prefer LinkedIn URL, fallback domain, fallback name | 0 |
| 7 | dedupe_status | Formula | Match against existing rows, flag duplicates | 0 |

### Layer 2. Firmographic (always-on, multi-source consensus)

All five primary sources fire on every row. Consensus formula picks the most-agreed value. AI tiebreaker resolves disagreements.

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 8 | apollo_enrichment | Enrichment | Clay: Enrich Company via Apollo.io | 1 credit |
| 9 | ocean_enrichment | Enrichment | Clay: Enrich Company via Ocean.io | 1 credit |
| 10 | clearbit_enrichment | Enrichment | Clay: Enrich Company via Clearbit | 8 credits |
| 11 | zoominfo_enrichment | Enrichment | Clay: Enrich Company via ZoomInfo | 8 credits |
| 12 | pdl_enrichment | Enrichment | Clay: Enrich Company via People Data Labs | 3 credits |
| 13 | lusha_enrichment | Conditional Enrichment | Clay: Enrich Company via Lusha. Only fires if any of 8 to 12 returns null on headcount or industry. | 4 credits |
| 14 | claygent_fallback | Conditional Enrichment | Clay: Claygent web search. Only fires if all above return null on critical fields. | 2 credits |
| 15 | firmographic_consensus | Formula | Weighted vote across sources for headcount, industry, stage, country | 0 |
| 16 | firmographic_confidence | Formula | (agreement_count / total_sources_responded) * 100 | 0 |
| 17 | firmographic_ai_tiebreaker | Conditional Use AI | Claude API. Fires only if confidence < 70. | 0.1 credit |

### Layer 2.5. Funding and valuation sub-waterfall (Clay-credit providers)

Sub-waterfall fires in sequence. Each source falls back to the next if the previous returns null on funding stage or last round amount.

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 18 | crunchbase_funding | Enrichment | Clay: Company Latest Funding (Crunchbase) | 5.8 credits |
| 19 | crunchbase_valuation | Conditional Enrichment | Clay: Company Valuation (Crunchbase). Only if 18 returns a stage. | 11.8 credits |
| 20 | tracxn_funding | Conditional Enrichment | Clay: Tracxn Company Funding. Only if 18 returns null. | 4 credits |
| 21 | dealroom_funding | Conditional Enrichment | Clay: Dealroom Company Funding. Only if 18 and 20 return null. | 3 credits |
| 22 | clearbit_funding_metrics | Formula extract | Pulled from 10 clearbit_enrichment | 0 |
| 23 | apollo_funding_metrics | Formula extract | Pulled from 8 apollo_enrichment | 0 |
| 24 | pdl_funding_metrics | Formula extract | Pulled from 12 pdl_enrichment | 0 |
| 25 | funding_consensus | Formula | Coalesce-with-priority across 18, 20, 21, 22, 23, 24 for funding_stage, last_round_amount, last_round_date | 0 |
| 26 | funding_confidence | Formula | Source agreement score | 0 |
| 27 | funding_ai_tiebreaker | Conditional Use AI | Claude API. Fires if confidence < 70, references latest press release. | 0.1 credit |

### Layer 3. Technographic (with fallback)

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 28 | builtwith_tech_stack | HTTP API | builtwith.com/api filtered to HR/L&D category | $0.05 |
| 29 | wappalyzer_tech_stack | Conditional HTTP API | wappalyzer.com/api. Only if 28 returns null or errors. | $0.03 |
| 30 | hr_stack_normalized | Formula | Map detected vendors to hr_stack_present boolean and named tools list | 0 |

### Layer 4. Signal lookups (from Signals table)

Each lookup joins on `company_id` against the Signals table and returns the most recent signal of each type with its weight and recency decay applied.

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 31 | latest_funding_signal | Lookup | Signals where signal_type = "funding" and company_id matches, ORDER BY signal_date DESC LIMIT 1 | 0 |
| 32 | latest_exec_change_signal | Lookup | Signals where signal_type = "exec_hire" | 0 |
| 33 | latest_headcount_growth_signal | Lookup | Signals where signal_type = "headcount_growth" | 0 |
| 34 | latest_ld_posting_signal | Lookup | Signals where signal_type = "ld_job_posting" | 0 |
| 35 | latest_intent_signal | Lookup | Signals where signal_type IN ("g2_intent", "commonroom", "rb2b") | 0 |
| 36 | aggregate_signal_score | Formula | SUM of (signal_weight * decay) across all signal types in last 90 days | 0 |

### Layer 5. ICP scoring

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 37 | icp_fit | Formula | See Clayscript below (0-4) | 0 |
| 38 | icp_timing | Formula | See Clayscript below (0-4) | 0 |
| 39 | icp_access | Lookup | Count Contacts where buyer_role IN ("economic", "champion") | 0 |
| 40 | icp_intent | Formula | Normalized from 35 latest_intent_signal (0-4) | 0 |
| 41 | icp_budget | Formula | Funding stage and amount to 0-4 | 0 |
| 42 | icp_total | Formula | Sum of 37 to 41 | 0 |

### Layer 6. Lifecycle

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 43 | lifecycle_stage | Formula | Cascading stage logic (see Clayscript) | 0 |
| 44 | dedup_audit | Formula | JSON payload with merge metadata | 0 |

### Layer 7. Write-back and alerts

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 45 | **Write to HubSpot** | Action | Update Company custom properties via native integration. Update-on-change only. | 0 |
| 46 | **Slack alert** | Action | Send to #sdr-priority if icp_total >= 16 | 0 |

**Per row total**, including always-on multi-source consensus and funding waterfall: ~40 Clay credits plus ~$0.08 external APIs.

---

## Contacts table: column-by-column

### Layer 1. Identification

| # | Column | Type | Source / Formula |
|---|---|---|---|
| 1 | hubspot_contact_id | Import | HubSpot Contacts |
| 2 | email_raw | Import | HubSpot |
| 3 | email_normalized | Formula | Strip plus-aliases, lowercase |
| 4 | personal_linkedin_url | Enrichment | Clay: Find Professional Profile (LeadMagic) |
| 5 | dedupe_key_contact | Formula | Prefer email, fallback LinkedIn URL, fallback name plus company |

### Layer 2. LinkedIn context enrichment

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 6 | person_current_company | Enrichment | Clay: Person Current Company | 1 credit |
| 7 | linkedin_role | Formula extract | Pulled from 6 | 0 |
| 8 | linkedin_seniority | Formula extract | Pulled from 6 | 0 |
| 9 | linkedin_about | Enrichment | Clay: Find Professional Profile (LeadMagic), about_section field | 1 credit |
| 10 | linkedin_responsibilities | Enrichment | Clay: Find Professional Profile (LeadMagic), experience field for current role | (included in 9) |
| 11 | claygent_role_context | Conditional Use AI | Claygent web search for additional context. Only fires if 6 through 10 leave role ambiguous. | 2 credits |

### Layer 3. Buyer role mapping (all Clay, no external lookup table)

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 12 | title_normalized | Formula | Lowercase, strip prefixes/suffixes (Sr., Jr.) | 0 |
| 13 | buyer_role_by_title | Formula | Title regex match to (economic, champion, user, procurement, unknown) | 0 |
| 14 | buyer_role_by_linkedin | Formula | Combines 7 linkedin_role and 9 linkedin_about for context-aware classification | 0 |
| 15 | buyer_role_final | Use AI | Claude API takes title, LinkedIn role, about section, responsibilities, and Claygent context. Returns one of (economic, champion, user, procurement, unknown) with confidence score. | 0.1 credit |

### Layer 4. Engagement and linkage

| # | Column | Type | Source / Formula | Cost |
|---|---|---|---|---|
| 16 | email_validated | Enrichment | Clay: Validate Email (LeadMagic) | 1 credit |
| 17 | engagement_score | Lookup | Sum of engagement events in last 30 days from HubSpot | 0 |
| 18 | linked_company_id | Lookup | Match email domain or company name to Companies table | 0 |

### Layer 5. Write-back

| # | Column | Type | Source / Formula |
|---|---|---|---|
| 19 | **Write to HubSpot** | Action | Update Contact custom properties (buyer_role_final, engagement_score, linked_company_id) |

**Per contact row total:** ~6 Clay credits.

---

## Signals table: column-by-column

One row per detected signal event. Seven signal types share the table; non-applicable fields are null per row.

### Layer 1. Source ingestion (per signal type)

| Signal type | Source | Refresh | Detection method |
|---|---|---|---|
| funding | Crunchbase API | Every 12h | Webhook for new funding rounds matching ICP filter |
| exec_hire | LinkedIn via Apify | Every 24h | Scrape company People page, diff against last snapshot |
| headcount_growth | Clearbit, PDL, LinkedIn | Every 7 days | Delta on current vs 6-month-prior headcount |
| ld_job_posting | Greenhouse, Lever, Firecrawl | Every 24h | Search "L&D", "Leadership Development", "Manager Development" titles |
| g2_intent | G2 Buyer Intent API | Every 6h | Buyer Intent score above threshold on coaching/L&D category |
| commonroom | CommonRoom API | Every 12h | Community engagement signal (DAU/MAU lift, post comments) |
| rb2b | RB2B webhook | Real-time | Identified website visitor matches a Company in our list |

### Layer 2. Signal columns

| # | Column | Type | Source / Formula |
|---|---|---|---|
| 1 | signal_id | Generated | UUID |
| 2 | company_id | Lookup | Match domain or name to Companies.hubspot_company_id |
| 3 | contact_id | Lookup | Match person name to Contacts.hubspot_contact_id (where applicable) |
| 4 | signal_type | Import | One of seven types above |
| 5 | signal_source | Import | API or scraper name |
| 6 | signal_date | Import | Event timestamp |
| 7 | signal_raw_payload | Import | JSON of full source response (for audit) |
| 8 | signal_weight | Formula | Per-type base weight, see scoring table below |
| 9 | signal_recency_decay | Formula | EXP(-DAYS_SINCE(signal_date) / 30) (half-life 30 days) |
| 10 | signal_score | Formula | signal_weight * signal_recency_decay |
| 11 | signal_status | Formula | active / decayed / superseded |

### Layer 3. Write-back to HubSpot

| # | Column | Type | Source / Formula |
|---|---|---|---|
| 12 | **Write to HubSpot** | Action | Upsert Signal Event custom object record, associated with Company and Contact |
| 13 | **Slack alert** | Action | If signal_score >= 3 AND company.icp_total >= 11, post to #sdr-priority |

### Signal weights (base, before decay)

| signal_type | Base weight | Rationale |
|---|---|---|
| funding (Series B/C in last 30d) | 4 | Highest predictive value for coaching demand |
| exec_hire (CHRO/CPO in last 60d) | 3 | New People exec triggers L&D review |
| ld_job_posting | 3 | Direct intent signal |
| headcount_growth (20%+ in 6mo) | 2 | Manager bench expansion |
| g2_intent | 2 | Active research stage |
| commonroom | 1 | Brand engagement, not buying intent yet |
| rb2b (website visit) | 1 | Mid-funnel, low confidence on intent depth |

---

## Clayscript formulas

### Companies col 4: `normalized_domain`

```clayscript
TRIM(
  REGEX_REPLACE(
    REGEX_REPLACE(
      LOWER({{/Company Website/}}),
      "^https?://(www\\.)?",
      ""
    ),
    "/.*$",
    ""
  )
)
```

### Companies col 15: `firmographic_consensus`

```clayscript
TO_JSON({
  "headcount": MODE([
    {{/Apollo Enrichment/}}.headcount,
    {{/Ocean Enrichment/}}.headcount,
    {{/Clearbit Enrichment/}}.headcount,
    {{/ZoomInfo Enrichment/}}.headcount,
    {{/PDL Enrichment/}}.headcount,
    {{/Lusha Enrichment/}}.headcount
  ]),
  "industry": MODE([
    {{/Apollo Enrichment/}}.industry,
    {{/Ocean Enrichment/}}.industry,
    {{/Clearbit Enrichment/}}.industry,
    {{/ZoomInfo Enrichment/}}.industry,
    {{/PDL Enrichment/}}.industry
  ]),
  "country": MODE([...]),
  "stage": MODE([...])
})
```

### Companies col 25: `funding_consensus`

```clayscript
TO_JSON({
  "funding_stage": COALESCE(
    {{/Crunchbase Funding/}}.stage,
    {{/Tracxn Funding/}}.stage,
    {{/Dealroom Funding/}}.stage,
    {{/Clearbit Funding Metrics/}}.stage,
    {{/Apollo Funding Metrics/}}.stage,
    {{/PDL Funding Metrics/}}.stage
  ),
  "last_round_amount_usd": COALESCE(
    {{/Crunchbase Funding/}}.last_round_amount,
    {{/Tracxn Funding/}}.last_round_amount,
    {{/Dealroom Funding/}}.last_round_amount
  ),
  "last_round_date": COALESCE(
    {{/Crunchbase Funding/}}.last_round_date,
    {{/Tracxn Funding/}}.last_round_date,
    {{/Dealroom Funding/}}.last_round_date
  ),
  "valuation_usd": {{/Crunchbase Valuation/}}.valuation
})
```

### Companies col 37: `icp_fit` (0-4)

```clayscript
(IF({{/Firmographic Consensus/}}.headcount >= 500 AND {{/Firmographic Consensus/}}.headcount <= 5000, 1, 0)) +
(IF(CONTAINS_ANY({{/Firmographic Consensus/}}.industry, ["SaaS","Software","AI","Cloud","B2B Tech"]), 1, 0)) +
(IF(CONTAINS_ANY({{/Funding Consensus/}}.funding_stage, ["Series B","Series C","Series D","Late Stage","Public"]), 1, 0)) +
(IF({{/HR Stack Normalized/}}.hr_stack_present == TRUE, 1, 0))
```

### Companies col 38: `icp_timing` (0-4)

```clayscript
IF({{/Latest Funding Signal/}}.signal_score >= 3,
   4,
   IF({{/Latest Exec Change Signal/}}.signal_score >= 2,
      3,
      IF({{/Latest Headcount Growth Signal/}}.signal_score >= 1.5,
         2,
         IF({{/Latest LD Posting Signal/}}.signal_score >= 1,
            1,
            0))))
```

### Companies col 41: `icp_budget` (0-4)

```clayscript
IF({{/Funding Consensus/}}.last_round_amount_usd >= 50000000
   AND DAYS_SINCE({{/Funding Consensus/}}.last_round_date) <= 540,
   4,
   IF(CONTAINS({{/Funding Consensus/}}.funding_stage, "Series B"),
      3,
      IF(CONTAINS({{/Funding Consensus/}}.funding_stage, "Series A"),
         2,
         IF(CONTAINS({{/Funding Consensus/}}.funding_stage, "Bootstrapped Profitable"),
            1,
            0))))
```

### Companies col 43: `lifecycle_stage`

```clayscript
IF({{/HubSpot Deal Stage/}} == "Closed Won",
   "Customer",
   IF({{/HubSpot Deal Stage/}} != "" AND {{/HubSpot Deal Stage/}} != "Closed Lost",
      "Opportunity",
      IF({{/SDR Qualified/}} == TRUE AND {{/Meeting Booked/}} == TRUE,
         "SQL",
         IF({{/ICP Total/}} >= 11 AND {{/ICP Timing/}} >= 2,
            "MQL",
            IF({{/ICP Fit/}} >= 2 AND DAYS_SINCE({{/Last Engagement/}}) <= 30,
               "Lead",
               "Subscriber")))))
```

### Contacts col 13: `buyer_role_by_title`

```clayscript
IF(CONTAINS_ANY(LOWER({{/Title Normalized/}}), ["chro","chief people","cpo","chief human resources","vp people","vp of people","head of people","svp people"]),
   "economic",
   IF(CONTAINS_ANY(LOWER({{/Title Normalized/}}), ["l&d","learning and development","leadership development","talent management","manager development","head of talent","head of learning","people development"]),
      "champion",
      IF(CONTAINS_ANY(LOWER({{/Title Normalized/}}), ["manager","director","senior","lead","head"]) AND NOT CONTAINS_ANY(LOWER({{/Title Normalized/}}), ["finance","legal","procurement"]),
         "user",
         IF(CONTAINS_ANY(LOWER({{/Title Normalized/}}), ["procurement","finance","legal","controller","general counsel"]),
            "procurement",
            "unknown"))))
```

### Contacts col 15: `buyer_role_final` (Use AI column)

```text
System prompt to Claude:

You are a B2B buyer-role classifier for a coaching platform sold into People/L&D functions.

Inputs:
- Title (normalized): {{/Title Normalized/}}
- Title-based heuristic: {{/Buyer Role By Title/}}
- LinkedIn role from profile: {{/LinkedIn Role/}}
- LinkedIn responsibilities: {{/LinkedIn Responsibilities/}}
- LinkedIn about section: {{/LinkedIn About/}}
- LinkedIn-based heuristic: {{/Buyer Role By LinkedIn/}}
- Claygent web context: {{/Claygent Role Context/}}

Classify into exactly one of: economic, champion, user, procurement, unknown.
Output JSON: { "buyer_role": "...", "confidence": 0-100, "reasoning": "..." }

Guidance:
- economic = signs the contract (CHRO, CPO, VP/Head of People)
- champion = runs the L&D program (Head of L&D, Talent Management, Manager Development)
- user = the leader receiving coaching (Manager, Director, Senior IC)
- procurement = Finance/Legal who only touch at contract stage
- unknown = signals genuinely ambiguous, do not force a category
```

### Signals col 9: `signal_recency_decay`

```clayscript
EXP(-1 * DAYS_SINCE({{/Signal Date/}}) / 30)
```

### Signals col 10: `signal_score`

```clayscript
{{/Signal Weight/}} * {{/Signal Recency Decay/}}
```

---

## Error handling and fallback strategy (cross-cutting)

### Per-column behaviour

| Failure mode | Clay behaviour | Recovery |
|---|---|---|
| Enrichment API timeout | Cell marked "Failed", row continues | Conditional retry once after 60s. If still fails, fallback chain fires. |
| Enrichment returns null | Cell marked "Empty", row continues | Next provider in waterfall fires. If all null, manual review queue. |
| Enrichment returns low confidence (<70) | Cell completes, confidence recorded | AI tiebreaker fires (Claude Use AI column). If still <70, manual review queue. |
| Conditional condition unmet | Cell skipped, no credit charged | Next column proceeds with prior data. |
| HubSpot write-back rate-limited | Action queued | Clay native backoff. Slack alert if queue depth > 50. |
| Slack alert send fails | Action queued | Retried automatically. Logged to Clay run history. |

### Manual review queue

Clay view named `Manual Review`. Filter logic:

```
firmographic_confidence < 70
OR funding_confidence < 70
OR dedupe_status = "review_required"
OR (icp_total >= 11 AND any source returned null on critical fields)
```

Reviewed daily by GTM Engineer or RevOps. Slack digest at 8am ET to `#revops-review` if queue depth > 10.

### Systemic failure alerts

| Trigger | Channel | Action |
|---|---|---|
| Apollo API failure rate > 20% in 1h window | `#gtm-engineering` | Page on-call |
| Crunchbase API quota near exhaustion (>80% of monthly cap) | `#gtm-engineering` | 24h notice to negotiate top-up |
| Clay credits remaining < 20% of monthly cap | `#gtm-engineering` | Immediate alert |
| HubSpot write-back failures > 100 in 1h | `#gtm-engineering` | Page on-call |
| Any column's failure rate > 30% over 24h | `#gtm-engineering` | Daily summary |

### Audit trail

Every row write to HubSpot logs:

- Sources consulted per layer
- Confidence score per source
- Final consensus value
- AI tiebreaker invocation (if any) with reasoning
- Manual review status

Stored as the `dedup_audit` JSON column (Companies col 44). Replayable.

---

## Rollout plan: pilot 100, then full 5,000

### Phase 1. Pilot (Days 1-5)

- Source: random 100 accounts from the ~5,000 HubSpot Companies. **Excludes the 200 target accounts** to isolate pilot validation from active outbound work.
- Run all enrichment layers end to end.
- Validation criteria before Phase 2:
  - Firmographic consensus confidence >= 80 on at least 70% of rows
  - Funding consensus confidence >= 80 on at least 60% of rows (lower bar since funding data is sparser)
  - No write-back failures to HubSpot
  - Manual review queue depth < 15 (less than 15% of rows flagged)
  - Credit burn at or below 5,000 credits plus ~$10 external APIs
  - Spot-check 20 random pilot rows against ground truth (LinkedIn manual lookup)
- Output: validation report. Go/no-go on Phase 2.

### Phase 2. Full backfill (Days 6-10)

- Source: remaining ~4,900 HubSpot Companies.
- Throttle: 200 rows/hour to stay inside HubSpot write rate limits.
- Monitoring: daily Slack digest, credit burn, manual review queue.
- Output: full HubSpot company database scored, lifecycle-assigned, signal-attached.

### Phase 3. 200 target accounts (Days 11-12)

- Source: the original 200 target account list.
- Same pipeline, expected high signal density.
- This is where Part 3's outreach engine starts pulling from.

### Phase 4. Steady state

- New Companies added to HubSpot trigger Clay enrichment within 1 hour.
- Signal sources poll on schedules defined in the Signals table section above.
- Weekly credit burn report, monthly model recalibration.

---

## Credit and cost budget

### Per-row breakdown (Companies, always-on)

| Layer | Tools | Credits/row |
|---|---|---|
| Identification | Company Domain to LinkedIn | 1 |
| Firmographic always-on | Apollo, Ocean, Clearbit, ZoomInfo, PDL | 21 |
| Firmographic conditional | Lusha (~30% fire) plus Claygent (~10% fire) | 1.4 |
| Funding waterfall | Crunchbase Funding plus Valuation plus conditional Tracxn/Dealroom (~20% fire) | 19 |
| Funding consensus AI tiebreaker | Claude Use AI (~15% fire) | 0.015 |
| Technographic | BuiltWith ($0.05) plus conditional Wappalyzer (~10% fire) | external |
| Contact-level (per associated contact, ~3 avg) | LinkedIn plus LeadMagic plus email validate | 12 |
| AI buyer-role per contact (~3 avg) | Claude Use AI | 0.3 |
| **Total per company row** | | **~54 credits plus ~$0.06 external** |

### Monthly volume

| Item | Pilot (100 rows) | Full backfill (4,900 rows) | Steady state (~500 rows/mo) |
|---|---|---|---|
| Clay credits | ~5,400 | ~265,000 | ~27,000 |
| External APIs | ~$6 | ~$300 | ~$30 |

### Plan recommendation

- **Pilot:** existing Clay Starter plan plus ~$50 credit top-up. Total spend ~$60 to validate.
- **Full backfill:** **Clay Explorer at $800/month** (100,000 credits) plus one-time top-up of ~165,000 credits (~$1,200 at top-up rates).
- **Steady state:** Clay Explorer covers monthly burn with headroom.

---

## Subroutines (reusable across all three tables)

| Subroutine | Used in | Purpose |
|---|---|---|
| `subroutine_normalize_domain` | Companies, Contacts, Signals | Lowercase, strip protocol/www/path |
| `subroutine_normalize_company_name` | Companies, Signals | Strip suffixes, punctuation, fuzzy-prep |
| `subroutine_count_non_nulls` | Companies dedup | Survivorship completeness scoring |
| `subroutine_mode_vote` | Companies firmographic | Picks most-agreed value across sources |
| `subroutine_coalesce_with_priority` | Companies funding waterfall | First-non-null with source priority preserved |
| `subroutine_signal_decay` | Signals | EXP-decay function |
| `subroutine_buyer_role_classifier` | Contacts | Title plus LinkedIn plus AI ensemble |

Built once at the workspace level, called from any table.

---

## Open items (need decision before Phase 1)

1. Confirm Clay Explorer billing budget approval. Pilot can run on Starter.
2. Confirm HubSpot custom property creation access (for Signal Event custom object, ICP score number properties, dedup_audit text property).
3. Confirm Slack workspace channel names. Defaults assumed: `#sdr-priority`, `#revops-review`, `#gtm-engineering`.
4. Confirm RB2B webhook destination (Clay receives, or HubSpot direct then Clay polls).
5. Confirm Greenhouse and Lever scrape compliance for L&D postings (public board pages only, no auth bypass).
