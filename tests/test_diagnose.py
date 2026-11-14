"""Diagnoser rule tests. Stats here are synthetic fixtures, not real champion data."""
import pytest

from agent.diagnose import diagnose
from schemas import Category, Complaints, ProRow, SoloQRow


def rows(wr, br, presence, pr=2):
    return (SoloQRow(patch="1.1", champion="F", wr=wr, pr=pr, br=br, games=1000),
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


@pytest.mark.parametrize("wr,pr,cat", [
    (49.0, 8, Category.POPULAR_WEAK),
    (49.0, 3, Category.HOLD),          # weak-ish but unpopular
    (47.0, 8, Category.OVERALL_WEAK),  # very weak wins over popular
    (50.0, 8, Category.HOLD),
])
def test_popular_weak(wr, pr, cat):
    assert diagnose(*rows(wr, 5, 15, pr=pr)).category == cat


def test_pro_jail_target_bands():
    d = diagnose(*rows(47, 5, 60))
    # bands recalibrated to the sim's scale (see TARGETS in agent/diagnose.py)
    assert d.target.pro_index.contains(-0.015) and not d.target.pro_index.contains(-0.002)
    assert d.target.soloq_index.contains(0.05) and not d.target.soloq_index.contains(-0.01)


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
