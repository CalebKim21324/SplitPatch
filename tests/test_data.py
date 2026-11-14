"""Consistency checks on the frozen dataset (no numbers asserted from memory)."""
import csv
from pathlib import Path

import pytest

from schemas import Kit, ProRow, SoloQRow

ROOT = Path(__file__).resolve().parents[1]
CHAMPS = ["Azir", "Kalista", "Garen", "Viego", "Qiyana", "Lee Sin"]
REGIONS = ["global", "kr"]
PATCHES = [f"26.{n}" for n in range(16, 23)]


def slug(champ):
    return champ.lower().replace(" ", "")


def rows(name):
    return list(csv.DictReader(open(ROOT / f"data/stats/{name}.csv", encoding="utf-8")))


@pytest.mark.parametrize("champ", CHAMPS)
def test_kit_base_matches_ddragon_csv(champ):
    kit = Kit.load(ROOT / f"data/champions/{slug(champ)}.yaml")
    row = next(r for r in csv.DictReader(open(ROOT / "data/champions/base_stats.csv"))
               if r["champion"] == champ and r["patch"] == kit.patch)
    for k, v in kit.base.model_dump(by_alias=True).items():
        assert float(row[k]) == v, f"{champ} base.{k}"


@pytest.mark.parametrize("champ", CHAMPS)
def test_kit_complete(champ):
    assert Kit.load(ROOT / f"data/champions/{slug(champ)}.yaml").missing() == []


def test_soloq_complete():
    data = [SoloQRow(**r) for r in rows("soloq")]
    assert {(r.region, r.champion, r.patch) for r in data} == {(g, c, p) for g in REGIONS for c in CHAMPS for p in PATCHES}
    assert len(data) == len(REGIONS) * len(CHAMPS) * len(PATCHES)


def test_pro_rows_valid():
    data = [ProRow(**{k: (v or None) for k, v in r.items()}) for r in rows("pro")]
    assert {r.champion for r in data} == set(CHAMPS)
    assert all(r.patch in PATCHES for r in data)
