"""
GateFix Cross-Domain Validation Dashboard
Education Domain (UNSW MCom Course Advisor)
Access: /admin — password protected
"""

import streamlit as st
import json, os, sys, csv, io
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

FEEDBACK_LOG = os.path.join(os.path.dirname(__file__), "..", "feedback_log.jsonl")

st.set_page_config(
    page_title="GateFix · Validation Dashboard",
    page_icon="📋",
    layout="wide",
)

# ── Academic paper CSS ────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,600;1,400&family=Source+Code+Pro:wght@400;500&display=swap');

.stApp {
  background: #fafaf8 !important;
  font-family: 'Source Serif 4', Georgia, serif !important;
}
.stApp h1 { font-size: 22px !important; font-weight: 600 !important; color: #1a1a1a !important; letter-spacing: -.3px; }
.stApp h2 { font-size: 15px !important; font-weight: 600 !important; color: #1a1a1a !important;
            border-bottom: 1.5px solid #1a1a1a; padding-bottom: 4px; margin-top: 28px !important; }
.stApp h3 { font-size: 13px !important; font-weight: 600 !important; color: #333 !important; margin-top: 18px !important; }
.stApp p, .stApp li { font-size: 13px !important; color: #222 !important; line-height: 1.7 !important; }
.stApp .stCaption p { font-size: 11px !important; color: #666 !important; font-style: italic; font-family: 'Source Serif 4', serif !important; }

/* Metric cards — paper style */
[data-testid="stMetric"] {
  background: #fff !important;
  border: 1px solid #ddd !important;
  border-radius: 2px !important;
  padding: 10px 14px !important;
  box-shadow: none !important;
}
[data-testid="stMetricLabel"] { font-size: 10px !important; color: #666 !important; text-transform: uppercase; letter-spacing: .6px; font-family: 'Source Code Pro', monospace !important; }
[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 600 !important; color: #1a1a1a !important; font-family: 'Source Serif 4', serif !important; }
[data-testid="stMetricDelta"] { font-size: 11px !important; }

/* Buttons */
.stButton > button { border-radius: 2px !important; font-size: 12px !important; border: 1px solid #999 !important; background: #fff !important; color: #333 !important; }

/* Sidebar */
[data-testid="stSidebar"] { background: #f2f2ef !important; border-right: 1px solid #ddd !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { font-size: 12px !important; color: #444 !important; }

/* Tables */
table { font-size: 12px !important; border-collapse: collapse; width: 100%; }
th { background: #1a1a1a !important; color: #fff !important; padding: 6px 10px !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: .5px; font-weight: 500; }
td { padding: 5px 10px !important; border-bottom: 1px solid #e5e5e5; }
tr:nth-child(even) td { background: #f7f7f5; }

/* Expander */
.streamlit-expanderHeader { font-size: 12px !important; font-family: 'Source Code Pro', monospace !important; background: #f2f2ef !important; border: 1px solid #ddd !important; border-radius: 2px !important; }

/* Note boxes */
.paper-note {
  background: #fffef5; border-left: 3px solid #b8860b;
  padding: 8px 14px; margin: 8px 0;
  font-size: 12px; font-style: italic; color: #555;
  font-family: 'Source Serif 4', serif;
}
.paper-finding {
  background: #f0f7f0; border-left: 3px solid #2d6a2d;
  padding: 8px 14px; margin: 8px 0;
  font-size: 12px; color: #1a3d1a;
  font-family: 'Source Serif 4', serif;
}
.paper-warning {
  background: #fff5f5; border-left: 3px solid #9b1c1c;
  padding: 8px 14px; margin: 8px 0;
  font-size: 12px; color: #7f1d1d;
  font-family: 'Source Serif 4', serif;
}
hr { border: none; border-top: 1px solid #ddd !important; margin: 20px 0 !important; }
</style>
""", unsafe_allow_html=True)

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "gatefix_log.jsonl")
PASSWORD = "gatefix2026"

# ── Auth ──────────────────────────────────────────────────────────
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

if not st.session_state.admin_auth:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_c = st.columns([1,2,1])[1]
    with col_c:
        st.markdown("### GateFix Validation Dashboard")
        st.caption("Restricted access — research personnel only")
        pwd = st.text_input("Password", type="password")
        if st.button("Sign in", use_container_width=True):
            if pwd == PASSWORD:
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()

# ── Load data (Supabase → local fallback) ─────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    import supabase_logger
    records = supabase_logger.read_records("gatefix_log")
    _source = f"Supabase ({len(records)} records)"
except Exception:
    records = []
    _source = None

if not records and os.path.exists(LOG_PATH):
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    _source = f"local file ({len(records)} records)"

# ── Page header ───────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:2px solid #1a1a1a;padding-bottom:12px;margin-bottom:4px">
<div style="font-size:11px;color:#666;font-family:'Source Code Pro',monospace;letter-spacing:.5px">
WORKING PAPER · CROSS-DOMAIN VALIDATION
</div>
<div style="font-size:21px;font-weight:600;color:#1a1a1a;margin:6px 0 2px 0;font-family:'Source Serif 4',serif">
GateFix 4D-CQ Framework: Cross-Domain Generalization to Education
</div>
<div style="font-size:13px;color:#444;font-family:'Source Serif 4',serif;font-style:italic">
Live validation data — UNSW MCom Course Advisor (Education Domain)
</div>
</div>
""", unsafe_allow_html=True)

col_meta = st.columns([3,1])
with col_meta[1]:
    st.markdown(
        f"<div style='text-align:right;font-size:11px;color:#888;font-family:\"Source Code Pro\",monospace'>"
        f"N = {len(records)} submissions<br>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>",
        unsafe_allow_html=True,
    )

# ── Paper baseline reference ──────────────────────────────────────
with st.expander("Paper Baseline Reference (FinQA Domain)", expanded=False):
    st.markdown("""
#### Dataset
| Field | Value |
|---|---|
| Domain | Financial QA (FinQA — S&P 500 annual reports) |
| N | 500 samples (100 per defect type × 4 + 85 clean) |
| Defect rate per dimension | 20.6% each (balanced by construction) |
| True label split | REFUSE 41.2% / CLARIFY 41.2% / PASS 17.5% |

#### GateFix Performance — FinQA Domain (GateFix-Full)
| Model | Auth Acc | Acc_PASS | Acc_CLARIFY | Acc_REFUSE | Detect_R | Detect_C | Detect_CONS |
|---|---|---|---|---|---|---|---|
| **Qwen-Plus** | **93.8%** | 91.0% | 88.0% | **99.5%** | 88% | 99% | 100% |
| Qwen-Max | 84.8% | 87.0% | 70.0% | 90.0% | 70% | 100% | 80% |
| GPT-4o | 40.0% | 64.5% | 52.0% | 9.5% | 58% | 91% | 27% |
| Claude | 46.6% | 29.0% | 100% | 37.5% | 100% | 97% | 48% |

*Each education domain submission is anonymously logged for cross-domain generalization research.*
    """)

if not records:
    st.info("No submissions recorded yet.")
    st.stop()

n = max(len(records), 1)
decisions  = [r["decision"] for r in records]
pass_n     = decisions.count("PASS")
clarify_n  = decisions.count("CLARIFY")
refuse_n   = decisions.count("REFUSE")

# ── Section 1: Dataset Summary ────────────────────────────────────
st.markdown("## 1. Dataset Summary")
if _source:
    st.caption(f"Data source: {_source}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Submissions", len(records))
c2.metric("PASS", f"{pass_n}",    f"{100*pass_n//n}%")
c3.metric("CLARIFY", f"{clarify_n}", f"{100*clarify_n//n}%")
c4.metric("REFUSE", f"{refuse_n}",  f"{100*refuse_n//n}%")
c5.metric("AI Generated", sum(1 for r in records if r.get("ai_generated")))

# Decision distribution pie
fig_pie = go.Figure(go.Pie(
    labels=["PASS", "CLARIFY", "REFUSE"],
    values=[pass_n, clarify_n, refuse_n],
    marker_colors=["#2d6a2d","#b8860b","#9b1c1c"],
    hole=0.45,
    textinfo="percent+label",
    textfont_size=11,
))
fig_pie.update_layout(
    height=220, margin=dict(t=10,b=10,l=10,r=10),
    showlegend=False,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
col_pie, col_tbl = st.columns([1,2])
with col_pie:
    st.markdown("<div style='font-size:11px;color:#666;text-align:center;margin-bottom:4px'>Figure 1. Decision distribution</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_pie, use_container_width=True)
with col_tbl:
    st.markdown("<div style='font-size:11px;color:#666;margin-bottom:6px'>Table 1. Submission profile</div>", unsafe_allow_html=True)
    profile_df = pd.DataFrame([{
        "Field": "Avg. goals per submission",
        "Value": f"{sum(r.get('n_goals') or 0 for r in records)/n:.1f}"
    },{
        "Field": "Avg. specialisations selected",
        "Value": f"{sum(r.get('n_specs') or 0 for r in records)/n:.1f}"
    },{
        "Field": "Submissions with WAM provided",
        "Value": f"{100*sum(1 for r in records if r.get('has_wam'))/n:.0f}%"
    },{
        "Field": "Submissions with notes provided",
        "Value": f"{100*sum(1 for r in records if r.get('has_notes'))/n:.0f}%"
    },{
        "Field": "Submissions with completed courses",
        "Value": f"{100*sum(1 for r in records if (r.get('n_completed') or 0)>0)/n:.0f}%"
    },{
        "Field": "Language (Chinese / English)",
        "Value": f"{100*sum(1 for r in records if r.get('lang')=='中文')//n}% / {100*sum(1 for r in records if r.get('lang')!='中文')//n}%"
    }])
    st.dataframe(profile_df, hide_index=True, use_container_width=True)

# ── Section 2: V1 — Safety Guarantee ─────────────────────────────
st.markdown("## 2. Hypothesis V1 — Safety Guarantee Cross-Domain Transfer")
st.markdown("""
**Thesis claim (Section V.C):** The safety guarantee of GateFix is domain-invariant.
When Relevance (R) or Coverage (C) dimensions are defective, the system *always* issues REFUSE,
achieving a gate accuracy of 1.0 regardless of domain.
""")

rc_defect  = [r for r in records if r.get("dim_relevance")=="DEFECT" or r.get("dim_coverage")=="DEFECT"]
rc_refused = [r for r in rc_defect if r.get("decision")=="REFUSE"]
safety_acc = len(rc_refused) / max(len(rc_defect), 1)

v1c1, v1c2, v1c3, v1c4 = st.columns(4)
v1c1.metric("R/C Defect Triggers", len(rc_defect))
v1c2.metric("Correctly Refused", len(rc_refused))
v1c3.metric("Safety Guarantee Acc.", f"{safety_acc:.3f}")
v1c4.metric("Paper Baseline", "1.000", delta="target")

if safety_acc == 1.0 and len(rc_defect) > 0:
    st.markdown(
        '<div class="paper-finding">&#10003; <strong>V1 Confirmed in education domain.</strong> '
        f'All {len(rc_defect)} submissions with R/C defects were correctly refused '
        f'(accuracy = 1.000), consistent with the domain-invariant safety guarantee reported in the thesis.</div>',
        unsafe_allow_html=True,
    )
elif len(rc_defect) == 0:
    st.markdown(
        '<div class="paper-note">V1 cannot yet be evaluated: no submissions with R/C defects recorded. '
        'Increase sample size to obtain this measurement.</div>',
        unsafe_allow_html=True,
    )
else:
    gap = len(rc_defect) - len(rc_refused)
    st.markdown(
        f'<div class="paper-warning">&#9888; V1 violated: {gap} submission(s) with R/C defects were not refused. '
        f'Safety accuracy = {safety_acc:.3f} (expected 1.000). Investigate governance logic.</div>',
        unsafe_allow_html=True,
    )

# ── Section 3: V2 — Domain-Specific Calibration ───────────────────
st.markdown("## 3. Hypothesis V2 — Domain-Specific Calibration of O/R Dimensions")
st.markdown("""
**Thesis claim (Section V.C):** Ordering (O) and Robustness (R) dimensions exhibit
domain-specific defect rates and require per-domain calibration,
unlike the domain-invariant R/C safety guarantee.
""")

edu_defect = {
    "Relevance (R)":   round(100 * sum(1 for r in records if r.get("dim_relevance") =="DEFECT") / n, 1),
    "Coverage (C)":    round(100 * sum(1 for r in records if r.get("dim_coverage")  =="DEFECT") / n, 1),
    "Ordering (O)":    round(100 * sum(1 for r in records if r.get("dim_ordering")  =="DEFECT") / n, 1),
    "Robustness (Ro)": round(100 * sum(1 for r in records if r.get("dim_robustness")=="DEFECT") / n, 1),
}
# FinQA domain baseline — balanced dataset (N=485, 100 defects per dim)
# Defect rate = 20.6% by construction; detection accuracy from Qwen-Plus GateFix-Full
PAPER_BASELINE = {
    "Relevance (R)":   20.6,   # dataset construction rate; Detect_R = 88.0%
    "Coverage (C)":    20.6,   # dataset construction rate; Detect_C = 99.0%
    "Ordering (O)":    20.6,   # dataset construction rate; Detect_CONS = 100.0%
    "Robustness (Ro)": 20.6,   # dataset construction rate; Dim_Recall_B = 93.0%
}

fig_v2 = go.Figure()
bar_colors = {
    "Relevance (R)":   "#9b1c1c",
    "Coverage (C)":    "#9b1c1c",
    "Ordering (O)":    "#1e3a5f",
    "Robustness (Ro)": "#1e3a5f",
}
fig_v2.add_trace(go.Bar(
    name="Education domain (this study)",
    x=list(edu_defect.keys()),
    y=list(edu_defect.values()),
    marker_color=[bar_colors[k] for k in edu_defect],
    text=[f"{v}%" for v in edu_defect.values()],
    textposition="outside",
    width=0.35,
    offset=-0.2,
))
if any(v is not None for v in PAPER_BASELINE.values()):
    fig_v2.add_trace(go.Bar(
        name="FinQA domain (paper baseline)",
        x=list(PAPER_BASELINE.keys()),
        y=[v or 0 for v in PAPER_BASELINE.values()],
        marker_color="rgba(100,100,100,0.4)",
        marker_line_color="rgba(100,100,100,0.8)",
        marker_line_width=1.5,
        text=[f"{v}%" if v is not None else "N/A" for v in PAPER_BASELINE.values()],
        textposition="outside",
        width=0.35,
        offset=0.2,
    ))
fig_v2.add_annotation(
    x=0.5, xref="paper", y=1.08, yref="paper",
    text="■ Critical (R/C)   ■ Non-critical (O/Ro)",
    showarrow=False, font=dict(size=10, color="#555"),
    align="center",
)
fig_v2.update_layout(
    barmode="overlay",
    yaxis=dict(range=[0, 120], title="DEFECT Rate (%)", tickfont_size=11, gridcolor="#eee"),
    xaxis=dict(tickfont_size=11),
    height=320, margin=dict(t=40, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.markdown("<div style='font-size:11px;color:#666;margin-bottom:4px'>Figure 2. Dimension-level DEFECT rates — education domain vs. paper baseline (FinQA)</div>", unsafe_allow_html=True)
st.plotly_chart(fig_v2, use_container_width=True)
st.caption("Red bars = critical dimensions (R, C). Blue bars = non-critical dimensions (O, Ro). "
           "Paper baseline values pending — replace None values in PAPER_BASELINE dict once available.")

# Auto-generated observations
obs = []
if edu_defect["Robustness (Ro)"] > 80:
    obs.append(f"**Robustness defect rate is {edu_defect['Robustness (Ro)']}%** in the education domain. "
               "Users rarely provide supplementary notes, suggesting the threshold for this dimension "
               "may warrant downward recalibration in educational contexts.")
if edu_defect["Ordering (O)"] < 10:
    obs.append(f"**Ordering defect rate is {edu_defect['Ordering (O)']}%** — markedly low. "
               "Students appear to provide credit/enrolment information consistently, "
               "indicating higher structural self-awareness than financial domain users.")
if edu_defect["Relevance (R)"] > 25:
    obs.append(f"**Relevance defect rate is {edu_defect['Relevance (R)']}%**. "
               "A non-trivial share of users submit without selecting a specialisation, "
               "pointing to a potential UX friction point.")
if obs:
    st.markdown("**Observations:**")
    for i, o in enumerate(obs, 1):
        st.markdown(f"*{i}.* {o}")
else:
    st.markdown('<div class="paper-note">Insufficient data for automated observation generation. '
                'Increase N to ≥ 30 for reliable dimension-level inference.</div>',
                unsafe_allow_html=True)

# ── Section 4: V3 — Governance Value ─────────────────────────────
st.markdown("## 4. Hypothesis V3 — Governance Intervention Value")
st.markdown("""
**Rationale:** If GateFix governance meaningfully changes the AI output,
the course recommendation overlap between governed and ungoverned calls should be low (< 0.7).
A high overlap suggests the governance adds little practical value for this domain.
""")

overlap_records = [r for r in records if r.get("overlap_rate") is not None]
if overlap_records:
    avg_ov = sum(r["overlap_rate"] for r in overlap_records) / len(overlap_records)
    pass_ov    = [r["overlap_rate"] for r in overlap_records if r.get("decision")=="PASS"]
    clarify_ov = [r["overlap_rate"] for r in overlap_records if r.get("decision")=="CLARIFY"]
    ov1, ov2, ov3 = st.columns(3)
    ov1.metric("Mean Overlap Rate (governed vs. ungoverned)", f"{avg_ov:.2f}")
    ov2.metric("PASS — mean overlap", f"{sum(pass_ov)/max(len(pass_ov),1):.2f}" if pass_ov else "—")
    ov3.metric("CLARIFY — mean overlap", f"{sum(clarify_ov)/max(len(clarify_ov),1):.2f}" if clarify_ov else "—")
    st.caption("Overlap rate = |governed ∩ ungoverned| / |governed|. Lower values indicate stronger governance intervention.")
    if avg_ov < 0.6:
        st.markdown('<div class="paper-finding">V3 supported: mean overlap is below 0.6, indicating governance '
                    'substantially alters recommendation output in this domain.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="paper-note">V3 inconclusive: overlap rate suggests governance has limited impact '
                    'on final output. May reflect domain simplicity or prompt design.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="paper-note"><strong>V3 pending data.</strong> '
                'Overlap rate will be computed automatically once PASS-state submissions are logged with '
                'the <code>overlap_rate</code> field. See implementation note below.</div>',
                unsafe_allow_html=True)
    with st.expander("Implementation note — how to log overlap_rate"):
        st.code("""# In app.py, before calling gf_engine.log_submission() on PASS path:
governed_codes = {s['code'] for s in result.get('selections', [])}
ungated_codes  = {s['code'] for s in result_ungated.get('selections', [])}
overlap = len(governed_codes & ungated_codes) / max(len(governed_codes), 1)
profile_meta['overlap_rate'] = round(overlap, 3)""", language="python")

# ── Section 5: Memory Layer Analysis ─────────────────────────────
st.markdown("## 5. Memory Injection Layer — Session-Level Analysis")
st.markdown("""
**Rationale:** The stateless 4D-CQ framework evaluates each submission in isolation.
A Memory Injection Layer (MIL) would carry forward previously-validated dimensions across
re-submissions within the same session, hypothetically converting CLARIFY → PASS without
requiring the user to re-enter already-confirmed information.
This section quantifies the theoretical lift of adding such a layer.
""")

# Collect session records
session_records = [r for r in records if r.get("session_id")]
multi_sub_sessions = {}
for r in session_records:
    sid = r["session_id"]
    if sid not in multi_sub_sessions:
        multi_sub_sessions[sid] = []
    multi_sub_sessions[sid].append(r)

# Sessions with >1 submission = "re-submitters"
multi_sessions = {k: v for k, v in multi_sub_sessions.items() if len(v) > 1}

# Counterfactual lift: records where actual=CLARIFY but counterfactual=PASS
cf_records = [r for r in records if r.get("counterfactual_decision")]
clarify_to_pass = [r for r in cf_records
                   if r.get("decision") == "CLARIFY"
                   and r.get("counterfactual_decision") == "PASS"]
refuse_to_clarify = [r for r in cf_records
                     if r.get("decision") == "REFUSE"
                     and r.get("counterfactual_decision") in ("CLARIFY", "PASS")]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Sessions with re-submissions", len(multi_sessions))
m2.metric("Multi-sub session submissions", sum(len(v) for v in multi_sessions.values()))
m3.metric("CLARIFY → PASS lift (MIL)", len(clarify_to_pass),
          help="Submissions where injecting prior-session OK dims would upgrade CLARIFY to PASS")
m4.metric("REFUSE → CLARIFY/PASS lift", len(refuse_to_clarify),
          help="Submissions where prior-session data would soften a REFUSE decision")

if cf_records:
    total_clarify = clarify_n
    lift_rate = len(clarify_to_pass) / max(total_clarify, 1)
    st.markdown(
        f'<div class="paper-finding">'
        f'MIL counterfactual: {len(clarify_to_pass)} of {total_clarify} CLARIFY decisions '
        f'({lift_rate*100:.1f}%) would upgrade to PASS if prior-session OK dims were injected. '
        f'This represents the theoretical governance-quality lift from adding a Memory Layer.'
        f'</div>', unsafe_allow_html=True
    )

    # Per-dimension session persistence table
    st.markdown("### Table V3-M: Dimension-Level Session Persistence")
    dim_names = ["relevance", "coverage", "ordering", "robustness"]
    dim_labels = ["Relevance (R)", "Coverage (C)", "Ordering (O)", "Robustness (Ro)"]
    # For each dim: how often does the dim flip from DEFECT in sub1 → OK in sub2+ within same session?
    dim_flip = {d: 0 for d in dim_names}
    dim_stable_ok = {d: 0 for d in dim_names}
    for sid, subs in multi_sessions.items():
        subs_sorted = sorted(subs, key=lambda x: x.get("submit_count", 0))
        first = subs_sorted[0]
        for later in subs_sorted[1:]:
            for d in dim_names:
                fk = f"dim_{d}"
                if first.get(fk) == "DEFECT" and later.get(fk) == "OK":
                    dim_flip[d] += 1
                if first.get(fk) == "OK" and later.get(fk) == "OK":
                    dim_stable_ok[d] += 1

    table_rows = ""
    for d, label in zip(dim_names, dim_labels):
        table_rows += f"<tr><td>{label}</td><td>{dim_flip[d]}</td><td>{dim_stable_ok[d]}</td></tr>"

    st.markdown(f"""
<table>
  <thead><tr><th>Dimension</th><th>DEFECT→OK flips (re-submission)</th><th>Stable OK across subs</th></tr></thead>
  <tbody>{table_rows}</tbody>
</table>
<div style="font-size:11px;color:#666;margin-top:4px">
Table V3-M. Within-session dimension state transitions for multi-submission users.
Flips indicate which dimensions users corrected on re-submission.
</div>
""", unsafe_allow_html=True)

    # Re-submission pattern chart
    if multi_sessions:
        sub_counts = [len(v) for v in multi_sub_sessions.values()]
        from collections import Counter
        cnt = Counter(sub_counts)
        df_sub = pd.DataFrame(
            [{"Submissions per session": k, "Sessions": v} for k, v in sorted(cnt.items())]
        )
        fig_sub = px.bar(df_sub, x="Submissions per session", y="Sessions",
                         height=180, labels={"Sessions": "# Sessions"})
        fig_sub.update_layout(
            margin=dict(t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#eee", dtick=1),
            yaxis=dict(gridcolor="#eee"),
        )
        st.markdown("<div style='font-size:11px;color:#666;margin-bottom:4px'>Figure M1. Session re-submission distribution</div>", unsafe_allow_html=True)
        st.plotly_chart(fig_sub, use_container_width=True)

else:
    st.markdown('<div class="paper-note"><strong>Memory Layer data pending.</strong> '
                'Session tracking fields (<code>session_id</code>, <code>submit_count</code>, '
                '<code>counterfactual_decision</code>) are now being logged. '
                'This section will populate after the first multi-submission sessions are recorded.</div>',
                unsafe_allow_html=True)

# ── Section 6: Timeline ────────────────────────────────────────────
st.markdown("## 6. Submission Timeline")

ts_data = []
for r in records:
    try:
        ts_data.append({"date": r["timestamp"][:10], "decision": r["decision"]})
    except Exception:
        pass

if ts_data:
    df_ts = pd.DataFrame(ts_data)
    counts = df_ts.groupby(["date","decision"]).size().reset_index(name="n")
    fig_ts = px.bar(counts, x="date", y="n", color="decision",
                    color_discrete_map={"PASS":"#2d6a2d","CLARIFY":"#b8860b","REFUSE":"#9b1c1c"},
                    height=220, labels={"n":"Submissions","date":"Date"})
    fig_ts.update_layout(
        margin=dict(t=10,b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#eee"), yaxis=dict(gridcolor="#eee"),
    )
    st.markdown("<div style='font-size:11px;color:#666;margin-bottom:4px'>Figure 3. Daily submission volume by gate decision</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_ts, use_container_width=True)

# ── Section 7: Export ──────────────────────────────────────────────
st.markdown("## 7. Data Export")
st.caption("All records are anonymised. Export for statistical analysis or thesis appendix.")

col_csv, col_json, col_summary = st.columns(3)
with col_csv:
    if records:
        # Collect all keys across all records (handles schema evolution)
        all_fields = list(dict.fromkeys(k for r in records for k in r.keys()))
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow({f: r.get(f, "") for f in all_fields})
        st.download_button(
            "Download CSV",
            data=buf.getvalue().encode("utf-8"),
            file_name=f"gatefix_edu_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv", use_container_width=True,
        )
with col_json:
    st.download_button(
        "Download JSON (full log)",
        data=json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"gatefix_edu_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json", use_container_width=True,
    )
with col_summary:
    summary = {
        "generated_at": datetime.now().isoformat(),
        "n_total": len(records),
        "decision_distribution": {"PASS": pass_n, "CLARIFY": clarify_n, "REFUSE": refuse_n},
        "safety_guarantee_acc": round(safety_acc, 4),
        "dim_defect_rates_pct": edu_defect,
        "paper_baseline_pct": PAPER_BASELINE,
    }
    st.download_button(
        "Download Summary JSON",
        data=json.dumps(summary, indent=2).encode("utf-8"),
        file_name=f"gatefix_summary_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json", use_container_width=True,
    )

with st.expander("Raw data table"):
    st.dataframe(pd.DataFrame(records), use_container_width=True)

# ── Section 8: User Feedback ───────────────────────────────────────
st.markdown("## 8. User Feedback")


try:
    fb_records = supabase_logger.read_records("feedback_log")
except Exception:
    fb_records = []

if not fb_records and os.path.exists(FEEDBACK_LOG):
    with open(FEEDBACK_LOG, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line:
                try:
                    fb_records.append(json.loads(_line))
                except Exception:
                    pass

if not fb_records:
    st.markdown('<div class="paper-note">No feedback collected yet. '
                'The in-app micro-feedback widget will populate this section.</div>',
                unsafe_allow_html=True)
else:
    fb_bad   = sum(1 for r in fb_records if r.get("rating") == "bad")
    fb_ok    = sum(1 for r in fb_records if r.get("rating") == "ok")
    fb_great = sum(1 for r in fb_records if r.get("rating") == "great")
    fb_total = len(fb_records)
    # NPS-style score: great=+1, bad=-1, ok=0, scaled to 0-100
    nps_raw   = (fb_great - fb_bad) / max(fb_total, 1)
    nps_score = round((nps_raw + 1) / 2 * 100)

    fb1, fb2, fb3, fb4 = st.columns(4)
    fb1.metric("Total feedback", fb_total)
    fb2.metric("😕 Off-target", f"{fb_bad} ({100*fb_bad//max(fb_total,1)}%)")
    fb3.metric("😊 Pretty good", f"{fb_ok} ({100*fb_ok//max(fb_total,1)}%)")
    fb4.metric("🤩 Exactly right", f"{fb_great} ({100*fb_great//max(fb_total,1)}%)")

    st.markdown(
        f'<div class="paper-finding">Satisfaction score: <strong>{nps_score}/100</strong> '
        f'({fb_great} positive, {fb_ok} neutral, {fb_bad} negative out of {fb_total} responses).</div>',
        unsafe_allow_html=True,
    )

    # Rating distribution by gate decision
    st.markdown("### Table F1: Feedback by Gate Decision")
    for dec in ["PASS", "CLARIFY", "REFUSE"]:
        dec_fb = [r for r in fb_records if r.get("gate_decision") == dec]
        if not dec_fb:
            continue
        d_bad   = sum(1 for r in dec_fb if r.get("rating") == "bad")
        d_ok    = sum(1 for r in dec_fb if r.get("rating") == "ok")
        d_great = sum(1 for r in dec_fb if r.get("rating") == "great")
        st.markdown(
            f"<div style='font-size:12px;margin:4px 0'>"
            f"<strong>{dec}</strong> ({len(dec_fb)} responses) — "
            f"😕 {d_bad} &nbsp; 😊 {d_ok} &nbsp; 🤩 {d_great}</div>",
            unsafe_allow_html=True,
        )

    # Recent comments
    comments = [r for r in fb_records if r.get("comment")]
    if comments:
        st.markdown("### Recent Comments")
        for r in sorted(comments, key=lambda x: x.get("timestamp",""), reverse=True)[:10]:
            rating_icon = {"bad":"😕","ok":"😊","great":"🤩"}.get(r.get("rating",""),"·")
            ts = r.get("timestamp","")[:10]
            dec = r.get("gate_decision","?")
            st.markdown(
                f"<div style='border-left:3px solid #ccc;padding:4px 10px;"
                f"margin-bottom:6px;font-size:12px;color:#333'>"
                f"{rating_icon} <em>{r['comment']}</em>"
                f"<span style='font-size:10px;color:#999;margin-left:8px'>{ts} · {dec}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with st.expander("Raw feedback data"):
        st.dataframe(pd.DataFrame(fb_records), use_container_width=True)
