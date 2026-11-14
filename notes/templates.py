"""Tooltip templates, generated from the kit so every number is a {placeholder} bound to a kit field.

A template never contains a literal number: each value appears as {field} and the checker resolves
it against the patched kit, so a tooltip can't drift from the data.
"""
from __future__ import annotations

from schemas import Ability, Kit

PCT_FIELDS = {"ap_ratio", "ad_ratio", "bonus_ad_ratio", "pct_max_hp", "pct_current_hp", "pct_missing_hp",
              "stack_ad_ratio", "stack_ap_ratio", "shield_ap_ratio", "shield_bonus_hp_ratio",
              "damage_reduction", "bonus_as", "bonus_ms", "slow"}

_PHRASES = [
    ("base", "{base}"), ("base_by_level", "(+ {base_by_level} based on level)"),
    ("ad_ratio", "(+ {ad_ratio} AD)"), ("bonus_ad_ratio", "(+ {bonus_ad_ratio} bonus AD)"),
    ("ap_ratio", "(+ {ap_ratio} AP)"), ("pct_max_hp", "(+ {pct_max_hp} of the target's maximum health)"),
    ("pct_current_hp", "(+ {pct_current_hp} of the target's current health)"),
    ("pct_missing_hp", "(+ {pct_missing_hp} of the target's missing health)"),
]


def template(key: str, ab: Ability) -> str:
    """A plain, generic tooltip: damage formula, then other effects, then cooldown and cost."""
    parts = []
    dmg = " ".join(p for f, p in _PHRASES if getattr(ab, f) is not None)
    if dmg:
        parts.append(f"Deals {dmg} {ab.damage_type or 'physical'} damage.")
    if ab.stack_base is not None:
        parts.append("Each additional stack adds {stack_base}"
                     + (" (+ {stack_ad_ratio} AD)" if ab.stack_ad_ratio is not None else "")
                     + (" (+ {stack_ap_ratio} AP)" if ab.stack_ap_ratio is not None else "") + ".")
    if ab.shield is not None:
        parts.append("Grants a {shield}"
                     + (" (+ {shield_ap_ratio} AP)" if ab.shield_ap_ratio is not None else "")
                     + (" (+ {shield_bonus_hp_ratio} bonus health)" if ab.shield_bonus_hp_ratio is not None else "")
                     + " shield.")
    if ab.damage_reduction is not None:
        parts.append("Reduces incoming damage by {damage_reduction}.")
    if ab.slow is not None:
        parts.append("Slows by {slow}" + (" for {slow_duration} seconds" if ab.slow_duration else "") + ".")
    if ab.cc_duration is not None:
        parts.append("Crowd control lasts {cc_duration} seconds.")
    if ab.bonus_as is not None:
        parts.append("Grants {bonus_as} bonus attack speed.")
    if ab.cooldown is not None:
        parts.append("Cooldown: {cooldown} seconds.")
    if ab.mana_cost is not None:
        parts.append("Cost: {mana_cost}.")
    return " ".join(parts)


def placeholders(key: str, ab: Ability) -> dict:
    """Field name -> current value for every placeholder the template uses."""
    import re
    names = set(re.findall(r"\{(\w+)\}", template(key, ab)))
    return {n: getattr(ab, n) for n in sorted(names)}


def all_templates(kit: Kit) -> dict[str, str]:
    return {k: template(k, ab) for k, ab in kit.abilities.items()}
