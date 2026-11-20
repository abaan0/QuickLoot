"""Read the public, login-free Telegram preview of selected channels.

Important: the /s/ preview is not an official API and may change, become
restricted, or omit posts that are images without captions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class DealPost:
    post_id: str
    channel: str
    text: str
    post_url: str
    offer_url: str | None
    published_at: datetime | None


def parse_preview(html: str, channel: str) -> list[DealPost]:
    soup = BeautifulSoup(html, "html.parser")
    posts: list[DealPost] = []

    for node in soup.select(".tgme_widget_message[data-post]"):
        post_id = str(node.get("data-post", "")).strip()
        if not post_id or "/" not in post_id:
            continue

        # Read this post's own caption, not comments or a forwarded preview.
        text_node = node.select_one(".tgme_widget_message_text")
        if text_node is None:
            continue

        # Reply snippets can contain unrelated words from another message.
        for extra in text_node.select(".tgme_widget_message_reply"):
            extra.decompose()

        text = "\n".join(line.strip() for line in text_node.stripped_strings)
        text = "\n".join(line for line in text.splitlines() if line)
        if not text:
            continue

        # First explicit external link from the message body (if present).
        offer_url = None
        for anchor in text_node.select("a[href]"):
            href = anchor.get("href", "").strip()
            parsed = urlparse(href)
            if parsed.scheme != "https" and parsed.scheme != "http":
                continue
            if parsed.hostname and parsed.hostname.lower().removeprefix("www.") not in {
                "t.me", "telegram.me", "telegram.org", "telegram.dog"
            }:
                offer_url = href
                break

        time_node = node.select_one(".tgme_widget_message_date time[datetime]")
        published = None
        if time_node is not None:
            date_string = time_node.get("datetime", "")
            try:
                published = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        posts.append(
            DealPost(
                post_id=post_id,
                channel=channel,
                text=text,
                post_url=f"https://t.me/{post_id}",
                offer_url=offer_url,
                published_at=published,
            )
        )

    return posts


def fetch_channel(channel: str, session: requests.Session | None = None) -> list[DealPost]:
    channel = channel.strip().lstrip("@")
    if not channel or not channel.replace("_", "").isalnum():
        raise ValueError(f"Invalid public Telegram channel: {channel!r}")

    client = session or requests.Session()
    response = client.get(
        f"https://t.me/s/{channel}",
        timeout=25,
        headers={"User-Agent": "Mozilla/5.0 (compatible; QuickLoot/1.0)"},
    )
    response.raise_for_status()
    posts = parse_preview(response.text, channel)
    if not posts:
        raise ValueError(
            f"No readable messages on @{channel}. This channel may be private, "
            "unavailable, or Telegram may have changed its HTML."
        )
    return posts
