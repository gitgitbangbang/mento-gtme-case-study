# 01. Diagnose & Prioritize

## Q1. The first three things, and why in that order

### 1. Clean the data foundation and confirm attribution tracking

Multiple source leads are sitting in the same place with no structure. That's the obvious problem. The non-obvious one is whether attribution is actually working today. You know your channels (events, inbound, referrals, outbound). You don't yet know whether HubSpot is correctly attributing each lead to its true source. I would ship the new system quickly, though I would want to gather information along the way to understand what would need to be addressed and iterated later to ensure every downstream measurement is eventually accounted for.

**How this looks.** Quick HubSpot data structure stood up first. Standardised schema on Contact, Company, Deal with custom properties for ICP score, signal type, signal date, lifecycle stage, and a dedup audit trail. Dedup on `company_domain` + `normalized_company_name` with email as tiebreaker, survivorship favouring most-non-null + most-recent activity. Enrichment waterfall (Clay) via Apollo API, Ocean.io API, Crunchbase API, LinkedIn API via Clay, confidence-scored with an AI tiebreaker for low-confidence matches. ICP score (0-100) written back as a HubSpot custom property. Lifecycle stages redefined with explicit entry and exit rules in HubSpot workflows. Attribution gaps observed and logged for v2, not blocked on for v1.

### 2. Audit Avoma to HubSpot dataflow feasibility

Avoma holds Mento's richest first-party signal data. Call transcripts, buyer language, objection patterns, expansion clues. If that data can't get into HubSpot cleanly, the signal engine in step 3 loses half its leverage. Answer this before committing to architecture in step 3. If Avoma's native HubSpot integration can't push transcript metadata or call-outcome fields reliably, a workaround is designed in upfront, not retrofitted.

**How this looks.** Review Avoma native integrations, API and webhook endpoints, rate limits, transcript export rights, deal-event hooks. HubSpot bi-directional mapping defining which Avoma fields land on which custom properties at Contact/Company/Deal. Fallback path scoped in case native is weak: n8n or a custom Node middleware exposing an MCP server so AI agents can read transcripts at draft time. Output is a one-page decision doc that picks the integration path with named tools and tradeoffs.

### 3. Build the agentic outbound engine on the 200 target accounts

The 200 accounts already exist as a list. Data hygiene there is solvable whether it's rich or not (assumption not) because we control the inputs and enrichment methods. Parallel workstream is supporting the SDRs on ICP definition, intent-signal weighting, deal scoring, and deal intelligence so they trust the system on day one.

**How this looks.** Clay orchestrates the v1 pipeline. Signal detection pulls from Crunchbase, LinkedIn (Apify), Firecrawl, BuiltWith, G2 Buyer Intent, RB2B, and CommonRoom via their APIs into a Clay account intake table. Enrichment waterfall inside Clay: FullEnrich primary, LeadMagic for verification, Prospeo and FindyMail as fallbacks, Clay's native APIs for firmographic depth. Verified email or skip, never pattern-guessed. Five-dimension ICP scoring (Fit, Timing, Access, Intent, Budget) weighted in Clay formulas. AI agents handle the non-deterministic work. A **personalisation agent** generates three hooks per prospect from the trigger event, recent LinkedIn activity, tech stack, and company news, with strong-hook gating (no strong hook means manual review queue, not a generic email). A **lead-management agent** maintains the prospect record, runs deal scoring against the signal-plus-ICP combination, and routes qualified leads into HubSpot as Deals. A **sequence-routing agent** picks the right Smartlead or Instantly campaign by signal type and score. Smartlead and Instantly handle domain rotation, SPF/DKIM/DMARC, and warm-up. The SDR reviews and approves the opener draft inside Slack before sequence kickoff. Replies webhook back into HubSpot where an **inbox-management agent** classifies intent, drafts the response, and books meetings via HubSpot Calendar with calls held on Avoma. The agent runs autonomously and only flags the SDR in Slack with emoji-based approval prompts when a case needs manual review or falls outside the provided parameters and guidelines. Thresholds are deterministic (scoring, routing); context-sensitive work is agentic (drafting, classification, booking). Monthly batch job feeds closed-won and closed-lost outcomes back into Clay's scoring weights so the ICP sharpens itself.

---

## Q2. What I'd gather in week one

Assuming no delays in immediate tech stack access, and with the understanding that not all information blocks shipping.

**1. State of attribution tracking.** Is HubSpot correctly tagging original source vs latest source on every contact today? Where do UTMs land, how is the GTM container configured, and what's the source-of-truth dictionary across events, inbound, referrals, and outbound? Where are the gaps and how visible are they to the team?

**2. Avoma integration and rate-limit capabilities.** Native HubSpot integration depth, API and webhook endpoints, transcript export rights, rate limits, deal-event hooks, MCP-friendliness. This is the input that decides Priority 2.

**3. The 200-account list's hygiene state.** How fresh is the list, where did it come from, and when was it last touched? What datapoints exist per account today (firmographic, technographic, contact-level, signal history)? Without this baseline, the engine in Priority 3 has no reliable surface to score against.

**4. ICP work to date.** How much strategy already exists? How many ICP layers and sublayers (industry, size band, stage, persona, geography, buying committee, negative ICP)? Is it written down or living in someone's head? The engine has to align to the actual ICP, not my reconstruction of it.

**5. Lead magnets in market.** What has marketing built (gated content, calculators, ROI tools, webinars, peer events)? What converts, what's dead? Lead magnets feed bridgebound plays and inbound-to-outbound conversion paths; the engine should route around them, not duplicate them.

**6. Rep account split.** How are the two SDRs splitting effort today? Are accounts owned by named rep, segment, geography, or unassigned? What's the routing logic when a signal fires on an unowned account? This is the spec for Priority 3's routing rules.

**7. What "working in 60 days" means in numbers.** Both SDRs on where time leaks and which signals they intuit today. Head of Coach Ops on cohort onboarding and expansion patterns. Marketing lead on attribution and spend. Three named customers (Anthropic, Vercel, Brex) on how they bought and what triggered the conversation.

**8. Parallel audits.** HubSpot data quality (dupe rate, null rate per field, lifecycle distribution, deal velocity by source). ICP retrospective on closed-won. Target account list staleness check.

**9. Exact HubSpot tier and seat count**

**10. SDR quota and segmentation**

**11. Marketing budget and current spend mix**

**12. Procurement and security review obligations for enterprise buyers**

---

## Q3. The biggest risk to 60 days

**Misalignment on the definition of "working."** Not the technical build. What "working" means to the team from a conversion and metric sense.

**SDR adoption.** Mitigation is shipping with them, measuring their skip and edit rates per signal weekly, and feeding that back into scoring v2.

These are the two points that first come to mind. Beyond this, I legitimately see no barrier to getting something working in 60 days. 60 days is more than fair to stand up a v1 working outbound system.
