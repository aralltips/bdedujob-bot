#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Thumbnail / Banner Generator for bdedujob.blogspot.com
Uses the exact official template style requested by the user:
- Saptahik Chakrir Khobor template (templates/saptahik_template_base.jpg)
- Govt/Private/Bank/Result/Routine template with BD Govt Emblem (templates/job_template_base.jpg)
"""

import os
import re
import urllib.request
from PIL import Image, ImageDraw, ImageFont

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

    # Dynamic font sizing for top green arc (max width 520px so it stays well inside the curve)
    f_top = _load_font(FONT_BOLD, 48)
    for sz in range(50, 24, -2):
        cand = _load_font(FONT_BOLD, sz)
        bbox = draw.textbbox((0, 0), clean_org, font=cand)
        if (bbox[2] - bbox[0]) <= 520:
            f_top = cand
            break

    # Dynamic font sizing for middle line 1 (max width 720px)
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
    Generates an exact 640x365 BCS Preliminary Question Solution banner
    identical to the user's existing 10th-23rd BCS banners.
    Example bcs_title_line1: '২৪ তম বিসিএস'
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
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _clean_org_name_bn(name: str) -> str:
    """Removes English brackets or redundant words so the Bangla title looks clean like the reference."""
    cleaned = re.sub(r"\([A-Za-z0-9\s\-_,\.]+\)", "", name)
    cleaned = re.sub(
        r"নিয়োগ বিজ্ঞপ্তি.*|নিয়োগ বিজ্ঞপ্তি.*|লিখিত পরীক্ষার ফলাফল.*|পরীক্ষার ফলাফল.*|পরীক্ষার সময়সূচি.*|ভর্তি বিজ্ঞপ্তি.*",
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
) -> str:
    """
    Generates a 2048x1152 banner matching the exact reference design.
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

    # Determine if red subtitle should change for Exam Result / Exam Routine / Admission
    custom_red_subtitle = None
    if any(k in combined_check for k in ["ফলাফল", "রেজাল্ট", "result"]):
        custom_red_subtitle = "পরীক্ষার ফলাফল"
    elif any(k in combined_check for k in ["সময়সূচি", "সময়সূচি", "রুটিন", "routine", "প্রবেশপত্র", "admit card"]):
        custom_red_subtitle = "পরীক্ষার সময়সূচি"
    elif any(k in combined_check for k in ["ভর্তি বিজ্ঞপ্তি", "admission"]):
        custom_red_subtitle = "ভর্তি বিজ্ঞপ্তি"

    if custom_red_subtitle:
        draw.rectangle([240, 598, 1130, 725], fill=(255, 255, 255))
        font_red = _load_font(FONT_BOLD, 108)
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
