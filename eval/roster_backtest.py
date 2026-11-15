"""Whole-roster backtest against Riot's real patch notes.

For each patch P in 26.16..26.21, run the same deterministic scan SplitPatch ran on 26.22 (every
champion, global + KR, ban-rate-sliding line, pro presence as of P) and take its picks. Score each
pick against Riot's actual champion changes in the next patch's notes (holdout/riot_patch_notes.yaml).

Baselines, given the same number of nerf and buff picks each patch:
  - win-rate rule: nerf the highest global win rates, buff the lowest
  - chance: picking champions at random

Usage: python eval/roster_backtest.py   -> runs/backtest/roster_backtest.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import scan as scan_mod  # noqa: E402
from schemas import Category  # noqa: E402

PATCHES = ["26.16", "26.17", "26.18", "26.19", "26.20", "26.21"]
SERIES = ROOT / "data" / "stats" / "pro_series.json"
NERFISH = {"OVERALL_STRONG", "SOLOQ_ONLY_STRONG", "PRO_JAIL"}


def nxt(p: str) -> str:
    return f"26.{int(p.split('.')[1]) + 1}"


def pro_series(champs: list[str]) -> dict[str, dict[str, float]]:
    """Per-patch pro presence for each champion from gol.gg (cached)."""
    from scripts.fetch_golgg import BASE, SEASON, champion_ids, get, presence_by_patch
    cache = json.loads(SERIES.read_text(encoding="utf-8")) if SERIES.exists() else {}
    need = [c for c in champs if c not in cache]
    if need:
        ids = {scan_mod.norm(n): i for n, i in champion_ids(get(f"{BASE}/list/{SEASON}")).items()}
        for c in need:
            cid = ids.get(scan_mod.norm(c))
            s = presence_by_patch(get(f"{BASE}/champion-stats/{cid}/{SEASON}")) if cid else {}
            cache[c] = {f"26.{k.split('.')[1]}": v for k, v in s.items()}
            SERIES.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return {c: cache[c] for c in champs}


def presence_at(series: dict[str, float], patch: str) -> float:
    """Presence on that patch, or the latest earlier patch with pro games; 0 if none."""
    earlier = [p for p in series if int(p.split(".")[1]) <= int(patch.split(".")[1])]
    return series[max(earlier, key=lambda p: int(p.split(".")[1]))] if earlier else 0.0


def run() -> dict:
    notes = yaml.safe_load((ROOT / "holdout" / "riot_patch_notes.yaml").read_text(encoding="utf-8"))
    riot = {p: {e["champion"]: e["direction"] for e in notes[p]} for p in notes}
    out = {"patches": [], "totals": {}}
    tot = {k: {"picks": 0, "next": 0, "within2": 0} for k in ("splitpatch", "rule")}
    tot["chance"] = {"picks": 0, "next": 0.0}
    for P in PATCHES:
        current = P

        def pro_presence(champs, current=current):
            s = pro_series(champs)
            return {c: {"presence": presence_at(s[c], current), "from_patch": current} for c in champs}

        scan_mod.pro_presence = pro_presence
        sc = scan_mod.scan(P, 3, 2, 2)
        res = {r["champion"]: r for r in sc["results"]}
        n1, n2 = riot.get(nxt(P), {}), riot.get(nxt(nxt(P)), {})

        def judge(c, d):
            return {"champion": c, "dir": d, "riot_next": n1.get(c), "riot_after": n2.get(c),
                    "next": n1.get(c) == d, "within2": n1.get(c) == d or n2.get(c) == d}

        sp = [judge(c, "nerf" if res[c]["category"] in NERFISH else "buff") | {"category": res[c]["category"]}
              for c in sc["selected"]]
        n_nerf = sum(p["dir"] == "nerf" for p in sp)
        n_buff = len(sp) - n_nerf
        by_wr = sorted(res.values(), key=lambda r: (r["stats"].get("global") or r["stats"]["kr"])["wr"])
        rule = [judge(r["champion"], "nerf") for r in by_wr[::-1][:n_nerf]] + \
               [judge(r["champion"], "buff") for r in by_wr[:n_buff]]
        n = len(res)
        chance = sum(sum(d == "nerf" for d in n1.values()) / n for _ in range(n_nerf)) + \
            sum(sum(d == "buff" for d in n1.values()) / n for _ in range(n_buff))
        flagged = {c: ("nerf" if r["category"] in NERFISH else "buff") for c, r in res.items() if r["category"] != "HOLD"}
        riot_list = [{"champion": c, "dir": d, "flagged": flagged.get(c) == d, "in_data": c in res} for c, d in n1.items()]
        out["patches"].append({"data_patch": P, "riot_patch": nxt(P), "n_champions": n,
                               "flagged": sc["flagged"], "splitpatch": sp, "rule": rule,
                               "chance_hits": round(chance, 2), "riot": riot_list})
        for k, picks in (("splitpatch", sp), ("rule", rule)):
            tot[k]["picks"] += len(picks)
            tot[k]["next"] += sum(p["next"] for p in picks)
            tot[k]["within2"] += sum(p["within2"] for p in picks)
        tot["chance"]["picks"] += len(sp)
        tot["chance"]["next"] += chance
        print(f"{P}: SP {sum(p['next'] for p in sp)}/{len(sp)} next, {sum(p['within2'] for p in sp)} within 2 | "
              f"rule {sum(p['next'] for p in rule)}/{len(rule)} | chance {chance:.2f}", flush=True)
    tot["chance"]["next"] = round(tot["chance"]["next"], 1)
    riot_dir = [r for p in out["patches"] for r in p["riot"] if r["dir"] != "adjust" and r["in_data"]]
    tot["riot_changes"] = len(riot_dir)
    tot["riot_flagged"] = sum(r["flagged"] for r in riot_dir)
    out["totals"] = tot
    return out


def main() -> int:
    out = run()
    p = ROOT / "runs" / "backtest" / "roster_backtest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["totals"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
