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

JOB_TEMPLATE_URL = "https://iili.io/njCwnWX.jpg"
SAPTAHIK_TEMPLATE_URL = "https://iili.io/njCwcX9.jpg"

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
