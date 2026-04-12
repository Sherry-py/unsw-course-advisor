import streamlit as st
import anthropic
import json
import time
import plotly.express as px
from gatefix import run_gatefix
from logger import log_submission

st.set_page_config(page_title="UNSW MCom Course Advisor", page_icon="🎓", layout="centered")

# ── Language toggle ──────────────────────────────────────────────────────────
lang = st.radio("", ["中文", "English"], horizontal=True, key="lang",
                label_visibility="collapsed")

T = {
    "中文": {
        "title": "🎓 UNSW MCom 选课助手",
        "caption": "Master of Commerce · Course Advisor",
        "spec_label": "专业方向（可选 1-2 个）",
        "spec_placeholder": "选择专业方向...",
        "term_label": "规划学期",
        "wam_label": "当前 WAM（可选）",
        "wam_placeholder": "例如 82",
        "uoc_label": "剩余学分",
        "completed_header": "**已修课程**",
        "completed_caption": "从列表中选择已修过的课程",
        "completed_placeholder": "选择已修课程（可多选）",
        "load_label": "每学期课程数量",
        "load_options": ["2门", "3门", "4门"],
        "notes_label": "其他备注（可选）",
        "notes_placeholder": "例如：避开周五，想做研究项目...",
        "goals_header": "**毕业目标**",
        "goals_caption": "第一步：选择目标；第二步：为每个目标打分",
        "goals_options": ["继续读博士 PhD", "科技行业就业", "金融/投行", "咨询 Consulting",
                          "创业", "留澳工作签证", "提高 WAM", "学习 AI/数据"],
        "custom_goal_label": "自定义目标（可选）",
        "custom_goal_placeholder": "例如：转型做产品经理...",
        "weights_caption": "为每个目标打分（1=不重要，5=最重要）",
        "submit_btn": "生成选课建议 →",
        "err_no_spec": "请至少选择一个专业方向",
        "spinner": "AI 分析中，请稍候...",
        "retry_toast": "服务器繁忙，3秒后重试...",
        "priority_map": {"must": "🔴 必选", "recommended": "🟢 强烈推荐", "optional": "⚪ 可选"},
        "handbook_btn": "📖 Handbook",
        "no_valid_courses": "AI 未能返回有效课程代码，请重试。",
        "goals_str_fmt": lambda gw: "、".join([f"{g}（重要程度{w}/5）" for g, w in gw.items()]),
        "goals_none": "未指定",
        "wam_none": "未提供",
        "notes_none": "无",
        "ai_lang": "Chinese",
        "summary_field": "一句话总体建议（中文）",
        "reason_field": "2-3句中文理由，结合目标权重",
        "warning_field": "提醒或空字符串",
        "prereq_label": "先修要求",
        "workload_label": "课程工作量",
        "final_label": "期末考试",
        "final_yes": "有",
        "final_no": "无",
        "prereq_none": "无",
        "conflict_title": "⚠️ 先修条件提醒",
        "conflict_body": "以下推荐课程有先修要求，请确认是否已完成：",
        "footer": "数据来源：UNSW Handbook（公开信息），非爬虫采集。本工具不代表官方学术建议。",
        # GateFix UI strings (user-facing: friendly assistant tone, no technical terms)
        "gf_pass":    None,   # silent pass — just proceed
        "gf_clarify": "💡 小提示",
        "gf_refuse":  "🤔 还差一步！助手需要更多信息才能给你精准建议",
        "gf_badge":   "✅ *已通过智能质量检测*",
        "gf_relevance_refuse": "🎯 **选择一个毕业目标吧！** 告诉我你想去哪个方向——金融、科技、创业还是读博？有了目标，我才能帮你选最合适的课 😊",
        "gf_coverage_refuse_goals": "📋 **选一个毕业目标就能生成啦！** 哪怕只选一个也行，这样我才能根据你的方向来推荐课程～",
        "gf_coverage_refuse_uoc": "📊 **学分和课程数对不上哦～** 你的剩余学分不够选这么多门课，要么减少课程数量，要么更新一下剩余学分？",
        "gf_coverage_refuse_pool": "📚 **可选课程太少了！** 当前专业方向下符合条件的课不够你选的，考虑加一个第二专业方向？",
        "gf_ordering_clarify": "📐 **小提醒：** 你的已修课程里有几门好像没满足先修要求，是不是选错了？没关系，我照样帮你生成建议，注意看先修提示就好～",
        "gf_robustness_clarify": "🔢 **WAM格式有点问题哦～** 应该是0-100之间的数字，我帮你忽略这项了，不影响其他推荐！",
        # Paywall strings
        "free_count_label":   lambda n, mx: f"本月剩余免费次数：**{n}/{mx}**",
        "paywall_title":      "🔓 免费次数已用完",
        "paywall_body":       "升级到 **Pro** 继续使用，还能解锁多学期规划和PDF导出！",
        "paywall_btn":        "✨ 升级 Pro — AUD $9.9/月",
        "paywall_url":        "https://buy.stripe.com/PLACEHOLDER",
        "pro_badge":          "✨ Pro",
        "pro_locked_tip":     "🔒 Pro 功能 — 升级后解锁",
        "multisem_label":     "📅 多学期规划（Pro）",
        "multisem_tip":       "规划未来多个学期的课程路径",
        "export_btn":         "📄 导出建议书 PDF（Pro）",
    },
    "English": {
        "title": "🎓 UNSW MCom Course Advisor",
        "caption": "Master of Commerce · Course Advisor",
        "spec_label": "Specialization (select 1-2)",
        "spec_placeholder": "Choose specialization...",
        "term_label": "Planning Term",
        "wam_label": "Current WAM (optional)",
        "wam_placeholder": "e.g. 82",
        "uoc_label": "Remaining UOC",
        "completed_header": "**Completed Courses**",
        "completed_caption": "Select courses you have already completed",
        "completed_placeholder": "Select completed courses (multi-select)",
        "load_label": "Courses per term",
        "load_options": ["2 courses", "3 courses", "4 courses"],
        "notes_label": "Additional notes (optional)",
        "notes_placeholder": "e.g. avoid Fridays, interested in research...",
        "goals_header": "**Graduation Goals**",
        "goals_caption": "Step 1: Select goals; Step 2: Rate each goal",
        "goals_options": ["Continue to PhD", "Tech industry jobs", "Finance / Investment Banking",
                          "Consulting", "Entrepreneurship", "Australian work visa",
                          "Improve WAM", "Learn AI / Data"],
        "custom_goal_label": "Custom goal (optional)",
        "custom_goal_placeholder": "e.g. transition to product management...",
        "weights_caption": "Rate each goal (1 = not important, 5 = most important)",
        "submit_btn": "Generate Course Recommendations →",
        "err_no_spec": "Please select at least one specialization",
        "spinner": "AI is analysing your profile, please wait...",
        "retry_toast": "Server busy, retrying in 3s...",
        "priority_map": {"must": "🔴 Must take", "recommended": "🟢 Recommended", "optional": "⚪ Optional"},
        "handbook_btn": "📖 Handbook",
        "no_valid_courses": "AI did not return valid course codes. Please try again.",
        "goals_str_fmt": lambda gw: ", ".join([f"{g} (importance {w}/5)" for g, w in gw.items()]),
        "goals_none": "Not specified",
        "wam_none": "Not provided",
        "notes_none": "None",
        "ai_lang": "English",
        "summary_field": "one-sentence overall recommendation (English)",
        "reason_field": "2-3 sentence reason in English, referencing goal weights",
        "warning_field": "warning message or empty string",
        "prereq_label": "Prerequisites",
        "workload_label": "Workload",
        "final_label": "Final Exam",
        "final_yes": "Yes",
        "final_no": "No",
        "prereq_none": "None",
        "conflict_title": "⚠️ Prerequisite Notice",
        "conflict_body": "Some recommended courses have prerequisites you may not have completed yet:",
        "footer": "Data source: UNSW handbook (public). No scraping. · Not official academic advice.",
        # GateFix UI strings (user-facing: friendly assistant tone, no technical terms)
        "gf_pass":    None,   # silent pass — just proceed
        "gf_clarify": "💡 Quick note",
        "gf_refuse":  "🤔 Almost there! The advisor needs a bit more info to give you great recommendations",
        "gf_badge":   "✅ *Passed smart quality check*",
        "gf_relevance_refuse": "🎯 **Pick a graduation goal!** Tell me where you're headed — finance, tech, entrepreneurship, or PhD? That's how I figure out which courses suit you best 😊",
        "gf_coverage_refuse_goals": "📋 **Just select one goal and you're good to go!** Even one goal helps me tailor the recommendations to your direction～",
        "gf_coverage_refuse_uoc": "📊 **UOC and course load don't add up!** You don't have enough remaining UOC for that many courses. Try reducing the course load or updating your remaining UOC.",
        "gf_coverage_refuse_pool": "📚 **Not enough courses available!** Your current specialization doesn't have enough eligible courses. Try adding a second specialization?",
        "gf_ordering_clarify": "📐 **Just a heads-up:** Some completed courses seem to have unmet prerequisites — double check your selections. I'll still generate recommendations, just watch the prerequisite notices～",
        "gf_robustness_clarify": "🔢 **WAM format looks off～** It should be a number between 0–100. I'll ignore that field for now — won't affect your other recommendations!",
        # Paywall strings
        "free_count_label":   lambda n, mx: f"Free uses remaining: **{n}/{mx}**",
        "paywall_title":      "🔓 Free limit reached",
        "paywall_body":       "Upgrade to **Pro** to keep going — plus unlock multi-term planning and PDF export!",
        "paywall_btn":        "✨ Upgrade to Pro — AUD $9.9/mo",
        "paywall_url":        "https://buy.stripe.com/PLACEHOLDER",
        "pro_badge":          "✨ Pro",
        "pro_locked_tip":     "🔒 Pro feature — upgrade to unlock",
        "multisem_label":     "📅 Multi-term Planning (Pro)",
        "multisem_tip":       "Plan your course path across multiple future terms",
        "export_btn":         "📄 Export Recommendation PDF (Pro)",
    },
}

