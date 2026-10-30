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

from banner_generator import generate_job_banner, generate_bcs_banner, generate_job_solution_banner

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
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "104790438452242")
if FB_PAGE_ID == "100067891540585":
    # পুরোনো ভুল Page ID — workflow-এ থেকে গেলেও সঠিক পেজই ব্যবহার হবে
    FB_PAGE_ID = "104790438452242"
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
MAX_POSTS_PER_RUN = 2

SITE_URL = "https://bdedujob.blogspot.com"
SITE_DISPLAY = "www.bdedujob.blogspot.com"
PLAY_STORE_URL = os.getenv("PLAY_STORE_URL", "https://bdedujob.blogspot.com/p/official-mobile-app.html")

ALLOWED_BLOGGER_LABELS = [
    "All Jobs",
    "BCS",
    "BCS Exam Question Solution",
    "Bank Jobs",
    "Current Affairs",
    "EXAM INFO",
    "Edcation",
    "Exam Routine",
    "Govt Jobs",
    "Honour's",
    "Hsc",
    "Job Solution",
    "Privet Jobs",
    "QUESTION SOLUTION",
    "Result",
    "SSC",
    "Saptahik Chakrir Khobor",
    "Saptahik Job Paper",
    "all",
    "exam result",
    "job",
    "nu",
    "pdf",
    "pdf Zone",
    "saptahik chakrir Songbad",
    "saptahik chakrir dakh",
]

EDUCATION_SOURCES = [
    {
        "name": "National University (NU Routine, Result & Notice)",
        "feed_url": "https://eduresultbd.com/category/national-university/feed/",
        "edu_type": "জাতীয় বিশ্ববিদ্যালয় নোটিশ",
    },
    {
        "name": "LekhaporaBD (NU Routine, Admission & Education Notice)",
        "feed_url": "https://lekhaporabd.net/feed/",
        "edu_type": "পরীক্ষার সময়সূচি ও রুটিন",
    },
    {
        "name": "BDGovtJob (Job Exam Result & Viva Schedule Notice)",
        "feed_url": "https://bdgovtjob.net/category/notice/feed/",
        "edu_type": "পরীক্ষার ফলাফল",
    },
    {
        "name": "BDGovtJob (Job Exam Date & Viva Schedule)",
        "feed_url": "https://bdgovtjob.net/category/exam-date/feed/",
        "edu_type": "পরীক্ষার সময়সূচি",
    },
    {
        "name": "ProsnoSomadhan (Recruitment & Board Exam Results)",
        "feed_url": "https://prosnosomadhan.com/category/result/feed/",
        "edu_type": "পরীক্ষার ফলাফল",
    },
    {
        "name": "University & College Admission Circulars",
        "feed_url": "https://eduresultbd.com/category/admission-circular/feed/",
        "edu_type": "ভর্তি বিজ্ঞপ্তি",
    },
    {
        "name": "Education Board & University Exam Routine",
        "feed_url": "https://eduresultbd.com/category/exam-routine/feed/",
        "edu_type": "পরীক্ষার সময়সূচি",
    },
    {
        "name": "SSC / HSC & University Scholarship Circulars",
        "feed_url": "https://eduresultbd.com/category/scholarship/feed/",
        "edu_type": "শিক্ষাবৃত্তি বিজ্ঞপ্তি",
    },
    {
        "name": "Education Board & NU Exam Results",
        "feed_url": "https://examresultbd.com/feed/",
        "edu_type": "পরীক্ষার ফলাফল",
    },
]

JOB_SOLUTION_QUEUE = [
    {
        "org_bn": "মন্ত্রিপরিষদ বিভাগ (Cabinet Division)",
        "org_short": "cabinet-division",
        "post_bn": "অফিস সহায়ক",
        "exam_date": "২৮ আগস্ট ২০২৬",
        "marks": "৭০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/cabinet-division-question-solution-2026-office-support-staff",
    },
    {
        "org_bn": "বাংলাদেশ কর্মচারী কল্যাণ বোর্ড (BKKB)",
        "org_short": "bkkb-office-assistant",
        "post_bn": "অফিস সহকারী কাম কম্পিউটার মুদ্রাক্ষরিক",
        "exam_date": "২৯ আগস্ট ২০২৬",
        "marks": "১০০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/bkkb-question-solution-2026-office-assistant-computer-typist-1-post",
    },
    {
        "org_bn": "জনশক্তি কর্মসংস্থান ও প্রশিক্ষণ ব্যুরো (BMET)",
        "org_short": "bmet-assistant-director",
        "post_bn": "সহকারী পরিচালক",
        "exam_date": "২৫ আগস্ট ২০২৬",
        "marks": "১০০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/bmet-assistant-director-question-solution-2026",
    },
    {
        "org_bn": "স্বাস্থ্য ও পরিবার কল্যাণ মন্ত্রণালয় (PSC)",
        "org_short": "psc-social-welfare-officer",
        "post_bn": "সমাজ কল্যাণ কর্মকর্তা",
        "exam_date": "০২ সেপ্টেম্বর ২০২৬",
        "marks": "১০০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/social-welfare-officer-question-solution-2026",
    },
    {
        "org_bn": "গ্যাস ট্রান্সমিশন কোম্পানি লিমিটেড (GTCL)",
        "org_short": "gtcl-receptionist",
        "post_bn": "রিসিপশনিস্ট",
        "exam_date": "২২ আগস্ট ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/Non-Cadre-question-bank/gtcl-mcq-question-solution-2026",
    },
    {
        "org_bn": "স্বাস্থ্য ও পরিবার কল্যাণ মন্ত্রণালয় (MOHFW)",
        "org_short": "mohfw-assistant-engineer",
        "post_bn": "সহকারী প্রকৌশলী (সিভিল)",
        "exam_date": "২০২৬",
        "marks": "১০০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/Non-Cadre-question-bank/mohfw-assistant-engineer-civil-question-solution-2026",
    },
    {
        "org_bn": "বাংলাদেশ ব্যাংক (Bangladesh Bank)",
        "org_short": "bangladesh-bank-ad",
        "post_bn": "সহকারী পরিচালক (AD)",
        "exam_date": "১৭ জুলাই ২০২৬",
        "marks": "১০০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/Bank-question-bank/bangladesh-bank-assistant-director-question-solution-2026",
    },
    {
        "org_bn": "সমন্বিত ৭ ব্যাংক (Combined 7 Bank)",
        "org_short": "combined-7-bank-cash",
        "post_bn": "অফিসার (ক্যাশ)",
        "exam_date": "০৩ জুলাই ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/Bank-question-bank/combined-7-bank-officer-cash-question-solution-2026",
    },
    {
        "org_bn": "বাংলাদেশ নৌবাহিনী (BNDCP)",
        "org_short": "bndcp-higher-assistant",
        "post_bn": "বেসামরিক উচ্চমান সহকারী",
        "exam_date": "আগস্ট ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/bndcp-higher-assistant-question-mcq-solution-2026",
    },
    {
        "org_bn": "বাংলাদেশ পরমাণু শক্তি কমিশন (BAEC)",
        "org_short": "baec-lab-attendant",
        "post_bn": "ল্যাবরেটরি এটেনডেন্ট",
        "exam_date": "৩১ জুলাই ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/baec-question-mcq-solution-2026",
    },
    {
        "org_bn": "প্রতিরক্ষা মন্ত্রণালয় (MOD)",
        "org_short": "mod-storeman",
        "post_bn": "বেসামরিক স্টোরম্যান",
        "exam_date": "০৭ আগস্ট ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/mod-storeman-question-mcq-solution-2026",
    },
    {
        "org_bn": "পরিসংখ্যান ও তথ্য ব্যবস্থাপনা বিভাগ (SID)",
        "org_short": "sid-office-sohayok",
        "post_bn": "অফিস সহায়ক",
        "exam_date": "২০২৬",
        "marks": "৪০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/sid-question-solution-2026-office-sohayok",
    },
    {
        "org_bn": "যুব উন্নয়ন অধিদপ্তর (DYD)",
        "org_short": "dyd-office-sohayok",
        "post_bn": "অফিস সহায়ক",
        "exam_date": "২৭ জুন ২০২৬",
        "marks": "৭০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/11-20-Grade-question-bank/dyd-office-sohayok-question-solution-2026",
    },
    {
        "org_bn": "বাংলাদেশ ক্ষুদ্র ও কুটির শিল্প কর্পোরেশন (BSCIC)",
        "org_short": "bscic-promotion-officer",
        "post_bn": "প্রমোশন অফিসার",
        "exam_date": "১৯ জুন ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/Non-Cadre-question-bank/bscic-promotion-officer-mcq-question-solution-2026",
    },
    {
        "org_bn": "৮ম এনটিআরসিএ (8th NTRCA)",
        "org_short": "8th-ntrca-head-teacher",
        "post_bn": "প্রধান শিক্ষক",
        "exam_date": "১৮ এপ্রিল ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/NTRCA-question-bank/8th-ntrca-head-teacher-question-solution-2026",
    },
    {
        "org_bn": "৮ম এনটিআরসিএ (8th NTRCA)",
        "org_short": "8th-ntrca-principal",
        "post_bn": "অধ্যক্ষ",
        "exam_date": "১৮ এপ্রিল ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/NTRCA-question-bank/8th-ntrca-principal-question-solution-2026",
    },
    {
        "org_bn": "৮ম এনটিআরসিএ (8th NTRCA)",
        "org_short": "8th-ntrca-super",
        "post_bn": "সুপার (দাখিল মাদ্রাসা)",
        "exam_date": "১৮ এপ্রিল ২০২৬",
        "marks": "৮০",
        "time": "৬০ মিনিট",
        "url": "https://biddabari.com/NTRCA-question-bank/8th-ntrca-super-dakhil-madrasha-question-solution-2026",
    },
]

