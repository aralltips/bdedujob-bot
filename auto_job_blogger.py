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
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "100067891540585")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
MAX_POSTS_PER_RUN = 1

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
    "Saptahik Job Paper",
    "all",
    "exam result",
    "job",
    "nu",
    "pdf",
    "pdf Zone",
]

EDUCATION_SOURCES = [
    {
        "name": "National University (NU Routine, Result & Notice)",
        "feed_url": "https://eduresultbd.com/category/national-university/feed/",
        "edu_type": "জাতীয় বিশ্ববিদ্যালয় নোটিশ",
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


BUILTIN_POSTED_URLS = [
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
    "https://biddabari.com/11-20-Grade-question-bank/cabinet-division-question-
