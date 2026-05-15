# Walkthrough & Verification Steps

Hands-on, 10-minute verification that the Mento signal engine actually does what the spec claims. You'll need a terminal, internet, and an Anthropic API key.

## What This Walkthrough Proves

- The code installs reproducibly from a lockfile. No "works on my machine" surprises.
- The deterministic logic (scoring formula, routing tiers) is covered by an automated test suite.
- The AI layer (hook generation, Strong-Hook Gate, draft assembly) is real Claude API, not pre-canned strings.
- Every signal event leaves a complete audit trail you can read.

## Step 1. Make `uv` available

```bash
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

**Plain English.** `uv` is the Python package manager this project uses (think `npm` for JavaScript). The first line tells your terminal where to find it; the second confirms it's installed.

**Expected.** Something like `uv 0.11.14`. If `command not found`, install with `curl -LsSf https://astral.sh/uv/install.sh | sh` and re-run.

**Why it matters.** Modern Python projects pin their dependencies via a lockfile. `uv` reads that lockfile and rebuilds the exact environment the developer tested against. That's what kills "works on my laptop" mystery bugs.

## Step 2. Clone the repo and go to the build directory

```bash
git clone https://github.com/gitgitbangbang/mento-gtme-case-study.git
cd mento-gtme-case-study/03_signal_workflow/build
pwd
```

**Plain English.** Pull a fresh copy of the case-study repo and navigate into the runnable Python project. The signal engine lives at `03_signal_workflow/build/`, alongside the case-study prose docs in `03_signal_workflow/`.

**Expected.** `pwd` prints the absolute path ending in `/03_signal_workflow/build`.

**Why it matters.** All subsequent commands run from inside this folder. The Python imports and the `.env` file are scoped here.

## Step 3. Drop your API key into `.env`

```bash
cp .env.example .env
# then either edit .env in a text editor and paste the key after the =
# OR run this one-liner (replace YOUR-KEY-HERE):
printf 'ANTHROPIC_API_KEY=%s\n' 'sk-ant-api03-YOUR-KEY-HERE' > .env

# verify:
test $(wc -c < .env) -gt 50 && echo "OK: key present" || echo "FAIL: paste your key in"
```

**Plain English.** The signal engine talks to Anthropic's Claude API to generate the email hooks and run the polish pass. It reads the key from a file called `.env`, which is gitignored. It never gets committed.

**Expected.** `OK: key present`.

**Why it matters.** Confirms the AI calls are real. They hit YOUR Anthropic account. You'll see the cost in your Anthropic console afterwards (roughly $0.02 per run).

## Step 4. Install dependencies

```bash
uv sync
```

**Plain English.** Reads the lockfile and downloads exactly the right versions of every Python library (the official Anthropic SDK, the test framework, the linter). Builds a virtual environment in `.venv/` so it never touches your system Python.

**Expected.** ~15 seconds. Ends with `Installed 30 packages` (or `Audited 30 packages` if already done).

**Why it matters.** This is the hermetic install. Anyone with the lockfile gets the exact same environment. No version drift, no surprises.

## Step 5. Run the automated test suite

```bash
uv run pytest -q
```

**Plain English.** Runs 57 automated tests covering the deterministic parts of the engine. The scoring math, the P1/P2/P3 routing logic, the gate's banned-phrase and length checks, the audit log format, and a full end-to-end run with a stubbed Claude client. No network calls, fast.

**Expected.** `57 passed in <2s`.

**Why it matters.** Tests passing means the rules in the Part 3 docs (the scoring formula, the routing tiers) are wired up correctly in code. Coverage on the deterministic modules is ~94%. Every multiplier, tier boundary, and gate check has a test guarding it.

## Step 6. Run one signal end-to-end against the live Claude API

```bash
uv run python -m signal_engine.run --signal funding --company linear --non-interactive
```

**Plain English.** This is the demo. Walks Linear's $82M Series C funding signal all the way through the five-stage pipeline: detection, enrichment, scoring, routing, AI drafting. Makes five real calls to Claude (one to generate three hook candidates, three to evaluate them, one to polish the final draft).

`--non-interactive` skips the human-in-the-loop prompt at the end and auto-treats every draft as Send. Drop the flag to get the interactive `[s]end / [e]dit / [k]ip` prompt.

**Expected (~10 seconds).** Five stage banners `[1/5]` through `[5/5]`, three hook candidates printed with their gate verdicts, a draft inside two banner rules with subject `manager bench` and body starting `Hi Karri,`, then `[STUB] Would have triggered Smartlead...`, then `[AUDIT] audit/<timestamp>...`.

### What's Deterministic (Same Every Run) Vs. Variable (Different Every Run)

