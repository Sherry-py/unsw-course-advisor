import streamlit as st
import anthropic
import json
import time
import plotly.express as px
import governance as gf_engine

st.set_page_config(
    page_title="UNSW MCom Course Advisor",
    page_icon="🎓",
    layout="centered",
)

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
        "paywall_title": "🔓 解锁深度选课咨询",
        "paywall_used":  "你已使用 {n} 次免费建议",
        "paywall_body":  """**免费版**已经很强大，但 Pro 版还有更多：

✅ **职业路径模拟** — 看不同选课方案对应什么工作  
✅ **WAM 提升策略** — AI 分析哪些课最容易拿高分  
✅ **论文研究方向** — 为读博/做研究定制的选课路径  
✅ **无限次数** — 随时改变方向，反复测试方案""",
        "paywall_btn":   "🚀 升级 Pro — $9.9/月",
        "paywall_url":   "https://buy.stripe.com/placeholder",  # replace with real Stripe link
        "free_remaining": "剩余免费次数：{n}/{total}",
        "pro_badge":      "✅ Pro 用户",

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

        "paywall_title": "🔓 Unlock Deep Advising",
        "paywall_used":  "You have used {n} free recommendations",
        "paywall_body":  """**Free tier** is already powerful. Upgrade for more:

✅ **Career path simulation** — see which jobs each course path leads to  
✅ **WAM improvement strategy** — AI finds the best courses for your GPA  
✅ **Research & PhD track** — custom plan if you're aiming for academia  
✅ **Unlimited generations** — change your mind, test new paths anytime""",
        "paywall_btn":   "🚀 Upgrade to Pro — A$9.9/month",
        "paywall_url":   "https://buy.stripe.com/placeholder",
        "free_remaining": "Free uses left: {n}/{total}",
        "pro_badge":      "✅ Pro User",

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
    },
}

# ════════════════════════════════════════════════════════
# SESSION STATE INIT
# ════════════════════════════════════════════════════════

if "gen_count" not in st.session_state:
    st.session_state.gen_count = 0
