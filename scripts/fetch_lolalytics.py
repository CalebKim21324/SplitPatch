"""Builds + item usage per champion from lolalytics -> data/items/{usage.csv,builds.yaml}.

lolalytics server-renders its state as Qwik JSON (<script type="qwik/json">); values are base-36
references into an `objs` table. We read:
  - item1..item3 slot tables: [item_id, wr, pick_pct, games, avg_minute_completed]
  - core build: start set, 3-item core, item4 options
  - skill order (max order, measured at level 15)

Usage: python scripts/fetch_lolalytics.py --patch 16.22 --regions global kr
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHAMPS = {  # name in our CSVs -> (lolalytics slug, lane)
    "Azir": ("azir", "middle"), "Kalista": ("kalista", "bottom"), "Garen": ("garen", "top"),
    "Viego": ("viego", "jungle"), "Qiyana": ("qiyana", "middle"), "Lee Sin": ("leesin", "jungle"),
}
TOP_N = 8  # options kept per slot


def fetch(slug: str, lane: str, patch: str, region: str) -> str:
    url = f"https://lolalytics.com/lol/{slug}/build/?tier=emerald_plus&lane={lane}&patch={patch}"
    if region != "global":
        url += f"&region={region}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        time.sleep(1)
        return r.read().decode("utf-8", errors="replace")


def state(html: str):
    objs = json.loads(re.search(r'<script type="qwik/json">(.*?)</script>', html, re.S).group(1))["objs"]

    def resolve(v, depth=0):
        if depth > 10:
            return v
        if isinstance(v, str) and re.fullmatch(r"[0-9a-z]+", v):
            try:
                return resolve(objs[int(v, 36)], depth + 1)
            except (ValueError, IndexError):
                return v
        if isinstance(v, dict):
            return {k: resolve(x, depth + 1) for k, x in v.items()}
        if isinstance(v, list):
            return [resolve(x, depth + 1) for x in v]
        return v

    def find(key, want=dict):
        """First object holding `key` whose resolved value has type `want`."""
        for o in objs:
            if isinstance(o, dict) and key in o:
                r = resolve(o)
                if isinstance(r[key], want):
                    return r
        raise KeyError(key)

    return find


def parse(html: str) -> dict:
    find = state(html)
    slots = find("item1", list)
    core = find("core")
    skills = find("skillOrder", list)["skillOrder"]
    return {
        "slots": {s: slots[f"item{s}"][:TOP_N] for s in (1, 2, 3)},
        "core": core["core"]["set"],
        "item4": [o["id"] for o in core["item4"]],
        "start": core["start"]["setUnique"],
        "skill_order": skills[0][0],  # most common max order, e.g. "WQE"
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", default="16.22")
    ap.add_argument("--regions", nargs="+", default=["global"])
    a = ap.parse_args()
    label = f"26.{a.patch.split('.')[1]}"

    usage, builds = [], {}
    for name, (slug, lane) in CHAMPS.items():
        for region in a.regions:
            p = parse(fetch(slug, lane, a.patch, region))
            for slot, table in p["slots"].items():
                for item, wr, pick, games, minute in (row[:5] for row in table):
                    usage.append({"patch": label, "region": region, "champion": name, "slot": slot,
                                  "item": item, "wr": wr, "pick_pct": pick, "games": games, "minute": minute})
            if region == "global":
                builds[name] = {"lane": lane, "skill_order": p["skill_order"], "start": p["start"],
                                "core": p["core"], "item4": p["item4"][0] if p["item4"] else None}
            print(f"{name} {region}: core {p['core']} skill {p['skill_order']}")

    out = ROOT / "data" / "items"
    with open(out / "usage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(usage[0]))
        w.writeheader()
        w.writerows(usage)
    (out / "builds.yaml").write_text(
        f"# Most common build per champion, lolalytics Emerald+ global, patch {label}.\n"
        "# core = items 1-3 in order, item4 = most common 4th item. Item ids are Data Dragon ids.\n"
        + yaml.safe_dump({"patch": label, "champions": builds}, sort_keys=False), encoding="utf-8")
    print(f"wrote {len(usage)} usage rows and builds for {len(builds)} champions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
