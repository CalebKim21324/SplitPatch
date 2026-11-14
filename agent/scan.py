"""Whole-roster scan: diagnose every champion on a patch and pick this patch's changes.

Deterministic. Reads data/stats/roster.csv (every champion's main lane, global + KR), fetches pro
presence from gol.gg for the champions that look out of band, diagnoses each one with the server-
combined rules (ban-rate-sliding strong line), ranks by statistical confidence, and selects a
reasonable number of nerfs and buffs.

  python -m agent.scan --patch 26.22 [--nerfs 5 --buffs 4]
Writes data/stats/scan_<patch>.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

from agent.diagnose import Thresholds, diagnose_regions
from schemas import Category, ProRow, SoloQRow

ROOT = Path(__file__).resolve().parents[1]
MIN_GAMES = {"global": 20000, "kr": 3000}   # below this a server's row is too noisy to act on
NERF = {Category.OVERALL_STRONG, Category.SOLOQ_ONLY_STRONG}
BUFF = {Category.OVERALL_WEAK, Category.POPULAR_WEAK}
PRO_CACHE = ROOT / "data" / "stats" / "pro_roster.json"


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_roster(patch: str) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for r in csv.DictReader(open(ROOT / "data/stats/roster.csv", encoding="utf-8")):
        if r["patch"] == patch:
            out.setdefault(r["champion"], {})[r["region"]] = r
    return out


def pro_presence(champs: list[str]) -> dict[str, dict]:
    """Latest per-patch pro presence from gol.gg (cached). Champions with no pro games -> 0."""
    from scripts.fetch_golgg import BASE, SEASON, champion_ids, get, presence_by_patch
    cache = json.loads(PRO_CACHE.read_text(encoding="utf-8")) if PRO_CACHE.exists() else {}
    need = [c for c in champs if c not in cache]
    if need:
        ids = {norm(n): i for n, i in champion_ids(get(f"{BASE}/list/{SEASON}")).items()}
        for c in need:
            cid = ids.get(norm(c))
            series = presence_by_patch(get(f"{BASE}/champion-stats/{cid}/{SEASON}")) if cid else {}
            last = max(series, key=lambda p: int(p.split(".")[1])) if series else None
            cache[c] = {"presence": series.get(last, 0.0) if last else 0.0,
                        "from_patch": f"26.{last.split('.')[1]}" if last else None, "gol_id": cid}
        PRO_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return {c: cache[c] for c in champs}


def zscore(wr: float, games: int, line: float) -> float:
    p = wr / 100
    se = math.sqrt(p * (1 - p) / games) * 100
    return (wr - line) / se


def severity(cat: Category, rows: dict[str, SoloQRow], t_by_region: dict[str, Thresholds]) -> float:
    """How confidently the champion is past its line, in standard errors (max over servers)."""
    best = 0.0
    for g, s in rows.items():
        t = t_by_region[g]
        if cat == Category.PRO_JAIL:  # how confidently solo queue is losing while pros love it
            best = max(best, -zscore(s.wr, s.games, t.wr_pro_jail))
        elif cat in NERF:
            best = max(best, zscore(s.wr, s.games, t.strong_line(s.br)))
        elif cat == Category.POPULAR_WEAK:
            best = max(best, -zscore(s.wr, s.games, t.wr_popular_weak))
        elif cat == Category.OVERALL_WEAK:
            best = max(best, -zscore(s.wr, s.games, t.wr_weak))
    return round(best, 1)


def scan(patch: str, n_nerf: int, n_buff: int, n_pro: int = 2) -> dict:
    roster = load_roster(patch)
    avg_br = {g: sum(float(r[g]["br"]) for r in roster.values() if g in r) / sum(g in r for r in roster.values())
              for g in ("global", "kr")}
    soloq = {c: {g: SoloQRow(patch=patch, region=g, champion=c, wr=float(r["wr"]), pr=float(r["pr"]),
                             br=float(r["br"]), games=int(r["games"]))
                 for g, r in rr.items() if int(r["games"]) >= MIN_GAMES[g]} for c, rr in roster.items()}
    soloq = {c: rr for c, rr in soloq.items() if rr}
    # Pro presence only matters for champions near a line; fetch it for those.
    near = [c for c, rr in soloq.items() if any(s.wr > 52.0 or s.wr < 49.5 for s in rr.values())]
    pro = pro_presence(near)
    t_by_region = {g: Thresholds(avg_br=avg_br[g]) for g in avg_br}
    results = []
    for c, rr in soloq.items():
        p = pro.get(c, {"presence": 0.0, "from_patch": None})
        d = diagnose_regions(rr, ProRow(patch=patch, champion=c, presence=p["presence"]), None, avg_br=avg_br)
        results.append({"champion": c, "lane": next(iter(roster[c].values()))["lane"],
                        "category": d.category.value, "severity": severity(d.category, rr, t_by_region),
                        "reasons": d.reasons, "presence": p["presence"], "pro_patch": p["from_patch"],
                        "stats": {g: s.model_dump() for g, s in rr.items()}})
    nerfs = sorted([r for r in results if Category(r["category"]) in NERF], key=lambda r: -r["severity"])
    buffs = sorted([r for r in results if Category(r["category"]) in BUFF], key=lambda r: -r["severity"])
    pro_jail = sorted([r for r in results if r["category"] == "PRO_JAIL"], key=lambda r: -r["severity"])
    selected = [r["champion"] for r in nerfs[:n_nerf] + pro_jail[:n_pro] + buffs[:n_buff]]
    return {"patch": patch, "avg_ban_rate": avg_br, "n_champions": len(results),
            "flagged": {"nerf": len(nerfs), "pro_jail": len(pro_jail), "buff": len(buffs)}, "selected": selected,
            "results": sorted(results, key=lambda r: (r["category"] == "HOLD", -r["severity"]))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", default="26.22")
    ap.add_argument("--nerfs", type=int, default=3)
    ap.add_argument("--pro", type=int, default=2)
    ap.add_argument("--buffs", type=int, default=2)
    a = ap.parse_args()
    out = scan(a.patch, a.nerfs, a.buffs, a.pro)
    (ROOT / "data" / "stats" / f"scan_{a.patch}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{out['n_champions']} champions scanned; flagged {out['flagged']}; avg ban rate {out['avg_ban_rate']}")
    for r in out["results"]:
        if r["category"] == "HOLD":
            continue
        s = r["stats"]
        mark = "*" if r["champion"] in out["selected"] else " "
        print(f" {mark} {r['champion']:14s} {r['lane']:8s} {r['category']:18s} z={r['severity']:5.1f} "
              + " ".join(f"{g}:{v['wr']:.2f}%/{v['pr']:.1f}%pr/{v['br']:.1f}%br" for g, v in s.items())
              + f" pro {r['presence']:.0f}%")
    print("selected:", out["selected"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
