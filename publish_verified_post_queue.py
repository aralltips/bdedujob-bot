#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish curated Blogger + Facebook posts from the Google Drive / local queue.

Reads posts from DRIVE_QUEUE_URL (if configured) and local verified_post_queue.json,
validates HTML/labels/duplicates/deadlines, publishes with each item's exact
published_iso date (when provided), shares to Facebook Page, and updates
posted_jobs.json / verified_post_state.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import auto_job_blogger as bot

ROOT = Path(bot.BASE_DIR)
QUEUE_PATH = ROOT / "verified_post_queue.json"
STATE_PATH = ROOT / "verified_post_state.json"
STATE_TMP = ROOT / "verified_post_state.json.tmp"
BD_TZ = timezone(timedelta(hours=6))
MIN_POST_GAP = timedelta(minutes=30)

DEFAULT_DRIVE_QUEUE_URL = (
    "https://drive.google.com/uc?export=download&id=1DMGaDPWncdRpjH53SJGnEHkYCoEV376O"
)


def log(message: str) -> None:
    print(f"[VERIFIED QUEUE] {message}", flush=True)


def set_output(slot_consumed: bool, published: bool = False) -> None:
    """Expose workflow outputs so the crawler can be skipped after a queue attempt."""
    values = {
        "slot_consumed": "true" if slot_consumed else "false",
        "published": "true" if published else "false",
    }
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as f:
            for key, value in values.items():
                f.write(f"{key}={value}\n")
    for key, value in values.items():
        os.environ[f"VERIFIED_QUEUE_{key.upper()}"] = value


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def read_state() -> dict[str, Any]:
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_state(data: dict[str, Any]) -> None:
    STATE_TMP.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATE_TMP.replace(STATE_PATH)


def get_public_latest_post_time() -> tuple[datetime | None, set[str]]:
    """Public Blogger feed duplicate/cooldown check; no credentials are needed."""
    url = f"{bot.SITE_URL}/feeds/posts/default?alt=json&max-results=100"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BDEduJob-VerifiedQueue/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        entries = data.get("feed", {}).get("entry", []) or []
        titles: set[str] = set()
        latest: datetime | None = None
        for entry in entries:
            title = entry.get("title", {}).get("$t", "")
            if title:
                titles.add(normalize_title(title))
            published = entry.get("published", {}).get("$t", "")
            dt = parse_timestamp(published)
            if dt and (latest is None or dt > latest):
                latest = dt
        return latest, titles
    except Exception as exc:
        log(f"Public feed check unavailable: {exc}")
        return None, set()


