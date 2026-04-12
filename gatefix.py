"""
GateFix: Pre-execution authorization layer for UNSW MCom Course Advisor
Implements the 4D-CQ framework extending Wang & Strong's IQ taxonomy.

Paper: "When Knowing Is Not Enough: Pre-Execution Governance for Intelligent Systems"
       Sherry Lian, JMIS submission

Architecture:
    f(C, g) = φ(h(C, g))
    h: context → S = (s_rel, s_cov, s_ord, s_rob) ∈ {OK, DEFECT}^4
    φ: S → {PASS, CLARIFY, REFUSE}

Dimension mapping to course-advisor execution context:
    Relevance  (CRITICAL)     — spec-goal semantic alignment
    Coverage   (CRITICAL)     — required information completeness for authorization
    Ordering   (non-critical) — prerequisite logical readiness
    Robustness (non-critical) — input anomaly / consistency detection
"""

from dataclasses import dataclass, field
from typing import Literal, Dict, List, Tuple, Set

DimResult   = Literal["OK", "DEFECT"]
AuthDecision = Literal["PASS", "CLARIFY", "REFUSE"]


# ── Domain knowledge: specialization → relevant goal clusters ─────────────────
SPEC_GOAL_MAP: Dict[str, List[str]] = {
    "Accounting": [
        "金融/投行", "提高 WAM", "留澳工作签证",
        "Finance / Investment Banking", "Improve WAM", "Australian work visa",
    ],
    "Finance": [
        "金融/投行", "留澳工作签证", "创业",
        "Finance / Investment Banking", "Australian work visa", "Entrepreneurship",
    ],
    "Economics and Finance": [
        "金融/投行", "创业", "学习 AI/数据",
        "Finance / Investment Banking", "Entrepreneurship", "Learn AI / Data",
    ],
    "Marketing": [
        "科技行业就业", "创业", "留澳工作签证",
        "Tech industry jobs", "Entrepreneurship", "Australian work visa",
    ],
    "Human Resource Management": [
        "咨询 Consulting", "留澳工作签证", "提高 WAM",
        "Consulting", "Australian work visa", "Improve WAM",
    ],
    "International Business": [
        "留澳工作签证", "咨询 Consulting", "创业",
        "Australian work visa", "Consulting", "Entrepreneurship",
    ],
    "Information Systems": [
        "科技行业就业", "学习 AI/数据", "咨询 Consulting", "创业",
        "Tech industry jobs", "Learn AI / Data", "Consulting", "Entrepreneurship",
    ],
    "Global Sustainability and Social Impact": [
        "创业", "留澳工作签证", "咨询 Consulting",
        "Entrepreneurship", "Australian work visa", "Consulting",
    ],
    "Risk Management": [
        "金融/投行", "咨询 Consulting", "留澳工作签证",
        "Finance / Investment Banking", "Consulting", "Australian work visa",
    ],
    "Strategy and Innovation": [
        "创业", "科技行业就业", "咨询 Consulting", "继续读博士 PhD",
        "Entrepreneurship", "Tech industry jobs", "Consulting", "Continue to PhD",
    ],
    "AI in Business and Society": [
        "学习 AI/数据", "科技行业就业", "创业", "继续读博士 PhD",
        "Learn AI / Data", "Tech industry jobs", "Entrepreneurship", "Continue to PhD",
    ],
    "General / Undecided": [],   # always relevant — no constraint
}

UOC_PER_COURSE = 6  # MCom standard: 6 UOC per course


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class CQVector:
    """4-dimensional context quality vector S ∈ {OK, DEFECT}^4"""
    relevance:  DimResult
    coverage:   DimResult
    ordering:   DimResult
    robustness: DimResult
    relevance_reason:  str = ""
    coverage_reason:   str = ""
    ordering_reason:   str = ""
    robustness_reason: str = ""


@dataclass
class GateFixResult:
    """Authorization output: decision + quality vector + audit trail"""
    decision:    AuthDecision
    cq_vector:   CQVector
    failed_dims: List[str] = field(default_factory=list)
    passed_dims: List[str] = field(default_factory=list)


