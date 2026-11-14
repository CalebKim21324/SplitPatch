"""Whole-roster solo queue stats from lolalytics tier lists -> data/stats/roster.csv

Each lane's tier-list page embeds every champion's stats in that lane (Qwik JSON keyed by Riot's
numeric champion key). We keep each champion's row for its main lane (`defaultLane`), for the
global and Korean servers. Champion keys are mapped to names with Data Dragon champion.json.

Usage: python scripts/fetch_roster.py --patch 16.22 --version 16.22.1
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

ROOT = Path(__file__).resolve().parents[1]
LANES = ["top", "jungle", "middle", "bottom", "support"]
UA = {"User-Agent": "Mozilla/5.0"}


def get(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def champion_names(version: str) -> dict[str, dict]:
    data = json.loads(get(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"))["data"]
    return {c["key"]: {"name": c["name"], "id": c["id"], "tags": c["tags"]} for c in data.values()}


def lane_rows(lane: str, patch: str, region: str) -> dict[str, dict]:
    url = f"https://lolalytics.com/lol/tierlist/?lane={lane}&tier=emerald_plus&patch={patch}"
    if region != "global":
        url += f"&region={region}"
    objs = json.loads(re.search(r'<script type="qwik/json">(.*?)</script>', get(url), re.S).group(1))["objs"]

    def ref(v):
        return objs[int(v, 36)] if isinstance(v, str) and re.fullmatch(r"[0-9a-z]+", v) else v

    is_row = lambda o: isinstance(o, dict) and {"wr", "games", "defaultLane"} <= o.keys()
    for o in objs:  # the dict whose values point at stat rows, keyed by champion key
        if isinstance(o, dict) and sum(is_row(ref(v)) for v in o.values()) > 50:
            return {k: {f: ref(ref(v)[f]) for f in ("lane", "defaultLane", "pctLane", "wr", "pr", "br", "games")}
                    for k, v in o.items() if is_row(ref(v))}
    raise RuntimeError(f"no stat table found for {lane}/{region}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", default="16.22")
    ap.add_argument("--version", default="16.22.1")
    ap.add_argument("--regions", nargs="+", default=["global", "kr"])
    a = ap.parse_args()
    names = champion_names(a.version)
    label = f"26.{a.patch.split('.')[1]}"
    out = []
    for region in a.regions:
        for lane in LANES:
            rows = lane_rows(lane, a.patch, region)
            kept = 0
            for key, r in rows.items():
                if r["defaultLane"] == lane and key in names:
                    out.append({"patch": label, "region": region, "champion": names[key]["name"],
                                "ddragon_id": names[key]["id"], "lane": lane, "pct_lane": r["pctLane"],
                                "wr": r["wr"], "pr": r["pr"], "br": r["br"], "games": r["games"]})
                    kept += 1
            print(f"{region:6s} {lane:8s} {len(rows)} rows, {kept} main-lane champions", flush=True)
            time.sleep(2)
    path = ROOT / "data" / "stats" / "roster.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} rows to {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
