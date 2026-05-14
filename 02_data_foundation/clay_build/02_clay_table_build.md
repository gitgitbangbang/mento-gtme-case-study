# Clay Table Build. Part 2 Data Foundation.

Two tables. **Companies** is the master. **Contacts** attaches to Companies via `hubspot_company_id`. Both run on a 6-hour HubSpot native pull, write-back triggered on row complete.

## Tables and source ingestion

### Companies table
- **Source:** HubSpot native Companies import
- **Import filter:** `lifecycle != "Customer" AND lifecycle != "Dormant"`
- **Refresh:** every 6 hours
- **Initial backfill:** all ~5,000 records from HubSpot

### Contacts table
- **Source:** HubSpot native Contacts import
- **Enriched on-demand** via `Find Contacts at Company` (Clay enrichment) for any Company that has fewer than 3 contacts and is `icp_total >= 11`
- **Refresh:** every 6 hours

## Companies table: column architecture

Each row is one Company. Columns run left to right in dependency order. Conditional steps marked.

| # | Column | Type | Source / Formula | Cost per row |
|---|---|---|---|---|
| 1 | hubspot_company_id | Import | HubSpot Companies | 0 |
| 2 | company_name | Import | HubSpot | 0 |
| 3 | company_website | Import | HubSpot | 0 |
| 4 | normalized_domain | Formula | Clayscript, lowercase + strip protocol/www/path | 0 |
| 5 | company_linkedin_url | Enrichment | Clay: Company Domain to LinkedIn | ~1 credit |
| 6 | dedupe_key | Formula | Prefer LinkedIn, fallback domain, fallback name | 0 |
| 7 | dedupe_status | Formula | Match against existing rows, flag duplicates | 0 |
| 8 | apollo_enrichment | Enrichment | Clay: Enrich Company via Apollo.io | 1 credit |
| 9 | ocean_enrichment | Conditional Enrichment | Only fires if apollo confidence < 80 | 1 credit |
| 10 | crunchbase_funding | Enrichment | Clay: Company Latest Funding | 5.8 credits |
| 11 | crunchbase_valuation | Enrichment | Clay: Company Valuation | 11.8 credits |
| 12 | builtwith_tech_stack | HTTP API | builtwith.com/api filtered to HR/L&D | $0.05 |
| 13 | headcount_growth_6mo | Formula | (current - 6mo ago) / 6mo ago | 0 |
| 14 | latest_chro_hire_date | Enrichment | Clay: Find Professional Profile (LeadMagic) filtered to CHRO/CPO/VP People | 1 credit |
| 15 | active_ld_job_postings | HTTP API | Greenhouse + Lever board scrape via Firecrawl | $0.02 |
| 16 | g2_intent | HTTP API | G2 Buyer Intent API | $0.10 |
| 17 | commonroom_signals | HTTP API | CommonRoom community signal endpoint | $0.05 |
| 18 | icp_fit | Formula | See Clayscript below | 0 |
| 19 | icp_timing | Formula | See Clayscript below | 0 |
| 20 | icp_access | Lookup | Count Contacts where `buyer_role IN (economic, champion)` | 0 |
| 21 | icp_intent | Formula | Composite from G2 + CommonRoom + RB2B | 0 |
| 22 | icp_budget | Formula | Funding stage to 0-4 | 0 |
| 23 | icp_total | Formula | Sum of dimensions 18-22 | 0 |
| 24 | lifecycle_stage | Formula | Cascading stage logic | 0 |
| 25 | dedup_audit | Formula | JSON payload with merge metadata | 0 |
| 26 | **Write to HubSpot** | Action | Update company custom properties via native integration | 0 |

**Per row total:** ~22.9 Clay credits + ~$0.22 external API.

## Clayscript formulas

### Column 4. `normalized_domain`

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

### Column 6. `dedupe_key`

```clayscript
IF({{/Company LinkedIn URL/}} != "",
   {{/Company LinkedIn URL/}},
   IF({{/Normalized Domain/}} != "",
      {{/Normalized Domain/}},
      LOWER(TRIM({{/Company Name/}}))))
```

### Column 18. `icp_fit` (0-4)