t = T[lang]
st.title(t["title"])
st.caption(t["caption"])

# ── Free usage counter ────────────────────────────────────────────────────────
FREE_LIMIT = 3
if "gen_count" not in st.session_state:
    st.session_state.gen_count = 0
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

# Sidebar
with st.sidebar:
    st.markdown("### 🎓 MCom Advisor")
    if st.session_state.is_pro:
        st.success(t["pro_badge"] + (" — 已激活" if lang == "中文" else " — Active"))
    else:
        remaining = max(0, FREE_LIMIT - st.session_state.gen_count)
        st.markdown(t["free_count_label"](remaining, FREE_LIMIT))
        st.progress(remaining / FREE_LIMIT)
        if remaining == 0:
            st.link_button(t["paywall_btn"], t["paywall_url"], use_container_width=True)
        st.caption("---")
    st.markdown(f"**{t['multisem_label']}**")
    st.caption(t["multisem_tip"] if st.session_state.is_pro else t["pro_locked_tip"])

# ── Step progress bar ─────────────────────────────────────────────────────────
step_labels_zh = ["🎯 目标", "📋 学习信息", "✨ 获取建议"]
step_labels_en = ["🎯 Goals", "📋 Your Profile", "✨ Get Advice"]
step_labels = step_labels_zh if lang == "中文" else step_labels_en
step_cols = st.columns(3)
for i, (col, label) in enumerate(zip(step_cols, step_labels)):
    with col:
        if i == 0:
            st.markdown(f"<div style='text-align:center;font-weight:bold;color:#FF4B4B'>{label}</div>", unsafe_allow_html=True)
        elif i == 1:
            st.markdown(f"<div style='text-align:center;color:#888'>{label}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center;color:#ccc'>{label}</div>", unsafe_allow_html=True)
