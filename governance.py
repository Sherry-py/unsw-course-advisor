"""
GateFix 4D-CQ Pre-Execution Governance Engine
Paper: "GateFix: A Pre-Execution Governance Framework for AI-Driven Academic Advising"
       IEEE/TETCI submission — Sherry

Architecture:
    f(C, g) = φ(h(C, g))
    h: user context → quality vector CQ (4 dimensions)
    φ: CQ → {PASS, CLARIFY, REFUSE}

4D-CQ Dimension mapping (course advisor domain):
    Relevance  [CRITICAL]     — Is a specialisation selected? (domain scope)
    Coverage   [CRITICAL]     — Are goals provided? (intent completeness)
    Ordering   [NON-CRITICAL] — Is UOC/progress context logically consistent?
    Robustness [NON-CRITICAL] — Are supporting details (WAM, notes) present?

Decision rule φ:
    Any CRITICAL dimension DEFECT  → REFUSE  (block AI call)
    Any NON-CRITICAL dim DEFECT    → CLARIFY (proceed with notice)
    All OK                         → PASS    (proceed silently)
"""

from dataclasses import dataclass, field, asdict
from typing import Literal
import uuid
import json
import os
from datetime import datetime, timezone

Decision = Literal["PASS", "CLARIFY", "REFUSE"]
Status   = Literal["OK", "DEFECT"]


@dataclass
class CQVector:
    relevance:  Status = "OK"   # CRITICAL
    coverage:   Status = "OK"   # CRITICAL
    ordering:   Status = "OK"   # NON-CRITICAL
    robustness: Status = "OK"   # NON-CRITICAL


@dataclass
class GateResult:
    decision:    Decision
    cq:          CQVector
    failed_dims: list = field(default_factory=list)
    refuse_key:  str = ""   # translation key for user-facing message
    clarify_key: str = ""   # translation key for user-facing hint


def evaluate(
    specs: list,
    goals: list,
    credits: str,
    completed: list,
    wam: str,
    notes: str,
) -> GateResult:
    """
    h(C, g): map user context → CQ vector
    φ(CQ)  : apply decision rule
    """
    cq = CQVector()
    failed = []

    # ── Relevance [CRITICAL]: specialisation defines the query domain ──────
    if not specs:
        cq.relevance = "DEFECT"
        failed.append("relevance")

    # ── Coverage [CRITICAL]: goals are required for aligned recommendations ─
    if not goals:
        cq.coverage = "DEFECT"
        failed.append("coverage")

    # ── Ordering [NON-CRITICAL]: UOC vs completed course count consistency ──
    try:
        uoc_left = int(credits.split()[0])
        courses_done = len(completed)
        # rough heuristic: each 6-UOC course = 1 unit; 96 max
        max_done = (96 - uoc_left) // 6
        if courses_done > max_done + 4:   # tolerance of 4 courses
            cq.ordering = "DEFECT"
            failed.append("ordering")
    except Exception:
        pass  # don't penalise if parsing fails

    # ── Robustness [NON-CRITICAL]: richer context → higher output quality ───
    wam_missing   = not wam.strip()
    notes_missing = not notes.strip()
    if wam_missing and notes_missing:
        cq.robustness = "DEFECT"
        failed.append("robustness")

    # ── φ: decision rule ────────────────────────────────────────────────────
    critical_failed = cq.relevance == "DEFECT" or cq.coverage == "DEFECT"

    if critical_failed:
        decision = "REFUSE"
        # pick the most specific refuse message key
        if cq.relevance == "DEFECT" and cq.coverage == "DEFECT":
            refuse_key = "gf_refuse_both"
        elif cq.relevance == "DEFECT":
            refuse_key = "gf_refuse_relevance"
        else:
            refuse_key = "gf_refuse_coverage"
        return GateResult(decision="REFUSE", cq=cq, failed_dims=failed,
                          refuse_key=refuse_key)

    if cq.ordering == "DEFECT" or cq.robustness == "DEFECT":
        clarify_key = "gf_clarify_ordering" if cq.ordering == "DEFECT" else "gf_clarify_robustness"
        return GateResult(decision="CLARIFY", cq=cq, failed_dims=failed,
                          clarify_key=clarify_key)

    return GateResult(decision="PASS", cq=cq, failed_dims=[])


# ── Structured logging (thesis data, no PII) ────────────────────────────────

LOG_PATH = os.path.join(os.path.dirname(__file__), "gatefix_log.jsonl")


def log_submission(gate: GateResult, profile: dict, ai_generated: bool):
    """Append one JSONL record for every submission (REFUSE/CLARIFY/PASS)."""
    record = {
        "id":           str(uuid.uuid4()),
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "decision":     gate.decision,
        "dim_relevance":  gate.cq.relevance,
        "dim_coverage":   gate.cq.coverage,
        "dim_ordering":   gate.cq.ordering,
        "dim_robustness": gate.cq.robustness,
        "failed_dims":    gate.failed_dims,
        "ai_generated":   ai_generated,
        # anonymised profile signals (no names, no free-text)
        "n_specs":        profile.get("n_specs", 0),
        "n_goals":        profile.get("n_goals", 0),
        "n_completed":    profile.get("n_completed", 0),
        "credits_left":   profile.get("credits_left", ""),
        "has_wam":        profile.get("has_wam", False),
        "has_notes":      profile.get("has_notes", False),
        "load":           profile.get("load", ""),
        "lang":           profile.get("lang", ""),
        # Memory Layer fields — session-level tracking
        "session_id":             profile.get("session_id", ""),
        "submit_count":           profile.get("submit_count", 0),
        "counterfactual_decision":profile.get("counterfactual_decision", ""),
        "overlap_rate":           profile.get("overlap_rate", None),
    }
    # Write to local JSONL
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # Dual-write to Supabase (cloud persistence)
    try:
        import supabase_logger
        supabase_logger.append_record("gatefix_log", record)
    except Exception:
        pass
