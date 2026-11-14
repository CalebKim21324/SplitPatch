"""Patch-note + tooltip writer (PLAN.md 3.7): one structured-output LLM call per verified proposal,
retried with the checker's errors up to 3 times. After that, deterministic lines without prose,
flagged for a human.
"""
from __future__ import annotations

import json

from agent import llm
from notes.checker import check
from notes.schema import JSON_SCHEMA, Line, Notes, PatchNote, Tooltip, from_json
from notes.templates import PCT_FIELDS, placeholders, template
from schemas import Kit, Proposal
from sim.patching import apply

MAX_TRIES = 3

SYSTEM = """You write League of Legends patch notes and ability tooltips for a balance team.

Output JSON only, in the given schema. Rules a checker will enforce:
- One line per changed field, no lines for anything else. Copy each line's `field`, `from`, `to`
  exactly from the diff.
- Each line's `text` names the stat, then the old value(s), an arrow, the new value(s). The only numbers
  in `text` are the old values then the new values, in that order. Write per-rank values as
  70/100/130/160/190. Ratios (fields named *ratio*, slow, pct_*) may be written as percentages (0.9 -> 90%).
  No other digits: no patch numbers, no ability ranks, no levels.
- Use "increased"/"reduced" only when it matches the direction of the number. "Buff"/"nerf" must match
  the effect for the player (a lower cooldown or cost is a buff).
- `context`: one sentence of designer intent in Riot's patch-note voice, grounded in the rationale.
- Tooltips: one per changed ability. Rewrite the given template into natural tooltip prose but keep every
  number as a {placeholder}; never write a literal digit. Every changed field must appear as a placeholder.
  `values` lists each placeholder's value from the PATCHED kit."""


def _fmt_pct(field: str) -> bool:
    return field.split(".")[-1] in PCT_FIELDS


def fallback(proposal: Proposal, kit: Kit) -> Notes:
    """Deterministic notes: structured lines + template tooltips, no prose (flag for a human)."""
    def show(field, v):
        vals = v if isinstance(v, list) else [v]
        return "/".join(f"{x * 100:g}%" if _fmt_pct(field) else f"{x:g}" for x in vals)

    lines = [Line(field=c.field, label=c.field.split(".")[-2] if c.field.startswith("abilities.") else "Base stats",
                  from_=c.from_, to=c.to, text=f"{c.field.split('.')[-1]}: {show(c.field, c.from_)} → {show(c.field, c.to)}")
             for c in proposal.changes]
    patched = apply(kit, proposal)
    tips = []
    for ab in sorted({c.field.split(".")[1] for c in proposal.changes if c.field.startswith("abilities.")}):
        a = patched.abilities[ab]
        tips.append(Tooltip(ability=ab, text=template(ab, a), values=placeholders(ab, a)))
    return Notes(patch_note=PatchNote(champion=proposal.champion, context="[needs designer review]", lines=lines),
                 tooltips=tips)


def write(proposal: Proposal, kit: Kit, log: list | None = None) -> tuple[Notes, bool, list[str]]:
    """Returns (notes, passed_checker, errors_of_last_attempt). Appends each attempt to `log`."""
    patched = apply(kit, proposal)
    changed = sorted({c.field.split(".")[1] for c in proposal.changes if c.field.startswith("abilities.")})
    brief = {
        "champion": proposal.champion, "patch": proposal.patch, "category": proposal.category.value,
        "rationale": proposal.rationale,
        "diff": [c.model_dump(by_alias=True) for c in proposal.changes],
        "tooltip_templates": {ab: template(ab, patched.abilities[ab]) for ab in changed},
        "patched_values": {ab: placeholders(ab, patched.abilities[ab]) for ab in changed},
    }
    user = "Write the patch notes and tooltips for this verified change.\n" + json.dumps(brief, indent=1)
    errors: list[str] = []
    for attempt in range(1, MAX_TRIES + 1):
        prompt = user if not errors else (
            user + "\n\nYour previous attempt failed these checks. Fix every one:\n- " + "\n- ".join(errors))
        try:
            notes = from_json(llm.json_call(system=SYSTEM, user=prompt, schema=JSON_SCHEMA, effort="medium"))
        except Exception as e:  # malformed output or API failure counts as a failed attempt
            errors = [f"writer error: {type(e).__name__}: {e}"]
            if log is not None:
                log.append({"attempt": attempt, "errors": errors})
            continue
        errors = check(notes, proposal, kit)
        if log is not None:
            log.append({"attempt": attempt, "notes": notes.model_dump(by_alias=True), "errors": errors})
        if not errors:
            return notes, True, []
    fb = fallback(proposal, kit)
    return fb, not check(fb, proposal, kit), errors
