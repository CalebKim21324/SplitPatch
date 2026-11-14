"""Reference target dummies for the sim -> sim/dummies.yaml.

Each dummy is the average base stats of every champion whose primary Data Dragon tag is
Mage, Fighter or Tank (champion.json, all champions). No hand-picked numbers.
Usage: python scripts/build_dummies.py --version 16.22.1
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"hp": "hp", "hp_per_lvl": "hpperlevel", "armor": "armor", "armor_per_lvl": "armorperlevel",
          "mr": "spellblock", "mr_per_lvl": "spellblockperlevel"}
DUMMIES = {"mage": "Mage", "bruiser": "Fighter", "tank": "Tank"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="16.22.1")
    a = ap.parse_args()
    url = f"https://ddragon.leagueoflegends.com/cdn/{a.version}/data/en_US/champion.json"
    champs = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "splitpatch"}), timeout=30))["data"]
    out = {}
    for name, tag in DUMMIES.items():
        group = [c["stats"] for c in champs.values() if c["tags"] and c["tags"][0] == tag]
        out[name] = {k: round(sum(s[v] for s in group) / len(group), 3) for k, v in FIELDS.items()}
        out[name]["n_champions"] = len(group)
    (ROOT / "sim" / "dummies.yaml").write_text(
        f"# Class-average base stats (primary tag), Data Dragon {a.version} champion.json.\n"
        "# Dummies have no items and don't fight back (SIMPLIFICATIONS.md).\n"
        + yaml.safe_dump({"version": a.version, "dummies": out}, sort_keys=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
