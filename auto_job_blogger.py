#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BD Education & Job Info (https://bdedujob.blogspot.com/)
100% Accurate Circular-Faithful Scraper, Banner Designer & Blogger Auto-Publisher
- Extracts exact circular details (Organization type, Vacancy, Posts, Salary, Qualification, Dates, Email/Portal/Teletalk Apply method)
- Decodes Cloudflare-protected emails (e.g. hrd@ad-din.org)
- Only shows Teletalk 16222 SMS steps when the job actually uses Teletalk (*.teletalk.com.bd)
"""

import os
import re
import time
import json
import base64
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup

from banner_generator import generate_job_banner

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "posted_jobs.json")
BANNERS_DIR = os.path.join(BASE_DIR, "generated_banners")

# ==============================================================================
# ১. কনফিগারেশন (Environment Variables থেকে লোড হবে)
# ==============================================================================
BLOGGER_BLOG_ID = os.getenv("BLOGGER_BLOG_ID", "3244474783562745180")
BLOGGER_CLIENT_ID = os.getenv("BLOGGER_CLIENT_ID", "")
BLOGGER_CLIENT_SECRET = os.getenv("BLOGGER_CLIENT_SECRET", "")
BLOGGER_REFRESH_TOKEN = os.getenv("BLOGGER_REFRESH_TOKEN", "")

BLOGGER_IS_DRAFT = os.getenv("BLOGGER_IS_DRAFT", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")
MAX_POSTS_PER_RUN = int(os.getenv("MAX_POSTS_PER_RUN", "1"))

SITE_URL = "https://bdedujob.blogspot.com"
SITE_DISPLAY = "www.bdedujob.blogspot.com"
PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=com.rakibtech.jobcircular"

ALLOWED_BLOGGER_LABELS = [
    "All Jobs",
    "Bank Jobs",
    "Current Affairs",
    "Edcation",
    "Exam Routine",
    "Govt Jobs",
    "Privet Jobs",
    "Result",
    "Saptahik Job Paper",
    "all",
    "exam result",
    "job",
]

JOB_SOURCES = [
    {
        "name": "BD Govt Job (All Latest)",
        "feed_url": "https://bdgovtjob.net/feed/",
        "default_label": "Govt Jobs",
    },
    {
        "name": "BD Govt Job (Bank Jobs)",
        "feed_url": "https://bdgovtjob.net/category/bank-jobs/feed/",
        "default_label": "Bank Jobs",
    },
    {
        "name": "BD Govt Job (Exam Result & Routine Notice)",
        "feed_url": "https://bdgovtjob.net/category/notice/feed/",
        "default_label": "Result",
    },
    {
        "name": "BD Govt Job (Educational Institution Jobs)",
        "feed_url": "https://bdgovtjob.net/category/educational-institution-jobs/feed/",
        "default_label": "Edcation",
    },
    {
        "name": "BD Govt Job (Govt Circulars)",
        "feed_url": "https://bdgovtjob.net/category/government-jobs-circular/feed/",
        "default_label": "Govt Jobs",
    },
    {
        "name": "BD Govt Job (NGO Jobs)",
        "feed_url": "https://bdgovtjob.net/category/ngo-job-circular/feed/",
        "default_label": "Privet Jobs",
    },
    {
        "name": "BD Govt Job (Private Jobs)",
        "feed_url": "https://bdgovtjob.net/category/private-jobs/feed/",
        "default_label": "Privet Jobs",
    },
    {
        "name": "BD Govt Job (Saptahik Chakrir Khobor)",
        "feed_url": "https://bdgovtjob.net/category/saptahik-chakrir-khobor/feed/",
        "default_label": "Saptahik Job Paper",
    },
    {
        "name": "eJobs Circular (Bank Jobs)",
        "feed_url": "https://ejobscircular.com/category/bank-jobs/feed/",
        "default_label": "Bank Jobs",
    },
    {
        "name": "eJobs Circular (All Jobs)",
        "feed_url": "https://ejobscircular.com/feed/",
        "default_label": "Govt Jobs",
    },
    {
        "name": "KF Planet (Exam Routine)",
        "feed_url": "https://kfplanet.com/category/education-bd/exam-routine/feed/",
        "default_label": "Exam Routine",
    },
    {
        "name": "KF Planet (Exam Result)",
        "feed_url": "https://kfplanet.com/category/education-bd/exam-result/feed/",
        "default_label": "Result",
    },
    {
        "name": "KF Planet (Education & Admission)",
        "feed_url": "https://kfplanet.com/category/education-bd/admission-info/feed/",
        "default_label": "Edcation",
    },
    {
        "name": "KF Planet (All Jobs)",
        "feed_url": "https://kfplanet.com/category/jobs-bd/feed/",
        "default_label": "All Jobs",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}


def decode_cfemail(cf_hex: str) -> str:
    """Cloudflare [email protected] হেক্স কোড থেকে আসল ই-মেইল ঠিকানা বের করে।"""
    try:
        r = int(cf_hex[:2], 16)
        return "".join(chr(int(cf_hex[i : i + 2], 16) ^ r) for i in range(2, len(cf_hex), 2))
    except Exception:
        return ""


def determine_blogger_labels(raw_title: str, raw_cats: list, ai_labels: list, job_type_bn: str = "", default_label: str = "") -> list:
    combined = f"{raw_title} {' '.join(raw_cats)} {' '.join(ai_labels)} {job_type_bn} {default_label}".lower()
    labels = {"All Jobs", "job", "all"}

    if default_label and default_label in ALLOWED_BLOGGER_LABELS:
        labels.add(default_label)

    if any(k in combined for k in ["সাপ্তাহিক", "saptahik", "weekly", "পত্রিকা"]):
        labels.update(["Saptahik Job Paper", "Govt Jobs", "Privet Jobs"])
    if any(k in combined for k in ["ব্যাংক", "bank"]):
        labels.add("Bank Jobs")
    if any(k in combined for k in ["বেসরকারি", "private", "privet", "ngo", "এনজিও", "ফাউন্ডেশন", "foundation", "কোম্পানি", "লিমিটেড", "ltd", "group", "হাসপাতাল", "ফার্মাসিউটিক্যাল"]):
        labels.add("Privet Jobs")
    if any(k in combined for k in ["সরকারি", "govt", "government", "মন্ত্রণালয়", "অধিদপ্তর", "বিশ্ববিদ্যালয়", "বিশ্ববিদ্যালয়", "কর্পোরেশন", "বোর্ড", "কমিশন", "সিভিল সার্জন", "জেলা প্রশাসক", "বিপিএটিসি", "বিকেএসপি", "ইনস্টিটিউট", "কর অঞ্চল"]):
        if "বেসরকারি" not in combined and "এনজিও" not in combined and "ফাউন্ডেশন" not in combined:
            labels.add("Govt Jobs")
    if any(k in combined for k in ["ফলাফল", "রেজাল্ট", "result"]):
        labels.update(["Result", "exam result"])
    if any(k in combined for k in ["রুটিন", "routine", "পরীক্ষার তারিখ", "exam date", "সময়সূচি", "সময়সূচি", "কেন্দ্র তালিকা", "প্রবেশপত্র", "admit card"]):
        labels.add("Exam Routine")
    if any(k in combined for k in ["শিক্ষা", "education", "edcation", "ভর্তি", "admission", "ssc", "hsc", "honours", "degree", "বিশ্ববিদ্যালয়", "বিশ্ববিদ্যালয়", "কলেজ", "স্কুল", "মাদ্রাসা"]):
        labels.add("Edcation")
    if any(k in combined for k in ["কারেন্ট অ্যাফেয়ার্স", "current affairs", "সাধারণ জ্ঞান"]):
        labels.add("Current Affairs")

    if not any(x in labels for x in ["Govt Jobs", "Privet Jobs", "Bank Jobs", "Saptahik Job Paper", "Result", "Exam Routine", "Edcation"]):
        labels.add("Govt Jobs")

    return [lbl for lbl in ALLOWED_BLOGGER_LABELS if lbl in labels]


def load_posted_jobs() -> list:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_posted_job(url: str):
    posted = load_posted_jobs()
    if url not in posted:
        posted.append(url)
        posted = posted[-500:]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(posted, f, ensure_ascii=False, indent=2)


def fetch_rss_items(feed_url: str) -> list:
    req = urllib.request.Request(feed_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        categories = [c.text.strip() for c in item.findall("category") if c.text]
        items.append({"title": title, "link": link, "categories": categories})
    return items


def scrape_job_details(article_url: str) -> dict:
    req = urllib.request.Request(article_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    soup = BeautifulSoup(html, "html.parser")

    # Decode Cloudflare protected emails before extracting text
    decoded_emails = []
    for el in soup.find_all(attrs={"data-cfemail": True}):
        email_str = decode_cfemail(el["data-cfemail"])
        if email_str:
            el.string = email_str
            if email_str not in decoded_emails:
                decoded_emails.append(email_str)

    content_div = (
        soup.find(class_="entry-content")
        or soup.find(class_="td-post-content")
        or soup.find("article")
        or soup.body
    )

    # সোর্স পেজের ভেতরে থাকা Related Posts / আরও দেখুন সেকশনগুলো মুছে ফেলা (যাতে অন্য পোস্টের ব্যানার বা লিংক কখনোই না আসে)
    if content_div:
        for junk in content_div.select(
            "ul.bdg-related-list, .bdg-related, .related-posts, .yarpp-related, "
            ".jp-relatedposts, .wp-block-latest-posts, nav, aside, .sharedaddy"
        ):
            junk.decompose()

    raw_text = content_div.get_text("\n", strip=True) if content_div else ""

    # অফিসিয়াল সার্কুলারের ছবিগুলো আলাদা করা (অন্য ওয়েবসাইটের ব্যানার/থাম্বনেইল সম্পূর্ণ বাদ দিয়ে)
    notice_images = []
    if content_div:
        for img in content_div.find_all("img"):
            # যদি ছবিটি অন্য কোনো পোস্টের লিংকের (<a href="...">) ভেতরে থাকে তবে বাদ দিন
            a_parent = img.find_parent("a")
            if a_parent and a_parent.get("href"):
                ahref = a_parent.get("href", "").strip().lower().split("?")[0]
                if (
                    ahref
                    and not ahref.startswith("#")
                    and not ahref.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))
                ):
                    continue

            # ছোট থাম্বনেইল বা আনুভূমিক (16:9) অন্য সাইটের ফিচার্ড ব্যানার বাদ দিন
            w_attr = img.get("width")
            h_attr = img.get("height")
            if w_attr and h_attr:
                try:
                    w_val, h_val = int(w_attr), int(h_attr)
                    if w_val < 350 or h_val < 350:
                        continue
                    if w_val > h_val * 1.35:
                        continue
                except ValueError:
                    pass

            src = img.get("data-src") or img.get("data-lazy-src") or img.get("src") or ""
            if not src or src.startswith("data:"):
                continue
            low = src.lower()
            if any(
                skip in low
                for skip in [
                    "logo",
                    "icon",
                    "button",
                    "apply",
                    "banner",
                    "avatar",
                    "gravatar",
                    "150x150",
                    "300x",
                    "100x",
                ]
            ):
                continue
            if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                clean_src = src.split("?")[0] if "wp.com" in src else src
                if clean_src not in notice_images:
                    notice_images.append(clean_src)

    # সোর্স পেজ থেকে লিংকসমূহ ও অফিশিয়াল PDF সংগ্রহ
    teletalk_url = ""
    official_site = ""
    external_apply_url = ""
    pdf_links = []
    if content_div:
        for a in content_div.find_all("a", href=True):
            href = a["href"].strip()
            if "cdn-cgi/l/email-protection#" in href:
                cf_hex = href.split("#")[-1]
                em = decode_cfemail(cf_hex)
                if em and em not in decoded_emails:
                    decoded_emails.append(em)
                continue
            low_href = href.lower()
            if ".pdf" in low_href and href.startswith("http"):
                if href not in pdf_links:
                    pdf_links.append(href)
                continue
            if any(skip in low_href for skip in ["bdgovtjob.net", "ejobscircular.com", "kfplanet.com", "facebook.com", "t.me", "whatsapp.com", "twitter.com", "wp.com"]):
                continue
            if "teletalk.com.bd" in low_href and not teletalk_url:
                teletalk_url = href
            elif any(d in low_href for d in ["bdjobs.com", "jobs.", "career", "erecruitment", "apply"]) and not external_apply_url:
                external_apply_url = href
            elif href.startswith("http") and not official_site:
                official_site = href

    # সোর্স পেজের লাইনগুলো থেকে কী-ভ্যালু সামারি পার্স করা (AI ছাড়াও যাতে ১০০% সঠিক তথ্য থাকে)
    lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
    kv_map = {}
    known_keys = [
        "প্রতিষ্ঠানের নাম",
        "প্রতিষ্ঠানের ইংরেজি নাম",
        "কার্যক্রম / খাত",
        "জব লোকেশন",
        "পদের ক্যাটাগরি",
        "পদের নাম",
        "মোট শূন্যপদ",
        "চাকরির ধরন",
        "নোটিশের ধরন",
        "স্মারক নম্বর",
        "নোটিশ প্রকাশের তারিখ",
        "ফলাফলের ধরন",
        "মোট উত্তীর্ণ প্রার্থী",
        "ব্যবহারিক / পরবর্তী পরীক্ষার তারিখ",
        "ব্যবহারিক / পরবর্তী পরীক্ষার কেন্দ্র",
        "বয়সসীমা",
        "শিক্ষাগত যোগ্যতা",
        "বেতন ও সুযোগ-সুবিধা",
        "বিজ্ঞপ্তির সোর্স",
        "বিজ্ঞপ্তি প্রকাশের তারিখ",
        "আবেদনের শুরু",
        "আবেদনের শেষ তারিখ",
        "আবেদনের শেষ সময়ঃ",
        "আবেদন পদ্ধতি",
        "আবেদনের পদ্ধতিঃ",
        "অফিশিয়াল ওয়েবসাইট",
        "প্রধান কার্যালয়ের ঠিকানা",
        "ই-মেইল",
        "আবেদনের ই-মেইলঃ",
    ]
    for i, ln in enumerate(lines[:-1]):
        if ln in known_keys:
            val = lines[i + 1]
            if val not in known_keys:
                kv_map[ln] = val

    # সোর্স থেকে আবেদনের ধাপগুলো বের করা
    apply_steps = []
    for i, ln in enumerate(lines):
        if ("কিভাবে" in ln and "আবেদন করবেন" in ln) or ("গুরুত্বপূর্ণ নির্দেশনা" in ln) or ("জরুরি নির্দেশাবলি" in ln):
            for sub in lines[i + 1 : i + 15]:
                if any(stop in sub for stop in ["Job Circular", "Images / PDFs", "সাধারণ জিজ্ঞাসা", "আরও চলমান"]):
                    break
                if len(sub) > 18 and not sub.isdigit():
                    apply_steps.append(sub)
            break

    # সোর্স থেকে পদের নাম, পদসংখ্যা, যোগ্যতা ও বেতনের তালিকা বের করা
    parsed_posts = []
    for i, ln in enumerate(lines):
        m = re.match(r"^[০-৯0-9]+[\.\)]\s+(.+)$", ln)
        if m and i + 6 < len(lines):
            p_name = m.group(1).strip()
            if any(q in p_name for q in ["শেষ তারিখ কবে", "কতজন লোক", "শিক্ষাগত যোগ্যতা কী", "আবেদন করবেন", "সুযোগ-সুবিধা কেমন"]):
                continue
            block = "\n".join(lines[i + 1 : i + 10])
            if "যোগ্যতা" in block or "বেতন" in block or "পদ:" in block:
                vac = "নির্দিষ্ট নয়"
                sal = kv_map.get("বেতন ও সুযোগ-সুবিধা", "বিজ্ঞপ্তি অনুযায়ী")
                qual = kv_map.get("শিক্ষাগত যোগ্যতা", "বিজ্ঞপ্তি অনুযায়ী")
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].startswith("পদ:"):
                        vac = lines[j].replace("পদ:", "").strip()
                    elif "বেতন" in lines[j] and j + 1 < len(lines):
                        sal = lines[j + 1]
                    elif "শিক্ষাগত যোগ্যতা" in lines[j] and j + 1 < len(lines):
                        qual = lines[j + 1]
                parsed_posts.append({
                    "post_name": p_name,
                    "vacancy": vac,
                    "qualification": qual,
                    "salary": sal,
                })

    return {
        "raw_text": raw_text[:9500],
        "notice_images": notice_images[:6],
        "pdf_links": pdf_links[:3],
        "teletalk_url": teletalk_url,
        "external_apply_url": external_apply_url,
        "official_site": official_site or kv_map.get("অফিশিয়াল ওয়েবসাইট", ""),
        "decoded_emails": decoded_emails,
        "kv_map": kv_map,
        "apply_steps": apply_steps[:6],
        "parsed_posts": parsed_posts[:8],
    }


def extract_structured_job_info(raw_title: str, scraped: dict) -> dict:
    """
    সোর্স পেজের প্রকৃত তথ্য এবং Gemini AI (রাইট্রাই সহ) ব্যবহার করে ১০০% নির্ভুল জব ডাটা তৈরি করে।
    """
    raw_text = scraped["raw_text"]
    kv = scraped["kv_map"]
    emails = scraped["decoded_emails"]

    en_match = re.search(r"([A-Za-z0-9\-\s\(\)&\.]+Job Circular\s*\d{4})", raw_title)
    title_en = en_match.group(1).strip() if en_match else ""
    bn_part = re.sub(r"[A-Za-z0-9\-\|]+Job Circular.*", "", raw_title).strip(" -–|")
    org_name_bn = kv.get("প্রতিষ্ঠানের নাম") or re.sub(r"^(?:[০-৯0-9]+\s*পদে\s*)?(.*?)?\s*(?:নিয়োগ বিজ্ঞপ্তি|নিয়োগ বিজ্ঞপ্তি).*", r"\1", bn_part).strip() or bn_part

    if not title_en:
        title_en = f"{org_name_bn} Job Circular 2026"

    short_match = re.search(r"\b([A-Z]{2,10})\b", title_en.replace("Job", "").replace("Circular", ""))
    short_code = short_match.group(1) if short_match else "JOB"

    job_type_raw = kv.get("চাকরির ধরন", "")
    if not job_type_raw:
        if any(w in (raw_title + raw_text[:600]) for w in ["এনজিও", "ফাউন্ডেশন", "NGO", "Foundation", "লিমিটেড", "বেসরকারি", "গ্রুপ", "ফার্মাসিউটিক্যাল"]):
            job_type_raw = "বেসরকারি / এনজিও চাকরি (Private/NGO Job)"
        elif any(w in (raw_title + raw_text[:600]) for w in ["ব্যাংক", "Bank"]):
            job_type_raw = "ব্যাংক জব (Bank Job)"
        else:
            job_type_raw = "সরকারি চাকরি (Government Job)"

    is_govt = "সরকারি" in job_type_raw and "বেসরকারি" not in job_type_raw
    is_teletalk = bool(scraped["teletalk_url"]) or ("16222" in raw_text and "টেলিটক" in raw_text)

    vacancy_bn = kv.get("মোট শূন্যপদ") or kv.get("পদের ক্যাটাগরি") or "বিজ্ঞপ্তিতে দেখুন"
    qualification_bn = kv.get("শিক্ষাগত যোগ্যতা", "বিজ্ঞপ্তিতে দেখুন")
    age_limit_bn = kv.get("বয়সসীমা", "বিজ্ঞপ্তিতে দেখুন")
    salary_bn = kv.get("বেতন ও সুযোগ-সুবিধা", "বিজ্ঞপ্তিতে দেখুন")
    location_bn = kv.get("জব লোকেশন") or kv.get("প্রধান কার্যালয়ের ঠিকানা") or "বাংলাদেশের যেকোনো স্থান (বিজ্ঞপ্তি অনুযায়ী)"
    start_date_bn = kv.get("আবেদনের শুরু") or kv.get("বিজ্ঞপ্তি প্রকাশের তারিখ") or "চলমান"
    deadline_bn = kv.get("আবেদনের শেষ তারিখ") or kv.get("আবেদনের শেষ সময়ঃ") or "বিজ্ঞপ্তিতে দেখুন"
    apply_method_bn = kv.get("আবেদন পদ্ধতি") or kv.get("আবেদনের পদ্ধতিঃ") or ("টেলিটক অনলাইন" if is_teletalk else "বিজ্ঞপ্তির নির্দেশনা অনুযায়ী")
    apply_email = emails[0] if emails else kv.get("ই-মেইল", "")

    official_site = scraped["official_site"]
    if official_site and not official_site.startswith("http"):
        official_site = "https://" + official_site

    apply_url = (
        scraped["teletalk_url"]
        or scraped["external_apply_url"]
        or (f"mailto:{apply_email}" if apply_email else "")
        or official_site
        or SITE_URL
    )

    # প্রকৃত প্রতিষ্ঠানের ধরন অনুযায়ী ভূমিকা
    if is_govt:
        intro_1 = (
            f"<b>{org_name_bn}</b> শূন্য পদসমূহে জনবল নিয়োগের লক্ষ্যে যোগ্য ও আগ্রহী বাংলাদেশী নাগরিকদের নিকট হতে "
            f"দরখাস্ত আহ্বান করেছে। প্রকাশিত নিয়োগ বিজ্ঞপ্তি অনুযায়ী প্রতিষ্ঠানটিতে <b>{vacancy_bn}</b> পদে নিয়োগ দেওয়া হবে। "
            f"আগ্রহী প্রার্থীদের <b>{deadline_bn}</b> তারিখের মধ্যে <b>{apply_method_bn}</b> আবেদন সম্পন্ন করতে হবে।"
        )
    else:
        intro_1 = (
            f"দেশের শীর্ষস্থানীয় প্রতিষ্ঠান <b>{org_name_bn}</b> নতুন জনবল নিয়োগের লক্ষ্যে আনুষ্ঠানিক নিয়োগ বিজ্ঞপ্তি ২০২৬ প্রকাশ করেছে। "
            f"প্রকাশিত বিজ্ঞপ্তি অনুযায়ী প্রতিষ্ঠানটিতে <b>{qualification_bn}</b> যোগ্যতায় আকর্ষণীয় বেতন ও সুযোগ-সুবিধায় নিয়োগ দেওয়া হবে। "
            f"যোগ্য ও আগ্রহী প্রার্থীরা আগামী <b>{deadline_bn}</b> পর্যন্ত <b>{apply_method_bn}</b> আবেদন করতে পারবেন।"
        )

    intro_2 = (
        f"এই পোস্টের মাধ্যমে আমরা <b>{org_name_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ ({title_en})</b>-এর পদের নাম, পদসংখ্যা, "
        f"শিক্ষাগত যোগ্যতা, অভিজ্ঞতা, বেতন ও সুযোগ-সুবিধা, কর্মস্থল, আবেদনের শেষ তারিখ এবং কীভাবে সঠিকভাবে আবেদন করবেন "
        f"তার বিস্তারিত ও অফিশিয়াল বিজ্ঞপ্তির ছবি তুলে ধরেছি।"
    )

    posts_breakdown = scraped["parsed_posts"] or [
        {
            "post_name": f"{org_name_bn}-এর বিজ্ঞপ্তিতে উল্লেখিত পদসমূহ",
            "vacancy": vacancy_bn,
            "qualification": qualification_bn,
            "salary": salary_bn,
        }
    ]

    apply_steps_bn = scraped["apply_steps"] or [
        f"প্রার্থীকে অবশ্যই {org_name_bn}-এর অফিশিয়াল নিয়োগ বিজ্ঞপ্তির শর্তাবলী মনোযোগ দিয়ে পড়তে হবে।",
        f"আবেদন পদ্ধতি: {apply_method_bn}" + (f" (ই-মেইল: {apply_email})" if apply_email else ""),
        f"আবেদনের শেষ সময়: {deadline_bn}-এর পূর্বেই আবেদনপত্র বা সিভি প্রেরণ নিশ্চিত করতে হবে।",
    ]

    info = {
        "post_title": f"{org_name_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ - {title_en}",
        "org_name_bn": org_name_bn,
        "org_name_en": title_en.replace("Job Circular 2026", "").replace("Job Circular 2025", "").strip() or org_name_bn,
        "short_code": short_code,
        "job_type_bn": job_type_raw,
        "is_govt": is_govt,
        "is_teletalk": is_teletalk,
        "blogger_labels": [],
        "vacancy_bn": vacancy_bn,
        "qualification_bn": qualification_bn,
        "age_limit_bn": age_limit_bn,
        "salary_bn": salary_bn,
        "location_bn": location_bn,
        "fee_bn": "বিজ্ঞপ্তি অনুযায়ী" if is_govt else "প্রযোজ্য নয় / বিজ্ঞপ্তি দেখুন",
        "start_date_bn": start_date_bn,
        "deadline_bn": deadline_bn,
        "apply_method_bn": apply_method_bn,
        "apply_email": apply_email,
        "official_site": official_site or "অফিশিয়াল বিজ্ঞপ্তিতে দেখুন",
        "apply_url": apply_url,
        "intro_paragraph_1": intro_1,
        "intro_paragraph_2": intro_2,
        "posts_breakdown": posts_breakdown,
        "apply_steps_bn": apply_steps_bn,
    }

    if GEMINI_API_KEY:
        prompt = f"""
