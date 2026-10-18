#!/usr/bin/env python3
"""
BABA News Tracker
-----------------
Fetches the latest 5 BABA (Alibaba) stock news headlines and sends them to a
Discord channel via webhook.

Required environment variable:
  DISCORD_WEBHOOK_URL  - Discord webhook URL for the target channel.
                         Create one in Discord: Channel Settings → Integrations
                         → Webhooks → New Webhook → Copy Webhook URL.
                         Then add it as a repository secret named
                         DISCORD_WEBHOOK_URL in GitHub Settings → Secrets and
                         variables → Actions.
"""

import datetime
import os
import sys
import xml.etree.ElementTree as ET

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TICKER = "BABA"
MAX_NEWS = 5
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

HEADERS = {
    "User-Agent": "BABANewsTracker/1.0 (+https://github.com/matthewnty/Matthew)"
}

# Alibaba red — used as the Discord embed accent colour
EMBED_COLOUR = 0xE31837


# ---------------------------------------------------------------------------
# News fetching
# ---------------------------------------------------------------------------

def fetch_yahoo_rss(ticker: str, max_items: int = 5) -> list:
    """Return up to *max_items* recent headlines from Yahoo Finance RSS."""
    url = (
        "https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={ticker}&region=US&lang=en-US"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            if title and link:
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "pub_date": pub_date,
                        "source": "Yahoo Finance",
                    }
                )
            if len(items) >= max_items:
                break
        return items
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Yahoo Finance RSS failed: {exc}", file=sys.stderr)
        return []


def fetch_google_news_rss(query: str, max_items: int = 5) -> list:
    """Return up to *max_items* recent headlines from Google News RSS."""
    url = (
        f"https://news.google.com/rss/search?q={query}"
        "&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.iter("item"):
            raw_title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            # Google News appends " - Source Name" to titles; split it off.
            if " - " in raw_title:
                title, source = raw_title.rsplit(" - ", 1)
                title = title.strip()
                source = source.strip()
            else:
                title = raw_title
                source = "Google News"
            if title and link:
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "pub_date": pub_date,
                        "source": source,
                    }
                )
            if len(items) >= max_items:
                break
        return items
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Google News RSS failed: {exc}", file=sys.stderr)
        return []


def fetch_baba_news(max_items: int = MAX_NEWS) -> list:
    """Fetch BABA news, falling back to Google News if Yahoo returns nothing."""
    news = fetch_yahoo_rss(TICKER, max_items)
    if not news:
        print(
            "[INFO] Yahoo Finance RSS returned no items — trying Google News…",
            file=sys.stderr,
        )
        news = fetch_google_news_rss("BABA+Alibaba+stock", max_items)
    return news[:max_items]


# ---------------------------------------------------------------------------
# Discord notification
# ---------------------------------------------------------------------------

def _truncate(text: str, limit: int = 1024) -> str:
    """Truncate *text* to fit within Discord's field value limit."""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def send_to_discord(news_items: list) -> None:
    """Post *news_items* to Discord as a rich embed via webhook."""
    if not DISCORD_WEBHOOK_URL:
        print(
            "[ERROR] DISCORD_WEBHOOK_URL environment variable is not set.\n"
            "        Add it as a GitHub repository secret named DISCORD_WEBHOOK_URL.",
            file=sys.stderr,
        )
        sys.exit(1)

    now_str = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    fields = []
    for idx, item in enumerate(news_items, start=1):
        pub = f"\n*{item['pub_date']}*" if item["pub_date"] else ""
        value = _truncate(f"[{item['title']}]({item['link']}){pub}")
        fields.append(
            {
                "name": f"{idx}. {item['source']}",
                "value": value,
                "inline": False,
            }
        )

    embed = {
        "title": f"📰 BABA — Latest {len(news_items)} News Headlines",
        "description": f"*{now_str}*",
        "color": EMBED_COLOUR,
        "fields": fields,
        "footer": {
            "text": "Source: Yahoo Finance / Google News • matthewnty/Matthew"
        },
    }

    try:
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"embeds": [embed]},
            timeout=15,
        )
        resp.raise_for_status()
        print("[INFO] Successfully sent to Discord.", file=sys.stderr)
    except requests.HTTPError as exc:
        print(
            f"[ERROR] Discord webhook request failed ({exc.response.status_code}): "
            f"{exc.response.text}",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to send to Discord: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"[INFO] Fetching latest {MAX_NEWS} BABA headlines…", file=sys.stderr)
    news = fetch_baba_news(MAX_NEWS)

    if not news:
        print("[WARN] No BABA news found from any source.", file=sys.stderr)
        if DISCORD_WEBHOOK_URL:
            now_str = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
            requests.post(
                DISCORD_WEBHOOK_URL,
                json={
                    "content": (
                        f"⚠️ BABA News Tracker: no headlines found at {now_str}. "
                        "Please check news sources."
                    )
                },
                timeout=15,
            )
        return

    for item in news:
        print(f"  • [{item['source']}] {item['title']}", file=sys.stderr)

    send_to_discord(news)


if __name__ == "__main__":
    main()
