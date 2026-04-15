import streamlit as st
import anthropic
import json
import time
import os
import plotly.express as px
import governance as gf_engine
from datetime import datetime, timezone

# ── Feedback logging ──────────────────────────────────────────────────────────
_FEEDBACK_LOG = os.path.join(os.path.dirname(__file__), "feedback_log.jsonl")

def _log_feedback(rating: str, comment: str, session_id: str, gate_decision: str, lang: str):
    import uuid
    record = {
        "id":           str(uuid.uuid4()),
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "session_id":   session_id,
        "gate_decision":gate_decision,
        "rating":       rating,          # "bad" | "ok" | "great"
        "comment":      comment.strip() if comment else "",
        "lang":         lang,
    }
    try:
        with open(_FEEDBACK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # Dual-write to Supabase
    try:
        import supabase_logger
        supabase_logger.append_record("feedback_log", record)
    except Exception:
        pass

st.set_page_config(
    page_title="UNSW MCom Course Advisor",
    page_icon="🎓",
    layout="centered",
)

# ── Hide "Select all" in multiselect via JS MutationObserver ──────────────────
import streamlit.components.v1 as _components
_components.html("""
<script>
  (function() {
    function hideSelectAll() {
      try {
        var doc = window.parent.document;
        doc.querySelectorAll('li[role="option"]').forEach(function(li) {
          if ((li.innerText || li.textContent || '').trim().toLowerCase() === 'select all') {
            li.style.display = 'none';
          }
        });
      } catch(e) {}
    }
    new MutationObserver(hideSelectAll).observe(
      window.parent.document.body,
      {childList: true, subtree: true}
    );
    hideSelectAll();
  })();
</script>
""", height=0, scrolling=False)

# ── Pixel town CSS ────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

/* ── Background: dark pixel grid ── */
.stApp {
  background-color: #0d0d1f !important;
  background-image:
    linear-gradient(rgba(129,140,248,.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(129,140,248,.04) 1px, transparent 1px);
  background-size: 24px 24px;
}

/* ── Main title ── */
.stApp h1 {
  font-family: 'Press Start 2P', monospace !important;
  font-size: 17px !important;
  color: #a5b4fc !important;
  text-shadow: 3px 3px 0 #1e1b4b, 6px 6px 0 #0d0d1f !important;
  letter-spacing: 1px;
  line-height: 1.7 !important;
}

/* ── Section subheadings ── */
.stApp h2, .stApp h3 {
  font-family: 'Press Start 2P', monospace !important;
  font-size: 10px !important;
  color: #34d399 !important;
  letter-spacing: 1px;
  line-height: 2 !important;
}

/* ── Caption / small text ── */
.stApp .stCaption {
  color: #6b7280 !important;
  font-family: 'Courier New', monospace !important;
  font-size: 11px !important;
}

/* ── Buttons – pixel press style ── */
.stButton > button {
  font-family: 'Press Start 2P', monospace !important;
  font-size: 8px !important;
  background: #1e1b4b !important;
  border: 3px solid #4f46e5 !important;
  border-radius: 0 !important;
  color: #c7d2fe !important;
  box-shadow: 4px 4px 0 #312e81 !important;
  transition: transform .08s, box-shadow .08s !important;
  letter-spacing: .5px;
}
.stButton > button:hover {
  transform: translate(2px,2px) !important;
  box-shadow: 2px 2px 0 #312e81 !important;
}
.stButton > button:active {
  transform: translate(4px,4px) !important;
  box-shadow: 0 0 0 #312e81 !important;
}
/* Primary submit button */
.stButton > button[kind="primary"] {
  background: #4f46e5 !important;
  border: 3px solid #818cf8 !important;
  color: #fff !important;
  box-shadow: 4px 4px 0 #1e1b4b !important;
  font-size: 10px !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input {
  background: #0d0d1f !important;
  border: 2px solid #374151 !important;
  border-radius: 0 !important;
  color: #e5e7eb !important;
  font-family: 'Courier New', monospace !important;
  font-size: 13px !important;
}
.stTextInput > div > div > input:focus {
  border: 2px solid #818cf8 !important;
  box-shadow: 0 0 0 !important;
}
/* ── Placeholder text — bright enough to read ── */
.stTextInput > div > div > input::placeholder {
  color: #94a3b8 !important;
  opacity: 1 !important;
}
textarea::placeholder {
  color: #94a3b8 !important;
  opacity: 1 !important;
}

/* ── Labels / widget text ── */
.stTextInput label, .stSelectbox label,
.stMultiSelect label, .stRadio label,
.stMarkdown p, .stMarkdown li {
  color: #cbd5e1 !important;
  font-family: 'Courier New', monospace !important;
}

/* ── Radio options ── */
.stRadio > div label {
  color: #94a3b8 !important;
  font-family: 'Courier New', monospace !important;
}
.stRadio > div label:hover { color: #e2e8f0 !important; }

/* ── Plotly chart transparent bg ── */
.js-plotly-plot .plotly, .js-plotly-plot .plotly .main-svg {
  background: transparent !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
  background: #0d0d1f !important;
  border: 2px solid #374151 !important;
  border-radius: 0 !important;
  color: #e5e7eb !important;
}

/* ── Multiselect ── */
.stMultiSelect > div {
  border: 2px solid #374151 !important;
  border-radius: 0 !important;
  background: #0d0d1f !important;
}
.stMultiSelect span[data-baseweb="tag"] {
  background: #1e1b4b !important;
  border-radius: 0 !important;
  border: 1px solid #4f46e5 !important;
}

/* ── Dividers ── */
hr {
  border-color: #1f2937 !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
  background: #0d0d1f !important;
  border: 2px solid #1f2937 !important;
  border-radius: 0 !important;
  font-family: 'Press Start 2P', monospace !important;
  font-size: 8px !important;
  color: #818cf8 !important;
}
.streamlit-expanderContent {
  background: #0d0d1f !important;
  border: 2px solid #1f2937 !important;
  border-top: none !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #0a0a18 !important;
  border-right: 3px solid #1f2937 !important;
}

/* ── Metric cards (GateFix 4D) ── */
[data-testid="stMetric"] {
  background: #111827 !important;
  border: 2px solid #374151 !important;
  border-radius: 0 !important;
  padding: 8px !important;
}

/* ── Hide "Select all" in multiselect dropdowns ── */
[data-testid="stMultiSelectSelectAll"],
[data-testid="stMultiSelectCheckAll"],
[data-baseweb="menu"] li[role="option"]:first-child:has(input[type="checkbox"]:indeterminate) {
  display: none !important;
}

/* ── Fix white search box in multiselect dropdown ── */
[data-baseweb="select-dropdown"],
[data-baseweb="select-dropdown"] > div,
[data-baseweb="popover"] [data-baseweb="base-input"],
[data-baseweb="popover"] [data-baseweb="base-input"] > div,
[data-baseweb="popover"] input,
[data-baseweb="popover"] input + div,
[data-baseweb="popover"] > div > div:first-child,
[data-baseweb="popover"] > div > div:first-child > div {
  background: #0d0d1f !important;
  background-color: #0d0d1f !important;
  color: #c7d2fe !important;
  border-color: #4f46e5 !important;
}

/* ── BaseWeb dropdown overlay (multiselect / selectbox menus) ── */
[data-baseweb="popover"] > div,
[data-baseweb="popover"] {
  background: #0d0d1f !important;
  border: 2px solid #4f46e5 !important;
  border-radius: 0 !important;
  box-shadow: 4px 4px 0 #1e1b4b !important;
}
[data-baseweb="menu"] {
  background: #0d0d1f !important;
  border-radius: 0 !important;
}
[data-baseweb="menu"] ul {
  background: #0d0d1f !important;
}
li[role="option"], [data-baseweb="option"] {
  background: #0d0d1f !important;
  color: #c7d2fe !important;
  font-family: 'Courier New', monospace !important;
  font-size: 13px !important;
  border-bottom: 1px solid #1f2937 !important;
  padding: 10px 14px !important;
}
li[role="option"]:hover, [data-baseweb="option"]:hover,
li[role="option"][aria-selected="true"] {
  background: #1e1b4b !important;
  color: #a5b4fc !important;
}
/* Selectbox selected value text */
[data-baseweb="select"] > div {
  background: #0d0d1f !important;
  border: 2px solid #374151 !important;
  border-radius: 0 !important;
  color: #e2e8f0 !important;
  font-family: 'Courier New', monospace !important;
}
[data-baseweb="select"] span {
  color: #e2e8f0 !important;
  font-family: 'Courier New', monospace !important;
}
/* Scrollbar inside dropdown */
[data-baseweb="menu"] *::-webkit-scrollbar { width: 6px !important; }
[data-baseweb="menu"] *::-webkit-scrollbar-track { background: #0d0d1f !important; }
[data-baseweb="menu"] *::-webkit-scrollbar-thumb { background: #374151 !important; border-radius: 0 !important; }

/* ── Link buttons (st.link_button) — gold Annual Pass style ── */
[data-testid="stLinkButton"] a {
  font-family: 'Press Start 2P', monospace !important;
  font-size: 8px !important;
  background: linear-gradient(135deg, #92400e 0%, #78350f 100%) !important;
  border: 3px solid #f59e0b !important;
  border-radius: 0 !important;
  color: #fef3c7 !important;
  box-shadow: 4px 4px 0 #451a03, 0 0 12px rgba(245,158,11,.25) !important;
  text-decoration: none !important;
  transition: transform .08s, box-shadow .08s !important;
  letter-spacing: .5px;
  display: block;
  padding: 10px 16px !important;
  text-align: center;
  animation: pass-glow 2.4s ease-in-out infinite;
}
[data-testid="stLinkButton"] a:hover {
  transform: translate(2px,2px) !important;
  box-shadow: 2px 2px 0 #451a03, 0 0 18px rgba(245,158,11,.4) !important;
  color: #fff !important;
}
@keyframes pass-glow {
  0%,100% { box-shadow: 4px 4px 0 #451a03, 0 0 8px rgba(245,158,11,.2); }
  50%      { box-shadow: 4px 4px 0 #451a03, 0 0 18px rgba(245,158,11,.5); }
}

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div {
  background: #1f2937 !important;
  border-radius: 0 !important;
  border: 1px solid #374151 !important;
}
[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg, #4f46e5, #818cf8) !important;
  border-radius: 0 !important;
}

/* ── Warning/info boxes ── */
[data-testid="stAlert"] {
  border-radius: 0 !important;
  border-left: 4px solid #f59e0b !important;
  background: #1a1200 !important;
  font-family: 'Courier New', monospace !important;
}

/* ── Containers with border ── */
[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-radius: 0 !important;
  border: 2px solid #1f2937 !important;
  background: #0a0a18 !important;
}

/* ── RPG dialog animation ── */
@keyframes blink-cursor {
  0%,49%{opacity:1} 50%,100%{opacity:0}
}
@keyframes float-up {
  0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)}
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# CONSTANTS & COURSE DATA
# (must appear before any st.* widget calls)
# ════════════════════════════════════════════════════════

FREE_LIMIT = 3  # free AI generations per session

COURSES = {
    "Accounting": [
        {"code": "ACCT5930", "name": "Financial Accounting",              "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5930"},
        {"code": "ACCT5907", "name": "International Financial Statement Analysis", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5907"},
        {"code": "ACCT5910", "name": "Business Analysis and Valuation",   "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5910"},
        {"code": "ACCT5919", "name": "Business Risk Management",          "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5919"},
        {"code": "ACCT5925", "name": "ESG Reporting and Enterprise Value Creation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5925"},
        {"code": "ACCT5942", "name": "Corporate Accounting and Regulation","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5942"},
        {"code": "ACCT5943", "name": "Advanced Financial Reporting",      "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5943"},
        {"code": "ACCT5955", "name": "Management Control Systems in Contemporary Contexts", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5955"},
        {"code": "ACCT5961", "name": "Reporting for Climate Change and Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5961"},
        {"code": "ACCT5972", "name": "Accounting Analytics for Business Decision Making", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5972"},
        {"code": "ACCT5995", "name": "Fraud Examination Fundamentals",    "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5995"},
        {"code": "ACCT5996", "name": "Management Accounting and Business Analysis", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5996"},
    ],
    "Finance": [
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "FINS5513", "name": "Investments and Portfolio Selection","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5513"},
        {"code": "FINS5514", "name": "Capital Budgeting and Financial Decisions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5514"},
        {"code": "FINS5510", "name": "Personal Financial Planning",        "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5510"},
        {"code": "FINS5530", "name": "Financial Institution Management",   "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5530"},
        {"code": "FINS5556", "name": "From Startup to Wall Street: Financing Innovation and Strategic Exits", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5556"},
        {"code": "COMM5204", "name": "Investing for Local and Global Impact", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5204"},
        {"code": "TABL5551", "name": "Taxation Law",                      "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/TABL5551"},
    ],
    "Economics and Finance": [
        {"code": "ECON5103", "name": "Business Economics",                "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "ECON5102", "name": "Macroeconomics",                    "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5102"},
        {"code": "ECON5106", "name": "Economics of Finance",              "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5106"},
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "COMM5040", "name": "Entrepreneurial Ecosystems",        "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5040"},
        {"code": "COMM5615", "name": "Systems Thinking and Business Dynamics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5615"},
        {"code": "ECON5111", "name": "Economics of Strategy",             "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5111"},
        {"code": "ECON5321", "name": "Industrial Organisation",            "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5321"},
        {"code": "ECON5323", "name": "Organisational Economics",          "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5323"},
        {"code": "ECON5324", "name": "Behavioural Economics",             "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5324"},
    ],
    "Marketing": [
        {"code": "MARK5700", "name": "Elements of Marketing",            "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5700"},
        {"code": "MARK5800", "name": "Consumer Behaviour",               "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5800"},
        {"code": "MARK5811", "name": "Applied Marketing Research",       "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5811"},
        {"code": "MARK5810", "name": "Marketing Communication and Promotion", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5810"},
        {"code": "MARK5812", "name": "Distribution, Retail Channels and Logistics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5812"},
        {"code": "MARK5813", "name": "New Product and Service Development","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5813"},
        {"code": "MARK5814", "name": "Digital Marketing",                "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5814"},
        {"code": "MARK5816", "name": "Services Marketing Management",    "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5816"},
        {"code": "MARK5820", "name": "Events Management and Marketing",  "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5820"},
        {"code": "MARK5821", "name": "Brand Management",                 "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5821"},
        {"code": "MARK5824", "name": "Sales Strategy and Implementation","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5824"},
        {"code": "MARK5825", "name": "Global Marketing Strategy",        "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5825"},
        {"code": "MARK5835", "name": "Artificial Intelligence in Marketing", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5835"},
    ],
    "Human Resource Management": [
        {"code": "MGMT5907", "name": "Human Resource Management",        "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5907"},
        {"code": "MGMT5908", "name": "Strategic Human Resource Management","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5908"},
        {"code": "MGMT5701", "name": "Global Employment Relations",      "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5701"},
        {"code": "MGMT5710", "name": "Managing and Leading People",      "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5710"},
        {"code": "MGMT5720", "name": "Sustainable and Inclusive HR",     "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5720"},
        {"code": "MGMT5904", "name": "Managing Organisational Change",   "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5904"},
        {"code": "MGMT5905", "name": "Managing Myself and Others in an AI-Enabled Workplace", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5905"},
        {"code": "MGMT5906", "name": "Organisations and People in Context","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5906"},
        {"code": "MGMT5930", "name": "Management Analytics",             "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5930"},
        {"code": "MGMT5940", "name": "Career Management Skills",         "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5940"},
        {"code": "MGMT5949", "name": "International Human Resource Management","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5949"},
    ],
    "International Business": [
        {"code": "MGMT5601", "name": "Global Business Environment",       "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5601"},
        {"code": "MGMT5602", "name": "Cross-Cultural Management",         "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5602"},
        {"code": "ACCT5955", "name": "Management Control Systems in Contemporary Contexts", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5955"},
        {"code": "FINS5516", "name": "International Corporate Finance",   "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5516"},
        {"code": "MGMT5603", "name": "Global Business Strategy",          "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5603"},
        {"code": "MGMT5912", "name": "Negotiating in Global Context",     "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5912"},
        {"code": "MGMT6005", "name": "Managing Organisational Risk in Global Context", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT6005"},
    ],
    "Information Systems": [
        {"code": "INFS5604", "name": "Optimising and Transforming Business Processes", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5604"},
        {"code": "INFS5848", "name": "Fundamentals of Information Systems and Technology Project Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5848"},
        {"code": "INFS5888", "name": "Responsible Information Technology Management: AI and Beyond", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5888"},
        {"code": "INFS5731", "name": "Information Systems Strategy and Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5731"},
        {"code": "INFS5831", "name": "Information Systems Consulting",    "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5831"},
        {"code": "INFS5885", "name": "Business in the Digital Age",       "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5885"},
        {"code": "INFS5631", "name": "Managing Digital Innovations and Emerging Technologies", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5631"},
        {"code": "INFS5871", "name": "Supply Chains and Logistics Design","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5871"},
        {"code": "LAWS9812", "name": "Introduction to Law and Policy for Cyber Security", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/LAWS9812"},
    ],
    "Global Sustainability and Social Impact": [
        {"code": "COMM5202", "name": "Social and Environmental Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5202"},
        {"code": "COMM5201", "name": "Business for Social Impact",        "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5201"},
        {"code": "COMM5205", "name": "Leading Change for Sustainability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5205"},
        {"code": "COMM5709", "name": "Corporate Responsibility and Accountability", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5709"},
    ],
    "Risk Management": [
        {"code": "RISK5001", "name": "Fundamentals of Risk and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/RISK5001"},
        {"code": "ACCT5919", "name": "Business Risk Management",          "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5919"},
        {"code": "COMM5615", "name": "Systems Thinking and Business Dynamics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5615"},
        {"code": "FINS5513", "name": "Investments and Portfolio Selection","url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5513"},
        {"code": "FINS5531", "name": "Personal Risk, Insurance, and Superannuation for Financial Advisers", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5531"},
        {"code": "FINS5535", "name": "Derivatives and Risk Management Techniques", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5535"},
        {"code": "INFS5929", "name": "Cybersecurity Leadership and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5929"},
        {"code": "MGMT6005", "name": "Managing Organisational Risk in Global Context", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT6005"},
    ],
    "Strategy and Innovation": [
        {"code": "ECON5103", "name": "Business Economics",                "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "MGMT5803", "name": "Business Innovation",              "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5803"},
        {"code": "COMM5040", "name": "Entrepreneurial Ecosystems",        "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5040"},
        {"code": "COMM5615", "name": "Systems Thinking and Business Dynamics", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5615"},
        {"code": "ECON5111", "name": "Economics of Strategy",             "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5111"},
        {"code": "ECON5321", "name": "Industrial Organisation",            "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5321"},
        {"code": "ECON5323", "name": "Organisational Economics",          "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5323"},
        {"code": "ECON5324", "name": "Behavioural Economics",             "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5324"},
        {"code": "MGMT5603", "name": "Global Business Strategy",          "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5603"},
        {"code": "MGMT5611", "name": "Entrepreneurship and New Venture Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5611"},
        {"code": "MGMT5800", "name": "Technology, Management and Innovation", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5800"},
        {"code": "MGMT5905", "name": "Managing Myself and Others in an AI-Enabled Workplace", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5905"},
    ],
    "AI in Business and Society": [
        {"code": "COMM5007", "name": "Coding for Business",               "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
        {"code": "INFS5704", "name": "Artificial Intelligence Fluency",   "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5704"},
        {"code": "INFS5888", "name": "Responsible Information Technology Management: AI and Beyond", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5888"},
        {"code": "ACTL5110", "name": "Statistical Machine Learning for Risk and Actuarial Applications", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACTL5110"},
        {"code": "INFS5705", "name": "Artificial Intelligence for Business Analytics in Practice", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5705"},
        {"code": "INFS5706", "name": "AI in Action",                      "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5706"},
        {"code": "MARK5836", "name": "Artificial Intelligence for Marketing Insights", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5836"},
        {"code": "MGMT5905", "name": "Managing Myself and Others in an AI-Enabled Workplace", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5905"},
    ],
    "General / Undecided": [
        {"code": "COMM5007", "name": "Coding for Business",               "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
        {"code": "ACCT5930", "name": "Financial Accounting",              "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ACCT5930"},
        {"code": "FINS5512", "name": "Financial Markets and Institutions", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/FINS5512"},
        {"code": "MARK5700", "name": "Elements of Marketing",            "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MARK5700"},
        {"code": "MGMT5907", "name": "Human Resource Management",        "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/MGMT5907"},
        {"code": "ECON5103", "name": "Business Economics",                "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/ECON5103"},
        {"code": "INFS5704", "name": "Artificial Intelligence Fluency",   "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/INFS5704"},
        {"code": "RISK5001", "name": "Fundamentals of Risk and Risk Management", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/RISK5001"},
    ],
}

COMMON_COURSES = [
    {"code": "COMM5000", "name": "Data Literacy",       "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5000"},
    {"code": "COMM5007", "name": "Coding for Business", "url": "https://www.handbook.unsw.edu.au/postgraduate/courses/2026/COMM5007"},
]

ALL_COURSES_DICT = {}
for _sc in COURSES.values():
    for _c in _sc:
        ALL_COURSES_DICT.setdefault(_c["code"], _c)
for _c in COMMON_COURSES:
    ALL_COURSES_DICT.setdefault(_c["code"], _c)
ALL_COURSE_CODES = sorted(ALL_COURSES_DICT.keys())

COURSE_META = {
    "ACCT5930": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": True},
    "ACCT5907": {"prereqs": ["ACCT5930"],    "workload": "~9 hrs/wk",  "has_final": False},
    "ACCT5910": {"prereqs": ["ACCT5930"],    "workload": "~10 hrs/wk", "has_final": False},
    "ACCT5919": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "ACCT5925": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "ACCT5942": {"prereqs": ["ACCT5930"],    "workload": "~10 hrs/wk", "has_final": True},
    "ACCT5943": {"prereqs": ["ACCT5930"],    "workload": "~11 hrs/wk", "has_final": True},
    "ACCT5955": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "ACCT5961": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "ACCT5972": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "ACCT5995": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "ACCT5996": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "FINS5512": {"prereqs": [],              "workload": "~10 hrs/wk", "has_final": True},
    "FINS5513": {"prereqs": ["FINS5512"],    "workload": "~11 hrs/wk", "has_final": True},
    "FINS5514": {"prereqs": [],              "workload": "~10 hrs/wk", "has_final": True},
    "FINS5510": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "FINS5516": {"prereqs": ["FINS5512"],    "workload": "~10 hrs/wk", "has_final": True},
    "FINS5530": {"prereqs": ["FINS5512"],    "workload": "~10 hrs/wk", "has_final": True},
    "FINS5531": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "FINS5535": {"prereqs": ["FINS5513"],    "workload": "~12 hrs/wk", "has_final": True},
    "FINS5556": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "ECON5102": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": True},
    "ECON5103": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": True},
    "ECON5106": {"prereqs": ["ECON5103"],    "workload": "~10 hrs/wk", "has_final": True},
    "ECON5111": {"prereqs": ["ECON5103"],    "workload": "~9 hrs/wk",  "has_final": True},
    "ECON5321": {"prereqs": ["ECON5103"],    "workload": "~10 hrs/wk", "has_final": True},
    "ECON5323": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": True},
    "ECON5324": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": True},
    "MARK5700": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MARK5800": {"prereqs": ["MARK5700"],    "workload": "~9 hrs/wk",  "has_final": False},
    "MARK5810": {"prereqs": ["MARK5700"],    "workload": "~9 hrs/wk",  "has_final": False},
    "MARK5811": {"prereqs": ["MARK5700"],    "workload": "~10 hrs/wk", "has_final": False},
    "MARK5812": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MARK5813": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MARK5814": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MARK5816": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MARK5820": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MARK5821": {"prereqs": ["MARK5700"],    "workload": "~9 hrs/wk",  "has_final": False},
    "MARK5824": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MARK5825": {"prereqs": ["MARK5700"],    "workload": "~9 hrs/wk",  "has_final": False},
    "MARK5835": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MARK5836": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MGMT5601": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5602": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5603": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MGMT5701": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5710": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5720": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5800": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MGMT5803": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MGMT5904": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5905": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5906": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5907": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5908": {"prereqs": ["MGMT5907"],    "workload": "~9 hrs/wk",  "has_final": False},
    "MGMT5912": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "MGMT5930": {"prereqs": [],              "workload": "~10 hrs/wk", "has_final": True},
    "MGMT5940": {"prereqs": [],              "workload": "~7 hrs/wk",  "has_final": False},
    "MGMT5949": {"prereqs": ["MGMT5907"],    "workload": "~9 hrs/wk",  "has_final": False},
    "MGMT5611": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "MGMT6005": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "INFS5604": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "INFS5631": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "INFS5704": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "INFS5705": {"prereqs": ["INFS5704"],    "workload": "~10 hrs/wk", "has_final": False},
    "INFS5706": {"prereqs": ["INFS5704"],    "workload": "~10 hrs/wk", "has_final": False},
    "INFS5731": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "INFS5831": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "INFS5848": {"prereqs": [],              "workload": "~10 hrs/wk", "has_final": False},
    "INFS5871": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "INFS5885": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "INFS5888": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "INFS5929": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "LAWS9812": {"prereqs": [],              "workload": "~10 hrs/wk", "has_final": True},
    "COMM5000": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "COMM5007": {"prereqs": [],              "workload": "~10 hrs/wk", "has_final": False},
    "COMM5040": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "COMM5201": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "COMM5202": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "COMM5204": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "COMM5205": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "COMM5615": {"prereqs": [],              "workload": "~9 hrs/wk",  "has_final": False},
    "COMM5709": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "RISK5001": {"prereqs": [],              "workload": "~8 hrs/wk",  "has_final": False},
    "TABL5551": {"prereqs": [],              "workload": "~10 hrs/wk", "has_final": True},
    "ACTL5110": {"prereqs": [],              "workload": "~12 hrs/wk", "has_final": True},
}

# ════════════════════════════════════════════════════════
# TRANSLATIONS
# ════════════════════════════════════════════════════════

T = {
    "中文": {
        "title":   "🎓 UNSW MCom 智能选课助手",
        "subtitle": "用 AI 帮你规划最适合的课程路径",

        # Section labels
        "sec_goals":   "第一步：告诉我你的目标",
        "sec_profile": "第二步：你的学习档案",
        "sec_result":  "第三步：AI 生成选课建议",

        # Goals
        "goals_options": ["继续读博士 PhD", "科技行业就业", "金融/投行", "咨询 Consulting",
                          "创业", "留澳工作签证", "提高 WAM", "学习 AI/数据"],
        "goals_label":   "选择毕业目标（可多选）",
        "custom_goal_label": "自定义目标",
        "custom_goal_ph":   "例如：转型做产品经理...",
        "weights_caption":  "为每个目标打分（1=不重要，5=最重要）",

        # Profile
        "spec_label":       "专业方向（1-2个）",
        "spec_ph":          "选择专业...",
        "term_label":       "规划学期",
        "wam_label":        "当前 WAM（选填）",
        "wam_ph":           "例如 82",
        "uoc_label":        "剩余学分",
        "completed_label":  "已修课程",
        "completed_ph":     "搜索已修课程（可多选）",
        "custom_completed_ph": "课程代码不在列表里？手动填写，英文逗号分隔，例如：COMM5007, MGMT6001",
        "load_label":       "每学期课程数",
        "load_options":     ["2门", "3门", "4门"],
        "notes_label":      "其他备注（选填）",
        "notes_ph":         "例如：避开周五，想做论文研究项目...",

        # Actions
        "submit_btn":   "✨ 生成选课建议",
        "spinner":      "AI 分析中，请稍候...",
        "retry_toast":  "服务器繁忙，3秒后重试...",

        # Results
        "priority_map": {"must": "🔴 必选", "recommended": "🟢 强烈推荐", "optional": "⚪ 可选"},
        "handbook_btn": "📖 查看 Handbook",
        "prereq_label": "先修要求",
        "workload_label": "课程工作量",
        "final_label":  "期末考试",
        "final_yes":    "有",
        "final_no":     "无",
        "prereq_none":  "无",
        "no_valid_courses": "AI 未能返回有效课程代码，请重试。",
        "conflict_title": "⚠️ 先修条件提醒",
        "conflict_body":  "以下推荐课程有先修要求，请确认是否已完成：",

        # GateFix user-facing messages (friendly, no academic terms)
        "gf_refuse_both":       "🤔 还差两步！请先**选择专业方向**和**至少一个目标**，AI 才能给你精准建议。",
        "gf_refuse_relevance":  "🤔 请先选择专业方向，助手才知道从哪里开始帮你规划！",
        "gf_refuse_coverage":   "🎯 选一个你的毕业目标就能生成啦！哪怕只选一个也行～",
        "gf_clarify_ordering":  "💡 小提示：你填写的剩余学分和已修课程数量有点对不上，建议核对一下。AI 还是会继续生成！",
        "gf_clarify_robustness": "💡 补充 WAM 或备注（比如时间偏好）可以让建议更精准哦，不填也没关系！",

        # Paywall
        "paywall_title": "免费次数已用完",
        "paywall_used":  "",
        "paywall_body":  "Annual Pass 解锁整学年无限次生成 — 🧋 一杯奶茶的价格，A$7.99。",
        "paywall_btn":   "🔓 解锁 Annual Pass — A$7.99/年",
        "paywall_url":   "https://buy.stripe.com/eVq3cw2ej4Iw8dNaLy9oc00",
        "free_remaining": "剩余免费次数：{n}/{total}",
        "pro_badge":      "✅ Annual Pass 用户",

        # AI instructions
        "ai_lang":       "Chinese",
        "summary_field": "一句话总体建议（中文）",
        "reason_field":  "2-3句中文理由，结合目标权重",
        "warning_field": "提醒或空字符串",
        "goals_str_fmt": lambda gw: "、".join([f"{g}（重要度{w}/5）" for g, w in gw.items()]),
        "goals_none":    "未指定",
        "wam_none":      "未提供",
        "notes_none":    "无",

        # Footer
        "footer": "数据来源：UNSW Handbook（公开信息）· 仅供参考，非官方学术建议",
        "feedback_btn": "📝 提交反馈",
        # Micro-feedback
        "fb_prompt":     "这次推荐对你有帮助吗？",
        "fb_sub":        "你的反馈会让下一个同学的结果更准 🙌",
        "fb_bad":        "😕 不太准",
        "fb_ok":         "😊 还不错",
        "fb_great":      "🤩 正是我要的",
        "fb_thanks_bad": "收到！帮我们说说哪里没对上？",
        "fb_thanks_ok":  "谢谢～有什么可以更好的吗？",
        "fb_thanks_great":"太好了！是什么让你觉得准？",
        "fb_comment_ph": "随便说说，不用很正式（可跳过）",
        "fb_submit":     "发送反馈",
        "fb_done":       "✓ 已收到，感谢你的反馈！对我们很有帮助 💪",
    },
    "English": {
        "title":   "🎓 UNSW MCom Smart Course Advisor",
        "subtitle": "AI-powered course planning tailored to your goals",

        "sec_goals":   "Step 1: Tell me your goals",
        "sec_profile": "Step 2: Your academic profile",
        "sec_result":  "Step 3: AI course recommendations",

        "goals_options": ["Continue to PhD", "Tech industry jobs", "Finance / Investment Banking",
                          "Consulting", "Entrepreneurship", "Australian work visa",
                          "Improve WAM", "Learn AI / Data"],
        "goals_label":   "Select graduation goals (multi-select)",
        "custom_goal_label": "Custom goal",
        "custom_goal_ph":   "e.g. transition to product management...",
        "weights_caption":  "Rate each goal (1 = low priority, 5 = top priority)",

        "spec_label":       "Specialization (1-2)",
        "spec_ph":          "Choose specialization...",
        "term_label":       "Planning Term",
        "wam_label":        "Current WAM (optional)",
        "wam_ph":           "e.g. 82",
        "uoc_label":        "Remaining UOC",
        "completed_label":  "Completed Courses",
        "completed_ph":     "Search completed courses (multi-select)",
        "custom_completed_ph": "Course not in list? Type codes separated by commas, e.g. COMM5007, MGMT6001",
        "load_label":       "Courses per term",
        "load_options":     ["2 courses", "3 courses", "4 courses"],
        "notes_label":      "Additional notes (optional)",
        "notes_ph":         "e.g. avoid Fridays, interested in research...",

        "submit_btn":   "✨ Generate Recommendations",
        "spinner":      "AI is analysing your profile, please wait...",
        "retry_toast":  "Server busy, retrying in 3s...",

        "priority_map": {"must": "🔴 Must take", "recommended": "🟢 Recommended", "optional": "⚪ Optional"},
        "handbook_btn": "📖 View Handbook",
        "prereq_label": "Prerequisites",
        "workload_label": "Workload",
        "final_label":  "Final Exam",
        "final_yes":    "Yes",
        "final_no":     "No",
        "prereq_none":  "None",
        "no_valid_courses": "AI did not return valid course codes. Please try again.",
        "conflict_title": "⚠️ Prerequisite Notice",
        "conflict_body":  "Some recommended courses have prerequisites you may not have completed:",

        "gf_refuse_both":       "🤔 Two things missing! Please select a **specialisation** and **at least one goal** so the advisor can help you.",
        "gf_refuse_relevance":  "🤔 Please choose a specialisation first — the advisor needs to know your area of study!",
        "gf_refuse_coverage":   "🎯 Pick at least one graduation goal so the AI can align its suggestions with your plans.",
        "gf_clarify_ordering":  "💡 Heads up: your remaining UOC and completed course count seem inconsistent — worth double-checking. AI will still generate suggestions!",
        "gf_clarify_robustness": "💡 Adding your WAM or notes (e.g. scheduling preferences) helps the AI give more precise advice — but it's optional!",

        "paywall_title": "You've used all 3 free tries",
        "paywall_used":  "",
        "paywall_body":  "Annual Pass = unlimited picks for the whole year — 🧋 one bubble tea, A$7.99.",
        "paywall_btn":   "🔓 Unlock Annual Pass — A$7.99/year",
        "paywall_url":   "https://buy.stripe.com/eVq3cw2ej4Iw8dNaLy9oc00",
        "free_remaining": "Free uses left: {n}/{total}",
        "pro_badge":      "✅ Annual Pass",

        "ai_lang":       "English",
        "summary_field": "one-sentence overall recommendation (English)",
        "reason_field":  "2-3 sentence reason in English, referencing goal weights",
        "warning_field": "warning message or empty string",
        "goals_str_fmt": lambda gw: ", ".join([f"{g} (priority {w}/5)" for g, w in gw.items()]),
        "goals_none":    "Not specified",
        "wam_none":      "Not provided",
        "notes_none":    "None",

        "footer": "Data: UNSW Handbook (public info) · For reference only — not official academic advice.",
        "feedback_btn": "📝 Give Feedback",
        # Micro-feedback
        "fb_prompt":     "Were these recommendations helpful?",
        "fb_sub":        "Your feedback helps the next student get better results 🙌",
        "fb_bad":        "😕 Off-target",
        "fb_ok":         "😊 Pretty good",
        "fb_great":      "🤩 Exactly right",
        "fb_thanks_bad": "Got it — what didn't fit?",
        "fb_thanks_ok":  "Thanks! What could be better?",
        "fb_thanks_great":"Love it! What made it feel right?",
        "fb_comment_ph": "Anything helps — no need to be formal (optional)",
        "fb_submit":     "Send feedback",
        "fb_done":       "✓ Received, thank you! This really helps us improve 💪",
    },
}

# ════════════════════════════════════════════════════════
# SESSION STATE INIT
# ════════════════════════════════════════════════════════

if "gen_count" not in st.session_state:
    st.session_state.gen_count = 0
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

# ── Demo scenario state ───────────────────────────────────
# ── Pixel art: result characters (8 archetypes) ──────────

# No-cap grid (casual / hoodie characters)
_CHAR_GRID_NOCAP = [
    #0  1  2  3  4  5  6  7  8  9
    [0, 0, 0, 5, 5, 5, 5, 0, 0, 0],  # 0 hair top
    [0, 0, 5, 5, 5, 5, 5, 5, 0, 0],  # 1 hair wider
    [0, 0, 5, 5, 5, 5, 5, 5, 0, 0],  # 2 hair fuller
    [0, 0, 0, 5, 5, 5, 5, 0, 0, 0],  # 3 hair base
    [0, 0, 2, 2, 2, 2, 2, 0, 0, 0],  # 4 face top
    [0, 0, 2, 1, 2, 1, 2, 0, 0, 0],  # 5 eyes
    [0, 0, 2, 2, 2, 2, 2, 0, 0, 0],  # 6 face mid
    [0, 0, 2, 0, 1, 1, 2, 0, 0, 0],  # 7 smile
    [0, 0, 0, 2, 2, 2, 0, 0, 0, 0],  # 8 chin
    [0, 0, 3, 3, 6, 3, 3, 0, 0, 0],  # 9 collar
    [0, 3, 3, 3, 3, 3, 3, 3, 0, 0],  # 10 body
    [1, 0, 3, 3, 3, 3, 3, 0, 1, 0],  # 11 arms
    [0, 0, 0, 3, 0, 3, 0, 0, 0, 0],  # 12 legs
    [0, 0, 0, 1, 0, 1, 0, 0, 0, 0],  # 13 shoes
]

# Cap grid (same as advisor — formal students)
_CHAR_GRID_CAP = [
    [0, 0, 1, 4, 4, 4, 1, 0, 0, 0],
    [0, 1, 1, 4, 4, 4, 1, 1, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 5, 5, 5, 5, 0, 0, 0],
    [0, 0, 2, 2, 2, 2, 2, 0, 0, 0],
    [0, 0, 2, 1, 2, 1, 2, 0, 0, 0],
    [0, 0, 2, 2, 2, 2, 2, 0, 0, 0],
    [0, 0, 2, 0, 1, 1, 2, 0, 0, 0],
    [0, 0, 0, 2, 2, 2, 0, 0, 0, 0],
    [0, 0, 3, 3, 6, 3, 3, 0, 0, 0],
    [0, 3, 3, 3, 3, 3, 3, 3, 0, 0],
    [1, 0, 3, 3, 3, 3, 3, 0, 1, 0],
    [0, 0, 0, 3, 0, 3, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 1, 0, 0, 0, 0],
]

# 8 student archetypes: {name_zh, name_en, flavor_zh, flavor_en, colors, cap}
_PIXEL_CHARS = [
    {"name_zh": "🎓 学霸控",  "name_en": "🎓 Academic",
     "flavor_zh": "GPA 是我的命",     "flavor_en": "Lives for the GPA",
     "colors": {1:'#1a1a1a',2:'#FFCC88',3:'#4472C4',4:'#FFD700',5:'#8B6914',6:'#fff',7:'#CC3300'},
     "cap": True},
    {"name_zh": "💼 金融狗",  "name_en": "💼 Finance Bro",
     "flavor_zh": "投行梦想家",        "flavor_en": "IB or bust",
     "colors": {1:'#1a1a1a',2:'#FFCC88',3:'#1a3a5c',4:'#aaaaaa',5:'#e8c840',6:'#fff',7:'#cc2200'},
     "cap": True},
    {"name_zh": "🎨 市场人",  "name_en": "🎨 Marketing",
     "flavor_zh": "创意无极限",        "flavor_en": "Vibes & strategy",
     "colors": {1:'#1a1a1a',2:'#FFCC88',3:'#c44472',4:'#ff88cc',5:'#7722bb',6:'#fff',7:'#ff4488'},
     "cap": False},
    {"name_zh": "📊 会计精",  "name_en": "📊 Accounting",
     "flavor_zh": "数字控制一切",      "flavor_en": "Spreadsheets = love",
     "colors": {1:'#1a1a1a',2:'#FFCC88',3:'#2d6a2d',4:'#44aa44',5:'#1a0a00',6:'#fff',7:'#88cc44'},
     "cap": True},
    {"name_zh": "💻 科技宅",  "name_en": "💻 Tech Nerd",
     "flavor_zh": "代码改变世界",      "flavor_en": "Code is everything",
     "colors": {1:'#1a1a1a',2:'#FFCC88',3:'#3a3a5a',4:'#6666aa',5:'#111111',6:'#8888bb',7:'#4488ff'},
     "cap": False},
    {"name_zh": "☕ 卷王",   "name_en": "☕ Night Owl",
     "flavor_zh": "图书馆最后一盏灯",  "flavor_en": "Last one out of the library",
     "colors": {1:'#1a1a1a',2:'#FFCC88',3:'#2a1a2a',4:'#553355',5:'#bb2200',6:'#887788',7:'#ff6600'},
     "cap": False},
    {"name_zh": "🌏 留子",   "name_en": "🌏 Int'l Student",
     "flavor_zh": "跨越半个地球来卷",  "flavor_en": "Flew halfway round the world",
     "colors": {1:'#1a1a1a',2:'#f0b888',3:'#cc6600',4:'#ff9900',5:'#110500',6:'#fff',7:'#ff3300'},
     "cap": True},
    {"name_zh": "🔬 研究生",  "name_en": "🔬 Researcher",
     "flavor_zh": "PhD 是终点",        "flavor_en": "Eyeing a PhD",
     "colors": {1:'#1a1a1a',2:'#FFCC88',3:'#dde8ee',4:'#aabbcc',5:'#222244',6:'#fff',7:'#4466cc'},
     "cap": False},
]

def _render_result_char(seed: int, cn: bool) -> str:
    import base64, random as _rnd
    char = _rnd.Random(seed).choice(_PIXEL_CHARS)
    grid = _CHAR_GRID_CAP if char["cap"] else _CHAR_GRID_NOCAP
    colors = char["colors"]
    cell = 9
    W, H = 10 * cell, len(grid) * cell
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" shape-rendering="crispEdges">']
    for r, row in enumerate(grid):
        for c, idx in enumerate(row):
            if idx == 0: continue
            parts.append(f'<rect x="{c*cell}" y="{r*cell}" width="{cell}" height="{cell}" fill="{colors[idx]}"/>')
    parts.append('</svg>')
    b64 = base64.b64encode(''.join(parts).encode()).decode()
    name   = char["name_zh"]   if cn else char["name_en"]
    flavor = char["flavor_zh"] if cn else char["flavor_en"]
    label  = "你本次召唤的角色" if cn else "Your character this run"
    return (
        f"<div style='display:inline-flex;align-items:center;gap:14px;"
        f"background:#0a0a18;border:2px solid #1f2937;padding:10px 16px;"
        f"margin:10px 0 14px 0'>"
        f"<img src='data:image/svg+xml;base64,{b64}' width='72' "
        f"style='image-rendering:pixelated;display:block'>"
        f"<div>"
        f"<div style='font-family:\"Press Start 2P\",monospace;font-size:6px;"
        f"color:#4b5563;margin-bottom:5px;letter-spacing:.5px'>{label}</div>"
        f"<div style='font-family:\"Press Start 2P\",monospace;font-size:10px;"
        f"color:#a5b4fc;margin-bottom:4px'>{name}</div>"
        f"<div style='font-family:\"Courier New\",monospace;font-size:11px;"
        f"color:#6b7280'>{flavor}</div>"
        f"</div></div>"
    )

# ── Pixel art advisor character (SVG) ────────────────────
_PIXEL_COLORS = {
    1: '#1a1a1a',   # outline / dark
    2: '#FFCC88',   # skin
    3: '#4472C4',   # blue outfit
    4: '#FFD700',   # gold (cap)
    5: '#8B6914',   # brown hair
    6: '#ffffff',   # white
    7: '#CC3300',   # red accent
}

_PIXEL_GRID = [
    #0  1  2  3  4  5  6  7  8  9
    [0, 0, 1, 4, 4, 4, 1, 0, 0, 0],  # 0  cap crown
    [0, 1, 1, 4, 4, 4, 1, 1, 0, 0],  # 1  cap wider
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0],  # 2  cap brim
    [0, 0, 0, 5, 5, 5, 5, 0, 0, 0],  # 3  hair
    [0, 0, 2, 2, 2, 2, 2, 0, 0, 0],  # 4  face top
    [0, 0, 2, 1, 2, 1, 2, 0, 0, 0],  # 5  eyes
    [0, 0, 2, 2, 2, 2, 2, 0, 0, 0],  # 6  face mid
    [0, 0, 2, 0, 1, 1, 2, 0, 0, 0],  # 7  smile
    [0, 0, 0, 2, 2, 2, 0, 0, 0, 0],  # 8  chin
    [0, 0, 3, 3, 6, 3, 3, 0, 0, 0],  # 9  collar (6=white shirt)
    [0, 3, 3, 3, 3, 3, 3, 3, 0, 0],  # 10 body
    [1, 0, 3, 3, 3, 3, 3, 0, 1, 0],  # 11 arms
    [0, 0, 0, 3, 0, 3, 0, 0, 0, 0],  # 12 legs
    [0, 0, 0, 1, 0, 1, 0, 0, 0, 0],  # 13 shoes
]

def _pixel_advisor_svg(cell: int = 10) -> str:
    W = 10 * cell
    H = len(_PIXEL_GRID) * cell
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'shape-rendering="crispEdges">']
    for r, row in enumerate(_PIXEL_GRID):
        for c, idx in enumerate(row):
            if idx == 0:
                continue
            x, y = c * cell, r * cell
            fill = _PIXEL_COLORS[idx]
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}"/>')
    parts.append('</svg>')
    return ''.join(parts)

def _pixel_advisor_html(size: int = 80) -> str:
    import base64
    svg_bytes = _pixel_advisor_svg(cell=10).encode()
    b64 = base64.b64encode(svg_bytes).decode()
    return (f'<img src="data:image/svg+xml;base64,{b64}" '
            f'width="{size}" style="image-rendering:pixelated;display:block">')

DEMO_SCENARIOS = {
    "A": {
        "label_zh": "😱 啥都没填",
        "label_en": "😱 Blank profile",
        "desc_zh":  "连你想学啥都不知道，我只能乱猜——看看没有信息时AI会推出什么离谱答案",
        "desc_en":  "You told me nothing. Watch me confidently recommend the wrong courses.",
        "verdict_zh": "🚫 我罢工了",
        "verdict_en": "🚫 I quit",
        "goals":       [],
        "specs":       [],
        "wam":         "",
        "credits":     "48 UOC",
        "completed":   [],
        "notes":       "",
    },
    "B": {
        "label_zh": "🤔 填了一半",
        "label_en": "🤔 Half done",
        "desc_zh":  "知道你想进科技行业了，但WAM是多少？修了啥课？我尽力，但别怪我不准",
        "desc_en":  "I know your goal but not much else. I'll try, but don't blame me.",
        "verdict_zh": "⚠️ 勉强能用",
        "verdict_en": "⚠️ Proceed with caution",
        "goals":       ["Tech industry jobs"],
        "specs":       ["Information Systems"],
        "wam":         "",
        "credits":     "48 UOC",
        "completed":   [],
        "notes":       "",
    },
    "C": {
        "label_zh": "🎉 信息给满了",
        "label_en": "🎉 Full profile",
        "desc_zh":  "完美！我知道你是谁、想去哪、还差几个学分——这才是我发挥的时候！",
        "desc_en":  "Now we're talking. I know everything I need. Watch the magic happen.",
        "verdict_zh": "✅ 这才对嘛",
        "verdict_en": "✅ This is the way",
        "goals":       ["Tech industry jobs", "Continue to PhD"],
        "specs":       ["Information Systems"],
        "wam":         "78",
        "credits":     "48 UOC",
        "completed":   ["COMM5007"],
        "notes":       "Interested in AI and data analytics, prefer courses with coding components",
    },
}

def _load_demo(scenario_key: str):
    s = DEMO_SCENARIOS[scenario_key]
    st.session_state["demo_goals"]     = s["goals"]
    st.session_state["demo_specs"]     = s["specs"]
    st.session_state["demo_wam"]       = s["wam"]
    st.session_state["demo_credits"]   = ["96 UOC", "72 UOC", "48 UOC", "36 UOC", "24 UOC", "12 UOC"].index(s["credits"])
    st.session_state["demo_completed"] = s["completed"]
    st.session_state["demo_notes"]     = s["notes"]
    st.session_state["active_demo"]    = scenario_key

# ════════════════════════════════════════════════════════
# HEADER + LANGUAGE TOGGLE
# ════════════════════════════════════════════════════════

lang = st.radio("", ["中文", "English"], horizontal=True, label_visibility="collapsed")
t = T[lang]

st.title(t["title"])
st.caption(t["subtitle"])

# ── Sidebar: usage counter + Pro teaser ──────────────────
with st.sidebar:
    st.markdown("### 使用情况 / Usage" if lang == "中文" else "### Usage")
    if st.session_state.is_pro:
        st.success(t["pro_badge"])
    else:
        remaining = max(0, FREE_LIMIT - st.session_state.gen_count)
        st.info(t["free_remaining"].format(n=remaining, total=FREE_LIMIT))
        st.progress(st.session_state.gen_count / FREE_LIMIT)
        st.markdown(
            "<div style='"
            "border:2px solid #92400e;"
            "background:linear-gradient(135deg,#0d0a00,#1a1200);"
            "padding:10px 12px;"
            "margin:8px 0 6px 0;"
            "box-shadow:3px 3px 0 #451a03;"
            "'>"
            "<div style='font-family:\"Press Start 2P\",monospace;font-size:7px;"
            "color:#f59e0b;margin-bottom:6px;letter-spacing:.5px'>✦ ANNUAL PASS</div>"
            "<div style='font-family:\"Courier New\",monospace;font-size:11px;"
            "color:#e5e7eb;line-height:1.8'>"
            + ("无限次生成 · 整学年有效" if lang == "中文" else "Unlimited · Valid all year") +
            "</div>"
            "<div style='font-family:\"Courier New\",monospace;font-size:10px;"
            "color:#d97706;margin-top:4px'>"
            + ("🧋 一杯奶茶的价格 — A$7.99" if lang == "中文" else "🧋 One bubble tea — A$7.99") +
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.link_button(
            "🔓 " + ("立即解锁" if lang == "中文" else "Unlock now") + " →",
            t["paywall_url"],
            use_container_width=True,
        )

# ════════════════════════════════════════════════════════
# STEP INDICATOR
# ════════════════════════════════════════════════════════

def step_bar(active: int):
    labels = [t["sec_goals"], t["sec_profile"], t["sec_result"]]
    cols = st.columns(3)
    for i, (col, label) in enumerate(zip(cols, labels)):
        with col:
            color  = "#FF4B4B" if i == active else ("#22c55e" if i < active else "#ccc")
            weight = "bold" if i == active else "normal"
            prefix = "✅ " if i < active else ""
            st.markdown(
                f"<div style='text-align:center;font-weight:{weight};color:{color};font-size:13px'>"
                f"{prefix}{label}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<hr style='margin:8px 0 20px 0'>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# DEMO MODE BANNER
# ════════════════════════════════════════════════════════

# Init demo state defaults
for _k, _v in [("demo_goals",[]), ("demo_specs",[]), ("demo_wam",""),
               ("demo_credits",2), ("demo_completed",[]), ("demo_notes",""),
               ("active_demo", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Session tracking for Memory Layer research ────────────────────
import uuid as _uuid
if "session_id" not in st.session_state:
    st.session_state["session_id"]    = str(_uuid.uuid4())[:8]
if "submit_count" not in st.session_state:
    st.session_state["submit_count"]  = 0
# Accumulate OK dimensions across submissions in this session
# Structure: {"relevance": True/False, "coverage": ..., "ordering": ..., "robustness": ...}
if "session_ok_dims" not in st.session_state:
    st.session_state["session_ok_dims"] = {
        "relevance": False, "coverage": False,
        "ordering": False,  "robustness": False,
    }

cn = (lang == "中文")

def _render_advisor_panel(goals, specs, wam, notes, lang):
    """Dynamic RPG-style advisor dialog reacting to current form state."""
    cn = (lang == "中文")
    goals_ok  = bool(goals)
    specs_ok  = bool(specs)
    wam_ok    = bool(wam and wam.strip())
    notes_ok  = bool(notes and notes.strip())

    completeness = sum([goals_ok, specs_ok, wam_ok, notes_ok])

    # ── Advisor state based on what's filled ──────────────
    if not goals_ok and not specs_ok:
        face_eyes = "◉  ◉"
        face_mouth = "  ___  "
        border = "#374151"
        bar_color = "#ef4444"
        bar_pct   = 5
        if cn:
            dialog_lines = [
                "哦？新同学来了。",
                "想让我帮你选课？",
                "先告诉我你想往哪个方向卷～",
            ]
            hint = "↓ 先选一个毕业目标"
        else:
            dialog_lines = ["New student, huh?","Tell me what you're chasing —","grades, jobs, or vibes?"]
            hint = "↓ Start by picking a goal"
    elif goals_ok and not specs_ok:
        face_eyes = "^  ^"
        face_mouth = "  ▽  "
        border = "#f59e0b"
        bar_color = "#f59e0b"
        bar_pct   = 35
        if cn:
            dialog_lines = [
                "目标收到，有想法！",
                "你具体在哪个方向？",
                "Finance 和 Marketing 差很多的。",
            ]
            hint = "↓ 选择你的专业方向"
        else:
            dialog_lines = ["Nice goals!","Which specialisation are you in?","Finance ≠ Marketing, big difference."]
            hint = "↓ Pick your specialisation above"
    elif goals_ok and specs_ok and not wam_ok:
        face_eyes = "◕  ◕"
        face_mouth = "  ∪  "
        border = "#818cf8"
        bar_color = "#818cf8"
        bar_pct   = 65
        if cn:
            dialog_lines = [
                "来了来了，越来越清晰了！",
                "WAM 多少？不用不好意思，",
                "我帮你选最值得冲的课。",
            ]
            hint = "↓ 填写 WAM（可选但有用）"
        else:
            dialog_lines = ["Getting clearer!","What's your WAM? No judgment —","I'll find the right difficulty for you."]
            hint = "↓ Enter WAM above (optional but useful)"
    else:
        face_eyes = "★  ★"
        face_mouth = "  ◡  "
        border = "#22c55e"
        bar_color = "#22c55e"
        bar_pct   = 100
        if cn:
            dialog_lines = [
                "信息齐了，可以出手了！",
                "点下面那个按钮，",
                "我给你整一套最合适的课表。",
            ]
            hint = "↓ 生成选课建议！"
        else:
            dialog_lines = ["All set, let's go!","Hit the button below —","I'll build your course lineup."]
            hint = "↓ Generate recommendations!"

    # ── Build pixel face (inline SVG, same art, different expression) ──
    face_svg = _pixel_advisor_html(size=72)

    # ── Status bar (4 tiles) ──
    dims = (
        [("目标","goals_ok"), ("方向","specs_ok"), ("WAM","wam_ok"), ("备注","notes_ok")]
        if cn else
        [("Goals","goals_ok"), ("Track","specs_ok"), ("WAM","wam_ok"), ("Notes","notes_ok")]
    )
    dim_vals = [goals_ok, specs_ok, wam_ok, notes_ok]
    tiles_html = ""
    for (label, _), filled in zip(dims, dim_vals):
        bg  = "#22c55e" if filled else "#1f2937"
        col = "#fff"    if filled else "#4b5563"
        icon = "■" if filled else "□"
        tiles_html += (
            f"<div style='display:inline-block;text-align:center;margin:0 4px;"
            f"background:{bg};border:2px solid {'#16a34a' if filled else '#374151'};"
            f"padding:3px 7px;font-family:\"Courier New\",monospace;font-size:10px;color:{col}'>"
            f"{icon} {label}</div>"
        )

    # ── Dialog text ──
    dialog_html = "".join(
        f"<div style='margin-bottom:6px'>{line}</div>" for line in dialog_lines
    )

    # ── Full panel HTML ──
    html = f"""
<div style="
  display:flex; gap:16px; align-items:flex-start;
  background:#0d0d1f;
  border:3px solid {border};
  box-shadow: 4px 4px 0 {border};
  padding:16px 18px; margin:16px 0;
">
  <div style="flex-shrink:0;text-align:center">
    <div style="animation:float-up 2s ease-in-out infinite">{face_svg}</div>
    <div style="font-family:'Press Start 2P',monospace;font-size:7px;
                color:{border};margin-top:6px;letter-spacing:1px">ADVISOR</div>
  </div>
  <div style="flex:1">
    <div style="
      font-family:'Press Start 2P',monospace;
      font-size:9px; color:#e2e8f0;
      line-height:2; margin-bottom:10px;
      border-bottom:1px solid #1f2937; padding-bottom:10px;
    ">
      {dialog_html}
      <span style="color:{border};animation:blink-cursor 1s infinite;
                   display:inline-block">▶</span>
    </div>
    <div style="margin-bottom:10px">{tiles_html}</div>
    <div style="margin-bottom:8px">
      <div style="font-family:'Courier New',monospace;font-size:10px;
                  color:#6b7280;margin-bottom:4px">
        {'信息完整度' if cn else 'Profile Power'} {bar_pct}%
      </div>
      <div style="height:10px;background:#1f2937;border:2px solid #374151;position:relative">
        <div style="height:100%;width:{bar_pct}%;background:{bar_color};
                    transition:width .5s"></div>
      </div>
    </div>
    <div style="font-family:'Press Start 2P',monospace;font-size:8px;
                color:{border};letter-spacing:.5px">{hint}</div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# STEP 1 — GOALS (Coverage dimension: CRITICAL)
# ════════════════════════════════════════════════════════

st.subheader(t["sec_goals"])

selected_goals = st.multiselect(t["goals_label"], t["goals_options"],
                               default=st.session_state["demo_goals"])
custom_goal    = st.text_input(t["custom_goal_label"], placeholder=t["custom_goal_ph"])

all_goals = selected_goals + ([custom_goal.strip()] if custom_goal.strip() else [])
goal_weights: dict = {}

if all_goals:
    st.caption(t["weights_caption"])
    for g in all_goals:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(
                f"<div style='padding:5px 0;font-size:14px'>{g}</div>",
                unsafe_allow_html=True,
            )
        with c2:
            goal_weights[g] = st.selectbox(
                g, [1, 2, 3, 4, 5], index=2,
                key=f"w_{g}", label_visibility="collapsed",
            )

    # ── Pixel bar chart (replaces Plotly pie) ──
    _PIXEL_PALETTE = [
        "#818cf8","#34d399","#f59e0b","#f87171",
        "#a78bfa","#38bdf8","#fb923c","#4ade80",
    ]
    total_w = sum(goal_weights.values()) or 1
    rows_html = ""
    for i, (name, w) in enumerate(goal_weights.items()):
        pct   = round(w / total_w * 100)
        color = _PIXEL_PALETTE[i % len(_PIXEL_PALETTE)]
        label = name if len(name) <= 22 else name[:20] + "…"
        rows_html += f"""
<div style="margin:6px 0">
  <div style="font-family:'Courier New',monospace;font-size:11px;
              color:#cbd5e1;margin-bottom:3px;letter-spacing:.3px">
    <span style="color:{color};margin-right:6px">■</span>{label}
    <span style="float:right;color:{color};font-weight:700">{pct}%</span>
  </div>
  <div style="height:14px;background:#1f2937;border:2px solid #374151;
              image-rendering:pixelated;position:relative">
    <div style="height:100%;width:{pct}%;background:{color};
                image-rendering:pixelated;transition:width .4s"></div>
  </div>
</div>"""
    st.markdown(
        f"""<div style="background:#0d0d1f;border:3px solid #1f2937;
                        box-shadow:4px 4px 0 #1e1b4b;padding:14px 16px;
                        margin:8px 0;font-family:'Press Start 2P',monospace">
  <div style="font-size:7px;color:#4b5563;letter-spacing:1px;
              margin-bottom:10px">GOAL WEIGHTS</div>
  {rows_html}
</div>""",
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════
# STEP 2 — PROFILE (Relevance + Ordering + Robustness)
# ════════════════════════════════════════════════════════

st.divider()
st.subheader(t["sec_profile"])

c1, c2 = st.columns(2)
with c1:
    specs = st.multiselect(t["spec_label"], list(COURSES.keys()),
                           default=st.session_state["demo_specs"],
                           max_selections=2, placeholder=t["spec_ph"])
with c2:
    term  = st.selectbox(t["term_label"],
                         ["Term 2 2026", "Term 3 2026", "Term 1 2027", "Term 2 2027"])

c3, c4 = st.columns(2)
with c3:
    wam     = st.text_input(t["wam_label"], placeholder=t["wam_ph"],
                           value=st.session_state["demo_wam"])
with c4:
    credits = st.selectbox(t["uoc_label"],
                           ["96 UOC", "72 UOC", "48 UOC", "36 UOC", "24 UOC", "12 UOC"],
                           index=st.session_state["demo_credits"])

completed_courses = st.multiselect(
    t["completed_label"],
    options=ALL_COURSE_CODES,
    default=st.session_state["demo_completed"],
    format_func=lambda code: f"{code} · {ALL_COURSES_DICT[code]['name']}",
    placeholder=t["completed_ph"],
    max_selections=50,
)
custom_completed_raw = st.text_input(
    label="　",
    placeholder=t["custom_completed_ph"],
    label_visibility="collapsed",
)
# Merge: dropdown selections + manual codes (uppercased, stripped)
_custom_codes = [c.strip().upper() for c in custom_completed_raw.split(",") if c.strip()]
completed_courses = list(dict.fromkeys(completed_courses + _custom_codes))

c5, c6 = st.columns([1, 2])
with c5:
    load = st.radio(t["load_label"], t["load_options"], index=1)
with c6:
    notes = st.text_input(t["notes_label"], placeholder=t["notes_ph"],
                         value=st.session_state["demo_notes"])

# ════════════════════════════════════════════════════════
# SIDEBAR QUEST LOG — live info completeness tracker
# ════════════════════════════════════════════════════════

def _pixel_bar(pct: int, color: str, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    blocks = "█" * filled + "░" * (width - filled)
    return f"<span style='color:{color};font-family:\"Courier New\",monospace;font-size:11px;letter-spacing:1px'>{blocks}</span>"

_goals_ok     = bool(all_goals)
_specs_ok     = bool(specs)
_wam_ok       = bool(wam.strip())
_notes_ok     = bool(notes.strip())
_completed_ok = bool(completed_courses)

_quest_items = [
    ("毕业目标" if cn else "Goals",       _goals_ok,     "#818cf8", 35),
    ("专业方向" if cn else "Specialise",  _specs_ok,     "#34d399", 25),
    ("当前WAM"  if cn else "WAM",         _wam_ok,       "#f59e0b", 20),
    ("已修课程" if cn else "Completed",   _completed_ok, "#38bdf8", 10),
    ("补充说明" if cn else "Extra notes", _notes_ok,     "#f87171", 10),
]
_total_weight = sum(w for *_, w in _quest_items)
_earned       = sum(w for *_, filled, _, w in _quest_items if filled)
_power_pct    = round(_earned / _total_weight * 100)
_power_color  = "#ef4444" if _power_pct < 40 else ("#f59e0b" if _power_pct < 70 else "#22c55e")

_rows = ""
for label, filled, color, _ in _quest_items:
    icon  = "▶" if filled else "▷"
    state = ("<span style='color:#22c55e'>DONE</span>" if filled
             else "<span style='color:#4b5563'>----</span>")
    bar   = _pixel_bar(100 if filled else 0, color if filled else "#1f2937")
    _rows += f"""
<div style="margin:8px 0">
  <div style="display:flex;justify-content:space-between;
              font-family:'Press Start 2P',monospace;font-size:7px;
              color:{'#e2e8f0' if filled else '#6b7280'};margin-bottom:3px">
    <span style="color:{color if filled else '#4b5563'}">{icon}</span>
    <span style="flex:1;margin-left:6px">{label}</span>
    {state}
  </div>
  {bar}
</div>"""

with st.sidebar:
    st.markdown(
        f"""<div style="background:#0a0a18;border:3px solid #1f2937;
                        box-shadow:3px 3px 0 #0d0d1f;padding:12px 14px;
                        margin-top:12px">
  <div style="font-family:'Press Start 2P',monospace;font-size:7px;
              color:#4f46e5;letter-spacing:1px;margin-bottom:4px">QUEST LOG</div>
  <div style="font-family:'Courier New',monospace;font-size:9px;
              color:#374151;margin-bottom:10px;border-bottom:1px solid #1f2937;
              padding-bottom:6px">{'越完整答案越精准' if cn else 'more info = better answer'}</div>
  {_rows}
  <div style="margin-top:12px;border-top:1px solid #1f2937;padding-top:10px">
    <div style="font-family:'Press Start 2P',monospace;font-size:7px;
                color:{_power_color};margin-bottom:5px">
      INFO PWR &nbsp; {_power_pct}%
    </div>
    <div style="height:10px;background:#1f2937;border:2px solid #374151">
      <div style="height:100%;width:{_power_pct}%;background:{_power_color};
                  image-rendering:pixelated"></div>
    </div>
    <div style="font-family:'Courier New',monospace;font-size:9px;
                color:#4b5563;margin-top:5px">
      {'★★★☆☆' if _power_pct < 40 else ('★★★★☆' if _power_pct < 80 else '★★★★★')}
      &nbsp;{'补充更多提升精度' if cn else 'fill more to improve'}
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════
# GATEFIX EXPERIMENT PANEL HELPER
# ════════════════════════════════════════════════════════

def _render_experiment_panel(gate, eligible_map, result_ungated, result_governed, t, lang):
    """
    Side-by-side GateFix diagnostic panel.
    result_ungated : JSON dict from AI called without governance (may be None)
    result_governed: JSON dict from governed AI call (None when decision=REFUSE)
    """
    cn = (lang == "中文")

    dec_color = {"PASS": "#22c55e", "CLARIFY": "#f59e0b", "REFUSE": "#ef4444"}[gate.decision]
    dec_label = {"PASS": "通过", "CLARIFY": "待确认", "REFUSE": "已拒绝"} if cn else \
                {"PASS": "PASS", "CLARIFY": "CLARIFY", "REFUSE": "REFUSED"}

    # ── Build "what's missing" message ───────────────────────
    dim_map = [
        ("relevance",  "专业方向" if cn else "specialisation",  True),
        ("coverage",   "毕业目标" if cn else "goals",           True),
        ("ordering",   "学分信息" if cn else "credit info",     False),
        ("robustness", "补充说明" if cn else "extra notes",     False),
    ]
    missing_critical = [lbl for dim, lbl, crit in dim_map
                        if crit and getattr(gate.cq, dim) != "OK"]
    missing_optional = [lbl for dim, lbl, crit in dim_map
                        if not crit and getattr(gate.cq, dim) != "OK"]

    if gate.decision == "REFUSE":
        banner_icon = "❌"
        banner_color = "#ef4444"
        banner_bg    = "#1a0505"
        banner_border = "#7f1d1d"
        if cn:
            banner_msg = f"缺少必填项：{'、'.join(missing_critical)}　→　请补充后重新提交"
        else:
            banner_msg = f"Missing required: {', '.join(missing_critical)} — please fill in and resubmit"
    elif gate.decision == "CLARIFY":
        banner_icon = "⚠️"
        banner_color = "#f59e0b"
        banner_bg    = "#1a1200"
        banner_border = "#78350f"
        parts = []
        if missing_optional:
            parts.append(("补充" if cn else "add") + "：" + ("、".join(missing_optional) if cn else ", ".join(missing_optional)))
        if cn:
            banner_msg = "已生成推荐，但" + "；".join(parts) + "能让结果更精准" if parts else "推荐已生成，结果供参考"
        else:
            banner_msg = ("Results generated, but " + "; ".join(parts) + " would improve accuracy") if parts else "Results generated for reference"
    else:
        banner_icon = "✅"
        banner_color = "#22c55e"
        banner_bg    = "#021a0a"
        banner_border = "#14532d"
        banner_msg = "信息完整，推荐结果已全面优化" if cn else "All info provided — recommendations fully optimised"

    # ── Chip row: one tag per dimension ──────────────────────
    chips_html = ""
    for dim, lbl, crit in dim_map:
        ok = getattr(gate.cq, dim) == "OK"
        chip_bg  = "#14532d" if ok else ("#7f1d1d" if crit else "#1c1917")
        chip_col = "#4ade80" if ok else ("#fca5a5" if crit else "#78716c")
        chip_icon = "■" if ok else ("✕" if crit else "△")
        chips_html += (
            f"<span style='display:inline-block;font-family:\"Courier New\",monospace;"
            f"font-size:11px;background:{chip_bg};color:{chip_col};"
            f"border:1px solid {chip_col}33;padding:2px 8px;margin:0 4px 4px 0'>"
            f"{chip_icon} {lbl}</span>"
        )

    st.divider()
    st.markdown(
        f"""<div style="background:{banner_bg};border:3px solid {banner_border};
                        box-shadow:4px 4px 0 #0d0d1f;padding:14px 18px;margin:12px 0">
  <div style="font-family:'Press Start 2P',monospace;font-size:9px;
              color:{banner_color};margin-bottom:8px;letter-spacing:.5px">
    {banner_icon} {banner_msg}
  </div>
  <div>{chips_html}</div>
</div>""",
        unsafe_allow_html=True,
    )

    # Banner only — columns are handled by the caller


# ════════════════════════════════════════════════════════
# ADVISOR PANEL — live feedback on form completeness
# ════════════════════════════════════════════════════════

_render_advisor_panel(all_goals, specs, wam, notes, lang)

# ════════════════════════════════════════════════════════
# STEP 3 — SUBMIT + GATEFIX + AI GENERATION
# ════════════════════════════════════════════════════════

st.divider()
st.subheader(t["sec_result"])

submitted = st.button(t["submit_btn"], use_container_width=True, type="primary")

if submitted:
    # ── Run GateFix 4D-CQ governance check ───────────────
    gate = gf_engine.evaluate(
        specs=specs,
        goals=all_goals,
        credits=credits,
        completed=completed_courses,
        wam=wam,
        notes=notes,
    )

    # ── Memory Layer: compute counterfactual gate decision ────────────────────
    # "If previously OK dims were inherited from session memory, what would the
    #  gate decide?" — lets us measure CLARIFY→PASS lift in admin analytics.
    _prev_ok = st.session_state["session_ok_dims"]
    _cf_cq_r  = "OK" if (gate.cq.relevance  == "OK" or _prev_ok["relevance"])  else "DEFECT"
    _cf_cq_c  = "OK" if (gate.cq.coverage   == "OK" or _prev_ok["coverage"])   else "DEFECT"
    _cf_cq_o  = "OK" if (gate.cq.ordering   == "OK" or _prev_ok["ordering"])   else "DEFECT"
    _cf_cq_ro = "OK" if (gate.cq.robustness == "OK" or _prev_ok["robustness"]) else "DEFECT"
    if _cf_cq_r == "DEFECT" or _cf_cq_c == "DEFECT":
        _cf_decision = "REFUSE"
    elif _cf_cq_o == "DEFECT" or _cf_cq_ro == "DEFECT":
        _cf_decision = "CLARIFY"
    else:
        _cf_decision = "PASS"

    profile_meta = {
        "n_specs":      len(specs),
        "n_goals":      len(all_goals),
        "n_completed":  len(completed_courses),
        "credits_left": credits,
        "has_wam":      bool(wam.strip()),
        "has_notes":    bool(notes.strip()),
        "load":         load,
        "lang":         lang,
        # Memory Layer fields
        "session_id":              st.session_state["session_id"],
        "submit_count":            st.session_state["submit_count"],
        "counterfactual_decision": _cf_decision,
    }

    # ── Build eligible course pool (needed for all paths incl. REFUSE) ──
    spec_pool = []
    for s in specs:
        spec_pool.extend(COURSES.get(s, []))
    # REFUSE case may have no specs — sample common + a few from each spec for experiment
    if not spec_pool:
        for v in COURSES.values():
            spec_pool.extend(v[:2])
    all_pool  = COMMON_COURSES + spec_pool
    seen, deduped = set(), []
    for c in all_pool:
        if c["code"] not in seen:
            seen.add(c["code"])
            deduped.append(c)

    completed_codes = set(completed_courses)
    eligible     = [c for c in deduped if c["code"] not in completed_codes]
    eligible_map = {c["code"]: c for c in eligible}
    eligible_str = "\n".join(f"- {c['code']}: {c['name']}" for c in eligible)

    load_num      = load[0]
    spec_label    = " & ".join(specs) if specs else (
        "（未选择专业）" if lang == "中文" else "(no specialisation selected)"
    )
    response_lang = t["ai_lang"]
    goals_str     = t["goals_str_fmt"](goal_weights) if goal_weights else t["goals_none"]
    wam_str       = wam.strip() if wam.strip() else t["wam_none"]

    prompt = f"""You are a UNSW MCom academic advisor. Respond in {response_lang}.

Student profile:
- Specialization: {spec_label}
- Planning for: {term}
- Current WAM: {wam_str}
- Remaining UOC: {credits}
- Completed courses: {", ".join(completed_codes) if completed_codes else "None"}
- Career goals (with priority weights): {goals_str}
- Courses per term: {load_num}
- Notes: {notes.strip() if notes.strip() else t["notes_none"]}

AVAILABLE COURSES — select ONLY from the codes below. Do NOT invent codes.
{eligible_str}

Select exactly {load_num} course codes that best match the student's goals and specialization.

CRITICAL: Every "code" value must exactly match a code listed above.

Respond ONLY with valid JSON (no markdown):
{{"summary":"{t['summary_field']}","selections":[{{"code":"XXXX0000","priority":"must|recommended|optional","reason":"{t['reason_field']}"}}],"warning":"{t['warning_field']}"}}"""

    # ── Create API client once (reused across all calls) ──
    try:
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    except Exception as _e:
        st.error(f"API key error: {_e}")
        st.stop()

    # ── Memory Layer: update session OK dims (regardless of decision) ────────
    def _update_session_memory(g):
        ok = st.session_state["session_ok_dims"]
        if g.cq.relevance  == "OK": ok["relevance"]  = True
        if g.cq.coverage   == "OK": ok["coverage"]   = True
        if g.cq.ordering   == "OK": ok["ordering"]   = True
        if g.cq.robustness == "OK": ok["robustness"] = True
        st.session_state["session_ok_dims"] = ok
        st.session_state["submit_count"] = st.session_state["submit_count"] + 1

    # ── REFUSE: block, tell user exactly what to fill in ─────
    if gate.decision == "REFUSE":
        gf_engine.log_submission(gate, profile_meta, ai_generated=False)
        _update_session_memory(gate)
        _render_experiment_panel(gate, eligible_map, None, None, t, lang)
        st.stop()

    # ── CLARIFY: proceed silently (hint shown in result panel) ─
    # (no st.info — the banner inside _render_experiment_panel handles it)

    # ── Paywall check (AFTER governance, BEFORE AI call) ──
    if not st.session_state.is_pro and st.session_state.gen_count >= FREE_LIMIT:
        gf_engine.log_submission(gate, profile_meta, ai_generated=False)
        _update_session_memory(gate)
        st.markdown(
            "<div style='border:3px solid #f59e0b;background:linear-gradient(135deg,#0d0a00,#1c1000);"
            "padding:16px 20px;box-shadow:5px 5px 0 #451a03;margin:12px 0'>"
            "<div style='font-family:\"Press Start 2P\",monospace;font-size:9px;"
            f"color:#f59e0b;margin-bottom:8px'>🔓 {t['paywall_title']}</div>"
            f"<div style='font-family:\"Courier New\",monospace;font-size:12px;"
            f"color:#d97706;line-height:1.7'>{t['paywall_body']}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.link_button(t["paywall_btn"], t["paywall_url"], use_container_width=True)
        st.stop()

    # ── Main governed AI call ─────────────────────────────
    with st.spinner(t["spinner"]):
        try:
            for attempt in range(3):
                try:
                    message = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    break
                except Exception as e:
                    if "529" in str(e) and attempt < 2:
                        st.toast(t["retry_toast"])
                        time.sleep(3)
                    else:
                        raise e

            raw    = message.content[0].text.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            # ── Increment usage counter ───────────────────
            st.session_state.gen_count += 1
            # Note: log_submission is called below — after overlap_rate is known for PASS,
            # or immediately here for CLARIFY (no ungated call, so no overlap to compute).

            # ── Render results based on gate decision ─────
            if result.get("warning"):
                st.warning(result["warning"])

            # Prerequisite conflicts (full-width)
            conflict_lines = []
            for s in result.get("selections", []):
                code = s.get("code", "")
                meta = COURSE_META.get(code, {})
                unmet = [p for p in meta.get("prereqs", []) if p not in completed_codes]
                if unmet:
                    name = eligible_map.get(code, {}).get("name", code)
                    conflict_lines.append(f"**{code} {name}** — {t['prereq_label']}: {', '.join(unmet)}")
            if conflict_lines:
                st.warning(t["conflict_title"] + "\n\n" + t["conflict_body"] + "\n\n" + "\n\n".join(f"- {l}" for l in conflict_lines))

            # ── Helper: render full course cards ──────────
            def _render_cards(res, eligible_map, completed_codes, t, cn, dec_color_r):
                priority_map = t["priority_map"]
                valid_shown  = 0
                if res.get("summary"):
                    st.markdown(
                        f"<div style='font-family:\"Courier New\",monospace;font-size:11px;"
                        f"color:{dec_color_r};padding:6px 10px;background:#0d0d1f;"
                        f"border-left:3px solid {dec_color_r};margin-bottom:12px'>"
                        f"{res['summary']}</div>",
                        unsafe_allow_html=True,
                    )
                for s in res.get("selections", []):
                    code   = s.get("code", "")
                    course = eligible_map.get(code)
                    if not course:
                        continue
                    valid_shown += 1
                    label    = priority_map.get(s.get("priority", "optional"), priority_map["optional"])
                    meta     = COURSE_META.get(code, {})
                    prereqs  = ", ".join(meta["prereqs"]) if meta.get("prereqs") else t["prereq_none"]
                    workload = meta.get("workload", "—")
                    has_exam = (t["final_yes"] if meta.get("has_final")
                                else t["final_no"] if "has_final" in meta else "—")
                    with st.container(border=True):
                        ca, cb = st.columns([4, 1])
                        with ca:
                            st.markdown(f"**{label}**")
                            st.markdown(f"#### {course['code']} · {course['name']}")
                            st.write(s.get("reason", ""))
                            st.markdown(
                                f"<small>🔗 **{t['prereq_label']}:** {prereqs} &nbsp;|&nbsp; "
                                f"⏱ **{t['workload_label']}:** {workload} &nbsp;|&nbsp; "
                                f"📝 **{t['final_label']}:** {has_exam}</small>",
                                unsafe_allow_html=True,
                            )
                        with cb:
                            st.link_button(t["handbook_btn"], course["url"], use_container_width=True)
                if valid_shown == 0:
                    st.error(t["no_valid_courses"])

            dec_color_r = {"PASS": "#22c55e", "CLARIFY": "#f59e0b"}[gate.decision]

            # ── Build context strings for both columns ────
            _missing_zh, _missing_en = [], []
            if gate.cq.ordering  == "DEFECT": _missing_zh.append("学分信息");  _missing_en.append("credit info")
            if gate.cq.robustness== "DEFECT": _missing_zh.append("补充说明");  _missing_en.append("extra notes")
            _used_zh, _used_en = [], []
            if gate.cq.relevance == "OK" and specs:
                _used_zh.append("专业：" + " & ".join(specs))
                _used_en.append("spec: " + " & ".join(specs))
            if gate.cq.coverage  == "OK" and all_goals:
                _g = "、".join(all_goals[:2]) + ("…" if len(all_goals)>2 else "")
                _used_zh.append(f"目标：{_g}")
                _used_en.append("goals: " + ", ".join(all_goals[:2]) + ("…" if len(all_goals)>2 else ""))
            if gate.cq.robustness== "OK" and notes.strip():
                _used_zh.append("备注已纳入"); _used_en.append("notes included")
            why_bad  = ("没拿到「"+"」「".join(_missing_zh)+"」，AI 只能瞎猜" if _missing_zh else "无目标/专业信息") if cn \
                       else ("No "+" / ".join(_missing_en)+" — AI is just guessing" if _missing_en else "No profile info")
            why_good = ("基于 "+"，".join(_used_zh)+" 生成" if _used_zh else "已综合你的信息生成") if cn \
                       else ("Built from: "+"; ".join(_used_en) if _used_en else "Generated from your full profile")

            # ── Random student character ──────────────────
            _char_seed = abs(hash(st.session_state["session_id"] + str(st.session_state.gen_count)))
            st.markdown(
                _render_result_char(seed=_char_seed, cn=cn),
                unsafe_allow_html=True,
            )

            # ── GateFix banner (full-width, always) ──────
            _render_experiment_panel(gate, eligible_map, None, result, t, lang)

            if gate.decision == "CLARIFY":
                # Log here — no ungated call, no overlap_rate
                gf_engine.log_submission(gate, profile_meta, ai_generated=True)
                _update_session_memory(gate)
                # Single column — best result with current info, no comparison
                st.markdown(
                    f"<div style='font-family:\"Courier New\",monospace;font-size:11px;"
                    f"color:{dec_color_r};padding:6px 10px;background:#0d0d1f;"
                    f"border-left:3px solid {dec_color_r};margin-bottom:4px'>"
                    f"↑ {why_good}</div>",
                    unsafe_allow_html=True,
                )
                _render_cards(result, eligible_map, completed_codes, t, cn, dec_color_r)

            else:  # PASS — two-column comparison
                result_ungated = None
                with st.spinner("🔬 " + ("对比无治理版本中…" if lang == "中文" else "Comparing ungoverned version…")):
                    try:
                        _ug_msg = client.messages.create(
                            model="claude-sonnet-4-6", max_tokens=512,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        _ug_raw = _ug_msg.content[0].text.replace("```json","").replace("```","").strip()
                        result_ungated = json.loads(_ug_raw)
                    except Exception:
                        result_ungated = result

                # ── Log with overlap_rate for V3 governance value analysis ──
                _gov_codes = {s["code"] for s in result.get("selections", [])}
                _ung_codes = {s["code"] for s in (result_ungated or {}).get("selections", [])}
                _overlap   = len(_gov_codes & _ung_codes) / max(len(_gov_codes), 1)
                profile_meta["overlap_rate"] = round(_overlap, 3)
                gf_engine.log_submission(gate, profile_meta, ai_generated=True)
                _update_session_memory(gate)

                col_l, col_r = st.columns(2, gap="medium")

                with col_l:
                    st.markdown(
                        f"<div style='font-family:\"Press Start 2P\",monospace;font-size:8px;"
                        f"color:#6b7280;margin-bottom:6px'>🎲 {'拉胯版' if cn else 'Blind guess'}</div>"
                        f"<div style='font-family:\"Courier New\",monospace;font-size:11px;"
                        f"color:#ef4444;padding:5px 8px;background:#1a0505;"
                        f"border-left:3px solid #7f1d1d;margin-bottom:10px'>⚠ {why_bad}</div>",
                        unsafe_allow_html=True,
                    )
                    for s in (result_ungated or {}).get("selections", [])[:4]:
                        code   = s.get("code", "")
                        course = eligible_map.get(code)
                        name   = course["name"] if course else code
                        reason = s.get("reason", "")
                        st.markdown(
                            f"""<div style="border:1px solid #374151;padding:10px 12px;
                                           margin-bottom:8px;background:#0d0d1f">
  <div style="font-family:'Courier New',monospace;font-size:12px;
              color:#6b7280;margin-bottom:4px">
    <code style="background:#1f2937;padding:2px 5px;color:#94a3b8">{code}</code>&nbsp;{name}
  </div>
  <div style="font-size:11px;color:#4b5563;line-height:1.5">{reason[:80]+'…' if len(reason)>80 else reason}</div>
</div>""",
                            unsafe_allow_html=True,
                        )
                    if result_ungated and result_ungated.get("summary"):
                        st.markdown(
                            f"<div style='font-size:11px;color:#4b5563;margin-top:6px;"
                            f"font-style:italic'>{result_ungated['summary']}</div>",
                            unsafe_allow_html=True,
                        )

                with col_r:
                    st.markdown(
                        f"<div style='font-family:\"Press Start 2P\",monospace;font-size:8px;"
                        f"color:{dec_color_r};margin-bottom:6px'>🎯 {'遥遥领先版' if cn else 'Smart pick'}</div>"
                        f"<div style='font-family:\"Courier New\",monospace;font-size:11px;"
                        f"color:{dec_color_r};padding:5px 8px;background:#021a0a;"
                        f"border-left:3px solid {dec_color_r};margin-bottom:10px'>↑ {why_good}</div>",
                        unsafe_allow_html=True,
                    )
                    _render_cards(result, eligible_map, completed_codes, t, cn, dec_color_r)

            # ── Post-generation paywall teaser ────────────
            remaining_after = max(0, FREE_LIMIT - st.session_state.gen_count)
            if not st.session_state.is_pro and remaining_after == 0:
                st.divider()
                st.markdown(
                    "<div style='border:3px solid #f59e0b;background:linear-gradient(135deg,#0d0a00,#1c1000);"
                    "padding:16px 20px;box-shadow:5px 5px 0 #451a03;margin:12px 0'>"
                    "<div style='font-family:\"Press Start 2P\",monospace;font-size:9px;"
                    f"color:#f59e0b;margin-bottom:8px'>🔓 {t['paywall_title']}</div>"
                    f"<div style='font-family:\"Courier New\",monospace;font-size:12px;"
                    f"color:#d97706;line-height:1.7'>{t['paywall_body']}</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.link_button(t["paywall_btn"], t["paywall_url"], use_container_width=True)

            # ── Micro-feedback widget ──────────────────────────────────────
            st.divider()
            _fb_key = f"fb_rating_{st.session_state['session_id']}"
            _fb_comment_key = f"fb_comment_{st.session_state['session_id']}"
            _fb_done_key = f"fb_done_{st.session_state['session_id']}"

            if not st.session_state.get(_fb_done_key):
                # Header
                st.markdown(
                    f"<div style='font-family:\"Press Start 2P\",monospace;font-size:8px;"
                    f"color:#818cf8;margin-bottom:4px'>{t['fb_prompt']}</div>"
                    f"<div style='font-family:\"Courier New\",monospace;font-size:11px;"
                    f"color:#4b5563;margin-bottom:12px'>{t['fb_sub']}</div>",
                    unsafe_allow_html=True,
                )
                _fb_col1, _fb_col2, _fb_col3 = st.columns(3)
                _current_rating = st.session_state.get(_fb_key)

                def _make_fb_btn(col, label, rating_val):
                    active = (_current_rating == rating_val)
                    with col:
                        if st.button(
                            label,
                            key=f"fb_btn_{rating_val}_{st.session_state['session_id']}",
                            use_container_width=True,
                            type="primary" if active else "secondary",
                        ):
                            st.session_state[_fb_key] = rating_val
                            st.rerun()

                _make_fb_btn(_fb_col1, t["fb_bad"],   "bad")
                _make_fb_btn(_fb_col2, t["fb_ok"],    "ok")
                _make_fb_btn(_fb_col3, t["fb_great"], "great")

                # Comment box — always visible, contextual label after rating chosen
                _thanks_map = {
                    "bad":   t["fb_thanks_bad"],
                    "ok":    t["fb_thanks_ok"],
                    "great": t["fb_thanks_great"],
                }
                _comment_label = _thanks_map.get(_current_rating, t["fb_prompt"])
                if _current_rating:
                    st.markdown(
                        f"<div style='font-size:11px;color:#22c55e;margin:8px 0 2px 0'>"
                        f"{_comment_label}</div>",
                        unsafe_allow_html=True,
                    )
                st.text_input(
                    "　",
                    placeholder=t["fb_comment_ph"],
                    key=_fb_comment_key,
                    label_visibility="collapsed",
                )
                if _current_rating:
                    if st.button(
                        t["fb_submit"],
                        key=f"fb_submit_{st.session_state['session_id']}",
                        type="primary",
                    ):
                        _log_feedback(
                            rating=_current_rating,
                            comment=st.session_state.get(_fb_comment_key, ""),
                            session_id=st.session_state["session_id"],
                            gate_decision=gate.decision,
                            lang=lang,
                        )
                        st.session_state[_fb_done_key] = True
                        st.rerun()
            else:
                st.markdown(
                    f"<div style='font-family:\"Courier New\",monospace;font-size:12px;"
                    f"color:#22c55e;padding:8px 0'>{t['fb_done']}</div>",
                    unsafe_allow_html=True,
                )

        except Exception as e:
            st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════

st.divider()
st.caption(t["footer"])
