"""Load the inputs a scenario needs: kit snapshot for a patch, build, items, dummies, combos.

Kit snapshots live in data/champions/snapshots/<slug>/<patch>.yaml (built by
eval/build_snapshots.py). Without a snapshot the 26.22 kit is used. sim/ never reads holdout/.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from schemas import Kit
from sim.engine import ItemStats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHAMPIONS = ["Azir", "Kalista", "Garen", "Viego", "Qiyana", "Lee Sin"]
PATCHES = [f"26.{n}" for n in range(16, 23)]


def slug(champ: str) -> str:
    return champ.lower().replace(" ", "")


def load_kit(champ: str, patch: str | None = None) -> Kit:
    snap = DATA / "champions" / "snapshots" / slug(champ) / f"{patch}.yaml"
    if patch and snap.exists():
        return Kit.load(snap)
    return Kit.load(DATA / "champions" / f"{slug(champ)}.yaml")


@lru_cache
def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def items() -> dict[int, dict]:
    return _yaml(DATA / "items" / "items.yaml")["items"]


def build(champ: str) -> list[int]:
    """Item ids in completion order: core items 1-3 then the most common 4th."""
    b = _yaml(DATA / "items" / "builds.yaml")["champions"][champ]
    return b["core"] + ([b["item4"]] if b["item4"] else [])


def build_stats(champ: str, n_items: int, override: dict | None = None) -> ItemStats:
    """Summed stats of the first n items of the champion's build.

    override = {"items": {id: item_dict}, "build": [ids]}: swap in edited items and/or a different
    build order (used by the item blast-radius check).
    """
    override = override or {}
    catalog = {**items(), **override.get("items", {})}
    order = override.get("build") or build(champ)
    return ItemStats.total([catalog[i]["stats"] for i in order[:n_items]])


def dummies() -> dict[str, dict]:
    return _yaml(ROOT / "sim" / "dummies.yaml")["dummies"]


def combo(champ: str) -> dict:
    return _yaml(ROOT / "sim" / "combos.yaml")[champ]
