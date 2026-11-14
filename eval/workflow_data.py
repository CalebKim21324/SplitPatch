"""Data for the workflow page: sim report + item blast radius -> runs/workflow_data.json.

Usage: python eval/workflow_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval import sim_report  # noqa: E402
from sim import kits  # noqa: E402
from sim.items import blast_radius, scaled  # noqa: E402

SHARED_ITEMS = [6699, 3071, 6698, 6697, 3814, 3031, 3033, 3036]  # bought by 2+ of our champions (>=3% in a slot)


def main() -> int:
    sim_report.main()
    report = json.loads((ROOT / "runs/sim_report.json").read_text(encoding="utf-8"))
    catalog = kits.items()
    report["items"] = []
    for i in SHARED_ITEMS:
        report["items"].append({
            "id": i, "name": catalog[i]["name"], "gold": catalog[i]["gold"], "stats": catalog[i]["stats"],
            "change": "+10% all stats",
            "blast": blast_radius(i, scaled(i, 1.10)),
        })
    report["builds"] = {c: [catalog[i]["name"] for i in kits.build(c)] for c in kits.CHAMPIONS}
    run = ROOT / "proposals" / "26.22" / "summary.json"
    report["run"] = json.loads(run.read_text(encoding="utf-8")) if run.exists() else None
    bt_rows, bt_scores = ROOT / "runs/backtest/rows.json", ROOT / "runs/backtest/scores.json"
    report["backtest"] = None
    if bt_rows.exists() and bt_scores.exists():
        from eval.backtest import nxt, riot_answers
        ans = riot_answers()
        rows = json.loads(bt_rows.read_text(encoding="utf-8"))
        report["backtest"] = {"scores": json.loads(bt_scores.read_text(encoding="utf-8")), "rows": [
            {"champion": r["champion"], "patch": r["patch"], "rule": r["rule"],
             "splitpatch": {k: r["splitpatch"][k] for k in ("direction", "category", "outcome", "lever")},
             "one_shot": {"direction": r["one_shot"]["direction"]} if "one_shot" in r else None,
             "riot": (ans.get((r["champion"], nxt(r["patch"]))) or {}).get("direction", "hold")} for r in rows]}
    (ROOT / "runs/workflow_data.json").write_text(json.dumps(report, default=float), encoding="utf-8")
    print(f"wrote runs/workflow_data.json ({(ROOT / 'runs/workflow_data.json').stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
