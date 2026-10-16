#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BD Education & Job Info (https://bdedujob.blogspot.com/)
100% Automated SEO & AdSense-Ready Job Circular Scraper, Banner Designer & Blogger Auto-Publisher
"""

import os
import re
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

# "false" মানে সরাসরি Publish (Direct SEO Publish), "true" মানে Draft হিসেবে সেভ হবে
BLOGGER_IS_DRAFT = os.getenv("BLOGGER_IS_DRAFT", "false").lower() == "true"

# ইউনিক ও AdSense-safe আর্টিকেল রিরাইটের জন্য ফ্রি Google Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ব্যানার ছবি হোস্ট করার জন্য ফ্রি ImgBB API Key (https://api.imgbb.com/)
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

# প্রতিবার স্ক্রিপ্ট রান করলে সর্বোচ্চ কয়টি নতুন পোস্ট করবে
MAX_POSTS_PER_RUN = int(os.getenv("MAX_POSTS_PER_RUN", "2"))

# আপনার সাইট ও অ্যাপের স্থায়ী তথ্য
SITE_URL = "https://bdedujob.blogspot.com"
SITE_DISPLAY = "www.bdedujob.blogspot.com"
PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=com.rakibtech.jobcircular"

# বাংলাদেশের জনপ্রিয় সরকারি, বেসরকারি ও ব্যাংক জব পোর্টাল সোর্সসমূহ
JOB_SOURCES = [
    {
        "name": "BD Govt Job",
        "feed_url": "https://bdgovtjob.net/feed/",
        "default_label": "Govt Jobs",
    },
    {
        "name": "eJobs Circular",
        "feed_url": "https://ejobscircular.com/feed/",
        "default_label": "Govt Jobs",
    },
    {
        "name": "KF Planet Jobs",
        "feed_url": "https://kfplanet.com/feed/",
        "default_label": "All Jobs",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


# ==============================================================================
# ২. ডুপ্লিকেট চেক ডাটাবেস (posted_jobs.json)
# ==============================================================================
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
        # সর্বশেষ ৫০০টি লিংক সংরক্ষণ করবে
        posted = posted[-500:]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(posted, f, ensure_ascii=False, indent=2)


# ==============================================================================
# ৩. সোর্স সাইট থেকে জব সার্কুলার ও অফিসিয়াল নোটিশের ছবি সংগ্রহ
# ==============================================================================
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
    content_div = (
        soup.find(class_="entry-content")
        or soup.find(class_="td-post-content")
        or soup.find("article")
        or soup.body
    )

    raw_text = content_div.get_text("\n", strip=True) if content_div else ""

    # অফিসিয়াল সার্কুলারের ছবিগুলো আলাদা করা (লোগো বা আইকন বাদ দিয়ে)
    notice_images = []
    if content_div:
        for img in content_div.find_all("img"):
            src = img.get("data-src") or img.get("data-lazy-src") or img.get("src") or ""
            if not src or src.startswith("data:"):
                continue
            low = src.lower()
            if any(skip in low for skip in ["logo", "icon", "button", "apply", "banner", "avatar", "gravatar"]):
                continue
            if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                if src not in notice_images:
                    notice_images.append(src)

    # টেলিটক বা অফিসিয়াল আবেদন লিংক খুঁজে বের করা
    apply_url = ""
    official_site = ""
    if content_div:
        for a in content_div.find_all("a", href=True):
            href = a["href"].strip()
            if "teletalk.com.bd" in href and not apply_url:
                apply_url = href
            elif (".gov.bd" in href or ".org.bd" in href or ".edu.bd" in href) and not official_site:
                official_site = href

    return {
        "raw_text": raw_text[:8000],
        "notice_images": notice_images[:6],
        "apply_url": apply_url,
        "official_site": official_site,
    }


# ==============================================================================
# ৪. AI (Gemini API) ও স্মার্ট পার্সার দিয়ে তথ্য এক্সট্রাক্ট ও ইউনিক রিরাইট
# ==============================================================================
def extract_structured_job_info(raw_title: str, scraped: dict) -> dict:
    """
    Gemini API থাকলে ১০০% ইউনিক ও AdSense-বান্ধব বাংলা কনটেন্ট তৈরি করবে।
    না থাকলে স্মার্ট রেগুলার এক্সপ্রেশন দিয়ে তথ্য সাজিয়ে নেবে।
    """
    raw_text = scraped["raw_text"]

    # Default fallback structure extracted from text
    en_match = re.search(r"([A-Za-z0-9\-\s\(\)&]+Job Circular\s*\d{4})", raw_title)
    title_en = en_match.group(1).strip() if en_match else "BD Govt Job Circular 2026"
    short_match = re.search(r"\b([A-Z]{2,10})\b", title_en)
    short_code = short_match.group(1) if short_match else "JOB"

    bn_part = re.sub(r"[A-Za-z0-9\-\|]+Job Circular.*", "", raw_title).strip(" -–|")
    org_name_bn = re.sub(r"নিয়োগ বিজ্ঞপ্তি.*|নিয়োগ বিজ্ঞপ্তি.*", "", bn_part).strip() or bn_part

    vac_match = re.search(r"(\d+|[\u09e6-\u09ef]+)\s*(?:টি পদে|পদে|জন)", raw_title + " " + raw_text[:1000])
    vacancy_bn = f"{vac_match.group(1)} জন" if vac_match else "বিজ্ঞপ্তিতে দেখুন"

    info = {
        "post_title": f"{org_name_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ - {title_en}",
        "org_name_bn": org_name_bn,
        "org_name_en": title_en.replace("Job Circular 2026", "").replace("Job Circular 2025", "").strip(),
        "short_code": short_code,
        "job_type_bn": "সরকারি চাকরি (Government Job)",
        "banner_badge_bn": "সরকারি চাকরি",
        "blogger_labels": ["All Jobs", "Govt Jobs"],
        "vacancy_bn": vacancy_bn,
        "qualification_bn": "৮ম / এসএসসি / এইচএসসি / স্নাতক পাশ",
        "age_limit_bn": "১৮ থেকে ৩২ বছর (বিজ্ঞপ্তির শর্তানুযায়ী)",
        "salary_bn": "জাতীয় বেতন স্কেল ২০১৫ অনুযায়ী",
        "fee_bn": "১১২/- থেকে ২২৩/- টাকা (বিজ্ঞপ্তি অনুযায়ী)",
        "start_date_bn": "বিজ্ঞপ্তিতে দেখুন",
        "deadline_bn": "বিজ্ঞপ্তিতে উল্লেখিত তারিখের মধ্যে",
        "official_site": scraped["official_site"] or "অফিসিয়াল বিজ্ঞপ্তিতে দেখুন",
        "apply_url": scraped["apply_url"] or scraped["official_site"] or SITE_URL,
        "intro_paragraph_1": (
            f"গণপ্রজাতন্ত্রী বাংলাদেশ সরকারের আওতাধীন <b>{org_name_bn}</b> রাজস্ব খাতভুক্ত শূন্য পদসমূহে "
            f"সরাসরি জনবল নিয়োগের লক্ষ্যে প্রকৃত বাংলাদেশী নাগরিকদের নিকট হতে অনলাইনে দরখাস্ত আহ্বান করেছে। "
            f"যারা দীর্ঘদিন ধরে একটি মানসম্মত সরকারি চাকরির অপেক্ষায় ছিলেন, তাদের জন্য এই নিয়োগ বিজ্ঞপ্তিটি একটি চমৎকার সুযোগ।"
        ),
        "intro_paragraph_2": (
            f"এই পোস্টের মাধ্যমে আমরা <b>{org_name_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ ({title_en})</b>-এর পদের নাম, পদসংখ্যা, "
            f"শিক্ষাগত যোগ্যতা, বেতন স্কেল, বয়সসীমা, অনলাইনে আবেদন ফরম পূরণের নিয়ম, টেলিটক প্রিপেইড সিমের মাধ্যমে "
            f"আবেদন ফি পরিশোধের এসএমএস পদ্ধতি এবং প্রবেশপত্র ডাউনলোড সম্পর্কে বিস্তারিত আলোচনা করব।"
        ),
        "posts_breakdown": [
            {
                "post_name": "বিজ্ঞপ্তিতে বর্ণিত বিভিন্ন ক্যাটাগরির পদসমূহ",
                "vacancy": vacancy_bn,
                "qualification": "স্বীকৃত বোর্ড বা বিশ্ববিদ্যালয় হতে ৮ম/এসএসসি/এইচএসসি/স্নাতক বা সমমান পরীক্ষায় উত্তীর্ণ।",
                "salary": "জাতীয় বেতন স্কেল ২০১৫ অনুযায়ী সংশ্লিষ্ট গ্রেড",
            }
        ],
    }

    if GEMINI_API_KEY:
        try:
            prompt = f"""
