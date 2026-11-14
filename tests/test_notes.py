"""Notes checker: a correct note passes, and all 8 planted errors (PLAN.md 3.7) are caught."""
import copy

import pytest

from notes.checker import check
from notes.schema import Notes
from schemas import Category, Proposal
from sim.kits import load_kit

KIT = load_kit("Qiyana", "26.22")
PROPOSAL = Proposal(champion="Qiyana", patch="26.22", category=Category.OVERALL_STRONG, rationale="test", changes=[
    {"field": "abilities.Q_edge_of_ixtal.base", "from": [70, 100, 130, 160, 190], "to": [60, 90, 120, 150, 180]},
    {"field": "abilities.Q_edge_of_ixtal.bonus_ad_ratio", "from": 0.9, "to": 0.85},
])
GOOD = {
    "patch_note": {"champion": "Qiyana", "context": "Qiyana's Q is pulling too much weight; we're trimming it.", "lines": [
        {"field": "abilities.Q_edge_of_ixtal.base", "label": "Q - Edge of Ixtal", "from": [70, 100, 130, 160, 190],
         "to": [60, 90, 120, 150, 180], "text": "Base damage reduced: 70/100/130/160/190 → 60/90/120/150/180"},
        {"field": "abilities.Q_edge_of_ixtal.bonus_ad_ratio", "label": "Q - Edge of Ixtal", "from": 0.9, "to": 0.85,
         "text": "Bonus AD ratio reduced: 90% → 85%"},
    ]},
    "tooltips": [{"ability": "Q_edge_of_ixtal",
                  "text": "Deals {base} (+ {bonus_ad_ratio} bonus AD) physical damage. Cooldown: {cooldown} seconds.",
                  "values": {"base": [60, 90, 120, 150, 180], "bonus_ad_ratio": 0.85, "cooldown": [7]}}],
}


def notes(mutate=None) -> Notes:
    d = copy.deepcopy(GOOD)
    if mutate:
        mutate(d)
    return Notes.model_validate(d)


def test_correct_note_passes():
    assert check(notes(), PROPOSAL, KIT) == []


def _line(d, i=0):
    return d["patch_note"]["lines"][i]


PLANTED = {
    "wrong number": lambda d: _line(d).update(text="Base damage reduced: 70/100/130/160/190 → 60/90/125/150/180"),
    "swapped from/to": lambda d: _line(d).update({"from": [60, 90, 120, 150, 180], "to": [70, 100, 130, 160, 190]}),
    "missing changed field": lambda d: d["patch_note"]["lines"].pop(1),
    "extra line for unchanged field": lambda d: d["patch_note"]["lines"].append(
        {"field": "abilities.Q_edge_of_ixtal.cooldown", "label": "Q", "from": [7], "to": [7], "text": "Cooldown 7 → 7"}),
    "'increased' on a decrease": lambda d: _line(d, 1).update(text="Bonus AD ratio increased: 90% → 85%"),
    "stale tooltip value": lambda d: d["tooltips"][0]["values"].update(bonus_ad_ratio=0.9),
    "per-rank array off by one rank": lambda d: d["tooltips"][0]["values"].update(base=[60, 90, 120, 150, 190]),
    "hardcoded number in tooltip": lambda d: d["tooltips"][0].update(
        text="Deals {base} (+ {bonus_ad_ratio} bonus AD) physical damage, 160% against monsters. Cooldown: {cooldown} seconds."),
}


@pytest.mark.parametrize("name", PLANTED)
def test_planted_error_caught(name):
    errs = check(notes(PLANTED[name]), PROPOSAL, KIT)
    assert errs, f"planted error not caught: {name}"


def test_all_eight_caught():
    caught = sum(bool(check(notes(m), PROPOSAL, KIT)) for m in PLANTED.values())
    assert caught == len(PLANTED) == 8
