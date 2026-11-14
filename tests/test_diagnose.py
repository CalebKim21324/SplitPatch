"""Diagnoser rule tests. Stats here are synthetic fixtures, not real champion data."""
import pytest

from agent.diagnose import diagnose
from schemas import Category, Complaints, ProRow, SoloQRow


def rows(wr, br, presence):
    return (SoloQRow(patch="1.1", champion="F", wr=wr, pr=5, br=br, games=1000),
            ProRow(patch="1.1", champion="F", presence=presence, picks=1, bans=1, wr=50, games=10))


@pytest.mark.parametrize("wr,br,pres,cat", [
    (47.0, 5, 60, Category.PRO_JAIL),
    (53.0, 5, 40, Category.OVERALL_STRONG),
    (53.0, 30, 15, Category.OVERALL_STRONG),     # BR high, presence mid
    (53.0, 5, 2, Category.SOLOQ_ONLY_STRONG),
    (47.0, 5, 2, Category.OVERALL_WEAK),
    (50.0, 5, 15, Category.HOLD),
    (49.5, 5, 60, Category.HOLD),                # high presence but WR not low enough
])
def test_categories(wr, br, pres, cat):
    assert diagnose(*rows(wr, br, pres)).category == cat


def test_pro_jail_target_bands():
    d = diagnose(*rows(47, 5, 60))
    assert d.target.pro_index.contains(-0.10) and not d.target.pro_index.contains(-0.02)
    assert d.target.soloq_index.contains(0.05) and not d.target.soloq_index.contains(-0.02)


def test_buff_requests_ignored_when_strong():
    c = Complaints.model_validate({"n_posts": 50, "complaints": [
        {"tag": "mana", "direction": "buff", "count": 40},
        {"tag": "damage", "direction": "nerf", "count": 5},
    ]})
    assert diagnose(*rows(53, 5, 2), c).lever_hints == ["damage"]
    assert diagnose(*rows(47, 5, 2), c).lever_hints == ["mana"]


def test_mismatched_rows_rejected():
    s, p = rows(50, 5, 15)
    with pytest.raises(ValueError):
        diagnose(s, p.model_copy(update={"patch": "1.2"}))
