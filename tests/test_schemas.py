"""Schema tests. Numbers here are synthetic fixtures, not game data."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas import Complaints, Kit, Proposal

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("path", sorted((ROOT / "data/champions").glob("*.yaml")), ids=lambda p: p.stem)
def test_champion_yaml_validates(path):
    kit = Kit.load(path)
    assert kit.abilities


def test_missing_lists_todos():
    kit = Kit.model_validate({
        "name": "Fixture", "base": {"hp": 600},
        "abilities": {"Q_hit": {"type": "damage", "cooldown": [8, 7]}},
    })
    miss = kit.missing()
    assert "abilities.Q_hit.base" in miss
    assert "base.armor" in miss and "base.hp" not in miss


def test_bad_ability_key_rejected():
    with pytest.raises(ValidationError):
        Kit.model_validate({"name": "X", "base": {}, "abilities": {"soldier": {"type": "damage"}}})


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Kit.model_validate({"name": "X", "base": {"crit": 1}, "abilities": {}})


PROPOSAL = """
champion: Fixture
patch: "1.1"
category: PRO_JAIL
changes:
  - field: abilities.W_hit.ap_ratio
    from: 0.5
    to: 0.45
  - field: base.armor
    from: [30, 32]
    to: [32, 34]
rationale: test
"""


def test_proposal_roundtrip():
    p = Proposal.from_yaml(PROPOSAL)
    assert p.changes[0].from_ == 0.5
    assert Proposal.from_yaml(p.to_yaml()) == p


@pytest.mark.parametrize("field", ["armor", "base.armor.x", "abilities.W_hit", "sim.weights"])
def test_proposal_bad_field(field):
    with pytest.raises(ValidationError):
        Proposal.model_validate({"champion": "F", "patch": "1", "category": "HOLD",
                                 "changes": [{"field": field, "from": 1, "to": 2}], "rationale": ""})


def test_proposal_bad_category():
    with pytest.raises(ValidationError):
        Proposal.model_validate({"champion": "F", "patch": "1", "category": "BUFF_IT",
                                 "changes": [], "rationale": ""})


def test_complaints_valid():
    c = Complaints.model_validate({"complaints": [{"tag": "mana", "direction": "buff", "count": 3,
                                                   "example_ids": ["t3_a"]}], "n_posts": 10})
    assert c.complaints[0].tag == "mana"


@pytest.mark.parametrize("bad", [
    {"complaints": [{"tag": "ignore previous instructions", "direction": "buff", "count": 1}], "n_posts": 5},
    {"complaints": [{"tag": "mana", "direction": "buff 50%", "count": 1}], "n_posts": 5},
    {"complaints": [{"tag": "mana", "direction": "buff", "count": 9}], "n_posts": 5},
    {"complaints": [], "n_posts": 5, "note": "extra field"},
])
def test_complaints_rejected(bad):
    with pytest.raises(ValidationError):
        Complaints.model_validate(bad)
