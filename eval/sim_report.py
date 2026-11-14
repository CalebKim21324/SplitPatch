"""Sim evidence: indices for every champion x patch, calibration correlations, and Riot's real
changes run through our sim. Writes runs/sim_report.json (also feeds the workflow page).

Usage: python eval/sim_report.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import yaml
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.diagnose import diagnose  # noqa: E402
from schemas import ProRow, SoloQRow  # noqa: E402
from sim import kits  # noqa: E402
from sim.indices import delta, evaluate  # noqa: E402

TRAIN = [f"26.{n}" for n in range(16, 20)]  # earlier patches; test = 26.20-26.22


def minor(p: str) -> int:
    return int(p.split(".")[1])


def load_stats():
    soloq = [SoloQRow(**r) for r in csv.DictReader(open(ROOT / "data/stats/soloq.csv", encoding="utf-8"))]
    pro = [ProRow(**{k: (v or None) for k, v in r.items()})
           for r in csv.DictReader(open(ROOT / "data/stats/pro.csv", encoding="utf-8"))]
    return soloq, pro


def latest_pro(pro, champ, patch):
    """Most recent pro patch <= patch (no pro games on 26.19/26.21/26.22)."""
    rows = [r for r in pro if r.champion == champ and minor(r.patch) <= minor(patch)]
    return max(rows, key=lambda r: minor(r.patch)) if rows else None


def main() -> int:
    soloq, pro = load_stats()
    rows = []
    for champ in kits.CHAMPIONS:
        for p in kits.PATCHES:
            e = evaluate(kits.load_kit(champ, p), champ, p)
            pr = latest_pro(pro, champ, p)
            row = {"champion": champ, "patch": p, "soloq_index": e["soloq_index"], "pro_index": e["pro_index"],
                   "metrics": e["metrics"], "presence": pr.presence if pr else None,
                   "pro_patch": pr.patch if pr else None}
            for region in ("global", "kr"):
                s = next(r for r in soloq if r.champion == champ and r.patch == p and r.region == region)
                d = diagnose(s, pr.model_copy(update={"patch": p}))
                row[region] = {"wr": s.wr, "pr": s.pr, "br": s.br, "games": s.games,
                               "category": d.category.value, "reasons": d.reasons}
            rows.append(row)

    calib = {}
    for split, patches in (("all", kits.PATCHES), ("train", TRAIN)):
        sel = [r for r in rows if r["patch"] in patches]
        calib[split] = {
            "pro_index_vs_presence": spearmanr([r["pro_index"] for r in sel], [r["presence"] for r in sel]).statistic,
            **{f"soloq_index_vs_wr_{g}": spearmanr([r["soloq_index"] for r in sel], [r[g]["wr"] for r in sel]).statistic
               for g in ("global", "kr")},
            "n": len(sel),
        }

    riot = []
    changes = yaml.safe_load((ROOT / "holdout/riot_changes.yaml").read_text(encoding="utf-8"))["changes"]
    for c in changes:
        prev = f"26.{minor(c['patch']) - 1}"
        before = evaluate(kits.load_kit(c["champion"], prev), c["champion"], prev)
        after = evaluate(kits.load_kit(c["champion"], c["patch"]), c["champion"], prev)
        nxt = {g: next(r[g] for r in rows if r["champion"] == c["champion"] and r["patch"] == c["patch"])
               for g in ("global", "kr")}
        was = {g: next(r[g] for r in rows if r["champion"] == c["champion"] and r["patch"] == prev)
               for g in ("global", "kr")}
        riot.append({"champion": c["champion"], "patch": c["patch"], "direction": c["direction"],
                     "fields": c["fields"], "delta": delta(before, after),
                     "wr_before": {g: was[g]["wr"] for g in was}, "wr_after": {g: nxt[g]["wr"] for g in nxt},
                     "diagnosis_before": {g: was[g]["category"] for g in was}})

    out = {"rows": rows, "calibration": calib, "riot_changes": riot}
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs/sim_report.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")

    print("calibration (Spearman):")
    for k, v in calib.items():
        print(f"  {k}: " + ", ".join(f"{m}={x:.2f}" if isinstance(x, float) else f"{m}={x}" for m, x in v.items()))
    print("Riot changes through our sim (delta index):")
    for r in riot:
        print(f"  {r['champion']:8s} {r['patch']} {r['direction']:4s} soloq {r['delta']['soloq_index']:+.1%} "
              f"pro {r['delta']['pro_index']:+.1%} | WR global {r['wr_before']['global']}->{r['wr_after']['global']} "
              f"kr {r['wr_before']['kr']}->{r['wr_after']['kr']} | we said {r['diagnosis_before']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
