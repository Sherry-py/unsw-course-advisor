"""
Admin dashboard for GateFix governance research.
Access at /?admin=1 or via the hidden sidebar link.

Shows:
  - Submission statistics
  - 4D-CQ dimension pass/fail rates  ← core thesis data
  - Authorization decision distribution
  - CSV/JSON export for paper analysis
"""

import json
import csv
import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from logger import get_logs

ADMIN_PASSWORD = "gatefix2026"   # change before public deployment


def render_admin_dashboard() -> None:
    st.set_page_config(page_title="GateFix Admin", page_icon="🔬", layout="wide")

    # ── Auth gate ─────────────────────────────────────────────────────────────
    if "admin_authed" not in st.session_state:
        st.session_state.admin_authed = False

    if not st.session_state.admin_authed:
        st.title("🔬 GateFix Research Dashboard")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        return

    # ── Data load ─────────────────────────────────────────────────────────────
    logs = get_logs()
    if not logs:
        st.info("No submissions recorded yet.")
        return

    df = pd.DataFrame(logs)

    # Flatten gatefix sub-dict
    gf_df = pd.json_normalize(df["gatefix"])
    df = pd.concat([df.drop(columns=["gatefix"]), gf_df], axis=1)

    st.title("🔬 GateFix Governance Research Dashboard")
    st.caption(
        f"Corpus: {len(df)} submission events  |  "
        f"Last updated: {df['timestamp'].max()[:19]} UTC"
    )

    # ── Top KPIs ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Submissions", len(df))
    col2.metric("PASS rate",
                f"{(df['decision'] == 'PASS').mean():.1%}")
    col3.metric("CLARIFY rate",
                f"{(df['decision'] == 'CLARIFY').mean():.1%}")
    col4.metric("REFUSE rate",
                f"{(df['decision'] == 'REFUSE').mean():.1%}")
    ai_gen_rate = df["ai_generated"].mean() if "ai_generated" in df else 0.0
    col5.metric("AI generation triggered",
                f"{ai_gen_rate:.1%}")

    st.divider()

    # ── 4D-CQ pass rates ─── CORE THESIS METRIC ───────────────────────────────
    st.subheader("4D-CQ Dimension Pass Rates")
    st.caption("Core empirical data for thesis — Coverage and Relevance are critical dimensions.")

    dims = ["relevance", "coverage", "ordering", "robustness"]
    labels = ["Relevance (critical)", "Coverage (critical)",
              "Ordering (non-critical)", "Robustness (non-critical)"]
    pass_rates = [(df[d] == "OK").mean() * 100 for d in dims]
    fail_rates = [100 - r for r in pass_rates]

    fig_dims = go.Figure()
    fig_dims.add_bar(name="PASS (OK)", x=labels, y=pass_rates,
                     marker_color=["#2ecc71", "#2ecc71", "#3498db", "#3498db"])
    fig_dims.add_bar(name="FAIL (DEFECT)", x=labels, y=fail_rates,
                     marker_color=["#e74c3c", "#e74c3c", "#e67e22", "#e67e22"])
    fig_dims.update_layout(barmode="stack", height=350,
                           yaxis_title="% submissions",
                           margin=dict(t=20, b=20))
    st.plotly_chart(fig_dims, use_container_width=True)

    for d, label in zip(dims, labels):
        fail_n = (df[d] == "DEFECT").sum()
        st.caption(f"  {label}: {fail_n} DEFECT ({fail_n/len(df):.1%})")

    st.divider()

    # ── Authorization decision timeline ───────────────────────────────────────
    st.subheader("Authorization Decision Distribution Over Time")
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    timeline = (
        df.groupby(["date", "decision"])
          .size()
          .reset_index(name="count")
    )
    if not timeline.empty:
        fig_time = px.bar(
            timeline, x="date", y="count", color="decision",
            color_discrete_map={"PASS": "#2ecc71", "CLARIFY": "#f39c12", "REFUSE": "#e74c3c"},
            height=280,
        )
        fig_time.update_layout(margin=dict(t=20, b=20))
        st.plotly_chart(fig_time, use_container_width=True)

    st.divider()

    # ── Submission profile stats ───────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Goals Completeness")
        st.caption("% of submissions with goals specified (Coverage dimension input)")
        goals_pct = (df["goals_count"] > 0).mean()
        st.metric("Submissions with goals", f"{goals_pct:.1%}")

        spec_counts = df["specs"].explode().value_counts().head(8).reset_index()
        spec_counts.columns = ["Specialization", "Count"]
        fig_spec = px.bar(spec_counts, x="Count", y="Specialization",
                          orientation="h", height=280)
        fig_spec.update_layout(margin=dict(t=20, b=20))
        st.plotly_chart(fig_spec, use_container_width=True)

    with col_b:
        st.subheader("Language Distribution")
        lang_counts = df["lang"].value_counts().reset_index()
        lang_counts.columns = ["Language", "Count"]
        fig_lang = px.pie(lang_counts, names="Language", values="Count", height=200)
        fig_lang.update_layout(margin=dict(t=20, b=20))
        st.plotly_chart(fig_lang, use_container_width=True)

        st.subheader("Course Load Requested")
        load_counts = df["load"].value_counts().reset_index()
        load_counts.columns = ["Load", "Count"]
        fig_load = px.bar(load_counts, x="Load", y="Count", height=180)
        fig_load.update_layout(margin=dict(t=20, b=20))
        st.plotly_chart(fig_load, use_container_width=True)

    st.divider()

    # ── Thesis-ready summary table ─────────────────────────────────────────────
    st.subheader("Thesis Data Summary Table")
    summary = {
        "Metric": [
            "Total submissions",
            "PASS (φ = PASS)",
            "CLARIFY (φ = CLARIFY)",
            "REFUSE (φ = REFUSE)",
            "AI generation triggered",
            "Relevance PASS rate",
            "Coverage PASS rate",
            "Ordering PASS rate",
            "Robustness PASS rate",
        ],
        "Value": [
            len(df),
            f"{(df['decision']=='PASS').sum()} ({(df['decision']=='PASS').mean():.1%})",
            f"{(df['decision']=='CLARIFY').sum()} ({(df['decision']=='CLARIFY').mean():.1%})",
            f"{(df['decision']=='REFUSE').sum()} ({(df['decision']=='REFUSE').mean():.1%})",
            f"{df['ai_generated'].sum()} ({df['ai_generated'].mean():.1%})",
            f"{(df['relevance']=='OK').mean():.1%}",
            f"{(df['coverage']=='OK').mean():.1%}",
            f"{(df['ordering']=='OK').mean():.1%}",
            f"{(df['robustness']=='OK').mean():.1%}",
        ],
    }
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

    st.divider()

    # ── Export ────────────────────────────────────────────────────────────────
    st.subheader("Export Data")
    col_ex1, col_ex2 = st.columns(2)

    with col_ex1:
        json_str = json.dumps(logs, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ Download JSON (full log)",
            data=json_str,
            file_name="gatefix_submissions.json",
            mime="application/json",
        )

    with col_ex2:
        csv_cols = [
            "id", "timestamp", "lang", "term", "credits", "load",
            "wam_provided", "goals_count", "completed_count",
            "decision", "relevance", "coverage", "ordering", "robustness",
            "ai_generated",
        ]
        available = [c for c in csv_cols if c in df.columns]
        csv_buf = io.StringIO()
        df[available].to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Download CSV (thesis-ready)",
            data=csv_buf.getvalue(),
            file_name="gatefix_submissions.csv",
            mime="text/csv",
        )

    st.caption(
        "Data collected under UNSW ethics guidelines. "
        "No personally identifiable information is stored."
    )


if __name__ == "__main__":
    render_admin_dashboard()
