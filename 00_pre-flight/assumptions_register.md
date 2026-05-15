# 00. Pre-Flight & Assumptions

The brief leaves gaps on purpose. This page lists every confident assumption I'm building from so the reviewer can disagree explicitly and the work below doesn't get misread. Everything here is informed by public Mento sources (mento.co, LinkedIn, Crunchbase, Greenhouse), the day-one Slack-style brief, and standard scale-stage operating norms.

## Tech Stack

1. **HubSpot Sales + Marketing Hub Pro.** Confirmed in brief. Pro tier (not Enterprise) inferred from company stage. Caps custom object count and workflow complexity, which shapes Part 2 design.
2. **Avoma** for call recording, transcripts, post-call summaries. Confirmed in brief.
3. **Greenhouse** for ATS. Confirmed via `boards.greenhouse.io/mento`.
4. **Calendly** for booking. Confirmed via `calendly.com/mento-partners`.
5. **Slack** for internal comms.
6. **Sanity CMS** for the marketing site.
7. **No data warehouse today.** No Snowflake/BigQuery/Databricks/Supabase public signal. HubSpot is the operational source of truth, Avoma is a side system.
8. **No marketing automation beyond HubSpot.** No external evidence.
9. **No dedicated revenue ops tool.** No Gong/Clari/Modjo. Avoma is acting as conversation intelligence.
10. **No CDP.** Not at this stage.

## Sales Motion

1. **Sales team: 2 SDRs.**
2. **Founder-led closing + warm-intro motion.** Executive dinners, warm intros, direct outreach. SDRs prospect and qualify; closing sits with leadership.
3. **No dedicated AE layer yet.** Closing is founder-led. The GTM Engineer fills the infrastructure gap underneath the SDRs.
4. **~5,000 HubSpot contacts** with the four named problems.
5. **~200 target accounts** sitting unworked.
6. **No documented playbook.**

## Product & Pricing

1. **Two tiers: Leadership Coaching and Executive Coaching.** Confirmed on `mento.co/why-mento`.
2. **Per-seat pricing, cohort-tiered.** Larger cohorts get lower per-seat price.
3. **Estimated price points** (for ICP scoring and account-tier math, not pricing strategy):
   - Leadership: ~$4-6k per seat per year
   - Executive: ~$10-18k per seat per year
4. **Typical cohort size:** 10-50 seats. Land deals likely 10-25.
5. **Estimated ACV band:** $40k-$300k. Most early enterprise lands ~$50k-$120k.
6. **Time to live: 2 weeks from signing.** Confirmed in FAQ.
7. **AI layer "Moments"** handles session summaries, multi-session insights, personalised session prep.

## ICP (Carrying Into Part 2 and Part 3)

1. **Size band: 500-5,000 employees.** Confirmed in brief.
2. **Sector: B2B tech, primarily SaaS and AI-native.** Inferred from customer roster.
3. **Stage: Series B/C or later, profitable scale-ups, public-track late-stage.**
4. **Geography: US-headquartered, English-speaking.** Coach roster signals US-first delivery.
5. **Negative ICP:** sub-200 headcount (no L&D budget), traditional non-tech enterprises (long procurement, low fit), agencies/services firms (different leverage profile), regulated finance/government (sales cycle kills the motion at Mento's stage).

## Buying Committee (Part 2 ICP Scoring and Part 3 Routing Depend on This)

1. **Economic buyer:** CHRO, CPO, VP People, Head of People.
2. **Champion:** Head of L&D, Head of Talent Management, Head of Manager Development, Head of Learning, Senior Manager People Operations.
3. **End user:** managers, directors, senior ICs, executives in the cohort.
4. **Procurement:** Finance, Legal. Touch deals over ~$75k ACV.
5. **Buyer trigger context:** demand spikes when companies hit inflection points (Series B/C, headcount sprint, new People exec, L&D hire). Coaching is rarely the budget line that gets cut.

## Out-of-Scope For This Exercise

1. **No live HubSpot access.** Part 2 work is designed to be portable into a real instance via a property scaffolder script.
2. **No live Clay workspace.** Part 2 and Part 3 Clay builds are documented as if I'm handing a build doc to a Clay engineer who can stand it up in 1-2 days.
3. **No production credentials for any vendor.** Build docs reference API contracts only.
4. **No Avoma transcript corpus to mine.** Part 1 mentions Avoma as a discovery dependency but doesn't depend on it for the v1 build.

## Things I'd Verify in Week 1 (Not Assumed, Captured for Part 1)

These are gaps the case study can't close without real conversations. They appear in Part 1's week-one discovery list.

- Exact HubSpot tier and seat count
- Avoma retention policy and transcript export rights
- Actual cohort price points and historical close rates
- SDR quota and segmentation
- Marketing budget and current spend mix
- Existing partner/agency relationships
- Procurement and security review obligations for enterprise buyers
