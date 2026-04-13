"""
Admin Research Dashboard — GateFix 4D-CQ Data
Password protected. For thesis data export only.
"""

import streamlit as st
import json
import os
import csv
import io
from datetime import datetime

st.set_page_config(page_title="GateFix Admin", page_icon="🔬", layout="wide")

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "gatefix_log.jsonl")
PASSWORD  = "gatefix2026"

# ── Password gate ─────────────────────────────────────────────────────────
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

if not st.session_state.admin_auth:
    pwd = st.text_input("管理员密码 / Admin Password", type="password")
    if st.button("登录 / Login"):
        if pwd == PASSWORD:
            st.session_state.admin_auth = True
            st.rerun()
        else:
            st.error("密码错误 / Wrong password")
    st.stop()

# ── Load log ──────────────────────────────────────────────────────────────
records = []
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

st.title("🔬 GateFix 4D-CQ Research Dashboard")
st.caption(f"Total submissions: {len(records)}  |  Log: {LOG_PATH}")

if not records:
    st.info("暂无数据 / No submissions yet.")
    st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────
decisions = [r["decision"] for r in records]
pass_n    = decisions.count("PASS")
clarify_n = decisions.count("CLARIFY")
refuse_n  = decisions.count("REFUSE")
ai_n      = sum(1 for r in records if r.get("ai_generated"))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total",   len(records))
c2.metric("PASS",    pass_n,    f"{100*pass_n//max(len(records),1)}%")
c3.metric("CLARIFY", clarify_n, f"{100*clarify_n//max(len(records),1)}%")
c4.metric("REFUSE",  refuse_n,  f"{100*refuse_n//max(len(records),1)}%")

st.divider()

# ── 4D dimension pass rates (thesis core data) ────────────────────────────
st.subheader("4D-CQ Dimension Pass Rates")

import plotly.graph_objects as go

dims   = ["Relevance (Critical)", "Coverage (Critical)", "Ordering (Non-crit)", "Robustness (Non-crit)"]
keys   = ["dim_relevance", "dim_coverage", "dim_ordering", "dim_robustness"]
colors = ["#ef4444", "#ef4444", "#3b82f6", "#3b82f6"]

rates = []
for k in keys:
    ok_n = sum(1 for r in records if r.get(k) == "OK")
    rates.append(100 * ok_n // max(len(records), 1))

fig = go.Figure(go.Bar(
    x=dims,
    y=rates,
    marker_color=colors,
    text=[f"{r}%" for r in rates],
    textposition="outside",
))
fig.update_layout(yaxis_range=[0, 110], yaxis_title="Pass Rate (%)",
                  margin=dict(t=20, b=20), height=300)
st.plotly_chart(fig, use_container_width=True)

# ── Decision timeline ─────────────────────────────────────────────────────
st.subheader("Submission Timeline")
import plotly.express as px

ts_data = []
for r in records:
    try:
        ts_data.append({
            "time":     r["timestamp"][:16],
            "decision": r["decision"],
        })
    except Exception:
        pass

if ts_data:
    import pandas as pd
    df = pd.DataFrame(ts_data)
    counts = df.groupby(["time", "decision"]).size().reset_index(name="count")
    fig2 = px.bar(counts, x="time", y="count", color="decision",
                  color_discrete_map={"PASS": "#22c55e", "CLARIFY": "#3b82f6", "REFUSE": "#ef4444"},
                  height=280)
    fig2.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

# ── Export ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Export")

col_csv, col_json = st.columns(2)

with col_csv:
    if records:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
        st.download_button(
            "📥 Download CSV (thesis-ready)",
            data=buf.getvalue().encode("utf-8"),
            file_name=f"gatefix_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

with col_json:
    st.download_button(
        "📥 Download JSON (full audit log)",
        data=json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"gatefix_log_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
    )

# ── Raw table ──────────────────────────────────────────────────────────────
with st.expander("Raw data table"):
    import pandas as pd
    st.dataframe(pd.DataFrame(records), use_container_width=True)
