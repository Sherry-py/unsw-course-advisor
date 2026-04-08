import streamlit as st
import anthropic
import json
import plotly.express as px

st.set_page_config(page_title="UNSW MCom 选课助手", page_icon="🎓", layout="centered")
st.title("🎓 UNSW MCom 选课助手")
st.caption("Master of Commerce · Course Advisor")

with st.form("advisor_form"):
    col1, col2 = st.columns(2)
    with col1:
        spec = st.selectbox("专业方向", [
            "Information Systems", "Finance", "Accounting",
            "Marketing", "Economics", "Business Analytics",
            "Human Resource Management", "General / Undecided"
        ])
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
    st.caption("每行一门，格式：课程代码 + 空格 + 成绩（HD / DN / CR / PS）")
    template_clicked = st.form_submit_button("📋 填入格式示例")
    courses = st.text_area(
        "已修课程",
        value="COMM5000 HD\nCOMM5007 DN\nINFS5704 CR" if template_clicked else "",
        placeholder="COMM5000 HD\nINFS5704 CR\nFINS5512 DN",
        height=120,
        label_visibility="collapsed"
    )

    st.markdown("**毕业目标**")
    st.caption("选择目标后为每个目标打分（1=不重要，5=最重要）")
    selected_goals = st.multiselect(
        "选择目标（可多选）",
        ["继续读博士 PhD", "科技行业就业", "金融/投行", "咨询 Consulting",
         "创业", "留澳工作签证", "提高 WAM", "学习 AI/数据"],
        label_visibility="collapsed"
    )
    custom_goal = st.text_input("自定义目标（可选）", placeholder="例如：转型做产品经理...")

    goal_weights = {}
    if selected_goals:
        for g in selected_goals:
            col_name, col_score = st.columns([3, 1])
            with col_name:
                st.markdown(f"<div style='padding:8px 0;font-size:14px;'>{g}</div>", unsafe_allow_html=True)
            with col_score:
                goal_weights[g] = st.selectbox(
                    g, [1, 2, 3, 4, 5], index=2,
                    key=f"w_{g}", label_visibility="collapsed"
                )
    if custom_goal.strip():
        col_name, col_score = st.columns([3, 1])
        with col_name:
            st.markdown(f"<div style='padding:8px 0;font-size:14px;'>{custom_goal.strip()}</div>", unsafe_allow_html=True)
        with col_score:
            goal_weights[custom_goal.strip()] = st.selectbox(
                custom_goal.strip(), [1, 2, 3, 4, 5], index=2,
                key="w_custom", label_visibility="collapsed"
            )

    load = st.radio("每学期课程数量", ["2门", "3门", "4门"], index=1, horizontal=True)
    notes = st.text_input("其他备注（可选）", placeholder="例如：避开周五，想做研究项目...")
    submitted = st.form_submit_button("生成选课建议 →", use_container_width=True, type="primary")

if goal_weights:
    fig = px.pie(
        names=list(goal_weights.keys()),
        values=list(goal_weights.values()),
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        showlegend=True,
        legend=dict(font=dict(size=11))
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

if submitted:
    wam_str = wam.strip() if wam.strip() else "未提供"
    load_num = load[0]
    goals_str = "、".join([
        f"{g}（重要程度{w}/5）" for g, w in goal_weights.items()
    ]) if goal_weights else "未指定"

    prompt = f"""You are a precise UNSW academic advisor for the Master of Commerce (MCom) program at UNSW Sydney.

Student profile:
- Specialization: {spec}
- Planning for: {term}
- Current WAM: {wam_str}
- Remaining UOC: {credits}
- Completed courses: {courses.strip() if courses.strip() else '暂无'}
- Career goals (with importance weights): {goals_str}
- Courses per term: {load_num}
- Notes: {notes.strip() if notes.strip() else '无'}

Recommend exactly {load_num} real UNSW MCom courses for next term.
Prioritise courses that best match the student's highest-weighted goals.
Only use verified UNSW course codes such as: INFS5710, INFS5704, INFS5814, INFS6021, INFS5741, COMM5000, COMM5007, COMM5111, FINS5512, FINS5510, ACCT5001, MARK5804, ECON5103, INFS5848, INFS5882.
Do NOT recommend courses already completed by the student.

Respond ONLY with valid JSON (no markdown):
{{"summary":"一句话总体建议（中文）","courses":[{{"code":"XXXX0000","name":"Full English Course Name","priority":"must|recommended|optional","reason":"2-3句中文理由，结合目标权重分析"}}],"warning":"重要提醒（中文），如无则为空字符串"}}"""

    with st.spinner("AI 分析中，请稍候..."):
        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            if result.get("warning"):
                st.warning(result["warning"])
            st.info(result.get("summary", ""))

            priority_map = {
                "must": "🔴 必选",
                "recommended": "🟢 强烈推荐",
                "optional": "⚪ 可选"
            }
            for c in result.get("courses", []):
                label = priority_map.get(c.get("priority", "optional"), "⚪ 可选")
                code = c.get("code", "")
                url = f"https://www.handbook.unsw.edu.au/postgraduate/courses/2026/{code}"
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**{label} · {code}**")
                        st.markdown(f"#### {c['name']}")
                        st.write(c["reason"])
                    with col_b:
                        st.link_button("📖 Handbook", url, use_container_width=True)

        except Exception as e:
            st.error(f"出错了：{e}")