"""
UNSW MCom Handbook Scraper
运行方式: python3 scrape_handbook.py
会自动抓取所有专业的最新课程，并输出可以直接粘贴进 app.py 的 COURSES 字典
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
BASE = "https://www.handbook.unsw.edu.au"
YEAR = 2026

# MCom 所有专业的 handbook 代码
SPECIALISATIONS = {
    "Accounting":                        "ACCTTS",
    "Business Analytics":                "COMMBS",
    "Cybersecurity, Risk and Privacy":   "COMMCS",
    "Digital Transformation":            "COMMDT",
    "Economics":                         "ECONTS",
    "Finance":                           "FINSFS",
    "Financial Technology":              "COMMFT",
    "Global Sustainability and Social Impact": "COMMGS",
    "Human Resource Management":         "MGMTHS",
    "International Business":            "MGMTIS",
    "Marketing":                         "MARKTS",
    "Marketing Analytics":               "COMMMA",
    "Risk Management":                   "COMMRM",
    "Strategy and Innovation":           "COMMSI",
    "AI in Business and Society":        "commls",
}

def fetch(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
            print(f"  HTTP {r.status_code}: {url}")
        except Exception as e:
            print(f"  Error ({i+1}/{retries}): {e}")
        time.sleep(1)
    return None

def get_course_name(code):
    """从课程页面抓取课程名称"""
    url = f"{BASE}/postgraduate/courses/{YEAR}/{code}"
    soup = fetch(url)
    if not soup:
        return code
    # 尝试找课程名称
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
        # 移除课程代码前缀（如 "COMM5202 - Social and Environmental Sustainability"）
        name = re.sub(rf"^{code}\s*[-–]\s*", "", name)
        return name
    title = soup.find("title")
    if title:
        name = title.get_text(strip=True).split("|")[0].strip()
        name = re.sub(rf"^{code}\s*[-–]\s*", "", name)
        return name
    return code

def get_specialisation_courses(spec_code):
    """从专业页面抓取所有课程代码"""
    url = f"{BASE}/postgraduate/specialisations/{YEAR}/{spec_code}"
    soup = fetch(url)
    if not soup:
        return []

    # 找所有课程代码链接（格式：/postgraduate/courses/YYYY/XXXX0000）
    course_pattern = re.compile(r"/postgraduate/courses/\d+/([A-Z]{4}\d{4})", re.IGNORECASE)
    found = {}
    for a in soup.find_all("a", href=course_pattern):
        m = course_pattern.search(a["href"])
        if m:
            code = m.group(1).upper()
            if code not in found:
                # 尝试从链接文字获取课程名
                name = a.get_text(strip=True)
                found[code] = name if name and name != code else None

    # 也用正则从全文提取课程代码
    full_text = soup.get_text()
    for code in re.findall(r"\b([A-Z]{4}\d{4})\b", full_text):
        if code not in found:
            found[code] = None

    return list(found.items())  # [(code, name_or_None), ...]

def build_course_entry(code, name=None):
    if not name or name == code:
        print(f"    Fetching name for {code}...")
        name = get_course_name(code)
        time.sleep(0.3)
    return {
        "code": code,
        "name": name,
        "url": f"https://www.handbook.unsw.edu.au/postgraduate/courses/{YEAR}/{code}"
    }

def main():
    print(f"Scraping UNSW MCom handbook ({YEAR})...\n")
    courses_dict = {}

    for spec_name, spec_code in SPECIALISATIONS.items():
        print(f"\n{'='*60}")
        print(f"Specialisation: {spec_name} ({spec_code})")
        url = f"{BASE}/postgraduate/specialisations/{YEAR}/{spec_code}"
        print(f"URL: {url}")

        pairs = get_specialisation_courses(spec_code)
        if not pairs:
            print(f"  ⚠️  No courses found — check spec code '{spec_code}'")
            courses_dict[spec_name] = []
            continue

        print(f"  Found {len(pairs)} course codes: {[p[0] for p in pairs]}")
        entries = []
        for code, name in pairs:
            entry = build_course_entry(code, name)
            print(f"    ✓ {entry['code']}: {entry['name']}")
            entries.append(entry)
        courses_dict[spec_name] = entries
        time.sleep(0.5)

    # 输出 Python 字典格式
    print("\n\n" + "="*60)
    print("COURSES DICT (copy into app.py):")
    print("="*60)
    print("COURSES = {")
    for spec, entries in courses_dict.items():
        print(f'    "{spec}": [')
        for e in entries:
            print(f'        {{"code": "{e["code"]}", "name": "{e["name"]}", "url": "{e["url"]}"}},')
        print("    ],")
    print("}")

    # 同时保存到 JSON 文件
    with open("handbook_courses.json", "w", encoding="utf-8") as f:
        json.dump(courses_dict, f, ensure_ascii=False, indent=2)
    print("\n✅ 已保存到 handbook_courses.json")

if __name__ == "__main__":
    main()
