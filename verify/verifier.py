"""Independent verifier (PLAN.md 3.6). Deterministic, no LLM. The agent can't see or edit this.

  1. schema     allowlisted numeric fields only, `from` matches the current kit exactly
  2. limits     at most 3 fields, each element within 20% of its old value, no no-ops
  3. integrity  sim/, verify/, data/ unchanged since the run started
  4. target     sim rerun from scratch; both index deltas inside the diagnosis target bands
  5. holdout    hidden scenarios move at most 15% and not the wrong way
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ValidationError

from schemas import Category, Diagnosis, Kit, Proposal
from sim.indices import delta, evaluate
from sim.patching import apply, get_field
from verify import holdout_scenarios, integrity

MAX_FIELDS = 3
MAX_REL_CHANGE = 0.20

BASE_FIELDS = {"hp", "hp_per_lvl", "mp", "mp_per_lvl", "armor", "armor_per_lvl", "mr", "mr_per_lvl",
               "ad", "ad_per_lvl", "ms"}
ABILITY_FIELDS = {"base", "base_by_level", "ap_ratio", "armor_ratio", "ad_ratio", "bonus_ad_ratio", "pct_max_hp",
                  "pct_current_hp", "pct_missing_hp", "min_damage", "stack_base", "stack_ad_ratio",
                  "stack_ap_ratio", "shield", "shield_ap_ratio", "shield_bonus_hp_ratio", "damage_reduction",
                  "bonus_as", "slow", "cc_duration", "cooldown", "mana_cost", "range"}
NERF = {Category.OVERALL_STRONG, Category.SOLOQ_ONLY_STRONG, Category.PRO_JAIL}
BUFF = {Category.OVERALL_WEAK, Category.POPULAR_WEAK}


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class Result:
    passed: bool
    checks: list[Check] = field(default_factory=list)
    deltas: dict[str, float] = field(default_factory=dict)
    holdout: dict[str, float] = field(default_factory=dict)

    def failures(self) -> list[str]:
        return [f"{c.name}: {c.detail}" for c in self.checks if not c.ok]

    def to_dict(self) -> dict:
        return {"passed": self.passed, "checks": [c.__dict__ for c in self.checks],
                "deltas": self.deltas, "holdout": self.holdout}


def _elements(v) -> list[float]:
    return list(v) if isinstance(v, list) else [v]


def check_schema(p: Proposal, kit: Kit, diag: Diagnosis) -> list[str]:
    errs = []
    if p.champion != kit.name or p.patch != kit.patch:
        errs.append(f"proposal is for {p.champion} {p.patch}, kit is {kit.name} {kit.patch}")
    if p.category != diag.category:
        errs.append(f"category {p.category.value} != diagnosis {diag.category.value}")
    for ch in p.changes:
        parts = ch.field.split(".")
        if parts[0] == "base" and parts[1] not in BASE_FIELDS:
            errs.append(f"{ch.field}: base field not editable")
            continue
        if parts[0] == "abilities":
            if parts[1] not in kit.abilities:
                errs.append(f"{ch.field}: no ability {parts[1]}")
                continue
            if parts[2] not in ABILITY_FIELDS:
                errs.append(f"{ch.field}: ability field not editable")
                continue
        current = get_field(kit, ch.field)
        if current is None:
            errs.append(f"{ch.field}: field is empty in the kit; can't change what isn't there")
            continue
        if _elements(ch.from_) != _elements(current):
            errs.append(f"{ch.field}: stale 'from' {ch.from_} (kit has {current})")
        if isinstance(current, list) != isinstance(ch.to, list) or len(_elements(ch.to)) != len(_elements(current)):
            errs.append(f"{ch.field}: 'to' must have the same shape as the current value {current}")
    return errs


def check_limits(p: Proposal) -> list[str]:
    errs = []
    if not p.changes:
        errs.append("no changes")
    if len(p.changes) > MAX_FIELDS:
        errs.append(f"{len(p.changes)} fields changed (max {MAX_FIELDS})")
    fields = [c.field for c in p.changes]
    if len(set(fields)) != len(fields):
        errs.append("a field is changed twice")
    for ch in p.changes:
        olds, news = _elements(ch.from_), _elements(ch.to)
        if olds == news:
            errs.append(f"{ch.field}: no-op change")
        for o, n in zip(olds, news):
            if o == 0:
                if n != 0:
                    errs.append(f"{ch.field}: can't change a 0 value")
            elif abs(n / o - 1) > MAX_REL_CHANGE + 1e-9:
                errs.append(f"{ch.field}: {o} -> {n} is {abs(n / o - 1):.0%} (max {MAX_REL_CHANGE:.0%})")
    return errs


def verify(p: Proposal, kit: Kit, diag: Diagnosis, integrity_before: dict[str, str] | None = None) -> Result:
    res = Result(passed=False)

    def add(name, errs):
        res.checks.append(Check(name, not errs, "; ".join(errs) if errs else "ok"))
        return not errs

    try:
        p = Proposal.model_validate(p.model_dump(by_alias=True))
    except ValidationError as e:
        add("schema", [str(e)])
        return res
    if not add("schema", check_schema(p, kit, diag)) or not add("limits", check_limits(p)):
        return res
    if integrity_before is not None and not add("integrity", [f"modified: {f}" for f in integrity.changed(integrity_before)]):
        return res

    champ, patch = kit.name, kit.patch
    patched = apply(kit, p)
    before, after = evaluate(kit, champ, patch), evaluate(patched, champ, patch)
    res.deltas = delta(before, after)
    errs = []
    for idx, band in (("soloq_index", diag.target.soloq_index), ("pro_index", diag.target.pro_index)):
        if not band.contains(res.deltas[idx]):
            errs.append(f"{idx} moved {res.deltas[idx]:+.1%}, target [{_fmt(band.lo)}, {_fmt(band.hi)}]")
    if not add("target", errs):
        return res

    hb, ha = holdout_scenarios.run(kit, champ), holdout_scenarios.run(patched, champ)
    errs = []
    for k in hb:
        d = ha[k] / hb[k] - 1 if hb[k] else 0.0
        res.holdout[k] = round(d, 4)
        if abs(d) > holdout_scenarios.MAX_SWING:
            errs.append(f"hidden scenario swung {d:+.1%}")
        if diag.category in NERF and d > holdout_scenarios.WRONG_WAY_TOLERANCE:
            errs.append(f"hidden scenario got {d:+.1%} stronger on a nerf")
        if diag.category in BUFF and d < -holdout_scenarios.WRONG_WAY_TOLERANCE:
            errs.append(f"hidden scenario got {d:+.1%} weaker on a buff")
    res.passed = add("holdout", errs)
    return res


def _fmt(x):
    return "open" if x is None else f"{x:+.2%}"