if "is_pro" not in st.session_state:
    st.session_state.is_pro = False

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
        st.markdown("---")
        st.markdown("**Pro 解锁：**" if lang == "中文" else "**Pro unlocks:**")
        st.markdown("🔒 职业路径模拟" if lang == "中文" else "🔒 Career path simulation")
        st.markdown("🔒 WAM 提升策略" if lang == "中文" else "🔒 WAM improvement strategy")
        st.markdown("🔒 论文研究路径" if lang == "中文" else "🔒 Research / PhD track")
        st.markdown("🔒 无限次数" if lang == "中文" else "🔒 Unlimited uses")
        st.link_button(
            t["paywall_btn"],
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
# STEP 1 — GOALS (Coverage dimension: CRITICAL)
# ════════════════════════════════════════════════════════

st.subheader(t["sec_goals"])

selected_goals = st.multiselect(t["goals_label"], t["goals_options"])
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

    fig = px.pie(
        names=list(goal_weights.keys()),
        values=list(goal_weights.values()),
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250,
                      showlegend=True, legend=dict(font=dict(size=10)))
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════
# STEP 2 — PROFILE (Relevance + Ordering + Robustness)
# ════════════════════════════════════════════════════════

st.divider()
st.subheader(t["sec_profile"])

c1, c2 = st.columns(2)
with c1:
    specs = st.multiselect(t["spec_label"], list(COURSES.keys()),
                           max_selections=2, placeholder=t["spec_ph"])
with c2:
    term  = st.selectbox(t["term_label"],
                         ["Term 2 2026", "Term 3 2026", "Term 1 2027", "Term 2 2027"])

c3, c4 = st.columns(2)
with c3:
    wam     = st.text_input(t["wam_label"], placeholder=t["wam_ph"])
with c4:
    credits = st.selectbox(t["uoc_label"],
                           ["96 UOC", "72 UOC", "48 UOC", "36 UOC", "24 UOC", "12 UOC"])

completed_courses = st.multiselect(
    t["completed_label"],
    options=ALL_COURSE_CODES,
    format_func=lambda code: f"{code} · {ALL_COURSES_DICT[code]['name']}",
    placeholder=t["completed_ph"],
)

c5, c6 = st.columns([1, 2])
with c5:
    load = st.radio(t["load_label"], t["load_options"], index=1)
with c6:
    notes = st.text_input(t["notes_label"], placeholder=t["notes_ph"])

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

    st.divider()
    with st.expander(
        "🛡️ GateFix 输入质量诊断" if cn else "🛡️ GateFix Input Quality Diagnostics",
        expanded=True,
    ):
        # ── 4D-CQ status bar ──────────────────────────────────────────
        # label, zh_ok, zh_fail, en_ok, en_fail, critical
        dim_info = [
            ("relevance",  "专业方向",   "✅ 已选择",  "🔴 未选择",  "Specialisation", "✅ Selected",  "🔴 Not selected",  True),
            ("coverage",   "毕业目标",   "✅ 已填写",  "🔴 未填写",  "Goals",          "✅ Provided",  "🔴 Not provided",  True),
            ("ordering",   "学分核对",   "✅ 正常",    "⚠️ 请检查",  "Credit check",   "✅ Consistent","⚠️ Please verify", False),
            ("robustness", "补充信息",   "✅ 已填写",  "⚠️ 建议补充","Extra details",  "✅ Provided",  "⚠️ Optional",      False),
        ]
        cols4 = st.columns(4)
        for col, (dim, zh_lbl, zh_ok, zh_fail, en_lbl, en_ok, en_fail, critical) in zip(cols4, dim_info):
            ok    = (getattr(gate.cq, dim) == "OK")
            label = zh_lbl if cn else en_lbl
            val   = (zh_ok if ok else zh_fail) if cn else (en_ok if ok else en_fail)
            col.metric(label=label, value=val)

        dec_label_full = {
            "PASS":    "✅ 已通过" if cn else "✅ Ready",
            "CLARIFY": "⚠️ 建议补充信息" if cn else "⚠️ Proceeding with note",
            "REFUSE":  "❌ 请完善必填项后重试" if cn else "❌ Please complete required fields",
        }
        st.markdown(
            f"<div style='margin:10px 0 4px 0;font-size:13px;color:{dec_color};font-weight:600'>"
            f"{dec_label_full[gate.decision]}"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # ── Side-by-side comparison ───────────────────────────────────
        col_l, col_r = st.columns(2, gap="medium")

        def _course_list(res):
            items = []
            for s in (res or {}).get("selections", [])[:4]:
                code   = s.get("code", "")
                course = eligible_map.get(code)
                name   = course["name"] if course else code
                items.append(f"<li style='margin:4px 0'><code>{code}</code> {name}</li>")
            return "<ul style='padding-left:16px;margin:8px 0'>" + "".join(items) + "</ul>" if items else ""

        with col_l:
            st.markdown(
                f"<div style='font-weight:600;margin-bottom:6px'>{'未治理' if cn else 'Without GateFix'}</div>",
                unsafe_allow_html=True,
            )
            if result_ungated:
                st.markdown(_course_list(result_ungated), unsafe_allow_html=True)
                if result_ungated.get("summary"):
                    st.caption(result_ungated["summary"])
            else:
                st.caption("—")

        with col_r:
            st.markdown(
                f"<div style='font-weight:600;color:{dec_color};margin-bottom:6px'>"
                f"{'GateFix 治理后' if cn else 'With GateFix'}</div>",
                unsafe_allow_html=True,
            )
            if gate.decision == "REFUSE":
                st.markdown(
                    f"<div style='color:#ef4444;font-size:13px'>"
                    f"{'🚫 执行已阻断' if cn else '🚫 Execution blocked'}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            elif gate.decision == "CLARIFY":
                if result_governed:
                    st.markdown(_course_list(result_governed), unsafe_allow_html=True)
                    if result_governed.get("summary"):
                        st.caption(result_governed["summary"])
                st.markdown(
                    f"<div style='color:#f59e0b;font-size:12px;margin-top:6px'>"
                    f"{'⚠️ 已标注质量提示' if cn else '⚠️ Quality flag annotated'}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:  # PASS
                if result_governed:
                    st.markdown(_course_list(result_governed), unsafe_allow_html=True)
                    if result_governed.get("summary"):
                        st.caption(result_governed["summary"])
                st.markdown(
                    f"<div style='color:#22c55e;font-size:12px;margin-top:6px'>"
                    f"{'✅ 全部维度通过验证' if cn else '✅ All dimensions verified'}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")


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

    profile_meta = {
        "n_specs":      len(specs),
        "n_goals":      len(all_goals),
        "n_completed":  len(completed_courses),
        "credits_left": credits,
        "has_wam":      bool(wam.strip()),
        "has_notes":    bool(notes.strip()),
        "load":         load,
        "lang":         lang,
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

    # ── REFUSE: block main AI, show guidance + experiment panel ──
    if gate.decision == "REFUSE":
        gf_engine.log_submission(gate, profile_meta, ai_generated=False)
        st.warning(t[gate.refuse_key])
        # Experiment: call ungated AI to show what it WOULD have returned
        result_ungated = None
        with st.spinner("🔬 " + ("模拟无治理 AI 中…" if lang == "中文" else "Simulating ungoverned AI…")):
            try:
                _msg = client.messages.create(
                    model="claude-sonnet-4-6", max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                _raw = _msg.content[0].text.replace("```json", "").replace("```", "").strip()
                result_ungated = json.loads(_raw)
            except Exception:
                pass
        _render_experiment_panel(gate, eligible_map, result_ungated, None, t, lang)
        st.stop()

    # ── CLARIFY: show hint, proceed ───────────────────────
    if gate.decision == "CLARIFY":
        st.info(t[gate.clarify_key])

    # ── Paywall check (AFTER governance, BEFORE AI call) ──
    if not st.session_state.is_pro and st.session_state.gen_count >= FREE_LIMIT:
        gf_engine.log_submission(gate, profile_meta, ai_generated=False)
        st.warning(f"**{t['paywall_title']}**\n\n"
                   + t["paywall_used"].format(n=st.session_state.gen_count)
                   + "\n\n" + t["paywall_body"])
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
            gf_engine.log_submission(gate, profile_meta, ai_generated=True)

            # ── Render results ────────────────────────────
            if result.get("warning"):
                st.warning(result["warning"])
            st.info(result.get("summary", ""))

            # Prerequisite conflicts
            conflict_lines = []
            for s in result.get("selections", []):
                code = s.get("code", "")
                meta = COURSE_META.get(code, {})
                unmet = [p for p in meta.get("prereqs", []) if p not in completed_codes]
                if unmet:
                    name = eligible_map.get(code, {}).get("name", code)
                    conflict_lines.append(
                        f"**{code} {name}** — {t['prereq_label']}: {', '.join(unmet)}"
                    )
            if conflict_lines:
                st.warning(
                    t["conflict_title"] + "\n\n" + t["conflict_body"] + "\n\n" +
                    "\n\n".join(f"- {l}" for l in conflict_lines)
                )

            priority_map = t["priority_map"]
            valid_shown  = 0
            for s in result.get("selections", []):
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
                        st.link_button(t["handbook_btn"], course["url"],
                                       use_container_width=True)

            if valid_shown == 0:
                st.error(t["no_valid_courses"])

            # ── Post-generation paywall teaser (blur gate) ─
            remaining_after = max(0, FREE_LIMIT - st.session_state.gen_count)
            if not st.session_state.is_pro and remaining_after == 0:
                st.divider()
                st.markdown(
                    "<div style='filter:blur(4px);opacity:0.4;pointer-events:none'>"
                    "🔒 职业路径模拟 · WAM 提升分析 · 论文研究路径规划 · 深度选课报告..."
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.warning(
                    f"**{t['paywall_title']}**\n\n"
                    + t["paywall_body"]
                )
                st.link_button(t["paywall_btn"], t["paywall_url"], use_container_width=True)

            # ── GateFix experiment panel (CLARIFY / PASS) ─
            # For CLARIFY/PASS the governed result IS the AI result;
            # the ungated column shows it WITHOUT the governance annotation,
            # demonstrating what a pure AI response looks like with no quality check.
            _render_experiment_panel(gate, eligible_map, result, result, t, lang)

        except Exception as e:
            st.error(f"Error: {e}")

# ════════════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════════════

st.divider()
c_foot, c_fb = st.columns([3, 1])
with c_foot:
    st.caption(t["footer"])
with c_fb:
    st.link_button(
        t["feedback_btn"],
        "https://docs.google.com/forms/d/e/1FAIpQLSe_YdjLFQOtPsEzV5n5Zdi1jPfq35Nk3cgoNESinbCEqFzNhw/viewform",
        use_container_width=True,
    )
