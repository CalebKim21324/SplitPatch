"""Baselines (PLAN.md 4), compared with SplitPatch on the same rows.

  rule:     global WR > 52.5% -> nerf base damage 5%; < 48% -> buff 5%; else hold
  one-shot: one LLM call with the same stats and kit, no simulator, no verifier, no retries
"""
from __future__ import annotations

import json

from agent import llm
from schemas import Kit

LEVERS = ["damage", "defense", "mana", "cooldown", "utility"]


def lever_of(field: str) -> str:
    f = field.split(".")[-1]
    if f in ("cooldown",):
        return "cooldown"
    if f in ("mana_cost", "mp", "mp_per_lvl"):
        return "mana"
    if f in ("hp", "hp_per_lvl", "armor", "armor_per_lvl", "mr", "mr_per_lvl", "shield", "shield_ap_ratio",
             "shield_bonus_hp_ratio", "damage_reduction"):
        return "defense"
    if f in ("cc_duration", "slow", "range", "ms", "bonus_ms"):
        return "utility"
    return "damage"


def rule_baseline(stats: dict) -> dict:
    wr = stats["solo_queue"]["global"]["wr"]
    if wr > 52.5:
        return {"direction": "nerf", "lever": "damage"}
    if wr < 48:
        return {"direction": "buff", "lever": "damage"}
    return {"direction": "hold", "lever": None}


ONE_SHOT_SYSTEM = """You are a League of Legends balance designer. Given one champion's solo queue stats
(global and Korea, Emerald+), pro presence and current kit numbers, decide whether to buff, nerf or hold
this champion next patch. If you change something, propose at most 3 field changes, each within 20% of
the current value, copying `from` exactly from the kit. Field paths look like base.ad or
abilities.<ability_key>.<field>; scalars are 1-item lists."""

ONE_SHOT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["direction", "lever", "changes", "rationale"],
    "properties": {
        "direction": {"type": "string", "enum": ["buff", "nerf", "hold"]},
        "lever": {"type": "string", "enum": LEVERS + ["none"]},
        "rationale": {"type": "string"},
        "changes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["field", "from", "to"],
            "properties": {"field": {"type": "string"},
                           "from": {"type": "array", "items": {"type": "number"}},
                           "to": {"type": "array", "items": {"type": "number"}}}}},
    },
}


def one_shot(kit: Kit, stats: dict) -> dict:
    user = json.dumps({"champion": kit.name, "patch": kit.patch, "stats": stats,
                       "kit": kit.model_dump(by_alias=True, exclude_none=True)}, default=float)
    return llm.json_call(system=ONE_SHOT_SYSTEM, user=user, schema=ONE_SHOT_SCHEMA, effort="medium")
