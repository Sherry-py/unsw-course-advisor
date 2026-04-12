"""
GateFix Admin Dashboard — Usage Statistics
Run with: streamlit run admin_stats.py
"""
import streamlit as st
import json
from pathlib import Path
from collections import Counter
import datetime

st.set_page_config(page_title="GateFix Admin Stats", page_icon="📊", layout="centered")
st.title("📊 GateFix 使用数据统计 / Usage Stats")

LOG_FILE = Path.home() / ".hermes" / "unsw_advisor_logs" / "usage_log.json"

if not LOG_FILE.exists():
    st.warning("暂无数据 / No data yet. 等用户使用后自动生成。")
    st.stop()

try:
    logs = json.loads(LOG_FILE.read_text())
except Exception as e:
    st.error(f"读取日志失败 / Failed to read log: {e}")
    st.stop()

if not logs:
    st.warning("日志为空 / Log is empty.")
    st.stop()

total = len(logs)
st.metric("总使用次数 / Total Sessions", total)

# GateFix decisions
decisions = Counter(entry.get("gatefix_decision", "UNKNOWN") for entry in logs)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("✅ PASS", decisions.get("PASS", 0),
              help="信息完整，AI正常执行")
with col2:
    st.metric("⚠️ CLARIFY", decisions.get("CLARIFY", 0),
              help="非关键问题，AI继续但给出警告")
with col3:
    st.metric("⛔ REFUSE", decisions.get("REFUSE", 0),
              help="关键信息缺失，AI拒绝执行")

st.divider()

# Dimension PASS rates
st.subheader("4D-CQ 各维度通过率 / Dimension Pass Rates")
dims = ["relevance", "coverage", "ordering", "robustness"]
dim_labels = {
    "relevance": "🎯 Relevance（目标）",
    "coverage": "📋 Coverage（完整度）",
    "ordering": "🔗 Ordering（先修顺序）",
    "robustness": "🛡 Robustness（WAM格式）",
}
for dim in dims:
    ok_count = sum(
        1 for e in logs
        if e.get("gatefix_results", {}).get(dim) == "OK"
    )
    rate = ok_count / total * 100 if total > 0 else 0
    st.progress(rate / 100, text=f"{dim_labels[dim]}: {rate:.1f}% PASS ({ok_count}/{total})")

st.divider()

# Top specializations
st.subheader("🏫 常用专业方向 / Top Specializations")
spec_counter = Counter()
for entry in logs:
    for s in entry.get("specializations", []):
        spec_counter[s] += 1
if spec_counter:
    for spec, count in spec_counter.most_common(5):
        st.write(f"- **{spec}**: {count} 次")
else:
    st.write("暂无数据")

st.divider()

# Recent sessions
st.subheader("🕐 最近使用记录 / Recent Sessions")
recent = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
for entry in recent:
    ts = entry.get("timestamp", "")[:19].replace("T", " ")
    decision = entry.get("gatefix_decision", "?")
    specs_str = ", ".join(entry.get("specializations", []))
    goals = entry.get("goals_count", 0)
    icon = {"PASS": "✅", "CLARIFY": "⚠️", "REFUSE": "⛔"}.get(decision, "❓")
    st.caption(f"{icon} `{ts}` | {specs_str} | {goals} goals | {decision}")

st.divider()
st.caption("数据来源：~/.hermes/unsw_advisor_logs/usage_log.json · GateFix Research Data · Not for distribution")
