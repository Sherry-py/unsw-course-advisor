"""
Behavior logging for GateFix governance research.

Every submission attempt is recorded with:
  - Student profile (anonymised — no PII)
  - 4D-CQ dimension results
  - Authorization decision
  - Whether AI generation was triggered

This dataset constitutes the empirical corpus for:
    "When Knowing Is Not Enough" — JMIS, Sherry Lian
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gatefix import GateFixResult

LOG_FILE = Path(__file__).parent / "data" / "submission_log.json"


def _ensure_log() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("[]", encoding="utf-8")


def log_submission(
    specs:            list,
    goal_weights:     dict,
    completed_courses: list,
    credits:          str,
    load:             str,
    wam:              str,
    notes:            str,
    term:             str,
    lang:             str,
    gatefix_result,          # GateFixResult
    ai_generated:     bool,
) -> None:
    """Append one submission record to the JSON log."""
    _ensure_log()

    try:
        logs = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        logs = []

    gf = gatefix_result
    entry = {
        "id":               str(uuid.uuid4())[:8],
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "lang":             lang,
        "term":             term,
        "specs":            specs,
        "credits":          credits,
        "load":             load,
        "wam_provided":     bool(wam.strip()),
        "goals_count":      len(goal_weights),
        "completed_count":  len(completed_courses),
        "notes_provided":   bool(notes.strip()),
        "goal_weights_avg": (
            round(sum(goal_weights.values()) / len(goal_weights), 2)
            if goal_weights else 0.0
        ),
        # ── GateFix audit record ──────────────────────────────────────────
        "gatefix": {
            "decision":    gf.decision,
            "relevance":   gf.cq_vector.relevance,
            "coverage":    gf.cq_vector.coverage,
            "ordering":    gf.cq_vector.ordering,
            "robustness":  gf.cq_vector.robustness,
            "failed_dims": gf.failed_dims,
        },
        "ai_generated": ai_generated,
    }

    logs.append(entry)
    LOG_FILE.write_text(
        json.dumps(logs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_logs() -> list:
    """Return all log records, or empty list on failure."""
    _ensure_log()
    try:
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
