#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Thumbnail / Banner Generator for bdedujob.blogspot.com
Uses the exact official template style requested by the user:
- Saptahik Chakrir Khobor template (templates/saptahik_template_base.jpg)
- Govt job template with BD Govt Emblem (templates/job_template_base.jpg)
- Private/NGO/Corporate job mode: removes BD Govt Emblem and places the
  actual company/NGO logo (or a clean corporate badge fallback).
"""

import io
import os
import re
import ssl
import urllib.request
from PIL import Image, ImageChops, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(BASE_DIR, "fonts", "HindSiliguri-Bold.ttf")
TEMPLATE_JOB = os.path.join(BASE_DIR, "templates", "job_template_base.jpg")
TEMPLATE_SAPTAHIK = os.path.join(BASE_DIR, "templates", "saptahik_template_base.jpg")
TEMPLATE_BCS = os.path.join(BASE_DIR, "templates", "bcs_template_base.jpg")
TEMPLATE_JOB_SOLUTION = os.path.join(BASE_DIR, "templates", "job_solution_template_base.jpg")

JOB_TEMPLATE_URL = "https://iili.io/njCwnWX.jpg"
SAPTAHIK_TEMPLATE_URL = "https://iili.io/njCwcX9.jpg"
BCS_TEMPLATE_URL = "https://img3.pixhost.to/images/6492/786119047_bcs_template_base.jpg"
JOB_SOLUTION_TEMPLATE_URL = "https://iili.io/njOqcgV.jpg"

DARK_GREEN = (8, 81, 51)  # Exact RGB from reference banner (#085133)
BRIGHT_RED = (237, 28, 36)  # Exact RGB of red subtitle (#ED1C24)

PRIVATE_KEYWORDS = (
    "বেসরকারি",
    "private",
    "privet",
    "ngo",
    "এনজিও",
    "corporate",
    "গ্রুপ",
    "group",
    "ফার্মাসিউটিক্যাল",
    "ফার্মা",
    "pharma",
    "ইন্ডাস্ট্রিজ",
    "industries",
    "কেমিক্যাল",
    "লিমিটেড",
    "পিএলসি",
    "plc",
    "ltd",
    "প্ল্যান ইন্টারন্যাশনাল",
    "ব্র্যাক",
    "brac",
    "walton",
    "ওয়ালটন",
    "rfl",
    "আরএফএল",
    "বসুন্ধরা",
    "মেঘনা",
    "রূপায়ণ",
    "যমুনা",
    "আবুল খায়ের",
    "স্কয়ার",
    "বেক্সিমকো",
    "রেনাটা",
    "পপুলার",
    "হেলথকেয়ার",
    "ডিবিএল",
    "সিনোভিয়া",
    "বিআরবি",
    "ইবনে সিনা",
)

GOVT_OVERRIDES = (
    "সরকারি",
    "govt",
    "মন্ত্রণালয়",
    "অধিদপ্তর",
    "পরিদপ্তর",
    "দপ্তর",
    "কমিশন",
    "বিশ্ববিদ্যালয়",
    "সিটি কর্পোরেশন",
    "জেলা পরিষদ",
    "জেলা প্রশাসক",
    "ক্যান্টনমেন্ট",
    "সেনাবাহিনী",
    "নৌবাহিনী",
    "বিমান বাহিনী",
    "পুলিশ",
    "বিসিএস",
    "বিপিএসসি",
    "বাংলাদেশ ব্যাংক",
    "কর্পোরেশন",
    "কর্তৃপক্ষ",
    "বোর্ড",
    "ইনস্টিটিউট",
)


def _ensure_templates():
    os.makedirs(os.path.join(BASE_DIR, "templates"), exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    if not os.path.exists(TEMPLATE_JOB):
        req = urllib.request.Request(JOB_TEMPLATE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r, open(TEMPLATE_JOB, "wb") as f:
            f.write(r.read())
    if not os.path.exists(TEMPLATE_SAPTAHIK):
        req = urllib.request.Request(SAPTAHIK_TEMPLATE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r, open(TEMPLATE_SAPTAHIK, "wb") as f:
            f.write(r.read())
    if not os.path.exists(TEMPLATE_BCS):
        req = urllib.request.Request(BCS_TEMPLATE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r, open(TEMPLATE_BCS, "wb") as f:
            f.write(r.read())
    if not os.path.exists(TEMPLATE_JOB_SOLUTION):
        req = urllib.request.Request(JOB_SOLUTION_TEMPLATE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r, open(TEMPLATE_JOB_SOLUTION, "wb") as f:
            f.write(r.read())


def _is_private_job(org_name_bn: str, org_short_en: str, job_type_bn: str) -> bool:
    jt = (job_type_bn or "").lower()
    if any(k in jt for k in ("বেসরকারি", "private", "privet", "ngo", "এনজিও", "corporate")):
        return True
    if "সরকারি" in jt or "govt" in jt:
        return False
    combined = f"{org_name_bn} {org_short_en} {job_type_bn}".lower()
    if any(k in combined for k in GOVT_OVERRIDES):
        return False
    return any(k in combined for k in PRIVATE_KEYWORDS)


def _trim_logo_on_white(logo_img: Image.Image) -> Image.Image:
    """Composite transparent logo over pure white and crop outer white margins."""
    rgba = logo_img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(bg, rgba).convert("RGB")
    diff = ImageChops.difference(flat, Image.new("RGB", flat.size, (255, 255, 255)))
    diff = diff.point(lambda p: 255 if p > 18 else 0)
    bbox = diff.getbbox()
    if bbox:
        pad = 6
        x1 = max(0, bbox[0] - pad)
        y1 = max(0, bbox[1] - pad)
        x2 = min(flat.width, bbox[2] + pad)
        y2 = min(flat.height, bbox[3] + pad)
        return flat.crop((x1, y1, x2, y2))
    return flat


def _load_company_logo(company_logo_path: str = "", company_logo_url: str = "") -> Image.Image | None:
    if company_logo_path and os.path.exists(company_logo_path):
        try:
            return Image.open(company_logo_path)
        except Exception:
            pass
    if company_logo_url:
        try:
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(company_logo_url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=15, context=ctx).read()
            return Image.open(io.BytesIO(raw))
        except Exception:
            pass
    return None


def _draw_private_corporate_badge(img: Image.Image, org_name_bn: str, org_short_en: str) -> None:
    """Fallback clean corporate monogram badge (never uses BD Govt emblem)."""
    draw = ImageDraw.Draw(img)
    cx, cy = 684, 248
    r = 76
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(236, 250, 241), outline=DARK_GREEN, width=5)
    initials = re.sub(r"[^A-Za-z]", "", org_short_en or "").upper()[:4]
    if not initials:
        words = [w for w in re.split(r"\s+", org_name_bn.strip()) if w]
        initials = "".join(w[0] for w in words[:2]) or "JOB"
    f_size = 46 if len(initials) <= 3 else 36
    f = _load_font(FONT_BOLD, f_size)
    draw.text((cx, cy), initials, font=f, fill=DARK_GREEN, anchor="mm")


def _apply_private_company_logo(
    img: Image.Image,
    org_name_bn: str,
    org_short_en: str,
    company_logo_path: str = "",
    company_logo_url: str = "",
) -> None:
    draw = ImageDraw.Draw(img)
    # Completely erase BD Govt emblem from the base template
    draw.rectangle((535, 130, 835, 372), fill=(255, 255, 255))

    logo = _load_company_logo(company_logo_path=company_logo_path, company_logo_url=company_logo_url)
    if logo is None:
        _draw_private_corporate_badge(img, org_name_bn, org_short_en)
        return

    trimmed = _trim_logo_on_white(logo)
    max_w, max_h = 440, 178
    scale = min(max_w / max(1, trimmed.width), max_h / max(1, trimmed.height))
    new_w = max(1, round(trimmed.width * scale))
    new_h = max(1, round(trimmed.height * scale))
    resized = trimmed.resize((new_w, new_h), Image.Resampling.LANCZOS)

    cx, cy = 684, 252
    px = cx - new_w // 2
    py = cy - new_h // 2
    img.paste(resized, (px, py))


def generate_job_solution_banner(
    org_name_bn: str,
    exam_line_bn: str = "নিয়োগ MCQ পরীক্ষার",
    output_path: str = "job_solution_banner.jpg",
) -> str:
    """
    Generates an exact 800x445 Job Exam Question Solution banner
    identical to the user's existing Job Solution banner in Soluson.html.
    """
    _ensure_templates()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img = Image.open(TEMPLATE_JOB_SOLUTION).convert("RGB")
    draw = ImageDraw.Draw(img)

    clean_org = re.sub(r"\([A-Za-z0-9\s\-_,\.]+\)", "", org_name_bn)
    clean_org = re.sub(
        r"পরীক্ষার প্রশ্ন সমাধান.*|প্রশ্ন সমাধান.*|নিয়োগ পরীক্ষা.*|নিয়োগ পরীক্ষা.*|Question Solution.*",
        "",
        clean_org,
        flags=re.IGNORECASE,
    ).strip(" -–|—") or org_name_bn.strip()

    f_top = _load_font(FONT_BOLD, 48)
    for sz in range(50, 24, -2):
        cand = _load_font(FONT_BOLD, sz)
        bbox = draw.textbbox((0, 0), clean_org, font=cand)
        if (bbox[2] - bbox[0]) <= 520:
            f_top = cand
            break

    t_m1 = (exam_line_bn or "নিয়োগ MCQ পরীক্ষার").strip()
    f_m1 = _load_font(FONT_BOLD, 48)
    for sz in range(50, 28, -2):
        cand = _load_font(FONT_BOLD, sz)
        bbox = draw.textbbox((0, 0), t_m1, font=cand)
        if (bbox[2] - bbox[0]) <= 720:
            f_m1 = cand
            break

    t_m2 = "প্রশ্নের সম্পূর্ণ সমাধান"
    f_m2 = _load_font(FONT_BOLD, 52)

    b_top = draw.textbbox((0, 0), clean_org, font=f_top)
    b_m1 = draw.textbbox((0, 0), t_m1, font=f_m1)
    b_m2 = draw.textbbox((0, 0), t_m2, font=f_m2)

    y_top = max(18, 60 - (b_top[3] - b_top[1]) // 2)
    draw.text((400 - (b_top[2] - b_top[0]) // 2, y_top), clean_org, font=f_top, fill=(255, 255, 255))
    draw.text((400 - (b_m1[2] - b_m1[0]) // 2, 175), t_m1, font=f_m1, fill=(13, 107, 136))
    draw.text((400 - (b_m2[2] - b_m2[0]) // 2, 248), t_m2, font=f_m2, fill=(22, 160, 93))

    fmt = "JPEG" if output_path.lower().endswith((".jpg", ".jpeg")) else "PNG"
    if fmt == "JPEG":
        img.save(output_path, format="JPEG", quality=95, optimize=True)
    else:
        img.save(output_path, format="PNG", optimize=True)
    return output_path


def generate_bcs_banner(bcs_title_line1: str, output_path: str = "bcs_banner.jpg") -> str:
    """
    Generates an exact 640x365 BCS Preliminary Question Solution banner.
    """
    _ensure_templates()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img = Image.open(TEMPLATE_BCS).convert("RGB")
    draw = ImageDraw.Draw(img)

    font1 = _load_font(FONT_BOLD, 52 if len(bcs_title_line1) <= 14 else 42)
    font2 = _load_font(FONT_BOLD, 44)

    t1 = bcs_title_line1.strip()
    t2 = "পরীক্ষার প্রশ্ন সমাধান"
    b1 = draw.textbbox((0, 0), t1, font=font1)
    b2 = draw.textbbox((0, 0), t2, font=font2)
    cx = 435
    draw.text((cx - (b1[2] - b1[0]) // 2, 78), t1, font=font1, fill=(10, 10, 10))
    draw.text((cx - (b2[2] - b2[0]) // 2, 148), t2, font=font2, fill=(10, 10, 10))
    img.save(output_path, format="JPEG", quality=95, optimize=True)
    return output_path


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size=size, layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _clean_org_name_bn(name: str) -> str:
    """Removes English brackets or redundant words so the Bangla title looks clean like the reference."""
    cleaned = re.sub(r"\([A-Za-z0-9\s\-_,\.]+\)", "", name)
    cleaned = re.sub(
        r"নিয়োগ বিজ্ঞপ্তি.*|নিয়োগ বিজ্ঞপ্তি.*|লিখিত পরীক্ষার ফলাফল.*|পরীক্ষার ফলাফল.*|পরীক্ষার সময়সূচি.*|ভর্তি বিজ্ঞপ্তি.*|শিক্ষাবৃত্তি বিজ্ঞপ্তি.*|শিক্ষাবৃত্তি.*",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–|")
    return cleaned or name


def _split_balanced_two_lines(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int):
    """Splits Bangla organization name into 1 or 2 visually balanced lines."""
    words = text.split()
    if not words:
        return [text]

    full_bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    full_w = full_bbox[2] - full_bbox[0]
    if full_w <= max_width and len(words) <= 2:
        return [text]

    best_split = None
    best_diff = 10**9
    for i in range(1, len(words)):
        line1 = " ".join(words[:i])
        line2 = " ".join(words[i:])
        w1 = draw.textbbox((0, 0), line1, font=font, stroke_width=2)[2]
        w2 = draw.textbbox((0, 0), line2, font=font, stroke_width=2)[2]
        if w1 <= max_width and w2 <= max_width:
            penalty = abs(w1 - w2 * 1.35)
            if penalty < best_diff:
                best_diff = penalty
                best_split = [line1, line2]

    if best_split:
        return best_split

    lines = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        tw = draw.textbbox((0, 0), test, font=font, stroke_width=2)[2]
        if tw <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:2]


def generate_job_banner(
    org_name_bn: str,
    org_short_en: str = "",
    vacancy_bn: str = "",
    qualification_bn: str = "",
    deadline_bn: str = "",
    job_type_bn: str = "সরকারি চাকরি",
    output_path: str = "job_banner.png",
    company_logo_path: str = "",
    company_logo_url: str = "",
    is_private: bool | None = None,
) -> str:
    """
    Generates a 2048x1152 banner matching the exact reference design.
    For Private/NGO/Corporate jobs, strips the BD Govt emblem and places
    the company's own logo (or corporate monogram badge fallback).
    """
    _ensure_templates()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    combined_check = f"{org_name_bn} {org_short_en} {job_type_bn}".lower()
    if "সাপ্তাহিক" in combined_check or "saptahik" in combined_check or "পত্রিকা" in combined_check:
        img = Image.open(TEMPLATE_SAPTAHIK).convert("RGB")
        img.save(output_path, format="PNG", optimize=True)
        return output_path

    if any(k in combined_check for k in ["প্রশ্ন সমাধান", "প্রশ্ন উত্তর", "question solution", "question answer", "exam solution"]):
        return generate_job_solution_banner(org_name_bn=org_name_bn, exam_line_bn="নিয়োগ MCQ পরীক্ষার", output_path=output_path)

    img = Image.open(TEMPLATE_JOB).convert("RGB")
    draw = ImageDraw.Draw(img)

    private_mode = is_private if is_private is not None else _is_private_job(org_name_bn, org_short_en, job_type_bn)
    if private_mode or company_logo_path or company_logo_url:
        _apply_private_company_logo(
            img,
            org_name_bn=org_name_bn,
            org_short_en=org_short_en,
            company_logo_path=company_logo_path,
            company_logo_url=company_logo_url,
        )
        draw = ImageDraw.Draw(img)

    # Determine if red subtitle should change for Exam Result / Exam Routine / Admission / Scholarship
    custom_red_subtitle = None
    if any(k in combined_check for k in ["ফলাফল", "রেজাল্ট", "result"]):
        custom_red_subtitle = "পরীক্ষার ফলাফল"
    elif any(k in combined_check for k in ["সময়সূচি", "সময়সূচি", "রুটিন", "routine", "প্রবেশপত্র", "admit card"]):
        custom_red_subtitle = "পরীক্ষার সময়সূচি"
    elif any(k in combined_check for k in ["ভর্তি বিজ্ঞপ্তি", "ভর্তি", "admission"]):
        custom_red_subtitle = "ভর্তি বিজ্ঞপ্তি"
    elif any(k in combined_check for k in ["শিক্ষাবৃত্তি", "উপবৃত্তি", "বৃত্তি", "scholarship"]):
        custom_red_subtitle = "শিক্ষাবৃত্তি বিজ্ঞপ্তি"
    elif any(k in combined_check for k in ["সমাবর্তন", "ফরম পূরণ", "রেজিস্ট্রেশন", "convocation", "form fill"]):
        custom_red_subtitle = "জরুরি শিক্ষা বিজ্ঞপ্তি"

    if custom_red_subtitle:
        draw.rectangle([200, 598, 1170, 725], fill=(255, 255, 255))
        font_red = _load_font(FONT_BOLD, 102 if len(custom_red_subtitle) > 16 else 108)
        draw.text(
            (684, 662),
            custom_red_subtitle,
            font=font_red,
            fill=BRIGHT_RED,
            anchor="mm",
            stroke_width=1,
            stroke_fill=BRIGHT_RED,
        )

    clean_name = _clean_org_name_bn(org_name_bn)

    center_x = 684
    max_width = 1080

    chosen_font = _load_font(FONT_BOLD, 92)
    chosen_lines = [clean_name]

    for fsize in range(100, 56, -4):
        font = _load_font(FONT_BOLD, fsize)
        lines = _split_balanced_two_lines(clean_name, draw, font, max_width=max_width)
        widths = [draw.textbbox((0, 0), ln, font=font, stroke_width=2)[2] for ln in lines]
        line_step = int(fsize * 1.12)
        total_h = line_step * len(lines)
        if max(widths) <= max_width and total_h <= 235:
            chosen_font = font
            chosen_lines = lines
            break

    fsize = chosen_font.size
    line_step = int(fsize * 1.10)

    if len(chosen_lines) == 1:
        draw.text(
            (center_x, 495),
            chosen_lines[0],
            font=chosen_font,
            fill=DARK_GREEN,
            anchor="mm",
            stroke_width=2,
            stroke_fill=DARK_GREEN,
        )
    else:
        y1 = 482 - (line_step // 2)
        y2 = 482 + (line_step // 2)
        draw.text(
            (center_x, y1),
            chosen_lines[0],
            font=chosen_font,
            fill=DARK_GREEN,
            anchor="mm",
            stroke_width=2,
            stroke_fill=DARK_GREEN,
        )
        draw.text(
            (center_x, y2),
            chosen_lines[1],
            font=chosen_font,
            fill=DARK_GREEN,
            anchor="mm",
            stroke_width=2,
            stroke_fill=DARK_GREEN,
        )

    img.save(output_path, format="PNG", optimize=True)
    return output_path


if __name__ == "__main__":
    out1 = generate_job_banner(
        org_name_bn="বাংলাদেশ লোক-প্রশাসন প্রশিক্ষণ কেন্দ্র (BPATC)",
        output_path=os.path.join(BASE_DIR, "sample_banner.png"),
    )
    print("Generated job banner:", out1)
