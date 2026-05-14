"""Stage 2: Enrich the Company and best buyer-committee Contact.

STUB: In production this is a Clay waterfall against
- Apollo + Ocean.io + Clearbit + ZoomInfo + PDL + Crunchbase + BuiltWith for
  Company attributes (headcount, funding stage, HR tech stack, ICP totals)
- Apollo + LeadMagic + PDL + LinkedIn (Apify) for the Contact record, with
  LinkedIn summaries and recent posts
- HubSpot CRM API for engagement score + lifecycle stage

For the demo it loads the matching fixture for the Company referenced by
the Signal, plus the canonical buyer contact for that company.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

from signal_engine.models import BuyerRole, Company, Contact, Signal

logger = logging.getLogger(__name__)

COMPANIES_ROOT = Path(__file__).resolve().parent.parent.parent / "fixtures" / "companies"
CONTACTS_ROOT = Path(__file__).resolve().parent.parent.parent / "fixtures" / "contacts"

# Map company_id -> canonical buyer contact fixture stem.
_BUYER_CONTACT: dict[str, str] = {
    "linear": "linear_karri",
    "vanta": "vanta_sarah",
    "ramp": "ramp_jen",
    "retool": "retool_jennifer",
}


def enrich(signal: Signal) -> tuple[Company, Contact]:
    """Return the (Company, Contact) pair attached to this signal.

    STUB: production replacement is a Clay enrichment waterfall + HubSpot
    lookup. Here we hydrate from fixtures.
    """
    company = _load_company(signal.company_id)
    contact = _load_best_contact(signal.company_id)
    logger.info(
        "enricher: %s icp_total=%d, contact=%s %s (%s)",
        company.company_name,
        company.icp_total,
        contact.first_name,
        contact.last_name,
        contact.title,
    )
    return company, contact


def _load_company(company_id: str) -> Company:
    """Hydrate a Company dataclass from fixtures/companies/<id>.json."""
    path = COMPANIES_ROOT / f"{company_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No company fixture for {company_id!r} at {path}. "
            f"Available: {[p.stem for p in COMPANIES_ROOT.glob('*.json')]}"
        )
    raw: dict[str, Any] = json.loads(path.read_text())
    return Company(
        company_id=raw["company_id"],
        company_name=raw["company_name"],
        domain=raw["domain"],
        linkedin_url=raw["linkedin_url"],
        headcount=raw["headcount"],
        industry=raw["industry"],
        funding_stage=raw["funding_stage"],
        hr_tech_stack=raw["hr_tech_stack"],
        icp_fit=raw["icp_fit"],
        icp_timing=raw["icp_timing"],
        icp_access=raw["icp_access"],
        icp_intent=raw["icp_intent"],
        icp_budget=raw["icp_budget"],
        icp_total=raw["icp_total"],
        lifecycle_stage=raw["lifecycle_stage"],
        recent_news=raw["recent_news"],
    )


def _load_best_contact(company_id: str) -> Contact:
    """Hydrate the canonical buyer contact for the company.

    STUB: production replacement chooses the highest-proximity contact from
    the Contacts table. Here we have one canonical contact per company.
    """
    if company_id not in _BUYER_CONTACT:
        raise FileNotFoundError(f"No canonical buyer contact mapped for {company_id!r}")
    stem = _BUYER_CONTACT[company_id]
    path = CONTACTS_ROOT / f"{stem}.json"
    raw: dict[str, Any] = json.loads(path.read_text())
    return Contact(
        contact_id=raw["contact_id"],
        company_id=raw["company_id"],
        first_name=raw["first_name"],
        last_name=raw["last_name"],
        email=raw["email"],
        title=raw["title"],
        linkedin_url=raw["linkedin_url"],
        buyer_role=cast(BuyerRole, raw["buyer_role"]),
        engagement_score=raw["engagement_score"],
        linkedin_summary=raw["linkedin_summary"],
        recent_posts=raw["recent_posts"],
    )
