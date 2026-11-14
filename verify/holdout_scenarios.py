"""Hidden scenarios the agent never sees (PLAN.md 3.6 step 5).

They catch patches tuned only to the visible metrics: a change that lands the visible indices in
band but swings an unseen fight a lot, or in the wrong direction, fails.
"""
from __future__ import annotations

from schemas import Kit
from sim import kits
from sim.scenarios import Setup, sustained

MAX_SWING = 0.15          # no hidden scenario may move more than 15%
WRONG_WAY_TOLERANCE = 0.02  # a nerf may not make a hidden scenario >2% stronger (and vice versa)


def tank_duel_l13(kit: Kit, champ: str) -> float:
    """Damage dealt to the tank dummy in 6 s, level 13, 3 items (higher = stronger)."""
    return sustained(Setup(kit, champ, 13, 3, "tank"), 6.0)[0]


def skirmish_burst_l11(kit: Kit, champ: str) -> float:
    """The trade combo at level 11, 2 items, vs the bruiser dummy (higher = stronger)."""
    f = Setup(kit, champ, 11, 2, "bruiser").fight()
    return sum(f.hit(a) for a in kits.combo(champ)["trade"])


HOLDOUT = {"tank_duel_l13": tank_duel_l13, "skirmish_burst_l11": skirmish_burst_l11}


def run(kit: Kit, champ: str) -> dict[str, float]:
    return {k: fn(kit, champ) for k, fn in HOLDOUT.items()}