You are an accurate Bangladeshi job & education portal editor for bdedujob.blogspot.com.
Read the source circular/notice carefully and extract ONLY the real facts from the source.
CRITICAL RULES:
1. NEVER say "গণপ্রজাতন্ত্রী বাংলাদেশ সরকারের আওতাধীন" if the organization is an NGO, Foundation, Private company, Hospital, or Private Bank!
2. Follow the exact post/notice type:
   - If it is a Job Circular: post_title should be "<Bangla Org Name> নিয়োগ বিজ্ঞপ্তি ২০২৬ - <English Org Name> Job Circular 2026"
   - If it is an Exam Result (ফলাফল / রেজাল্ট): post_title should be "<Bangla Org/Exam Name> পরীক্ষার ফলাফল ২০২৬ - <English Name> Exam Result 2026" and job_type_bn should be "পরীক্ষার ফলাফল (Exam Result)"
   - If it is an Exam Routine/Schedule (সময়সূচি / রুটিন / কেন্দ্র তালিকা): post_title should be "<Bangla Org/Exam Name> পরীক্ষার সময়সূচি ২০২৬ - <English Name> Exam Routine 2026" and job_type_bn should be "পরীক্ষার রুটিন ও সময়সূচি (Exam Routine)"
   - If it is an Admission Notice (ভর্তি বিজ্ঞপ্তি): post_title should be "<Bangla Institution Name> ভর্তি বিজ্ঞপ্তি ২০২৬ - <English Name> Admission 2026" and job_type_bn should be "ভর্তি বিজ্ঞপ্তি (Admission Info)"
