# STUB Swap Points

Five concrete swap points in the engine code where mocked data becomes real API calls. Each is marked with a `# STUB:` comment in the source naming the production replacement. Going to production means swapping the body of five functions; the rest of the engine (scoring, routing, agentic drafting, audit) is already production-grade.

Of roughly 1,200 lines across 14 source modules, the stubbed surface is ~120 lines. The other ~1,080 lines ship as-is.

---

## 1. Signal Detection (`detector.py`)

[View on GitHub](./src/signal_engine/detector.py)

Today the detector loads pre-fired signal events from `fixtures/signals/*.json`. In production, four Clay polling jobs replace it.

**Today (lines 45-73):**

```python
def detect(signal_type, company_id, *, reference_date=None) -> Signal:
    """
    STUB: production replacement is a Clay polling job firing into the
    Signals table. Here we read the matching fixture file from disk.
    """
    stem = _SIGNAL_FILE_MAP[(signal_type, company_id)]
    path = FIXTURE_ROOT / f"{stem}.json"
    raw = json.loads(path.read_text())
    return _signal_from_dict(raw, reference_date=reference_date or date.today())
```

**In production:**

```python
def detect(signal_type, company_id, ...):
    if signal_type == "funding":
        raw = crunchbase.search_funding_rounds(
            company_domain=lookup_domain(company_id),
            round_filter=["Series B", "Series C"],
            since_days=30,
        )
    elif signal_type == "exec_hire":
        raw = apify.run_actor(
            "apify/linkedin-job-changes-scraper",
            input={"company": company_id, "titles": ["CHRO", "CPO", "VP People"]},
        )
    # ... etc.
    return _signal_from_dict(raw, ...)
```

Per signal type:

| Signal type | Production data source | Cadence |
|---|---|---|
| `funding` (Series B/C) | Crunchbase API | every 12h |
| `exec_hire` (CHRO / CPO / VP People) | LinkedIn via Apify | every 24h |
| `ld_posting` (Director / Head of L&D) | Greenhouse + Lever + Firecrawl | every 24h |
| `headcount_growth` (20%+ in 6mo) | Clearbit + PDL + LinkedIn | every 7d |

The `Signal` dataclass returned stays identical; only the input acquisition changes. Everything downstream (scorer, router, agents) is API-source agnostic.

---

## 2. Company and Contact Enrichment (`enricher.py`)

[View on GitHub](./src/signal_engine/enricher.py)

Today reads company + contact JSON from `fixtures/companies/` and `fixtures/contacts/`. In production this is two distinct waterfalls.

**Today (lines 37-53):**

```python
def enrich(signal: Signal) -> tuple[Company, Contact]:
    """
    STUB: production replacement is a Clay enrichment waterfall + HubSpot
    lookup. Here we hydrate from fixtures.
    """
    company = _load_company(signal.company_id)
    contact = _load_best_contact(signal.company_id)
    return company, contact
```

**In production:**

```python
def enrich(signal: Signal) -> tuple[Company, Contact]:
    # 1. Company waterfall: first hit wins, fall through on null fields
    company_data = (
        hubspot.get_company(signal.company_id)        # existing CRM data first
        or apollo.get_company(domain=...)              # then Apollo
        or ocean.get_company(linkedin_url=...)         # then Ocean.io
        or clearbit.enrich_company(domain=...)         # then Clearbit
        or zoominfo.get_company(name=...)              # then ZoomInfo
        or pdl.company_enrich(name=...)                # then PDL
    )

    # 2. Best buyer contact: highest-proximity match
    contacts = hubspot.search_contacts(
        company_id=signal.company_id,
        titles=["CHRO", "CPO", "VP People", "Head of L&D"],
    )
    if not contacts:
        # Find Contacts at Company: the Discovery-tier subroutine
        contacts = (
            apollo.search_people(company_domain=..., roles=["chief_human_resources_officer", ...])
            or leadmagic.lookup_people(...)
            or pdl.person_search(...)
        )

    best = max(contacts, key=buyer_proximity_score)

    # 3. Hydrate LinkedIn summary + recent posts for the personaliser
    best.linkedin_summary = leadmagic.profile_summary(best.linkedin_url)
    best.recent_posts = apify.linkedin_posts(best.linkedin_url, days=30)

    return company_data, best
```

Returns the same `(Company, Contact)` shape so nothing downstream changes. The "Find Contacts at Company" sub-trigger the spec mentions for the Discovery tier lives here.

---

## 3. Slack Delivery (`router.py`)

[View on GitHub](./src/signal_engine/router.py)

Today returns a human-readable label that the CLI prints alongside the draft. In production this posts to Slack via Block Kit.

**Today (lines 75-88):**

