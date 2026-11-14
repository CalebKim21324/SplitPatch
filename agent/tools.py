"""The only tools the patch agent gets (PLAN.md 3.5). Never imports holdout/ or eval/.

read_kit, read_stats, read_complaints, run_sim, submit_proposal. Each session is bound to one
champion and patch; the only write is the proposal file under proposals/.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from agent import sentiment
from schemas import Diagnosis, Kit, Proposal
from sim.indices import delta, evaluate
from sim.patching import apply, get_field
from verify.verifier import ABILITY_FIELDS, BASE_FIELDS, MAX_FIELDS, MAX_REL_CHANGE, verify

ROOT = Path(__file__).resolve().parents[1]
MAX_SUBMISSIONS = 5

_CHANGES = {"type": "array", "description": "Up to 3 field changes.", "items": {
    "type": "object", "additionalProperties": False, "required": ["field", "from", "to"],
    "properties": {
        "field": {"type": "string", "description": "base.<stat> or abilities.<key>.<field>"},
        "from": {"type": "array", "items": {"type": "number"}, "description": "Current value(s); scalars as a 1-item list."},
        "to": {"type": "array", "items": {"type": "number"}, "description": "New value(s), same length as from."},
    }}}

TOOLS = [
    {"name": "read_kit", "strict": True,
     "description": "The champion's kit for this patch: base stats and every ability's numbers.",
     "input_schema": {"type": "object", "additionalProperties": False, "properties": {}, "required": []}},
    {"name": "read_stats", "strict": True,
     "description": "Solo queue stats (global + KR), pro presence, the diagnosis with numeric target bands for both indices, and the patch rules.",
     "input_schema": {"type": "object", "additionalProperties": False, "properties": {}, "required": []}},
    {"name": "read_complaints", "strict": True,
     "description": "Structured community complaints (tag, direction, count). Use them to choose WHICH lever; stats decide how much.",
     "input_schema": {"type": "object", "additionalProperties": False, "properties": {}, "required": []}},
    {"name": "run_sim", "strict": True,
     "description": "Simulate a candidate diff. Returns metric changes and the relative change of soloq_index and pro_index. Not pass/fail.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["changes"],
                      "properties": {"changes": _CHANGES}}},
    {"name": "submit_proposal", "strict": True,
     "description": f"Submit the final diff with a rationale. An independent verifier reruns everything and returns PASS or FAIL with reasons. At most {MAX_SUBMISSIONS} submissions.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["changes", "rationale"],
                      "properties": {"changes": _CHANGES, "rationale": {"type": "string"}}}},
]


class Session:
    def __init__(self, kit: Kit, diagnosis: Diagnosis, stats: dict, integrity_before: dict):
        self.kit, self.diag, self.stats, self.integrity = kit, diagnosis, stats, integrity_before
        self.submissions: list[dict] = []
        self.passed: Proposal | None = None
        self.last_result = None

    # -- helpers
    def _proposal(self, changes: list[dict], rationale: str) -> Proposal:
        fixed = []
        for c in changes:
            cur = get_field(self.kit, c["field"])
            scalar = not isinstance(cur, list)
            fixed.append({"field": c["field"],
                          "from": c["from"][0] if scalar and len(c["from"]) == 1 else c["from"],
                          "to": c["to"][0] if scalar and len(c["to"]) == 1 else c["to"]})
        return Proposal(champion=self.kit.name, patch=self.kit.patch, category=self.diag.category,
                        changes=fixed, rationale=rationale)

    # -- tools
    def read_kit(self) -> dict:
        return self.kit.model_dump(by_alias=True, exclude_none=True)

    def read_stats(self) -> dict:
        return {**self.stats, "diagnosis": self.diag.model_dump(mode="json"), "rules": {
            "max_fields": MAX_FIELDS, "max_relative_change_per_value": MAX_REL_CHANGE,
            "editable_base_fields": sorted(BASE_FIELDS), "editable_ability_fields": sorted(ABILITY_FIELDS),
            "from_must_equal_current_value": True,
            "note": "Targets are relative changes of each index, e.g. -0.01 = -1%. Both must land in band. "
                    "The verifier also runs hidden scenarios you can't see; keep the change honest, not tuned to one metric."}}

    def read_complaints(self) -> dict:
        c = sentiment.load(self.kit.name, self.kit.patch)
        return c.model_dump() if c else {"complaints": [], "n_posts": 0, "note": "no complaints collected"}

    def run_sim(self, changes: list[dict]) -> dict:
        p = self._proposal(changes, "sim")
        before, after = evaluate(self.kit, self.kit.name, self.kit.patch), evaluate(apply(self.kit, p), self.kit.name, self.kit.patch)
        return {"index_delta": delta(before, after),
                "metrics_before": before["metrics"], "metrics_after": after["metrics"],
                "target": self.diag.target.model_dump()}

    def submit_proposal(self, changes: list[dict], rationale: str) -> dict:
        if len(self.submissions) >= MAX_SUBMISSIONS:
            return {"result": "REFUSED", "reason": "submission limit reached"}
        p = self._proposal(changes, rationale)
        n = len(self.submissions) + 1
        out = ROOT / "proposals" / self.kit.patch / f"{self.kit.name.lower().replace(' ', '')}_attempt{n}.yaml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(p.to_yaml(), encoding="utf-8")
        res = verify(p, self.kit, self.diag, self.integrity)
        self.last_result = res
        self.submissions.append({"attempt": n, "proposal": p.model_dump(by_alias=True, mode="json"),
                                 "file": str(out.relative_to(ROOT)).replace("\\", "/"), "verifier": res.to_dict()})
        if res.passed:
            self.passed = p
            return {"result": "PASS", "index_delta": res.deltas}
        return {"result": "FAIL", "failures": res.failures(), "index_delta": res.deltas,
                "submissions_left": MAX_SUBMISSIONS - n}

    def call(self, name: str, args: dict) -> str:
        fn = {"read_kit": self.read_kit, "read_stats": self.read_stats, "read_complaints": self.read_complaints,
              "run_sim": self.run_sim, "submit_proposal": self.submit_proposal}[name]
        return json.dumps(fn(**args), default=float)