st.markdown("<hr style='margin:8px 0 16px 0'>", unsafe_allow_html=True)

# ── STEP 1: Goals first ───────────────────────────────────────────────────────
st.markdown(t["goals_header"])
st.caption(t["goals_caption"])

selected_goals = st.multiselect(
    t["goals_header"],
    t["goals_options"],
    label_visibility="collapsed"
)
custom_goal = st.text_input(t["custom_goal_label"], placeholder=t["custom_goal_placeholder"])

goal_weights = {}
all_goals = selected_goals + ([custom_goal.strip()] if custom_goal.strip() else [])

if all_goals:
    st.caption(t["weights_caption"])
    for g in all_goals:
        col_name, col_score = st.columns([3, 1])
        with col_name:
            st.markdown(f"<div style='padding:6px 0;font-size:14px;'>{g}</div>",
                        unsafe_allow_html=True)
        with col_score:
            goal_weights[g] = st.selectbox(
                g, [1, 2, 3, 4, 5], index=2,
                key=f"w_{g}", label_visibility="collapsed"
            )
    fig = px.pie(
        names=list(goal_weights.keys()),
        values=list(goal_weights.values()),
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=250,
                      showlegend=True, legend=dict(font=dict(size=11)))
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── STEP 2: Profile ───────────────────────────────────────────────────────────
# Update step indicator
step_cols2 = st.columns(3)
for i, (col, label) in enumerate(zip(step_cols2, step_labels)):
    with col:
        if i == 0:
            st.markdown(f"<div style='text-align:center;color:#888'>{label}</div>", unsafe_allow_html=True)
        elif i == 1:
            st.markdown(f"<div style='text-align:center;font-weight:bold;color:#FF4B4B'>{label}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center;color:#ccc'>{label}</div>", unsafe_allow_html=True)
st.markdown("<hr style='margin:8px 0 16px 0'>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    specs = st.multiselect(
        t["spec_label"],
        list(COURSES.keys()),
        max_selections=2,
        placeholder=t["spec_placeholder"],
    )
with col2:
    term = st.selectbox(t["term_label"], [
        "Term 2 2026", "Term 3 2026", "Term 1 2027", "Term 2 2027"
    ])

col3, col4 = st.columns(2)
with col3:
    wam = st.text_input(t["wam_label"], placeholder=t["wam_placeholder"])
with col4:
    credits = st.selectbox(t["uoc_label"], [
        "96 UOC", "72 UOC", "48 UOC", "36 UOC", "24 UOC", "12 UOC"
    ])

st.markdown(t["completed_header"])
st.caption(t["completed_caption"])
completed_courses = st.multiselect(
    t["completed_header"],
    options=ALL_COURSE_CODES,
    format_func=lambda code: f"{code} · {ALL_COURSES_DICT[code]['name']}",
    placeholder=t["completed_placeholder"],
    label_visibility="collapsed",
)

