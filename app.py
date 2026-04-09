import streamlit as st
import anthropic
import json
import time
import plotly.express as px

st.set_page_config(page_title="UNSW MCom 选课助手", page_icon="🎓", layout="centered")
st.title("🎓 UNSW MCom 选课助手")
st.caption("Master of Commerce · Course Advisor")

COURSES = {
    "Information Systems": [
        {"code": "INFS5704", "name": "Enterprise Systems", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5704"},
        {"code": "INFS5710", "name": "Business Intelligence and Data Warehousing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5710"},
        {"code": "INFS5714", "name": "Project Management in Practice", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5714"},
        {"code": "INFS5741", "name": "Managing IT Outsourcing and Offshoring", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5741"},
        {"code": "INFS5848", "name": "Digital Innovation and Entrepreneurship", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5848"},
        {"code": "INFS5882", "name": "Business Process Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5882"},
        {"code": "INFS6021", "name": "Audit and IT Governance", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS6021"},
        {"code": "INFS6030", "name": "Cybersecurity and Privacy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS6030"},
        {"code": "INFS5800", "name": "Strategy, Innovation and Entrepreneurship", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5800"},
        {"code": "COMM5111", "name": "Research Methods in Information Systems", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5111"},
    ],
    "Finance": [
        {"code": "FINS5510", "name": "Personal Financial Planning", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5510"},
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "FINS5514", "name": "Capital Budgeting and Financial Decisions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5514"},
        {"code": "FINS5516", "name": "International Finance", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5516"},
        {"code": "FINS5517", "name": "Investments and Portfolio Selection", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5517"},
        {"code": "FINS5519", "name": "Derivatives and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5519"},
        {"code": "FINS5535", "name": "Debt Markets and Fixed Income Securities", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5535"},
        {"code": "FINS5536", "name": "Options, Futures and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5536"},
        {"code": "FINS5542", "name": "Applied Funds Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5542"},
        {"code": "FINS5568", "name": "Financial Regulation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5568"},
    ],
    "Accounting": [
        {"code": "ACCT5001", "name": "Accounting for Managerial Decisions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5001"},
        {"code": "ACCT5002", "name": "Financial Accounting and Reporting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5002"},
        {"code": "ACCT5003", "name": "Management Accounting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5003"},
        {"code": "ACCT5004", "name": "Auditing and Assurance Services", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5004"},
        {"code": "ACCT5005", "name": "Corporate Governance and Accountability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5005"},
        {"code": "ACCT5006", "name": "Taxation Law and Practice", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5006"},
        {"code": "ACCT5007", "name": "Advanced Financial Accounting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5007"},
        {"code": "ACCT5009", "name": "Sustainability and Integrated Reporting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5009"},
    ],
    "Marketing": [
        {"code": "MARK5804", "name": "Marketing Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5804"},
        {"code": "MARK5806", "name": "Consumer Behaviour", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5806"},
        {"code": "MARK5808", "name": "Marketing Research", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5808"},
        {"code": "MARK5810", "name": "Digital Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5810"},
        {"code": "MARK5812", "name": "Strategic Brand Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5812"},
        {"code": "MARK5814", "name": "Services Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5814"},
        {"code": "MARK5816", "name": "Business to Business Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5816"},
        {"code": "MARK5820", "name": "International Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5820"},
    ],
    "Economics": [
        {"code": "ECON5103", "name": "Business Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "ECON5106", "name": "Applied Econometrics for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5106"},
        {"code": "ECON5108", "name": "Industry Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5108"},
        {"code": "ECON5110", "name": "International Trade and Finance", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5110"},
        {"code": "ECON5111", "name": "Behavioural Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5111"},
        {"code": "ECON5203", "name": "Advanced Econometrics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5203"},
    ],
    "Business Analytics": [
        {"code": "COMM5007", "name": "Data Analysis for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
        {"code": "INFS5710", "name": "Business Intelligence and Data Warehousing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5710"},
        {"code": "INFS5882", "name": "Business Process Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5882"},
        {"code": "ECON5106", "name": "Applied Econometrics for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5106"},
        {"code": "COMP5318", "name": "Machine Learning and Data Mining", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMP5318"},
    ],
    "Human Resource Management": [
        {"code": "MGMT5601", "name": "Human Resource Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5601"},
        {"code": "MGMT5603", "name": "Employment Relations", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5603"},
        {"code": "MGMT5605", "name": "Organisational Behaviour", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5605"},
        {"code": "MGMT5607", "name": "Strategic Human Resource Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5607"},
        {"code": "MGMT5609", "name": "Managing Diversity in Organisations", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5609"},
        {"code": "MGMT5611", "name": "Leadership and Motivation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5611"},
        {"code": "MGMT5613", "name": "Negotiation and Conflict Resolution", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5613"},
    ],
    "International Business": [
        {"code": "MGMT5501", "name": "International Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5501"},
        {"code": "MGMT5503", "name": "Multinational Enterprise", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5503"},
        {"code": "MARK5820", "name": "International Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5820"},
        {"code": "FINS5516", "name": "International Finance", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5516"},
        {"code": "ECON5110", "name": "International Trade and Finance", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5110"},
        {"code": "MGMT5505", "name": "Global Strategy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5505"},
    ],
    "Global Sustainability and Social Impact": [
        {"code": "COMM5202", "name": "Social and Environmental Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5202"},
        {"code": "COMM5205", "name": "Leading Change for Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5205"},
        {"code": "MGMT5501", "name": "International Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5501"},
        {"code": "MGMT5605", "name": "Organisational Behaviour", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5605"},
        {"code": "ECON5103", "name": "Business Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "ACCT5009", "name": "Sustainability and Integrated Reporting", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5009"},
    ],
    "AI in Business and Society": [
        # ⚠️ 课程代码待从 UNSW handbook 确认后补充
        # https://www.handbook.unsw.edu.au/postgraduate/specialisations/2026/commls
        {"code": "INFS5848", "name": "Digital Innovation and Entrepreneurship", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5848"},
        {"code": "INFS5710", "name": "Business Intelligence and Data Warehousing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5710"},
        {"code": "COMP5318", "name": "Machine Learning and Data Mining", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMP5318"},
        {"code": "INFS6030", "name": "Cybersecurity and Privacy", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS6030"},
        {"code": "INFS5882", "name": "Business Process Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5882"},
        {"code": "ECON5106", "name": "Applied Econometrics for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5106"},
    ],
    "General / Undecided": [
        {"code": "COMM5000", "name": "Business Research Methods", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5000"},
        {"code": "COMM5007", "name": "Data Analysis for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
        {"code": "ACCT5001", "name": "Accounting for Managerial Decisions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5001"},
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "MARK5804", "name": "Marketing Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5804"},
        {"code": "MGMT5605", "name": "Organisational Behaviour", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5605"},
        {"code": "ECON5103", "name": "Business Economics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "INFS5704", "name": "Enterprise Systems", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5704"},
    ],
}

COMMON_COURSES = [
    {"code": "COMM5000", "name": "Business Research Methods", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5000"},
    {"code": "COMM5007", "name": "Data Analysis for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
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

col1, col2 = st.columns(2)
with col1:
    specs = st.multiselect(
        "专业方向（可选 1-2 个）",
        list(COURSES.keys()),
        max_selections=2,
        placeholder="选择专业方向...",
    )
with col2:
    term = st.selectbox("规划学期", [
        "Term 1 2026", "Term 2 2026", "Term 3 2026", "Term 1 2027"
    ])

col3, col4 = st.columns(2)
with col3:
    wam = st.text_input("当前 WAM（可选）", placeholder="例如 82")
with col4:
    credits = st.selectbox("剩余学分", [
        "96 UOC", "72 UOC", "48 UOC", "36 UOC", "24 UOC", "12 UOC"
    ])

st.markdown("**已修课程**")
st.caption("从列表中选择已修过的课程")
completed_courses = st.multiselect(
    "已修课程",
    options=ALL_COURSE_CODES,
    format_func=lambda code: f"{code} · {ALL_COURSES_DICT[code]['name']}",
    placeholder="选择已修课程（可多选）",
    label_visibility="collapsed",
)

load = st.radio("每学期课程数量", ["2门", "3门", "4门"], index=1, horizontal=True)
notes = st.text_input("其他备注（可选）", placeholder="例如：避开周五，想做研究项目...")

st.divider()
st.markdown("**毕业目标**")
st.caption("第一步：选择目标；第二步：为每个目标打分")

selected_goals = st.multiselect(
    "选择目标（可多选）",
    ["继续读博士 PhD", "科技行业就业", "金融/投行", "咨询 Consulting",
     "创业", "留澳工作签证", "提高 WAM", "学习 AI/数据"],
    label_visibility="collapsed"
)
custom_goal = st.text_input("自定义目标（可选）", placeholder="例如：转型做产品经理...")

goal_weights = {}
all_goals = selected_goals + ([custom_goal.strip()] if custom_goal.strip() else [])

if all_goals:
    st.caption("为每个目标打分（1=不重要，5=最重要）")
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
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280,
                      showlegend=True, legend=dict(font=dict(size=11)))
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
submitted = st.button("生成选课建议 →", use_container_width=True, type="primary")

if submitted:
    if not specs:
        st.error("请至少选择一个专业方向")
        st.stop()

    wam_str = wam.strip() if wam.strip() else "未提供"
    load_num = load[0]
    goals_str = "、".join([
        f"{g}（重要程度{w}/5）" for g, w in goal_weights.items()
    ]) if goal_weights else "未指定"

    # Combine courses from all selected specializations
    spec_pool = []
    for s in specs:
        spec_pool.extend(COURSES.get(s, []))

    all_courses = COMMON_COURSES + spec_pool
    seen = set()
    deduped = []
    for c in all_courses:
        if c["code"] not in seen:
            seen.add(c["code"])
            deduped.append(c)
    all_courses = deduped

    completed_codes = set(completed_courses)
    eligible = [c for c in all_courses if c["code"] not in completed_codes]
    eligible_map = {c["code"]: c for c in eligible}
    # Include names in the list so the AI can reason about course content
    eligible_codes_str = "\n".join([f"- {c['code']}: {c['name']}" for c in eligible])

    spec_label = " & ".join(specs)

    prompt = f"""You are a UNSW MCom academic advisor.

Student profile:
- Specialization: {spec_label}
- Planning for: {term}
- Current WAM: {wam_str}
- Remaining UOC: {credits}
- Completed courses: {", ".join(completed_codes) if completed_codes else "None"}
- Career goals (with importance weights): {goals_str}
- Courses per term: {load_num}
- Notes: {notes.strip() if notes.strip() else "None"}

AVAILABLE COURSES — you MUST select ONLY from the course codes listed below.
Do NOT invent, modify, or abbreviate any course code.
{eligible_codes_str}

Select exactly {load_num} course codes from the list above that best match the student's goals and specialization.

CRITICAL: Every "code" value in your JSON must exactly match one of the codes listed above. Any code not in the list will be discarded.

Respond ONLY with valid JSON (no markdown):
{{"summary":"一句话总体建议（中文）","selections":[{{"code":"XXXX0000","priority":"must|recommended|optional","reason":"2-3句中文理由，结合目标权重"}}],"warning":"提醒或空字符串"}}"""

    with st.spinner("AI 分析中，请稍候..."):
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
                        st.toast("服务器繁忙，3秒后重试...")
                        time.sleep(3)
                    else:
                        raise e

            raw = message.content[0].text.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            if result.get("warning"):
                st.warning(result["warning"])
            st.info(result.get("summary", ""))

            priority_map = {"must": "🔴 必选", "recommended": "🟢 强烈推荐", "optional": "⚪ 可选"}
            valid_shown = 0
            for s in result.get("selections", []):
                code = s.get("code", "")
                course = eligible_map.get(code)
                if not course:
                    continue
                valid_shown += 1
                label = priority_map.get(s.get("priority", "optional"), "⚪ 可选")
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{label} · {course['code']}**")
                        st.markdown(f"#### {course['name']}")
                        st.write(s["reason"])
                    with col_b:
                        st.link_button("📖 Handbook", course["url"], use_container_width=True)

            if valid_shown == 0:
                st.error("AI 未能返回有效课程代码，请重试。")

        except Exception as e:
            st.error(f"出错了：{e}")
