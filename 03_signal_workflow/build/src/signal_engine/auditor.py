"""JSON audit logging for one signal-engine run.

Every run writes a single JSON file to `audit/` capturing:

- signal payload
- enriched company + contact
- score breakdown (each multiplier visible)
- assigned tier and routing channel
- all three hook candidates with their gate verdicts
- selected hook and final draft
- SDR Send / Edit / Skip decision (and the edited body if edited)

Filename format: `audit/<timestamp>_<signal_id>.json`. The audit
directory sits at the project root, alongside src/, fixtures/, and
tests/.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from signal_engine.models import AuditEntry, Company, Contact, Signal

logger = logging.getLogger(__name__)

AUDIT_ROOT = Path(__file__).resolve().parent.parent.parent / "audit"


def new_entry(
    *,
    run_id: str,
    started_at: datetime,
    signal: Signal,
    company: Company,
    contact: Contact,
) -> AuditEntry:
    """Open an AuditEntry pre-populated with the three input records."""
    return AuditEntry(
        run_id=run_id,
        started_at=started_at,
        signal=_signal_to_dict(signal),
        company=asdict(company),
        contact=asdict(contact),
    )


def write(entry: AuditEntry, *, audit_root: Path | None = None) -> Path:
    """Write the audit entry to disk and return the path."""
    root = audit_root or AUDIT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    ts = entry.started_at.strftime("%Y%m%dT%H%M%SZ")
    safe_signal_id = entry.signal.get("signal_id", "unknown").replace("/", "_")
    path = root / f"{ts}_{safe_signal_id}.json"
    payload = _entry_to_dict(entry)
    path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n")
    logger.info("auditor: wrote %s", path)
    return path


def _entry_to_dict(entry: AuditEntry) -> dict[str, object]:
    """Convert an AuditEntry to a JSON-serialisable dict."""
    return {
        "run_id": entry.run_id,
        "started_at": entry.started_at.isoformat(),
        "completed_at": (entry.completed_at.isoformat() if entry.completed_at else None),
        "signal": entry.signal,
        "company": entry.company,
        "contact": entry.contact,
        "score": entry.score,
        "tier": entry.tier,
        "hook_candidates": entry.hook_candidates,
        "selected_hook": entry.selected_hook,
        "gate_decision": entry.gate_decision,
        "draft": entry.draft,
        "sdr_decision": entry.sdr_decision,
        "sdr_edited_body": entry.sdr_edited_body,
    }


def _signal_to_dict(signal: Signal) -> dict[str, object]:
    """Serialise the Signal dataclass with the date as ISO string."""
    raw = asdict(signal)
    raw["signal_date"] = signal.signal_date.isoformat()
    return raw


def _json_default(value: object) -> str:
    """Fallback serialiser for date / datetime values."""
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[no-any-return]
    raise TypeError(f"Unserialisable {type(value).__name__}: {value!r}")
