# Part 2. Data Foundation Plan

## (a) Dedupe and merge logic

The dedupe runs as a one-off cleanup pass followed by a continuous workflow that catches new duplicates as they land.

**Matching keys in priority order.** The brief points at ~5,000 contact-level records, so the matching is contact-first. Primary match on `email` (lowercase, strip plus-aliases like `+marketing` so the same buyer doesn't appear five times). Secondary match on `personal_linkedin_url` (normalised, lowercase, strip trailing slash, strip query params). Tertiary on first-name + last-name fuzzy match (Levenshtein) **scoped within the same company**, so John Smith at Anthropic only collapses with another John Smith at Anthropic, never with John Smith at Stripe.

**Company-level grouping** runs in parallel so contacts attach to the right Company record. Primary match on `company_linkedin_url` (LinkedIn company IDs are stable even when domains aren't, and Clay has native enrichment that resolves a domain to its LinkedIn URL). Secondary on `normalized_company_domain` (lowercase, strip `www.`, root domain only, so `go.anthropic.com` collapses to `anthropic.com`). Tertiary on `normalized_company_name` with a tight Levenshtein threshold (strip suffixes like Inc/Ltd/LLC, strip punctuation) so Mento, Mento Inc, and Mento.co collapse without false-merging unrelated names.

**Survivorship rules.** The record with the most non-null fields wins on completeness. The record with activity in the last 90 days wins on freshness. The original `original_source` value inherits from the **oldest** record so attribution isn't rewritten by a merge. Lifecycle stage takes the most-advanced value (a Customer always beats an MQL). Engagement history is unioned across all merged records. ICP score and any computed fields are re-computed post-merge, never inherited.

**Audit trail.** Every merge writes a `dedup_audit` JSON property on the surviving HubSpot record with timestamp, merging tool, survivor ID, source IDs, and the matching rule that fired. Soft-deleted records archive to an SQL db (e.g. Supabase) log table for 90 days before hard delete, so a wrongful merge can be reversed.

## (b) Enrichment sources and waterfall

Three layers, sequenced. Firmographic first, then technographic, then contact-level with email verification at the end. Each step writes a confidence score. Below 70 = manual review queue. Conflicting data triggers an AI tiebreaker (Claude API or Mistral, called from Clay's native Use AI columns) that looks at the most recent press release or LinkedIn headcount badge to pick the truer value. Email is never pattern-guessed. Verified or skipped.

All orchestrated in Clay or via Claude Code.

**Layer 1. Firmographic.** Apollo.io first inside Clay (native, paid via Clay credits) for breadth and cost-per-contact at Mento's volume. Ocean.io second for size, stage, and industry validation (US-focused, strong on Series B/C scale-ups which is exactly Mento's ICP). Crunchbase third, called inside Clay via the **Company Latest Funding** and **Company Valuation** enrichments (Clay credits), for funding history, latest round, and valuation. Crunchbase is the only reliable source for the "Series B/C funding in the last 90 days" trigger in Part 3. From there a trail waterfall inside Clay across **Claygent**, **Clearbit**, **Datagma**, **ZoomInfo**, **People Data Labs**, and **Lusha**, most consumable on Clay credits so a single procurement line covers the bulk of the stack.

**Layer 2. Technographic.** BuiltWith for the prospect's HR tech stack (Workday, BambooHR, Lattice, Culture Amp). Strong proxy for L&D maturity and budget. A company already running Lattice is a higher-fit coaching buyer than one running a homegrown Notion doc.

**Layer 3. Contact-level.** LinkedIn data flows through Clay's **Person Current Company** and **Find Professional Profile** (LeadMagic) enrichments for org chart, exec changes, and role tenures. **FullEnrich**, **LeadMagic** (Find Work Email, Find Personal Email), **Prospeo**, and **FindyMail** run as the email-discovery waterfall when the primary lookup doesn't surface a working address. **LeadMagic Validate Email** does the final verification before any contact gets pushed outbound. Clay's **Find Contacts at Company** surfaces buying-committee contacts (CHRO, CPO, Head of L&D, Head of Talent) at no marginal sourcing effort once the Company record is enriched.

**Why these tools, not others.** Clay is the orchestration layer for one specific reason. It ships with 30+ enrichment integrations natively, and most of them are payable from a single Clay credit balance. A 9-source waterfall doesn't require 9 separate procurement processes, 9 vendor contracts, or 9 API key rotations. **Apollo, Clearbit, Datagma, ZoomInfo, People Data Labs, RocketReach, Surfe, LeadIQ, LeadMagic, Icypeas, Store Leads, and Crunchbase all run on Clay credits**, which means the GTM Engineer sets a credit budget once and the team gets a flexible 12-source stack underneath it. Tools outside Clay's credit system, including **BuiltWith** for technographic data, **Apify** for any LinkedIn pulls that go beyond Clay's native paths, **FullEnrich**, **Prospeo**, and **FindyMail**, get standalone API keys but wire into the same Clay table as HTTP-API columns, so the orchestration layer stays unified. The AI tiebreaker runs as a Clay **Use AI** column calling Claude or Mistral, which means even the LLM step lives one column away from the enrichment data, not in a separate service. That keeps the whole pipeline observable and editable from a single surface, which is the difference between v1 shipping in 2 weeks and v1 shipping in 8.

## (c) ICP scoring model

Five dimensions, each scored 0-4. Max score 20. Score 16+ is High, 11-15 is Medium, 6-10 is Low, 5 or below is Park. Five dimensions instead of one weighted formula because each one is independently actionable. A high-Fit + low-Timing account belongs in nurture. A high-Timing + low-Fit account gets disqualified fast. A single composite score hides that nuance.

**Dimension 1. Fit (0-4).** One point each for: headcount in the 500-5,000 band, B2B tech sector, Series B or later, identified HR tech stack present. Headcount outside the band zeroes the dimension regardless of the other three. Fit is necessary but not sufficient. Most teams over-weight it.

**Dimension 2. Timing (0-4).** Highest-leverage dimension at Mento's stage. Companies don't buy coaching on a steady-state schedule. They buy when they hit an inflection point. 4 = funding announcement in the last 30 days. 3 = new CHRO/CPO in the last 60 days. 2 = 20%+ headcount growth in 6 months. 1 = active "Leadership Development" or "L&D Manager" job posting. 0 = no trigger.

**Dimension 3. Access (0-4).** 4 = CHRO/CPO with engagement history already in HubSpot. 3 = CHRO/CPO present but no engagement. 2 = Head of L&D or Talent. 1 = generic HR contact. 0 = no relevant contact at all. Access matters because Mento sells to People executives, not HR generalists, and having the right buyer already in the system shortens the cycle.

**Dimension 4. Intent (0-4).** Recency-decayed composite across G2 Buyer Intent activity, CommonRoom community engagement, RB2B website visits, and content engagement on mento.co. Each source contributes weighted points, with a half-life of 30 days so stale intent doesn't count.

**Dimension 5. Budget (0-4).** Funding stage as a proxy for spend approval. 4 = recent Series C or later ($50M+ raised in 18 months). 3 = Series B. 2 = late-stage Series A. 1 = bootstrapped profitable. 0 = pre-revenue or unknown. Budget captures whether a willing buyer can actually approve the spend.

**Where this lives in HubSpot.** Each dimension stores as a custom Number property on the Company record. The total is a computed property. Routing rules in Part 3 fire off the total. When the model needs adjustment, the weights are config, not code, so updates ship in minutes instead of days.

## (d) Lifecycle stage architecture

Current state has contacts scattered across Lead, MQL, and Customer with no rules. The fix puts deterministic entry and exit rules on each stage and adds the Expansion and Dormant stages that don't exist today.

**Stage architecture (left to right).** Subscriber → Lead → MQL → SQL → Opportunity → Customer → Expansion / Dormant.

**Subscriber.** Entry: any form fill or content download with no qualifying action behind it. Exit to Lead: ICP Fit ≥ 2 AND any engagement event in the last 30 days.

**Lead.** Entry: ICP Fit ≥ 2 plus recent engagement. Exit to MQL: ICP Total ≥ 11 (Medium or higher).

**MQL.** Entry: ICP Total ≥ 11 AND Timing ≥ 2 (an active trigger event exists). Exit to SQL: SDR manually confirms qualification in HubSpot AND a meeting is booked. The manual SDR flag is the deliberate human-in-the-loop at the fragile judgment call.

**SQL.** Entry: SDR-qualified, meeting on the calendar. Exit to Opportunity: founder or AE accepts the deal and creates a HubSpot Deal record.

**Opportunity.** Entry: Deal record exists. Exit to Customer: Deal stage moves to Closed Won.

**Customer.** Entry: Deal Closed Won, contract signed. Exit to Expansion: a new Deal opens on the same Company. Exit to Dormant: cohort completes without renewal AND no engagement for 90 days.

**Expansion.** Entry: new Deal opened on an existing Customer Company (additional cohort, new business unit, tier upgrade). Same exit logic as Opportunity.

**Dormant.** Entry: cohort complete + no renewal + 90-day engagement silence. Exit back to Lead: any re-engagement event (form fill, exec change detected, signal trigger fires).

**Why this architecture.** Every stage has a deterministic entry and exit rule so transitions aren't vibes. The ICP score is the gate between Subscriber → Lead → MQL, which means lifecycle finally means something instead of being a label. The Customer → Expansion stage is the one most SaaS companies forget. Adding it turns expansion into a measurable motion rather than a side effect.

## Data Model

Live Version via GitHub Pages 📊: [data_model.html](https://gitgitbangbang.github.io/mento-gtme-case-study/02_data_foundation/data_model.html)

Static SQL Render:

```sql
-- HubSpot data model: six entities, Company is the spine
-- Convention: PI = Primary Record ID, AI = Associated Record ID

CREATE TABLE company (
    company_id            VARCHAR PRIMARY KEY,    -- PI
    company_linkedin_url  VARCHAR,
    normalized_domain     VARCHAR,
    company_name          VARCHAR,
    headcount             INTEGER,
    funding_stage         VARCHAR,
    hr_tech_stack         VARCHAR,
    icp_fit               INTEGER,
    icp_timing            INTEGER,
    icp_access            INTEGER,
    icp_intent            INTEGER,
    icp_budget            INTEGER,
    icp_total             INTEGER,
    lifecycle_stage       VARCHAR,
    dedup_audit           JSON
);

CREATE TABLE contact (
    contact_id            VARCHAR PRIMARY KEY,                     -- PI
    company_id            VARCHAR REFERENCES company(company_id),  -- AI
    email                 VARCHAR,
    personal_linkedin_url VARCHAR,
    first_name            VARCHAR,
    last_name             VARCHAR,
    title                 VARCHAR,
    buyer_role            VARCHAR,
    original_source       VARCHAR,
    engagement_score      INTEGER
);

CREATE TABLE deal (
    deal_id               VARCHAR PRIMARY KEY,                              -- PI
    company_id            VARCHAR REFERENCES company(company_id),           -- AI
    deal_stage            VARCHAR,
    tier                  VARCHAR,
    seats                 INTEGER,
    acv                   NUMERIC,
    expected_close        DATE,
    triggering_signal_id  VARCHAR REFERENCES signal_event(signal_id)        -- AI
);

CREATE TABLE cohort (
    cohort_id             VARCHAR PRIMARY KEY,                     -- PI
    deal_id               VARCHAR REFERENCES deal(deal_id),        -- AI
    company_id            VARCHAR REFERENCES company(company_id),  -- AI
    start_date            DATE,
    seat_count            INTEGER,
    nps_score             NUMERIC,
    expansion_signals     INTEGER,
    renewal_status        VARCHAR
);

CREATE TABLE signal_event (
    signal_id             VARCHAR PRIMARY KEY,                     -- PI
    company_id            VARCHAR REFERENCES company(company_id),  -- AI
    signal_type           VARCHAR,
    signal_source         VARCHAR,
    signal_date           DATE,
    signal_weight         INTEGER,
    ai_drafted            BOOLEAN
);

CREATE TABLE engagement (
    engagement_id         VARCHAR PRIMARY KEY,                     -- PI
    contact_id            VARCHAR REFERENCES contact(contact_id),  -- AI
    company_id            VARCHAR REFERENCES company(company_id),  -- AI
    channel               VARCHAR,
    timestamp             TIMESTAMP,
    direction             VARCHAR,
    avoma_transcript_id   VARCHAR
);
```

## Lifecycle State Machine

```sql
-- Lifecycle state transitions: deterministic rules, not vibes
-- One row per allowed transition with its trigger condition

CREATE TABLE lifecycle_transition (
    from_stage    VARCHAR,
    to_stage      VARCHAR,
    trigger_rule  VARCHAR,
    PRIMARY KEY (from_stage, to_stage)
);

INSERT INTO lifecycle_transition (from_stage, to_stage, trigger_rule) VALUES
    (NULL,          'Subscriber',  'New record, no qualifying action'),
    ('Subscriber',  'Lead',        'ICP Fit >= 2 AND engagement event in last 30d'),
    ('Lead',        'MQL',         'ICP Total >= 11'),
    ('MQL',         'SQL',         'SDR confirms qualification AND meeting booked'),
    ('SQL',         'Opportunity', 'Founder or AE accepts; Deal record created'),
    ('Opportunity', 'Customer',    'Deal Closed Won'),
    ('Customer',    'Expansion',   'New Deal opened on same Company'),
    ('Customer',    'Dormant',     'Cohort complete AND no renewal AND 90d silence'),
    ('Expansion',   'Customer',    'Deal Closed Won'),
    ('Dormant',     'Lead',        'Re-engagement event (form fill, exec change, signal)');
```
