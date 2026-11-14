"""Kit DSL: base stats + abilities for one champion (PLAN.md 3.1).

Numbers are hand-checked from Data Dragon (base stats) and the wiki (abilities).
A value of `None` means "not entered yet" (leave a `# TODO` in the YAML).
`Kit.missing()` lists every None so nothing silently defaults to zero.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

Num = float | None
PerRank = list[float] | None
Ratio = float | list[float] | None  # scalar, or per rank

ABILITY_KEY = re.compile(r"^(P|Q|W|E|R)_[a-z0-9_]+$")
AbilityType = Literal["damage", "cc", "buff", "utility", "mobility"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class BaseStats(Strict):
    """Level-1 values plus per-level growth (Data Dragon champion.json names in comments)."""

    hp: Num = None                 # hp
    hp_per_lvl: Num = None         # hpperlevel
    mp: Num = None                 # mp (0 for manaless)
    mp_per_lvl: Num = None         # mpperlevel
    armor: Num = None              # armor
    armor_per_lvl: Num = None      # armorperlevel
    mr: Num = None                 # spellblock
    mr_per_lvl: Num = None         # spellblockperlevel
    ad: Num = None                 # attackdamage
    ad_per_lvl: Num = None         # attackdamageperlevel
    as_: Num = Field(default=None, alias="as")  # attackspeed
    as_per_lvl: Num = None         # attackspeedperlevel (percent)
    ms: Num = None                 # movespeed
    range: Num = None              # attackrange


class Ability(Strict):
    """All ratios and percentages are fractions (35% AP -> 0.35). Lists are per rank."""

    type: AbilityType
    damage_type: Literal["physical", "magic", "true"] | None = None
    base: PerRank = None           # damage per rank
    base_by_level: PerRank = None  # [lvl1, lvl18] flat bonus "based on level", added to base
    ap_ratio: Ratio = None
    ad_ratio: Ratio = None         # total AD ratio
    bonus_ad_ratio: Ratio = None
    pct_max_hp: PerRank = None     # of target's maximum health
    pct_current_hp: PerRank = None
    pct_missing_hp: PerRank = None
    min_damage: PerRank = None     # floor for %-health damage
    stack_base: PerRank = None     # per extra stack (e.g. each extra Rend spear)
    stack_ad_ratio: Ratio = None
    stack_ap_ratio: Ratio = None
    shield: PerRank = None
    shield_ap_ratio: Ratio = None
    shield_bonus_hp_ratio: Ratio = None
    damage_reduction: PerRank = None
    duration: Num = None           # buff / shield / damage-reduction duration (s)
    bonus_as: PerRank = None
    bonus_ms: Ratio = None
    slow: Ratio = None
    slow_duration: Num = None
    cc_duration: Ratio = None      # stun / knock-up / silence seconds, scalar or per rank
    cooldown: PerRank = None
    mana_cost: PerRank = None
    range: Num = None
    hits: Num = None               # hits per cast in the standard combo (see SIMPLIFICATIONS.md)
    tags: list[str] = []
    notes: str | None = None       # free text, never read by the sim

    @field_validator("base", "base_by_level", "cooldown", "mana_cost", "pct_max_hp", "pct_current_hp",
                     "pct_missing_hp", "min_damage", "stack_base", "shield", "damage_reduction", "bonus_as")
    @classmethod
    def _non_empty(cls, v: PerRank) -> PerRank:
        if v is not None and len(v) == 0:
            raise ValueError("per-rank list must not be empty; use null for unknown")
        return v


class Kit(Strict):
    name: str
    patch: str | None = None       # patch these numbers are valid for
    base: BaseStats
    abilities: dict[str, Ability]

    @field_validator("abilities")
    @classmethod
    def _keys(cls, v: dict[str, Ability]) -> dict[str, Ability]:
        for k in v:
            if not ABILITY_KEY.match(k):
                raise ValueError(f"ability key {k!r} must look like 'W_soldier_attack'")
        return v

    def missing(self) -> list[str]:
        """Dotted paths of fields still None (only fields relevant to the ability type count)."""
        out = [f"base.{k}" for k, v in self.base.model_dump().items() if v is None]
        for key, ab in self.abilities.items():
            want = set() if key.startswith("P_") else {"cooldown"}
            if ab.type == "damage" and not (ab.pct_current_hp or ab.pct_missing_hp or ab.ad_ratio):
                want |= {"base"}
            if ab.type == "cc":
                want |= {"cc_duration"}
            out += [f"abilities.{key}.{f}" for f in sorted(want) if getattr(ab, f) is None]
        return out

    @classmethod
    def load(cls, path: str | Path) -> "Kit":
        return cls.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
