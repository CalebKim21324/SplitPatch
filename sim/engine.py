"""Deterministic combat math (PLAN.md 3.2). No LLM, no randomness.

Formulas (wiki.leagueoflegends.com, checked 2026-11-14):
  stat at level n   = base + g * (n-1) * (0.7025 + 0.0175 * (n-1))          (Champion_statistic)
  attack speed      = base_as + (bonus_as% / 100) * as_ratio, capped at 3.003  (Attack_speed)
  crit              = 200% damage; expected multiplier 1 + crit_chance        (Critical_strike)
  armor/MR mitigation = 100 / (100 + R), R >= 0                               (Armor)
  penetration order = % penetration, then flat (lethality is 1:1 flat)        (Armor_penetration)
  cooldown          = base * 100 / (100 + ability_haste)                      (Haste)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from schemas import Ability, Kit

AS_CAP = 3.003
CRIT_MULT = 2.0
MAX_LEVEL = 18


def growth(base: float, g: float, level: int) -> float:
    n = level - 1
    return base + g * n * (0.7025 + 0.0175 * n)


def lerp_level(lo_hi: list[float], level: int) -> float:
    """'X - Y (based on level)' values: linear from level 1 to 18 (SIMPLIFICATIONS.md)."""
    lo, hi = lo_hi[0], lo_hi[-1]
    return lo + (hi - lo) * (level - 1) / (MAX_LEVEL - 1)


def at_rank(v, rank: int) -> float:
    """Scalar or per-rank list -> value at `rank` (1-based). Shorter lists clamp to the last entry."""
    if v is None:
        return 0.0
    if isinstance(v, list):
        return float(v[min(rank, len(v)) - 1])
    return float(v)


# ---------------------------------------------------------------- items + stats

@dataclass(frozen=True)
class ItemStats:
    ad: float = 0
    ap: float = 0
    hp: float = 0
    armor: float = 0
    mr: float = 0
    mp: float = 0
    as_pct: float = 0
    ah: float = 0
    crit_pct: float = 0
    lethality: float = 0
    armor_pen_pct: float = 0
    magic_pen: float = 0
    magic_pen_pct: float = 0
    critical_strike_damage: float = 0   # bonus crit damage % (Infinity Edge)

    @classmethod
    def total(cls, items: list[dict]) -> "ItemStats":
        keys = cls.__dataclass_fields__
        sums = {k: sum(i.get(k, 0) for i in items) for k in keys}
        sums["crit_pct"] = min(sums["crit_pct"], 100)
        return cls(**sums)


@dataclass(frozen=True)
class Stats:
    level: int
    hp: float
    mp: float
    armor: float
    mr: float
    ad: float
    base_ad: float
    ap: float
    attack_speed: float
    attack_range: float
    ah: float
    crit: float          # 0..1
    crit_mult: float     # 2.0 + bonus crit damage
    lethality: float
    armor_pen_pct: float
    magic_pen: float
    magic_pen_pct: float

    @property
    def bonus_ad(self) -> float:
        return self.ad - self.base_ad


def champion_stats(kit: Kit, level: int, items: ItemStats = ItemStats()) -> Stats:
    b = kit.base
    base_ad = growth(b.ad, b.ad_per_lvl, level)
    n = level - 1
    bonus_as = b.as_per_lvl * n * (0.7025 + 0.0175 * n) + items.as_pct
    ratio = kit.as_ratio if kit.as_ratio is not None else b.as_
    return Stats(
        level=level,
        hp=growth(b.hp, b.hp_per_lvl, level) + items.hp,
        mp=growth(b.mp, b.mp_per_lvl, level) + items.mp,
        armor=growth(b.armor, b.armor_per_lvl, level) + items.armor,
        mr=growth(b.mr, b.mr_per_lvl, level) + items.mr,
        ad=base_ad + items.ad,
        base_ad=base_ad,
        ap=items.ap,
        attack_speed=min(AS_CAP, b.as_ + bonus_as / 100 * ratio),
        attack_range=b.range,
        ah=items.ah,
        crit=items.crit_pct / 100,
        crit_mult=CRIT_MULT + items.critical_strike_damage / 100,
        lethality=items.lethality,
        armor_pen_pct=items.armor_pen_pct,
        magic_pen=items.magic_pen,
        magic_pen_pct=items.magic_pen_pct,
    )


@dataclass(frozen=True)
class Target:
    """A reference dummy at a level: no items, never fights back."""
    name: str
    max_hp: float
    armor: float
    mr: float

    @classmethod
    def from_dummy(cls, name: str, d: dict, level: int) -> "Target":
        return cls(name, growth(d["hp"], d["hp_per_lvl"], level),
                   growth(d["armor"], d["armor_per_lvl"], level), growth(d["mr"], d["mr_per_lvl"], level))


def mitigation(resist: float, pen_pct: float, flat_pen: float) -> float:
    effective = max(0.0, resist * (1 - pen_pct / 100) - flat_pen)
    return 100 / (100 + effective)


def mitigate(raw: float, dtype: str, s: Stats, t: Target) -> float:
    if dtype == "physical":
        return raw * mitigation(t.armor, s.armor_pen_pct, s.lethality)
    if dtype == "magic":
        return raw * mitigation(t.mr, s.magic_pen_pct, s.magic_pen)
    return raw  # true damage


# ---------------------------------------------------------------- ranks

def ability_rank(kit: Kit, key: str, level: int) -> int:
    """Rank of an ability at `level` from the kit's max order (lolalytics skill order).

    Levels 1-3 take one point each in primary, secondary, tertiary; R at 6/11/16;
    otherwise the next point goes to the first unmaxed ability in max order, respecting
    rank <= ceil(level / 2). Recasts share their parent's slot.
    """
    slot = (kit.abilities[key].recast_of or key)[0]
    if slot == "P":
        return 1
    if slot == "R":
        return sum(level >= lv for lv in (6, 11, 16))
    order = list(kit.skill_order or "QWE")
    ranks = dict.fromkeys(order, 0)
    for lv in range(1, level + 1):
        if lv in (6, 11, 16):
            continue
        if lv <= 3:
            ranks[order[lv - 1]] += 1
            continue
        for a in order:
            if ranks[a] < 5 and ranks[a] < (lv + 1) // 2:
                ranks[a] += 1
                break
    return ranks[slot]


# ---------------------------------------------------------------- damage

def raw_damage(ab: Ability, rank: int, s: Stats, t_hp: float, t: Target, stacks: int = 0) -> float:
    """Pre-mitigation damage of one hit of `ab` at `rank` against a target at t_hp."""
    if rank <= 0:
        return 0.0
    dmg = at_rank(ab.base, rank)
    if ab.base_by_level:
        dmg += lerp_level(ab.base_by_level, s.level)
    dmg += at_rank(ab.ad_ratio, rank) * s.ad + at_rank(ab.bonus_ad_ratio, rank) * s.bonus_ad
    dmg += at_rank(ab.ap_ratio, rank) * s.ap + at_rank(ab.armor_ratio, rank) * s.armor
    pct = (at_rank(ab.pct_max_hp, rank) * t.max_hp + at_rank(ab.pct_current_hp, rank) * t_hp
           + at_rank(ab.pct_missing_hp, rank) * (t.max_hp - t_hp))
    if ab.min_damage:
        pct = max(pct, at_rank(ab.min_damage, rank))
    dmg += pct
    if stacks > 1 and ab.stack_base:
        extra = (at_rank(ab.stack_base, rank) + at_rank(ab.stack_ad_ratio, rank) * s.ad
                 + at_rank(ab.stack_ap_ratio, rank) * s.ap)
        dmg += extra * (stacks - 1)
    return dmg


def cooldown(ab: Ability, rank: int, s: Stats) -> float:
    return at_rank(ab.cooldown, rank) * 100 / (100 + s.ah) if ab.cooldown else 0.0


def auto_damage(kit: Kit, s: Stats, t_hp: float, t: Target, auto_key: str | None) -> float:
    """One basic attack (or the champion's replacement, e.g. Azir soldier) plus on-hit effects."""
    if auto_key:
        ab = kit.abilities[auto_key]
        dmg = mitigate(raw_damage(ab, ability_rank(kit, auto_key, s.level), s, t_hp, t),
                       ab.damage_type or "magic", s, t)
    else:
        dmg = mitigate(s.ad * (1 + s.crit * (s.crit_mult - 1)), "physical", s, t)
    for key, ab in kit.abilities.items():
        if "on_hit" in ab.tags:
            rank = ability_rank(kit, key, s.level)
            dmg += mitigate(raw_damage(ab, rank, s, t_hp, t), ab.damage_type or "physical", s, t)
    return dmg


@dataclass
class Fight:
    """Running state of one deterministic fight against a dummy."""
    kit: Kit
    s: Stats
    t: Target
    auto_key: str | None = None
    hp: float = 0.0
    stacks: int = 0
    log: list[tuple[str, float]] = field(default_factory=list)

    def __post_init__(self):
        self.hp = self.t.max_hp

    def hit(self, key: str) -> float:
        if key == "AA":
            dmg = auto_damage(self.kit, self.s, self.hp, self.t, self.auto_key)
            self.stacks += 1
        else:
            ab = self.kit.abilities[key]
            rank = ability_rank(self.kit, key, self.s.level)
            hits = int(ab.hits or 1)
            dmg = 0.0
            for _ in range(hits):
                dmg += mitigate(raw_damage(ab, rank, self.s, self.hp - dmg, self.t, self.stacks),
                                ab.damage_type or "physical", self.s, self.t)
            if ab.stack_base:
                self.stacks = 0
            elif dmg > 0:
                self.stacks += 1
        self.hp -= dmg
        self.log.append((key, dmg))
        return dmg