3. Set "is_teletalk": true ONLY if the application link contains "teletalk.com.bd" or uses 16222 SMS fee payment. Otherwise set "is_teletalk": false.

Return ONLY valid JSON with these keys:
- post_title: Accurate Bangla + English title for 2026
- org_name_bn: Bangla organization/board/institution name (concise, e.g. "বাংলাদেশ পরমাণু কৃষি গবেষণা ইনস্টিটিউট (বিনা)" or "ব্যাংক এশিয়া পিএলসি")
- org_name_en: English organization name
- short_code: Short English acronym (e.g. BPATC, BINA, BPSC, BANKASIA)
- job_type_bn: Exact category in Bangla (e.g. "সরকারি চাকরি (Government Job)", "ব্যাংক জব (Bank Job)", "বেসরকারি চাকরি (Private Job)", "এনজিও চাকরি (NGO Job)", "পরীক্ষার ফলাফল (Exam Result)", "পরীক্ষার রুটিন ও সময়সূচি (Exam Routine)")
- is_govt: boolean (true only for government/public university/board, false for NGO/private/private bank)
- is_teletalk: boolean (true ONLY if applied via *.teletalk.com.bd and 16222 SMS)
- vacancy_bn: Exact vacancy count / passed candidates count in Bangla from the notice
- qualification_bn: Exact educational qualification or post names in Bangla
- age_limit_bn: Exact age limit or notice memo number in Bangla
- salary_bn: Exact salary & benefits or exam details in Bangla
- location_bn: Exact job location or exam center in Bangla
- fee_bn: Exact application fee in Bangla (or "প্রযোজ্য নয়")
- start_date_bn: Publish/start date in Bangla
- deadline_bn: Exact application deadline or exam date in Bangla
- apply_method_bn: Exact method (e.g. "অনলাইনে", "ই-মেইলের মাধ্যমে", "সরাসরি সাক্ষাৎকার", "অফিশিয়াল ওয়েবসাইট থেকে ফলাফল ও নোটিশ ডাউনলোড")
- apply_email: Email address if mentioned, else ""
- official_site: Official website URL
- apply_url: Best application/result/notice URL or mailto: link
- intro_paragraph_1: 3-4 accurate Bangla sentences introducing this specific circular/result/routine based strictly on its real facts.
- intro_paragraph_2: 2-3 accurate Bangla sentences explaining what details are covered below.
- posts_breakdown: List of all job posts or exam schedules from the notice, each object having {{"post_name", "vacancy", "qualification", "salary"}} in Bangla.
- apply_steps_bn: List of 4-5 step-by-step Bangla strings explaining the EXACT application or result-checking/exam instructions from this notice.

