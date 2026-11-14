"""Verifier tests: planted bad patches are all rejected, a valid patch passes, tampering is caught."""
from eval.mutation_test import CASES, S, diag, prop, run
from sim.kits import load_kit
from verify import integrity
from verify.verifier import verify


def test_all_planted_bad_patches_rejected():
    results = run()
    assert len(results) == len(CASES)
    missed = [name for name, rejected, _ in results if not rejected]
    assert missed == []


def test_valid_solo_only_nerf_passes():
    p = prop("Garen", S, [{"field": "base.ad", "from": 69, "to": 64}])
    res = verify(p, load_kit("Garen", "26.22"), diag("Garen", S), integrity.digest())
    assert res.passed, res.failures()
    assert res.deltas["soloq_index"] < 0


def test_integrity_detects_tampering():
    before = integrity.digest()
    after = dict(before)
    key = next(k for k in after if k.startswith("verify/"))
    after[key] = "0" * 64
    after["sim/new_file.py"] = "x"
    assert integrity.changed(before, after) == sorted([key, "sim/new_file.py"])
