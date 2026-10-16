#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Thumbnail / Banner Generator for bdedujob.blogspot.com
Automatically designs a 1200x630 SEO & Social-Share friendly job circular banner
in Bangla & English using Pillow (with HarfBuzz/Raqm complex script support).
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(BASE_DIR, "fonts", "HindSiliguri-Bold.ttf")
FONT_SEMIBOLD = os.path.join(BASE_DIR, "fonts", "HindSiliguri-SemiBold.ttf")
FONT_REGULAR = os.path.join(BASE_DIR, "fonts", "HindSiliguri-Regular.ttf")


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if os.path.exists(path):
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int):
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines[:2]


def _fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: str, start_size: int, min_size: int, max_width: int):
    for size in range(start_size, min_size - 1, -2):
        f = _load_font(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=f)
        if (bbox[2] - bbox[0]) <= max_width:
            return f, text
    f = _load_font(font_path, min_size)
    return f, text[:22] + "..."


def generate_job_banner(
    org_name_bn: str,
    org_short_en: str,
    vacancy_bn: str,
    qualification_bn: str,
    deadline_bn: str,
    job_type_bn: str = "সরকারি চাকরি",
    output_path: str = "job_banner.png",
) -> str:
    """
    Creates a 1200x630 modern, high-CTR job circular thumbnail banner for bdedujob.blogspot.com.
    """
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), "#0b2e1f")
    draw = ImageDraw.Draw(img)

    # Smooth dark-emerald to teal gradient background
    for y in range(height):
        r = int(10 + (y / height) * 12)
        g = int(48 + (y / height) * 35)
        b = int(32 + (y / height) * 28)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Decorative geometric accent shapes
    draw.ellipse([920, -120, 1340, 300], fill="#145337", outline="#1e704c", width=3)
    draw.ellipse([-140, 380, 260, 780], fill="#11422c", outline="#1c6443", width=3)

    # Outer border frame
    draw.rounded_rectangle(
        [28, 28, width - 28, height - 28],
        radius=24,
        outline="#34d399",
        width=3,
    )

    # Top header badge (Job Type + Year) with drawn indicator circle
    draw.rounded_rectangle([64, 58, 390, 118], radius=30, fill="#f59e0b")
    draw.ellipse([86, 78, 106, 98], fill="#0b2e1f")
    font_badge = _load_font(FONT_BOLD, 30)
    draw.text((246, 88), f"{job_type_bn} ২০২৬", font=font_badge, fill="#0b2e1f", anchor="mm")

    # Right top short code pill
    if org_short_en:
        draw.rounded_rectangle([860, 58, 1136, 118], radius=16, fill="#145337", outline="#34d399", width=2)
        font_code = _load_font(FONT_BOLD, 28)
        draw.text((998, 88), org_short_en.upper()[:18], font=font_code, fill="#ecfdf5", anchor="mm")

    # Main Title: Organization Name in Bangla (1-2 lines)
    font_org = _load_font(FONT_BOLD, 54)
    org_lines = _wrap_text(draw, org_name_bn, font_org, max_width=1060)
    y_cursor = 150
    for line in org_lines:
        draw.text((64, y_cursor), line, font=font_org, fill="#ffffff")
        y_cursor += 68

    # Subtitle highlight bar: "নিয়োগ বিজ্ঞপ্তি ২০২৬ প্রকাশিত"
    y_cursor += 12
    draw.rounded_rectangle([64, y_cursor, 660, y_cursor + 68], radius=14, fill="#10b981")
    font_sub = _load_font(FONT_BOLD, 38)
    draw.text((362, y_cursor + 34), "নিয়োগ বিজ্ঞপ্তি ২০২৬ প্রকাশিত", font=font_sub, fill="#06281b", anchor="mm")

    # Info cards row (Vacancy | Qualification | Deadline)
    card_y = 400
    card_h = 118
    cards = [
        ("শূন্যপদ সংখ্যা", vacancy_bn, "#d97706"),
        ("শিক্ষাগত যোগ্যতা", qualification_bn, "#0284c7"),
        ("আবেদনের শেষ তারিখ", deadline_bn, "#db2777"),
    ]
    card_w = 340
    gap = 26
    start_x = 64

    font_card_label = _load_font(FONT_SEMIBOLD, 23)

    for idx, (label, val, accent_col) in enumerate(cards):
        cx = start_x + idx * (card_w + gap)
        draw.rounded_rectangle(
            [cx, card_y, cx + card_w, card_y + card_h],
            radius=16,
            fill="#0f3d29",
            outline="#34d399",
            width=2,
        )
        draw.rounded_rectangle([cx, card_y, cx + 12, card_y + card_h], radius=5, fill=accent_col)
        draw.text((cx + 28, card_y + 18), label, font=font_card_label, fill="#a7f3d0")
        fitted_font, val_display = _fit_font(draw, val, FONT_BOLD, start_size=30, min_size=21, max_width=card_w - 44)
        draw.text((cx + 28, card_y + 60), val_display, font=fitted_font, fill="#ffffff")

    # Bottom footer bar with website & app branding
    draw.rounded_rectangle([32, 542, width - 32, height - 32], radius=18, fill="#062015")
    draw.ellipse([58, 563, 74, 579], fill="#34d399")
    font_footer = _load_font(FONT_SEMIBOLD, 24)
    draw.text(
        (88, 554),
        "বিস্তারিত ও অনলাইন আবেদন: www.bdedujob.blogspot.com",
        font=font_footer,
        fill="#6ee7b7",
    )
    draw.text(
        (1136, 571),
        "BD Education & Job Info",
        font=font_footer,
        fill="#fbbf24",
        anchor="rm",
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)
    return output_path


if __name__ == "__main__":
    out = generate_job_banner(
        org_name_bn="বাংলাদেশ লোক-প্রশাসন প্রশিক্ষণ কেন্দ্র (BPATC)",
        org_short_en="BPATC JOB 2026",
        vacancy_bn="৩৯ টি পদ (স্থায়ী)",
        qualification_bn="৮ম / এসএসসি / এইচএসসি / স্নাতক",
        deadline_bn="১৫ নভেম্বর ২০২৬",
        job_type_bn="সরকারি চাকরি",
        output_path=os.path.join(BASE_DIR, "sample_banner.png"),
    )
    print("Generated sample banner:", out)