load = st.radio(t["load_label"], t["load_options"], index=1, horizontal=True)
notes = st.text_input(t["notes_label"], placeholder=t["notes_placeholder"])

st.divider()
submitted = st.button(t["submit_btn"], use_container_width=True, type="primary")

COURSES = {
    "Accounting": [
        {"code": "ACCT5930", "name": "Financial Accounting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5930"},
        {"code": "ACCT5907", "name": "International Financial Statement Analysis", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5907"},
        {"code": "ACCT5910", "name": "Business Analysis and Valuation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5910"},
        {"code": "ACCT5919", "name": "Business Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5919"},
        {"code": "ACCT5925", "name": "ESG Reporting and Enterprise Value Creation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5925"},
        {"code": "ACCT5942", "name": "Corporate Accounting and Regulation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5942"},
        {"code": "ACCT5943", "name": "Advanced Financial Reporting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5943"},
        {"code": "ACCT5955", "name": "Management Control Systems in Contemporary Contexts", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5955"},
        {"code": "ACCT5961", "name": "Reporting for Climate Change and Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5961"},
        {"code": "ACCT5972", "name": "Accounting Analytics for Business Decision Making", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5972"},
        {"code": "ACCT5995", "name": "Fraud Examination Fundamentals", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5995"},
        {"code": "ACCT5996", "name": "Management Accounting and Business Analysis", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5996"},
    ],
    "Finance": [
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "FINS5513", "name": "Investments and Portfolio Selection", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5513"},
        {"code": "FINS5514", "name": "Capital Budgeting and Financial Decisions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5514"},
        {"code": "FINS5510", "name": "Personal Financial Planning", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5510"},
        {"code": "FINS5530", "name": "Financial Institution Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5530"},
        {"code": "FINS5556", "name": "From Startup to Wall Street: Financing Innovation and Strategic Exits", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5556"},
        {"code": "COMM5204", "name": "Investing for Local and Global Impact", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5204"},
        {"code": "TABL5551", "name": "Taxation Law", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/TABL5551"},
    ],
    "Economics and Finance": [
        {"code": "ECON5103", "name": "Business Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "ECON5102", "name": "Macroeconomics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5102"},
        {"code": "ECON5106", "name": "Economics of Finance", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5106"},
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "COMM5040", "name": "Entrepreneurial Ecosystems", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5040"},
        {"code": "COMM5615", "name": "Systems Thinking and Business Dynamics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5615"},
        {"code": "ECON5111", "name": "Economics of Strategy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5111"},
        {"code": "ECON5321", "name": "Industrial Organisation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5321"},
        {"code": "ECON5323", "name": "Organisational Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5323"},
        {"code": "ECON5324", "name": "Behavioural Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5324"},
    ],
    "Marketing": [
        {"code": "MARK5700", "name": "Elements of Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5700"},
        {"code": "MARK5800", "name": "Consumer Behaviour", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5800"},
        {"code": "MARK5811", "name": "Applied Marketing Research", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5811"},
        {"code": "MARK5810", "name": "Marketing Communication and Promotion", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5810"},
        {"code": "MARK5812", "name": "Distribution, Retail Channels and Logistics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5812"},
        {"code": "MARK5813", "name": "New Product and Service Development", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5813"},
        {"code": "MARK5814", "name": "Digital Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5814"},
        {"code": "MARK5816", "name": "Services Marketing Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5816"},
        {"code": "MARK5820", "name": "Events Management and Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5820"},
        {"code": "MARK5821", "name": "Brand Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5821"},
        {"code": "MARK5824", "name": "Sales Strategy and Implementation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5824"},
        {"code": "MARK5825", "name": "Global Marketing Strategy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5825"},
        {"code": "MARK5835", "name": "Artificial Intelligence in Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5835"},
    ],
    "Human Resource Management": [
        {"code": "MGMT5907", "name": "Human Resource Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5907"},
        {"code": "MGMT5908", "name": "Strategic Human Resource Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5908"},
        {"code": "MGMT5701", "name": "Global Employment Relations", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5701"},
        {"code": "MGMT5710", "name": "Managing and Leading People", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5710"},
        {"code": "MGMT5720", "name": "Sustainable and Inclusive HR", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5720"},
        {"code": "MGMT5904", "name": "Managing Organisational Change", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5904"},
        {"code": "MGMT5905", "name": "Managing Myself and Others in an AI-Enabled Workplace", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5905"},
        {"code": "MGMT5906", "name": "Organisations and People in Context", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5906"},
        {"code": "MGMT5930", "name": "Management Analytics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5930"},
        {"code": "MGMT5940", "name": "Career Management Skills", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5940"},
        {"code": "MGMT5949", "name": "International Human Resource Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5949"},
    ],
    "International Business": [
        {"code": "MGMT5601", "name": "Global Business Environment", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5601"},
        {"code": "MGMT5602", "name": "Cross-Cultural Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5602"},
        {"code": "ACCT5955", "name": "Management Control Systems in Contemporary Contexts", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5955"},
        {"code": "FINS5516", "name": "International Corporate Finance", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5516"},
        {"code": "MGMT5603", "name": "Global Business Strategy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5603"},
        {"code": "MGMT5912", "name": "Negotiating in Global Context", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5912"},
        {"code": "MGMT6005", "name": "Managing Organisational Risk in Global Context", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT6005"},
    ],
    "Information Systems": [
        {"code": "INFS5604", "name": "Optimising and Transforming Business Processes", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5604"},
        {"code": "INFS5848", "name": "Fundamentals of Information Systems and Technology Project Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5848"},
        {"code": "INFS5888", "name": "Responsible Information Technology Management: AI and Beyond", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5888"},
        {"code": "INFS5731", "name": "Information Systems Strategy and Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5731"},
        {"code": "INFS5831", "name": "Information Systems Consulting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5831"},
        {"code": "INFS5885", "name": "Business in the Digital Age", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5885"},
        {"code": "INFS5631", "name": "Managing Digital Innovations and Emerging Technologies", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5631"},
        {"code": "INFS5871", "name": "Supply Chains and Logistics Design", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5871"},
        {"code": "LAWS9812", "name": "Introduction to Law and Policy for Cyber Security", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/LAWS9812"},
    ],
    "Global Sustainability and Social Impact": [
        {"code": "COMM5202", "name": "Social and Environmental Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5202"},
        {"code": "COMM5201", "name": "Business for Social Impact", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5201"},
        {"code": "COMM5205", "name": "Leading Change for Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5205"},
        {"code": "COMM5709", "name": "Corporate Responsibility and Accountability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5709"},
    ],
    "Risk Management": [
        {"code": "RISK5001", "name": "Fundamentals of Risk and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/RISK5001"},
        {"code": "ACCT5919", "name": "Business Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5919"},
        {"code": "COMM5615", "name": "Systems Thinking and Business Dynamics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5615"},
        {"code": "FINS5513", "name": "Investments and Portfolio Selection", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5513"},
        {"code": "FINS5531", "name": "Personal Risk, Insurance, and Superannuation for Financial Advisers", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5531"},
        {"code": "FINS5535", "name": "Derivatives and Risk Management Techniques", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5535"},
        {"code": "INFS5929", "name": "Cybersecurity Leadership and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5929"},
        {"code": "MGMT6005", "name": "Managing Organisational Risk in Global Context", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT6005"},
    ],
    "Strategy and Innovation": [
        {"code": "ECON5103", "name": "Business Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "MGMT5803", "name": "Business Innovation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5803"},
        {"code": "COMM5040", "name": "Entrepreneurial Ecosystems", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5040"},
        {"code": "COMM5615", "name": "Systems Thinking and Business Dynamics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5615"},
        {"code": "ECON5111", "name": "Economics of Strategy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5111"},
        {"code": "ECON5321", "name": "Industrial Organisation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5321"},
        {"code": "ECON5323", "name": "Organisational Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5323"},
        {"code": "ECON5324", "name": "Behavioural Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5324"},
        {"code": "MGMT5603", "name": "Global Business Strategy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5603"},
        {"code": "MGMT5611", "name": "Entrepreneurship and New Venture Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5611"},
        {"code": "MGMT5800", "name": "Technology, Management and Innovation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5800"},
        {"code": "MGMT5905", "name": "Managing Myself and Others in an AI-Enabled Workplace", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5905"},
    ],
    "AI in Business and Society": [
        {"code": "COMM5007", "name": "Coding for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
        {"code": "INFS5704", "name": "Artificial Intelligence Fluency", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5704"},
        {"code": "INFS5888", "name": "Responsible Information Technology Management: AI and Beyond", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5888"},
        {"code": "ACTL5110", "name": "Statistical Machine Learning for Risk and Actuarial Applications", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACTL5110"},
        {"code": "INFS5705", "name": "Artificial Intelligence for Business Analytics in Practice", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5705"},
        {"code": "INFS5706", "name": "AI in Action", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5706"},
        {"code": "MARK5836", "name": "Artificial Intelligence for Marketing Insights", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5836"},
        {"code": "MGMT5905", "name": "Managing Myself and Others in an AI-Enabled Workplace", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5905"},
    ],
    "General / Undecided": [
        {"code": "COMM5007", "name": "Coding for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
        {"code": "ACCT5930", "name": "Financial Accounting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5930"},
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "MARK5700", "name": "Elements of Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5700"},
        {"code": "MGMT5907", "name": "Human Resource Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5907"},
        {"code": "ECON5103", "name": "Business Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "INFS5704", "name": "Artificial Intelligence Fluency", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5704"},
        {"code": "RISK5001", "name": "Fundamentals of Risk and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/RISK5001"},
    ],
}

COMMON_COURSES = [
    {"code": "COMM5000", "name": "Data Literacy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5000"},
    {"code": "COMM5007", "name": "Coding for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
]

# Deduplicated lookup of every course across all specializations + common courses
ALL_COURSES_DICT = {}
for _spec_courses in COURSES.values():
    for _c in _spec_courses:
        if _c["code"] not in ALL_COURSES_DICT:
            ALL_COURSES_DICT[_c["code"]] = _c
for _c in COMMON_COURSES:
    if _c["code"] not in ALL_COURSES_DICT:
        ALL_COURSES_DICT[_c["code"]] = _c
ALL_COURSE_CODES = sorted(ALL_COURSES_DICT.keys())

# ── Course metadata: prerequisites, workload, final exam ─────────────────────
COURSE_META = {
    "ACCT5930": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": True},
    "ACCT5907": {"prereqs": ["ACCT5930"], "workload": "~9 hrs/wk", "has_final": False},
    "ACCT5910": {"prereqs": ["ACCT5930"], "workload": "~10 hrs/wk", "has_final": False},
    "ACCT5919": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "ACCT5925": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "ACCT5942": {"prereqs": ["ACCT5930"], "workload": "~10 hrs/wk", "has_final": True},
    "ACCT5943": {"prereqs": ["ACCT5930"], "workload": "~11 hrs/wk", "has_final": True},
    "ACCT5955": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "ACCT5961": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "ACCT5972": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "ACCT5995": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "ACCT5996": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "FINS5512": {"prereqs": [], "workload": "~10 hrs/wk", "has_final": True},
    "FINS5513": {"prereqs": ["FINS5512"], "workload": "~11 hrs/wk", "has_final": True},
    "FINS5514": {"prereqs": [], "workload": "~10 hrs/wk", "has_final": True},
    "FINS5510": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "FINS5516": {"prereqs": ["FINS5512"], "workload": "~10 hrs/wk", "has_final": True},
    "FINS5530": {"prereqs": ["FINS5512"], "workload": "~10 hrs/wk", "has_final": True},
    "FINS5531": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "FINS5535": {"prereqs": ["FINS5513"], "workload": "~12 hrs/wk", "has_final": True},
    "FINS5556": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "ECON5102": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": True},
    "ECON5103": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": True},
    "ECON5106": {"prereqs": ["ECON5103"], "workload": "~10 hrs/wk", "has_final": True},
    "ECON5111": {"prereqs": ["ECON5103"], "workload": "~9 hrs/wk", "has_final": True},
    "ECON5321": {"prereqs": ["ECON5103"], "workload": "~10 hrs/wk", "has_final": True},
    "ECON5323": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": True},
    "ECON5324": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": True},
    "MARK5700": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MARK5800": {"prereqs": ["MARK5700"], "workload": "~9 hrs/wk", "has_final": False},
    "MARK5810": {"prereqs": ["MARK5700"], "workload": "~9 hrs/wk", "has_final": False},
    "MARK5811": {"prereqs": ["MARK5700"], "workload": "~10 hrs/wk", "has_final": False},
    "MARK5812": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MARK5813": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MARK5814": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MARK5816": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MARK5820": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MARK5821": {"prereqs": ["MARK5700"], "workload": "~9 hrs/wk", "has_final": False},
    "MARK5824": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MARK5825": {"prereqs": ["MARK5700"], "workload": "~9 hrs/wk", "has_final": False},
    "MARK5835": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MARK5836": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MGMT5601": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5602": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5603": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MGMT5701": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5710": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5720": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5800": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MGMT5803": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MGMT5904": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5905": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5906": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5907": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5908": {"prereqs": ["MGMT5907"], "workload": "~9 hrs/wk", "has_final": False},
    "MGMT5912": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "MGMT5930": {"prereqs": [], "workload": "~10 hrs/wk", "has_final": True},
    "MGMT5940": {"prereqs": [], "workload": "~7 hrs/wk", "has_final": False},
    "MGMT5949": {"prereqs": ["MGMT5907"], "workload": "~9 hrs/wk", "has_final": False},
    "MGMT5611": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "MGMT6005": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "INFS5604": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "INFS5631": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "INFS5704": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "INFS5705": {"prereqs": ["INFS5704"], "workload": "~10 hrs/wk", "has_final": False},
    "INFS5706": {"prereqs": ["INFS5704"], "workload": "~10 hrs/wk", "has_final": False},
    "INFS5731": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "INFS5831": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "INFS5848": {"prereqs": [], "workload": "~10 hrs/wk", "has_final": False},
    "INFS5871": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "INFS5885": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "INFS5888": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "INFS5929": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "LAWS9812": {"prereqs": [], "workload": "~10 hrs/wk", "has_final": True},
    "COMM5000": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "COMM5007": {"prereqs": [], "workload": "~10 hrs/wk", "has_final": False},
    "COMM5040": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "COMM5201": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "COMM5202": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "COMM5204": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "COMM5205": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "COMM5615": {"prereqs": [], "workload": "~9 hrs/wk", "has_final": False},
    "COMM5709": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "RISK5001": {"prereqs": [], "workload": "~8 hrs/wk", "has_final": False},
    "TABL5551": {"prereqs": [], "workload": "~10 hrs/wk", "has_final": True},
    "ACTL5110": {"prereqs": [], "workload": "~12 hrs/wk", "has_final": True},
}



if submitted:
    if not specs:
        st.error(t["err_no_spec"])
        st.stop()

    # ── Pre-compute eligible course pool ─────────────────────────────────────
    spec_pool = []
    for s in specs:
        spec_pool.extend(COURSES.get(s, []))
    all_courses_pool = COMMON_COURSES + spec_pool
    seen_codes: set = set()
    deduped = []
    for c in all_courses_pool:
        if c["code"] not in seen_codes:
            seen_codes.add(c["code"])
            deduped.append(c)
    completed_codes = set(completed_courses)
    eligible = [c for c in deduped if c["code"] not in completed_codes]
    eligible_map = {c["code"]: c for c in eligible}

    # ── GateFix: 4D-CQ pre-execution governance check ────────────────────────
    # Architecture: f(C, g) = φ(h(C, g))
    # h: context → S = (s_rel, s_cov, s_ord, s_rob)
    # φ: S → {PASS, CLARIFY, REFUSE}
    gf = run_gatefix(
        specs=specs,
        goal_weights=goal_weights,
        eligible_courses=eligible,
        completed_codes=completed_codes,
        credits_str=credits,
        load_str=load,
        wam=wam,
        course_meta=COURSE_META,
    )

    # ── φ = REFUSE: critical dimension(s) failed — block execution ────────────
    if gf.decision == "REFUSE":
        refuse_lines = []
        cq = gf.cq_vector
        if cq.relevance == "DEFECT":
            refuse_lines.append(t["gf_relevance_refuse"])
        if cq.coverage == "DEFECT":
            # Pick the most specific coverage message
            reason = cq.coverage_reason
            if "goal" in reason.lower() or "目标" in reason:
                refuse_lines.append(t["gf_coverage_refuse_goals"])
            elif "UOC" in reason or "学分" in reason:
                refuse_lines.append(t["gf_coverage_refuse_uoc"])
            else:
                refuse_lines.append(t["gf_coverage_refuse_pool"])
        st.warning(
            t["gf_refuse"] + "\n\n" +
            "\n\n".join(refuse_lines)
        )
        log_submission(
            specs=specs, goal_weights=goal_weights, completed_courses=completed_courses,
            credits=credits, load=load, wam=wam, notes=notes, term=term, lang=lang,
            gatefix_result=gf, ai_generated=False,
        )
        st.stop()

    # ── φ = CLARIFY: non-critical dimension(s) flagged — warn but proceed ─────
    if gf.decision == "CLARIFY":
        clarify_lines = []
        cq = gf.cq_vector
        if cq.ordering == "DEFECT":
            clarify_lines.append(t["gf_ordering_clarify"])
        if cq.robustness == "DEFECT":
            clarify_lines.append(t["gf_robustness_clarify"])
        st.info(t["gf_clarify"] + "\n\n" + "\n\n".join(clarify_lines))

    # ── φ = PASS: silent — just proceed cleanly ───────────────────────────────

    # ── Paywall check ─────────────────────────────────────────────────────────
    if not st.session_state.is_pro and st.session_state.gen_count >= FREE_LIMIT:
        st.warning(f"**{t['paywall_title']}**\n\n{t['paywall_body']}")
        st.link_button(t["paywall_btn"], t["paywall_url"], use_container_width=True)
        st.stop()

    # ── AI generation (authorized) ───────────────────────────────────────────
    # WAM is ignored if Robustness flagged it as invalid
    wam_str = (
        wam.strip()
        if wam.strip() and gf.cq_vector.robustness == "OK"
        else t["wam_none"]
    )
    load_num = load[0]
    goals_str = t["goals_str_fmt"](goal_weights) if goal_weights else t["goals_none"]
    spec_label = " & ".join(specs)
    response_lang = t["ai_lang"]
    eligible_codes_str = "\n".join([f"- {c['code']}: {c['name']}" for c in eligible])

    prompt = f"""You are a UNSW MCom academic advisor. Respond in {response_lang}.

Student profile:
- Specialization: {spec_label}
- Planning for: {term}
- Current WAM: {wam_str}
- Remaining UOC: {credits}
- Completed courses: {", ".join(completed_codes) if completed_codes else "None"}
- Career goals (with importance weights): {goals_str}
- Courses per term: {load_num}
- Notes: {notes.strip() if notes.strip() else t["notes_none"]}

AVAILABLE COURSES — you MUST select ONLY from the course codes listed below.
Do NOT invent, modify, or abbreviate any course code.
{eligible_codes_str}

Select exactly {load_num} course codes from the list above that best match the student's goals and specialization.

CRITICAL: Every "code" value in your JSON must exactly match one of the codes listed above. Any code not in the list will be discarded.

Respond ONLY with valid JSON (no markdown):
{{"summary":"{t['summary_field']}","selections":[{{"code":"XXXX0000","priority":"must|recommended|optional","reason":"{t['reason_field']}"}}],"warning":"{t['warning_field']}"}}"""

    with st.spinner(t["spinner"]):
        ai_generated = False
        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            for attempt in range(3):
                try:
                    message = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    break
                except Exception as e:
                    if "529" in str(e) and attempt < 2:
                        st.toast(t["retry_toast"])
                        time.sleep(3)
                    else:
                        raise e

            raw = message.content[0].text.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            ai_generated = True

            if result.get("warning"):
                st.warning(result["warning"])
            st.info(result.get("summary", ""))

            # ── Conflict / prerequisite banner ───────────────────────────────
            conflict_lines = []
            for s in result.get("selections", []):
                code = s.get("code", "")
                meta = COURSE_META.get(code, {})
                unmet = [p for p in meta.get("prereqs", []) if p not in completed_codes]
                if unmet:
                    course_name = eligible_map.get(code, {}).get("name", code)
                    conflict_lines.append(f"**{code} {course_name}** — {t['prereq_label']}: {', '.join(unmet)}")
            if conflict_lines:
                with st.container(border=False):
                    st.warning(
                        t["conflict_title"] + "\n\n" +
                        t["conflict_body"] + "\n\n" +
                        "\n\n".join(f"- {line}" for line in conflict_lines)
                    )

            priority_map = t["priority_map"]
            valid_shown = 0
            for s in result.get("selections", []):
                code = s.get("code", "")
                course = eligible_map.get(code)
                if not course:
                    continue
                valid_shown += 1
                label = priority_map.get(s.get("priority", "optional"), priority_map["optional"])
                meta = COURSE_META.get(code, {})
                prereq_display = ", ".join(meta["prereqs"]) if meta.get("prereqs") else t["prereq_none"]
                workload_display = meta.get("workload", "—")
                final_display = t["final_yes"] if meta.get("has_final") else t["final_no"] if "has_final" in meta else "—"
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{label} · {course['code']}**")
                        st.markdown(f"#### {course['name']}")
                        st.write(s["reason"])
                        st.markdown(
                            f"<small>🔗 **{t['prereq_label']}:** {prereq_display} &nbsp;|&nbsp; "
                            f"⏱ **{t['workload_label']}:** {workload_display} &nbsp;|&nbsp; "
                            f"📝 **{t['final_label']}:** {final_display}</small>",
                            unsafe_allow_html=True,
                        )
                    with col_b:
                        st.link_button(t["handbook_btn"], course["url"], use_container_width=True)

            if valid_shown == 0:
                st.error(t["no_valid_courses"])
            else:
                st.caption(t["gf_badge"])
                st.session_state.gen_count += 1
                # ── Pro: PDF export ───────────────────────────────────────────
                st.divider()
                if st.session_state.is_pro:
                    if st.button(t["export_btn"], use_container_width=True):
                        st.info("PDF导出功能开发中，敬请期待！" if lang == "中文" else "PDF export coming soon!")
                else:
                    # Blur-gate: show upgrade prompt inline under results
                    remaining_after = max(0, FREE_LIMIT - st.session_state.gen_count)
                    if remaining_after == 0:
                        st.markdown(
                            "<div style='filter:blur(3px);pointer-events:none;opacity:0.5'>"
                            + ("🔒 解锁更多功能..." if lang == "中文" else "🔒 Unlock more features...")
                            + "</div>",
                            unsafe_allow_html=True
                        )
                        st.warning(t["paywall_title"] + "\n\n" + t["paywall_body"])
                        st.link_button(t["paywall_btn"], t["paywall_url"], use_container_width=True)
                    else:
                        col_pdf, col_up = st.columns([2, 1])
                        with col_pdf:
                            st.button(t["export_btn"], disabled=True, use_container_width=True)
                        with col_up:
                            st.link_button(t["paywall_btn"], t["paywall_url"], use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")

        finally:
            # Always log — regardless of AI success/failure
            try:
                log_submission(
                    specs=specs, goal_weights=goal_weights,
                    completed_courses=completed_courses,
                    credits=credits, load=load, wam=wam, notes=notes,
                    term=term, lang=lang,
                    gatefix_result=gf, ai_generated=ai_generated,
                )
            except Exception:
                pass  # Never break the app due to logging failure

st.divider()
col_footer, col_feedback = st.columns([3, 1])
with col_footer:
    st.caption(t["footer"])
with col_feedback:
    st.link_button(
        "📝 提交反馈 / Give Feedback",
        "https://docs.google.com/forms/d/e/1FAIpQLSe_YdjLFQOtPsEzV5n5Zdi1jPfq35Nk3cgoNESinbCEqFzNhw/viewform",
        use_container_width=True,
    )
