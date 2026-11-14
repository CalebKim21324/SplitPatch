"""Rule-based diagnoser: stats + complaints -> schemas.Diagnosis (PLAN.md 3.4). No LLM.

Stats alone decide the category and target ("whether and how much").
Complaints only produce lever hints ("which lever"), and buff requests are
dropped when the stats say the champion is already strong (one-trick bias).
"""
from __future__ import annotations

from dataclasses import dataclass

from schemas import Band, Category, Complaints, Diagnosis, ProRow, SoloQRow, Target


@dataclass(frozen=True)
class Thresholds:
    """Hand-set; tune on train patches only. Percentages."""

    presence_high: float = 30.0
    presence_low: float = 10.0
    br_high: float = 20.0
    wr_strong: float = 52.5
    wr_weak: float = 48.0
    wr_pro_jail: float = 49.0
    pr_high: float = 5.0
    wr_popular_weak: float = 49.5


TARGETS: dict[Category, Target] = {
    Category.PRO_JAIL: Target(pro_index=Band(lo=-0.15, hi=-0.08), soloq_index=Band(lo=-0.01)),
    Category.OVERALL_STRONG: Target(pro_index=Band(lo=-0.08, hi=-0.03), soloq_index=Band(lo=-0.08, hi=-0.03)),
    Category.OVERALL_WEAK: Target(soloq_index=Band(lo=0.03, hi=0.08)),
    Category.SOLOQ_ONLY_STRONG: Target(soloq_index=Band(lo=-0.08, hi=-0.03), pro_index=Band(lo=-0.01)),
    # Popular but losing: a small, targeted solo queue buff; don't let pro power jump.
    Category.POPULAR_WEAK: Target(soloq_index=Band(lo=0.02, hi=0.06), pro_index=Band(hi=0.03)),
    Category.HOLD: Target(pro_index=Band(lo=0.0, hi=0.0), soloq_index=Band(lo=0.0, hi=0.0)),
}

# Which complaint directions are usable as hints for each category.
_ALLOWED = {
    Category.PRO_JAIL: {"buff", "nerf"},
    Category.OVERALL_STRONG: {"nerf"},
    Category.SOLOQ_ONLY_STRONG: {"nerf"},
    Category.OVERALL_WEAK: {"buff"},
    Category.POPULAR_WEAK: {"buff"},
    Category.HOLD: set(),
}


def categorize(soloq: SoloQRow, pro: ProRow, t: Thresholds = Thresholds()) -> tuple[Category, list[str]]:
    wr, pr, br, pres = soloq.wr, soloq.pr, soloq.br, pro.presence
    hi, lo = pres >= t.presence_high, pres < t.presence_low
    facts = f"soloq WR {wr:.2f}%, PR {pr:.2f}%, BR {br:.2f}%, pro presence {pres:.1f}%"

    if hi and wr < t.wr_pro_jail:
        return Category.PRO_JAIL, [facts, f"presence >= {t.presence_high} and WR < {t.wr_pro_jail}"]
    if wr > t.wr_strong and (hi or br >= t.br_high):
        return Category.OVERALL_STRONG, [facts, f"WR > {t.wr_strong} and (presence >= {t.presence_high} or BR >= {t.br_high})"]
    if wr > t.wr_strong and lo:
        return Category.SOLOQ_ONLY_STRONG, [facts, f"WR > {t.wr_strong} and presence < {t.presence_low}"]
    if wr < t.wr_weak and not hi:
        return Category.OVERALL_WEAK, [facts, f"WR < {t.wr_weak} and presence < {t.presence_high}"]
    if wr < t.wr_popular_weak and pr >= t.pr_high:
        return Category.POPULAR_WEAK, [facts, f"WR < {t.wr_popular_weak} and PR >= {t.pr_high}"]
    return Category.HOLD, [facts, "no rule matched"]


def lever_hints(category: Category, complaints: Complaints | None) -> list[str]:
    if complaints is None:
        return []
    ok = _ALLOWED[category]
    counts: dict[str, int] = {}
    for c in complaints.complaints:
        if c.direction in ok and c.tag != "too_strong":
            counts[c.tag] = counts.get(c.tag, 0) + c.count
    return [tag for tag, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def diagnose(soloq: SoloQRow, pro: ProRow, complaints: Complaints | None = None,
             t: Thresholds = Thresholds()) -> Diagnosis:
    if (soloq.champion, soloq.patch) != (pro.champion, pro.patch):
        raise ValueError("soloq and pro rows must be for the same champion and patch")
    category, reasons = categorize(soloq, pro, t)
    return Diagnosis(champion=soloq.champion, patch=soloq.patch, category=category,
                     target=TARGETS[category], reasons=reasons,
                     lever_hints=lever_hints(category, complaints))