Source Title: {raw_title}
Decoded Emails found: {emails}
Parsed Summary Key-Values: {json.dumps(kv, ensure_ascii=False)}
Source Text:
{raw_text[:6000]}
"""
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }).encode("utf-8")

        models = [
            "gemini-flash-lite-latest",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
        ]
        ai_data = None
        for attempt in range(2):
            for model_name in models:
                try:
                    api_url = (
                        f"https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{model_name}:generateContent?key={GEMINI_API_KEY}"
                    )
                    req = urllib.request.Request(api_url, data=payload, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=25) as resp:
                        result = json.loads(resp.read().decode("utf-8"))
                    ai_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    ai_data = json.loads(ai_text)
                    print(f"[AI] Extracted 100% accurate circular details using {model_name}!")
                    break
                except Exception as model_err:
                    print(f"[WARN] Model {model_name} attempt {attempt+1} failed ({model_err})")
                    time.sleep(2)
            if ai_data:
                break
            time.sleep(4)

        if ai_data:
            for k, v in ai_data.items():
                if v is not None and v != "" and v != []:
                    info[k] = v

    return info


def create_and_upload_banner(info: dict) -> str:
    os.makedirs(BANNERS_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", info["short_code"].lower()).strip("-") or "job"
    filename = f"{slug}-job-circular-2026-{int(datetime.now().timestamp())}.png"
    local_path = os.path.join(BANNERS_DIR, filename)

    generate_job_banner(
        org_name_bn=info["org_name_bn"],
        org_short_en=f"{info['short_code']} 2026",
        vacancy_bn=info["vacancy_bn"],
        qualification_bn=info["qualification_bn"],
        deadline_bn=info["deadline_bn"],
        job_type_bn=f"{info.get('job_type_bn', '')} {info.get('post_title', '')}",
        output_path=local_path,
    )

    if IMGBB_API_KEY:
        try:
            with open(local_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
            data = urllib.parse.urlencode({"key": IMGBB_API_KEY, "image": b64_img, "name": slug}).encode("utf-8")
            req = urllib.request.Request("https://api.imgbb.com/1/upload", data=data)
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json["data"]["url"]
        except Exception as e:
            print(f"[WARN] ImgBB upload failed: {e}")

    try:
        with open(local_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
        data = urllib.parse.urlencode({
            "key": "6d207e02198a847aa98d0a2a901485a5",
            "action": "upload",
            "source": b64_img,
            "format": "json",
        }).encode("utf-8")
        req = urllib.request.Request("https://freeimage.host/api/1/upload", data=data, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            cdn_url = res_json.get("image", {}).get("url")
            if cdn_url:
                print(f"[BANNER] Uploaded custom banner to CDN: {cdn_url}")
                return cdn_url
    except Exception as e:
        print(f"[WARN] FreeImage upload failed: {e}")

    gh_repo = os.getenv("GITHUB_REPOSITORY", "")
    gh_branch = os.getenv("GITHUB_REF_NAME", "main")
    if gh_repo:
        return f"https://raw.githubusercontent.com/{gh_repo}/{gh_branch}/generated_banners/{filename}"

    return local_path


def build_bdedujob_post_html(info: dict, banner_url: str, notice_images: list, pdf_links: list = None) -> str:
    pdf_links = pdf_links or []
    org_bn = info["org_name_bn"]
    org_en = info["org_name_en"]
    short_code = info["short_code"].upper()
    title_full = info["post_title"]
    apply_url = info["apply_url"]
    official_site = info["official_site"]
    is_teletalk = bool(info.get("is_teletalk"))
    apply_email = info.get("apply_email", "")
    apply_method_bn = info.get("apply_method_bn", "বিজ্ঞপ্তির নির্দেশনা অনুযায়ী")

    rows_html = ""
    for idx, p in enumerate(info.get("posts_breakdown", []), start=1):
        rows_html += f"""
        <tr>
          <td style="border: 1px solid #cbd5e1; padding: 10px; text-align: center;">{idx}</td>
          <td style="border: 1px solid #cbd5e1; padding: 10px; font-weight: bold;">{p.get('post_name', '')}</td>
          <td style="border: 1px solid #cbd5e1; padding: 10px; text-align: center;">{p.get('vacancy', '')}</td>
          <td style="border: 1px solid #cbd5e1; padding: 10px;">{p.get('qualification', '')}</td>
          <td style="border: 1px solid #cbd5e1; padding: 10px;">{p.get('salary', '')}</td>
        </tr>"""

    notice_imgs_html = ""
    for i, img_url in enumerate(notice_images, start=1):
        alt_txt = f"{title_full} Page {i}"
        notice_imgs_html += f"""
        <div class="separator" style="clear: both; text-align: center; margin: 18px 0;">
          <a href="{img_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;" target="_blank" rel="noopener">
            <img alt="{alt_txt}" title="{alt_txt}" border="0" loading="lazy" src="{img_url}" style="max-width: 100%; height: auto; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);" />
          </a>
        </div>"""

    for idx_pdf, pdf_url in enumerate(pdf_links, start=1):
        encoded_pdf = urllib.parse.quote(pdf_url, safe="")
        notice_imgs_html += f"""
        <div style="margin: 20px 0; text-align: center;">
          <iframe src="https://docs.google.com/viewer?url={encoded_pdf}&amp;embedded=true" style="width: 100%; height: 580px; border: 1px solid #cbd5e1; border-radius: 6px;" frameborder="0" loading="lazy"></iframe>
          <div style="margin-top: 12px;">
            <a href="{pdf_url}" target="_blank" rel="nofollow noopener" style="display: inline-block; background-color: #dc2626; color: #ffffff; font-weight: bold; padding: 10px 24px; border-radius: 6px; text-decoration: none;">
              📥 অফিসিয়াল নোটিশ / ফলাফল PDF ডাউনলোড করুন (Download PDF {idx_pdf})
            </a>
          </div>
        </div>"""

    # আবেদনের বাটন ও পদ্ধতি (বিজ্ঞপ্তিতে যা আছে ঠিক তাই দেখাবে!)
    if apply_email and ("ই-মেইল" in apply_method_bn or "email" in apply_method_bn.lower() or apply_url.startswith("mailto:")):
        btn_href = f"mailto:{apply_email}"
        btn_label = f"📧 ই-মেইলে আবেদন পাঠান ({apply_email})"
    else:
        btn_href = apply_url if apply_url.startswith("http") else SITE_URL
        btn_label = "👉 অনলাইনে আবেদন / বিস্তারিত দেখুন (Apply Now)"

    steps_li_html = "".join(f"<li>{st}</li>" for st in info.get("apply_steps_bn", []))

    if is_teletalk:
        apply_section_html = f"""
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    আবেদন পদ্ধতি (How to Apply {short_code} Job Circular 2026)
  </h2>
  <p style="text-align: justify;">
    আপনি যদি <b>{org_bn}</b> নিয়োগ বিজ্ঞপ্তিটিতে আবেদন করার জন্য একজন যোগ্য ও আগ্রহী প্রার্থী হন, তাহলে দেরি না করে কর্তৃপক্ষের দেওয়া নির্দেশনা অনুযায়ী নির্দিষ্ট সময়ের মধ্যে টেলিটক অনলাইনে (<a href="{btn_href}" rel="nofollow noopener" target="_blank">{btn_href}</a>) মাধ্যমে আবেদন সম্পন্ন করুন।
  </p>
  <ul>
    {steps_li_html}
    <li>নির্ধারিত সাইজে আপনার রঙিন ছবি (300×300 pixel, সর্বোচ্চ 100 KB) এবং স্বাক্ষর (300×80 pixel, সর্বোচ্চ 60 KB) আপলোড করে Submit করুন।</li>
  </ul>
  <h3 style="text-align: center; color: #38761d; font-size: 19px;">
    টেলিটক প্রিপেইড সিমের মাধ্যমে আবেদন ফি পরিশোধের SMS নিয়ম
  </h3>
  <p style="text-align: justify;">
    অনলাইনে আবেদনপত্র পূরণ করলে একটি <b>User ID</b> পাবেন। পরবর্তী ৭২ ঘণ্টার মধ্যে টেলিটক প্রিপেইড সিম থেকে নিচের দুটি SMS পাঠিয়ে আবেদন ফি (<b>{info['fee_bn']}</b>) পরিশোধ করুন:
  </p>
  <p style="text-align: justify;">
    <b>প্রথম SMS:</b> <code>{short_code} &lt;স্পেস&gt; User ID</code> লিখে পাঠিয়ে দিন <b>16222</b> নম্বরে। (উদাহরণ: <b>{short_code} BDEDUJOB</b>)<br/>
    <b>দ্বিতীয় SMS:</b> <code>{short_code} &lt;স্পেস&gt; YES &lt;স্পেস&gt; PIN</code> লিখে পাঠিয়ে দিন <b>16222</b> নম্বরে। (উদাহরণ: <b>{short_code} YES 12345678</b>)
  </p>"""
    else:
        email_box_html = (
            f'<p style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; font-weight: bold;">'
            f'📧 আবেদনের নির্ধারিত ই-মেইল ঠিকানা: <a href="mailto:{apply_email}" style="color: #1d4ed8;">{apply_email}</a></p>'
            if apply_email
            else ""
        )
        apply_section_html = f"""
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    আবেদন করার নিয়মাবলী (How to Apply {org_en} Job Circular 2026)
  </h2>
  <p style="text-align: justify;">
    <b>{org_bn}</b> নিয়োগ বিজ্ঞপ্তি ২০২৬ অনুযায়ী যোগ্য ও আগ্রহী প্রার্থীদের <b>{apply_method_bn}</b> আবেদন সম্পন্ন করতে হবে। আবেদনের ধাপসমূহ নিচে তুলে ধরা হলো:
  </p>
  {email_box_html}
  <ul style="line-height: 1.85;">
    {steps_li_html}
  </ul>"""

    today_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+06:00")
    schema_json = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "NewsArticle",
                "headline": title_full[:110],
                "image": [banner_url] + notice_images[:2],
                "datePublished": today_iso,
                "dateModified": today_iso,
                "author": [{"@type": "Organization", "name": "BD Education & Job Info", "url": SITE_URL}],
                "publisher": {"@type": "Organization", "name": "BD Education & Job Info", "url": SITE_URL},
            },
            {
                "@type": "JobPosting",
                "title": title_full,
                "description": f"{org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ ({org_en} Job Circular 2026) বিস্তারিত তথ্য ও আবেদন পদ্ধতি।",
                "datePosted": datetime.now().strftime("%Y-%m-%d"),
                "employmentType": "FULL_TIME",
                "hiringOrganization": {
                    "@type": "Organization",
                    "name": org_bn,
                    "sameAs": official_site if official_site.startswith("http") else SITE_URL,
                },
                "jobLocation": {
                    "@type": "Place",
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": info.get("location_bn", "Dhaka"),
                        "addressCountry": "BD",
                    },
                },
            },
        ],
    }
    schema_script = f'<script type="application/ld+json">{json.dumps(schema_json, ensure_ascii=False)}</script>'

    email_li = (
        f'<li><b>আবেদনের ই-মেইল (Application Email):</b> <span style="color: #1d4ed8; font-weight: bold;">{apply_email}</span></li>'
        if apply_email
        else ""
    )

    html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <!-- ১. অটো-জেনারেটেড থাম্বনেইল ব্যানার ইমেজ -->
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 20px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{title_full}" title="{title_full}" border="0" data-original-height="630" data-original-width="1200" loading="lazy" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 8px;" />
    </a>
  </div>

  <!-- ২. ভূমিকা -->
  <p style="text-align: justify;">
    <span style="color: #38761d;"><b>{org_en} Job Circular 2026:</b></span>
    {info['intro_paragraph_1']}
  </p>

  <p style="text-align: justify;">
    {info['intro_paragraph_2']}
  </p>

  <!-- ৩. অফিসিয়াল অ্যাপ ও ওয়েবসাইট প্রমোশন বক্স -->
  <div style="background: #f0fdf4; border-left: 4px solid #38761d; padding: 14px 18px; margin: 18px 0; border-radius: 6px; text-align: center;">
    <p style="margin: 0 0 8px 0; font-weight: bold;">
      <a href="{PLAY_STORE_URL}" rel="nofollow noopener" target="_blank" style="color: #15803d; text-decoration: underline;">
        📱 একটি বিজ্ঞপ্তিও মিস হবে না! আমাদের অফিসিয়াল জব সার্কুলার অ্যাপটি ডাউনলোড করে নিন।
      </a>
    </p>
    <p style="margin: 0; text-align: justify; font-size: 15px;">
      সরকারি ও বেসরকারি সব ধরনের চাকরির খবর সবার আগে পেতে ভিজিট করুন আমাদের ওয়েবসাইটে
      <a href="{SITE_URL}" style="color: #38761d; font-weight: bold;">{SITE_DISPLAY}</a>
      এবং <a href="{PLAY_STORE_URL}" rel="nofollow noopener" target="_blank" style="color: #38761d; font-weight: bold;">প্লে-স্টোর লিংক</a>
      থেকে আমাদের অফিসিয়াল অ্যাপটি ইনস্টল করে রাখুন।
    </p>
  </div>

  <!-- ৪. কাজের সংক্ষিপ্ত বিবরণ (Job Summary - বিজ্ঞপ্তির হুবহু তথ্য) -->
  <h2 style="text-align: center; color: #38761d; font-size: 22px; border-bottom: 2px solid #38761d; padding-bottom: 6px; margin-top: 26px;">
    এক নজরে {org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ (Job Summary)
  </h2>

  <ul style="line-height: 1.9;">
    <li><b>প্রতিষ্ঠানের নাম (Organization Name):</b> {org_bn} ({org_en})</li>
    <li><b>চাকরির ধরণ (Type of Job):</b> {info['job_type_bn']}</li>
    <li><b>মোট শূন্যপদ / ক্যাটাগরি (Vacancy):</b> {info['vacancy_bn']}</li>
    <li><b>শিক্ষাগত যোগ্যতা (Qualification):</b> {info['qualification_bn']}</li>
    <li><b>বয়সসীমা (Age Limit):</b> {info['age_limit_bn']}</li>
    <li><b>বেতন ও সুযোগ-সুবিধা (Salary &amp; Benefits):</b> {info['salary_bn']}</li>
    <li><b>কর্মস্থল (Job Location):</b> {info.get('location_bn', 'বিজ্ঞপ্তি অনুযায়ী')}</li>
    <li><b>আবেদন পদ্ধতি (Application Method):</b> {apply_method_bn}</li>
    {email_li}
    <li><b>আবেদন ফি (Application Fee):</b> {info['fee_bn']}</li>
    <li><b>প্রকাশের / শুরুর তারিখ:</b> {info['start_date_bn']}</li>
    <li><b>আবেদনের শেষ তারিখ (Deadline):</b> <span style="color: #dc2626; font-weight: bold;">{info['deadline_bn']}</span></li>
    <li><b>অফিসিয়াল ওয়েবসাইট (Official Website):</b> <span style="color: #0000ee;"><b><u>{official_site}</u></b></span></li>
  </ul>

  <!-- ৫. পদের নাম, পদসংখ্যা ও যোগ্যতার বিস্তারিত ছক -->
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    {org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬: পদভিত্তিক যোগ্যতা ও বেতন
  </h2>
  <p style="text-align: justify;">
    {org_bn}-এর প্রকাশিত অফিশিয়াল বিজ্ঞপ্তি অনুযায়ী কোন পদে কতজন নিয়োগ দেওয়া হবে এবং আবেদনের জন্য কী কী শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা প্রয়োজন, তার বিস্তারিত বিবরণ নিচের ছকে দেওয়া হলো:
  </p>

  <div style="overflow-x: auto; margin: 16px 0;">
    <table style="width: 100%; border-collapse: collapse; font-size: 15px;">
      <thead>
        <tr style="background-color: #38761d; color: #ffffff;">
          <th style="border: 1px solid #cbd5e1; padding: 10px;">ক্রমিক</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">পদের নাম</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">পদসংখ্যা</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">বেতন ও সুযোগ-সুবিধা</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <!-- ৬. আবেদনের সময়সীমা ও অফিসিয়াল বিজ্ঞপ্তির ছবি -->
  <div style="background: #fffbeb; border: 1px solid #f59e0b; padding: 14px 18px; border-radius: 6px; margin: 22px 0;">
    <div><b>আবেদন পদ্ধতি:</b> {apply_method_bn}</div>
    <div><b>আবেদনের শেষ সময়:</b> <span style="color: #b91c1c; font-weight: bold;">{info['deadline_bn']}</span></div>
  </div>

  <h3 style="color: #38761d; font-size: 19px; margin-top: 24px;">
    বিস্তারিত জানতে অফিসিয়াল নিয়োগ বিজ্ঞপ্তি (Official Notice) দেখুন:
  </h3>

  {notice_imgs_html}

  <!-- ৭. আবেদন করার বাটন -->
  <div style="text-align: center; margin: 26px 0;">
    <a href="{btn_href}" rel="nofollow noopener" target="_blank" style="display: inline-block; background-color: #38761d; color: #ffffff; font-size: 20px; font-weight: bold; padding: 12px 34px; border-radius: 30px; text-decoration: none; box-shadow: 0 4px 10px rgba(56,118,29,0.3);">
      {btn_label}
    </a>
  </div>

  <!-- ৮. বিজ্ঞপ্তি অনুযায়ী সঠিক আবেদন পদ্ধতি -->
  {apply_section_html}

  <!-- ৯. নিয়োগ পরীক্ষা ও ইন্টারভিউ সংক্রান্ত তথ্য -->
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    নিয়োগ পরীক্ষা ও ইন্টারভিউ সংক্রান্ত তথ্য
  </h2>
  <p style="text-align: justify;">
    <b>{org_bn}</b>-এ আবেদনপত্র গ্রহণের পর প্রাথমিক বাছাই (Shortlisting) করা হবে। যোগ্য বিবেচিত প্রার্থীদের মোবাইল SMS অথবা ই-মেইলের মাধ্যমে লিখিত পরীক্ষা বা মৌখিক পরীক্ষার (Interview) তারিখ, সময় ও স্থান জানানো হবে। এছাড়াও নিয়মিত আপডেট আমাদের জব পোর্টাল <a href="{SITE_URL}">{SITE_DISPLAY}</a>-এ প্রকাশ করা হবে।
  </p>

  <!-- ১০. সচরাচর জিজ্ঞাসিত প্রশ্নোত্তর (FAQ) -->
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    সচরাচর জিজ্ঞাসিত প্রশ্নোত্তর (FAQ)
  </h2>
  <p style="text-align: justify;">
    <b>প্রশ্ন ১: {org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬-এ আবেদনের শেষ তারিখ কবে?</b><br/>
    উত্তর: আগ্রহী প্রার্থীরা আগামী <b>{info['deadline_bn']}</b> পর্যন্ত আবেদন করতে পারবেন।
  </p>
  <p style="text-align: justify;">
    <b>প্রশ্ন ২: এই নিয়োগে আবেদনের জন্য শিক্ষাগত যোগ্যতা কী প্রয়োজন?</b><br/>
    উত্তর: পদভেদে <b>{info['qualification_bn']}</b> যোগ্যতাসম্পন্ন প্রার্থীরা আবেদন করতে পারবেন।
  </p>
  <p style="text-align: justify;">
    <b>প্রশ্ন ৩: কীভাবে আবেদন করতে হবে?</b><br/>
    উত্তর: বিজ্ঞপ্তির নির্দেশনা অনুযায়ী প্রার্থীদের <b>{apply_method_bn}</b> আবেদন সম্পন্ন করতে হবে।
  </p>

  <!-- ১১. সতর্কীকরণ বিজ্ঞপ্তি ও ট্যাগ -->
  <div style="background: #fef2f2; border: 1px solid #f87171; padding: 14px 18px; border-radius: 6px; margin-top: 26px;">
    <p style="text-align: center; margin: 0 0 6px 0;">
      <b><span style="color: red; font-size: medium;">সতর্কীকরণীয় বিজ্ঞপ্তি:</span></b>
    </p>
    <p style="text-align: justify; margin: 0; font-size: 14.5px;">
      চাকরি আবেদনকারী প্রার্থীদের জানানো যাচ্ছে যে, অনেক প্রতিষ্ঠান আকর্ষণীয় বেতন এবং লোভনীয় অফার দিয়ে বিজ্ঞাপন দিয়ে থাকে। এই সকল বিজ্ঞাপন ভালোভাবে বুঝেশুনে নিজ দায়িত্বে আবেদন করবেন। চাকরির ক্ষেত্রে টাকা-পয়সা লেনদেন আপনার নিজ দায়িত্বে করবেন; এক্ষেত্রে প্রতারিত হলে <a href="{SITE_URL}">{SITE_DISPLAY}</a> কর্তৃপক্ষ দায়ী থাকবে না। আমাদের সাইট ভিজিট করার জন্য ধন্যবাদ।
    </p>
  </div>

  <p style="text-align: justify; margin-top: 18px; font-size: 14px; color: #475569;">
    <b><span style="color: #38761d;"><u>Post Related Tag:</u></span></b>
    <i>{org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬, {org_bn} নতুন চাকরি, {org_en} Job Circular 2026, {short_code} Job Circular 2026, bd job circular 2026 today, নতুন নিয়োগ বিজ্ঞপ্তি ২০২৬, bdedujob.</i>
  </p>
  {schema_script}
</div>"""
    return html