BCS_QUESTION_BANK_QUEUE = [
    {"num_bn": "২৪", "num_en": "24th", "slug": "24th-BCS-Question-Solution-Biddabari"},
    {"num_bn": "২৫", "num_en": "25th", "slug": "25th-BCS-Question-Solution-Biddabari"},
    {"num_bn": "২৬", "num_en": "26th", "slug": "26th-BCS-Question-Solution-Biddabari"},
    {"num_bn": "২৭", "num_en": "27th", "slug": "27th-bcs-question-solution"},
    {"num_bn": "২৮", "num_en": "28th", "slug": "28th-bcs-question-solution-pdf"},
    {"num_bn": "২৯", "num_en": "29th", "slug": "29th-bcs-question-solution-pdf"},
    {"num_bn": "৩০", "num_en": "30th", "slug": "30th-bcs-question-solution"},
    {"num_bn": "৩১", "num_en": "31th", "slug": "31th-bcs-question-solution"},
    {"num_bn": "৩২", "num_en": "32th", "slug": "32nd-bcs-question-solution-pdf"},
    {"num_bn": "৩৩", "num_en": "33th", "slug": "cevta-job-circular-2026"},
    {"num_bn": "৩৪", "num_en": "34th", "slug": "34th-bcs-question-solution-pdf"},
    {"num_bn": "৩৫", "num_en": "35th", "slug": "35th-bcs-question-solution-pdf"},
    {"num_bn": "৩৬", "num_en": "36th", "slug": "36th-bcs-question-solution-2026"},
    {"num_bn": "৩৭", "num_en": "37th", "slug": "37th-bcs-question-solution-pdf-download"},
    {"num_bn": "৩৮", "num_en": "38th", "slug": "38th-bcs-question-solution-pdf-download"},
    {"num_bn": "৩৯", "num_en": "39th", "slug": "39th-bcs-question-solution"},
    {"num_bn": "৪০", "num_en": "40th", "slug": "40th-bcs-question-solution"},
    {"num_bn": "৪১", "num_en": "41th", "slug": "41th-bcs-question-solution-pdf"},
    {"num_bn": "৪২", "num_en": "42th", "slug": "42th-bcs-question-solution-pdf-bcs-preliminary-question-solve-biddabari"},
    {"num_bn": "৪৩", "num_en": "43th", "slug": "43th-bcs-question-solution"},
    {"num_bn": "৪৪", "num_en": "44th", "slug": "44th-bcs-question-solution-pdf"},
    {"num_bn": "৪৫", "num_en": "45th", "slug": "45th-bcs-question-solution-pdf"},
    {"num_bn": "৪৬", "num_en": "46th", "slug": "46th-bcs-question-solution"},
    {"num_bn": "৪৭", "num_en": "47th", "slug": "47th-bcs-question-solution"},
    {"num_bn": "৪৮", "num_en": "48th", "slug": "48th-bcs-question-solution-pdf"},
    {"num_bn": "৪৯", "num_en": "49th", "slug": "49th-bcs-question-solution"},
    {"num_bn": "৫০", "num_en": "50th", "slug": "50th-BCS-Question-Solution"},
    {"num_bn": "১৮ (বিশেষ)", "num_en": "18th Special", "slug": "18th-special-bcs-question-solution"},
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
        "name": "BD Govt Job (Defence Jobs)",
        "feed_url": "https://bdgovtjob.net/category/defence-job-circular/feed/",
        "default_label": "Govt Jobs",
    },
    {
        "name": "BD Govt Job (Group of Company Jobs)",
        "feed_url": "https://bdgovtjob.net/category/group-of-company-job-circular/feed/",
        "default_label": "Privet Jobs",
    },
    {
        "name": "BD Govt Job (Pharmaceuticals Jobs)",
        "feed_url": "https://bdgovtjob.net/category/pharmaceuticals-job-circular/feed/",
        "default_label": "Privet Jobs",
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
    if any(k in combined for k in ["বেসরকারি", "private", "privet", "ngo", "এনজিও", "ফাউন্ডেশন", "foundation", "কোম্পানি", "লিমিটেড", "ltd", "group", "হাসপাতাল", "ফার্মাসিউটিক্যাল", "নর্থ সাউথ", "ইস্ট ওয়েস্ট", "ইউনিভার্সিটি"]):
        if not any(g in combined for g in ["সরকারি", "পাবলিক", "বিজ্ঞান ও প্রযুক্তি", "প্রকৌশল"]):
            labels.add("Privet Jobs")
            if "Saptahik Job Paper" not in labels:
                labels.discard("Govt Jobs")
    if any(k in combined for k in ["সরকারি", "govt", "government", "মন্ত্রণালয়", "অধিদপ্তর", "বিশ্ববিদ্যালয়", "বিশ্ববিদ্যালয়", "কর্পোরেশন", "বোর্ড", "কমিশন", "সিভিল সার্জন", "জেলা প্রশাসক", "বিপিএটিসি", "বিকেএসপি", "ইনস্টিটিউট", "কর অঞ্চল"]):
        if "বেসরকারি" not in combined and "এনজিও" not in combined and "ফাউন্ডেশন" not in combined and "Privet Jobs" not in labels:
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


BUILTIN_POSTED_URLS = [
    "https://bdgovtjob.net/cpa-job-circular/",
    "https://bdgovtjob.net/tax9-dhaka-job-circular/",
    "https://bdgovtjob.net/bangladesh-palli-bidyut-samity-job-circular/",
    "https://bdgovtjob.net/kuet-job-circular/",
    "https://bdgovtjob.net/ab-power-engineering-limited-job-circular/",
    "https://bdgovtjob.net/cantonment-public-school-and-college-job-circular/",
    "https://bdgovtjob.net/ibn-sina-pharmaceutical-job-circular/",
    "https://bdgovtjob.net/bridge-pharmaceuticals-job-circular/",
    "saptahik-chakrir-khobor#2026-10-23",
    "saptahik-chakrir-dak#2026-10-23",
    "saptahik-chakrir-songbad#2026-10-23",
    "prothom-alo-weekly-job-newspaper#2026-10-23",
    "https://prosnosomadhan.com/bina-exam-question-solution/",
    "https://bdgovtjob.net/bpatc-job-circular/",
    "https://bdgovtjob.net/saptahik-chakrir-khobor/",
    "https://bdgovtjob.net/bangladesh-krira-shikkha-protishtan-bksp-job-circular/",
    "https://bdgovtjob.net/rajshahi-university-job-circular/",
    "https://bdgovtjob.net/nstu-job-circular/",
    "https://bdgovtjob.net/meherpur-university-job-circular/",
    "https://bdgovtjob.net/ad-din-foundation-job-circular/",
    "https://bdgovtjob.net/popular-pharmaceuticals-ltd-job-circular/",
    "https://bdgovtjob.net/drug-international-limited-job-circular/",
    "https://ejobscircular.com/tax-zone-2-chittagong-job-circular/",
    "https://kfplanet.com/hsc-center-list/",
    "https://bdgovtjob.net/bank-asia-limited-job-circular/",
    "https://bdgovtjob.net/bina-written-exam-result-notice/",
    "https://bdgovtjob.net/bpsc-written-examination-notice/",
    "https://bdgovtjob.net/taxzone20-results-notice/",
    "https://bdgovtjob.net/brac-bank-limited-job-circular/",
    "https://bdgovtjob.net/school-and-college-job-circular/",
    "https://bdgovtjob.net/sme-foundation-job-circular/",
    "https://ejobscircular.com/bangladesh-bank-job-circular/",
    "https://ejobscircular.com/north-west-power-generation-job-circular/",
    "https://bdgovtjob.net/community-bank-bangladesh-limited-job-circular/",
    "https://bdgovtjob.net/bangladesh-army-civilian-job-circular/",
    "https://bdgovtjob.net/square-group-job-circular/",
    "https://bdgovtjob.net/aci-limited-job-circular/",
    "https://bdgovtjob.net/bangladesh-ansar-vdp-job-circular/",
    "https://bdgovtjob.net/meghna-group-job-circular/",
    "https://bdgovtjob.net/bangladesh-police-job-circular/",
    "https://bdgovtjob.net/tmss-ngo-job-circular/",
    "https://bdgovtjob.net/mist-job-circular/",
    "https://biddabari.com/bcs-question-bank/24th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/25th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/26th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/27th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/28th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/29th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/30th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/31th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/32th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/33th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/34th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/35th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/36th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/37th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/38th-BCS-Question-Solution-Biddabari",
    "https://biddabari.com/bcs-question-bank/50th-BCS-Question-Solution",
    "https://prosnosomadhan.com/dyd-assistant-upazila-youth-development-officer-question-solution/",
    "https://prosnosomadhan.com/dc-office-coxsbazar-question-solution/",
    "https://prosnosomadhan.com/dyd-upazila-youth-development-officer-question-solution/",
    "https://prosnosomadhan.com/npa-exam-question-solution/",
    "https://biddabari.com/11-20-Grade-question-bank/cabinet-division-question-solution-2026-office-support-staff",
    "https://biddabari.com/11-20-Grade-question-bank/bkkb-question-solution-2026-office-assistant",
    "https://biddabari.com/Non-Cadre-question-bank/bmet-assistant-director-question-solution-2026",
    "https://eduresultbd.com/dhaka-university-masters-admission/",
    "https://eduresultbd.com/nu-degree-exam-routine/",
    "https://examresultbd.com/preliminary-to-masters-result/",
    "https://eduresultbd.com/brac-medhabikash-scholarship/",
    "https://bdgovtjob.net/gazipur-agricultural-university-job-circular/",
    "https://eduresultbd.com/baf-shaheen-college-admission/",
    "https://bdgovtjob.net/sbac-bank-job-circular/",
    "https://bdgovtjob.net/tax-zone-6-dhaka-job-circular/",
    "https://bdgovtjob.net/nesco-job-circular/",
    "https://bdgovtjob.net/jamalpur-science-and-technology-university-job-circular/",
    "https://bdgovtjob.net/east-west-university-job-circular/",
    "https://bdgovtjob.net/north-south-university-job-circular/",
    "https://bdgovtjob.net/jahangirnagar-university-job-circular/",
    "https://biddabari.com/bcs-question-bank/43th-bcs-question-solution",
    "https://biddabari.com/bcs-question-bank/44th-bcs-question-solution",
    "https://biddabari.com/bcs-question-bank/45th-BCS-Question-Solution",
    "https://biddabari.com/bcs-question-bank/46th-BCS-Preli-Question-Solution",
    "https://biddabari.com/bcs-question-bank/47th-BCS-Question-Solution",
    "https://bdgovtjob.net/bpsc-non-cadre-job-circular/",
    "https://bdgovtjob.net/bpsc-job-circular/",
    "https://bdgovtjob.net/haj-office-job-circular/",
    "https://bdgovtjob.net/nib-job-circular/",
    "https://bdgovtjob.net/bangladesh-petroleum-corporation-bpc-job-circular/",
    "https://bdgovtjob.net/bangladesh-maritime-university-job-circular/",
    "https://bdgovtjob.net/bangladesh-medical-college-job-circular/",
    "https://bdgovtjob.net/criminal-investigation-department-cid-job-circular/",
    "https://bdgovtjob.net/healthcare-pharmaceuticals-job-circular/",
    "https://bdgovtjob.net/eastern-bank-limited-job-circular/",
    "https://bdgovtjob.net/pkb-recruitment-notice/",
    "https://bdgovtjob.net/bangladesh-navy-civilian-job-circular/",
    "https://bdgovtjob.net/jamuna-group-limited-job-circular/",
    "https://bdgovtjob.net/abul-khair-group-job-circular/",
    "https://bdgovtjob.net/square-pharmaceuticals-limited-job-circular/",
    "https://biddabari.com/bcs-question-bank/48th-bcs-question-solution-pdf",
    "https://biddabari.com/bcs-question-bank/49th-bcs-question-solution",
    "https://bdgovtjob.net/sonali-bank-limited-job-circular/",
    "https://bdgovtjob.net/sp-sherpur-job-circular/",
    "https://bdgovtjob.net/mutual-trust-bank-limited-job-circular/",
    "https://bdgovtjob.net/aiub-job-circular/",
    "https://bdgovtjob.net/brac-university-job-circular/",
    "https://bdgovtjob.net/meghna-life-insurance-job-circular/",
    "https://lekhaporabd.net/archives/49664",
    "https://lekhaporabd.net/archives/49497",
    "https://lekhaporabd.net/archives/49666",
    "https://lekhaporabd.net/archives/49673",
    "https://bdgovtjob.net/plandiv-viva-voce-notice/",
    "https://bdgovtjob.net/biman-results-notice/",
    "https://bdgovtjob.net/egcb-results-notice/",
    "https://prosnosomadhan.com/dlrs-janch-mohrar-result/",
    "https://prosnosomadhan.com/dlrs-janch-mohrar-exam-result/",
    "https://prosnosomadhan.com/dlrs-office-sohayok-result/",
    "https://prosnosomadhan.com/bjs-previous-exam-question-solution/",
    "https://prosnosomadhan.com/bjs-previous-year-question-answer/",
    "https://biddabari.com/11-20-Grade-question-bank/bndcp-higher-assistant-question-mcq-solution-2026",
    "https://biddabari.com/11-20-Grade-question-bank/baec-question-mcq-solution-2026",
    "https://lekhaporabd.net/archives/41040",
]


def load_posted_jobs() -> list:
    posted = list(BUILTIN_POSTED_URLS)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                for u in json.load(f):
                    if u not in posted:
                        posted.append(u)
        except Exception:
            pass
    return posted


def save_posted_job(url: str):
    posted = load_posted_jobs()
    if url not in posted:
        posted.append(url)
        posted = posted[-500:]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(posted, f, ensure_ascii=False, indent=2)


def parse_bn_date_to_iso(date_str: str) -> str:
    """বাংলা বা ইংরেজি তারিখ (যেমন '১৫ অক্টোবর ২০২৬', '১৭ জানুয়ারি ২০২৬', বা '০৪/০৮/২০২৬') থেকে RFC 3339 ISO টাইমস্ট্যাম্প তৈরি করে।"""
    if not date_str:
        return ""
    bn_digits = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    s = date_str.translate(bn_digits).lower()
    dmy = re.search(r"\b([0-3]?\d)[/\.-]([01]?\d)[/\.-](20[12]\d)\b", s)
    if dmy:
        day, m_num, year = int(dmy.group(1)), int(dmy.group(2)), int(dmy.group(3))
        if 1 <= m_num <= 12 and 1 <= day <= 31:
            now_bd = datetime.now()
            return f"{year:04d}-{m_num:02d}-{day:02d}T{now_bd.hour:02d}:{now_bd.minute:02d}:00+06:00"
    month_map = [
        ("জানুয়ারি", 1), ("জানুয়ারি", 1), ("january", 1),
        ("ফেব্রুয়ারি", 2), ("ফেব্রুয়ারি", 2), ("february", 2),
        ("মার্চ", 3), ("march", 3),
        ("এপ্রিল", 4), ("april", 4),
        ("মে", 5), ("may", 5),
        ("জুন", 6), ("june", 6),
        ("জুলাই", 7), ("july", 7),
        ("আগস্ট", 8), ("august", 8),
        ("সেপ্টেম্বর", 9), ("september", 9),
        ("অক্টোবর", 10), ("october", 10),
        ("নভেম্বর", 11), ("november", 11),
        ("ডিসেম্বর", 12), ("december", 12),
    ]
    found_month = None
    for m_name, m_num in month_map:
        if m_name in s:
            found_month = m_num
            break
    if not found_month:
        return ""
    day_m = re.search(r"\b([0-3]?\d)\b", s)
    year_m = re.search(r"\b(202\d)\b", s)
    day = int(day_m.group(1)) if day_m and 1 <= int(day_m.group(1)) <= 31 else 15
    year = int(year_m.group(1)) if year_m else 2026
    now_bd = datetime.now()
    return f"{year:04d}-{found_month:02d}-{day:02d}T{now_bd.hour:02d}:{now_bd.minute:02d}:00+06:00"


def format_iso_to_bn_date(iso_str: str) -> str:
    """ISO টাইমস্ট্যাম্প (যেমন '2026-10-16T13:21:00+00:00') থেকে বাংলা তারিখ ('১৬ অক্টোবর ২০২৬') তৈরি করে।"""
    if not iso_str or len(iso_str) < 10:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso_str.strip())
    if not m:
        return ""
    yr, mo, dy = m.group(1), int(m.group(2)), int(m.group(3))
    bn_months = {
        1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
        5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
        9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর",
    }
    en_to_bn = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
    return f"{dy:02d} {bn_months.get(mo, 'অক্টোবর')} {yr}".translate(en_to_bn)


def fetch_rss_items(feed_url: str, max_age_days: int = 14) -> list:
    import email.utils
    from datetime import timezone, timedelta

    req = urllib.request.Request(feed_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)
    items = []
    now_utc = datetime.now(timezone.utc)
    bd_tz = timezone(timedelta(hours=6))
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_str = (item.findtext("pubDate") or "").strip()
        pub_iso = ""
        if pub_str:
            try:
                pub_dt = email.utils.parsedate_to_datetime(pub_str)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                age_days = (now_utc - pub_dt).days
                if age_days > max_age_days:
                    continue
                pub_iso = pub_dt.astimezone(bd_tz).isoformat()
            except Exception:
                pass
        categories = [c.text.strip() for c in item.findall("category") if c.text]
        items.append({"title": title, "link": link, "categories": categories, "pub_iso": pub_iso})
    return items


def is_deadline_expired(deadline_bn: str, title_str: str = "") -> bool:
    """চলমান মাসের আগের কোনো মাসের (যেমন সেপ্টেম্বর বা আগস্ট) মেয়াদোত্তীর্ণ সার্কুলার বা রুটিন হলে True রিটার্ন করবে।"""
    combined = f"{deadline_bn} {title_str}".lower()
    if any(k in combined for k in ["ফলাফল", "রেজাল্ট", "result"]):
        return False

    bn_months = [
        ("জানুয়ারি", 1), ("জানুয়ারি", 1), ("january", 1),
        ("ফেব্রুয়ারি", 2), ("ফেব্রুয়ারি", 2), ("february", 2),
        ("মার্চ", 3), ("march", 3),
        ("এপ্রিল", 4), ("april", 4),
        ("মে", 5), ("may", 5),
        ("জুন", 6), ("june", 6),
        ("জুলাই", 7), ("july", 7),
        ("আগস্ট", 8), ("august", 8),
        ("সেপ্টেম্বর", 9), ("september", 9),
        ("অক্টোবর", 10), ("october", 10),
        ("নভেম্বর", 11), ("november", 11),
        ("ডিসেম্বর", 12), ("december", 12),
    ]
    cur_month = datetime.now().month
    mentioned_months = [m_num for m_name, m_num in bn_months if m_name in deadline_bn.lower()]
    if mentioned_months and "২০২৭" not in deadline_bn and "2027" not in deadline_bn:
        if max(mentioned_months) < cur_month:
            return True
    return False


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

    published_iso = ""
    for m_el in [
        soup.find("meta", {"property": "article:modified_time"}),
        soup.find("meta", {"property": "article:published_time"}),
        soup.find("time"),
    ]:
        if m_el:
            cand = (m_el.get("content") or m_el.get("datetime") or "").strip()
            if cand and "202" in cand:
                published_iso = cand
                break

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
        "published_iso": published_iso,
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

    vacancy_bn = kv.get("মোট উত্তীর্ণ প্রার্থী") or kv.get("মোট শূন্যপদ") or kv.get("পদের ক্যাটাগরি") or "অফিশিয়াল নোটিশ দেখুন"
    qualification_bn = kv.get("পদের নাম") or kv.get("শিক্ষাগত যোগ্যতা") or "অফিশিয়াল নোটিশ দেখুন"
    age_limit_bn = kv.get("স্মারক নম্বর") or kv.get("বয়সসীমা") or "অফিশিয়াল নোটিশ দেখুন"
    salary_bn = kv.get("ফলাফলের ধরন") or kv.get("বেতন ও সুযোগ-সুবিধা") or "অফিশিয়াল নোটিশ অনুযায়ী"
    location_bn = kv.get("ব্যবহারিক / পরবর্তী পরীক্ষার কেন্দ্র") or kv.get("জব লোকেশন") or kv.get("প্রধান কার্যালয়ের ঠিকানা") or "অফিশিয়াল নোটিশ অনুযায়ী"
    start_date_bn = kv.get("নোটিশ প্রকাশের তারিখ") or kv.get("আবেদনের শুরু") or kv.get("বিজ্ঞপ্তি প্রকাশের তারিখ") or "চলমান"
    deadline_bn = kv.get("ব্যবহারিক / পরবর্তী পরীক্ষার তারিখ") or kv.get("আবেদনের শেষ তারিখ") or kv.get("আবেদনের শেষ সময়ঃ") or "অফিশিয়াল নোটিশ দেখুন"
    apply_method_bn = kv.get("আবেদন পদ্ধতি") or kv.get("আবেদনের পদ্ধতিঃ") or ("টেলিটক অনলাইন" if is_teletalk else "অফিশিয়াল নোটিশের নির্দেশনা অনুযায়ী")
    apply_email = emails[0] if emails else kv.get("ই-মেইল", "")
    org_name_en_fallback = kv.get("প্রতিষ্ঠানের ইংরেজি নাম") or title_en.replace("Job Circular 2026", "").replace("Job Circular 2025", "").strip() or org_name_bn

    is_res_fallback = any(k in (raw_title + kv.get("নোটিশের ধরন", "") + kv.get("ফলাফলের ধরন", "")) for k in ["ফলাফল", "রেজাল্ট", "Result"])
    is_rout_fallback = any(k in (raw_title + kv.get("নোটিশের ধরন", "")) for k in ["সময়সূচি", "সময়সূচি", "রুটিন", "Routine"])

    if is_res_fallback:
        fallback_post_title = f"{org_name_bn} পরীক্ষার ফলাফল ২০২৬ - {org_name_en_fallback} Exam Result 2026"
        job_type_raw = "পরীক্ষার ফলাফল (Exam Result)"
    elif is_rout_fallback:
        fallback_post_title = f"{org_name_bn} পরীক্ষার সময়সূচি ২০২৬ - {org_name_en_fallback} Exam Routine 2026"
        job_type_raw = "পরীক্ষার রুটিন ও সময়সূচি (Exam Routine)"
    else:
        fallback_post_title = f"{org_name_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ - {title_en}"

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
        "post_title": fallback_post_title,
        "org_name_bn": org_name_bn,
        "org_name_en": org_name_en_fallback,
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

    try:
        import subprocess
        out = subprocess.check_output(
            ["curl", "-s", "--max-time", "12", "-F", "content_type=0", "-F", f"img=@{local_path}", "https://api.pixhost.to/images"],
            timeout=15,
        ).decode("utf-8", errors="replace")
        res_json = json.loads(out)
        th_url = res_json.get("th_url", "")
        if th_url and "/thumbs/" in th_url:
            cdn_url = re.sub(r"^https://t(\d+)\.pixhost\.to/thumbs/", r"https://img\1.pixhost.to/images/", th_url)
            print(f"[BANNER] Uploaded custom banner to Pixhost CDN: {cdn_url}")
            return cdn_url
    except Exception as e:
        print(f"[WARN] Pixhost upload failed: {e}")

    gh_repo = os.getenv("GITHUB_REPOSITORY", "")
    gh_branch = os.getenv("GITHUB_REF_NAME", "main")
    if gh_repo:
        return f"https://raw.githubusercontent.com/{gh_repo}/{gh_branch}/generated_banners/{filename}"

    return local_path


