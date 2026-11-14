"""Offline test of the base-block rewrite (no network). Values are synthetic."""
from pathlib import Path

import yaml

from schemas import Kit
from scripts.fetch_ddragon import FIELDS, rewrite

ROOT = Path(__file__).resolve().parents[1]


def test_rewrite_fills_base_only():
    text = (ROOT / "data/champions/azir.yaml").read_text(encoding="utf-8")
    stats = {k: float(i + 1) for i, k in enumerate(FIELDS)}
    kit = Kit.model_validate(yaml.safe_load(rewrite(text, stats, "1.1.1")))
    assert kit.patch == "1.1.1"
    assert kit.base.hp == 1.0 and kit.base.as_ == stats["as"]
    assert not any(m.startswith("base.") for m in kit.missing())
    assert kit.abilities == Kit.model_validate(yaml.safe_load(text)).abilities  # abilities untouched


def test_patch_label():
    from scripts.fetch_ddragon import patch_label
    assert patch_label("16.22.1") == "26.22"


def test_ad_growth_override():
    from scripts.fetch_ddragon import apply_overrides
    stats = {"ad_per_lvl": 0, "mp": 10000}
    assert apply_overrides("Viego", "26.17", stats) == {"ad_per_lvl": 3.5, "mp": 0}
    assert apply_overrides("Viego", "26.18", stats)["ad_per_lvl"] == 4.0