def get_blogger_access_token() -> str:
    token_url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode({
        "client_id": BLOGGER_CLIENT_ID,
        "client_secret": BLOGGER_CLIENT_SECRET,
        "refresh_token": BLOGGER_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode("utf-8")
    req = urllib.request.Request(token_url, data=payload)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["access_token"]


def ping_google_websub_hub():
    hub_url = "https://pubsubhubbub.appspot.com/"
    for topic in [
        f"{SITE_URL}/feeds/posts/default",
        f"{SITE_URL}/feeds/posts/default?alt=rss",
    ]:
        try:
            data = urllib.parse.urlencode({"hub.mode": "publish", "hub.url": topic}).encode("utf-8")
            req = urllib.request.Request(hub_url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"[GOOGLE PING] Notified Google Hub for {topic} (Status: {resp.status})")
        except Exception as e:
            print(f"[WARN] Google Hub ping failed: {e}")


def publish_to_blogger(title: str, html_content: str, labels: list, is_draft: bool = False) -> dict:
    access_token = get_blogger_access_token()
    api_url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}/posts/?isDraft={'true' if is_draft else 'false'}"
    body = json.dumps({
        "kind": "blogger#post",
        "blog": {"id": BLOGGER_BLOG_ID},
        "title": title,
        "content": html_content,
        "labels": labels,
    }).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    posted_urls = load_posted_jobs()
    published_count = 0

    # সব ক্যাটাগরির পোস্ট যেন পালাক্রমে (Round-Robin) সমানভাবে পাবলিশ হয়
    offset = len(posted_urls) % len(JOB_SOURCES)
    rotated_sources = JOB_SOURCES[offset:] + JOB_SOURCES[:offset]

    for source in rotated_sources:
        if published_count >= MAX_POSTS_PER_RUN:
            break
        print(f"[INFO] Checking source: {source['name']} ({source['feed_url']})")
        try:
            items = fetch_rss_items(source["feed_url"])
        except Exception as e:
            print(f"[ERROR] Failed to fetch feed {source['feed_url']}: {e}")
            continue

        for item in items:
            if published_count >= MAX_POSTS_PER_RUN:
                break
            link = item["link"]
            if not link or link in posted_urls:
                continue

            print(f"[NEW JOB FOUND] {item['title']} -> {link}")
            try:
                scraped = scrape_job_details(link)
                info = extract_structured_job_info(item["title"], scraped)
                banner_url = create_and_upload_banner(info)
                html_post = build_bdedujob_post_html(
                    info,
                    banner_url,
                    scraped["notice_images"],
                    scraped.get("pdf_links", []),
                )
                final_labels = determine_blogger_labels(
                    item["title"],
                    item.get("categories", []),
                    info.get("blogger_labels", []),
                    info.get("job_type_bn", ""),
                    source.get("default_label", ""),
                )

                if BLOGGER_BLOG_ID and BLOGGER_REFRESH_TOKEN:
                    res = publish_to_blogger(
                        title=info["post_title"],
                        html_content=html_post,
                        labels=final_labels,
                        is_draft=BLOGGER_IS_DRAFT,
                    )
                    print(f"[SUCCESS] Published to Blogger! Post URL: {res.get('url')}")
                    ping_google_websub_hub()
                    save_posted_job(link)
                    posted_urls.append(link)
                    published_count += 1
                    time.sleep(4)
                    # একটি ক্যাটাগরি থেকে ১টি পোস্ট করার পর পরবর্তী ক্যাটাগরিতে যাবে
                    break
                else:
                    preview_file = os.path.join(BASE_DIR, "sample_post_preview.html")
                    with open(preview_file, "w", encoding="utf-8") as f:
                        f.write(html_post)
                    print(f"[PREVIEW] Saved sample SEO post HTML to: {preview_file}")
                    published_count += 1
                    break
            except Exception as e:
                print(f"[ERROR] Failed processing {link}: {e}")


if __name__ == "__main__":
    main()