def make_fb_rss_seo_div(core_lines: list, tags: list) -> str:
    """
    [বন্ধ করা হয়েছে] আগে dlvr.it RSS ফিডের জন্য পোস্টের বডিতে লুকানো SEO text রাখা হতো।
    এখন Facebook-এ সরাসরি API দিয়ে পোস্ট হয়, তাই বডিতে লুকানো text রাখা হয় না —
    এটি AdSense ও Google-এর hidden-text নীতির জন্য ঝুঁকিপূর্ণ। ফাংশনটি রাখা হলো যাতে
    পুরোনো কল-সাইটগুলো ভেঙে না যায়; সবসময় খালি স্ট্রিং ফেরত দেয়।
    """
    return ""


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

    combined_type_check = f"{title_full} {info.get('job_type_bn', '')}".lower()
    is_notice_or_result = any(
        k in combined_type_check
        for k in ["ফলাফল", "রেজাল্ট", "result", "সময়সূচি", "সময়সূচি", "রুটিন", "routine", "কেন্দ্র তালিকা", "প্রবেশপত্র"]
    )

    if is_notice_or_result:
        notice_label_bn = "পরীক্ষার ফলাফল" if any(k in combined_type_check for k in ["ফলাফল", "রেজাল্ট", "result"]) else "পরীক্ষার সময়সূচি ও রুটিন"
        notice_rows_html = ""
        for idx, p in enumerate(info.get("posts_breakdown", []), start=1):
            notice_rows_html += f"""
        <tr>
          <td style="border: 1px solid #cbd5e1; padding: 10px; text-align: center;">{idx}</td>
          <td style="border: 1px solid #cbd5e1; padding: 10px; font-weight: bold;">{p.get('post_name', '')}</td>
          <td style="border: 1px solid #cbd5e1; padding: 10px; text-align: center;">{p.get('vacancy', '')}</td>
          <td style="border: 1px solid #cbd5e1; padding: 10px;">{p.get('qualification', '')} — {p.get('salary', '')}</td>
        </tr>"""

        notice_btn_href = pdf_links[0] if pdf_links else (apply_url if apply_url.startswith("http") else SITE_URL)
        fb_notice_div = make_fb_rss_seo_div(
            [
                f"📢 {title_full}",
                f"🏢 প্রতিষ্ঠান: {org_bn}",
                f"📌 নোটিশের ধরন: {notice_label_bn} ২০২৬",
                f"📅 তারিখ / সময়সূচি: {info['deadline_bn']}",
                "👉 অফিশিয়াল নোটিশ ও PDF ডাউনলোড করুন নিচের লিংকে:",
            ],
            ["#ExamResult2026", "#ExamRoutine2026", "#পরীক্ষার_রুটিন", "#ফলাফল", "#BDJobs", "#bdedujob"],
        )
        html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 20px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{title_full}" title="{title_full}" border="0" data-original-height="630" data-original-width="1200" loading="lazy" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 8px;" />
    </a>
  </div>
  {fb_notice_div}
  <p style="text-align: justify;">
    <span style="color: #38761d;"><b>{org_en} Official Notice 2026:</b></span>
    {info['intro_paragraph_1']}
  </p>
  <!--more-->

  <p style="text-align: justify;">
    {info['intro_paragraph_2']}
  </p>
  <div style="background: #f0fdf4; border-left: 4px solid #38761d; padding: 14px 18px; margin: 18px 0; border-radius: 6px; text-align: center;">
    <p style="margin: 0 0 8px 0; font-weight: bold;">
      <a href="{PLAY_STORE_URL}" rel="nofollow noopener" target="_blank" style="color: #15803d; text-decoration: underline;">
        📱 একটি নোটিশ বা ফলাফলও মিস হবে না! আমাদের অফিসিয়াল অ্যাপটি ডাউনলোড করে নিন।
      </a>
    </p>
    <p style="margin: 0; text-align: justify; font-size: 15px;">
      সরকারি ও বেসরকারি সব ধরনের চাকরির খবর, পরীক্ষার রুটিন ও ফলাফল সবার আগে পেতে ভিজিট করুন আমাদের ওয়েবসাইটে
      <a href="{SITE_URL}" style="color: #38761d; font-weight: bold;">{SITE_DISPLAY}</a>
      এবং <a href="{PLAY_STORE_URL}" rel="nofollow noopener" target="_blank" style="color: #38761d; font-weight: bold;">প্লে-স্টোর লিংক</a>
      থেকে আমাদের অফিসিয়াল অ্যাপটি ইনস্টল করে রাখুন।
    </p>
  </div>
  <h2 style="text-align: center; color: #38761d; font-size: 22px; border-bottom: 2px solid #38761d; padding-bottom: 6px; margin-top: 26px;">
    এক নজরে {org_bn} {notice_label_bn} ২০২৬ (Notice Summary)
  </h2>

  <ul style="line-height: 1.9;">
    <li><b>প্রতিষ্ঠানের নাম (Organization Name):</b> {org_bn} ({org_en})</li>
    <li><b>নোটিশের ধরন (Notice Category):</b> {info['job_type_bn']}</li>
    <li><b>পদের নাম / পরীক্ষার বিষয় (Post / Exam):</b> {info['qualification_bn']}</li>
    <li><b>প্রার্থী / উত্তীর্ণ সংখ্যা (Candidates Count):</b> {info['vacancy_bn']}</li>
    <li><b>পরীক্ষার কেন্দ্র / স্থান (Exam Venue):</b> {info.get('location_bn', 'অফিশিয়াল নোটিশ অনুযায়ী')}</li>
    <li><b>নোটিশ প্রকাশের তারিখ (Publish Date):</b> {info['start_date_bn']}</li>
    <li><b>পরীক্ষার তারিখ ও সময়সূচি (Exam Date &amp; Time):</b> <span style="color: #dc2626; font-weight: bold;">{info['deadline_bn']}</span></li>
    <li><b>অফিসিয়াল ওয়েবসাইট (Official Website):</b> <span style="color: #0000ee;"><b><u>{official_site}</u></b></span></li>
  </ul>
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    {org_bn} {notice_label_bn} ২০২৬: পদভিত্তিক বিস্তারিত তথ্য
  </h2>
  <p style="text-align: justify;">
    {org_bn}-এর প্রকাশিত অফিশিয়াল নোটিশ অনুযায়ী পদভিত্তিক সময়সূচি, উত্তীর্ণ প্রার্থীদের তথ্য ও গুরুত্বপূর্ণ বিবরণ নিচের ছকে তুলে ধরা হলো:
  </p>

  <div style="overflow-x: auto; margin: 16px 0;">
    <table style="width: 100%; border-collapse: collapse; font-size: 15px;">
      <thead>
        <tr style="background-color: #38761d; color: #ffffff;">
          <th style="border: 1px solid #cbd5e1; padding: 10px;">ক্রমিক</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">পদের নাম / বিষয়</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">প্রার্থী সংখ্যা / পদ</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">সময়সূচি, কেন্দ্র ও বিস্তারিত নির্দেশনা</th>
        </tr>
      </thead>
      <tbody>
        {notice_rows_html}
      </tbody>
    </table>
  </div>
  <h3 style="color: #38761d; font-size: 19px; margin-top: 24px;">
    বিস্তারিত রোল নম্বর ও সময়সূচি দেখতে অফিশিয়াল নোটিশ (Official Notice / PDF) দেখুন:
  </h3>

  {notice_imgs_html}

  <div style="text-align: center; margin: 26px 0;">
    <a href="{notice_btn_href}" rel="nofollow noopener" target="_blank" style="display: inline-block; background-color: #38761d; color: #ffffff; font-size: 20px; font-weight: bold; padding: 12px 34px; border-radius: 30px; text-decoration: none; box-shadow: 0 4px 10px rgba(56,118,29,0.3);">
      📥 অফিশিয়াল ফলাফল ও নোটিশ ডাউনলোড করুন (Official Notice)
    </a>
  </div>
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    পরীক্ষার্থীদের জন্য জরুরি নির্দেশনা ও করণীয়
  </h2>
  <ul style="line-height: 1.85;">
    {steps_li_html}
  </ul>
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    সচরাচর জিজ্ঞাসিত প্রশ্নোত্তর (FAQ)
  </h2>
  <p style="text-align: justify;">
    <b>প্রশ্ন ১: {org_bn}-এর {notice_label_bn} কোথায় পাওয়া যাবে?</b><br/>
    উত্তর: প্রার্থীরা অফিশিয়াল ওয়েবসাইট (<b>{official_site}</b>) এবং আমাদের এই পোস্টে সংযুক্ত অফিশিয়াল নোটিশ/PDF থেকে বিস্তারিত দেখতে ও ডাউনলোড করতে পারবেন।
  </p>
  <p style="text-align: justify;">
    <b>প্রশ্ন ২: পরবর্তী পরীক্ষা বা ভাইভা কবে অনুষ্ঠিত হবে?</b><br/>
    উত্তর: প্রকাশিত নোটিশ অনুযায়ী নির্ধারিত তারিখ ও সময়: <b>{info['deadline_bn']}</b>।
  </p>
</div>"""
        return html

    fb_job_div = make_fb_rss_seo_div(
        [
            f"📢 {title_full}",
            f"🏢 প্রতিষ্ঠান: {org_bn}",
            f"💼 ধরন: {info.get('job_type_bn', 'চাকরি')} | 📌 পদসংখ্যা: {info['vacancy_bn']}",
            f"🎓 যোগ্যতা: {info.get('qualification_bn', 'বিজ্ঞপ্তি অনুযায়ী')}",
            f"⏳ আবেদনের শেষ তারিখ: {info['deadline_bn']}",
            "👉 বিস্তারিত দেখুন ও আবেদন করুন নিচের লিংকে:",
        ],
        ["#JobCircular2026", "#BDJobs", "#GovtJobsBD", "#চাকরির_খবর", "#নিয়োগ_বিজ্ঞপ্তি_২০২৬", "#bdedujob"],
    )

    html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 20px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{title_full}" title="{title_full}" border="0" data-original-height="630" data-original-width="1200" loading="lazy" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 8px;" />
    </a>
  </div>
  {fb_job_div}
  <p style="text-align: justify;">
    <span style="color: #38761d;"><b>{org_en} Job Circular 2026:</b></span>
    {info['intro_paragraph_1']}
  </p>
  <!--more-->

  <p style="text-align: justify;">
    {info['intro_paragraph_2']}
  </p>
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
  <div style="background: #fffbeb; border: 1px solid #f59e0b; padding: 14px 18px; border-radius: 6px; margin: 22px 0;">
    <div><b>আবেদন পদ্ধতি:</b> {apply_method_bn}</div>
    <div><b>আবেদনের শেষ সময়:</b> <span style="color: #b91c1c; font-weight: bold;">{info['deadline_bn']}</span></div>
  </div>

  <h3 style="color: #38761d; font-size: 19px; margin-top: 24px;">
    বিস্তারিত জানতে অফিসিয়াল নিয়োগ বিজ্ঞপ্তি (Official Notice) দেখুন:
  </h3>

  {notice_imgs_html}
  <div style="text-align: center; margin: 26px 0;">
    <a href="{btn_href}" rel="nofollow noopener" target="_blank" style="display: inline-block; background-color: #38761d; color: #ffffff; font-size: 20px; font-weight: bold; padding: 12px 34px; border-radius: 30px; text-decoration: none; box-shadow: 0 4px 10px rgba(56,118,29,0.3);">
      {btn_label}
    </a>
  </div>
  {apply_section_html}
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    নিয়োগ পরীক্ষা ও ইন্টারভিউ সংক্রান্ত তথ্য
  </h2>
  <p style="text-align: justify;">
    <b>{org_bn}</b>-এ আবেদনপত্র গ্রহণের পর প্রাথমিক বাছাই (Shortlisting) করা হবে। যোগ্য বিবেচিত প্রার্থীদের মোবাইল SMS অথবা ই-মেইলের মাধ্যমে লিখিত পরীক্ষা বা মৌখিক পরীক্ষার (Interview) তারিখ, সময় ও স্থান জানানো হবে। এছাড়াও নিয়মিত আপডেট আমাদের জব পোর্টাল <a href="{SITE_URL}">{SITE_DISPLAY}</a>-এ প্রকাশ করা হবে।
  </p>

  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    আবেদনের আগে করণীয় (আবেদনকারীদের জন্য চেকলিস্ট)
  </h2>
  <ul style="line-height: 1.9; text-align: justify;">
    <li>মূল বিজ্ঞপ্তিতে উল্লেখিত যোগ্যতা, বয়সসীমা ও কোটা-সংক্রান্ত শর্ত আপনার ক্ষেত্রে প্রযোজ্য কি না যাচাই করুন।</li>
    <li>সদ্য তোলা রঙিন ছবি, স্বাক্ষর, জাতীয় পরিচয়পত্র ও শিক্ষাগত সনদের স্ক্যান কপি নির্ধারিত সাইজে আগে থেকে প্রস্তুত রাখুন।</li>
    <li>আবেদন ফি জমা দেওয়ার মাধ্যম (মোবাইল ব্যাংকিং/টেলিটক/ব্যাংক চালান) আগে থেকে নিশ্চিত হয়ে রাখুন।</li>
    <li>শেষ তারিখের জন্য অপেক্ষা না করে হাতে সময় রেখে আবেদন করুন; আবেদনের প্রিন্ট কপি বা স্ক্রিনশট সংরক্ষণ করুন।</li>
    <li>মনে রাখবেন: বিজ্ঞপ্তিতে দেওয়া নির্দেশনাই চূড়ান্ত — কোনো অসঙ্গতি দেখলে অফিসিয়াল বিজ্ঞপ্তিটিকেই প্রাধান্য দিন।</li>
  </ul>

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
  <div style="background: #fef2f2; border: 1px solid #f87171; padding: 14px 18px; border-radius: 6px; margin-top: 26px;">
    <p style="text-align: center; margin: 0 0 6px 0;">
      <b><span style="color: red; font-size: medium;">সতর্কীকরণীয় বিজ্ঞপ্তি:</span></b>
    </p>
    <p style="text-align: justify; margin: 0; font-size: 14.5px;">
      চাকরি আবেদনকারী প্রার্থীদের জানানো যাচ্ছে যে, অনেক প্রতিষ্ঠান আকর্ষণীয় বেতন এবং লোভনীয় অফার দিয়ে বিজ্ঞাপন দিয়ে থাকে। এই সকল বিজ্ঞাপন ভালোভাবে বুঝেশুনে নিজ দায়িত্বে আবেদন করবেন। চাকরির ক্ষেত্রে টাকা-পয়সা লেনদেন আপনার নিজ দায়িত্বে করবেন; এক্ষেত্রে প্রতারিত হলে <a href="{SITE_URL}">{SITE_DISPLAY}</a> কর্তৃপক্ষ দায়ী থাকবে না। আমাদের সাইট ভিজিট করার জন্য ধন্যবাদ।
    </p>
  </div>

  <p style="text-align: justify; margin-top: 18px; font-size: 14.5px; color: #475569;">
    তথ্যসূত্র: {org_bn}-এর প্রকাশিত অফিসিয়াল নিয়োগ বিজ্ঞপ্তি। আবেদনের আগে মূল বিজ্ঞপ্তিটি ভালোভাবে পড়ে নিন এবং
    <a href="{SITE_URL}" style="color: #38761d; font-weight: bold;">{SITE_DISPLAY}</a>-এ নিয়মিত চোখ রাখুন — নতুন চাকরি, পরীক্ষার রুটিন ও ফলাফলের আপডেট আমরা দ্রুত প্রকাশ করে থাকি।
  </p>
  {schema_script}
</div>"""
    return html


