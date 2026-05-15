# Submission Index — Mento GTM Engineer Case Study

**Candidate.** Jared Burke
**Date.** May 2026
**Live submission.** [Mento: GTM Engineer Case Study (Notion)](https://www.notion.so/3607642d57d781ce9c16f0541f6992ef) — reviewer-facing canonical page.
**Code home.** [github.com/gitgitbangbang/mento-gtme-case-study](https://github.com/gitgitbangbang/mento-gtme-case-study) (this repo).

This page is the one-stop index of everything I've shipped. Use the Reading Order below if you're skimming; use the full Artifact Map if you want every file in one place.

---

## Status

| Item | Status |
|---|---|
| Part 1 — Diagnose & Prioritize | ✓ merged to `main` |
| Part 2 — Data Foundation Plan + Clay build | ✓ merged to `main` |
| Part 3 — Buying Signal Workflow (docs) | ✓ merged to `main` |
| Part 3 — Working Python build (Claude Code) | ✓ merged via [PR #1](https://github.com/gitgitbangbang/mento-gtme-case-study/pull/1) |
| Continuous integration on the build (ruff + mypy + pytest) | ✓ green on `main` |
| Test coverage on the deterministic core | ~94% |
| Branch protection on `main` | active (CI required, force-push + deletion blocked) |
| End-to-end live verification on a clean clone | ✓ passed (10-minute walkthrough) |

---

## Reading Order

If you have **15 minutes**: read the Notion page, then run the 10-minute build verification at [`03_signal_workflow/build/README.md`](../03_signal_workflow/build/README.md#verification-walkthrough--7-steps-in-10-minutes).

If you have **60 minutes**: do all of the above plus read the four Part 3 docs in order.

If you have **2 hours**: read every part start to finish, top to bottom.

1. **[`00_pre-flight/assumptions_register.md`](../00_pre-flight/assumptions_register.md)** — what I assumed before answering.
2. **[`01_diagnose_prioritize/01_diagnose_prioritize.md`](../01_diagnose_prioritize/01_diagnose_prioritize.md)** — Part 1: 60-day priorities, week-1 discovery, the risk register.
3. **[`02_data_foundation/02_data_foundation.md`](../02_data_foundation/02_data_foundation.md)** — Part 2: dedupe, enrichment waterfalls, ICP scoring, lifecycle. Pair with the [interactive data model](../02_data_foundation/data_model.html).
4. **[`02_data_foundation/clay_build/02_clay_board_build.md`](../02_data_foundation/clay_build/02_clay_board_build.md)** — Part 2 operationalised in Clay (three-table board).
5. **[`03_signal_workflow/03_workflow_architecture_text.md`](../03_signal_workflow/03_workflow_architecture_text.md)** — Part 3: five-stage workflow, AI vs deterministic boundary, HITL.
6. **[`03_signal_workflow/03_signal_scoring_framework.md`](../03_signal_workflow/03_signal_scoring_framework.md)** — scoring formula, base weights, routing tiers, self-improvement loop.
7. **[`03_signal_workflow/03_outreach_drafts.md`](../03_signal_workflow/03_outreach_drafts.md)** — four signal-specific templates + the agent prompt and Strong-Hook Gate.
8. **[`03_signal_workflow/build/`](../03_signal_workflow/build/)** — Part 3 as runnable Python. Start with its [README](../03_signal_workflow/build/README.md) and the [verification walkthrough](../03_signal_workflow/build/README.md#verification-walkthrough--7-steps-in-10-minutes).

---

## Artifact Map

| # | What | Path | Format |
|---|---|---|---|
| 1 | Assumptions register | [`00_pre-flight/assumptions_register.md`](../00_pre-flight/assumptions_register.md) | Markdown |
| 2 | Part 1 — Diagnose & Prioritize | [`01_diagnose_prioritize/01_diagnose_prioritize.md`](../01_diagnose_prioritize/01_diagnose_prioritize.md) | Markdown |
| 3 | Part 2 — Data Foundation prose | [`02_data_foundation/02_data_foundation.md`](../02_data_foundation/02_data_foundation.md) | Markdown |
| 4 | Part 2 — Interactive data model | [`02_data_foundation/data_model.html`](../02_data_foundation/data_model.html) | Self-contained HTML (Mermaid + Mento brand) |
| 5 | Part 2 — Clay board build doc | [`02_data_foundation/clay_build/02_clay_board_build.md`](../02_data_foundation/clay_build/02_clay_board_build.md) | Markdown |
| 6 | Part 3 — Workflow architecture | [`03_signal_workflow/03_workflow_architecture_text.md`](../03_signal_workflow/03_workflow_architecture_text.md) | Markdown |
| 7 | Part 3 — Signal scoring framework | [`03_signal_workflow/03_signal_scoring_framework.md`](../03_signal_workflow/03_signal_scoring_framework.md) | Markdown |
| 8 | Part 3 — Outreach drafts (4 templates) | [`03_signal_workflow/03_outreach_drafts.md`](../03_signal_workflow/03_outreach_drafts.md) | Markdown |
| 9 | Part 3 — Interactive workflow diagram | [`03_signal_workflow/workflow_diagram.html`](../03_signal_workflow/workflow_diagram.html) | Self-contained HTML |
| 10 | Part 3 — Working Python build | [`03_signal_workflow/build/`](../03_signal_workflow/build/) | Python 3.12 / uv project |
| 11 | Part 3 — Build README + verification walkthrough | [`03_signal_workflow/build/README.md`](../03_signal_workflow/build/README.md) | Markdown |
| 12 | Part 3 — Captured live runs (4 signals) | [`03_signal_workflow/build/examples/`](../03_signal_workflow/build/examples/) | Plain text |
| 13 | Part 3 — Merge PR for the working build | [PR #1](https://github.com/gitgitbangbang/mento-gtme-case-study/pull/1) | GitHub PR (merged) |
| 14 | CI workflow | [`.github/workflows/build-ci.yml`](../.github/workflows/build-ci.yml) | YAML |

---

## How to Verify the Working Build

The Part 3 deliverable that's hardest to evaluate from prose alone is the working Python build. It's a runnable signal engine implementing exactly what the three Part 3 docs describe.

There's a **10-minute, 7-step verification walkthrough** at the top of [`03_signal_workflow/build/README.md`](../03_signal_workflow/build/README.md#verification-walkthrough--7-steps-in-10-minutes). Each step gives the command, what it does in plain English, the expected output, and what it proves.

What that walkthrough verifies, end to end on a clean clone:

1. The build installs reproducibly from a lockfile (no "works on my machine")
2. The deterministic core — scoring formula, P1/P2/P3 routing — has 57 automated tests passing at ~94% coverage
3. A funding signal flows through detection → enrichment → scoring → routing exactly per the spec
4. The Personalisation Agent, Strong-Hook Gate, and Draft Assembly Agent are real Claude API calls (not pre-canned strings — you can see hook text vary across runs)
5. Every run leaves a complete audit JSON the SDR / RevOps team can read

Captured outputs from a recent live run sit in [`03_signal_workflow/build/examples/`](../03_signal_workflow/build/examples/) for reference.

---

## What's Real vs What's Mocked

Roughly **65% real working code, 35% mocked**. Mocking is concentrated at external API boundaries.

**Real:** scoring formula, routing tiers, Personalisation Agent (real Claude API), Strong-Hook Gate, Draft Assembly Agent, CLI HITL prompt, JSON audit logging, full pytest suite.

**Mocked:** signal detection (would call Crunchbase / LinkedIn-Apify / Greenhouse / Lever / Firecrawl / Clearbit / PDL), company + contact enrichment (Apollo / Ocean.io / ZoomInfo / LeadMagic / BuiltWith), HubSpot lookup + write, Slack DM delivery, Smartlead campaign trigger.

Every mock carries a `# STUB:` comment in code with a one-line note on the production replacement.

Full breakdown in [`03_signal_workflow/build/README.md`](../03_signal_workflow/build/README.md#whats-real-whats-mocked).

---

## Engagement Model Mapping

For each deliverable, the engagement model that would make most sense if Mento were buying this work as a service from Pyrashyut:

| Deliverable | Model |
|---|---|
| Part 1 strategy + Part 2 data plan | **Consultancy** — strategic guidance, Mento implements |
| Part 2 Clay build (data foundation) | **Done-For-You** — Pyrashyut builds + hands off |
| Part 3 signal engine (code build) | **Hybrid** — strategy + execution; ongoing maintenance + recalibration of base weights |

---

## Contact

**Jared Burke** — jared@pyrashyut.com — [pyrashyut.com](https://pyrashyut.com)

Pyrashyut LLC | GTM Engineering As A Service | Tbilisi, Georgia
