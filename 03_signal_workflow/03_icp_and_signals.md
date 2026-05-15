# 3.1 ICP and Intent Signals

## ICP

### Firmographics

| Attribute | Target |
|---|---|
| Headcount | 500 to 5,000 employees |
| Stage | Series B/C or later (includes late Series A with $50M+ raised) |
| Sector | B2B tech: SaaS, AI-native, cloud infrastructure, dev tools, fintech-SaaS, Sales/Marketing & CS SaaS |
| Geography | US-headquartered, English-speaking |
| Estimated ARR | $20M to $300M |
| HQ density | NYC, SF, Seattle, Austin, Boston (where Mento's coach roster has bench depth) |

### Technographics (Positive)

- **HR platforms:** Workday, BambooHR, Rippling, Personio, Gusto
- **Performance management:** Lattice, Culture Amp, 15Five
- **Learning platforms:** LinkedIn Learning, Udemy Business, Coursera Business, Disco
- **Communication and collaboration:** Slack, Notion (Mento integrates cleanly here)
- **Modern dev stack:** Vercel, AWS, Linear, Datadog (proxy for tech-forward culture)

### Technographics (Negative)

- ATS-only without any performance or learning platform (basic HR ops, no L&D maturity)
- SAP SuccessFactors or Oracle HCM only (traditional enterprise pattern)
- No performance management tool of any kind (under-invested in People function)

### Org Signals

- Has a named Head of L&D, Head of Manager Development, Director of Talent, or similar
- Public company values that explicitly call out leadership, growth, or manager quality
- Existing internal manager training program (signals they take L&D seriously, want a partner)
- Recent reorg, restructuring, or geographic expansion announcement
- OKRs or company-wide goals mentioning leadership development, manager effectiveness, or retention
- Mid-management title proliferation in role tree

### Buying Committee

| Role | Title Patterns | Role In Deal |
|---|---|---|
| Economic | CHRO, CPO, VP People, Head of People, SVP People | Signs the contract |
| Champion | Head of L&D, Head of Talent Management, Manager Development, Head of Learning, Senior Manager People Operations | Runs the cohort, internal advocate |
| End User | Managers, directors, senior ICs, executives in the cohort | Receives the coaching |
| Procurement | Finance, Legal, Procurement, Controller, General Counsel | Touches deals over ~$75k ACV |

### Negative ICP

- Sub-200 headcount (no L&D budget, founder-led management still works)
- Traditional non-tech enterprises (long procurement, low cultural fit)
- Agencies and services firms (different unit economics)
- Regulated finance and government (sales cycle kills the motion at Mento's stage)
- Recently failed coaching pilot at a competitor (rebuild trust takes 18+ months)
- Companies with active mass RIFs in management ranks (budget is freezing)

---

## Eleven-Signal Portfolio

Four from the brief plus seven additional. Diversified across six categories so no single source failure kills the engine.

### Original Four (from the Brief)

| # | Signal | 1st Source | Additional Sources | Weight |
|---|---|---|---|---|
| 1 | Series B/C funding (last 30d) | Clay | Crunchbase API, CommonRoom API | **4 (P1)** |
| 2 | Headcount growth 20%+ in 6 months | Clay | Clearbit, PDL, LinkedIn, CommonRoom API | 2 (P3) |
| 3 | New CHRO/CPO/VP People (last 60d) | Clay | LinkedIn API, CommonRoom API | 3 (P2) |
| 4 | Active L&D job posting (generic) | Clay | Greenhouse, Lever, Firecrawl, CommonRoom API | 3 (P2) |

### Seven Additional Signals

| # | Signal | 1st Source | Additional Sources | Detection | Why It Matters | Weight |
|---|---|---|---|---|---|---|
| 5 | Net-new manager hire surge | Clay | LinkedIn API, CommonRoom API | 3+ new "Manager" titles in 60d | Doubling management bench triggers coaching demand inside 6 months | 2 (P3) |
| 6 | Manager promotion at known contact | Clay | LinkedIn API (track existing contacts), CommonRoom API | IC promoted to Manager / Senior Manager / Director in last 90d | Newly-promoted managers are the highest-fit segment. Person-level identification, immediate timing, named champion already in HubSpot. | **4 (P1)** |
| 7 | RIF with management retained | Layoffs.fyi, LinkedIn diff | (none) | Layoff filed OR 10%+ non-mgmt headcount drop in 30d | Post-RIF orgs double down on retained talent | 2 (P3) |
| 8 | New L&D / Manager Development role posted | Clay | Greenhouse, Lever via Firecrawl, CommonRoom API | Posting with "Manager Development", "Leadership Development", "L&D Director", "Head of Talent Development" | Single cleanest buying-intent signal. They are literally hiring someone whose job is to spend the L&D budget. The 4-month gap between job posting and hire start is the ideal partnership-pitch window. | **4 (P1)** |
| 9 | Exec LinkedIn engagement on leadership content | Clay | LinkedIn API, CommonRoom API | Named exec likes / comments / shares coaching or manager content in 30d | Social engagement precedes active vendor research by 4-6 weeks | 2 (P3) |
| 10 | Glassdoor / Comparably manager sentiment drop | Firecrawl, Apify scraping (monthly) | (none) | Senior Mgmt sub-score drops 0.3+ OR net-negative review velocity | Predicts internal pressure on People team to invest in mgmt improvement | 2 (P3) |
| 11 | Existing customer expansion signal | HubSpot deal data, LinkedIn | (none) | Customer headcount up 30%+ since cohort start OR new dept head post-cohort | Expansion is cheapest acquisition. No procurement friction, no security review. Closes 2 to 3x faster than net-new at higher gross margin. Catches before QBR. | **4 (P1)** |

---

## Signal Portfolio Coverage

Brief's four plus seven additional gives an 11-signal portfolio across six categories. Diversified enough that no single source failure kills the engine.

| Category | Signals | Coverage |
|---|---|---|
| Funding inflection | Series B/C funding | 1 signal |
| Headcount inflection | 20%+ growth, manager-hire surge | 2 signals |
| Exec change | New CHRO/CPO/VP People | 1 signal |
| Job-posting intent | L&D postings, Manager Development roles | 2 signals |
| Org disruption | RIF with management retention, manager promotion events | 2 signals |
| Public and social intent | Exec LinkedIn engagement, Glassdoor sentiment drop | 2 signals |
| Customer expansion | Headcount post-cohort, new dept head | 1 signal |

## P1 Signal Distribution

Four signals at P1 (weight 4). One per high-conversion mechanic.

| Signal | Conversion Edge |
|---|---|
| Series B/C funding | New budget unlocked, scaling org needs management infrastructure |
| Manager promotion at a known contact | Person-level identification, immediate timing, named champion already in HubSpot |
| New L&D / Manager Development role posted | Direct hiring for the function, ideal partnership pitch window before new hire lands |
| Existing customer expansion signal | Lowest CAC, fastest close, no procurement friction |

P1 signals get prioritised routing (direct DM to assigned SDR within 60 seconds). P2 to a daily digest. P3 to a weekly digest. Defined in Part 3.4.

---

## How This Feeds the Rest of Part 3

| Downstream Artifact | What It Uses |
|---|---|
| 3.2 Workflow architecture (text) | All 11 signals as the trigger surface |
| 3.3 Workflow architecture diagram | Visual of signal-to-routing-to-draft pipeline |
| 3.4 Signal scoring framework | Base weights here combined with recency decay and ICP fit multiplier |
| 3.5 Pre-populated outreach drafts | One draft template per signal type, anchored to trigger context |
| 3.6 Clay workflow build doc | Signals table ingestion per source plus routing logic |