def read_drive_queue(drive_url: str) -> list[dict[str, Any]]:
    if not drive_url:
        return []
    req = urllib.request.Request(
        drive_url,
        headers={
            "User-Agent": "Mozilla/5.0 BDEduJob-VerifiedQueue/2.0",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    items = data.get("items", []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        raise ValueError("Remote Drive queue: 'items' must be a list")
    return [item for item in items if isinstance(item, dict)]


def read_local_queue() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    items = data.get("items", []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        raise ValueError("verified_post_queue.json: 'items' must be a list")
    return [item for item in items if isinstance(item, dict)]


def read_all_queues(drive_url: str) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if drive_url:
        try:
            drive_items = read_drive_queue(drive_url)
            log(f"Loaded {len(drive_items)} item(s) from Google Drive queue.")
            for item in drive_items:
                item_id = str(item.get("id", "")).strip()
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    merged.append(item)
        except Exception as exc:
            log(f"Google Drive queue read warning: {exc}")

    try:
        local_items = read_local_queue()
        for item in local_items:
            item_id = str(item.get("id", "")).strip()
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                merged.append(item)
    except Exception as exc:
        log(f"Local queue read warning: {exc}")

    return merged


def resolve_html(item: dict[str, Any]) -> str:
    inline_html = item.get("html")
    if isinstance(inline_html, str) and inline_html.strip():
        return inline_html
    rel_path = str(item.get("html_file", "")).strip()
    if rel_path:
        html_path = ROOT / rel_path
        if html_path.is_file():
            return html_path.read_text(encoding="utf-8")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate and show pending items; do not publish")
    args = parser.parse_args()

    drive_url = os.getenv("DRIVE_QUEUE_URL", DEFAULT_DRIVE_QUEUE_URL).strip()
    max_posts = max(1, int(os.getenv("MAX_QUEUE_POSTS_PER_RUN", "1") or "1"))
    ignore_cooldown = os.getenv("IGNORE_COOLDOWN", "false").lower() == "true"

    items = read_all_queues(drive_url)
    if not items:
        log("No queued items found.")
        set_output(False, False)
        return 0

    if bot.BLOGGER_IS_DRAFT and not args.dry_run:
        log("BLOGGER_IS_DRAFT=true; refusing to process the live queue.")
        set_output(False, False)
        return 0

    now = datetime.now(timezone.utc)
    latest_public, public_titles = get_public_latest_post_time()
    state = read_state()
    last_attempt = parse_timestamp(str(state.get("last_attempt_utc", "")))
    cooldown_base = max([dt for dt in (latest_public, last_attempt) if dt is not None], default=None)
    if not args.dry_run and not ignore_cooldown and cooldown_base and now - cooldown_base < MIN_POST_GAP:
        log("A Blogger post was published/attempted within the last 30 minutes; skipping scheduled slot.")
        set_output(True, False)
        return 0

    try:
        already_posted = set(bot.load_posted_jobs())
    except Exception:
        already_posted = set()

    if not args.dry_run:
        try:
            for title in bot.get_live_blogger_titles(100):
                if title:
                    public_titles.add(normalize_title(title))
        except Exception:
            pass

    today_bd = datetime.now(BD_TZ).date()
    candidates: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not item_id or not title:
            log("Skipping malformed queue record without id/title.")
            continue
        marker = f"verified-queue:{item_id}"
        if marker in already_posted:
            continue

        expires_on = str(item.get("expires_on", "")).strip()
        if expires_on:
            try:
                if today_bd > date.fromisoformat(expires_on):
                    log(f"Expired; not publishing: {title} (active through {expires_on}, Dhaka date {today_bd}).")
                    continue
            except ValueError:
                log(f"Invalid expires_on for {item_id}; skipping for safety.")
                continue

        if normalize_title(title) in public_titles:
            log(f"Title is already live; recording idempotency marker: {title}")
            if not args.dry_run:
                bot.save_posted_job(marker)
            already_posted.add(marker)
            continue

        html = resolve_html(item)
        if not html.strip():
            log(f"HTML missing/empty; skipping {item_id}.")
            continue
        if "<!--more-->" not in html:
            html = html.replace("</p>", "</p>\n<!--more-->", 1) if "</p>" in html else (html + "\n<!--more-->")

        raw_labels = item.get("labels", [])
        if not isinstance(raw_labels, list):
            raw_labels = []
        labels = [lbl for lbl in raw_labels if lbl in bot.ALLOWED_BLOGGER_LABELS]
        if not labels:
            labels = ["All Jobs", "Govt Jobs", "job", "all"]

        pub_iso = str(item.get("published_iso", "")).strip()
        if pub_iso and parse_timestamp(pub_iso) is None:
            log(f"Invalid published_iso '{pub_iso}' on {item_id}; clearing to current time.")
            pub_iso = ""

        candidates.append({
            "item_id": item_id,
            "marker": marker,
            "title": title,
            "html": html,
            "labels": labels,
            "published_iso": pub_iso,
            "banner_url": str(item.get("banner_url", "")).strip(),
            "facebook_summary": str(item.get("facebook_summary", "")).strip(),
            "expires_on": expires_on or "none",
        })

    if not candidates:
        log("No unposted, non-expired, valid queue items remain.")
        set_output(False, False)
        return 0

    if args.dry_run:
        for idx, c in enumerate(candidates[:max_posts], start=1):
            log(
                f"DRY RUN #{idx}: {c['title']} | published_iso={c['published_iso'] or 'now'} "
                f"| labels={c['labels']} | expires_on={c['expires_on']}"
            )
        set_output(False, False)
        return 0

    published_any = False
    for idx, c in enumerate(candidates[:max_posts]):
        if idx > 0:
            time.sleep(2)
        state.update({"last_attempt_utc": datetime.now(timezone.utc).isoformat(), "last_attempt_id": c["item_id"]})
        write_state(state)
        log(f"Publishing ({idx + 1}/{min(len(candidates), max_posts)}): {c['title']} [date={c['published_iso'] or 'now'}]")

        try:
            result = bot.publish_to_blogger(
                title=c["title"],
                html_content=c["html"],
                labels=c["labels"],
                is_draft=False,
                published_iso=c["published_iso"],
            )
        except Exception as exc:
            log(f"Blogger publish failed; marking run failed: {exc}")
            set_output(True, published_any)
            return 1

        post_url = str(result.get("url", ""))
        state.update({
            "last_attempt_utc": datetime.now(timezone.utc).isoformat(),
            "last_posted_id": c["item_id"],
            "last_post_url": post_url,
        })
        write_state(state)
        bot.save_posted_job(c["marker"])
        published_any = True
        log(f"Blogger post created. URL: {post_url or '(API response did not include URL)'}")

        if post_url:
            try:
                bot.share_to_facebook_page(
                    title=c["title"],
                    post_url=post_url,
                    banner_url=c["banner_url"],
                    summary_text=c["facebook_summary"],
                )
            except Exception as exc:
                log(f"Facebook share helper raised an error; Blogger post remains live: {exc}")

        try:
            bot.ping_google_websub_hub()
        except Exception:
            pass

    set_output(True, published_any)
    return 0


if __name__ == "__main__":
    sys.exit(main())
