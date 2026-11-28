#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch the 13 already-published Private Job posts on Blogger to replace the
Govt-emblem banner with each company's real-logo banner.

Pure Python stdlib (no extra pip packages needed). Run via GitHub Actions
(.github/workflows/patch_private_banners.yml) or locally with BLOGGER_* env vars.
"""

import json
import os
import re
import urllib.parse
import urllib.request

BLOGGER_BLOG_ID = os.getenv("BLOGGER_BLOG_ID", "3244474783562745180")
BLOGGER_CLIENT_ID = os.getenv("BLOGGER_CLIENT_ID", "")
BLOGGER_CLIENT_SECRET = os.getenv("BLOGGER_CLIENT_SECRET", "")
BLOGGER_REFRESH_TOKEN = os.getenv("BLOGGER_REFRESH_TOKEN", "")

PATCH_MAP = {
    "5558854127715252410": "https://img3.pixhost.to/images/7524/817031754_01_brb_cable.png",
    "8850045563224715899": "https://img3.pixhost.to/images/7524/817031779_02_dbl_pharma.png",
    "6858767015971493286": "https://img3.pixhost.to/images/7524/817031810_03_healthcare_pharma.png",
    "5283988910751794594": "https://img3.pixhost.to/images/7524/817031837_04_popular_pharma.png",
    "2804155245917275788": "https://img3.pixhost.to/images/7524/817031861_05_renata_plc.png",
    "2947920232927892419": "https://img3.pixhost.to/images/7524/817031890_06_meghna_group.png",
    "1244866971110565919": "https://img3.pixhost.to/images/7524/817031928_07_bashundhara_group.png",
    "1263785872732715105": "https://img3.pixhost.to/images/7524/817031955_08_rfl_group.png",
    "4067981161441726133": "https://img3.pixhost.to/images/7524/817031967_09_walton_group.png",
    "6673021840828532121": "https://img3.pixhost.to/images/7524/817031984_10_synovia_pharma.png",
    "1209310785347206301": "https://img3.pixhost.to/images/7524/817032009_11_plan_international.png",
    "1514020824270443382": "https://img3.pixhost.to/images/7524/817032024_12_beximco_pharma.png",
    "7514893091674927282": "https://img3.pixhost.to/images/7524/817032040_13_rupayan_group.png",
}


def get_access_token() -> str:
    rt = BLOGGER_REFRESH_TOKEN.strip()
    if not rt:
        raise RuntimeError("BLOGGER_REFRESH_TOKEN is missing")

    if BLOGGER_CLIENT_ID and BLOGGER_CLIENT_SECRET:
        try:
            payload = urllib.parse.urlencode({
                "client_id": BLOGGER_CLIENT_ID,
                "client_secret": BLOGGER_CLIENT_SECRET,
                "refresh_token": rt,
                "grant_type": "refresh_token",
            }).encode("utf-8")
            req = urllib.request.Request("https://oauth2.googleapis.com/token", data=payload)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("access_token"):
                return data["access_token"]
        except Exception:
            pass

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
        return pg_data["access_token"]
    raise RuntimeError("Could not obtain Blogger access token")


def main():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for post_id, new_banner in PATCH_MAP.items():
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}/posts/{post_id}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        post = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
        content = post.get("content", "")
        new_content, count = re.subn(
            r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'])',
            rf"\g<1>{new_banner}\g<3>",
            content,
            count=1,
            flags=re.IGNORECASE,
        )
        if not count:
            print(f"SKIP {post_id}: no <img> found")
            continue
        payload = json.dumps({"content": new_content}).encode("utf-8")
        preq = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(preq, timeout=20) as resp:
            print(f"PATCHED {post_id} ({resp.status}) -> {new_banner}")


if __name__ == "__main__":
    main()
