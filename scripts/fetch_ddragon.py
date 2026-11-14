"""Fill the `base:` block of data/champions/<name>.yaml from Data Dragon champion.json.

Usage:
  python scripts/fetch_ddragon.py --version 14.3.1 azir kalista      # dry run, prints values
  python scripts/fetch_ddragon.py --version 14.3.1 azir --write      # rewrites base block in place
  python scripts/fetch_ddragon.py --versions                         # list available versions

Only the base block and `patch:` are touched; ability numbers stay hand-entered from the wiki.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CDN = "https://ddragon.leagueoflegends.com"

# our field -> Data Dragon stats key
FIELDS = {
    "hp": "hp", "hp_per_lvl": "hpperlevel", "mp": "mp", "mp_per_lvl": "mpperlevel",
    "armor": "armor", "armor_per_lvl": "armorperlevel", "mr": "spellblock", "mr_per_lvl": "spellblockperlevel",
    "ad": "attackdamage", "ad_per_lvl": "attackdamageperlevel", "as": "attackspeed",
    "as_per_lvl": "attackspeedperlevel", "ms": "movespeed", "range": "attackrange",
}


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "splitpatch-data-fetch"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_stats(version: str, champ_id: str) -> dict[str, float]:
    data = get_json(f"{CDN}/cdn/{version}/data/en_US/champion/{champ_id}.json")
    stats = data["data"][champ_id]["stats"]
    return {ours: stats[theirs] for ours, theirs in FIELDS.items()}


def rewrite(text: str, stats: dict[str, float], version: str) -> str:
    head, sep, rest = text.partition("\nbase:\n")
    if not sep:
        raise ValueError("no 'base:' block found")
    block, sep2, tail = rest.partition("\nabilities:")
    lines = []
    for line in block.splitlines():
        m = re.match(r"^(\s+)(\w+):", line)
        if m and m.group(2) in stats:
            lines.append(f"{m.group(1)}{m.group(2)}: {stats[m.group(2)]}  # ddragon {version}")
        else:
            lines.append(line)
    head = re.sub(r"^patch:.*$", f'patch: "{version}"  # ddragon version for base stats', head, flags=re.M)
    return head + sep + "\n".join(lines) + sep2 + tail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("champions", nargs="*")
    ap.add_argument("--version")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--versions", action="store_true")
    a = ap.parse_args()
    if a.versions:
        print(" ".join(get_json(f"{CDN}/api/versions.json")[:40]))
        return 0
    if not a.version or not a.champions:
        ap.error("--version and at least one champion are required")
    for name in a.champions:
        path = ROOT / "data" / "champions" / f"{name.lower()}.yaml"
        stats = fetch_stats(a.version, name.capitalize())
        print(f"{name} @ {a.version}: {stats}")
        if a.write:
            path.write_text(rewrite(path.read_text(encoding="utf-8"), stats, a.version), encoding="utf-8")
            print(f"  wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
