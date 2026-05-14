# Mento Signal Engine

Working code companion to Part 3 of the [Mento GTM Engineer case study](../../README.md). Demonstrates the buying signal workflow described in [`03_workflow_architecture_text.md`](../03_workflow_architecture_text.md) as runnable Python.

## What's Real, What's Mocked

Roughly **65% real working code, 35% mocked**. Mocking is concentrated at external API boundaries.

### Real Working Code

| Component | Why real |
|---|---|
| Scoring formula | Pure math, no dependencies |
| Routing tiers (P1/P2/P3/Discovery/Park) | Pure deterministic logic |
| Personalisation Agent | Real Claude API call (`claude-sonnet-4-6`) |
| Strong-Hook Gate | Real LLM evaluation + deterministic length / regex checks |
| Draft Assembly Agent | Real Claude API call |
| CLI HITL prompt | Real interactive `[s]end / [e]dit / [k]ip` |
| Audit logger | Writes JSON to `audit/` per signal event |
| Tests | pytest, 45 tests, 94% coverage on the deterministic core |

### Mocked (with `# STUB:` comments)

| Component | Why mocked | Production replacement |
|---|---|---|
| Signal detection | No paid API access | Crunchbase API, LinkedIn (Apify), Greenhouse + Lever (Firecrawl), Clearbit + PDL |
| Company / contact enrichment | Same | Apollo, Ocean.io, Clearbit, ZoomInfo, PDL, Crunchbase, BuiltWith |
| HubSpot lookup + write | Requires OAuth + account | HubSpot CRM API |
| Slack DM delivery | Requires workspace + bot token | Slack Web API + Block Kit |
| Smartlead trigger | Requires account | Smartlead REST API |

Every stub line carries a `# STUB:` comment with a one-line note on what would replace it.

## What The Reviewer Sees

```bash
$ uv run python -m signal_engine.run --signal funding --company linear

[1/5] Detecting signal: funding @ linear...
      sig_linear_funding_2026_05_10 (crunchbase, fired 2026-05-10)
[2/5] Enriching (mocked Clay waterfall)...
      company=Linear icp_total=18 | contact=Karri Saarinen (CEO)
[3/5] Scoring...
      base_weight       4.000  (funding signal)
      recency_decay     0.875  (4 days, half-life 30)
      buyer_proximity   1.000  (CEO, engagement=7)
      signal_score      3.501
[4/5] Routing: P1
      # STUB: SDR direct DM (would post to #sdr-priority, 60s SLA)
[5/5] Drafting via Claude API...
      Personalisation Agent: generating 3 hook candidates...
      Strong-Hook Gate: evaluating candidates...
      Selected hook: candidate 2
      Draft Assembly Agent: merging template + hook...

────────────────────────────────────────────────────────────
 DRAFT (Claude-generated)
────────────────────────────────────────────────────────────
Subject: manager bench

Hi Karri,

Saw Linear's $82M Series C from Accel close last week. With the
agent-triage rollout in parallel, your headcount math probably gets
interesting fast.

Pattern post-funding: hiring outpaces the manager bench by 90 days.
Performance dips at the team-lead layer. Brex and Vercel saw it. Their
People teams worked with our coaches in months 3-9.

Happy to share the playbook.

Worth 15 minutes?

— Alex
────────────────────────────────────────────────────────────

[s]end / [e]dit / [k]ip > _
```

The draft is a live Claude API output, not a hardcoded string.

## Quick Start

```bash
cd 03_signal_workflow/build
cp .env.example .env
# add your ANTHROPIC_API_KEY

uv sync
uv run pytest
uv run python -m signal_engine.run --signal funding --company linear
```

Available signals: `funding`, `exec_hire`, `ld_posting`, `headcount_growth`.
Available companies: `linear`, `vanta`, `ramp`, `retool`.

Useful flags:
- `--non-interactive` — skip the HITL prompt (treats every draft as Send). For CI / smoke tests.
- `--no-polish` — skip the assembler's final Claude voice pass. Saves one API call per run.
- `--sdr-signature "Your Name"` — override the signoff (default `Alex`).
- `-v` / `--verbose` — echo INFO-level pipeline logs to stderr.

## Project Structure

```
build/
├── src/signal_engine/        # Python package
│   ├── constants.py          # Tuneable thresholds (weights, decay, gate)
│   ├── models.py             # Frozen dataclasses passed between stages
│   ├── detector.py           # Stage 1: signal detection (STUB: Clay)
│   ├── enricher.py           # Stage 2: enrich Company + Contact (STUB: waterfalls)
│   ├── scorer.py             # Stage 3: signal_score formula
│   ├── router.py             # Stage 4: P1/P2/P3/Discovery/Park tier
│   ├── personaliser.py       # Personalisation Agent (real Claude API)
│   ├── gate.py               # Strong-Hook Gate (LLM + deterministic checks)
│   ├── assembler.py          # Draft Assembly Agent (real Claude API)
│   ├── hitl.py               # CLI Send/Edit/Skip prompt
│   ├── auditor.py            # JSON audit logging
│   ├── run.py                # CLI entry point
│   └── templates/            # 4 signal-specific email templates
├── fixtures/                 # Mock data for the four scenarios
│   ├── signals/
│   ├── companies/
│   └── contacts/
├── tests/                    # pytest suite (45 tests, 94% core coverage)
├── audit/                    # JSON audit logs (gitignored, created at runtime)
├── examples/                 # Captured CLI runs from `uv run ...`
├── pyproject.toml            # uv-managed
└── README.md                 # This file
```

## Architecture

See [`../03_workflow_architecture_text.md`](../03_workflow_architecture_text.md), [`../03_signal_scoring_framework.md`](../03_signal_scoring_framework.md), and [`../03_outreach_drafts.md`](../03_outreach_drafts.md). This code is a faithful implementation of those docs.

The orchestration shape:

```
detector.detect()         # Stage 1: load Signal from fixtures
   ↓
enricher.enrich()         # Stage 2: load Company + Contact
   ↓
scorer.compute()          # Stage 3: base_weight × recency_decay × buyer_proximity
   ↓
router.assign()           # Stage 4a: P1 / P2 / P3 / Discovery / Park
   ↓
personaliser.generate_hooks()  # Stage 4b: 3 hook candidates via Claude
   ↓
gate.evaluate() + pick_strongest()  # Stage 4c: Strong-Hook Gate
   ↓
assembler.assemble()      # Stage 4d: template + hook → final Draft
   ↓
hitl.review()             # Stage 4e: SDR Send / Edit / Skip
   ↓
auditor.write()           # JSON audit at audit/<ts>_<signal_id>.json
```

Discovery and Park exit early before the agentic layer. Manual review fires when no hook candidate clears the Strong-Hook Gate. Every exit path writes a full audit entry.

## Why This Exists

The case study includes both a no-code Clay build (for Part 2's data foundation) and this code build (for Part 3's signal engine). Each picks the right tool for its problem. Together they demonstrate full-stack GTM Engineer competence: operator no-code at the data layer, code where the agentic logic and orchestration deserve real implementation.
