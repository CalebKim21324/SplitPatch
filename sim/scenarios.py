"""Visible scenarios (PLAN.md 3.2). Each returns one number per champion. Deterministic.

  lane_trade_l6       damage of the standard trade, lvl 6, 1 item, vs mage dummy          (solo queue)
  duel_ttk_l9         seconds to kill the bruiser dummy, lvl 9, 2 items (lower = stronger)  (solo queue)
  mana_casts_to_oom   trades before running out of mana, lvl 6 (manaless/energy = cap)      (solo queue)
  late_dps_l16        damage per second over 10 s, lvl 16, 4 items, vs tank dummy          (pro)
  siege_score         threat range x late DPS / 1000                                         (pro)
  utility_cc_per_10s  CC seconds per 10 s at lvl 16 + slow value + disengage bonus           (pro)
  scaling_ratio       late DPS / early DPS (lvl 6, 1 item, same tank dummy)                  (pro)
"""
from __future__ import annotations

from schemas import Kit
from sim import kits
from sim.engine import Fight, Stats, Target, ability_rank, at_rank, champion_stats, cooldown, raw_damage

DT = 0.05
MAX_TTK = 60.0
MANALESS_CAP = 10        # trades before oom for manaless / energy champions
DISENGAGE_BONUS = 1.0
SLOW_WEIGHT = 0.5        # a slow second counts as half a CC second
EXECUTE_HP = 0.40
STACK_CAST = 5

SOLOQ_METRICS = ["lane_trade_l6", "duel_ttk_l9", "mana_casts_to_oom"]
PRO_METRICS = ["late_dps_l16", "siege_score", "utility_cc_per_10s", "scaling_ratio"]
LOWER_IS_BETTER = {"duel_ttk_l9"}


class Setup:
    """Champion at a level with n items, against a dummy."""

    def __init__(self, kit: Kit, champ: str, level: int, n_items: int, dummy: str, override=None):
        self.kit, self.champ = kit, champ
        items = kits.build_stats(champ, n_items, override)
        bonus_as = sum(_uptime(ab) * at_rank(ab.bonus_as, ability_rank(kit, k, level)) * 100
                       for k, ab in kit.abilities.items() if ab.bonus_as and not k.startswith("P_"))
        items = items.__class__(**{**items.__dict__, "as_pct": items.as_pct + bonus_as})
        self.s: Stats = champion_stats(kit, level, items)
        self.t = Target.from_dummy(dummy, kits.dummies()[dummy], level)
        self.auto = kits.combo(champ).get("auto")

    def fight(self) -> Fight:
        return Fight(self.kit, self.s, self.t, self.auto)


def _uptime(ab) -> float:
    """Average uptime of a timed buff (duration / cooldown); passives count fully."""
    if not ab.duration or not ab.cooldown:
        return 1.0
    return min(1.0, ab.duration / min(ab.cooldown))


def _rotation(kit: Kit) -> list[str]:
    skip = lambda ab: ab.recast_of or "on_hit" in ab.tags
    has_damage = lambda ab: any(v is not None for v in (ab.base, ab.base_by_level, ab.ad_ratio,
                                                         ab.bonus_ad_ratio, ab.pct_max_hp, ab.pct_missing_hp))
    return [k for k, ab in kit.abilities.items() if not skip(ab) and has_damage(ab)]


def _recasts(kit: Kit, parent: str) -> list[str]:
    return [k for k, ab in kit.abilities.items() if ab.recast_of == parent and "on_hit" not in ab.tags]


