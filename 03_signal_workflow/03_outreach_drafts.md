# Part 3.5. Pre-Populated Outreach Drafts per Signal

Four templates, one per brief signal. Built using Pyrashyut's cold email framework (Trigger → Insight → Ask), Josh Braun's low-stakes principles, and Mento's brand voice. Each email is the first touch in a Smartlead sequence specific to the signal type.

## Brand Voice Rules

| Rule | Why |
|---|---|
| Operator to operator | Mento sells coaching from former CTOs, VPs, and Heads of. The email reads like a peer noticed something. |
| Specific over generic | Named investor, exact dollar amount, named prior company. Generic claims trigger disbelief. |
| Lower the stakes | "Worth 15 min?" not "Schedule a 30-min discovery call." Easy to say no makes "yes" more common. |
| Lead with their world | "You/your" dominates. Don't open with who we are. |
| One ask, binary yes/no CTA | Single low-friction question, replyable in five words. |
| Under 70 words total | Senior People execs scan, don't read. |
| No filler, no jargon | Cut "I hope this finds you well", "I wanted to reach out", "leverage", "circle back". |
| British English | No exclamation marks, no emojis. |

## 4-Part Email Structure

Every email is four parts in this order.

| Part | Purpose | Length |
|---|---|---|
| **Personalisation hook** | Reference the signal directly. Sound like one operator writing to another. | 1-2 sentences |
| **Insight** | Pattern Mento sees at similar companies hitting this signal, with named proof | 2-3 sentences |
| **Free Value** | What Mento can give: playbook reference, named-customer comparison, specific case detail | 1 sentence |
| **Soft CTA** | Single binary yes/no question | 1 sentence |

Signoff: `— {{sdr_signature}}`

## Personalisation Layer Detail

The `{{ai_hook}}` slot is filled by the **Personalisation Agent** in Stage 4 of the workflow (Part 3.2). It is not template text. It is generated per prospect per signal event.

### What Feeds the Agent

| Source | Data Pulled |
|---|---|
| Signals table | signal_type, signal_date, signal_payload (full JSON of the source event) |
| Companies table | company_name, normalized_domain, industry, recent_news (Firecrawl scrape of /blog, /press, /news), customer_logos_referenced |
| Contacts table | prospect_first_name, prospect_title, personal_linkedin_url, linkedin_summary (LeadMagic), recent_posts (LinkedIn via Apify), prior_company |
| Mento voice doc | Brand rules, banned phrases, three sample emails that closed |

### Agent Prompt (Claude API via Clay Use AI Column)

```
You are writing the opening 1-2 sentences of a cold email to a senior People exec.

Prospect: {{prospect_first_name}}, {{prospect_title}} at {{company_name}}
Signal: {{signal_type}} on {{signal_date}}
Signal payload: {{signal_payload_json}}
LinkedIn summary: {{linkedin_summary}}
Recent activity: {{recent_posts}}
Company news: {{company_recent_news}}

Output: 1-2 sentences referencing the signal directly. Specific, no salesy hedging.
Sound like one operator writing to another.

Must reference at least one of:
- Named investor or dollar amount (funding signal)
- Named prior company or exact role (exec hire signal)
- Exact job title posted (L&D posting signal)
- Specific headcount numbers (growth signal)

Reject if:
- Generic ("congrats on the recent news")
- Cites info not in inputs
- Over 50 words
- Uses banned phrases ("hope this finds you well", "wanted to reach out", "leverage", "synergy")
```

### Strong-Hook Gate (Deterministic Filter)

| Criterion | Pass | Fail |
|---|---|---|
| Specificity | Names investor / dollar amount / prior company / exact title / headcount | Generic |
| Timeliness | Trigger within last 60 days | Stale |
| Buyer context | References prospect's role or activity | Generic to anyone at that company |
| Length | Under 50 words | Over 50 |
| Voice | Operator tone, no hedging | Salesy or templated |

After the agent produces three hook candidates, the gate picks the strongest. If all three fail, the signal routes to manual review queue. No draft delivered to SDR.

---

## Template 1: Series B/C Funding

**Trigger.** Crunchbase API detects a new Series B or C round in the last 30 days at a target Company.

**Subject (lowercase, 2-4 words):** `manager bench`, `post-funding pattern`, or `scaling note`