```clayscript
(IF({{/Headcount/}} >= 500 AND {{/Headcount/}} <= 5000, 1, 0)) +
(IF(CONTAINS_ANY({{/Industry/}}, ["SaaS","Software","AI","Cloud","B2B Tech"]), 1, 0)) +
(IF(CONTAINS_ANY({{/Funding Stage/}}, ["Series B","Series C","Series D","Late Stage","Public"]), 1, 0)) +
(IF({{/BuiltWith Tech Stack/}} != "" AND CONTAINS_ANY({{/BuiltWith Tech Stack/}}, ["Workday","BambooHR","Lattice","Culture Amp","15Five","Gusto","Rippling","Personio"]), 1, 0))
```

### Column 19. `icp_timing` (0-4)

```clayscript
IF(DAYS_SINCE({{/Latest Funding Date/}}) <= 30 AND CONTAINS_ANY({{/Funding Stage/}}, ["Series B","Series C","Series D"]),
   4,
   IF(DAYS_SINCE({{/Latest CHRO Hire Date/}}) <= 60,
      3,
      IF({{/Headcount Growth 6mo/}} >= 0.20,
         2,
         IF({{/Active L&D Job Postings/}} >= 1,
            1,
            0))))
```

### Column 22. `icp_budget` (0-4)

```clayscript
IF({{/Last Funding Amount USD/}} >= 50000000 AND DAYS_SINCE({{/Latest Funding Date/}}) <= 540,
   4,
   IF(CONTAINS({{/Funding Stage/}}, "Series B"),
      3,
      IF(CONTAINS({{/Funding Stage/}}, "Series A"),
         2,
         IF(CONTAINS({{/Funding Stage/}}, "Bootstrapped Profitable"),
            1,
            0))))
```

### Column 23. `icp_total`

```clayscript
{{/ICP Fit/}} + {{/ICP Timing/}} + {{/ICP Access/}} + {{/ICP Intent/}} + {{/ICP Budget/}}
```

### Column 24. `lifecycle_stage`

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

### Column 25. `dedup_audit`

```clayscript
TO_JSON({
  "merge_timestamp": NOW(),
  "survivor_company_id": {{/HubSpot Company ID/}},
  "matched_via": {{/Dedupe Match Type/}},
  "merged_from": {{/Duplicate Source IDs/}},
  "confidence_score": {{/Dedupe Confidence/}}
})
```

## Contacts table: abbreviated

Same architecture pattern as Companies. Key columns:

| # | Column | Type | Source / Formula |
|---|---|---|---|
| 1 | hubspot_contact_id | Import | HubSpot Contacts |
| 2 | email | Import + Formula | Strip plus-aliases, lowercase |
| 3 | personal_linkedin_url | Enrichment | Clay: Find Professional Profile (LeadMagic) |
| 4 | dedupe_key_contact | Formula | Prefer email, fallback LinkedIn URL, fallback name+company |
| 5 | email_validated | Enrichment | Clay: Validate Email (LeadMagic) |
| 6 | buyer_role | Formula | Map title to enum (economic / champion / user / procurement) |
| 7 | engagement_score | Lookup | Sum of engagement events in last 30 days |
| 8 | linked_company_id | Lookup | Match domain to Companies table |

### Buyer role mapping formula

```clayscript
IF(CONTAINS_ANY({{/Title/}}, ["CHRO","Chief People","CPO","Chief Human Resources","VP People","VP of People","Head of People"]),
   "economic",
   IF(CONTAINS_ANY({{/Title/}}, ["L&D","Learning","Leadership Development","Talent Management","Manager Development","Coaching"]),
      "champion",
      IF(CONTAINS_ANY({{/Title/}}, ["Manager","Director","Senior","Lead","Head"]),
         "user",
         IF(CONTAINS_ANY({{/Title/}}, ["Procurement","Finance","Legal"]),
            "procurement",
            "unknown"))))
```

## Dedup logic (continuous workflow)

1. New row arrives via HubSpot import
2. `dedupe_key` is computed
3. Conditional check: if `dedupe_key` matches an existing row, set `dedupe_status = "duplicate_pending"`
4. Survivorship rules apply via subroutine:
   - Most non-null fields wins on completeness
   - Most recent activity wins on freshness
   - Oldest `original_source` is preserved
5. Survivor record gets `dedup_audit` JSON written
6. Loser records route to a Clay view `Soft Delete Queue`, archived to Supabase log table after 90 days

**Manual review queue:** Clay view filtered to `dedupe_status = "review_required"` (low-confidence matches). Slack alert to `#revops-review` when queue depth crosses 10.

## Write-back to HubSpot (native integration)

Action: "Update Company in HubSpot" runs after column 25.

Property mapping:

| Clay column | HubSpot property | Type |
|---|---|---|
| icp_fit | `mento__icp_fit` | Number |
| icp_timing | `mento__icp_timing` | Number |
| icp_access | `mento__icp_access` | Number |
| icp_intent | `mento__icp_intent` | Number |
| icp_budget | `mento__icp_budget` | Number |
| icp_total | `mento__icp_total` | Number |
| lifecycle_stage | `lifecyclestage` (standard) | Dropdown |
| dedup_audit | `mento__dedup_audit_json` | Multi-line text |
| signal_summary | `mento__signal_summary` | Multi-line text |

**Update only on change** (Clay toggle ON). Saves HubSpot API quota.
**Rate limit:** 100 records/minute (HubSpot Sales Hub Pro default).

## Monitoring and alerts

| Trigger | Channel | Action |
|---|---|---|
| Row scored `icp_total >= 16` | Slack `#sdr-priority` | DM to assigned SDR with record link |
| Row scored `icp_total` 11-15 | Slack `#sdr-priority` daily digest | Single 9am ET message with table |
| Dedup review queue > 10 | Slack `#revops-review` | 8am ET digest |
| Enrichment confidence < 70 | Clay view | Manual review filter |
| Daily summary | Slack `#gtm-engineering` | Rows processed, lifecycle distribution, ICP total histogram, credit burn |
| Clay credits remaining < 20% of monthly cap | Slack `#gtm-engineering` | Immediate alert |

## Credit and cost budget

### Per-row breakdown

| Operation | Per row | Notes |
|---|---|---|
| Apollo + LinkedIn lookup | 2 credits | Always fires |
| Ocean.io fallback | 0.3 credits | Fires ~30% of the time |
| Crunchbase Latest Funding | 5.8 credits | Always fires |
| Crunchbase Valuation | 11.8 credits | Always fires |
| Find CHRO hire date | 1 credit | Always fires |
| LeadMagic profile + email validate (per contact) | 2 credits | Companies × ~3 contacts = 6 credits |
| **Clay credits per company** | **~22.9** | |
| BuiltWith | $0.05 | |
| Firecrawl (job postings) | $0.02 | |
| G2 Intent | $0.10 | |
| CommonRoom | $0.05 | |
| **External APIs per company** | **~$0.22** | |

### Monthly volume estimate

| Item | Initial backfill (5,000 rows) | Steady state (~500 rows/mo) |
|---|---|---|
| Clay credits | ~115,000 | ~12,000 |
| External APIs | ~$1,100 | ~$110 |

### Plan recommendation

**Clay Explorer at $800/month (100,000 credits)** for ongoing operations after backfill. Use a one-time credit top-up for the initial 5,000-row backfill (~15,000 credits over the monthly cap). After backfill, steady-state monthly burn sits well inside Explorer's allowance.

## Subroutines (reusable)

| Subroutine | Used in | Purpose |
|---|---|---|
| `subroutine_normalize_domain` | Companies, Contacts | Lowercase + strip protocol/www/path |
| `subroutine_normalize_company_name` | Companies, Contacts | Strip suffixes (Inc/Ltd/LLC), strip punctuation |
| `subroutine_count_non_nulls` | Dedup logic | Counts populated fields for survivorship |
| `subroutine_compute_icp_total` | Companies | Sum of five ICP dimensions |
| `subroutine_assign_lifecycle_stage` | Companies | Cascading stage logic |
| `subroutine_map_buyer_role` | Contacts | Title to buyer_role enum |

Built once at the workspace level, called from both tables.

## Rollout plan

| Day | Work |
|---|---|
| 1-2 | Set up HubSpot native imports (Companies + Contacts). Confirm webhook permissions and rate-limit budget. |
| 3-4 | Build Companies table column-by-column. Validate each enrichment against 20 hand-picked Mento ICP accounts (Anthropic, Vercel, Brex, Gusto, 1Password) before scaling. |
| 5-6 | Build Contacts table + buyer_role mapping. Validate against same accounts. |
| 7 | Wire write-back. Run end-to-end on 50 records. Diff against HubSpot. |
| 8-10 | Initial backfill (~5,000 rows). Burn budget monitoring on. |
| 11-12 | Set up Slack alerts, manual review queue, daily digest. |
| 13-14 | Handoff: SDR walkthrough, RevOps walkthrough, Marketing walkthrough. Document gotchas. |

Two-week ship target. Aligns with the 60-day plan from Part 1.
