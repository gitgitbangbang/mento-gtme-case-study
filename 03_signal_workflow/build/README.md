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

## Verification Walkthrough — 7 Steps in ~10 Minutes

You'll need a terminal, internet, and an Anthropic API key. Each step has the command, what it does in plain English, and what you should see.

What this walkthrough proves to you:

- The code installs reproducibly from a lockfile — no "works on my machine" surprises
- The deterministic logic (scoring formula, routing tiers) is covered by an automated test suite
- The AI layer (hook generation, Strong-Hook Gate, draft assembly) is real Claude API, not pre-canned strings
- Every signal event leaves a complete audit trail you can read

### Step 1 — Make `uv` available

```bash
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

**Plain English.** `uv` is the Python package manager this project uses (think `npm` for JavaScript). The first line tells your terminal where to find it; the second confirms it's installed.

**Expected.** Something like `uv 0.11.14`. If `command not found`, install with `curl -LsSf https://astral.sh/uv/install.sh | sh` and re-run.

**Why it matters.** Modern Python projects pin their dependencies via a lockfile. `uv` reads that lockfile and rebuilds the exact environment the developer tested against — that's what kills "works on my laptop" mystery bugs.

### Step 2 — Go to the build directory

```bash
cd 03_signal_workflow/build
pwd
```

(From the root of your repo clone.)

**Plain English.** Navigate into the runnable Python project. The signal engine lives at `03_signal_workflow/build/`, alongside the case-study prose docs in `03_signal_workflow/`.

**Expected.** `pwd` prints the absolute path ending in `/03_signal_workflow/build`.

**Why it matters.** All subsequent commands run from inside this folder. The Python imports and the `.env` file are scoped here.

### Step 3 — Drop your API key into `.env`

Run **one** of these two options. Don't copy the prose between them or the `# verify` block into your shell — each code block below is meant to be pasted on its own.

**Option A** — edit `.env` in your editor and paste the key after the `=`:

```bash
cp .env.example .env
open -e .env
```

**Option B** — write the key directly via `printf` (replace `<your-key-here>` with your real key, drop the angle brackets):

```bash
printf 'ANTHROPIC_API_KEY=%s\n' '<your-key-here>' > .env
```

Then verify (paste this exactly as shown):

```bash
test $(wc -c < .env) -gt 50 && echo "OK: key present" || echo "FAIL: paste your key in"
```

**Plain English.** The signal engine talks to Anthropic's Claude API to generate the email hooks and run the polish pass. It reads the key from a file called `.env`, which is gitignored — it never gets committed.

**Expected.** `OK: key present`.

**Why it matters.** Confirms the AI calls are real — they hit YOUR Anthropic account. You'll see the cost in your Anthropic console afterwards (roughly $0.02 per run).

### Step 4 — Install dependencies

```bash
uv sync
```

**Plain English.** Reads the lockfile and downloads exactly the right versions of every Python library (the official Anthropic SDK, the test framework, the linter). Builds a virtual environment in `.venv/` so it never touches your system Python.

**Expected.** ~15 seconds. Ends with `Installed 30 packages` (or `Audited 30 packages` if already done).

**Why it matters.** This is the hermetic install. Anyone with the lockfile gets the exact same environment. No version drift, no surprises.

### Step 5 — Run the automated test suite

```bash
uv run pytest -q
```

**Plain English.** Runs 57 automated tests covering the deterministic parts of the engine — the scoring math, the P1/P2/P3 routing logic, the gate's banned-phrase and length checks, the audit log format, and a full end-to-end run with a stubbed Claude client. No network calls, fast.

**Expected.** `57 passed in <2s`.

**Why it matters.** Tests passing means the rules in the Part 3 docs (the scoring formula, the routing tiers) are wired up correctly in code. Coverage on the deterministic modules is ~94%; every multiplier, tier boundary, and gate check has a test guarding it.

### Step 6 — Run one signal end-to-end against the live Claude API

```bash
uv run python -m signal_engine.run --signal exec_hire --company vanta --non-interactive
```

**Plain English.** This is the demo. Walks Vanta's new CHRO hire (Sarah Chen, ex-Coda VP People, scaled that team 80→600) all the way through the five-stage pipeline: detection → enrichment → scoring → routing → AI drafting. Makes five real calls to Claude (one to generate three hook candidates, three to evaluate them, one to polish the final draft).

`--non-interactive` skips the human-in-the-loop prompt at the end and auto-treats every draft as Send. Drop the flag to get the interactive `[s]end / [e]dit / [k]ip` prompt.

