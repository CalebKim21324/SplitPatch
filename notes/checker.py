"""Deterministic patch-note + tooltip checker (PLAN.md 3.7). No LLM.

  1. coverage    every changed field has exactly one line; no lines for unchanged fields
  2. values      each line's from/to equals the diff exactly (per-rank arrays included)
  3. text        the numbers in each line's text are exactly from... then to... in order
                 (ratios may be written as percentages: 0.9 -> 90)
  4. tooltips    every changed ability has a tooltip; every {placeholder} resolves to the PATCHED kit
                 value; each changed field appears as a placeholder; no hardcoded numbers
  5. direction   "increased/reduced/buff/nerf" wording agrees with the sign of each change
"""
from __future__ import annotations

import re

from notes.schema import Notes
from notes.templates import PCT_FIELDS
from schemas import Kit, Proposal
from sim.patching import apply, get_field

NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
PLACEHOLDER = re.compile(r"\{(\w+)\}")
UP = re.compile(r"\b(increas\w*|rais\w*|higher|more)\b", re.I)
DOWN = re.compile(r"\b(decreas\w*|reduc\w*|lower\w*|less)\b", re.I)
BUFF = re.compile(r"\bbuff\w*\b", re.I)
NERF = re.compile(r"\bnerf\w*\b", re.I)
LOWER_IS_BETTER = {"cooldown", "mana_cost"}


def _els(v) -> list[float]:
    return [float(x) for x in v] if isinstance(v, list) else [float(v)]


def _same(a, b) -> bool:
    return _els(a) == _els(b)


def _num_ok(token: float, value: float, field: str) -> bool:
    if abs(token - value) < 1e-6:
        return True
    return field.split(".")[-1] in PCT_FIELDS and abs(token - round(value * 100, 4)) < 1e-6


def _mean(v) -> float:
    e = _els(v)
    return sum(e) / len(e)


def check(notes: Notes, proposal: Proposal, kit: Kit) -> list[str]:
    errs: list[str] = []
    diff = {c.field: c for c in proposal.changes}
    lines = notes.patch_note.lines

    # 1. coverage
    seen = [l.field for l in lines]
    for f in diff:
        n = seen.count(f)
        if n != 1:
            errs.append(f"coverage: {f} has {n} lines (need exactly 1)")
    for f in set(seen) - set(diff):
        errs.append(f"coverage: line for unchanged field {f}")
    if notes.patch_note.champion != proposal.champion:
        errs.append(f"coverage: note is for {notes.patch_note.champion}, diff is for {proposal.champion}")

    for l in lines:
        ch = diff.get(l.field)
        if ch is None:
            continue
        # 2. values
        if not _same(l.from_, ch.from_) or not _same(l.to, ch.to):
            errs.append(f"values: {l.field} line says {l.from_} -> {l.to}, diff is {ch.from_} -> {ch.to}")
            continue
        # 3. text numbers, in order: from..., to...
        tokens = [float(t) for t in NUM.findall(l.text)]
        want = _els(ch.from_) + _els(ch.to)
        if len(tokens) != len(want) or not all(_num_ok(t, w, l.field) for t, w in zip(tokens, want)):
            errs.append(f"text: {l.field} text numbers {tokens} don't match from {ch.from_} then to {ch.to}")
        # 5. direction words
        up = _mean(ch.to) > _mean(ch.from_)
        good = up != (l.field.split(".")[-1] in LOWER_IS_BETTER)
        if UP.search(l.text) and not up:
            errs.append(f"direction: {l.field} says increased but the value went down")
        if DOWN.search(l.text) and up:
            errs.append(f"direction: {l.field} says reduced but the value went up")
        if BUFF.search(l.text) and not good:
            errs.append(f"direction: {l.field} calls a nerf a buff")
        if NERF.search(l.text) and good:
            errs.append(f"direction: {l.field} calls a buff a nerf")

    # 4. tooltips against the PATCHED kit
    patched = apply(kit, proposal)
    changed_abilities = {f.split(".")[1]: [] for f in diff if f.startswith("abilities.")}
    for f in diff:
        if f.startswith("abilities."):
            changed_abilities[f.split(".")[1]].append(f.split(".")[2])
    tips = {t.ability: t for t in notes.tooltips}
    for ab in changed_abilities:
        if ab not in tips:
            errs.append(f"tooltip: no tooltip for changed ability {ab}")
    for t in notes.tooltips:
        if t.ability not in patched.abilities:
            errs.append(f"tooltip: unknown ability {t.ability}")
            continue
        names = PLACEHOLDER.findall(t.text)
        for n in names:
            if n not in t.values:
                errs.append(f"tooltip: {t.ability} placeholder {{{n}}} has no value")
                continue
            actual = get_field(patched, f"abilities.{t.ability}.{n}")
            if actual is None or not _same(t.values[n], actual):
                errs.append(f"tooltip: {t.ability} {{{n}}} = {t.values[n]}, patched kit has {actual}")
        for fld in changed_abilities.get(t.ability, []):
            if fld not in names:
                errs.append(f"tooltip: {t.ability} doesn't show changed field {{{fld}}}")
        hard = NUM.findall(PLACEHOLDER.sub("", t.text))
        if hard:
            errs.append(f"tooltip: {t.ability} has hardcoded numbers {hard}; use placeholders")
    return errs
