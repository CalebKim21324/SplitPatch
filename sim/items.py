"""Item blast radius (docs/WORKFLOW.md I-1, I-6). Deterministic.

For each champion that buys the item (lolalytics slot tables), place the item in that slot of the
champion's build, sim before/after the change, and weight by exposure E[c,i,s] = pick share in slot s.
  delta_index(c) = sum_s E[c,i,s] * delta_index(c, item in slot s)
"""
from __future__ import annotations

import csv
from functools import lru_cache

from sim import kits
from sim.indices import delta, evaluate

SLOTS = (1, 2, 3)


@lru_cache
def usage(region: str = "global") -> list[dict]:
    with open(kits.DATA / "items" / "usage.csv", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["region"] == region]


def exposure(item: int, region: str = "global") -> dict[str, dict[int, dict]]:
    """champion -> slot -> {share, minute, wr, games} for one item."""
    out: dict[str, dict[int, dict]] = {}
    for r in usage(region):
        if int(r["item"]) == item:
            out.setdefault(r["champion"], {})[int(r["slot"])] = {
                "share": float(r["pick_pct"]) / 100, "minute": float(r["minute"]),
                "wr": float(r["wr"]), "games": int(r["games"])}
    return out


def scaled(item: int, factor: float) -> dict:
    """The item with every stat multiplied by `factor` (a uniform +/-X% stat change)."""
    base = kits.items()[item]
    return {**base, "stats": {k: v * factor for k, v in base["stats"].items()}}


def blast_radius(item: int, new_item: dict, patch: str = "26.22", region: str = "global") -> list[dict]:
    rows = []
    for champ, slots in exposure(item, region).items():
        kit = kits.load_kit(champ, patch)
        base_build = kits.build(champ)
        weighted = {"soloq_index": 0.0, "pro_index": 0.0}
        per_slot = {}
        for s, e in slots.items():
            order = list(base_build)
            order[s - 1] = item
            before = evaluate(kit, champ, patch, {"build": order})
            after = evaluate(kit, champ, patch, {"build": order, "items": {item: new_item}})
            d = delta(before, after)
            per_slot[s] = {**e, **d}
            for k in weighted:
                weighted[k] += e["share"] * d[k]
        rows.append({"champion": champ, "slots": per_slot,
                     "exposure": round(sum(e["share"] for e in slots.values()), 4),
                     **{k: round(v, 4) for k, v in weighted.items()}})
    return sorted(rows, key=lambda r: -r["exposure"])