# ── Dimension check functions (h decomposed per dimension) ────────────────────

def _check_relevance(
    specs: List[str],
    goal_weights: Dict[str, int],
) -> Tuple[DimResult, str]:
    """
    s_rel: task-context semantic alignment.
    DEFECT when: top-priority goals (weight >= 4) have zero lexical/semantic
    intersection with any selected specialization's domain cluster.
    Rationale: recommending Accounting courses to a student whose primary goal
    is 'Learn AI/Data' violates relevance and will produce unhelpful output.
    """
    if not goal_weights:
        return "OK", "No goals specified — relevance check skipped (Coverage will catch this)."

    high_priority = {g for g, w in goal_weights.items() if w >= 4}
    if not high_priority:
        return "OK", "No high-priority goals (weight ≥ 4) to cross-check."

    for spec in specs:
        if spec == "General / Undecided":
            return "OK", "General / Undecided is relevant to all goal directions."
        relevant = SPEC_GOAL_MAP.get(spec, [])
        for goal in high_priority:
            for rg in relevant:
                if rg.lower() in goal.lower() or goal.lower() in rg.lower():
                    return "OK", f"'{spec}' aligns with high-priority goal '{goal}'."

    spec_str  = " & ".join(specs)
    goal_str  = "; ".join(sorted(high_priority))
    return (
        "DEFECT",
        f"High-priority goals [{goal_str}] do not align with {spec_str}. "
        "Your specialization choice may not serve your stated career direction — "
        "consider switching to a more relevant stream or adding a second specialization.",
    )


def _check_coverage(
    goal_weights:     Dict[str, int],
    eligible_courses: List[dict],
    credits_str:      str,
    load_str:         str,
) -> Tuple[DimResult, str]:
    """
    s_cov: required information completeness for authorization.
    DEFECT when:
      (a) no graduation goals selected — AI cannot tailor recommendations;
      (b) remaining UOC insufficient to accommodate requested course load;
      (c) eligible course pool smaller than requested load.
    """
    # (a) Goals are the primary context signal for recommendation quality
    if not goal_weights:
        return (
            "DEFECT",
            "No graduation goals selected. Without goals the AI cannot assess "
            "course-goal fit — a core part of the recommendation. "
            "Please select at least one goal before generating.",
        )

    # (b) UOC feasibility
    try:
        remaining_uoc = int(credits_str.split()[0])
    except Exception:
        remaining_uoc = 96
    try:
        load_num = int(load_str[0])
    except Exception:
        load_num = 3
    required_uoc = load_num * UOC_PER_COURSE
    if remaining_uoc < required_uoc:
        return (
            "DEFECT",
            f"You requested {load_num} course(s) ({required_uoc} UOC) "
            f"but only {remaining_uoc} UOC remain. "
            "Please reduce your course load or update your remaining UOC.",
        )

    # (c) Pool size check
    if len(eligible_courses) < load_num:
        return (
            "DEFECT",
            f"Only {len(eligible_courses)} eligible course(s) remain in your "
            f"specialization pool, but you requested {load_num}. "
            "Add a second specialization or reduce course load.",
        )

    return (
        "OK",
        f"All required fields complete — {len(eligible_courses)} eligible courses "
        f"available for {load_num} recommendation slot(s).",
    )