You are an expert Bangladeshi job portal editor for bdedujob.blogspot.com.
Extract accurate job circular information from the text below and return ONLY valid JSON with these exact keys:
- post_title: Format "<Bangla Org Name> নিয়োগ বিজ্ঞপ্তি ২০২৬ - <Short English Name> Job Circular 2026"
- org_name_bn: Bangla organization name
- org_name_en: English organization name
- short_code: Short uppercase code (e.g. BPATC, CSMUN, RPCL)
- job_type_bn: "সরকারি চাকরি (Government Job)" or "বেসরকারি চাকরি (Private Job)" or "ব্যাংক জব (Bank Job)"
- banner_badge_bn: "সরকারি চাকরি" or "বেসরকারি চাকরি" or "ব্যাংক জব"
- blogger_labels: Array of matching labels from ["All Jobs", "Govt Jobs", "Privet Jobs", "Bank Jobs", "Saptahik Job Paper"]
- vacancy_bn: Total vacancies in Bangla (e.g. "৩৯ জন")
- qualification_bn: Short qualification summary in Bangla (e.g. "৮ম / এসএসসি / এইচএসসি / স্নাতক")
- age_limit_bn: Age limit in Bangla
- salary_bn: Salary range in Bangla
- fee_bn: Application fee in Bangla
- start_date_bn: Application start date & time in Bangla
- deadline_bn: Application deadline date & time in Bangla
- official_site: Official website URL
- apply_url: Online application URL (Teletalk or official link)
- intro_paragraph_1: 100% unique, natural Bangla opening paragraph (3-4 sentences) about this recruitment.
- intro_paragraph_2: 100% unique Bangla second paragraph explaining what candidates will learn in this article.
- posts_breakdown: List of up to 6 objects with keys {{"post_name", "vacancy", "qualification", "salary"}} in Bangla.

