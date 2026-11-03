#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish one verified, time-sensitive Blogger post per scheduled workflow run.

The existing GitHub Actions runner provides Blogger/Facebook secrets. This script
reuses the project's Blogger and Facebook helpers, publishes at most one queued
post, stores an idempotency marker, and skips any item whose active window ended.
Run with --dry-run to validate/display the next candidate without posting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
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
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BDEduJob-VerifiedQueue/1.0"})
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


def read_queue() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    items = data.get("items", []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        raise ValueError("verified_post_queue.json: 'items' must be a list")
    return [item for item in items if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate and show the next eligible item; do not publish")
    args = parser.parse_args()

    try:
        items = read_queue()
    except Exception as exc:
        log(f"Queue file could not be read: {exc}")
        set_output(False, False)
        return 0

    if not items:
        log("No queued items; regular auto-publisher may run.")
        set_output(False, False)
        return 0

    # Scheduled release is live-only. Do not accidentally mark drafts as published.
    if bot.BLOGGER_IS_DRAFT and not args.dry_run:
        log("BLOGGER_IS_DRAFT=true; refusing to process the live queue.")
        set_output(False, False)
        return 0

    now = datetime.now(timezone.utc)
    latest_public, public_titles = get_public_latest_post_time()
    state = read_state()
    last_attempt = parse_timestamp(str(state.get("last_attempt_utc", "")))
    cooldown_base = max([dt for dt in (latest_public, last_attempt) if dt is not None], default=None)
    if not args.dry_run and cooldown_base and now - cooldown_base < MIN_POST_GAP:
        log("A Blogger post was published/attempted within the last 30 minutes; skipping this run to prevent a burst.")
        set_output(True, False)
        return 0

    try:
        already_posted = set(bot.load_posted_jobs())
    except Exception:
        already_posted = set()

    # Authenticated list complements the public feed. The public feed remains the fallback.
    try:
        for title in bot.get_live_blogger_titles(100):
            if title:
                public_titles.add(normalize_title(title))
    except Exception:
        pass

    today_bd = datetime.now(BD_TZ).date()
    candidate: dict[str, Any] | None = None
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
            bot.save_posted_job(marker)
            already_posted.add(marker)
            continue

        html_path = ROOT / str(item.get("html_file", ""))
        if not html_path.is_file():
            log(f"HTML file missing; skipping {item_id}: {html_path}")
            continue
        html = html_path.read_text(encoding="utf-8")
        if "<!--more-->" not in html or not html.strip():
            log(f"HTML failed Blogger excerpt/content validation; skipping {item_id}.")
            continue

        labels = item.get("labels", [])
        if not isinstance(labels, list) or any(label not in bot.ALLOWED_BLOGGER_LABELS for label in labels):
            log(f"Invalid/unapproved Blogger Labels in {item_id}; skipping for safety.")
            continue

        candidate = item
        break

    if candidate is None:
        log("No unposted, non-expired, valid queue item remains; regular auto-publisher may run.")
        set_output(False, False)
        return 0

    title = str(candidate["title"])
    item_id = str(candidate["id"])
    marker = f"verified-queue:{item_id}"
    html_path = ROOT / str(candidate["html_file"])
    html = html_path.read_text(encoding="utf-8")
    labels = list(candidate["labels"])
    banner_url = str(candidate.get("banner_url", ""))
    fb_summary = str(candidate.get("facebook_summary", ""))

    if args.dry_run:
        log(f"DRY RUN — next post: {title}; labels={labels}; expires_on={candidate.get('expires_on', 'none')}")
        set_output(False, False)
        return 0

    # Persist an attempt timestamp before the API call; the workflow step itself
    # fails closed if the process crashes, and the next run still observes cooldown.
    state.update({"last_attempt_utc": now.isoformat(), "last_attempt_id": item_id})
    write_state(state)
    log(f"Publishing one verified post: {title}")

    try:
        result = bot.publish_to_blogger(
            title=title,
            html_content=html,
            labels=labels,
            is_draft=False,
            published_iso="",  # Let Blogger use the actual publication time; never backdate.
        )
    except Exception as exc:
        log(f"Blogger publish failed; this run remains rate-limited and the queue item will retry next run: {exc}")
        set_output(True, False)
        return 0

    post_url = str(result.get("url", ""))
    post_id = str(result.get("id", ""))
    state.update({"last_attempt_utc": now.isoformat(), "last_posted_id": item_id, "last_post_url": post_url})
    write_state(state)
    bot.save_posted_job(marker)
    log(f"Blogger post created. URL: {post_url or '(API response did not include URL)'}")

    if post_url:
        try:
            bot.share_to_facebook_page(
                title=title,
                post_url=post_url,
                banner_url=banner_url,
                summary_text=fb_summary,
            )
        except Exception as exc:
            log(f"Facebook share helper raised an error; Blogger post remains live: {exc}")

    try:
        bot.ping_google_websub_hub()
    except Exception:
        pass

    set_output(True, True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
