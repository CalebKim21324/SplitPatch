"""Item stats from Data Dragon item.json -> data/items/items.yaml.

Stats are parsed from each item's <stats> description block, which (unlike the `stats` field)
also lists Ability Haste, Lethality and penetration. Passive numbers aren't in Data Dragon and
stay as text (see SIMPLIFICATIONS.md).

Usage: python scripts/fetch_items.py --version 16.22.1
Items fetched = every id in data/items/usage.csv and data/items/builds.yaml.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "data" / "items"

STAT_KEYS = {  # description label -> our key
    "Ability Power": "ap", "Attack Damage": "ad", "Attack Speed": "as_pct", "Ability Haste": "ah",
    "Health": "hp", "Armor": "armor", "Magic Resist": "mr", "Mana": "mp",
    "Critical Strike Chance": "crit_pct", "Lethality": "lethality",
    "Armor Penetration": "armor_pen_pct", "Magic Penetration": "magic_pen",
    "Move Speed": "ms", "Life Steal": "lifesteal_pct", "Omnivamp": "omnivamp_pct",
    "Base Health Regen": "hp_regen_pct", "Base Mana Regen": "mp_regen_pct",
    "Heal and Shield Power": "heal_shield_pct", "Tenacity": "tenacity_pct",
}


def parse_stats(description: str) -> dict[str, float]:
    block = re.search(r"<stats>(.*?)</stats>", description, re.S)
    out: dict[str, float] = {}
    if not block:
        return out
    for value, label in re.findall(r"<attention>([\d.]+%?)</attention>\s*([^<]+)", block.group(1)):
        label = label.strip()
        key = STAT_KEYS.get(label, re.sub(r"\W+", "_", label.lower()).strip("_"))
        if key == "magic_pen" and value.endswith("%"):
            key = "magic_pen_pct"
        if key == "ms" and value.endswith("%"):
            key = "ms_pct"
        out[key] = float(value.rstrip("%"))
    return out


def wanted_ids() -> set[int]:
    ids = {int(r["item"]) for r in csv.DictReader(open(ITEMS / "usage.csv", encoding="utf-8"))}
    builds = yaml.safe_load((ITEMS / "builds.yaml").read_text(encoding="utf-8"))["champions"]
    for b in builds.values():
        ids |= set(b["core"]) | set(b["start"]) | ({b["item4"]} if b["item4"] else set())
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="16.22.1")
    a = ap.parse_args()
    url = f"https://ddragon.leagueoflegends.com/cdn/{a.version}/data/en_US/item.json"
    data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "splitpatch"}), timeout=30))["data"]

    items, missing = {}, []
    for i in sorted(wanted_ids()):
        d = data.get(str(i))
        if d is None:
            missing.append(i)
            continue
        passive = re.sub(r"<[^>]+>", " ", d["description"].split("</stats>")[-1])
        items[i] = {"name": d["name"], "gold": d["gold"]["total"], "stats": parse_stats(d["description"]),
                    "passive": re.sub(r"\s+", " ", passive).strip()[:300] or None}
    (ITEMS / "items.yaml").write_text(
        f"# Data Dragon {a.version} item.json. Stats parsed from each item's <stats> block.\n"
        "# Percent stats use *_pct keys (50 = 50%). Passives are text only (not simulated).\n"
        + yaml.safe_dump({"version": a.version, "items": items}, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    print(f"wrote {len(items)} items; not in ddragon: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
