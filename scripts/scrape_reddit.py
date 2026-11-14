"""Scrape recent posts from each champion's subreddit -> data/sentiment/<slug>/<patch>.jsonl

Uses Reddit's public Atom feeds (/new/.rss and /top/.rss?t=week). The JSON API returns 403
without auth. Posts are UNTRUSTED text: they are only ever read by agent/sentiment.py, inside
<untrusted_post> tags, and never reach the diagnoser or the patch agent.

Usage: python scripts/scrape_reddit.py --patch 26.22
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBS = {"Azir": "AzirMains", "Kalista": "KalistaMains", "Garen": "GarenMains",
        "Viego": "ViegoMains", "Qiyana": "QiyanaMains", "Lee Sin": "LeeSinMains"}
FEEDS = ["new/.rss", "top/.rss?t=week"]
ATOM = {"a": "http://www.w3.org/2005/Atom"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
MAX_TEXT = 1500


def get(url: str, tries: int = 4) -> bytes:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1:
                raise
            time.sleep(20 * (i + 1))
    raise RuntimeError("unreachable")


def clean(raw: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(raw or "")))
    text = re.sub(r"submitted by\s+/u/\S+.*$", "", text, flags=re.S)  # drop the feed's footer
    return re.sub(r"\s+", " ", text).strip()[:MAX_TEXT]


def parse(feed: bytes) -> list[dict]:
    root = ET.fromstring(feed)
    posts = []
    for e in root.findall("a:entry", ATOM):
        pid = (e.findtext("a:id", "", ATOM) or "").strip()
        link = e.find("a:link", ATOM)
        posts.append({
            "id": pid,
            "title": clean(e.findtext("a:title", "", ATOM)),
            "text": clean(e.findtext("a:content", "", ATOM)),
            "published": e.findtext("a:published", "", ATOM) or e.findtext("a:updated", "", ATOM),
            "url": link.get("href") if link is not None else None,
        })
    return posts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", default="26.22")
    ap.add_argument("--champions", nargs="*", default=list(SUBS))
    a = ap.parse_args()
    for champ in a.champions:
        sub, seen, rows = SUBS[champ], set(), []
        for feed in FEEDS:
            try:
                for p in parse(get(f"https://www.reddit.com/r/{sub}/{feed}")):
                    if p["id"] and p["id"] not in seen:
                        seen.add(p["id"])
                        rows.append({**p, "subreddit": sub, "feed": feed.split("/")[0]})
            except Exception as e:  # keep going; report what failed
                print(f"  {sub}/{feed}: {type(e).__name__} {e}")
            time.sleep(8)
        out = ROOT / "data" / "sentiment" / champ.lower().replace(" ", "") / f"{a.patch}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"{champ}: {len(rows)} posts -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