def _check_ordering(
    completed_codes:  Set[str],
    eligible_courses: List[dict],
    course_meta:      dict,
) -> Tuple[DimResult, str]:
    """
    s_ord: logical prerequisite ordering.
    DEFECT when: > 50 % of the eligible course pool carries unmet prerequisites,
    indicating the student's academic trajectory is not ready for the
    specialization-level content being recommended.
    Non-critical: a warning is issued but generation is not blocked (CLARIFY path).
    """
    if not eligible_courses:
        return "OK", "No eligible courses to evaluate for prerequisite ordering."

    unmet_courses = []
    for course in eligible_courses:
        meta  = course_meta.get(course["code"], {})
        unmet = [p for p in meta.get("prereqs", []) if p not in completed_codes]
        if unmet:
            unmet_courses.append(course["code"])

    ratio = len(unmet_courses) / len(eligible_courses)
    if ratio > 0.5:
        return (
            "DEFECT",
            f"{len(unmet_courses)}/{len(eligible_courses)} eligible courses have "
            "unmet prerequisites. You may wish to complete foundational courses "
            "first, or update your completed-courses list if this is inaccurate.",
        )

    return (
        "OK",
        f"Prerequisite coverage adequate — "
        f"{len(eligible_courses) - len(unmet_courses)}/{len(eligible_courses)} "
        "courses have all prerequisites met.",
    )


def _check_robustness(
    wam:         str,
    credits_str: str,
    load_str:    str,
) -> Tuple[DimResult, str]:
    """
    s_rob: input anomaly and internal consistency.
    DEFECT when: WAM is outside the valid academic range [0, 100].
    Non-critical: generation proceeds with a cautionary note (CLARIFY path).
    """
    wam_clean = wam.strip()
    skip_values = {"", "未提供", "Not provided"}
    if wam_clean not in skip_values:
        try:
            wam_val = float(wam_clean)
            if not (0.0 <= wam_val <= 100.0):
                return (
                    "DEFECT",
                    f"WAM value {wam_val} is outside the valid range [0, 100]. "
                    "Please correct or leave blank.",
                )
        except ValueError:
            return (
                "DEFECT",
                f"WAM '{wam_clean}' is not a valid numeric value. "
                "Please enter a number between 0 and 100, or leave blank.",
            )

    return "OK", "Input values are within expected ranges."


# ── Authorization function φ ──────────────────────────────────────────────────

def run_gatefix(
    specs:            List[str],
    goal_weights:     Dict[str, int],
    eligible_courses: List[dict],
    completed_codes:  Set[str],
    credits_str:      str,
    load_str:         str,
    wam:              str,
    course_meta:      dict,
) -> GateFixResult:
    """
    Main GateFix entry point.
    Computes CQ vector S, then applies authorization rule φ: S → {PASS, CLARIFY, REFUSE}.

    φ logic (per paper Definition 3):
        PASS    ↔ ∀i: sᵢ = OK
        REFUSE  ↔ s_rel = DEFECT OR s_cov = DEFECT     (critical dimensions)
        CLARIFY ↔ (s_ord = DEFECT OR s_rob = DEFECT)
                  AND s_rel = OK AND s_cov = OK          (non-critical only)
    """
    rel_r, rel_msg = _check_relevance(specs, goal_weights)
    cov_r, cov_msg = _check_coverage(goal_weights, eligible_courses, credits_str, load_str)
    ord_r, ord_msg = _check_ordering(completed_codes, eligible_courses, course_meta)
    rob_r, rob_msg = _check_robustness(wam, credits_str, load_str)

    cq = CQVector(
        relevance=rel_r,  relevance_reason=rel_msg,
        coverage=cov_r,   coverage_reason=cov_msg,
        ordering=ord_r,   ordering_reason=ord_msg,
        robustness=rob_r, robustness_reason=rob_msg,
    )

    dims = [
        ("Relevance",  rel_r),
        ("Coverage",   cov_r),
        ("Ordering",   ord_r),
        ("Robustness", rob_r),
    ]
    failed = [d for d, r in dims if r == "DEFECT"]
    passed = [d for d, r in dims if r == "OK"]

    # Deterministic authorization rule
    if rel_r == "DEFECT" or cov_r == "DEFECT":
        decision: AuthDecision = "REFUSE"
    elif ord_r == "DEFECT" or rob_r == "DEFECT":
        decision = "CLARIFY"
    else:
        decision = "PASS"

    return GateFixResult(decision=decision, cq_vector=cq, failed_dims=failed, passed_dims=passed)