Source Title: {raw_title}
Source Text:
{raw_text[:4500]}
"""
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }).encode("utf-8")
            ai_data = None
            for model_name in ["gemini-flash-lite-latest", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]:
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
                    print(f"[AI] Successfully rewrote job circular using {model_name}!")
                    break
                except Exception as model_err:
                    print(f"[WARN] Model {model_name} failed ({model_err}), trying next...")
            if ai_data:
                info.update({k: v for k, v in ai_data.items() if v})
        except Exception as e:
            print(f"[WARN] Gemini AI fallback triggered: {e}")

    return info


# ==============================================================================
# ৫. ব্যানার তৈরি ও ইমেজ হোস্টিং (ImgBB অথবা Base64 Data URI)
# ==============================================================================
def create_and_upload_banner(info: dict) -> str:
    os.makedirs(BANNERS_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", info["short_code"].lower()).strip("-") or "job"
    filename = f"{slug}-job-circular-2026-{int(datetime.now().timestamp())}.png"
    local_path = os.path.join(BANNERS_DIR, filename)

    generate_job_banner(
        org_name_bn=info["org_name_bn"],
        org_short_en=f"{info['short_code']} JOB 2026",
        vacancy_bn=info["vacancy_bn"],
        qualification_bn=info["qualification_bn"],
        deadline_bn=info["deadline_bn"],
        job_type_bn=info.get("banner_badge_bn", "সরকারি চাকরি"),
        output_path=local_path,
    )

    # ১. যদি IMGBB_API_KEY দেওয়া থাকে
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
            print(f"[WARN] ImgBB upload failed, trying FreeImage.host: {e}")

    # ২. বিল্ট-ইন ফ্রি ইমেজ CDN হোস্টিং (FreeImage.host / iili.io - কোনো আলাদা API Key লাগবে না!)
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
        print(f"[WARN] FreeImage upload failed, using GitHub fallback: {e}")

    # ৩. GitHub Actions এ রান হলে অটোমেটিক GitHub CDN লিংক তৈরি করবে
    gh_repo = os.getenv("GITHUB_REPOSITORY", "")
    gh_branch = os.getenv("GITHUB_REF_NAME", "main")
    if gh_repo:
        return f"https://raw.githubusercontent.com/{gh_repo}/{gh_branch}/generated_banners/{filename}"

    return local_path


# ==============================================================================
# ৬. আপনার ব্লগের হুবহু স্টাইল + ১০০% SEO ও AdSense-উপযোগী HTML জেনারেটর
# ==============================================================================
def build_bdedujob_post_html(info: dict, banner_url: str, notice_images: list) -> str:
    org_bn = info["org_name_bn"]
    org_en = info["org_name_en"]
    short_code = info["short_code"].upper()
    title_full = info["post_title"]
    apply_url = info["apply_url"]
    official_site = info["official_site"]

    # পদের তালিকা টেবিল তৈরি
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

    # অফিসিয়াল নোটিশের ছবিগুলো যুক্ত করা (SEO Alt ও Title ট্যাগসহ)
    notice_imgs_html = ""
    for i, img_url in enumerate(notice_images, start=1):
        alt_txt = f"{org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ - {org_en} Job Circular 2026 Page {i}"
        notice_imgs_html += f"""
        <div class="separator" style="clear: both; text-align: center; margin: 18px 0;">
          <a href="{img_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;" target="_blank" rel="noopener">
            <img alt="{alt_txt}" title="{alt_txt}" border="0" loading="lazy" src="{img_url}" style="max-width: 100%; height: auto; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);" />
          </a>
        </div>"""

    # Google JobPosting Schema Markup (JSON-LD)
    today_iso = datetime.now().strftime("%Y-%m-%d")
    schema_json = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": title_full,
        "description": f"{org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬ ({org_en} Job Circular 2026) বিস্তারিত তথ্য ও অনলাইন আবেদন পদ্ধতি।",
        "datePosted": today_iso,
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
                "addressLocality": "Dhaka",
                "addressCountry": "BD",
            },
        },
    }
    schema_script = f'<script type="application/ld+json">{json.dumps(schema_json, ensure_ascii=False)}</script>'

    html = f"""<div class="post-body entry-content" style="font-size: 16px; line-height: 1.75; color: #1e293b;">
  <!-- ১. অটো-জেনারেটেড থাম্বনেইল ব্যানার ইমেজ (SEO Alt & Title সহ) -->
  <div class="separator" style="clear: both; text-align: center; margin-bottom: 20px;">
    <a href="{banner_url}" imageanchor="1" style="margin-left: 1em; margin-right: 1em;">
      <img alt="{title_full}" title="{title_full}" border="0" data-original-height="630" data-original-width="1200" loading="lazy" src="{banner_url}" style="max-width: 100%; height: auto; border-radius: 8px;" />
    </a>
  </div>

  <!-- ২. ভূমিকা (আপনার ব্লগের সবুজ কালার স্টাইল ও জাস্টিফাইড টেক্সট) -->
  <p style="text-align: justify;">
    <span style="color: #38761d;"><b>{org_en} Job Circular 2026:</b></span>
    {info['intro_paragraph_1']}
  </p>

  <p style="text-align: justify;">
    {info['intro_paragraph_2']}
  </p>

  <p style="text-align: justify;">
    নিম্নবর্ণিত শর্তাবলী আবেদন ফরম পূরণ এবং পরীক্ষায় অংশগ্রহণের ক্ষেত্রে অবশ্যই অনুসরণ করতে হবে। নিচে আপনাদের সুবিধার্থে নিয়োগ বিজ্ঞপ্তিটির সম্পূর্ণ তথ্য তুলে ধরা হলো। আগ্রহ ও যোগ্যতা থাকলে আপনিও নির্দিষ্ট সময়ের মধ্যে আবেদন করতে পারেন।
  </p>

  <!-- ৩. আপনার অফিসিয়াল অ্যাপ ও ওয়েবসাইট প্রমোশন বক্স -->
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

  <!-- ৪. কাজের সংক্ষিপ্ত বিবরণ (Job Summary) -->
  <h2 style="text-align: center; color: #38761d; font-size: 22px; border-bottom: 2px solid #38761d; padding-bottom: 6px; margin-top: 26px;">
    কাজের সংক্ষিপ্ত বিবরণ ({short_code} Job Summary)
  </h2>

  <ul style="line-height: 1.9;">
    <li><b>প্রতিষ্ঠানের নাম (Name of the Organization):</b> {org_bn} – {org_en}</li>
    <li><b>চাকরির ধরণ (Type of Job):</b> {info['job_type_bn']}</li>
    <li><b>মোট শূন্যপদ (Total Vacancy):</b> {info['vacancy_bn']}</li>
    <li><b>চাকরির প্রকৃতি (Job Nature):</b> ফুল টাইম (স্থায়ী/অস্থায়ী)</li>
    <li><b>বয়সসীমা (Age Limitation):</b> {info['age_limit_bn']}</li>
    <li><b>শিক্ষাগত যোগ্যতা (Qualification):</b> {info['qualification_bn']}</li>
    <li><b>বেতন স্কেল (Salary Scale):</b> {info['salary_bn']}</li>
    <li><b>লিঙ্গ (Gender):</b> নারী ও পুরুষ উভয়ই আবেদন করতে পারবেন (Men and Women Both)</li>
    <li><b>কর্মস্থল (Job Location):</b> বাংলাদেশের যেকোনো স্থান (বিজ্ঞপ্তি অনুযায়ী)</li>
    <li><b>আবেদনের ফি (Application Fee):</b> {info['fee_bn']}</li>
    <li><b>আবেদন শুরুর তারিখ (Application Start):</b> {info['start_date_bn']}</li>
    <li><b>আবেদনের শেষ তারিখ (Application Deadline):</b> <span style="color: #dc2626; font-weight: bold;">{info['deadline_bn']}</span></li>
    <li><b>অফিসিয়াল ওয়েবসাইট (Official Website):</b> <span style="color: #0000ee;"><b><u>{official_site}</u></b></span></li>
  </ul>

  <!-- ৫. পদের নাম, পদসংখ্যা ও যোগ্যতার বিস্তারিত তালিকা (AdSense ইউনিক টেক্সট টেবিল) -->
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    {org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬: পদের নাম ও যোগ্যতা
  </h2>
  <p style="text-align: justify;">
    {org_bn}-এর প্রকাশিত বিজ্ঞপ্তি অনুযায়ী কোন পদে কতজন নিয়োগ দেওয়া হবে এবং আবেদনের জন্য কী কী শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা প্রয়োজন, তার সংক্ষিপ্ত বিবরণ নিচের ছকে দেওয়া হলো:
  </p>

  <div style="overflow-x: auto; margin: 16px 0;">
    <table style="width: 100%; border-collapse: collapse; font-size: 15px;">
      <thead>
        <tr style="background-color: #38761d; color: #ffffff;">
          <th style="border: 1px solid #cbd5e1; padding: 10px;">ক্রমিক</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">পদের নাম</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">পদসংখ্যা</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা</th>
          <th style="border: 1px solid #cbd5e1; padding: 10px;">বেতন স্কেল</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <!-- ৬. আবেদনের সময়সীমা ও অফিসিয়াল বিজ্ঞপ্তির ছবি -->
  <div style="background: #fffbeb; border: 1px solid #f59e0b; padding: 14px 18px; border-radius: 6px; margin: 22px 0;">
    <div><b>আবেদনের শুরু সময়:</b> {info['start_date_bn']}</div>
    <div><b>আবেদনের শেষ সময়:</b> <span style="color: #b91c1c; font-weight: bold;">{info['deadline_bn']}</span></div>
  </div>

  <h3 style="color: #38761d; font-size: 19px; margin-top: 24px;">
    বিস্তারিত জানতে অফিসিয়াল বিজ্ঞপ্তি দেখুন:
  </h3>

  {notice_imgs_html}

  <!-- ৭. অনলাইনে আবেদন করার বাটন (AdSense-safe ডাইরেক্ট লিংক) -->
  <div style="text-align: center; margin: 26px 0;">
    <a href="{apply_url}" rel="nofollow noopener" target="_blank" style="display: inline-block; background-color: #38761d; color: #ffffff; font-size: 20px; font-weight: bold; padding: 12px 34px; border-radius: 30px; text-decoration: none; box-shadow: 0 4px 10px rgba(56,118,29,0.3);">
      👉 অনলাইনে আবেদন করুন (Apply Now)
    </a>
  </div>

  <!-- ৮. অনলাইনে আবেদন পদ্ধতি ও টেলিটক SMS নিয়ম -->
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    আবেদন পদ্ধতি (How to Apply {short_code} Job Circular 2026)
  </h2>
  <p style="text-align: justify;">
    আপনি যদি <b>{org_bn}</b> নিয়োগ বিজ্ঞপ্তিটিতে আবেদন করার জন্য একজন যোগ্য ও আগ্রহী প্রার্থী হন, তাহলে দেরি না করে কর্তৃপক্ষের দেওয়া নির্দেশনা অনুযায়ী নির্দিষ্ট সময়ের মধ্যে অনলাইনে (<a href="{apply_url}" rel="nofollow noopener" target="_blank">{apply_url}</a>) মাধ্যমে আবেদন সম্পন্ন করুন।
  </p>

  <ul>
    <li><b>1st Step:</b> Online Apply (অনলাইনে আবেদন ফরম পূরণ)</li>
    <li><b>2nd Step:</b> Payment of Application Fees (টেলিটক প্রিপেইড সিমের মাধ্যমে ফি পরিশোধ)</li>
  </ul>

  <h3 style="text-align: center; color: #38761d; font-size: 19px;">
    অনলাইনে আবেদন ফরম পূরণের ধাপসমূহ – {short_code} Online Apply
  </h3>
  <ul>
    <li>প্রথমে ভিজিট করুন: <b>{apply_url}</b></li>
    <li>এখন <b>“Application Form (Click here to apply Online)”</b> অপশনে ক্লিক করুন।</li>
    <li>আপনি যে পদে আবেদন করতে চান সেই <b>Post</b> সিলেক্ট করে <b>Next</b> বাটনে ক্লিক করুন।</li>
    <li>Premium Member না হলে <b>“No”</b> সিলেক্ট করে <b>Next</b> চাপুন।</li>
    <li>আপনার সকল ব্যক্তিগত ও শিক্ষাগত তথ্য দিয়ে সঠিকভাবে Application Form পূরণ করে Next-এ ক্লিক করুন।</li>
    <li>নির্ধারিত সাইজে আপনার রঙিন ছবি এবং স্বাক্ষর (Photo &amp; Signature) আপলোড করুন:
      <ul>
        <li><b>ছবি (Photo):</b> 300×300 pixel, সর্বোচ্চ 100 KB, JPG ফরম্যাট।</li>
        <li><b>স্বাক্ষর (Signature):</b> 300×80 pixel, সর্বোচ্চ 60 KB, JPG ফরম্যাট।</li>
      </ul>
    </li>
    <li>সব তথ্য যাচাই করে <b>Submit</b> বাটনে ক্লিক করুন এবং <b>Applicant's Copy</b> প্রিন্ট বা PDF ডাউনলোড করে সংরক্ষণ করুন।</li>
  </ul>

  <p style="text-align: justify; color: #dc2626; font-weight: bold;">
    বি.দ্র: অনলাইনে আবেদন ফরম সাবমিট করার পরবর্তী ৭২ ঘণ্টার মধ্যে যেকোনো টেলিটক প্রিপেইড (Teletalk Prepaid) মোবাইল নাম্বারের মাধ্যমে নির্ধারিত আবেদন ফি পরিশোধ করতে হবে।
  </p>

  <h3 style="text-align: center; color: #38761d; font-size: 19px;">
    আবেদন ফি পরিশোধের SMS নিয়ম (Teletalk SMS Payment)
  </h3>
  <p style="text-align: justify;">
    অনলাইনে আবেদনপত্র পূরণ করলে Applicant's Copy-তে একটি <b>User ID</b> পাবেন। এই User ID ব্যবহার করে নিম্নোক্ত দুটি SMS পাঠিয়ে আবেদন ফি বাবদ <b>{info['fee_bn']}</b> পরিশোধ করতে পারবেন:
  </p>
  <p style="text-align: justify;">
    <b>প্রথম SMS:</b> <code>{short_code} &lt;স্পেস&gt; User ID</code> লিখে পাঠিয়ে দিন <b>16222</b> নম্বরে।<br/>
    উদাহরণ: <b>{short_code} BDEDUJOB</b>
  </p>
  <p style="text-align: justify;">
    <b>দ্বিতীয় SMS:</b> ফিরতি মেসেজে একটি PIN নম্বর পাবেন। এরপর <code>{short_code} &lt;স্পেস&gt; YES &lt;স্পেস&gt; PIN</code> লিখে পাঠিয়ে দিন <b>16222</b> নম্বরে।<br/>
    উদাহরণ: <b>{short_code} YES 12345678</b>
  </p>

  <!-- ৯. প্রবেশপত্র ডাউনলোড ও নিয়োগ পরীক্ষা -->
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    প্রবেশপত্র ডাউনলোড ও চাকরির পরীক্ষা (Admit Card &amp; Exam Info)
  </h2>
  <p style="text-align: justify;">
    পরীক্ষার তারিখ, কেন্দ্র এবং প্রবেশপত্র (Admit Card) ডাউনলোড সম্পর্কিত তথ্য প্রার্থীর মোবাইলে SMS-এর মাধ্যমে জানানো হবে। এছাড়াও <b>{org_bn}</b>-এর অফিসিয়াল ওয়েবসাইট ({official_site}) এবং আমাদের জব পোর্টাল <a href="{SITE_URL}">{SITE_DISPLAY}</a>-এ নিয়মিত আপডেট পাওয়া যাবে।
  </p>
  <p style="text-align: justify;">
    বাংলাদেশে সরকারি ও স্বায়ত্তশাসিত প্রতিষ্ঠানগুলোতে সাধারণত নিচের ৩টি ধাপে নিয়োগ পরীক্ষা অনুষ্ঠিত হয়ে থাকে:
  </p>
  <ul>
    <li>১. প্রিলিমিনারি বা বাছাই পরীক্ষা (MCQ Test)</li>
    <li>২. লিখিত ও ব্যবহারিক পরীক্ষা (Written &amp; Practical Exam - প্রযোজ্য ক্ষেত্রে)</li>
    <li>৩. মৌখিক পরীক্ষা (Viva Voce)</li>
  </ul>

  <!-- ১০. সচরাচর জিজ্ঞাসিত প্রশ্নোত্তর (SEO FAQ Section) -->
  <h2 style="text-align: center; color: #38761d; font-size: 21px; margin-top: 28px;">
    সচরাচর জিজ্ঞাসিত প্রশ্নোত্তর (FAQ)
  </h2>
  <p style="text-align: justify;">
    <b>প্রশ্ন ১: {org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬-এ মোট কতজন নিয়োগ দেওয়া হবে?</b><br/>
    উত্তর: এই বিজ্ঞপ্তির মাধ্যমে মোট {info['vacancy_bn']} জনবল নিয়োগ দেওয়া হবে।
  </p>
  <p style="text-align: justify;">
    <b>প্রশ্ন ২: আবেদনের শেষ তারিখ কবে?</b><br/>
    উত্তর: আগ্রহী প্রার্থীরা {info['deadline_bn']} পর্যন্ত অনলাইনে আবেদন করতে পারবেন।
  </p>
  <p style="text-align: justify;">
    <b>প্রশ্ন ৩: কীভাবে অনলাইনে আবেদন করব?</b><br/>
    উত্তর: প্রার্থীকে অফিশিয়াল ওয়েবসাইট বা টেলিটক পোর্টাল ({apply_url})-এ গিয়ে অনলাইনে ফরম পূরণ করতে হবে।
  </p>

  <!-- ১১. আপনার সাইটের সতর্কীকরণ বিজ্ঞপ্তি ও ট্যাগ -->
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
    <i>{org_bn} নিয়োগ বিজ্ঞপ্তি ২০২৬, {org_bn} নতুন চাকরি, {org_en} Job Circular 2026, {short_code} Job Circular 2026, {short_code} teletalk apply, govt job circular 2026, bd job circular 2026 today, সরকারি চাকরির খবর ২০২৬, নতুন নিয়োগ বিজ্ঞপ্তি ২০২৬, bdedujob.</i>
  </p>
  {schema_script}
</div>"""
    return html


# ==============================================================================
# ৭. Blogger API v3 এর মাধ্যমে অটোমেটিক পোস্ট পাবলিশ
# ==============================================================================
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


# ==============================================================================
# ৮. মেইন অটোমেশন রানার
# ==============================================================================
def main():
    posted_urls = load_posted_jobs()
    published_count = 0

    for source in JOB_SOURCES:
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
                html_post = build_bdedujob_post_html(info, banner_url, scraped["notice_images"])

                if BLOGGER_BLOG_ID and BLOGGER_REFRESH_TOKEN:
                    res = publish_to_blogger(
                        title=info["post_title"],
                        html_content=html_post,
                        labels=info.get("blogger_labels", ["All Jobs", source["default_label"]]),
                        is_draft=BLOGGER_IS_DRAFT,
                    )
                    print(f"[SUCCESS] Published to Blogger! Post URL: {res.get('url')}")
                    save_posted_job(link)
                    published_count += 1
                else:
                    # লোকাল প্রিভিউ মোড (ক্রেডেনশিয়াল সেট করার আগে টেস্ট করার জন্য)
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