```python
def channel_for(tier: Tier) -> str:
    """
    STUB: production replacement posts a Slack DM (P1) or threaded message
    to `#sdr-priority-p2` / `#sdr-priority-p3` (P2/P3 digests).
    """
    return {
        "P1": "SDR direct DM (would post to #sdr-priority, 60s SLA)",
        "P2": "P2 daily digest (would post to #sdr-priority-p2, 9am ET daily)",
        "P3": "P3 weekly digest (would post to #sdr-priority-p3, Monday 9am ET)",
        "Discovery": "No SDR alert; fires Find Contacts at Company (6h SLA)",
        "Park": "No alert; rescore monthly",
    }[tier]
```

**In production:**

```python
from slack_sdk import WebClient

slack = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

def deliver(tier, draft, signal, company, contact) -> None:
    sdr_user_id = lookup_assigned_sdr(company.company_id)  # HubSpot owner OR round-robin

    if tier == "P1":
        slack.chat_postMessage(
            channel=sdr_user_id,                       # direct DM
            blocks=build_block_kit_draft(draft, signal, company, contact),
            text=f"P1 signal: {signal.signal_type} @ {company.company_name}",
        )
    elif tier == "P2":
        # P2 digest accumulates; a separate scheduled job posts the day's batch at 9am ET
        digest_store.add_p2_entry(signal, company, contact, draft)
    elif tier == "P3":
        digest_store.add_p3_entry(signal, company, contact, draft)
```

The Block Kit message is the rich Slack card the brief calls out with three buttons (`[Send via Smartlead]`, `[Edit]`, `[Skip]`). The current CLI HITL prompt in `hitl.py` is the local-terminal equivalent.

---

## 4. Smartlead Trigger (`run.py`)

[View on GitHub](./src/signal_engine/run.py)

Today prints a `[STUB]` line announcing what would happen. In production this fires the Smartlead campaign.

**Today (lines 328-339):**

```python
if decision == "send":
    print(
        f"[STUB] Would have triggered Smartlead campaign {campaign!r} "
        "with personalised_first_email custom variable populated."
    )
```

**In production:**

```python
import httpx

SMARTLEAD_API = "https://server.smartlead.ai/api/v1"

if decision == "send":
    campaign_id = SMARTLEAD_CAMPAIGNS[signal_type]  # e.g. "mento-signal-funding"

    # Step 1: add the lead to the campaign with personalised body as a custom var
    lead_response = httpx.post(
        f"{SMARTLEAD_API}/leads/{campaign_id}",
        headers={"X-API-Key": os.environ["SMARTLEAD_API_KEY"]},
        json={
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "company_name": company.company_name,
            "custom_fields": {
                "personalised_first_email": draft.body,
                "signal_type": signal_type,
                "signal_score": score.signal_score,
            },
        },
    )
    lead_id = lead_response.json()["lead_id"]

    # Step 2: fire the campaign immediately rather than waiting for next batch
    httpx.post(
        f"{SMARTLEAD_API}/campaigns/{campaign_id}/start-lead/{lead_id}",
        headers={"X-API-Key": os.environ["SMARTLEAD_API_KEY"]},
    )

    # Step 3: write back to HubSpot so the engagement is tracked
    hubspot.create_engagement(
        contact_id=contact.contact_id,
        engagement_type="EMAIL",
        body_preview=draft.body[:200],
        source="mento-signal-engine",
    )
```

Smartlead then handles the actual send + spintax + domain rotation + deliverability + follow-up cadence per the campaign's configured 4-5 step sequence.

---

## 5. Two Smaller Stubs (`run.py`)

**Manual-review queue** ([line 281](./src/signal_engine/run.py#L281)). When all three hooks fail the gate:

```python
print("      # STUB: would create a ticket in #signal-manual-review")
```

In production: post a structured Slack message to `#signal-manual-review` with the signal payload, the three failed candidates, and the gate's pass/fail reasoning so an SDR can write the email by hand.

**Skip decay** ([line 339](./src/signal_engine/run.py#L339)). When the SDR clicks Skip:

```python
print("[STUB] Skipped. Production would decay the signal and capture a reason.")
```

In production: write a `skipped_at` / `skip_reason` row to the Signals table. The recalibration job uses these to adjust the base weight per the Self-Improvement Loop in [`03_signal_scoring_framework.md`](../03_signal_scoring_framework.md).

---

## What Does NOT Change Going to Production

The 65% that's already real. Going live touches none of this code:

| Layer | File | Status |
|---|---|---|
| Score formula | [`scorer.py`](./src/signal_engine/scorer.py) | real, pure math |
| Tier routing math | [`router.py`](./src/signal_engine/router.py) lines 1-73 | real, pure mapping |
| Personalisation Agent | [`personaliser.py`](./src/signal_engine/personaliser.py) | real Claude API |
| Strong-Hook Gate | [`gate.py`](./src/signal_engine/gate.py) | real Claude API + deterministic checks |
| Draft Assembly Agent | [`assembler.py`](./src/signal_engine/assembler.py) | real Claude API + dash strip + word cap |
| Audit log | [`auditor.py`](./src/signal_engine/auditor.py) | real JSON writer |
| HITL CLI | [`hitl.py`](./src/signal_engine/hitl.py) | real; Slack Block Kit version replaces this for prod |

---

## Summary

Going-to-prod is roughly: **add five API integrations behind existing function signatures.** The orchestration logic, the agentic layer, the audit trail, and the test suite all carry over unchanged.

Environment variables the production deployment would add to `.env`:

```
# Signal detection
CRUNCHBASE_API_KEY=
APIFY_API_TOKEN=
FIRECRAWL_API_KEY=

# Enrichment waterfall
APOLLO_API_KEY=
OCEAN_API_KEY=
CLEARBIT_API_KEY=
ZOOMINFO_API_KEY=
PDL_API_KEY=
LEADMAGIC_API_KEY=

# CRM
HUBSPOT_ACCESS_TOKEN=

# Delivery
SLACK_BOT_TOKEN=
SMARTLEAD_API_KEY=
```

`ANTHROPIC_API_KEY` is already used in dev and stays.

---

## Source

- Parent overview: [`README.md`](./README.md)
- Verification walkthrough: [`README.md#verification-walkthrough--7-steps-in-10-minutes`](./README.md#verification-walkthrough--7-steps-in-10-minutes)
- Notion mirror: [STUB Swap Points (Notion)](https://www.notion.so/3647642d57d781d2ba1ed5cffd13401d)
