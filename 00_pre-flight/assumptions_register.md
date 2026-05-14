# Assumptions Register

**Mento GTME Case Study. Jared Burke**
**Last updated:** 2026-05-14

The brief leaves gaps on purpose. This doc lists every confident assumption I'm building from so the reviewer can disagree explicitly and so the work below doesn't get misread. Everything here is informed by public Mento sources (mento.co, LinkedIn, Crunchbase, Greenhouse), the Slack-style brief on day one, and standard scale-stage operating norms.

## Company & Stage

1. **ARR band: $10-15M.** Inferred from ~87 employees on LinkedIn, premium per-seat pricing across two tiers, ~50+ named enterprise customer logos visible, and reported 3x revenue growth YoY. Sanity check against typical seed-extension benchmarks at this headcount.
2. **Funding stage: post-seed, pre-Series A.** $5.5M seed disclosed (Twelve Below, 186 Ventures, M13, Bossa Invest). Hiring patterns and product investment in AI ("Moments") suggest active fundraise prep.
3. **HQ: New York, NY. Remote-first team.** Coach roster is global.
4. **Co-CEO: Jamie Albers** (still in seat as of latest public signal).

## Tech Stack (assumed installed and writable)

5. **HubSpot Sales + Marketing Hub Pro.** Confirmed by the brief. I assume Pro tier (not Enterprise) based on company stage. This caps custom object count and workflow complexity, which affects Part 2 design.
6. **Avoma** for call recording, transcript, and post-call summaries. Confirmed by the brief.
7. **Greenhouse** for ATS. Confirmed by `boards.greenhouse.io/mento`.
8. **Calendly** for booking. Confirmed by `calendly.com/mento-partners`.
9. **Slack** for internal comms (confirmed via brief framing).
10. **Sanity CMS** for the marketing site (confirmed in page metadata).
11. **No data warehouse today.** No Snowflake/BigQuery/Databricks signal anywhere public. Assume HubSpot is the operational source of truth and Avoma is a side system.
12. **No marketing automation beyond HubSpot.** Mailchimp/Customer.io are not in evidence.
13. **No dedicated revenue ops tool** (no Gong, no Clari, no Modjo). Avoma is acting as the conversation intelligence layer.
14. **No CDP.** Not at this stage.

## Sales Motion (current state, per brief)

15. **Sales team: 2 SDRs.** Confirmed in the brief.
16. **Founder-led closing + warm-intro motion.** Confirmed in brief framing (executive dinners, warm intros, direct outreach). SDRs prospect and qualify; closing sits with leadership.
17. **No dedicated AE layer yet.** Closing is founder-led. The GTM Engineer fills the infrastructure gap underneath the SDRs.
18. **~5,000 HubSpot contacts** with the four named problems. Confirmed in Part 2 brief.
19. **~200 target accounts** sitting unworked. Confirmed in brief.
20. **No documented playbook.** Confirmed in brief.

## Product & Pricing

21. **Two tiers: Leadership Coaching and Executive Coaching.** Confirmed on mento.co/why-mento.
22. **Per-seat pricing, cohort-tiered.** Confirmed in FAQ. Larger cohorts get lower per-seat price.
23. **Estimated price points** (for ICP scoring and account-tier math, not for pricing strategy):
    - Leadership: ~$4-6k per seat per year
    - Executive: ~$10-18k per seat per year
24. **Typical cohort size:** 10-50 seats. Land deals likely 10-25.
25. **Estimated ACV band:** $40k-$300k. Most early enterprise lands ~$50k-$120k.
26. **Time to live: 2 weeks from signing.** Confirmed in FAQ.
27. **AI layer "Moments"** handles session summaries, multi-session insights, personalised session prep. Public.

## ICP (carrying into Part 2 and Part 3)

28. **Size band: 500-5,000 employees.** Confirmed in brief.
29. **Sector: B2B tech, primarily SaaS and AI-native.** Inferred from customer roster.
30. **Stage: Series B/C or later, profitable scale-ups, public-track late-stage.** Confirmed in brief and customer roster.
31. **Geography: US-headquartered, English-speaking.** Coach roster signals US-first delivery.
32. **Negative ICP:** Sub-200 headcount (no L&D budget), traditional non-tech enterprises (long procurement, low fit), agencies/services firms (different leverage profile), regulated finance/government (sales cycle kills the motion at this stage).

## Buying Committee (Part 2 ICP scoring and Part 3 routing depend on this)

33. **Economic buyer:** CHRO, CPO, VP People, Head of People. They sign the contract.
34. **Champion:** Head of L&D, Head of Talent Management, Head of Manager Development, Head of Learning, Senior Manager People Operations. They run the program.
35. **End user:** managers, directors, senior ICs, executives in the cohort.
36. **Procurement:** Finance, Legal. Touch deals over ~$75k ACV.
37. **Buyer trigger context:** demand spikes when companies hit inflection points the brief named (Series B/C, headcount sprint, new People exec, L&D hire). Coaching is rarely the budget line that gets cut.

## Out-of-Scope For This Exercise

38. **No live HubSpot access.** All Part 2 work is designed to be portable into a real instance via the property scaffolder in Task 6.
39. **No live Clay workspace.** All Part 2 and Part 3 Clay builds are documented as if I'm handing a build doc to a Clay engineer who can stand it up in 1-2 days.
40. **No production credentials for any vendor.** Code briefs reference API contracts only.
41. **No Avoma transcript corpus to mine.** Part 1 mentions Avoma as a discovery dependency but doesn't depend on it for the v1 build.

## Things I'd Verify in Week 1 (not assumed, captured for Part 1)

These are gaps the case study can't close without real conversations. They appear in Part 1's week-one discovery list, not here.

- Exact HubSpot tier and seat count
- Avoma retention policy and transcript export rights
- Actual cohort price points and historical close rates
- SDR quota and segmentation
- Marketing budget and current spend mix
- Existing partner/agency relationships
- Procurement and security review obligations for enterprise buyers
