"""Entry point: python -m quickloot [--dry-run | --test-alert]."""

import argparse
import html
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from quickloot.filtering import classify, fingerprint
from quickloot.sources import DealPost, fetch_channel
from quickloot.state import load_state, now_iso, save_state

CONFIG_PATH = Path("config.json")


def send_telegram(text: str, *, token: str, chat_id: str) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram rejected the message: {payload.get('description', 'unknown error')}")


def render_alert(post: DealPost, category: str) -> str:
    # Use the original posted words instead of inventing a discount or price.
    snippet = post.text[:1100]
    if len(post.text) > 1100:
        snippet = snippet.rsplit(" ", 1)[0] + "…"

    label = html.escape(category)
    body = html.escape(snippet)
    parts = [
        f"<b>QUICKLOOT | {label}</b>",
        "",
        body,
        "",
        "📍 Price and stock depend on your delivery PIN code.",
    ]
    if post.offer_url:
        parts.append(f'🛒 <a href="{html.escape(post.offer_url, quote=True)}">Open offer</a>')
    parts.append(f'🔗 <a href="{html.escape(post.post_url, quote=True)}">Original post</a>')
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send selected public deal posts to Telegram")
    parser.add_argument("--dry-run", action="store_true", help="Show matching offers without sending or writing state")
    parser.add_argument("--test-alert", action="store_true", help="Send a Telegram connectivity test")
    parser.add_argument("--send-existing", action="store_true", help="Alert on recent posts on initial setup")
    args = parser.parse_args()

    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if (args.test_alert or not args.dry_run) and (not token or not chat_id):
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID first.", file=sys.stderr)
        return 2

    if args.test_alert:
        send_telegram(
            "<b>QuickLoot test successful</b>\nFood, grocery and household deal alerts are configured.",
            token=token, chat_id=chat_id,
        )
        print("Test alert sent.")
        return 0

    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = json.load(file)
    channels = config.get("channels", [])
    if not channels:
        print("Add at least one public Telegram channel in config.json", file=sys.stderr)
        return 2

    state = load_state()
    started = state["initialized"]
    seen = state["seen"]
    hashes = state["sent_hashes"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=float(config.get("max_post_age_hours", 6)))
    city = str(config.get("preferred_city", "Mumbai"))
    max_alerts = max(1, int(config.get("max_alerts_per_run", 12)))
    collected: list[DealPost] = []
    errors: list[str] = []
    for channel in channels:
        try:
            posts = fetch_channel(channel)
            collected.extend(posts)
            print(f"@{channel}: {len(posts)} messages fetched")
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"@{channel}: {exc}")
            print(f"WARNING: {errors[-1]}", file=sys.stderr)

    if not collected:
        print("No source available, keeping existing state unchanged.", file=sys.stderr)
        return 1

    collected.sort(key=lambda post: post.published_at or datetime.min.replace(tzinfo=timezone.utc))

    # First run is intentionally quiet: existing deals may be old/expired.
    if not started and not args.send_existing and not args.dry_run:
        for post in collected:
            seen[post.post_id] = now_iso()
        state["initialized"] = True
        save_state(state)
        print(f"First run: saved {len(collected)} existing posts, no historical alerts sent.")
        return 0

    sent = 0
    matches = 0
    skipped = 0
    failed = 0
    for post in collected:
        if post.post_id in seen and not args.dry_run:
            continue
        if post.published_at and post.published_at < cutoff:
            if not args.dry_run:
                seen[post.post_id] = now_iso()
            skipped += 1
            continue

        category = classify(post.text, preferred_city=city).category
        if not category:
            if not args.dry_run:
                seen[post.post_id] = now_iso()
            skipped += 1
            continue

        matches += 1
        key = fingerprint(post.text)
        if key in hashes and not args.dry_run:
            seen[post.post_id] = now_iso()
            skipped += 1
            continue

        if args.dry_run:
            print(f"\nMATCH [{category}] {post.post_url}\n{post.text[:220]}")
            continue

        if sent >= max_alerts:
            # Leave extra matches unseen so the next execution can deliver them.
            continue

        try:
            send_telegram(render_alert(post, category), token=token, chat_id=chat_id)
            print(f"SENT [{category}] {post.post_url}")
            seen[post.post_id] = now_iso()
            hashes[key] = now_iso()
            sent += 1
            time.sleep(0.4)
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            print(f"ERROR sending {post.post_url}: {exc}", file=sys.stderr)
            failed += 1

    if not args.dry_run:
        state["initialized"] = True
        save_state(state)
    print(f"Summary: qualifying={matches}, sent={sent}, skipped={skipped}, errors={failed}, source_errors={len(errors)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
