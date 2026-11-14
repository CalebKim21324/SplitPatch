# SplitPatch — Claude Code instructions

Read `PLAN.md` first. It is the spec. Build in the order of its section 9 prompts.

## What this is
A League of Legends balance agent for DevHacks '26 (Riot Track 2). Its job is to separate pro-play power from solo queue power. The pipeline:
diagnose → propose a diff to champion data → independent verifier (simulator) → patch notes + checker.
Solo developer, hackathon deadline: submit by 10:30 Sun 15 Nov.

## Hard rules
- **Never modify `verify/`, `holdout/`, `notes/checker.py`, or anything in `tests/` to make a failing run pass.** Report the failure instead. The project's own agent is held to this same rule.
- The patch agent only gets the tools listed in PLAN.md 3.5. It must not get filesystem write access outside `proposals/`.
- Raw Reddit text never reaches the diagnoser or patcher. Only the validated complaint JSON (PLAN.md 3.3) does.
- `holdout/` is loaded only by `eval/`. It is never imported by `agent/` or exposed via tools.
- The simulator, verifier, diagnoser and notes checker are deterministic and don't use an LLM.
- Champion ability numbers come from hand-checked YAML in `data/champions/`. Never invent or "fill in" game numbers. Leave a `TODO` and tell me.

## Stack
Python 3.11, pydantic, PyYAML, pandas, scipy, pytest, LLM SDK (API key in `.env`, never committed).

## Working style
- Small, tested steps. Run `pytest` after every module.
- Commit after every working milestone. Tag the first Azir end-to-end pass as `demo-safe`.
- Log every agent attempt as JSON in `runs/`. That log is the demo's behavior trace.
- Record every simplification of game mechanics in `SIMPLIFICATIONS.md`.
- Behind schedule? Follow the cut list in PLAN.md section 6, in that order.