_CACHED_ACCESS_TOKEN = ""
_FALLBACK_RT_B64 = ""  # টোকেন শুধু GitHub Secrets (env) থেকে আসবে


def get_blogger_access_token() -> str:
    global _CACHED_ACCESS_TOKEN
    if _CACHED_ACCESS_TOKEN:
        return _CACHED_ACCESS_TOKEN

    candidate_tokens = []
    if _FALLBACK_RT_B64:
        try:
            candidate_tokens.append(base64.b64decode(_FALLBACK_RT_B64).decode("utf-8"))
        except Exception:
            pass
    if BLOGGER_REFRESH_TOKEN and BLOGGER_REFRESH_TOKEN.strip() not in candidate_tokens:
        candidate_tokens.append(BLOGGER_REFRESH_TOKEN.strip())

    for rt in candidate_tokens:
        # ১. প্রথমে কাস্টম OAuth Client দিয়ে চেষ্টা করবে (যদি ১//০৪ না হয়)
        if not rt.startswith("1//04") and BLOGGER_CLIENT_ID and BLOGGER_CLIENT_SECRET:
            try:
                token_url = "https://oauth2.googleapis.com/token"
                payload = urllib.parse.urlencode({
                    "client_id": BLOGGER_CLIENT_ID,
                    "client_secret": BLOGGER_CLIENT_SECRET,
                    "refresh_token": rt,
                    "grant_type": "refresh_token",
                }).encode("utf-8")
                req = urllib.request.Request(token_url, data=payload)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if data.get("access_token"):
                    _CACHED_ACCESS_TOKEN = data["access_token"]
                    return _CACHED_ACCESS_TOKEN
            except Exception:
                pass

        # ২. OAuth Playground Refresh Endpoint দিয়ে চেষ্টা করবে
        try:
            pg_body = json.dumps({
                "token_uri": "https://oauth2.googleapis.com/token",
                "refresh_token": rt,
            }).encode("utf-8")
            pg_req = urllib.request.Request(
                "https://developers.google.com/oauthplayground/refreshAccessToken",
                data=pg_body,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                method="POST",
            )
            with urllib.request.urlopen(pg_req, timeout=15) as resp:
                pg_data = json.loads(resp.read().decode("utf-8"))
            if pg_data.get("access_token"):
                _CACHED_ACCESS_TOKEN = pg_data["access_token"]
                return _CACHED_ACCESS_TOKEN
        except Exception:
            pass

    raise RuntimeError("Failed to obtain Blogger access_token from all configured refresh tokens.")


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


def share_to_facebook_page(
    title: str,
    post_url: str,
    banner_url: str = "",
    summary_text: str = "",
    hashtags: str = "#JobCircular2026 #BDJobs #GovtJobsBD #PrivateJobsBD #BankJobsBD #EducationBD #QuestionSolution2026 #চাকরির_খবর #নিয়োগ_বিজ্ঞপ্তি_২০২৬ #সরকারি_চাকরি #শিক্ষা_সংবাদ #bdedujob",
):
    """
    Facebook Page-এ অটো-শেয়ার (নতুন নিয়ম):
    - মূল পোস্ট: কাস্টম ব্যানার ছবি + সংক্ষিপ্ত structured ক্যাপশন (কোনো URL নয়)
    - আর্টিকেলের বিস্তারিত লিংক যাবে ওই পোস্টের প্রথম কমেন্টে
    Also saves the generated Facebook post to latest_facebook_posts.txt.
    """
    if not post_url:
        return

    t_low = f"{title} {summary_text}".lower()
    if "প্রশ্ন" in t_low or "question solution" in t_low:
        cta_line = "👉 ১০০% নির্ভুল সম্পূর্ণ প্রশ্ন সমাধান ও উত্তরমালা দেখুন এখানে:"
    elif "ফলাফল" in t_low or "result" in t_low or "রুটিন" in t_low or "routine" in t_low:
        cta_line = "👉 অফিসিয়াল নোটিশ ও সম্পূর্ণ বিস্তারিত (PDF সহ) দেখুন এখানে:"
    else:
        cta_line = "👉 সম্পূর্ণ বিজ্ঞপ্তি ও আবেদনের বিস্তারিত দেখুন এখানে:"

    # মূল পোস্টের ক্যাপশন — এখানে কোনো লিংক থাকবে না
    caption = f"📢 {title}\n\n"
    if summary_text:
        caption += f"{summary_text.strip()}\n\n"
    caption += (
        "👉 বিস্তারিত লিংক প্রথম কমেন্টে দেওয়া আছে 👇\n\n"
        f"{hashtags}"
    )

    # প্রথম কমেন্টের লেখা — বিস্তারিত আর্টিকেল লিংক
    comment_text = f"{cta_line}\n🔗 {post_url}"

    try:
        fb_log_path = os.path.join(BASE_DIR, "latest_facebook_posts.txt")
        with open(fb_log_path, "a", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(caption + "\n")
            f.write("[FIRST COMMENT] " + comment_text + "\n")
    except Exception:
        pass

    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("[FACEBOOK INFO] FB_PAGE_ACCESS_TOKEN not set in Secrets; saved SEO caption to latest_facebook_posts.txt")
        return

    # FB_PAGE_ACCESS_TOKEN হলো Page Token (Graph API Explorer থেকে নেওয়া,
    # long-lived User Token থেকে তৈরি) — সরাসরি Page ID দিয়ে পোস্ট হবে।
    page_token = str(FB_PAGE_ACCESS_TOKEN).strip()
    graph_base = "https://graph.facebook.com/v26.0"

    def _fb_post(endpoint: str, params: dict) -> dict:
        data = urllib.parse.urlencode({**params, "access_token": page_token}).encode("utf-8")
        req = urllib.request.Request(f"{graph_base}/{endpoint}", data=data, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))

    fb_post_id = ""

    # ধাপ ১: কাস্টম ব্যানার ছবি + ক্যাপশন দিয়ে মূল পোস্ট
    if banner_url:
        try:
            res = _fb_post(f"{FB_PAGE_ID}/photos", {
                "url": banner_url,
                "caption": caption,
                "published": "true",
            })
            fb_post_id = res.get("post_id") or res.get("id") or ""
            print(f"[FACEBOOK SHARE] Photo post published to Page! Post ID: {fb_post_id}")
        except Exception as e:
            print(f"[WARN] Facebook photo post failed, falling back to text post: {e}")

    # ধাপ ২: ব্যানার না থাকলে বা ছবির পোস্ট ব্যর্থ হলে শুধু ক্যাপশনের টেক্সট পোস্ট (লিংক ছাড়া)
    if not fb_post_id:
        try:
            res = _fb_post(f"{FB_PAGE_ID}/feed", {"message": caption})
            fb_post_id = res.get("id") or ""
            print(f"[FACEBOOK SHARE] Text post published to Page! Post ID: {fb_post_id}")
        except Exception as e:
            print(f"[WARN] Facebook text post failed: {e}")

    if not fb_post_id:
        return

    # ধাপ ৩: প্রথম কমেন্টে বিস্তারিত আর্টিকেল লিংক
    try:
        cres = _fb_post(f"{fb_post_id}/comments", {"message": comment_text})
        print(f"[FACEBOOK COMMENT] First comment with article link added! Comment ID: {cres.get('id')}")
    except Exception as e:
        print(f"[WARN] Facebook first comment failed: {e}")


def publish_to_blogger(title: str, html_content: str, labels: list, is_draft: bool = False, published_iso: str = "") -> dict:
    if "fb-rss-seo-summary" in html_content and ".fb-rss-seo-summary{display:none" not in html_content:
        html_content = html_content + '\n<style>.fb-rss-seo-summary{display:none!important;}</style>'
    access_token = get_blogger_access_token()
    api_url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}/posts/?isDraft={'true' if is_draft else 'false'}"
    payload = {
        "kind": "blogger#post",
        "blog": {"id": BLOGGER_BLOG_ID},
        "title": title,
        "content": html_content,
        "labels": labels,
    }
    if published_iso:
        payload["published"] = published_iso
    body = json.dumps(payload).encode("utf-8")
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


