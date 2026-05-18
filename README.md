# Mento: GTM Engineer Case Study

> Mento has a real customer base, real buying signals, and real first-party data. What it doesn't have is the infrastructure to turn that into a scalable, repeatable revenue engine. This submission lays out what I'd build, in what order, and why.

**Code home.** https://github.com/gitgitbangbang/mento-gtme-case-study
**Live submission (Notion master page):** (https://jaredburke-mento.notion.site)

## Status

All shipped, merged, CI-green on main. Test coverage ~94% on the deterministic core. Branch protection active. End-to-end live verification on a clean clone passed.

- Part 1 ✓ Diagnose & Prioritize
- Part 2 ✓ Data Foundation Plan + Clay Board Build
- Part 3 docs ✓ ICP, Workflow Text, Workflow Diagram, Scoring, Outreach Drafts, Claude Code Build
- Part 3 build ✓ Working Python signal engine merged via PR #1
- CI green
- Branch protection active

## Reading Order

| Mode | Read this first |
|---|---|
| 15 min | Notion master page → 99 Submission Index → 3.6 Claude Code Working Build |
| 60 min | Add Parts 1, 2 (incl. Clay Board Build), and 3.1-3.5 |
| 2 hours | Open `03_signal_workflow/build/` and run the engine end to end |

## Structure

```
.
├── 00_pre-flight/
│   └── assumptions_register.md
├── 01_diagnose_prioritize/
│   └── 01_diagnose_prioritize.md
├── 02_data_foundation/
│   ├── 02_data_foundation.md
│   ├── data_model.html
│   └── clay_build/
│       └── 02_clay_board_build.md
├── 03_signal_workflow/
│   ├── 03_icp_and_signals.md
│   ├── 03_workflow_architecture_text.md
│   ├── 03_signal_scoring_framework.md
│   ├── 03_outreach_drafts.md
│   ├── workflow_diagram.html
│   └── build/
│       ├── README.md          (verification walkthrough)
│       └── (Python signal engine implementation)
└── README.md
```

## Live Artifacts (GitHub Pages)

- Data model: https://gitgitbangbang.github.io/mento-gtme-case-study/02_data_foundation/data_model.html
- Workflow diagram: https://gitgitbangbang.github.io/mento-gtme-case-study/03_signal_workflow/workflow_diagram.html

## Claude Code Working Build (Part 3)

Roughly **65% real working code, 35% mocked**. Real: scoring, routing, audit, Personalisation Agent + Strong-Hook Gate + Draft Assembly Agent (all real Claude API), CLI HITL. Mocked at external API boundaries (Crunchbase, LinkedIn, HubSpot, Slack, Smartlead) with explicit `# STUB:` comments.

### How to verify it works

A **10-minute, 7-step verification walkthrough** lives at the top of [`03_signal_workflow/build/README.md`](./03_signal_workflow/build/README.md#verification-walkthrough--7-steps-in-10-minutes). For every step the reviewer gets the command, what it does in plain English, the expected output, and what it proves.

The walkthrough handles installing `uv`, cloning into a fresh directory, passing your Anthropic API key inline via `--api-key`, running the test suite, running one signal end-to-end against the live Claude API, running all four signals in one command (`--all`), and reading the audit log. Total: ~10 minutes, ~$0.40 in Anthropic API spend.

72 tests passing, ~94% coverage on the deterministic core. CI green on every push to `main`.

