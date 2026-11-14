"""Sim tests. The hand calculations are written out from wiki numbers, NOT via engine functions."""
import pytest

from sim import kits
from sim.engine import Fight, Target, ability_rank, champion_stats, growth
from sim.indices import delta, evaluate
from sim.scenarios import Setup, run_all


def test_growth_matches_wiki_example():
    # wiki Champion_statistic: Alistar 685 hp + 120 growth at level 2 -> 771.4
    assert growth(685, 120, 2) == pytest.approx(771.4)
    assert growth(100, 10, 18) == pytest.approx(100 + 10 * 17)  # full growth by 18


@pytest.mark.parametrize("champ,key,levels", [
    ("Garen", "E_judgment", {1: 1, 2: 1, 3: 1, 4: 2, 5: 3, 9: 5}),   # EQW: E first and maxed first
    # level 8: E can't reach rank 5 yet (rank <= ceil(level/2)), so the point goes to Q
    ("Garen", "Q_decisive_strike", {1: 0, 2: 1, 7: 1, 8: 2, 10: 3}),
    ("Garen", "R_demacian_justice", {5: 0, 6: 1, 11: 2, 16: 3}),
    ("Azir", "W_soldier_attack", {1: 1, 6: 3, 9: 5}),                # WQE
    ("Lee Sin", "Q_resonating_strike", {1: 1, 9: 5}),                # recast shares Q's rank
])
def test_ability_ranks(champ, key, levels):
    kit = kits.load_kit(champ, "26.22")
    for lv, rank in levels.items():
        assert ability_rank(kit, key, lv) == rank, f"{key} at level {lv}"


def test_hand_calc_garen_q_level6():
    """Garen Q, level 6, 1 item (Berserker's Greaves: no AD), vs mage dummy at level 6.

    Wiki: Garen AD 69 + 4.5/lvl; Q rank 1 = 30 (+50% AD). Level factor (6-1)*(0.7025+0.0175*5) = 3.95.
    AD = 69 + 4.5*3.95 = 86.775. Raw = 30 + 0.5*86.775 = 73.3875.
    Mage dummy armor = 22.686 + 4.601*3.95 = 40.85995 -> x 100/140.85995.
    """
    expected = 73.3875 * 100 / (100 + 22.686 + 4.601 * 3.95)
    f = Setup(kits.load_kit("Garen", "26.22"), "Garen", 6, 1, "mage").fight()
    assert f.hit("Q_decisive_strike") == pytest.approx(expected, rel=1e-6)


def test_hand_calc_azir_soldier_level6():
    """Azir soldier stab (his auto), level 6, 1 item (Nashor's Tooth: 80 AP), vs mage dummy.

    Wiki: W rank 3 (WQE order) = 80 + (0-72 by level -> 72*5/17 at level 6) + 50% AP.
    Raw = 80 + 21.17647 + 0.5*80 = 141.17647 magic. Mage MR = 30.171 + 1.343*3.95 = 35.47585.
    """
    expected = (80 + 72 * 5 / 17 + 0.5 * 80) * 100 / (100 + 30.171 + 1.343 * 3.95)
    f = Setup(kits.load_kit("Azir", "26.22"), "Azir", 6, 1, "mage").fight()
    assert f.hit("AA") == pytest.approx(expected, rel=1e-6)


def test_garen_r_scales_with_missing_health():
    s = Setup(kits.load_kit("Garen", "26.22"), "Garen", 6, 1, "mage")
    full, low = s.fight(), s.fight()
    low.hp = low.t.max_hp * 0.3
    assert low.hit("R_demacian_justice") > full.hit("R_demacian_justice")


def test_deterministic():
    kit = kits.load_kit("Viego", "26.22")
    assert run_all(kit, "Viego") == run_all(kit, "Viego")


def test_buff_raises_soloq_index():
    kit = kits.load_kit("Garen", "26.22")
    before = evaluate(kit, "Garen", "26.22")
    buffed = kit.model_copy(deep=True)
    buffed.abilities["Q_decisive_strike"].base = [x * 1.2 for x in buffed.abilities["Q_decisive_strike"].base]
    after = evaluate(buffed, "Garen", "26.22")
    assert after["metrics"]["lane_trade_l6"] > before["metrics"]["lane_trade_l6"]
    assert delta(before, after)["soloq_index"] > 0


def test_pool_average_is_one():
    rows = [evaluate(kits.load_kit(c, "26.22"), c, "26.22") for c in kits.CHAMPIONS]
    assert sum(r["pro_index"] for r in rows) / len(rows) == pytest.approx(1.0, abs=0.05)


def test_riot_lee_sin_nerf_lowers_both_indices():
    """Riot's 26.21 Lee Sin nerf (R damage, W cooldown), run through our sim at 26.20 pool means."""
    before = evaluate(kits.load_kit("Lee Sin", "26.20"), "Lee Sin", "26.20")
    after = evaluate(kits.load_kit("Lee Sin", "26.21"), "Lee Sin", "26.20")
    d = delta(before, after)
    assert d["soloq_index"] <= 0 and d["pro_index"] <= 0