**Body:**

```
Hi {{prospect_first_name}},

{{ai_hook}}

Pattern post-funding: hiring outpaces the manager bench by 90 days. Performance dips at the team-lead layer. Brex and Vercel saw it. Their People teams worked with our coaches in months 3-9.

Happy to share the playbook.

Worth 15 minutes?

— {{sdr_signature}}
```

**LinkedIn variant:** `Hi {{prospect_first_name}}, saw {{company_name}}'s {{funding_round}}. Pattern post-funding is the manager bench falling behind hiring. Have a playbook from Brex and Vercel if useful.`

**Trigger variables.** `funding_round`, `funding_amount`, `funding_date`, `lead_investor`.

### Live Example: Linear's $82M Series C (Oct 2024, Accel-Led)

Signal payload received by the agent:

```
{ "round": "Series C", "amount_usd": 82000000, "date": "2024-10-31", "lead_investor": "Accel" }
prospect: Karri Saarinen, CEO
company_recent_news: "Linear launched Customer Requests; agent-triage features rolling out"
```

Hook selected by the gate:

> Saw Linear's $82M Series C from Accel close last week. Congrats. With the agent-triage rollout in parallel, your headcount math probably gets interesting fast.

Final assembled email:

```
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

— Alex
```

**65 words.** Subject 2 words.

---

## Template 2: New CHRO / CPO / VP People

**Trigger.** LinkedIn (Apify) detects a new CHRO, CPO, or VP People hire in the last 60 days at a target Company.

**Subject:** `first 90 days`, `coaching playbook`, or `welcome`

**Body:**

```
Hi {{prospect_first_name}},

{{ai_hook}}

Most People execs start a coaching program in months 2-6 of tenure. Coaches are former CHROs and VPs People who've sat in the same first-investment call.

Happy to share what worked at Brex and Gusto.

Worth 20 minutes?

— {{sdr_signature}}
```

**LinkedIn variant:** `Hi {{prospect_first_name}}, welcome to {{company_name}}. Most People execs run a coaching program in months 2-6. Have notes from Brex and Gusto if useful.`

**Trigger variables.** `prospect_first_name`, `prospect_title`, `prospect_start_date`, `prospect_prior_company`.

### Live Example: Vanta Hires New CHRO

```
{ "role": "CHRO", "prior_company": "Coda", "start_date": "2024-11-15" }
prospect: Sarah Chen, CHRO
linkedin_summary: "VP People at Coda for 4 years, scaled team from 80 to 600 headcount"
```

Hook selected:

> Welcome to Vanta, Sarah. Coda to a Series B compliance scale-up is an interesting move. The 80-to-600 scale you ran at Coda is rare context.

Final email:

```
Subject: first 90 days

Hi Sarah,

Welcome to Vanta. Coda to a Series B compliance scale-up is an interesting
move. The 80-to-600 scale you ran at Coda is rare context.

Most People execs start a coaching program in months 2-6 of tenure.
Coaches are former CHROs and VPs People who've sat in the same
first-investment call.

Happy to share what worked at Brex and Gusto.

Worth 20 minutes?

— Alex
```

**65 words.**

---

## Template 3: L&D Job Posting

**Trigger.** Greenhouse, Lever, or Firecrawl detects a posting for "Manager Development", "Leadership Development", "L&D Director", "Head of Talent Development", or "Director of Learning" at a target Company.

**Subject:** `before week 1`, `L&D hire window`, or `4-month gap`

**Body:**

```
Hi {{prospect_first_name}},

{{ai_hook}}

The 4-month gap before they start is the best window to set up a cohort they inherit day one. Anthropic and Hims did this. Saves 3 months after the leader lands.

Happy to share how that handoff worked.

Worth 15 minutes?

— {{sdr_signature}}
```

**LinkedIn variant:** `Hi {{prospect_first_name}}, saw the {{job_title}} posting. The 4-month gap before they start is the window to set up a cohort they inherit day one. Worth a quick chat?`

**Trigger variables.** `job_title`, `job_posting_url`, `job_posting_date`.

### Live Example: Ramp Posts Director of Leadership Development

```
{ "job_title": "Director, Leadership Development", "posting_date": "2024-12-01" }
prospect: Jen Liu, VP People at Ramp
linkedin_summary: "VP People at Ramp 2 years, prior Director Talent at Stripe"
```

