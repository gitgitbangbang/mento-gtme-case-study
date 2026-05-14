# Claude Code Brief: Mento Signal Engine

You are building the working code companion to the Mento GTM Engineer case study. This brief is self-contained. Read it end to end before starting.

## 1. Context

The repo `gitgitbangbang/mento-gtme-case-study` already exists. It contains the case study response across Parts 1, 2, and 3. Your job is to build a working Python signal engine that operationalises the workflow described in `03_signal_workflow/03_workflow_architecture_text.md`.

The repo is at `~/code/mento-gtme-case-study/` on Jared's machine. You do **not** need to run any of `/code-setup` Section 0 or `/git-discipline` Section 0. The repo, GitHub remote, and `gitgitbangbang` account are already set up.

What you DO need from those skills:
- `/git-discipline` Sections 1-3 (commits, branches, PRs)
- `/code-setup` Steps 4-12 (CLAUDE.md, hooks, agents, settings) **but scoped to `03_signal_workflow/build/`** if needed at all. Don't overwrite root `CLAUDE.md`.

## 2. Mission

Build a runnable Python project at `03_signal_workflow/build/` that demonstrates the signal engine end to end. Real working code where it matters, honest mocking where it doesn't.

The reviewer (Mento hiring manager) should be able to:
1. Clone the repo
2. Set their `ANTHROPIC_API_KEY`
3. Run `uv sync && uv run python -m signal_engine.run --signal funding --company linear`
4. See a real signal flow through detection → enrichment → scoring → routing → AI-drafted email → CLI HITL prompt
5. Approve / edit / skip the draft
6. Read the audit log and the generated email

## 3. Scope: Working Code vs Mocked

### Working (real implementation)

