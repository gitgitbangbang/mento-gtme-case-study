# Mento GTM Engineer Case Study

Take-home case study response for the GTM Engineer role at [Mento](https://www.mento.co).

**Candidate.** Jared Burke
**Date.** May 2026
**Live submission.** [Mento: GTM Engineer Case Study (Notion)](https://www.notion.so/3607642d57d781ce9c16f0541f6992ef)

## Structure

```
.
├── 00_pre-flight/                  Assumptions register
├── 01_diagnose_prioritize/         Part 1. Diagnose & Prioritize
├── 02_data_foundation/             Part 2. Data Foundation Plan
│   ├── 02_data_foundation.md       Prose answer to brief's four asks
│   ├── data_model.html             Interactive data model + lifecycle diagram
│   └── clay_build/
│       └── 02_clay_board_build.md  Three-table Clay board build doc
├── 03_signal_workflow/             Part 3. Buying Signal Workflow (in progress)
│   ├── clay_build/
│   └── outreach_drafts/
└── 99_submission/                  Submission index
```

## Live Artifacts

- **[data_model.html](./02_data_foundation/data_model.html)**. Interactive entity diagram + lifecycle state machine, branded to Mento's design system. Built with Mermaid + Mento's coral/sage palette + Hanken Grotesk typography.

Once GitHub Pages is enabled on this repo, every artifact is also reachable as a public URL the Mento reviewer can click directly from the Notion submission.

## Claude Code Working Build (Part 3 Companion)

Part 3's signal workflow is implemented as a runnable Python project at [`03_signal_workflow/build/`](./03_signal_workflow/build/). Roughly **65% real working code, 35% mocked**. The mocking is concentrated at external API boundaries (Crunchbase, LinkedIn, HubSpot, Slack, Smartlead). The orchestration logic, scoring, agentic drafting, and audit trail are real and runnable.

### What's Real

Scoring formula, routing tiers, Personalisation Agent (real Claude API), Strong-Hook Gate, Draft Assembly Agent (real Claude API), CLI HITL prompt, JSON audit logging, pytest suite.

### What's Mocked

External API integrations (signal detection, enrichment, HubSpot lookup/write, Slack DM, Smartlead send). Every mock carries a `# STUB:` comment with a note on the production replacement.

### Quick Start

```bash
cd 03_signal_workflow/build
cp .env.example .env
# add your ANTHROPIC_API_KEY
uv sync
uv run python -m signal_engine.run --signal funding --company linear
```

See [`03_signal_workflow/build/README.md`](./03_signal_workflow/build/README.md) for the full working/mocked breakdown and architecture explanation.

## Reading Order

1. Notion master page (link above) for the reviewer-facing read.
2. Part 1 sets the strategic frame (60-day priorities, week 1 discovery, risk).
3. Part 2 answers the four data foundation questions (dedupe, enrichment, ICP scoring, lifecycle) and links to the interactive data model.
4. Part 3 covers the buying signal workflow (build doc + Claude Code approach plan).

## Why This Repo Exists

Mirrors the live Notion submission for portability, version history, and as a public-URL host for the interactive HTML artifacts that Notion can't render natively.
