#!/usr/bin/env python3
"""
Daily Stock Digest
------------------
1. Fetches Yahoo Finance RSS news for the watchlist.
2. Scrapes Reddit (r/wallstreetbets, r/stocks, r/investing, r/StockMarket)
   using the public JSON API (no API key required) to measure social momentum.
3. Ranks symbols by Reddit mention velocity + score to surface GME-style
   crowd moves.
4. Falls back to curated BABA / TCEHY / Magnificent-7 news when no spike
   is detected.
5. Writes a Markdown digest to digest/YYYY-MM-DD.md and prints it to
   stdout (visible in GitHub Actions logs).
"""

import datetime
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WATCH_LIST = [
    "BABA", "TCEHY",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",  # Magnificent 7
]

REDDIT_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "StockMarket"]

# Minimum Reddit mentions within the current hot/top posts to count as a spike
SOCIAL_SPIKE_THRESHOLD = 3

# News items to show per ticker in the fallback section
NEWS_PER_TICKER_DEFAULT = 5
NEWS_PER_TICKER_SPIKE = 3   # fewer per ticker when spike tickers dominate

HEADERS = {
    "User-Agent": "StockDigestBot/1.0 (+https://github.com/matthewnty/Matthew)"
}


# ---------------------------------------------------------------------------
# Yahoo Finance helpers
# ---------------------------------------------------------------------------

def fetch_yahoo_news(ticker: str, max_items: int = 5) -> list:
    """Return up to *max_items* recent headlines from Yahoo Finance RSS."""
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline"
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
                        "ticker": ticker,
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
        print(f"[WARN] Yahoo RSS failed for {ticker}: {exc}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Reddit helpers
# ---------------------------------------------------------------------------

def fetch_reddit_posts(subreddit: str, limit: int = 100) -> list:
    """Return hot posts from *subreddit* via the public JSON endpoint."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            p = child["data"]
            posts.append(
                {
                    "title": p.get("title", ""),
                    "score": p.get("score", 0),
                    "num_comments": p.get("num_comments", 0),
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                    "subreddit": subreddit,
                    "created_utc": p.get("created_utc", 0),
                }
            )
        return posts
    except Exception as exc:  # noqa: BLE001
        print(
            f"[WARN] Reddit fetch failed for r/{subreddit}: {exc}",
            file=sys.stderr,
        )
        return []


def count_ticker_mentions(posts: list, tickers: list) -> dict:
    """Return per-ticker mention counts and aggregated engagement stats."""
    counts = defaultdict(
        lambda: {"mentions": 0, "total_score": 0, "total_comments": 0, "posts": []}
    )
    for post in posts:
        text = (post["title"] + " ").upper()
        for ticker in tickers:
            # Match whole-word occurrences: BABA or $BABA, not BABAS
            pattern = r"(?<![A-Z$])" + re.escape(ticker) + r"(?![A-Z])"
            if re.search(pattern, text) or f"${ticker}" in text:
                counts[ticker]["mentions"] += 1
                counts[ticker]["total_score"] += post["score"]
                counts[ticker]["total_comments"] += post["num_comments"]
                counts[ticker]["posts"].append(post)
    return counts


# ---------------------------------------------------------------------------
# Digest builder
# ---------------------------------------------------------------------------

def build_digest() -> str:
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# 📈 Daily Stock Digest — {now_str}", ""]

    # ------------------------------------------------------------------ #
    # 1. Reddit social momentum
    # ------------------------------------------------------------------ #
    print("[INFO] Fetching Reddit posts …", file=sys.stderr)
    all_posts = []
    for sub in REDDIT_SUBREDDITS:
        posts = fetch_reddit_posts(sub, limit=100)
        all_posts.extend(posts)
        time.sleep(1.5)   # respectful crawl delay

    ticker_data = count_ticker_mentions(all_posts, WATCH_LIST)

    # Rank by composite momentum score: score + 2×comments (comments signal
    # heated discussion more than passive upvotes)
    spike_tickers = sorted(
        [
            (t, d)
            for t, d in ticker_data.items()
            if d["mentions"] >= SOCIAL_SPIKE_THRESHOLD
        ],
        key=lambda x: x[1]["total_score"] + x[1]["total_comments"] * 2,
        reverse=True,
    )

    if spike_tickers:
        lines.append("## 🔥 Social Momentum Spikes (Reddit)")
        lines.append(
            "> Stocks with elevated Reddit discussion — "
            "potential GME-style crowd moves"
        )
        lines.append("")
        lines.append("| Ticker | Mentions | Reddit Score | Comments |")
        lines.append("|--------|:--------:|-------------:|---------:|")
        for ticker, data in spike_tickers[:10]:
            lines.append(
                f"| **{ticker}** | {data['mentions']} "
                f"| {data['total_score']:,} | {data['total_comments']:,} |"
            )
        lines.append("")

        # Top posts for the hottest ticker
        top_ticker, top_data = spike_tickers[0]
        lines.append(f"### Top Reddit posts mentioning {top_ticker}")
        for post in sorted(
            top_data["posts"], key=lambda p: p["score"], reverse=True
        )[:3]:
            title_trunc = post["title"][:110]
            lines.append(
                f"- [{title_trunc}]({post['url']}) — "
                f"⬆️ {post['score']:,} | 💬 {post['num_comments']:,} "
                f"| r/{post['subreddit']}"
            )
        lines.append("")
    else:
        lines.append("## 📊 Social Momentum")
        lines.append(
            "> No significant social spikes detected today. "
            "Showing full watchlist news below."
        )
        lines.append("")

    # ------------------------------------------------------------------ #
    # 2. Yahoo Finance news
    # ------------------------------------------------------------------ #
    print("[INFO] Fetching Yahoo Finance news …", file=sys.stderr)

    # If spikes found, fetch news for spike tickers first, then rest of
    # watchlist.  Otherwise iterate the full watchlist.
    if spike_tickers:
        spike_symbols = [t for t, _ in spike_tickers[:3]]
        news_order = spike_symbols + [
            t for t in WATCH_LIST if t not in spike_symbols
        ]
    else:
        news_order = WATCH_LIST[:]

    lines.append("## 📰 Latest News (Yahoo Finance)")
    lines.append("")

    for ticker in news_order:
        max_n = (
            NEWS_PER_TICKER_SPIKE
            if spike_tickers and ticker not in ["BABA", "TCEHY"]
            else NEWS_PER_TICKER_DEFAULT
        )
        items = fetch_yahoo_news(ticker, max_items=max_n)

        lines.append(f"### {ticker}")
        if not items:
            lines.append("*No news available.*")
        else:
            for item in items:
                pub = f" — *{item['pub_date']}*" if item["pub_date"] else ""
                lines.append(f"- [{item['title']}]({item['link']}){pub}")
        lines.append("")
        time.sleep(0.5)

    # ------------------------------------------------------------------ #
    # Footer
    # ------------------------------------------------------------------ #
    lines.append("---")
    lines.append(
        "*Generated by [matthewnty/Matthew](https://github.com/matthewnty/Matthew) "
        "• Sources: Yahoo Finance RSS · Reddit public API*"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    digest = build_digest()
    print(digest)

    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    out_dir = os.path.join(os.path.dirname(__file__), "..", "digest")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{date_str}.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(digest)
    print(f"[INFO] Digest written → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
