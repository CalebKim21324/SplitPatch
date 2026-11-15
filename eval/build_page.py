"""Build the demo page: compact runs/workflow_data.json and inline it into app/demo.html.

Usage: python eval/build_page.py [out_path]   (default runs/demo.html)
Run `python eval/workflow_data.py` first to refresh the data.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tool_results(log):
    """Pair each tool call with its result, in order, grouped by turn."""
    turns, pending = [], []
    for e in log:
        if "tool_calls" in e:
            calls = [{"name": c["name"], "input": c["input"]} for c in e["tool_calls"]]
            turns.append({"turn": e["turn"], "seconds": e["seconds"], "say": e.get("say", []), "calls": calls})
            pending = list(calls)
        elif "tool" in e and pending:
            c = pending.pop(0)
            r = e["result"]
            if c["name"] == "run_sim":
                c["result"] = {"delta": r.get("index_delta"), "before": r.get("metrics_before"),
                               "after": r.get("metrics_after")}
            elif c["name"] == "submit_proposal":
                c["result"] = r
            else:
                c.pop("input")
    return turns


def compact(d):
    runs = []
    for t in d["run"]["traces"]:
        sub = t["submissions"][-1] if t["submissions"] else None
        runs.append({
            "champion": t["champion"], "lane": t["stats"].get("lane"),
            "stats": t["stats"]["solo_queue"], "presence": (t["stats"].get("pro") or {}).get("presence"),
            "posts": t["sentiment"]["n_posts"], "complaints": t["sentiment"]["complaints"]["complaints"],
            "category": t["diagnosis"]["category"], "reasons": t["diagnosis"]["reasons"],
            "target": t["diagnosis"]["target"], "turns": tool_results(t["agent_log"]),
            "submissions": len(t["submissions"]), "verifier": sub["verifier"] if sub else None,
            "proposal": t["agent"].get("proposal"), "usage": t["agent"].get("usage"),
            "notes": t["notes"], "seconds": t["seconds"], "decision": t["decision"],
        })
    sc = d["scan"]
    points = [{"c": r["champion"], "lane": r["lane"], "cat": r["category"], "sev": r.get("severity"),
               "presence": r.get("presence"), "g": r["stats"].get("global"), "kr": r["stats"].get("kr")}
              for r in sc["results"]]
    rb = ROOT / "runs" / "backtest" / "roster_backtest.json"
    roster_bt = json.loads(rb.read_text(encoding="utf-8")) if rb.exists() else None
    return {"patch": d["run"]["patch"], "runs": runs, "roster_bt": roster_bt,
            "scan": {k: sc[k] for k in ("avg_ban_rate", "n_champions", "flagged", "selected")} | {"points": points},
            "injection": d["injection"], "evidence": d["evidence"], "backtest": d["backtest"]}


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runs" / "demo.html"
    d = json.loads((ROOT / "runs" / "workflow_data.json").read_text(encoding="utf-8"))
    data = json.dumps(compact(d), separators=(",", ":")).replace("</", "<\\/")
    html = (ROOT / "app" / "demo.html").read_text(encoding="utf-8").replace("/*DATA*/null", data)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
