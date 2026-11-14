"""Pro presence per patch from gol.gg -> data/stats/pro.csv.

gol.gg's patch filter only works from a browser (scripted POSTs return a stub),
but each champion-stats page embeds a "Presence by patch" chart series in its
HTML. That series is whole-number presence % for the patches with pro games,
so picks/bans/wr/games stay blank (per-patch values aren't published there).
Patches with no pro games are simply absent; see agent/data.py for how they're handled.

Usage: python scripts/fetch_golgg.py Azir Kalista Garen Viego --patches 16.16 16.17 16.18 16.19 16.20 16.21 16.22
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://gol.gg/champion"
SEASON = "season-S16/split-ALL/tournament-ALL/"


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def champion_ids(list_html: str) -> dict[str, str]:
    return dict((name, cid) for cid, name in
                re.findall(r"href='\./champion-stats/(\d+)/[^']*'>.*?/>\s*([^<]+?)</a>", list_html, re.S))


def presence_by_patch(stats_html: str) -> dict[str, float]:
    block = re.search(r"var golddatas = \{(.*?)\};", stats_html, re.S)
    if not block:
        return {}
    labels = re.findall(r"'([\d.]+)'", re.search(r"labels:\s*\[(.*?)\]", block.group(1), re.S).group(1))
    series = re.search(r"label: 'Presence %',\s*data:\s*\[(.*?)\]", block.group(1), re.S)
    values = [float(v) for v in series.group(1).split(",") if v.strip()]
    return dict(zip(labels, values))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("champions", nargs="+")
    ap.add_argument("--patches", nargs="+", required=True, help="gol.gg ids, e.g. 16.20")
    ap.add_argument("--out", default=str(ROOT / "data/stats/pro.csv"))
    a = ap.parse_args()

    ids = champion_ids(get(f"{BASE}/list/{SEASON}"))
    rows = []
    for champ in a.champions:
        series = presence_by_patch(get(f"{BASE}/champion-stats/{ids[champ]}/{SEASON}"))
        print(f"{champ}: {series}")
        for p in a.patches:
            if p in series:
                rows.append({"patch": f"26.{p.split('.')[1]}", "champion": champ, "presence": series[p],
                             "picks": "", "bans": "", "wr": "", "games": ""})
    rows.sort(key=lambda r: (int(r["patch"].split(".")[1]), r["champion"]))
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["patch", "champion", "presence", "picks", "bans", "wr", "games"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
