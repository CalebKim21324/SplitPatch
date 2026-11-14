"""Backtest (PLAN.md 4): SplitPatch vs rule baseline vs LLM one-shot, against Riot's real changes.

Row = (champion, stats patch p) for p in 26.16-26.21; Riot's answer is its change in p+1 (holdout/).
Train = 26.16-26.18 (thresholds were set looking at these), test = 26.19-26.21 (headline).
Results are cached in runs/backtest/rows.json so an interrupted run resumes.

Usage: python eval/backtest.py [--workers 4] [--no-llm]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.run_patch import run_champion, stats_for  # noqa: E402
from eval.baselines import lever_of, one_shot, rule_baseline  # noqa: E402
from schemas import Category, Diagnosis, Proposal  # noqa: E402
from sim.kits import CHAMPIONS, load_kit  # noqa: E402
from verify import integrity  # noqa: E402
from verify.verifier import verify  # noqa: E402

PATCHES = [f"26.{n}" for n in range(16, 22)]
TRAIN, TEST = PATCHES[:3], PATCHES[3:]
OUT = ROOT / "runs" / "backtest"
NERF = {"OVERALL_STRONG", "SOLOQ_ONLY_STRONG", "PRO_JAIL"}
BUFF = {"OVERALL_WEAK", "POPULAR_WEAK"}


def riot_answers() -> dict:
    changes = yaml.safe_load((ROOT / "holdout/riot_changes.yaml").read_text(encoding="utf-8"))["changes"]
    return {(c["champion"], c["patch"]): c for c in changes}


def nxt(p: str) -> str:
    return f"26.{int(p.split('.')[1]) + 1}"


def direction_of(category: str) -> str:
    return "nerf" if category in NERF else "buff" if category in BUFF else "hold"


def run_row(champ: str, p: str, use_llm: bool) -> dict:
    t0 = time.time()
    _, _, stats = stats_for(champ, p)
    row = {"champion": champ, "patch": p, "split": "train" if p in TRAIN else "test", "stats": stats,
           "rule": rule_baseline(stats)}
    trace = run_champion(champ, p, use_llm, False, {})
    cat = trace["diagnosis"]["category"]
    prop = (trace.get("agent") or {}).get("proposal")
    row["splitpatch"] = {"category": cat, "direction": direction_of(cat),
                         "lever": lever_of(prop["changes"][0]["field"]) if prop else None,
                         "proposal": prop, "outcome": (trace.get("agent") or {}).get("outcome"),
                         "submissions": len(trace.get("submissions", [])),
                         "notes_ok": (trace.get("notes") or {}).get("checker_passed"),
                         "seconds": round(time.time() - t0, 1)}
    if use_llm:
        t1 = time.time()
        kit = load_kit(champ, p)
        os_ = one_shot(kit, stats)
        os_["seconds"] = round(time.time() - t1, 1)
        # Would the one-shot diff pass our verifier? Only defined where SplitPatch has a target.
        if cat != "HOLD" and os_["direction"] != "hold" and os_["changes"]:
            d = Diagnosis.model_validate(trace["diagnosis"])
            try:
                fixed = []
                for c in os_["changes"]:
                    from sim.patching import get_field
                    cur = get_field(kit, c["field"])
                    scalar = not isinstance(cur, list)
                    fixed.append({"field": c["field"], "from": c["from"][0] if scalar and len(c["from"]) == 1 else c["from"],
                                  "to": c["to"][0] if scalar and len(c["to"]) == 1 else c["to"]})
                pr = Proposal(champion=kit.name, patch=p, category=Category(cat), changes=fixed, rationale=os_["rationale"])
                res = verify(pr, kit, d, integrity.digest())
                os_["verifier"] = {"passed": res.passed, "failures": res.failures(), "deltas": res.deltas}
            except Exception as e:
                os_["verifier"] = {"passed": False, "failures": [f"invalid proposal: {e}"]}
        row["one_shot"] = os_
    return row


def score(rows: list[dict], answers: dict) -> dict:
    out = {}
    for split in ("train", "test", "all"):
        sel = [r for r in rows if split == "all" or r["split"] == split]
        res = {"n": len(sel), "riot_changes": 0}
        for system in ("rule", "one_shot", "splitpatch"):
            have = [r for r in sel if system in r]
            agree = lever_hits = changed = 0
            for r in have:
                riot = answers.get((r["champion"], nxt(r["patch"])))
                truth = riot["direction"] if riot else "hold"
                agree += r[system]["direction"] == truth
                if riot:
                    changed += 1
                    lever_hits += r[system].get("lever") == riot["lever"]
            res["riot_changes"] = changed
            res[system] = {"direction_agreement": f"{agree}/{len(have)}" if have else "n/a",
                           "lever_agreement": f"{lever_hits}/{changed}" if have and changed else "n/a"}
        flagged = [r for r in sel if r["splitpatch"]["category"] != "HOLD"]
        res["verification"] = {
            "splitpatch_passed": f"{sum(r['splitpatch']['outcome'] == 'PASS' for r in flagged)}/{len(flagged)}",
            "one_shot_passed": f"{sum(bool(r.get('one_shot', {}).get('verifier', {}).get('passed')) for r in flagged)}/"
                               f"{sum('verifier' in r.get('one_shot', {}) for r in flagged)}",
        }
        out[split] = res
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / ("rows_nollm.json" if a.no_llm else "rows.json")
    rows = {f"{r['champion']}|{r['patch']}": r for r in json.loads(cache.read_text(encoding="utf-8"))} if cache.exists() else {}
    todo = [(c, p) for p in PATCHES for c in CHAMPIONS if f"{c}|{p}" not in rows]
    print(f"{len(rows)} cached, {len(todo)} to run", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(run_row, c, p, not a.no_llm): (c, p) for c, p in todo}
        for f in as_completed(futs):
            c, p = futs[f]
            try:
                r = f.result()
                rows[f"{c}|{p}"] = r
                cache.write_text(json.dumps(list(rows.values()), default=float), encoding="utf-8")
                sp = r["splitpatch"]
                print(f"  {c:8s} {p} splitpatch={sp['direction']:4s} ({sp['outcome']}) rule={r['rule']['direction']:4s} "
                      f"one_shot={r.get('one_shot', {}).get('direction', '-')}", flush=True)
            except Exception as e:
                print(f"  {c:8s} {p} ERROR {type(e).__name__}: {e}", flush=True)
    scores = score(list(rows.values()), riot_answers())
    (OUT / ("scores_nollm.json" if a.no_llm else "scores.json")).write_text(json.dumps(scores, indent=1), encoding="utf-8")
    print(json.dumps(scores, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