| Element | Behaviour Across Runs |
|---|---|
| `base_weight = 4.000` | identical. Funding signal weight is fixed |
| `recency_decay = 0.875` | identical. Fixture pegs the signal to 4 days ago |
| `buyer_proximity = 1.000` | identical. Karri is the economic buyer with engagement |
| `signal_score = 3.501` | identical |
| `Routing: P1` | identical. Score >= 3 AND icp_total >= 11 |
| The 3 hook candidates' wording | **different**. Claude generates fresh each run |
| Which candidate the gate selects | may vary. Depends on which hook clears all five criteria |
| The polished draft body | **different** in opening, identical in template content |

**Why it matters.** This is the proof the AI layer is real. The hook text and chosen hook will be different each run because Claude isn't deterministic, but the tier, the score, and the template structure are stable. That asymmetry is the design: **deterministic where it needs to be auditable** (scoring, routing), **agentic where it needs to be contextual** (the opening line).

## Step 7. Read the audit log

```bash
uv run python -m signal_engine.inspect_audit --latest
```

**Plain English.** Every run writes a JSON file capturing the full trace. This command pretty-prints the most recent one. You see the signal payload, the enriched company / contact, the score breakdown with every multiplier, the assigned tier, all three hook candidates with the gate's verdict on each (including the reason it passed or failed), the chosen hook, the final draft body, and the SDR's decision.

**Expected.** A sectioned report ending in:

```javascript
── SDR DECISION ───────────...
  decision:  send
```

**Why it matters.** This is the compliance and learning layer. In production, this audit trail is what RevOps inspects when calibrating the base weights (per the Self-Improvement Loop in the [Signal Scoring Framework](../03_signal_scoring_framework.md)). When the SDR Skip rate climbs above 40% on a signal type, the audit logs are what tell you whether it was the score, the hook, or the draft that triggered the skip.

## What You've Just Verified

After Step 7, you've proven, end to end on a clean machine:

1. The build installs reproducibly (Step 4. Lockfile-backed)
2. The deterministic core is test-covered and correct (Step 5. 57 tests, ~94% coverage)
3. A funding signal flows through detection, enrichment, scoring, routing exactly per the Part 3 spec (Step 6, stages 1-4)
4. The Personalisation Agent really is a live Claude call (Step 6, stage 5. Hook text varies each run)
5. The Strong-Hook Gate really evaluates candidates (you can read the pass/fail reasons)
6. The Draft Assembly Agent really polishes (compare the chosen hook text with the final draft body)
7. Every run leaves a complete, machine-readable audit (Step 7)

Roughly 10 minutes of your time. The only thing taken on faith is that the mocked external integrations (Crunchbase, Apollo, HubSpot, Slack, Smartlead) would behave the way the architecture doc says they would in production. Every stub is annotated with a `# STUB:` comment and a note on the real API that would replace it.

## Try the Other Three Signals

Available signals: `funding`, `exec_hire`, `ld_posting`, `headcount_growth`.
Available companies: `linear`, `vanta`, `ramp`, `retool`.

```bash
uv run python -m signal_engine.run --signal exec_hire --company vanta --non-interactive
uv run python -m signal_engine.run --signal ld_posting --company ramp --non-interactive
uv run python -m signal_engine.run --signal headcount_growth --company retool --non-interactive
```

Each produces a different tier (Linear=P1, Vanta=P2, Ramp=P2, Retool=P3) so you can see routing diverge in practice. Captured outputs from a recent live run sit in [examples/](./examples/).

## Interactive HITL

Drop `--non-interactive` and you'll get the `[s]end / [e]dit / [k]ip` prompt at the end:

- `s` simulates sending via Smartlead (prints what the production call would do, no real send)
- `e` opens the body in `$EDITOR` (default `vim`) so you can adjust copy before send
- `k` skips the signal; production would decay it and capture a reason

## Useful Flags

- `--non-interactive`. Skip the HITL prompt (treats every draft as Send). For CI / smoke tests.
- `--no-polish`. Skip the assembler's final Claude voice pass. Saves one API call per run.
- `--sdr-signature "Your Name"`. Override the signoff (default `Alex`).
- `-v` / `--verbose`. Echo INFO-level pipeline logs to stderr.

## Source Material

- Parent overview page: [3.6 Claude Code Working Build](https://www.notion.so/3607642d57d781599180ebc2a5160e25)
- GitHub equivalent: [build/README.md, Verification Walkthrough](./README.md#verification-walkthrough--7-steps-in-10-minutes)
- Merged PR: [#1, feat(part3): Claude Code working build of signal engine](https://github.com/gitgitbangbang/mento-gtme-case-study/pull/1)