Hook selected:

> Caught the Director of Leadership Development posting on your Greenhouse last week. Hiring for the function usually means budget is approved and you're sizing the program.

Final email:

```
Subject: before week 1

Hi Jen,

Caught the Director of Leadership Development posting on your Greenhouse
last week. Hiring for the function usually means budget is approved and
you're sizing the program.

The 4-month gap before they start is the best window to set up a cohort
they inherit day one. Anthropic and Hims did this. Saves 3 months after
the leader lands.

Happy to share how that handoff worked.

Worth 15 minutes?

— Alex
```

**69 words.**

---

## Template 4: Headcount Growth 20%+ in 6 Months

**Trigger.** Clearbit, PDL, or LinkedIn shows headcount has grown more than 20% in the last 6 months at a target Company.

**Subject:** `bench math`, `manager math`, or `scaling pattern`

**Body:**

```
Hi {{prospect_first_name}},

{{ai_hook}}

Math at this stage: every 30 ICs need ~5 managers. You're promoting first-time managers into roles their training hasn't caught up to. Gusto and 1Password ran structured coaching for that group. 6-month programs, 98% utilisation, 93% performance lift.

Happy to share their setup.

Worth 20 minutes?

— {{sdr_signature}}
```

**LinkedIn variant:** `Hi {{prospect_first_name}}, {{company_name}} hit {{growth_pct}} growth in 6 months. Usually means a wave of first-time managers. Coaching playbooks from Gusto and 1Password if useful.`

**Trigger variables.** `headcount_old`, `headcount_new`, `growth_pct`, `new_managers_needed`.

### Live Example: Retool Grows 250 to 320 (28% in 6 Months)

```
{ "headcount_old": 250, "headcount_new": 320, "growth_pct": 28, "window_months": 6 }
prospect: Jennifer Saavedra, Head of People at Retool
linkedin_summary: "Head of People at Retool 1 year, prior CHRO at Dropbox"
```

Hook selected:

> Saw Retool went from 250 to 320 in 6 months. 28% growth, so probably 12+ new managers in the next quarter.

Final email:

```
Subject: bench math

Hi Jennifer,

Saw Retool went from 250 to 320 in 6 months. 28% growth, so probably 12+
new managers in the next quarter.

Math at this stage: every 30 ICs need ~5 managers. You're promoting
first-time managers into roles their training hasn't caught up to. Gusto
and 1Password ran structured coaching for that group. 6-month programs,
98% utilisation, 93% performance lift.

Happy to share their setup.

Worth 20 minutes?

— Alex
```

**69 words.**

---

## Pre-Populate Path Into Smartlead (Email Sequencer)

Each signal type has its own Smartlead campaign with a multi-step sequence. The first email contains a `{{personalised_first_email}}` custom variable that holds the AI-assembled draft.

### Flow When SDR Clicks Send

1. SDR clicks `[Send via Smartlead]` in the Slack draft message
2. Clay calls Smartlead API:
   - `POST /api/v1/leads/{campaign_id}` adds the lead with all custom variables populated
   - `POST /api/v1/campaigns/{campaign_id}/start-lead/{lead_id}` fires the first email immediately
3. Smartlead handles assignment, spintax, delivery, domain rotation, deliverability monitoring, and follow-up cadence
4. Smartlead writes activity back to HubSpot via the reply-detection webhook

### One Smartlead Campaign per Signal Type

| Signal | Smartlead Campaign |
|---|---|
| Series B/C funding | `mento-signal-funding` |
| New CHRO / CPO / VP People | `mento-signal-exec-hire` |
| L&D job posting | `mento-signal-ld-posting` |
| Headcount growth 20%+ | `mento-signal-headcount-growth` |

Each campaign has 4-5 follow-up emails. Follow-ups are written manually, stored in Smartlead, and follow the same brand-voice rules. Only the first email is AI-personalised because that's where the trigger context lives. Follow-ups rotate through three angles (efficiency, proof, single-question close) per the Pyrashyut framework.

## Quality Gates Before Send

The Strong-Hook Gate filters drafts before they reach the SDR. Drafts that pass all five criteria land in Slack. Drafts that fail any criterion route to the manual review queue, no draft sent.

Better to send no draft than a generic one to a senior People exec at a target account.