| Component | Why real |
|---|---|
| Project scaffold (uv, pyproject.toml, ruff, pytest) | Modern Python tooling, reviewer can `uv sync` and run |
| Scoring module | Pure math, no external dependency |
| Routing module | Pure deterministic logic |
| Personalisation Agent | Real Claude API call (uses Jared's `ANTHROPIC_API_KEY`) |
| Strong-Hook Gate | Real LLM evaluation + deterministic length/regex checks |
| Draft Assembly Agent | Real Claude API call |
| Audit logger | Writes JSON logs to local `audit/` per signal event |
| CLI HITL prompt | Real interactive prompt |
| Tests | pytest, focused on scoring + routing + audit (the deterministic core) |

### Mocked (with explicit `# STUB:` comments)

| Component | Why mocked |
|---|---|
| Crunchbase / LinkedIn / Greenhouse / Lever / Firecrawl / Clearbit / PDL / Apollo / Ocean.io | Paid APIs, no keys |
| HubSpot lookup and write | Requires OAuth + account |
| Slack DM delivery | Requires workspace + bot token |
| Smartlead campaign trigger | Requires account |

Every mock carries a `# STUB:` comment explaining what would replace it in production.

### The Honest Split

Roughly **65% real working code, 35% mocked**. The mocking is concentrated at the I/O boundaries (external APIs, CRM, Slack). The orchestration logic, scoring, agentic drafting, and audit trail are real and runnable.

## 4. Architecture (Reference Only — Do Not Re-Specify)

The workflow you're building is documented in three sibling files. Read them before coding:

- `03_signal_workflow/03_workflow_architecture_text.md` — five-stage workflow, AI vs deterministic boundary, HITL terminal
- `03_signal_workflow/03_signal_scoring_framework.md` — the formula, base weights, routing tiers
- `03_signal_workflow/03_outreach_drafts.md` — four templates, agent prompt, strong-hook gate criteria

Implement what those docs describe. Do not invent your own logic.

## 5. Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Package manager | `uv` (Astral) |
| Linter / formatter | `ruff` |
| Type checker | `mypy --strict` for `src/`, lenient for `tests/` and fixtures |
| Test framework | `pytest` + `pytest-asyncio` |
| LLM SDK | `anthropic` (official Python SDK) |
| Default model | `claude-sonnet-4-6` |
| Logging | Python stdlib `logging` + JSON output to `audit/` |
| CLI | `argparse` (stdlib, no extra dep) |
| Env vars | `python-dotenv` for local dev |

No frameworks. No FastAPI. No Pydantic v2 unless you have a real reason. This is a demo, not a service.

## 6. Repo Structure to Create

Inside `03_signal_workflow/build/`:

```
build/
├── README.md                         (you write this — see Section 11)
├── pyproject.toml                    uv-managed
├── .python-version                   3.12
├── .env.example                      ANTHROPIC_API_KEY=
├── .gitignore                        .env, audit/, __pycache__/, .pytest_cache/, .venv/
├── ruff.toml                         line-length 100, target-version py312
├── src/
│   └── signal_engine/
│       ├── __init__.py
│       ├── run.py                    CLI entry point
│       ├── models.py                 dataclasses for Signal, Company, Contact, Draft
│       ├── detector.py               Stage 1: signal detection (reads fixtures)
│       ├── enricher.py               Stage 2: enrich Company + Contacts (mocked, reads fixtures)
│       ├── scorer.py                 Stage 3: signal_score formula
│       ├── router.py                 Stage 4: P1/P2/P3/Discovery tier assignment
│       ├── personaliser.py           Personalisation Agent (Claude API)
│       ├── gate.py                   Strong-Hook Gate (LLM + deterministic checks)
│       ├── assembler.py              Draft Assembly Agent (Claude API)
│       ├── hitl.py                   CLI Send/Edit/Skip prompt
│       ├── auditor.py                JSON audit logging
│       └── templates/
│           ├── funding.txt
│           ├── exec_hire.txt
│           ├── ld_posting.txt
│           └── headcount_growth.txt
├── fixtures/
│   ├── signals/
│   │   ├── linear_funding.json
│   │   ├── vanta_chro.json
│   │   ├── ramp_ld_posting.json
│   │   └── retool_headcount.json
│   ├── companies/
│   │   ├── linear.json
│   │   ├── vanta.json
│   │   ├── ramp.json
│   │   └── retool.json
│   └── contacts/
│       ├── linear_karri.json
│       ├── vanta_sarah.json
│       ├── ramp_jen.json
│       └── retool_jennifer.json
├── audit/                             gitignored, created at runtime
└── tests/
    ├── __init__.py
    ├── test_scorer.py                 unit tests for the formula
    ├── test_router.py                 unit tests for tier assignment
    ├── test_gate.py                   tests for the deterministic part of the gate
    └── test_audit.py                  tests for JSON audit format
```

## 7. Step-by-Step Build Plan

Work in this order. Commit after each numbered step. Use clean conventional-commit messages per `/git-discipline` Section 1.

### Step 1 — Branch + scaffold (commit: `chore(build): scaffold Python project with uv`)

```bash
cd ~/code/mento-gtme-case-study
git checkout -b feat/signal-engine
mkdir -p 03_signal_workflow/build
cd 03_signal_workflow/build

# Initialise uv project
uv init --python 3.12
uv add anthropic python-dotenv
uv add --dev pytest pytest-asyncio ruff mypy

# Create folder structure
mkdir -p src/signal_engine/templates
mkdir -p fixtures/{signals,companies,contacts}
mkdir -p tests
touch src/signal_engine/__init__.py tests/__init__.py
```

Add `.gitignore`:
```
.env
audit/
__pycache__/
.pytest_cache/
.venv/
.mypy_cache/
.ruff_cache/
*.pyc
```

Add `.env.example`:
```
ANTHROPIC_API_KEY=
```

### Step 2 — Models (commit: `feat(build): add core dataclasses`)

`src/signal_engine/models.py` — dataclasses for `Signal`, `Company`, `Contact`, `Draft`, `HookCandidate`, `AuditEntry`. Frozen where it makes sense. Type hints throughout.

### Step 3 — Fixtures (commit: `feat(build): add fixtures for Linear/Vanta/Ramp/Retool`)

Eight files in `fixtures/`. Each `signals/*.json` matches the signal_payload format from `03_outreach_drafts.md` Live Examples. Each `companies/*.json` includes `icp_total` (15-19 range, all in ICP) and ICP dimension breakdown. Each `contacts/*.json` includes the buyer_proximity-relevant fields.

Use the EXACT data from the 3.5 Live Examples:
- Linear: $82M Series C, Accel-led, Karri Saarinen
- Vanta: New CHRO Sarah Chen from Coda
- Ramp: Director, Leadership Development posting, Jen Liu
- Retool: 250 → 320 headcount growth, Jennifer Saavedra

### Step 4 — Detector + Enricher (mocked, commit: `feat(build): signal detection and enrichment, fixture-backed`)

`detector.py` reads from `fixtures/signals/`. `enricher.py` reads from `fixtures/companies/` and `fixtures/contacts/`. Both have explicit `# STUB:` comments at the top noting the production replacements (Crunchbase API, Apollo, etc.).

### Step 5 — Scorer + Router (commit: `feat(build): scoring formula and tier routing`)

`scorer.py` implements `signal_score = base_weight × recency_decay × buyer_proximity` exactly as specified in `03_signal_scoring_framework.md`. `router.py` assigns P1/P2/P3/Discovery per the routing tiers table.

### Step 6 — Templates (commit: `feat(build): add four signal-specific email templates`)

`src/signal_engine/templates/*.txt` — copy verbatim from `03_outreach_drafts.md` Templates 1-4. Use Python string format-style placeholders: `{ai_hook}`, `{prospect_first_name}`, `{sdr_signature}`, etc.

### Step 7 — Personaliser + Gate + Assembler (commit: `feat(build): agentic drafting layer with Claude API`)

`personaliser.py` calls Claude API with the prompt from `03_outreach_drafts.md` "Agent Prompt" section. Returns three hook candidates.

`gate.py` evaluates candidates against the five Strong-Hook Gate criteria. Deterministic checks (length, banned phrases) inline; LLM check (specificity, voice) via a separate Claude call. Returns selected hook or rejection.

`assembler.py` merges template + selected hook + variables into final draft. Returns `Draft` dataclass.

### Step 8 — HITL CLI (commit: `feat(build): CLI HITL prompt for SDR review`)

`hitl.py` prints the assembled draft formatted for terminal reading, then prompts `[s]end / [e]dit / [k]ip > `. Capture the response. On `[e]dit`, open in `$EDITOR` (default `vim`).

`run.py` is the CLI entry point: `python -m signal_engine.run --signal <type> --company <name>`. Walks one signal end to end through all stages, prints stage-by-stage status, calls `hitl.py` at the end.

### Step 9 — Auditor (commit: `feat(build): JSON audit logging per signal event`)

`auditor.py` writes one JSON file per run to `audit/{timestamp}_{signal_id}.json`. Captures: signal payload, enrichment data, score breakdown (each multiplier shown), tier assignment, hook candidates with gate verdicts, selected hook, final draft, SDR decision.

### Step 10 — Tests (commit: `test(build): unit tests for scorer, router, gate, audit`)

pytest. Cover the deterministic core. Skip the LLM-calling modules (or mock the anthropic client). Aim for >80% coverage on `scorer.py`, `router.py`, the deterministic part of `gate.py`, and `auditor.py`.

### Step 11 — README (commit: `docs(build): add README explaining working vs mocked split`)

Write `build/README.md` per Section 11 of this brief.

### Step 12 — Root README update (commit: `docs: link Claude Code build from root README`)

Update `~/code/mento-gtme-case-study/README.md` to add a new section about the Claude Code build. Content per Section 12 of this brief.

### Step 13 — End-to-end smoke test (commit only if this works)

Run all four signal types end to end:
```bash
uv run python -m signal_engine.run --signal funding --company linear
uv run python -m signal_engine.run --signal exec_hire --company vanta
uv run python -m signal_engine.run --signal ld_posting --company ramp
uv run python -m signal_engine.run --signal headcount_growth --company retool
```

Each should produce a real Claude-generated draft. Capture the four outputs as text files in `examples/` and commit (`docs(build): add captured example runs`).

### Step 14 — Open PR

Per `/git-discipline` Section 3, Path A:

```bash
git push -u origin feat/signal-engine

gh pr create \
  --title "feat(part3): Claude Code working build of signal engine" \
  --body "## What this does
Builds the Mento signal engine companion to Part 3 of the case study at \`03_signal_workflow/build/\`.

## Scope
Roughly 65% real working code, 35% mocked. See \`build/README.md\` for the full breakdown.

Real: scoring, routing, audit, Claude API drafting, HITL CLI.
Mocked: external API integrations (Crunchbase, LinkedIn, HubSpot, Slack, Smartlead).

## How to test
\`\`\`bash
cd 03_signal_workflow/build
cp .env.example .env
# add your ANTHROPIC_API_KEY
uv sync
uv run python -m signal_engine.run --signal funding --company linear
\`\`\`

## Notes
Updates root README with a build section. No changes to existing case-study docs in 01-03." \
  --base main
```

Do not auto-merge. Leave the PR open for Jared to review.

## 8. Code Style and Conventions

- Type hints on every function signature, including return types
- Docstrings on every public function, one-line summary minimum
- Module-level docstring at the top of every `.py` file explaining what the module does
- `# STUB:` comments on every line that mocks an external integration, with a one-line note on what would replace it
- ruff defaults plus `line-length = 100`
- No print statements outside `run.py` and `hitl.py`. Use `logging` everywhere else.
- Constants (base weights, thresholds, model name) live in a `constants.py` module, not scattered through code

## 9. Git Workflow (per /git-discipline)

- Branch name: `feat/signal-engine`
- One commit per build step (Steps 1-13 above)
- Conventional commit format: `type(scope): summary`
- Run tests before each commit: `uv run pytest`
- Push to remote after each commit: `git push origin feat/signal-engine`
- Final step: open PR via `gh pr create`, leave open for review

## 10. Acceptance Criteria

The build is done when:

- [ ] `uv sync` runs cleanly with no warnings
- [ ] `uv run pytest` passes all tests with >80% coverage on the deterministic modules
- [ ] `uv run ruff check src/ tests/` passes
- [ ] `uv run mypy src/signal_engine` passes (strict for src/, OK to be lenient on tests)
- [ ] All four signal types run end to end and produce real Claude-generated drafts
- [ ] HITL CLI accepts Send / Edit / Skip and writes the result to the audit log
- [ ] `audit/` contains one JSON entry per run with full traceability
- [ ] `build/README.md` exists and explains working vs mocked
- [ ] Root `README.md` has the new build section linking down to `build/`
- [ ] PR is open against `main` with the title and body from Step 14
- [ ] No `CLAUDE.local.md` or `.env` committed

## 11. build/README.md Content

Write the following at `03_signal_workflow/build/README.md`:

```markdown
# Mento Signal Engine

Working code companion to Part 3 of the [Mento GTM Engineer case study](../../README.md). Demonstrates the buying signal workflow described in [`03_workflow_architecture_text.md`](../03_workflow_architecture_text.md) as runnable Python.

## What's Real, What's Mocked

Roughly **65% real working code, 35% mocked**. Mocking is concentrated at external API boundaries.

### Real Working Code

| Component | Why real |
|---|---|
| Scoring formula | Pure math, no dependencies |
| Routing tiers (P1/P2/P3/Discovery) | Pure deterministic logic |
| Personalisation Agent | Real Claude API call (`claude-sonnet-4-6`) |
| Strong-Hook Gate | Real LLM evaluation + deterministic length / regex checks |
| Draft Assembly Agent | Real Claude API call |
| CLI HITL prompt | Real interactive `[s]end / [e]dit / [k]ip` |
| Audit logger | Writes JSON to `audit/` per signal event |
| Tests | pytest with >80% coverage on deterministic core |

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

[1/5] Signal detected: Linear Series C $82M from Accel
[2/5] Enriching company (mock)... done. icp_total=18
[3/5] Scoring: base=4, decay=0.875, buyer_proximity=1.0 → score=3.5 → P1
[4/5] Routing: P1 → SDR direct DM (mocked, would post to #sdr-priority)
[5/5] Drafting via Claude API...

────── DRAFT ──────
Subject: manager bench

Hi Karri,

Saw Linear's $82M Series C from Accel close last week. Congrats. With the
agent-triage rollout in parallel, your headcount math probably gets
interesting fast.

Pattern post-funding: hiring outpaces the manager bench by 90 days.
Performance dips at the team-lead layer. Brex and Vercel saw it. Their
People teams worked with our coaches in months 3-9.

Happy to share the playbook.

Worth 15 minutes?

— {{sdr_signature}}
─────────────────────

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

## Project Structure

```
build/
├── src/signal_engine/        # Python package
├── fixtures/                 # Mock data for the four scenarios
├── tests/                    # pytest suite
├── audit/                    # JSON audit logs (gitignored)
├── pyproject.toml            # uv-managed
└── README.md                 # This file
```

## Architecture

See [`../03_workflow_architecture_text.md`](../03_workflow_architecture_text.md), [`../03_signal_scoring_framework.md`](../03_signal_scoring_framework.md), and [`../03_outreach_drafts.md`](../03_outreach_drafts.md). This code is a faithful implementation of those docs.

## Why This Exists

The case study includes both a no-code Clay build (for Part 2's data foundation) and this code build (for Part 3's signal engine). Each picks the right tool for its problem. Together they demonstrate full-stack GTM Engineer competence: operator no-code at the data layer, code where the agentic logic and orchestration deserve real implementation.
```

## 12. Root README.md Update

Add this section to `~/code/mento-gtme-case-study/README.md`. Place it after the existing "Live Artifacts" section.

```markdown
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
```

## 13. Appendix: Reference Examples

### Sample fixture: `fixtures/signals/linear_funding.json`

```json
{
  "signal_id": "sig_linear_funding_2024_10_31",
  "signal_type": "funding",
  "signal_date": "2024-10-31",
  "company_id": "linear",
  "signal_source": "crunchbase",
  "signal_payload": {
    "round": "Series C",
    "amount_usd": 82000000,
    "lead_investor": "Accel",
    "press_release_url": "https://linear.app/blog/series-c"
  }
}
```

### Sample fixture: `fixtures/companies/linear.json`

```json
{
  "company_id": "linear",
  "company_name": "Linear",
  "domain": "linear.app",
  "linkedin_url": "https://linkedin.com/company/linear",
  "headcount": 280,
  "industry": "B2B SaaS",
  "funding_stage": "Series C",
  "hr_tech_stack": ["Lattice", "Rippling"],
  "icp_fit": 4,
  "icp_timing": 4,
  "icp_access": 4,
  "icp_intent": 3,
  "icp_budget": 3,
  "icp_total": 18,
  "lifecycle_stage": "Lead",
  "recent_news": "Linear launched Customer Requests; agent-triage features rolling out"
}
```

### Sample fixture: `fixtures/contacts/linear_karri.json`

```json
{
  "contact_id": "linear_karri",
  "company_id": "linear",
  "first_name": "Karri",
  "last_name": "Saarinen",
  "email": "karri@linear.app",
  "title": "CEO",
  "linkedin_url": "https://linkedin.com/in/karrisaarinen",
  "buyer_role": "economic",
  "engagement_score": 7,
  "linkedin_summary": "Co-founder and CEO at Linear. Previously design lead at Airbnb.",
  "recent_posts": [
    "Excited to share Linear's Series C close. Thank you to our team and customers."
  ]
}
```

### Sample scoring output (test assertion)

```python
def test_linear_funding_scores_p1():
    signal = load_signal("linear_funding")
    company = load_company("linear")
    contact = load_contact("linear_karri")

    score = scorer.compute(signal, company, contact)
    
    assert score.base_weight == 4
    assert 0.85 <= score.recency_decay <= 0.90  # ~4 days old
    assert score.buyer_proximity == 1.0          # CEO with engagement
    assert score.signal_score >= 3.0
    
    tier = router.assign(score, company)
    assert tier == "P1"
```

### Sample CLI run capture (for `examples/` folder)

```
$ uv run python -m signal_engine.run --signal funding --company linear

[1/5] Signal detected: Linear Series C $82M from Accel (4 days ago)
[2/5] Enriching... done. company.icp_total=18, contact=Karri Saarinen (CEO)
[3/5] Scoring breakdown:
        base_weight       4.000  (funding signal)
        recency_decay     0.875  (4 days, half-life 30)
        buyer_proximity   1.000  (CEO with engagement)
        signal_score      3.500
[4/5] Routing: P1 (signal_score>=3 AND icp_total>=11) → SDR DM
        # STUB: would post to Slack #sdr-priority via Slack Web API
[5/5] Drafting...
        Personalisation Agent: 3 hook candidates generated
        Strong-Hook Gate: candidate 2 selected (specificity ✓ timeliness ✓ voice ✓)
        Draft Assembly Agent: template merged with hook

────── DRAFT (Claude-generated) ──────
Subject: manager bench

Hi Karri,

[full draft body]

────────────────────────────────────────

[s]end / [e]dit / [k]ip > s

[STUB] Would have triggered Smartlead campaign 'mento-signal-funding'
       with personalised_first_email custom variable populated.
[AUDIT] Wrote audit/2024-12-01T15-30-22_sig_linear_funding_2024_10_31.json
```

---

## 14. Notes for Claude Code

- This brief is at `03_signal_workflow/build/CLAUDE_CODE_BRIEF.md`. It will be committed to the repo as part of the PR (it's the spec, leave it in place).
- If you hit ambiguity, default toward the documented architecture in `03_workflow_architecture_text.md`, `03_signal_scoring_framework.md`, and `03_outreach_drafts.md`. Don't invent new logic.
- If a real Claude API call fails (rate limit, network), don't fall back to a hardcoded string. Surface the error in the CLI output. The point is to show the agentic layer is real.
- The reviewer is a Mento hiring manager evaluating a GTM Engineer candidate. Code quality matters. Type hints, tests, docstrings, clear module separation.
- When in doubt about scope, less is more. Don't add features the brief doesn't ask for.

End of brief. Build it.