def sustained(setup: Setup, duration: float | None) -> tuple[float, float]:
    """Simulate autos + rotation. Returns (damage dealt, time). duration=None -> fight to the death."""
    f, kit, s = setup.fight(), setup.kit, setup.s
    ready = {k: 0.0 for k in _rotation(kit)}
    used_once: set[str] = set()
    next_auto, t, total = 0.0, 0.0, 0.0
    limit = duration if duration is not None else MAX_TTK
    while t < limit and (duration is not None or f.hp > 0):
        for key in ready:
            ab = kit.abilities[key]
            rank = ability_rank(kit, key, s.level)
            if rank <= 0 or ready[key] > t or (not ab.cooldown and key in used_once):
                continue
            kill = raw_damage(ab, rank, s, f.hp, f.t, f.stacks) >= f.hp
            if ab.stack_base and f.stacks < STACK_CAST and not kill:
                continue
            if "execute" in ab.tags and not ab.stack_base and f.hp > EXECUTE_HP * f.t.max_hp and not kill:
                continue
            total += f.hit(key)
            for rc in _recasts(kit, key):
                if ability_rank(kit, rc, s.level) > 0 and raw_damage(kit.abilities[rc], rank, s, f.hp, f.t) > 0:
                    total += f.hit(rc)
            used_once.add(key)
            ready[key] = t + cooldown(ab, rank, s) if ab.cooldown else float("inf")
        if t >= next_auto:
            total += f.hit("AA")
            next_auto = t + 1 / s.attack_speed
        if duration is None and f.hp <= 0:
            return total, t
        t += DT
    return total, t


# ---------------------------------------------------------------- metrics

def lane_trade_l6(kit, champ, override=None) -> float:
    f = Setup(kit, champ, 6, 1, "mage", override).fight()
    return sum(f.hit(a) for a in kits.combo(champ)["trade"])


def duel_ttk_l9(kit, champ, override=None) -> float:
    return sustained(Setup(kit, champ, 9, 2, "bruiser", override), None)[1]


def mana_casts_to_oom(kit, champ, override=None) -> float:
    if kit.resource in ("none", "energy") or kit.base.mp == 0:
        return float(MANALESS_CAP)
    st = Setup(kit, champ, 6, 1, "mage", override)
    cost = sum(at_rank(kit.abilities[a].mana_cost, ability_rank(kit, a, 6))
               for a in kits.combo(champ)["trade"] if a != "AA")
    return float(min(MANALESS_CAP, st.s.mp / cost)) if cost else float(MANALESS_CAP)


def late_dps_l16(kit, champ, override=None) -> float:
    return sustained(Setup(kit, champ, 16, 4, "tank", override), 10.0)[0] / 10.0


def early_dps_l6(kit, champ, override=None) -> float:
    return sustained(Setup(kit, champ, 6, 1, "tank", override), 10.0)[0] / 10.0


def siege_score(kit, champ, override=None) -> float:
    ranges = [ab.range for ab in kit.abilities.values() if ab.range and ab.type in ("damage", "cc")]
    threat = max([kit.base.range, *[r for r in ranges if r <= 1500]])
    return threat * late_dps_l16(kit, champ, override) / 1000


def utility_cc_per_10s(kit, champ, override=None) -> float:
    s = Setup(kit, champ, 16, 4, "tank", override).s
    score = 0.0
    for key, ab in kit.abilities.items():
        rank = ability_rank(kit, key, 16)
        cd = cooldown(ab, rank, s) or (cooldown(kit.abilities[ab.recast_of], rank, s) if ab.recast_of else 0)
        if rank <= 0 or cd <= 0:
            continue
        score += at_rank(ab.cc_duration, rank) / cd * 10
        score += SLOW_WEIGHT * at_rank(ab.slow, rank) * (ab.slow_duration or 0) / cd * 10
    if any("disengage" in ab.tags for ab in kit.abilities.values()):
        score += DISENGAGE_BONUS
    return score


def scaling_ratio(kit, champ, override=None) -> float:
    early = early_dps_l6(kit, champ, override)
    return late_dps_l16(kit, champ, override) / early if early else 0.0


METRICS = {
    "lane_trade_l6": lane_trade_l6, "duel_ttk_l9": duel_ttk_l9, "mana_casts_to_oom": mana_casts_to_oom,
    "late_dps_l16": late_dps_l16, "siege_score": siege_score,
    "utility_cc_per_10s": utility_cc_per_10s, "scaling_ratio": scaling_ratio,
}


def run_all(kit: Kit, champ: str, override=None) -> dict[str, float]:
    return {name: round(fn(kit, champ, override), 4) for name, fn in METRICS.items()}
