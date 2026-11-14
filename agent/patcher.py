"""Patch agent (PLAN.md 3.5): an LLM tool loop that turns a diagnosis into a verified diff.

The loop ends when the verifier returns PASS, after 5 failed submissions (-> HOLD + escalate to a
designer), or after MAX_TURNS model turns. Every model turn and tool call is appended to `log`.
"""
from __future__ import annotations

import json
import time

from agent import llm
from agent.tools import MAX_SUBMISSIONS, TOOLS, Session

MAX_TURNS = 30

SYSTEM = """You are the patch agent on a League of Legends balance team.

You get one champion, one patch and a diagnosis with numeric targets for two indices from a
deterministic simulator: soloq_index (individual, early/mid power) and pro_index (late, coordinated
power). Your job: propose a small number change (max 3 fields, each value within 20%) that lands BOTH
indices inside their target bands, then submit it. An independent verifier reruns everything.

How to work:
1. read_stats and read_kit first; read_complaints to see which levers players are upset about.
   Complaints choose the lever; the stats and targets decide the size. Ignore complaints that point the
   other way from the diagnosis.
2. Form a hypothesis about which levers move solo queue power vs pro power. Early-rank values and base
   stats tend to move solo queue; late ranks, ratios and utility move pro. Use run_sim to test candidates
   before submitting. Prefer the simplest change a player would understand.
3. submit_proposal with a rationale in plain designer language: what the problem is and why this lever.
   If the verifier says FAIL, read the reasons and adjust. You have 5 submissions.
Only edit fields that already have values in the kit, and copy `from` exactly from read_kit."""


def run(session: Session, log: list) -> dict:
    kit, diag = session.kit, session.diag
    messages = [{"role": "user", "content":
                 f"Champion: {kit.name}. Patch: {kit.patch}. Diagnosis: {diag.category.value}. "
                 "Find and submit a verified patch."}]
    usage = {"input_tokens": 0, "output_tokens": 0}
    for turn in range(1, MAX_TURNS + 1):
        t0 = time.time()
        resp = llm.create(system=SYSTEM, messages=messages, tools=TOOLS, effort="high", max_tokens=32000)
        for k, v in llm.usage(resp).items():
            usage[k] += v
        texts = [b.text for b in resp.content if b.type == "text" and b.text.strip()]
        calls = [b for b in resp.content if b.type == "tool_use"]
        log.append({"turn": turn, "seconds": round(time.time() - t0, 1), "say": texts,
                    "tool_calls": [{"name": c.name, "input": c.input} for c in calls]})
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use" or not calls:
            break
        results = []
        for c in calls:
            try:
                out = session.call(c.name, dict(c.input))
                results.append({"type": "tool_result", "tool_use_id": c.id, "content": out})
            except Exception as e:
                out = f"Error: {type(e).__name__}: {e}"
                results.append({"type": "tool_result", "tool_use_id": c.id, "content": out, "is_error": True})
            log.append({"turn": turn, "tool": c.name, "result": json.loads(out) if out.startswith("{") else out})
        messages.append({"role": "user", "content": results})
        if session.passed or len(session.submissions) >= MAX_SUBMISSIONS:
            break
    outcome = "PASS" if session.passed else ("ESCALATE" if session.submissions else "NO_SUBMISSION")
    return {"outcome": outcome, "submissions": session.submissions, "usage": usage,
            "proposal": session.passed.model_dump(by_alias=True, mode="json") if session.passed else None}
