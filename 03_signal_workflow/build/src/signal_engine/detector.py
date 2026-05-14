"""Stage 1: Signal detection.

STUB: In production this module wraps Clay polling jobs against
- Crunchbase (Series B/C funding, every 12h)
- LinkedIn via Apify (new CHRO/CPO/VP People, every 24h)
- Greenhouse + Lever + Firecrawl (L&D postings, every 24h)
- Clearbit + PDL + LinkedIn (headcount growth, every 7d)

For the demo it loads pre-fired signal events from fixtures/signals/.
The fixture file naming convention is `<company>_<signal_type>.json`
(e.g. `linear_funding.json`). Each file matches the signal_payload
schema described in 03_outreach_drafts.md.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast

from signal_engine.models import Signal, SignalType

logger = logging.getLogger(__name__)

FIXTURE_ROOT = Path(__file__).resolve().parent.parent.parent / "fixtures" / "signals"

# Map (signal_type, company_id) -> fixture filename stem.
# Keeps the CLI invocation friendly: `--signal funding --company linear`
# resolves to `linear_funding.json` here without leaking the filename to the user.
_SIGNAL_FILE_MAP: dict[tuple[str, str], str] = {
    ("funding", "linear"): "linear_funding",
    ("exec_hire", "vanta"): "vanta_chro",
    ("ld_posting", "ramp"): "ramp_ld_posting",
    ("headcount_growth", "retool"): "retool_headcount",
}


def available_signals() -> list[tuple[str, str]]:
    """Return the (signal_type, company_id) pairs the demo can detect."""
    return list(_SIGNAL_FILE_MAP.keys())


def detect(
    signal_type: str,
    company_id: str,
    *,
    reference_date: date | None = None,
) -> Signal:
    """Return the Signal for `(signal_type, company_id)`.

    Fixtures express signal age as `days_ago` (so the demo stays fresh
    no matter when it's run); the literal `signal_date` is derived as
    `reference_date - days_ago`. If a fixture instead provides a
    literal `signal_date` field, that value is used unchanged — useful
    for tests that need a specific calendar date.

    STUB: production replacement is a Clay polling job firing into the
    Signals table. Here we read the matching fixture file from disk.
    """
    key = (signal_type, company_id)
    if key not in _SIGNAL_FILE_MAP:
        raise ValueError(
            f"No fixture for signal_type={signal_type!r} company_id={company_id!r}. "
            f"Available: {available_signals()}"
        )

    stem = _SIGNAL_FILE_MAP[key]
    path = FIXTURE_ROOT / f"{stem}.json"
    logger.info("detector: loading fixture %s", path.name)
    raw = json.loads(path.read_text())
    return _signal_from_dict(raw, reference_date=reference_date or date.today())


def _signal_from_dict(raw: dict[str, Any], *, reference_date: date) -> Signal:
    """Hydrate a Signal dataclass from the fixture JSON shape.

    Resolves `signal_date` from either the literal field or the
    `days_ago` offset, preferring the literal if both are present.
    """
    if "signal_date" in raw:
        signal_date = date.fromisoformat(raw["signal_date"])
    elif "days_ago" in raw:
        signal_date = reference_date - timedelta(days=int(raw["days_ago"]))
    else:
        raise ValueError(
            f"Fixture {raw.get('signal_id', '?')!r} must declare either "
            "'signal_date' (literal) or 'days_ago' (offset)."
        )

    return Signal(
        signal_id=raw["signal_id"],
        signal_type=cast(SignalType, raw["signal_type"]),
        signal_date=signal_date,
        company_id=raw["company_id"],
        signal_source=raw["signal_source"],
        signal_payload=raw["signal_payload"],
    )
