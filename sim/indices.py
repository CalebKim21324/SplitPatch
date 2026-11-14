"""soloq_index / pro_index (PLAN.md 3.2).

Each metric is normalized by the pool mean for that patch (6 champions, baseline kits), so an
index of 1.0 is "pool average" and a relative change of the index is meaningful. PLAN.md said
z-scores; ratio-to-mean is used instead because z-scores near 0 make "-8%" undefined
(SIMPLIFICATIONS.md). Lower-is-better metrics (time to kill) are inverted.
Weights are hand-set (equal) and tuned on train patches only.
"""
from __future__ import annotations

from functools import lru_cache

from schemas import Kit
from sim import kits
from sim.scenarios import LOWER_IS_BETTER, PRO_METRICS, SOLOQ_METRICS, run_all

WEIGHTS = {m: 1.0 for m in SOLOQ_METRICS + PRO_METRICS}


@lru_cache(maxsize=None)
def pool_means(patch: str) -> dict[str, float]:
    rows = [run_all(kits.load_kit(c, patch), c) for c in kits.CHAMPIONS]
    return {m: sum(r[m] for r in rows) / len(rows) for m in rows[0]}


def _index(metrics: dict[str, float], means: dict[str, float], names: list[str]) -> float:
    total = sum(WEIGHTS[m] for m in names)
    score = 0.0
    for m in names:
        if m in LOWER_IS_BETTER:
            ratio = means[m] / metrics[m] if metrics[m] else 0.0
        else:
            ratio = metrics[m] / means[m] if means[m] else 0.0
        score += WEIGHTS[m] * ratio
    return score / total


def indices(metrics: dict[str, float], patch: str) -> dict[str, float]:
    means = pool_means(patch)
    return {"soloq_index": round(_index(metrics, means, SOLOQ_METRICS), 4),
            "pro_index": round(_index(metrics, means, PRO_METRICS), 4)}


def evaluate(kit: Kit, champ: str, patch: str, override=None) -> dict:
    """Metrics + indices for one kit (patched or not) at a patch, against that patch's pool means."""
    m = run_all(kit, champ, override)
    return {"metrics": m, **indices(m, patch)}


def delta(before: dict, after: dict) -> dict[str, float]:
    """Relative change of each index, as fractions (-0.08 = -8%)."""
    return {k: round(after[k] / before[k] - 1, 4) for k in ("soloq_index", "pro_index")}
