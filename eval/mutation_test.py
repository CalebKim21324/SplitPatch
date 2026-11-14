"""Planted bad proposals (PLAN.md 3.6): report "the verifier rejected N/N planted bad patches".

Each case is a deliberately broken proposal against a real 26.22 kit and diagnosis.
Usage: python eval/mutation_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.diagnose import TARGETS  # noqa: E402
from schemas import Category, Diagnosis, Proposal  # noqa: E402
from sim.kits import load_kit  # noqa: E402
from verify import integrity  # noqa: E402
from verify.verifier import verify  # noqa: E402

PATCH = "26.22"
GAREN_Q = [30, 60, 90, 120, 150]
GAREN_E = [4, 7, 10, 13, 16]


def diag(champ: str, cat: Category) -> Diagnosis:
    return Diagnosis(champion=champ, patch=PATCH, category=cat, target=TARGETS[cat], reasons=["planted"])


def prop(champ: str, cat: Category, changes: list[dict]) -> Proposal:
    return Proposal(champion=champ, patch=PATCH, category=cat, changes=changes, rationale="planted")


S = Category.SOLOQ_ONLY_STRONG
CASES = [
    ("wrong direction (buff on a nerf)", "Garen", S, [{"field": "base.ad", "from": 69, "to": 74}]),
    ("too large (+40%)", "Garen", S, [{"field": "base.ad", "from": 69, "to": 41}]),
    ("too many fields (4)", "Garen", S, [
        {"field": "base.ad", "from": 69, "to": 66}, {"field": "base.hp", "from": 690, "to": 670},
        {"field": "base.armor", "from": 38, "to": 36}, {"field": "base.mr", "from": 32, "to": 31}]),
    ("forbidden base field (attack range)", "Garen", S, [{"field": "base.range", "from": 175, "to": 160}]),
    ("forbidden ability field (hits)", "Garen", S, [{"field": "abilities.Q_decisive_strike.hits", "from": 1, "to": 0.9}]),
    ("stale 'from' value", "Garen", S, [{"field": "base.ad", "from": 70, "to": 65}]),
    ("ability that doesn't exist", "Garen", S, [{"field": "abilities.Q_imaginary.base", "from": [1], "to": [0.9]}]),
    ("field that's empty in the kit", "Garen", S, [{"field": "abilities.Q_decisive_strike.ap_ratio", "from": 0.1, "to": 0.09}]),
    ("per-rank list with wrong length", "Garen", S, [{"field": "abilities.Q_decisive_strike.base", "from": GAREN_Q, "to": [28, 55, 85]}]),
    ("no-op change", "Garen", S, [{"field": "base.ad", "from": 69, "to": 69}]),
    ("same field twice", "Garen", S, [{"field": "base.ad", "from": 69, "to": 66}, {"field": "base.ad", "from": 69, "to": 65}]),
    ("category doesn't match diagnosis", "Garen", Category.OVERALL_WEAK, [{"field": "base.ad", "from": 69, "to": 66}]),
    ("too small to reach the band", "Garen", S, [{"field": "abilities.E_judgment.base", "from": GAREN_E, "to": [4, 7, 10, 13, 15]}]),
    ("hits pro power on a solo-only nerf", "Garen", S, [
        {"field": "abilities.E_judgment.ad_ratio", "from": [0.40, 0.43, 0.46, 0.49, 0.52], "to": [0.34, 0.36, 0.38, 0.40, 0.42]}]),
    ("wrong champion's kit", "Qiyana", S, [{"field": "base.ad", "from": 69, "to": 66}]),
]


def run() -> list[tuple[str, bool, list[str]]]:
    before = integrity.digest()
    out = []
    for name, champ, cat, changes in CASES:
        kit = load_kit("Garen", PATCH)
        p = prop(champ, cat, changes)
        res = verify(p, kit, diag("Garen", S), before)
        out.append((name, not res.passed, res.failures()))
    return out


def main() -> int:
    results = run()
    for name, rejected, why in results:
        print(f"{'REJECTED' if rejected else 'MISSED  '}  {name:40s} {why[0] if why else ''}")
    n = sum(r for _, r, _ in results)
    print(f"\nThe verifier rejected {n}/{len(results)} planted bad patches.")
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