**Expected (~10 seconds).** Five stage banners `[1/5]` through `[5/5]`, three hook candidates printed with their gate verdicts (typically all three pass the gate on this run because Sarah's prior-role context is rich), a draft inside two banner rules with subject `first 90 days` and body starting `Hi Sarah,`, then `[STUB] Would have triggered Smartlead campaign 'mento-signal-exec-hire'...`, then `[AUDIT] audit/<timestamp>...`.

**What's deterministic (same every run) vs variable (different every run):**

| | Behaviour across runs |
|---|---|
| `base_weight = 3.000` | identical — exec_hire signal weight is fixed |
| `recency_decay` ≈ 0.766 | identical — fixture pegs the signal to 8 days ago |
| `buyer_proximity = 1.000` | identical — Sarah is the economic buyer with engagement |
| `signal_score` ≈ 2.298 | identical |
| `Routing: P2` | identical — score in [1.5, 3) AND icp_total = 19 |
| The 3 hook candidates' wording | **different** — Claude generates fresh each run |
| Which candidate the gate selects | may vary — depends on which hook clears all five criteria |
| The polished draft body | **different** in opening, identical in template content |

**Why it matters.** This is the proof the AI layer is real. The hook text and chosen hook will be different each run because Claude isn't deterministic — but the tier, the score, and the template structure are stable. That asymmetry is the design: **deterministic where it needs to be auditable** (scoring, routing), **agentic where it needs to be contextual** (the opening line).

### Step 6b — Run all four signals in sequence (the variety pass)

```bash
uv run python -m signal_engine.run --all --non-interactive
```

**Plain English.** Cycles through all four canonical signal/company pairs: funding/linear, exec_hire/vanta, ld_posting/ramp, headcount_growth/retool. `--all` implies `--non-interactive`. About 60 seconds and ~$0.40 in API spend per invocation.

**Expected.** Four full `[1/5]…[5/5]` pipeline blocks, one per pair, then a summary table:

```
─── BATCH SUMMARY ───────────────────────────────────────────
signal             company  tier       gate       outcome
─────────────────────────────────────────────────────────────
funding            linear   P1         varies     draft sent OR manual review
exec_hire          vanta    P2         3/3        draft sent
ld_posting         ramp     P2         2/3        draft sent
headcount_growth   retool   P3         2/3        draft sent
```

**Why Linear's outcome varies.** Karri Saarinen is Linear's CEO, not a People exec. Mento sells to senior People execs (CHRO / CPO / VP People), so the agent prompt and the Strong-Hook Gate are calibrated for People-exec voice. When the agent can latch onto Karri's Airbnb design-lead background, the gate often passes a candidate. When it leans on his founder-philosophy LinkedIn posts about small teams, the gate often flags "no buyer context" and the signal correctly routes to manual review. **Either outcome demonstrates the gate working as designed.** See [the case-study spec on the Strong-Hook Gate](../03_outreach_drafts.md) — "Better to send no draft than a generic one to a senior People exec at a target account."

### Step 7 — Read the audit log

```bash
uv run python -m signal_engine.inspect_audit --latest
```

**Plain English.** Every run writes a JSON file capturing the full trace. This command pretty-prints the most recent one. You see the signal payload, the enriched company / contact, the score breakdown with every multiplier, the assigned tier, all three hook candidates with the gate's verdict on each (including the reason it passed or failed), the chosen hook, the final draft body, and the SDR's decision.

**Expected.** A sectioned report ending in:

```
── SDR DECISION ───────────...
  decision:  send
```

**Why it matters.** This is the compliance and learning layer. In production, this audit trail is what RevOps inspects when calibrating the base weights (per the "Self-Improvement Loop" in `03_signal_scoring_framework.md`). When the SDR Skip rate climbs above 40% on a signal type, the audit logs are what tell you whether it was the score, the hook, or the draft that triggered the skip.

### What you've just verified

After Step 7, you've proven, end-to-end on a clean machine:

1. ✓ The build installs reproducibly (Step 4 — lockfile-backed)
2. ✓ The deterministic core is test-covered and correct (Step 5 — 60 tests, ~94% coverage)
3. ✓ An exec_hire signal flows through detection → enrichment → scoring → routing exactly per the Part 3 spec (Step 6, stages 1–4)
4. ✓ The Personalisation Agent really is a live Claude call (Step 6, stage 5 — hook text varies each run)
5. ✓ The Strong-Hook Gate really evaluates candidates (you can read the pass/fail reasons; Step 6b shows the manual-review path on Linear)
6. ✓ The Draft Assembly Agent really polishes (compare the chosen hook text with the final draft body)
7. ✓ Every run leaves a complete, machine-readable audit (Step 7); `--all` produces four audits side-by-side (Step 6b)

Roughly 10 minutes of your time. The only thing taken on faith is that the mocked external integrations (Crunchbase, Apollo, HubSpot, Slack, Smartlead) would behave the way the architecture doc says they would in production. Every stub is annotated with a `# STUB:` comment and a note on the real API that would replace it.

### Try the Other Signals Individually

Available signals: `funding`, `exec_hire`, `ld_posting`, `headcount_growth`.
Available companies: `linear`, `vanta`, `ramp`, `retool`.

```bash
uv run python -m signal_engine.run --signal funding --company linear
uv run python -m signal_engine.run --signal ld_posting --company ramp
uv run python -m signal_engine.run --signal headcount_growth --company retool
```

Each produces a different tier (Linear=P1, Vanta=P2, Ramp=P2, Retool=P3) so you can see routing diverge in practice. Captured example outputs from a recent live run sit in [`examples/`](./examples/).

### Interactive HITL

Drop `--non-interactive` and you'll get the `[s]end / [e]dit / [k]ip` prompt at the end:

- `s` simulates sending via Smartlead (prints what the production call would do — no real send)
- `e` opens the body in `$EDITOR` (default `vim`) so you can adjust copy before send
- `k` skips the signal; production would decay it and capture a reason

### Useful Flags

- `--all` — run all four canonical signal/company pairs in sequence with a summary table. Implies `--non-interactive`. ~60 seconds, ~$0.40 API.
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
│   ├── inspect_audit.py      # Pretty-printer for audit JSON files
│   ├── run.py                # CLI entry point
│   └── templates/            # 4 signal-specific email templates
├── fixtures/                 # Mock data for the four scenarios
│   ├── signals/
│   ├── companies/
│   └── contacts/
├── tests/                    # pytest suite (60 tests, 94% core coverage)
├── audit/                    # JSON audit logs (gitignored, created at runtime)
├── examples/                 # Captured CLI runs from `uv run ...`
├── pyproject.toml            # uv-managed
└── README.md                 # This file
```

## Architecture

See [`../03_workflow_architecture_text.md`](../03_workflow_architecture_text.md), [`../03_signal_scoring_framework.md`](../03_signal_scoring_framework.md), and [`../03_outreach_drafts.md`](../03_outreach_drafts.md). This code is a faithful implementation of those docs.

```mermaid
flowchart TD
    Start([CLI: --signal X --company Y]) --> Detect[detector.detect<br/>STUB: fixtures/signals/*.json<br/>prod: Clay polling]
    Detect --> Enrich[enricher.enrich<br/>STUB: fixtures/companies + /contacts<br/>prod: Apollo / Ocean / Clearbit waterfall]
    Enrich --> Score[scorer.compute<br/>base_weight × recency_decay × buyer_proximity]
    Score --> Route{router.assign}

    Route -- P1 / P2 / P3 --> Personalise[personaliser.generate_hooks<br/>REAL Claude API · 3 candidates]
    Route -- Discovery --> StubDisc[STUB: Find Contacts at Company<br/>6h SLA · re-score next pass]
    Route -- Park --> StubPark[no alert · rescore monthly]

    Personalise --> Gate{gate.evaluate<br/>+ pick_strongest}
    Gate -- all fail --> Manual[STUB: manual review queue<br/>no draft to SDR]
    Gate -- pass --> Assemble[assembler.assemble<br/>template merge + REAL Claude polish]
    Assemble --> HITL{hitl.review<br/>s / e / k}

    HITL -- send --> Smartlead[STUB: Smartlead campaign trigger<br/>POST /api/v1/leads + start-lead]
    HITL -- edit --> EditBody[open in $EDITOR<br/>then send edited body]
    HITL -- skip --> SkipReason[capture skip reason<br/>decay the signal]

    Smartlead --> Audit[auditor.write<br/>audit/&lt;ts&gt;_&lt;signal_id&gt;.json]
    EditBody --> Audit
    SkipReason --> Audit
    Manual --> Audit
    StubDisc --> Audit
    StubPark --> Audit
    Audit --> Done([exit 0])

    classDef stub fill:#fff3e0,stroke:#e65100,color:#000
    classDef live fill:#e8f5e9,stroke:#2e7d32,color:#000
    classDef hitl fill:#e3f2fd,stroke:#1565c0,color:#000
    class Detect,Enrich,StubDisc,StubPark,Manual,Smartlead stub
    class Personalise,Assemble live
    class HITL,EditBody hitl
```

Legend: orange = STUB (mocked I/O), green = live Claude API call, blue = SDR human-in-the-loop. Everything else is pure Python with no external dependencies.

Discovery and Park exit early before the agentic layer. Manual review fires when no hook candidate clears the Strong-Hook Gate. Every exit path writes a full audit entry.

## Why This Exists

The case study includes both a no-code Clay build (for Part 2's data foundation) and this code build (for Part 3's signal engine). Each picks the right tool for its problem. Together they demonstrate full-stack GTM Engineer competence: operator no-code at the data layer, code where the agentic logic and orchestration deserve real implementation.