def upload_local_banner_to_cdn(local_path: str, filename: str) -> str:
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
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            cdn_url = res_json.get("image", {}).get("url")
            if cdn_url:
                return cdn_url
    except Exception:
        pass
    try:
        import subprocess
        out = subprocess.check_output(
            ["curl", "-s", "--max-time", "12", "-F", "content_type=0", "-F", f"img=@{local_path}", "https://api.pixhost.to/images"],
            timeout=15,
        ).decode("utf-8", errors="replace")
        res_json = json.loads(out)
        th_url = res_json.get("th_url", "")
        if th_url and "/thumbs/" in th_url:
            return re.sub(r"^https://t(\d+)\.pixhost\.to/thumbs/", r"https://img\1.pixhost.to/images/", th_url)
    except Exception:
        pass
    gh_repo = os.getenv("GITHUB_REPOSITORY", "aralltips/bdedujob-bot")
    gh_branch = os.getenv("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{gh_repo}/{gh_branch}/generated_banners/{filename}"


def build_and_publish_bcs_item(bcs_item: dict, is_draft: bool = False) -> dict:
    num_bn = bcs_item["num_bn"]
    num_en = bcs_item["num_en"]
    slug = bcs_item["slug"]
    source_url = f"https://biddabari.com/bcs-question-bank/{slug}"

    req = urllib.request.Request(source_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")
    bsc = soup.select_one("div.blog-slide-content")
    if not bsc:
        raise ValueError(f"No blog-slide-content found in {source_url}")

    raw_lines = [p.get_text(" ", strip=True) for p in bsc.find_all("p", attrs={"dir": "ltr"}) if p.get_text(" ", strip=True)]
    if len(raw_lines) < 50:
        raw_lines = [ln.strip() for ln in bsc.get_text("\n").splitlines() if ln.strip()]

    q_html_parts = []
    for ln in raw_lines:
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln or "বিদ্যাবাড়ি" in ln or "বিদ্যাবাড়ি" in ln or "biddabari" in ln.lower():
            continue
        if re.match(r"^[০-৯0-9]{1,3}[\.।]\s*\S+", ln):
            q_html_parts.append("<hr /><hr />")
            q_html_parts.append(f'<p><span style="font-size: 18px;"><span style="color: green;"><strong>{ln}</strong></span></span></p>')
        elif re.match(r"^(\(?[কখগঘabcdABCD][\.\)]|\([কখগঘabcdABCD]\))\s*", ln):
            q_html_parts.append(f'<p><span style="font-size: 18px;">{ln}</span></p>')
        elif re.match(r"^(উত্তর|সঠিক উত্তর|নোট|Note|Ans)", ln, re.I):
            q_html_parts.append(f'<p><span style="font-size: 18px;"><span style="color: red;"><strong>{ln}</strong></span></span></p>')
        elif len(ln) < 65 and any(s in ln for s in ["বাংলা", "ইংরেজি", "গণিত", "বিজ্ঞান", "আন্তর্জাতিক", "বাংলাদেশ", "মানসিক", "ভূগোল", "নৈতিকতা", "কম্পিউটার"]):
            q_html_parts.append(
                f'<hr /><hr /><p style="text-align: center;"><span style="font-size: 18px;"><span style="color: lavenderblush;"><strong><span style="background-color: red; padding: 2px 10px;">{ln}</span></strong></span></span></p><hr />'
            )
        else:
            q_html_parts.append(f'<p><span style="font-size: 18px;">{ln}</span></p>')

    os.makedirs(BANNERS_DIR, exist_ok=True)
    safe_en = re.sub(r"[^a-z0-9]+", "-", num_en.lower()).strip("-")
    banner_filename = f"{safe_en}-bcs-prelim-question-solution.jpg"
    local_banner = os.path.join(BANNERS_DIR, banner_filename)
    generate_bcs_banner(f"{num_bn} তম বিসিএস", output_path=local_banner)
    banner_url = upload_local_banner_to_cdn(local_banner, banner_filename)

    post_title = f"{num_bn} তম বি সি এস প্রিলি পরীক্ষার প্রশ্নের সমাধান । {num_en} BCS Prelim Exam Question Solution"
    questions_joined = "\n".join(q_html_parts)
    fb_bcs_div = make_fb_rss_seo_div(
        [
            f"📢 {post_title}",
            "🏛️ কর্তৃপক্ষ: বাংলাদেশ সরকারি কর্ম কমিশন (BPSC)",
            f"📘 পরীক্ষার নাম: {num_bn} তম বিসিএস প্রিলিমিনারি পরীক্ষা",
            "💯 পূর্ণমান: ২০০ (পূর্ণাঙ্গ MCQ প্রশ্ন ও নির্ভুল সমাধান)",
            "👉 সম্পূর্ণ প্রশ্ন ও সমাধান দেখুন নিচের লিংকে:",
        ],
        ["#BCSQuestionSolution", "#BCSPreparation", "#বিসিএস_প্রশ্ন_সমাধান", "#BPSC", "#bdedujob"],
    )

    post_html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 18px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title}" title="{post_title}" border="0" data-original-height="365" data-original-width="640" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 6px;" />
    </a>
  </div>
  {fb_bcs_div}

  <p style="text-align: center;"><b><span style="font-size: x-large;">{num_bn} তম বি সি এস প্রিলি পরীক্ষার প্রশ্নের সমাধান</span></b></p>

  <div style="text-align: justify; margin-bottom: 16px;">
    সরকারি বেসরকারি সব ধরনের চাকরির খবর, বিসিএস ও ব্যাংক পরীক্ষার প্রশ্ন সমাধান, মাসিক প্রফেসর'স কারেন্ট অ্যাফেয়ার্স সবার আগে এই ওয়েবসাইটে <a href="https://bdedujob.blogspot.com">bdedujob.blogspot.com</a> এবং <a href="{PLAY_STORE_URL}" rel="nofollow" target="_blank">প্লে-স্টোর লিংক</a> এ গিয়ে আমাদের অফিসিয়াল অ্যাপটি ডাউনলোড করতে পারেন। তাই যেকোনো ধরনের চাকরির খবর ও বিগত বিসিএস প্রিলিমিনারি পরীক্ষার প্রশ্ন সমাধান পেতে ভিজিট করুন আমাদের ওয়েবসাইটে এবং অ্যাপে। নিচে <b>{num_bn} তম বিসিএস প্রিলিমিনারি পরীক্ষার পূর্ণাঙ্গ প্রশ্ন ও সমাধান</b> দেওয়া হলো:
  </div>
  <!--more-->

  <hr />
  <hr />
  <p style="text-align: center;"><span style="font-size: 20px;"><span style="color: blue;"><strong>{num_bn} তম বি সি এস প্রিলিমিনারি প্রশ্নের সমাধান ({num_en} BCS Preliminary Question Solution)</strong></span></span></p>
  <hr />
  <hr />
  <p style="text-align: center;"><span style="font-size: 18px;"><span style="color: violet;"><strong>উত্তর ভুল মনে হলে সঠিক উত্তরটি কমেন্ট বা মেইল করুন, আপডেট করে দেওয়া হবে।</strong></span></span></p>

  {questions_joined}

  <hr />
  <hr />
</div>"""

    labels = ["all", "BCS", "BCS Exam Question Solution", "QUESTION SOLUTION", "Edcation"]
    # বিগত বিসিএস প্রশ্ন সমাধানগুলোকে ক্রমানুসারে সঠিক ঐতিহাসিক তারিখে পাবলিশ করা যাতে হোমপেজের সর্বশেষ আপডেটগুলো এলোমেলো না হয়
    bcs_num_m = re.search(r"(\d+)", num_en)
    bcs_n = int(bcs_num_m.group(1)) if bcs_num_m else 39
    if bcs_n >= 50:
        bcs_pub_iso = "2026-01-30T16:00:00+06:00"
    elif "special" in num_en.lower():
        bcs_pub_iso = "2022-06-23T01:55:00-07:00"
    else:
        total_mins = 170 + max(0, bcs_n - 24) * 10
        hh = 2 + (total_mins // 60)
        mm = total_mins % 60
        bcs_pub_iso = f"2022-06-23T{hh:02d}:{mm:02d}:00-07:00"

    res = publish_to_blogger(
        title=post_title,
        html_content=post_html,
        labels=labels,
        is_draft=is_draft,
        published_iso=bcs_pub_iso,
    )
    return res, source_url


def get_live_blogger_titles(max_results: int = 40) -> list:
    if not BLOGGER_BLOG_ID or not BLOGGER_REFRESH_TOKEN:
        return []
    try:
        access_token = get_blogger_access_token()
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}/posts?maxResults={max_results}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [p.get("title", "") for p in data.get("items", [])]
    except Exception:
        return []


def clean_and_upload_solution_image(img_url: str, prefix_slug: str, idx: int) -> str:
    """Downloads a question solution image, removes any light-grey center watermark, and uploads to CDN."""
    try:
        from PIL import Image
        import numpy as np

        os.makedirs(BANNERS_DIR, exist_ok=True)
        fname = f"{prefix_slug}-page-{idx}.jpg"
        local_path = os.path.join(BANNERS_DIR, fname)
        req = urllib.request.Request(img_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp, open(local_path, "wb") as f:
            f.write(resp.read())

        im = Image.open(local_path).convert("RGB")
        arr = np.array(im)
        h, w, _ = arr.shape
        y0, y1 = int(h * 0.28), int(h * 0.76)
        x0, x1 = int(w * 0.18), int(w * 0.82)
        sub = arr[y0:y1, x0:x1]
        mask = (sub[:, :, 0] > 125) & (sub[:, :, 1] > 125) & (sub[:, :, 2] > 125)
        sub[mask] = [255, 255, 255]
        arr[y0:y1, x0:x1] = sub
        Image.fromarray(arr).save(local_path, format="JPEG", quality=92, optimize=True)
        return upload_local_banner_to_cdn(local_path, fname)
    except Exception:
        return img_url


def extract_first_solution_image_series(soup: BeautifulSoup) -> list:
    """Extracts the primary contiguous series of current-year solution images from prosnosomadhan.com."""
    ec = soup.select_one(".entry-content")
    if not ec:
        return []
    raw_imgs = []
    for img in ec.find_all("img"):
        src = (img.get("src") or img.get("data-src") or "").strip()
        if not src or "/uploads/2026/" not in src:
            continue
        raw_imgs.append(src)
    if not raw_imgs:
        return []

    def _stem_prefix(u: str) -> str:
        base = u.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        base = re.sub(r"[-_]?(scaled|\d+)$", "", base, flags=re.I)
        base = re.sub(r"[-_]?\d+$", "", base)
        return base.lower()

    first_prefix = _stem_prefix(raw_imgs[0])
    series = []
    for u in raw_imgs:
        if _stem_prefix(u) == first_prefix:
            if u not in series:
                series.append(u)
        elif series:
            break
    return series[:8]


def build_and_publish_image_job_solution(
    org_bn: str,
    post_bn: str,
    exam_date_bn: str,
    marks_bn: str,
    time_bn: str,
    solution_image_urls: list,
    source_url: str,
    slug_prefix: str = "job-solution-2026",
    is_draft: bool = False,
    published_iso: str = "",
) -> tuple:
    os.makedirs(BANNERS_DIR, exist_ok=True)
    safe_slug = re.sub(r"[^a-z0-9]+", "-", slug_prefix.lower()).strip("-") or "job-solution-2026"
    banner_filename = f"{safe_slug}-banner.jpg"
    local_banner = os.path.join(BANNERS_DIR, banner_filename)
    exam_line = f"{post_bn} পরীক্ষার" if len(post_bn) <= 26 else "নিয়োগ MCQ পরীক্ষার"
    generate_job_solution_banner(org_name_bn=org_bn, exam_line_bn=exam_line, output_path=local_banner)
    banner_url = upload_local_banner_to_cdn(local_banner, banner_filename)

    uploaded_pages = []
    for i, img_u in enumerate(solution_image_urls, 1):
        cdn_u = clean_and_upload_solution_image(img_u, safe_slug, i)
        uploaded_pages.append(cdn_u)

    slug_en_clean = re.sub(r"\b(question|solution|answer|exam)\b", "", slug_prefix.replace("-", " "), flags=re.I)
    slug_en_clean = re.sub(r"\s+", " ", slug_en_clean).strip().title()
    if post_bn in ("নিয়োগ পরীক্ষা", "বিভিন্ন পদ"):
        post_title = f"{org_bn} পরীক্ষার প্রশ্ন সমাধান ২০২৬ । {slug_en_clean} Exam Question Solution 2026"
    else:
        post_title = f"{org_bn} এর {post_bn} পদের পরীক্ষার প্রশ্ন সমাধান ২০২৬ । {slug_en_clean} Question Solution 2026"
    post_title = re.sub(r"\s+", " ", post_title).strip()
    pages_html = "\n".join(
        f'''  <div class="separator" style="clear: both; text-align: center; margin: 16px 0;">
    <p style="font-weight: bold; color: #0b5394; margin-bottom: 6px;">প্রশ্ন ও সমাধান পৃষ্ঠা - {i}</p>
    <a href="{u}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title} - Page {i}" title="{post_title} - Page {i}" border="0" src="{u}" style="max-width: 100%; height: auto; border: 1px solid #cbd5e1; border-radius: 6px;" />
    </a>
  </div>'''
        for i, u in enumerate(uploaded_pages, 1)
    )

    post_html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 18px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title}" title="{post_title}" border="0" data-original-height="445" data-original-width="800" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 6px;" />
    </a>
  </div>
  {make_fb_rss_seo_div([f"📢 {post_title}", f"🏢 প্রতিষ্ঠান: {org_bn}", f"💼 পদের নাম: {post_bn}", f"📅 তারিখ: {exam_date_bn} | 💯 পূর্ণমান: {marks_bn}", "👉 ১০০% নির্ভুল প্রশ্ন ও সমাধান দেখুন নিচের লিংকে:"], ["#QuestionSolution2026", "#JobSolutionBD", "#প্রশ্ন_সমাধান", "#নিয়োগ_পরীক্ষা", "#bdedujob"])}

  <p style="text-align: center;"><b><span style="font-size: x-large;">{org_bn} এর {post_bn} পদের পরীক্ষার প্রশ্ন সমাধান ২০২৬</span></b></p>

  <div style="text-align: justify; margin-bottom: 16px;">
    সরকারি ও বেসরকারি সকল নিয়োগ পরীক্ষার প্রশ্ন সমাধান, চাকরির খবর, পরীক্ষার রুটিন ও ফলাফল সবার আগে পেতে ভিজিট করুন <a href="https://bdedujob.blogspot.com">bdedujob.blogspot.com</a> এবং আমাদের <a href="{PLAY_STORE_URL}" rel="nofollow" target="_blank">অফিসিয়াল অ্যান্ড্রয়েড অ্যাপ</a>। নিচে <b>{org_bn}</b>-এর <b>{post_bn}</b> পদের নিয়োগ পরীক্ষার নির্ভুল প্রশ্ন ও সম্পূর্ণ সমাধান তুলে ধরা হলো:
  </div>
  <!--more-->

  <table style="width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 16px;" border="1" cellpadding="8">
    <tbody>
      <tr style="background-color: #0d6b88; color: #ffffff;">
        <th colspan="2" style="text-align: center; padding: 10px;">পরীক্ষার সংক্ষিপ্ত তথ্য (Exam Overview)</th>
      </tr>
      <tr>
        <td style="width: 38%; font-weight: bold; background-color: #f8fafc;">প্রতিষ্ঠানের নাম</td>
        <td>{org_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">পদের নাম</td>
        <td>{post_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">পরীক্ষার তারিখ</td>
        <td>{exam_date_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">সময় ও পূর্ণমান</td>
        <td>সময়: {time_bn} | পূর্ণমান: {marks_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">ক্যাটাগরি</td>
        <td><a href="https://bdedujob.blogspot.com/search/label/Job%20Solution">Job Solution (প্রশ্ন সমাধান)</a></td>
      </tr>
    </tbody>
  </table>

  <hr />
  <p style="text-align: center;"><span style="font-size: 20px; color: #0b5394;"><strong>{org_bn} ({post_bn}) পরীক্ষার সম্পূর্ণ প্রশ্ন ও উত্তরমালা</strong></span></p>
  <hr />
  <p style="text-align: center;"><span style="font-size: 16px; color: #b45309;"><strong>বিঃদ্রঃ কোনো প্রশ্নের উত্তর ভুল মনে হলে কমেন্ট করে জানাবেন, দ্রুত সংশোধন করে দেওয়া হবে।</strong></span></p>

{pages_html}

  <hr />
</div>"""

    labels = ["all", "EXAM INFO", "Job Solution", "QUESTION SOLUTION", "Govt Jobs", "Edcation"]
    eff_pub_iso = published_iso or parse_bn_date_to_iso(exam_date_bn)
    res = publish_to_blogger(
        title=post_title,
        html_content=post_html,
        labels=labels,
        is_draft=is_draft,
        published_iso=eff_pub_iso,
    )
    return res, source_url, banner_url


def build_and_publish_text_job_solution(item_meta: dict, is_draft: bool = False) -> tuple:
    source_url = item_meta["url"]
    org_bn = item_meta["org_bn"]
    post_bn = item_meta["post_bn"]
    exam_date = item_meta.get("exam_date", "২০২৬")
    marks = item_meta.get("marks", "১০০")
    time_bn = item_meta.get("time", "৬০ মিনিট")
    org_short = item_meta.get("org_short", "job-solution")

    req = urllib.request.Request(source_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    bsc = soup.select_one("div.blog-slide-content")
    if not bsc:
        raise ValueError(f"No blog-slide-content found in {source_url}")

    raw_lines = [re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip() for p in bsc.find_all(["p", "li", "h3", "h4"]) if p.get_text(" ", strip=True)]
    if len(raw_lines) < 30:
        raw_lines = [ln.strip() for ln in bsc.get_text("\n").splitlines() if ln.strip()]
    if len(raw_lines) < 30:
        raise ValueError(f"Insufficient question lines ({len(raw_lines)}) in {source_url}")

    q_html_parts = []
    for ln in raw_lines:
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln or "বিদ্যাবাড়ি" in ln or "বিদ্যাবাড়ি" in ln or "biddabari" in ln.lower() or "other job’s preparation" in ln.lower():
            continue
        if re.match(r"^[০-৯0-9]{1,3}[\.।\)]\s*\S+", ln):
            q_html_parts.append("<hr />")
            q_html_parts.append(f'<p><span style="font-size: 18px;"><span style="color: green;"><strong>{ln}</strong></span></span></p>')
        elif re.match(r"^(\(?[কখগঘabcdABCD][\.\)]|\([কখগঘabcdABCD]\))\s*", ln):
            q_html_parts.append(f'<p><span style="font-size: 18px;">{ln}</span></p>')
        elif re.match(r"^(উত্তর|সঠিক উত্তর|নোট|Note|Ans|ব্যাখ্যা)", ln, re.I):
            q_html_parts.append(f'<p><span style="font-size: 18px;"><span style="color: red;"><strong>{ln}</strong></span></span></p>')
        else:
            q_html_parts.append(f'<p><span style="font-size: 18px;">{ln}</span></p>')

    os.makedirs(BANNERS_DIR, exist_ok=True)
    safe_slug = re.sub(r"[^a-z0-9]+", "-", org_short.lower()).strip("-")
    banner_filename = f"{safe_slug}-question-solution-2026.jpg"
    local_banner = os.path.join(BANNERS_DIR, banner_filename)
    exam_line = f"{post_bn} MCQ পরীক্ষার" if len(post_bn) <= 22 else "নিয়োগ MCQ পরীক্ষার"
    generate_job_solution_banner(org_name_bn=org_bn, exam_line_bn=exam_line, output_path=local_banner)
    banner_url = upload_local_banner_to_cdn(local_banner, banner_filename)

    post_title = f"{org_bn} এর {post_bn} পদের MCQ পরীক্ষার প্রশ্ন সমাধান – ২০২৬ । {org_short.replace('-', ' ').title()} Question Solution 2026"
    questions_joined = "\n".join(q_html_parts)

    post_html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 18px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title}" title="{post_title}" border="0" data-original-height="445" data-original-width="800" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 6px;" />
    </a>
  </div>
  {make_fb_rss_seo_div([f"📢 {post_title}", f"🏢 প্রতিষ্ঠান: {org_bn}", f"💼 পদের নাম: {post_bn}", f"📅 তারিখ: {exam_date} | 💯 পূর্ণমান: {marks}", "👉 পূর্ণাঙ্গ MCQ প্রশ্ন ও সমাধান দেখুন নিচের লিংকে:"], ["#QuestionSolution2026", "#JobSolutionBD", "#প্রশ্ন_সমাধান", "#নিয়োগ_পরীক্ষা", "#bdedujob"])}

  <p style="text-align: center;"><b><span style="font-size: x-large;">{org_bn} এর {post_bn} পদের MCQ পরীক্ষার প্রশ্ন সমাধান – ২০২৬</span></b></p>

  <div style="text-align: justify; margin-bottom: 16px;">
    সরকারি বেসরকারি সব ধরনের চাকরির খবর, নিয়োগ পরীক্ষার প্রশ্ন সমাধান ও মাসিক কারেন্ট অ্যাফেয়ার্স সবার আগে পেতে ভিজিট করুন <a href="https://bdedujob.blogspot.com">bdedujob.blogspot.com</a> এবং আমাদের <a href="{PLAY_STORE_URL}" rel="nofollow" target="_blank">অফিসিয়াল অ্যাপ</a>। নিচে <b>{org_bn}</b>-এর <b>{post_bn}</b> পদের নিয়োগ পরীক্ষার পূর্ণাঙ্গ MCQ প্রশ্ন ও নির্ভুল সমাধান তুলে ধরা হলো:
  </div>
  <!--more-->

  <table style="width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 16px;" border="1" cellpadding="8">
    <tbody>
      <tr style="background-color: #0d6b88; color: #ffffff;">
        <th colspan="2" style="text-align: center; padding: 10px;">পরীক্ষার সংক্ষিপ্ত তথ্য (Exam Overview)</th>
      </tr>
      <tr>
        <td style="width: 38%; font-weight: bold; background-color: #f8fafc;">প্রতিষ্ঠানের নাম</td>
        <td>{org_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">পদের নাম</td>
        <td>{post_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">পরীক্ষার তারিখ</td>
        <td>{exam_date}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">সময় ও পূর্ণমান</td>
        <td>সময়: {time_bn} | পূর্ণমান: {marks}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">ক্যাটাগরি</td>
        <td><a href="https://bdedujob.blogspot.com/search/label/Job%20Solution">Job Solution (প্রশ্ন সমাধান)</a></td>
      </tr>
    </tbody>
  </table>

  <hr />
  <hr />
  <p style="text-align: center;"><span style="font-size: 20px;"><span style="color: blue;"><strong>{org_bn} ({post_bn}) পরীক্ষার সম্পূর্ণ প্রশ্ন সমাধান ২০২৬</strong></span></span></p>
  <hr />
  <hr />
  <p style="text-align: center;"><span style="font-size: 18px;"><span style="color: violet;"><strong>উত্তর ভুল মনে হলে সঠিক উত্তরটি কমেন্ট বা মেইল করুন, আপডেট করে দেওয়া হবে।</strong></span></span></p>

  {questions_joined}

  <hr />
  <hr />
</div>"""

    labels = ["all", "EXAM INFO", "Job Solution", "QUESTION SOLUTION", "Edcation"]
    if "ব্যাংক" in org_bn or "bank" in org_bn.lower():
        labels.append("Bank Jobs")
    else:
        labels.append("Govt Jobs")

    exam_pub_iso = parse_bn_date_to_iso(exam_date)
    res = publish_to_blogger(
        title=post_title,
        html_content=post_html,
        labels=labels,
        is_draft=is_draft,
        published_iso=exam_pub_iso,
    )
    return res, source_url, banner_url


def publish_next_job_question_solution(posted_urls: list) -> bool:
    """
    ১) প্রথমে prosnosomadhan.com এর লাইভ ফিড থেকে সদ্য অনুষ্ঠিত পরীক্ষার প্রশ্ন সমাধান (ছবিসহ) চেক করে পাবলিশ করে।
    ২) নতুন লাইভ পরীক্ষা না থাকলে JOB_SOLUTION_QUEUE থেকে ২০২৬ সালের চাকরির পরীক্ষার MCQ প্রশ্ন সমাধান পাবলিশ করে।
    """
    live_titles = " | ".join(get_live_blogger_titles(50)).lower()

    # Step 1: Check live feed from prosnosomadhan.com/category/question-solution/feed/
    try:
        items = fetch_rss_items("https://prosnosomadhan.com/category/question-solution/feed/", max_age_days=14)
        for item in items:
            link = item["link"]
            raw_t = item["title"]
            if not link or link in posted_urls:
                continue
            req = urllib.request.Request(link, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")
            series = extract_first_solution_image_series(soup)
            if not series:
                # এখনো প্রশ্নের সমাধানের ছবি আপলোড হয়নি, তাই পরবর্তী রানের জন্য অপেক্ষা করবে
                continue
            # Check if duplicate image series already posted from a twin URL
            if series[0] in posted_urls:
                save_posted_job(link)
                posted_urls.append(link)
                continue

            clean_t = re.sub(r"প্রশ্ন সমাধান.*|প্রশ্ন উত্তর.*|পরীক্ষার প্রশ্ন.*|Question Solution.*|Question Answer.*", "", raw_t, flags=re.I).strip(" -–|")
            org_bn = clean_t or raw_t.split("|")[0].strip()
            if org_bn.lower() in live_titles:
                save_posted_job(link)
                save_posted_job(series[0])
                posted_urls.extend([link, series[0]])
                continue

            pub_iso = item.get("pub_iso", "")
            for m_el in [soup.find("meta", {"property": "article:published_time"}), soup.find("time")]:
                if m_el:
                    cand = (m_el.get("content") or m_el.get("datetime") or "").strip()
                    if cand and "202" in cand:
                        pub_iso = cand
                        break
            exam_dt_bn = format_iso_to_bn_date(pub_iso) or "অক্টোবর ২০২৬"
            if pub_iso and pub_iso.startswith("2026-10"):
                pub_iso = ""

            slug_part = link.rstrip("/").rsplit("/", 1)[-1]
            res, src, b_url = build_and_publish_image_job_solution(
                org_bn=org_bn,
                post_bn="নিয়োগ পরীক্ষা",
                exam_date_bn=exam_dt_bn,
                marks_bn="১০০",
                time_bn="৬০/৯০ মিনিট",
                solution_image_urls=series,
                source_url=link,
                slug_prefix=slug_part,
                is_draft=BLOGGER_IS_DRAFT,
                published_iso=pub_iso,
            )
            print(f"[JOB SOLUTION LIVE] Published {org_bn} -> {res.get('url')}")
            save_posted_job(link)
            save_posted_job(series[0])
            posted_urls.extend([link, series[0]])
            ping_google_websub_hub()
            share_to_facebook_page(
                title=f"{org_bn} পরীক্ষার প্রশ্ন সমাধান ২০২৬ - Question Solution 2026",
                post_url=res.get("url", ""),
                banner_url=b_url,
                summary_text=(
                    f"🏢 প্রতিষ্ঠান: {org_bn}\n"
                    f"📌 পরীক্ষার নাম: নিয়োগ পরীক্ষা ২০২৬\n"
                    f"📅 পরীক্ষার তারিখ: অক্টোবর ২০২৬\n"
                    f"💯 পূর্ণমান: ১০০ (১০০% নির্ভুল উত্তরমালা)\n"
                    f"📂 ক্যাটাগরি: Job Solution (প্রশ্ন সমাধান)"
                ),
            )
            return True
    except Exception as e:
        print(f"[WARN] Live prosnosomadhan check error: {e}")

    # Step 2: Publish from 2026 JOB_SOLUTION_QUEUE (Biddabari full-text MCQ solutions)
    for item_meta in JOB_SOLUTION_QUEUE:
        u = item_meta["url"]
        if u in posted_urls:
            continue
        if item_meta["org_bn"].split("(")[0].strip().lower() in live_titles and item_meta["post_bn"].lower() in live_titles:
            save_posted_job(u)
            posted_urls.append(u)
            continue
        try:
            print(f"[JOB SOLUTION QUEUE] Uploading {item_meta['org_bn']} ({item_meta['post_bn']}) -> {u}")
            res, src, b_url = build_and_publish_text_job_solution(item_meta, is_draft=BLOGGER_IS_DRAFT)
            print(f"[JOB SOLUTION SUCCESS] Published! URL: {res.get('url')}")
            save_posted_job(u)
            posted_urls.append(u)
            ping_google_websub_hub()
            share_to_facebook_page(
                title=f"{item_meta['org_bn']} এর {item_meta['post_bn']} পদের পরীক্ষার প্রশ্ন সমাধান ২০২৬",
                post_url=res.get("url", ""),
                banner_url=b_url,
                summary_text=(
                    f"🏢 প্রতিষ্ঠান: {item_meta['org_bn']}\n"
                    f"💼 পদের নাম: {item_meta['post_bn']}\n"
                    f"📅 পরীক্ষার তারিখ: {item_meta.get('exam_date', '২০২৬')}\n"
                    f"⏱️ সময় ও পূর্ণমান: {item_meta.get('time', '৬০ মিনিট')} | পূর্ণমান: {item_meta.get('marks', '১০০')}\n"
                    f"📂 ক্যাটাগরি: Job Solution (পূর্ণাঙ্গ MCQ প্রশ্ন ও উত্তর)"
                ),
            )
            return True
        except Exception as e:
            print(f"[WARN] Failed Job Solution upload for {u}: {e}")
            continue
    return False


def publish_next_bcs_question_solution(posted_urls: list) -> bool:
    live_titles = " | ".join(get_live_blogger_titles(50))
    for bcs_item in BCS_QUESTION_BANK_QUEUE:
        source_url = f"https://biddabari.com/bcs-question-bank/{bcs_item['slug']}"
        if source_url in posted_urls:
            continue
        if f"{bcs_item['num_en']} BCS Prelim" in live_titles or f"{bcs_item['num_bn']} তম বি সি এস প্রিলি" in live_titles:
            save_posted_job(source_url)
            posted_urls.append(source_url)
            continue
        try:
            print(f"[BCS SCHEDULE] Uploading {bcs_item['num_bn']} তম বিসিএস প্রিলি প্রশ্ন সমাধান -> {source_url}")
            res, src = build_and_publish_bcs_item(bcs_item, is_draft=BLOGGER_IS_DRAFT)
            print(f"[BCS SUCCESS] Published {bcs_item['num_bn']}th BCS! URL: {res.get('url')}")
            save_posted_job(src)
            posted_urls.append(src)
            ping_google_websub_hub()
            share_to_facebook_page(
                title=f"{bcs_item['num_bn']} তম বি সি এস প্রিলি পরীক্ষার প্রশ্নের সমাধান - {bcs_item['num_en']} BCS Question Solution",
                post_url=res.get("url", ""),
                summary_text=(
                    f"🏛️ প্রতিষ্ঠান: বাংলাদেশ সরকারি কর্ম কমিশন (BPSC)\n"
                    f"📘 পরীক্ষার নাম: {bcs_item['num_bn']} তম বিসিএস প্রিলিমিনারি পরীক্ষা\n"
                    f"💯 পূর্ণমান: ২০০ (পূর্ণাঙ্গ MCQ প্রশ্ন ও নির্ভুল সমাধান)\n"
                    f"📂 ক্যাটাগরি: BCS Question Solution & Job Preparation"
                ),
            )
            return True
        except Exception as e:
            print(f"[WARN] Failed BCS upload for {bcs_item['slug']}: {e}")
            continue
    return False


def publish_next_live_job_circular(posted_urls: list) -> bool:
    live_titles_joined = " | ".join(get_live_blogger_titles(45)).lower()

    # প্রথমে আজকের একদম নতুন প্রকাশিত সব সার্কুলার (All Latest) চেক করবে, এরপর বাকি ক্যাটাগরিগুলো পালাক্রমে চেক করবে
    offset = len(posted_urls) % len(JOB_SOURCES)
    rotated_sources = [JOB_SOURCES[0]] + [s for s in (JOB_SOURCES[offset:] + JOB_SOURCES[:offset]) if s != JOB_SOURCES[0]]

    for source in rotated_sources:
        print(f"[INFO] Checking source: {source['name']} ({source['feed_url']})")
        try:
            items = fetch_rss_items(source["feed_url"])
        except Exception as e:
            print(f"[ERROR] Failed to fetch feed {source['feed_url']}: {e}")
            continue

        for item in items:
            link = item["link"]
            if not link or link in posted_urls:
                continue

            # Blogger Content Policy (Regulated Goods: Tobacco, Gambling, Alcohol) filter
            title_low = item["title"].lower()
            if any(bad in title_low for bad in ["বিড়ি", "বিড়ি", "সিগারেট", "তামাক", "tobacco", "biri", "cigarette", "casino", "betting", "gambling"]):
                print(f"[SKIP POLICY] Regulated goods keyword in title: {item['title']}")
                save_posted_job(link)
                posted_urls.append(link)
                continue

            print(f"[NEW JOB FOUND] {item['title']} -> {link}")
            try:
                scraped = scrape_job_details(link)
                if not scraped["notice_images"] and not scraped.get("pdf_links"):
                    print(f"[SKIP] No official circular image or PDF found in {link}")
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue
                kv_dl = scraped["kv_map"].get("আবেদনের শেষ তারিখ") or scraped["kv_map"].get("আবেদনের শেষ সময়ঃ") or ""
                if kv_dl and is_deadline_expired(kv_dl, item["title"]):
                    print(f"[SKIP EXPIRED] Circular deadline already passed ({kv_dl}) -> {link}")
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue
                info = extract_structured_job_info(item["title"], scraped)
                if is_deadline_expired(info.get("deadline_bn", ""), info.get("post_title", "")):
                    print(f"[SKIP EXPIRED] Circular deadline already passed ({info.get('deadline_bn')}) -> {link}")
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue
                if info["org_name_bn"].lower() in live_titles_joined or info["org_name_en"].lower() in live_titles_joined:
                    print(f"[SKIP DUPLICATE] Already live on blog: {info['post_title']} -> {link}")
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue
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
                if scraped.get("pdf_links") or "Saptahik Job Paper" in final_labels or "Current Affairs" in final_labels:
                    for pdf_lbl in ["pdf", "pdf Zone"]:
                        if pdf_lbl not in final_labels:
                            final_labels.append(pdf_lbl)

                if BLOGGER_BLOG_ID:
                    job_pub_iso = (
                        scraped.get("published_iso")
                        or item.get("pub_iso")
                        or parse_bn_date_to_iso(info.get("start_date_bn", ""))
                    )
                    if job_pub_iso and job_pub_iso.startswith("2026-10"):
                        job_pub_iso = ""
                    res = publish_to_blogger(
                        title=info["post_title"],
                        html_content=html_post,
                        labels=final_labels,
                        is_draft=BLOGGER_IS_DRAFT,
                        published_iso=job_pub_iso,
                    )
                    print(f"[SUCCESS] Published to Blogger! Post URL: {res.get('url')}")
                    save_posted_job(link)
                    posted_urls.append(link)
                    ping_google_websub_hub()
                    share_to_facebook_page(
                        title=info["post_title"],
                        post_url=res.get("url", ""),
                        banner_url=banner_url,
                        summary_text=(
                            f"🏢 প্রতিষ্ঠান: {info['org_name_bn']}\n"
                            f"💼 চাকরির ধরণ: {info.get('job_type_bn', 'বিজ্ঞপ্তি অনুযায়ী')}\n"
                            f"📌 পদসংখ্যা: {info['vacancy_bn']}\n"
                            f"🎓 শিক্ষাগত যোগ্যতা: {info.get('qualification_bn', 'বিজ্ঞপ্তি অনুযায়ী')}\n"
                            f"💰 বেতন স্কেল: {info.get('salary_bn', 'বিজ্ঞপ্তি অনুযায়ী')}\n"
                            f"⏳ শেষ তারিখ: {info['deadline_bn']}"
                        ),
                    )
                    return True
                else:
                    preview_file = os.path.join(BASE_DIR, "sample_post_preview.html")
                    with open(preview_file, "w", encoding="utf-8") as f:
                        f.write(html_post)
                    print(f"[PREVIEW] Saved sample SEO post HTML to: {preview_file}")
                    return True
            except Exception as e:
                print(f"[ERROR] Failed processing {link}: {e}")
    return False


def build_and_publish_education_notice(
    org_bn: str,
    org_en: str,
    notice_type_bn: str,
    program_bn: str,
    publish_date_bn: str,
    exam_or_deadline_bn: str,
    official_site: str,
    notice_images: list,
    pdf_links: list,
    source_url: str,
    slug_prefix: str = "education-notice-2026",
    extra_labels: list = None,
    is_draft: bool = False,
    published_iso: str = "",
) -> tuple:
    os.makedirs(BANNERS_DIR, exist_ok=True)
    safe_slug = re.sub(r"[^a-z0-9]+", "-", slug_prefix.lower()).strip("-") or "education-notice-2026"
    banner_filename = f"{safe_slug}-banner.png"
    local_banner = os.path.join(BANNERS_DIR, banner_filename)

    generate_job_banner(
        org_name_bn=org_bn,
        org_short_en=org_en,
        job_type_bn=notice_type_bn,
        output_path=local_banner,
    )
    banner_url = upload_local_banner_to_cdn(local_banner, banner_filename)

    uploaded_imgs = []
    for i, im_u in enumerate(notice_images[:4], 1):
        try:
            fname = f"{safe_slug}-notice-{i}.jpg"
            lpath = os.path.join(BANNERS_DIR, fname)
            req = urllib.request.Request(im_u, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r, open(lpath, "wb") as f:
                f.write(r.read())
            uploaded_imgs.append(upload_local_banner_to_cdn(lpath, fname))
        except Exception:
            uploaded_imgs.append(im_u)

    en_clean = slug_prefix.replace("-", " ").title()
    generic_programs = {"অফিশিয়াল শিক্ষা ও পরীক্ষা বিজ্ঞপ্তি", "শিক্ষা ও পরীক্ষা সংক্রান্ত বিজ্ঞপ্তি"}
    if program_bn and program_bn not in generic_programs and program_bn not in org_bn and not re.search(r"[A-Za-z]{4,}", program_bn):
        post_title = f"{org_bn} {program_bn} {notice_type_bn} ২০২৬ । {en_clean} 2026"
    else:
        post_title = f"{org_bn} {notice_type_bn} ২০২৬ । {en_clean} 2026"
    post_title = re.sub(r"\s+", " ", post_title).strip()

    imgs_html = "\n".join(
        f'''  <div class="separator" style="clear: both; text-align: center; margin: 16px 0;">
    <a href="{u}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title} - Notice {i}" title="{post_title} - Notice {i}" border="0" src="{u}" style="max-width: 100%; height: auto; border: 1px solid #cbd5e1; border-radius: 6px;" />
    </a>
  </div>'''
        for i, u in enumerate(uploaded_imgs, 1)
    )

    btn_href = pdf_links[0] if pdf_links else (official_site if official_site.startswith("http") else f"https://{official_site}")
    fb_edu_div = make_fb_rss_seo_div(
        [
            f"📢 {post_title}",
            f"🏛️ কর্তৃপক্ষ: {org_bn}",
            f"📌 নোটিশের ধরন: {notice_type_bn}",
            f"📚 কোর্স / পর্যায়: {program_bn}",
            f"⏳ তারিখ / সময়সূচি: {exam_or_deadline_bn}",
            "👉 অফিশিয়াল নোটিশ ও PDF ডাউনলোড করুন নিচের লিংকে:",
        ],
        ["#EducationBD", "#Admission2026", "#ExamResult2026", "#শিক্ষা_সংবাদ", "#bdedujob"],
    )

    post_html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 18px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title}" title="{post_title}" border="0" data-original-height="630" data-original-width="1200" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 8px;" />
    </a>
  </div>
  {fb_edu_div}

  <p style="text-align: justify;">
    <span style="color: #38761d;"><b>{org_en} Official Education Notice 2026:</b></span>
    <b>{org_bn}</b> কর্তৃক <b>{program_bn}</b>-এর অফিশিয়াল <b>{notice_type_bn}</b> প্রকাশিত হয়েছে। দেশের সকল বিশ্ববিদ্যালয়, জাতীয় বিশ্ববিদ্যালয় (NU), শিক্ষা বোর্ড (SSC/HSC), ভর্তি বিজ্ঞপ্তি, পরীক্ষার রুটিন, ফলাফল ও শিক্ষাবৃত্তির সর্বশেষ আপডেট সবার আগে পেতে নিয়মিত ভিজিট করুন <a href="{SITE_URL}">{SITE_DISPLAY}</a> এবং আমাদের <a href="{PLAY_STORE_URL}" rel="nofollow" target="_blank">অফিসিয়াল অ্যাপ</a>।
  </p>
  <!--more-->

  <h2 style="text-align: center; color: #38761d; font-size: 21px; border-bottom: 2px solid #38761d; padding-bottom: 6px; margin-top: 24px;">
    এক নজরে {org_bn} {notice_type_bn} ২০২৬ (Education Summary)
  </h2>

  <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 16px;" border="1" cellpadding="8">
    <tbody>
      <tr style="background-color: #38761d; color: #ffffff;">
        <th colspan="2" style="text-align: center; padding: 10px;">শিক্ষা ও পরীক্ষা সংক্রান্ত সংক্ষিপ্ত তথ্য</th>
      </tr>
      <tr>
        <td style="width: 38%; font-weight: bold; background-color: #f8fafc;">প্রতিষ্ঠান / শিক্ষা বোর্ড</td>
        <td>{org_bn} ({org_en})</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">নোটিশের ধরন</td>
        <td>{notice_type_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">কোর্স / বর্ষ / শ্রেণি</td>
        <td>{program_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">প্রকাশের তারিখ</td>
        <td>{publish_date_bn}</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">পরীক্ষা / আবেদনের শেষ তারিখ</td>
        <td><span style="color: #dc2626; font-weight: bold;">{exam_or_deadline_bn}</span></td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">অফিশিয়াল ওয়েবসাইট</td>
        <td><a href="{btn_href}" rel="nofollow noopener" target="_blank"><b>{official_site}</b></a></td>
      </tr>
    </tbody>
  </table>

  <h3 style="color: #38761d; font-size: 19px; margin-top: 24px;">
    বিস্তারিত দেখতে অফিশিয়াল নোটিশ / রুটিন / ফলাফল (Official Notice Image) দেখুন:
  </h3>

{imgs_html}

  <div style="text-align: center; margin: 24px 0;">
    <a href="{btn_href}" rel="nofollow noopener" target="_blank" style="display: inline-block; background-color: #38761d; color: #ffffff; font-size: 19px; font-weight: bold; padding: 12px 32px; border-radius: 30px; text-decoration: none;">
      📥 অফিশিয়াল নোটিশ ও বিস্তারিত দেখুন (Official Website / PDF)
    </a>
  </div>
</div>"""

    labels = ["all", "Edcation", "EXAM INFO"]
    if extra_labels:
        for lbl in extra_labels:
            if lbl in ALLOWED_BLOGGER_LABELS and lbl not in labels:
                labels.append(lbl)
    if any(k in notice_type_bn for k in ["রুটিন", "সময়সূচি", "সময়সূচি"]):
        if "Exam Routine" not in labels:
            labels.append("Exam Routine")
    if any(k in notice_type_bn for k in ["ফলাফল", "রেজাল্ট"]):
        for rl in ["Result", "exam result"]:
            if rl not in labels:
                labels.append(rl)
    if pdf_links:
        for pl in ["pdf", "pdf Zone"]:
            if pl not in labels:
                labels.append(pl)

    eff_pub_iso = published_iso if published_iso is not None else parse_bn_date_to_iso(publish_date_bn)
    res = publish_to_blogger(
        title=post_title,
        html_content=post_html,
        labels=labels,
        is_draft=is_draft,
        published_iso=eff_pub_iso,
    )
    return res, source_url, banner_url


def publish_next_education_notice(posted_urls: list) -> bool:
    """বিশ্ববিদ্যালয় ও কলেজ ভর্তি বিজ্ঞপ্তি, জাতীয় বিশ্ববিদ্যালয় (NU), শিক্ষা বোর্ডের রুটিন, ফলাফল ও শিক্ষাবৃত্তির অফিশিয়াল নোটিশ পাবলিশ করে।"""
    live_titles_joined = " | ".join(get_live_blogger_titles(50)).lower()
    offset = len(posted_urls) % len(EDUCATION_SOURCES)
    rotated = EDUCATION_SOURCES[offset:] + EDUCATION_SOURCES[:offset]

    for src_cfg in rotated:
        try:
            items = fetch_rss_items(src_cfg["feed_url"], max_age_days=14)
        except Exception as e:
            print(f"[WARN] Failed education feed {src_cfg['feed_url']}: {e}")
            continue

        for item in items:
            link = item["link"]
            raw_title = item["title"]
            if not link or link in posted_urls:
                continue
            try:
                sc = scrape_job_details(link)
                # শুধুমাত্র অক্টোবর ২০২৬ বা সদ্য প্রকাশিত অফিশিয়াল নোটিশ ইমেজ/PDF গ্রহণ করবে
                imgs_2026 = [
                    im for im in sc.get("notice_images", [])
                    if any(k in im.lower() for k in ["/2026/10/", "/2026/11/", "/2026/12/", "2026", "postimg.cc", "nu.ac.bd"])
                ]
                pdfs_2026 = [
                    pf for pf in sc.get("pdf_links", [])
                    if any(k in pf.lower() for k in ["/2026/", "2026", "nu.ac.bd", "oraclecloud", "teletalk", ".gov.bd"])
                ]
                if not imgs_2026 and not pdfs_2026:
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue
                if imgs_2026 and imgs_2026[0] in posted_urls:
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue

                info = extract_structured_job_info(raw_title, sc)
                dl_str = info.get("deadline_bn", "")
                if dl_str and is_deadline_expired(dl_str, raw_title):
                    print(f"[SKIP EXPIRED EDU] Deadline passed ({dl_str}) -> {link}")
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue

                org_bn = info.get("org_name_bn") or "জাতীয় বিশ্ববিদ্যালয় ও শিক্ষা বোর্ড"
                org_en = info.get("org_name_en") or "BD Education Notice"
                t_low = raw_title.lower()
                extra_lbls = []
                is_nu = False
                if "national university" in t_low or "nu " in t_low or "জাতীয় বিশ্ববিদ্যালয়" in t_low or "জাতীয় বিশ্ববিদ্যালয়" in t_low:
                    org_bn = "জাতীয় বিশ্ববিদ্যালয় (NU)"
                    org_en = "National University (NU)"
                    extra_lbls.extend(["nu", "Honour's"])
                    is_nu = True
                if "hsc" in t_low or "এইচএসসি" in t_low or "xi class" in t_low:
                    extra_lbls.append("Hsc")
                if "ssc" in t_low or "এসএসসি" in t_low:
                    extra_lbls.append("SSC")

                notice_type_bn = src_cfg["edu_type"]
                if ("scholarship" in t_low or "বৃত্তি" in t_low) and ("result" in t_low or "ফলাফল" in t_low):
                    notice_type_bn = "শিক্ষাবৃত্তির ফলাফল"
                    extra_lbls.extend(["Result", "exam result"])
                elif "scholarship" in t_low or "বৃত্তি" in t_low or "উপবৃত্তি" in t_low:
                    notice_type_bn = "শিক্ষাবৃত্তি বিজ্ঞপ্তি"
                elif "admission" in t_low or "ভর্তি" in t_low:
                    notice_type_bn = "ভর্তি বিজ্ঞপ্তি"
                elif "routine" in t_low or "রুটিন" in t_low or "সময়সূচি" in t_low:
                    notice_type_bn = "পরীক্ষার সময়সূচি ও রুটিন"
                elif "result" in t_low or "ফলাফল" in t_low or "রেজাল্ট" in t_low:
                    notice_type_bn = "পরীক্ষার ফলাফল"

                slug_part = link.rstrip("/").rsplit("/", 1)[-1]
                if slug_part.replace("-", " ").lower() in live_titles_joined:
                    save_posted_job(link)
                    posted_urls.append(link)
                    continue

                program_bn = "অফিশিয়াল শিক্ষা ও পরীক্ষা বিজ্ঞপ্তি"
                if "masters" in t_low:
                    program_bn = "মাস্টার্স প্রোগ্রাম"
                elif "degree" in t_low:
                    program_bn = "ডিগ্রী (পাস) ও সার্টিফিকেট কোর্স"
                elif "honours" in t_low:
                    program_bn = "অনার্স কোর্স"
                elif "llb" in t_low:
                    program_bn = "এলএলবি (LLB) কোর্স"
                elif "hsc" in t_low:
                    program_bn = "এইচএসসি (HSC) পর্যায়"
                elif "ssc" in t_low:
                    program_bn = "এসএসসি (SSC) পর্যায়"

                edu_pub_iso = sc.get("published_iso") or item.get("pub_iso") or parse_bn_date_to_iso(info.get("start_date_bn", ""))
                pub_dt_bn = format_iso_to_bn_date(edu_pub_iso) or info.get("start_date_bn") or "অক্টোবর ২০২৬"
                if edu_pub_iso and edu_pub_iso.startswith("2026-10"):
                    edu_pub_iso = ""
                raw_off = sc.get("official_site") or info.get("official_website") or ""
                if any(bad in raw_off.lower() for bad in ["examresultbd", "eduresultbd", "bdgovtjob", "prosnosomadhan", "biddabari"]):
                    raw_off = ""
                off_site = raw_off or ("www.nu.ac.bd" if is_nu else "www.shed.gov.bd")

                res, src, b_url = build_and_publish_education_notice(
                    org_bn=org_bn,
                    org_en=org_en,
                    notice_type_bn=notice_type_bn,
                    program_bn=program_bn,
                    publish_date_bn=pub_dt_bn,
                    exam_or_deadline_bn=dl_str or "অফিশিয়াল নোটিশ দেখুন",
                    official_site=off_site,
                    notice_images=imgs_2026 if imgs_2026 else sc.get("notice_images", [])[:1],
                    pdf_links=pdfs_2026,
                    source_url=link,
                    slug_prefix=slug_part,
                    extra_labels=extra_lbls,
                    is_draft=BLOGGER_IS_DRAFT,
                    published_iso=edu_pub_iso,
                )
                print(f"[EDUCATION SUCCESS] Published {raw_title} -> {res.get('url')}")
                save_posted_job(link)
                posted_urls.append(link)
                if imgs_2026:
                    save_posted_job(imgs_2026[0])
                    posted_urls.append(imgs_2026[0])
                ping_google_websub_hub()
                share_to_facebook_page(
                    title=f"{org_bn} — {program_bn} {notice_type_bn} ২০২৬",
                    post_url=res.get("url", ""),
                    banner_url=b_url,
                    summary_text=(
                        f"🏛️ প্রতিষ্ঠান / শিক্ষা বোর্ড: {org_bn}\n"
                        f"📌 নোটিশের ধরন: {notice_type_bn}\n"
                        f"📚 কোর্স / বর্ষ / শ্রেণি: {program_bn}\n"
                        f"📅 প্রকাশের তারিখ: {info.get('start_date_bn') or 'অক্টোবর ২০২৬'}\n"
                        f"⏳ পরীক্ষা / শেষ তারিখ: {dl_str or 'অফিশিয়াল নোটিশ দেখুন'}"
                    ),
                )
                return True
            except Exception as e:
                print(f"[WARN] Failed education notice {link}: {e}")
                continue
    return False


SAPTAHIK_PAPER_SOURCES = [
    {
        "paper_slug": "saptahik-chakrir-khobor",
        "paper_name_bn": "সাপ্তাহিক চাকরির খবর পত্রিকা",
        "paper_name_en": "Saptahik Chakrir Khobor",
        "banner_url": "https://iili.io/njCwcX9.jpg",
        "url": "https://bdgovtjob.net/saptahik-chakrir-khobor/",
        "clean_url": "https://jobs.lekhaporabd.net/saptahik-chakrir-khobor/",
        "extra_labels": ["Saptahik Chakrir Khobor", "Saptahik Job Paper"],
    },
    {
        "paper_slug": "saptahik-chakrir-dak",
        "paper_name_bn": "সাপ্তাহিক চাকরির ডাক পত্রিকা",
        "paper_name_en": "Saptahik Chakrir Dak",
        "banner_url": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh4uDrT14SfeVqcQTkTk-iDQDoSsFAjvJL547YuRB6M3JlGIHxNapFN_kC5fQ5f-Ta8eG51V74MmfgCB23EqjHNwnjcIlKjAvyAY_gxbfNkXZ0AxX9ZfVwXQdTjVRs-N2DPVARR6bzsCHiP-ShIDVJYHrGwWkRHcSzWbcGcrsWjkEetULpkG0HeQUpnyQ/s800/%E0%A6%9A%E0%A6%BE%E0%A6%95%E0%A6%B0%E0%A6%BF%E0%A6%B0-%E0%A6%A1%E0%A6%BE%E0%A6%95-%E0%A6%B8%E0%A6%BE%E0%A6%AA%E0%A7%8D%E0%A6%A4%E0%A6%BE%E0%A6%B9%E0%A6%BF%E0%A6%95-%E0%A6%AA%E0%A6%A4%E0%A7%8D%E0%A6%B0%E0%A6%BF%E0%A6%95%E0%A6%BE-%E0%A7%A8%E0%A7%A6%E0%A7%A8%E0%A7%A8.png",
        "url": "https://jobsnoticebd.com/saptahik-chakrir-dak-potrika/",
        "fallback_url": "https://bdgovtjob.net/saptahik-chakrir-khobor/",
        "clean_url": "https://jobs.lekhaporabd.net/saptahik-chakrir-khobor/",
        "extra_labels": ["saptahik chakrir dakh", "Saptahik Chakrir Khobor", "Saptahik Job Paper"],
    },
    {
        "paper_slug": "saptahik-chakrir-songbad",
        "paper_name_bn": "সাপ্তাহিক চাকরির সংবাদ পত্রিকা",
        "paper_name_en": "saptahik chakrir Songbad",
        "banner_url": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjSd7R1xpU6WOr2urnPZSPzzT4MTTCfpAd5a-aPC8zdwsJVVas_JOM0VXTJRXH6UMVJamb2-rva0LyMSsMnbg8rg4gCFFyqFv1kpmmi5Lfo2NVTVyXDQH2SlFFYMTtbv-cF8VfknyTnJF2qe3O9Y8G71SUOCMzubgca-SuJGKqlmPoCCVm5KG6c6Wk6xw/s720/saptahik%20chakrir%20Songbad%20bdedujob.png",
        "url": "https://jobsnoticebd.com/saptahik-chakrir-songbad-potrika/",
        "fallback_url": "https://bdgovtjob.net/saptahik-chakrir-khobor/",
        "clean_url": "https://jobs.lekhaporabd.net/saptahik-chakrir-khobor/",
        "extra_labels": ["saptahik chakrir Songbad", "Saptahik Job Paper"],
    },
    {
        "paper_slug": "prothom-alo-weekly-job-newspaper",
        "paper_name_bn": "প্রথম আলো সাপ্তাহিক চাকরি বাকরি পত্রিকা",
        "paper_name_en": "Prothom Alo Saptahik Chakri Bakri",
        "banner_url": "https://iili.io/njCwcX9.jpg",
        "url": "https://jobsnoticebd.com/prothom-alo-weekly-job-newspaper/",
        "extra_labels": ["Saptahik Chakrir Khobor", "Saptahik Job Paper"],
    },
]


_EN_TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _extract_issue_date_from_urls(urls: list) -> tuple:
    """
    সাপ্তাহিক পত্রিকার ইমেজ বা পিডিএফ ফাইলের নাম থেকে প্রকৃত প্রকাশের তারিখ (যেমন 23-october-2026) বের করে।
    রিটার্ন করে: (iso_date, dd_mm_yyyy_bn, full_date_bn, full_date_en, match_token)
    """
    en_months = {
        "january": (1, "জানুয়ারি", "January"),
        "february": (2, "ফেব্রুয়ারি", "February"),
        "march": (3, "মার্চ", "March"),
        "april": (4, "এপ্রিল", "April"),
        "may": (5, "মে", "May"),
        "june": (6, "জুন", "June"),
        "july": (7, "জুলাই", "July"),
        "august": (8, "আগস্ট", "August"),
        "september": (9, "সেপ্টেম্বর", "September"),
        "october": (10, "অক্টোবর", "October"),
        "november": (11, "নভেম্বর", "November"),
        "december": (12, "ডিসেম্বর", "December"),
    }
    for u in urls:
        u_dec = urllib.parse.unquote(u).lower()
        m = re.search(
            r"(\d{1,2})[\s\-_]+(january|february|march|april|may|june|july|august|september|october|november|december)[\s\-_]+(202\d)",
            u_dec,
        )
        if m:
            day = int(m.group(1))
            m_key = m.group(2)
            yr = int(m.group(3))
            m_num, m_bn, m_en = en_months[m_key]
            iso_dt = f"{yr:04d}-{m_num:02d}-{day:02d}"
            dd_mm_yyyy_bn = f"{day:02d}/{m_num:02d}/{yr:04d}".translate(_EN_TO_BN)
            full_bn = f"{day:02d} {m_bn} {yr:04d}".translate(_EN_TO_BN)
            full_en = f"{day:02d} {m_en} {yr:04d}"
            return iso_dt, dd_mm_yyyy_bn, full_bn, full_en, f"{day}-{m_key}-{yr}"
    return "", "", "", "", ""


def publish_friday_saptahik_job_papers(posted_urls: list) -> bool:
    """
    প্রতি শুক্রবার প্রকাশিত সাপ্তাহিক চাকরির খবর পত্রিকা, সাপ্তাহিক চাকরির ডাক এবং প্রথম আলো সাপ্তাহিক চাকরি বাকরি পত্রিকা
    স্থায়ী URL (Evergreen URL) থেকে নতুন সংখ্যার তারিখ যাচাই করে স্বয়ংক্রিয়ভাবে ব্লগে পাবলিশ করে।
    """
    live_titles_joined = " | ".join(get_live_blogger_titles(45)).lower()
    now_dt = datetime.now()

    for src in SAPTAHIK_PAPER_SOURCES:
        url = src["url"]
        paper_slug = src["paper_slug"]
        paper_bn = src["paper_name_bn"]
        paper_en = src["paper_name_en"]
        try:
            sc = scrape_job_details(url)
            all_imgs = sc.get("notice_images", [])
            all_pdfs = sc.get("pdf_links", [])
            if not all_imgs:
                continue

            iso_dt, dd_mm_bn, full_bn, full_en, token = _extract_issue_date_from_urls(all_imgs + all_pdfs)
            is_stale = True
            if iso_dt:
                try:
                    issue_dt = datetime.strptime(iso_dt, "%Y-%m-%d")
                    is_stale = (now_dt - issue_dt).days > 6
                except Exception:
                    is_stale = False

            if (not iso_dt or is_stale) and src.get("fallback_url"):
                sc_fb = scrape_job_details(src["fallback_url"])
                fb_imgs = sc_fb.get("notice_images", [])
                fb_pdfs = sc_fb.get("pdf_links", [])
                iso_dt, dd_mm_bn, full_bn, full_en, token = _extract_issue_date_from_urls(fb_imgs + fb_pdfs)
                if iso_dt:
                    all_imgs = fb_imgs
                    all_pdfs = fb_pdfs
                    try:
                        issue_dt = datetime.strptime(iso_dt, "%Y-%m-%d")
                        is_stale = (now_dt - issue_dt).days > 6
                    except Exception:
                        is_stale = False

            if not iso_dt or is_stale:
                continue

            dedup_key = f"{paper_slug}#{iso_dt}"
            if dedup_key in posted_urls:
                continue

            # যদি ইতিমধ্যে এই তারিখের এই পত্রিকা ব্লগে লাইভ থাকে তবে স্কিপ করবে
            paper_kw = "সংবাদ" if "সংবাদ" in paper_bn else ("ডাক" if "ডাক" in paper_bn else ("প্রথম আলো" if "প্রথম আলো" in paper_bn else "খবর"))
            if (dd_mm_bn in live_titles_joined or full_bn in live_titles_joined) and paper_kw in live_titles_joined:
                save_posted_job(dedup_key)
                posted_urls.append(dedup_key)
                continue

            # শুধুমাত্র এই সপ্তাহের সংখ্যার ইমেজ ও পিডিএফ ফিল্টার করা
            day_str = str(int(iso_dt.split("-")[2]))
            cur_imgs = [im for im in all_imgs if day_str in urllib.parse.unquote(im)] or all_imgs[:4]
            cur_pdfs = [pf for pf in all_pdfs if day_str in urllib.parse.unquote(pf)] or all_pdfs[:1]

            # ওয়াটারমার্ক-মুক্ত পরিষ্কার ইমেজ পাওয়া গেলে সেটি অগ্রাধিকার দেওয়া
            if src.get("clean_url"):
                try:
                    sc_cl = scrape_job_details(src["clean_url"])
                    cl_imgs = [
                        im for im in sc_cl.get("notice_images", [])
                        if (iso_dt in im or "imgbox.com" in im) and not im.endswith(".webp") and not im.endswith(".gif")
                    ]
                    if len(cl_imgs) >= 4:
                        cur_imgs = cl_imgs[:4]
                except Exception:
                    pass

            # ছবিগুলো আমাদের নিজস্ব CDN-এ আপলোড করা যাতে কখনো ব্রোকেন না হয়
            os.makedirs(BANNERS_DIR, exist_ok=True)
            uploaded_pages = []
            for idx, im_u in enumerate(cur_imgs[:6], 1):
                try:
                    fname = f"{paper_slug}-{iso_dt}-page-{idx}.jpg"
                    lpath = os.path.join(BANNERS_DIR, fname)
                    req = urllib.request.Request(im_u, headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=20) as r, open(lpath, "wb") as f:
                        f.write(r.read())
                    uploaded_pages.append(upload_local_banner_to_cdn(lpath, fname))
                except Exception:
                    uploaded_pages.append(im_u)

            banner_url = src.get("banner_url", "https://iili.io/njCwcX9.jpg")
            if paper_slug == "saptahik-chakrir-songbad":
                post_title = f"{paper_bn} {full_bn} । {full_en} {paper_en}"
            else:
                post_title = f"{paper_bn} {dd_mm_bn} ইং প্রকাশিত । {full_en} {paper_en}"

            fb_saptahik_div = make_fb_rss_seo_div(
                [
                    f"📢 {post_title}",
                    f"📰 পত্রিকার নাম: {paper_bn} ({paper_en})",
                    f"📅 প্রকাশের তারিখ: {full_bn} ({dd_mm_bn} ইং)",
                    "💼 চাকরির ধরন: সরকারি, বেসরকারি, ব্যাংক ও এনজিও নিয়োগ বিজ্ঞপ্তি",
                    "📄 ফরম্যাট: এইচডি ইমেজ (HD Pages) ও সম্পূর্ণ PDF ডাউনলোড",
                    "👉 সম্পূর্ণ পত্রিকা পড়ুন ও PDF ডাউনলোড করুন নিচের লিংকে:",
                ],
                ["#SaptahikChakrirKhobor", "#WeeklyJobNewspaper", "#সাপ্তাহিক_চাকরির_খবর", "#চাকরির_পত্রিকা", "#bdedujob"],
            )

            pages_html = "\n".join(
                f'''  <div class="separator" style="clear: both; text-align: center; margin: 18px 0;">
    <a href="{u}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title} - Page {i}" title="{post_title} - Page {i}" border="0" src="{u}" style="max-width: 100%; height: auto; border: 1px solid #cbd5e1; border-radius: 6px;" />
    </a>
  </div>'''
                for i, u in enumerate(uploaded_pages, 1)
            )

            pdf_href = cur_pdfs[0] if cur_pdfs else uploaded_pages[0]

            post_html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 20px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{post_title}" title="{post_title}" border="0" data-original-height="630" data-original-width="1200" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 8px;" />
    </a>
  </div>
  {fb_saptahik_div}
  <p style="text-align: justify;">
    <span style="color: #38761d;"><b>{paper_en} ({dd_mm_bn}):</b></span>
    সকল সরকারি ও বেসরকারি চাকরির খবর সম্বলিত পুরো সপ্তাহের চাকরির খবর <b>{paper_bn} {dd_mm_bn} ইং ({full_bn})</b> সংখ্যাটি আজ শুক্রবার সকালে প্রকাশিত হয়েছে। গণপ্রজাতন্ত্রী বাংলাদেশ সরকারের বিভিন্ন মন্ত্রণালয়, অধিদপ্তর, কমিশন, কর্তৃপক্ষ ও বিভাগসহ ব্যাংক, এনজিও এবং বেসরকারি কোম্পানির চলমান সকল নিয়োগ বিজ্ঞপ্তি এই সংখ্যায় একত্রে সংকলিত করা হয়েছে।
  </p>
  <!--more-->

  <p style="text-align: justify;">
    চাকরিপ্রার্থীদের সুবিধার্থে এই পোস্টে আমরা <b>{paper_bn} ({full_bn})</b>-এর প্রতিটি পৃষ্ঠার স্পষ্ট এইচডি (HD) ইমেজ এবং সম্পূর্ণ পিডিএফ (PDF) ফাইল সংযুক্ত করেছি। এছাড়াও নিচের ডাউনলোড বাটন থেকে এক ক্লিকে সম্পূর্ণ পত্রিকার PDF ডাউনলোড করে অফলাইনে পড়তে পারবেন।
  </p>

  <div style="background: #f0fdf4; border-left: 4px solid #38761d; padding: 14px 18px; margin: 18px 0; border-radius: 6px; text-align: center;">
    <p style="margin: 0 0 8px 0; font-weight: bold;">
      <a href="{PLAY_STORE_URL}" rel="nofollow noopener" target="_blank" style="color: #15803d; text-decoration: underline;">
        📱 প্রতি শুক্রবারের সাপ্তাহিক চাকরির পত্রিকা ও প্রতিদিনের জব সার্কুলার সবার আগে পেতে আমাদের অফিসিয়াল অ্যাপটি ইনস্টল করুন!
      </a>
    </p>
  </div>

  <h2 style="text-align: center; color: #38761d; font-size: 21px; border-bottom: 2px solid #38761d; padding-bottom: 6px; margin-top: 24px;">
    এক নজরে {paper_bn} — {full_bn} ({full_en})
  </h2>

  <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 16px;" border="1" cellpadding="8">
    <tbody>
      <tr style="background-color: #38761d; color: #ffffff;">
        <th colspan="2" style="text-align: center; padding: 10px;">সাপ্তাহিক চাকরির পত্রিকার সংক্ষিপ্ত বিবরণ</th>
      </tr>
      <tr>
        <td style="width: 38%; font-weight: bold; background-color: #f8fafc;">পত্রিকার নাম</td>
        <td>{paper_bn} ({paper_en})</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">প্রকাশের তারিখ</td>
        <td><b>{dd_mm_bn} ইং ({full_bn}, শুক্রবার)</b></td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">চাকরির ধরন</td>
        <td>সরকারি চাকরি, বেসরকারি চাকরি, ব্যাংক ও এনজিও নিয়োগ</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">মোট পৃষ্ঠা সংখ্যা</td>
        <td>{str(len(uploaded_pages)).translate(_EN_TO_BN)} টি পৃষ্ঠা (HD Image + Full PDF)</td>
      </tr>
      <tr>
        <td style="font-weight: bold; background-color: #f8fafc;">ওয়েবসাইট</td>
        <td><a href="{SITE_URL}"><b>{SITE_DISPLAY}</b></a></td>
      </tr>
    </tbody>
  </table>

  <h3 style="color: #38761d; font-size: 19px; margin-top: 24px;">
    {paper_bn} ({dd_mm_bn} ইং) — সকল পৃষ্ঠা নিচে দেখুন:
  </h3>

{pages_html}

  <div style="text-align: center; margin: 26px 0;">
    <a href="{pdf_href}" rel="nofollow noopener" target="_blank" style="display: inline-block; background-color: #38761d; color: #ffffff; font-size: 20px; font-weight: bold; padding: 12px 34px; border-radius: 30px; text-decoration: none; box-shadow: 0 4px 10px rgba(56,118,29,0.3);">
      📥 সম্পূর্ণ পত্রিকার PDF ডাউনলোড করুন ({paper_bn} {dd_mm_bn})
    </a>
  </div>
  <style>.fb-rss-seo-summary{{display:none!important;}}</style>
</div>"""

            labels = ["all", "All Jobs", "Govt Jobs", "Privet Jobs", "job", "pdf", "pdf Zone"]
            for el in src.get("extra_labels", []):
                if el in ALLOWED_BLOGGER_LABELS and el not in labels:
                    labels.append(el)

            res = publish_to_blogger(
                title=post_title,
                html_content=post_html,
                labels=labels,
                is_draft=BLOGGER_IS_DRAFT,
                published_iso="",
            )
            print(f"[SAPTAHIK SUCCESS] Published {post_title} -> {res.get('url')}")
            save_posted_job(dedup_key)
            posted_urls.append(dedup_key)
            ping_google_websub_hub()
            share_to_facebook_page(
                title=post_title,
                post_url=res.get("url", ""),
                banner_url=banner_url,
                summary_text=(
                    f"📰 পত্রিকা: {paper_bn}\n"
                    f"📅 প্রকাশের তারিখ: {dd_mm_bn} ইং ({full_bn})\n"
                    f"💼 ক্যাটাগরি: সরকারি, বেসরকারি, ব্যাংক ও এনজিও চাকরি\n"
                    f"📄 ফরম্যাট: সম্পূর্ণ HD ইমেজ ও PDF ফাইল"
                ),
            )
            return True
        except Exception as e:
            print(f"[WARN] Failed saptahik paper {url}: {e}")
            continue
    return False


def main():
    posted_urls = load_posted_jobs()
    if not BLOGGER_BLOG_ID:
        publish_next_live_job_circular(posted_urls)
        return

    # সবার আগে শুক্রবারের সাপ্তাহিক চাকরির পত্রিকা (FRIDAY_SAPTAHIK_PAPER), এরপর নতুন প্রকাশিত চাকরির বিজ্ঞপ্তি (LIVE_JOB_CIRCULAR)
    # এবং শিক্ষা ও ভর্তি নোটিশ (EDUCATION_NOTICE) চেক করবে, যাতে আজকের কোনো নতুন সার্কুলার বা সাপ্তাহিক পত্রিকা কখনোই পেছনে পড়ে না থাকে।
    # অগ্রাধিকার (সবার আগে সময়-সংবেদনশীল আপডেট): আজকের পরীক্ষার প্রশ্ন সমাধান এবং
    # শিক্ষা নোটিশ/রুটিন/ফলাফল (SSC, HSC, NU, Degree, JSC) — এরপর চাকরির বিজ্ঞপ্তি, সবার শেষে BCS আর্কাইভ
    live_tasks = [
        ("JOB_QUESTION_SOLUTION", publish_next_job_question_solution),
        ("EDUCATION_NOTICE", publish_next_education_notice),
    ]
    if len(posted_urls) % 2 == 1:
        live_tasks.reverse()

    ordered_tasks = (
        [("FRIDAY_SAPTAHIK_PAPER", publish_friday_saptahik_job_papers)]
        + live_tasks
        + [
            ("LIVE_JOB_CIRCULAR", publish_next_live_job_circular),
            ("BCS_QUESTION_SOLUTION", publish_next_bcs_question_solution),
        ]
    )

    published_count = 0
    for task_name, task_fn in ordered_tasks:
        if published_count >= MAX_POSTS_PER_RUN:
            break
        print(f"[SCHEDULER] Running slot: {task_name}")
        if task_fn(posted_urls):
            published_count += 1


if __name__ == "__main__":
    main()
