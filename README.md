# SplitPatch

A balance agent for League of Legends that only ships patches it can verify. Built for DevHacks '26, Riot Games Track 2 (agentic development).

## Try it out

- **Live demo:** https://claude.ai/artifact/YJteopG5KedGc9x8W8gVNJ
- **Slides:** https://claude.ai/artifact/EAxUyowjSTiZp9Ctk4qiax
- **Video:** [video link]
- **Code:** this repo

## What it does

Every patch, SplitPatch:

1. **Scans** every champion with enough games on the global and Korean servers (lolalytics, Emerald+), plus pro presence (gol.gg) and Reddit.
2. **Diagnoses** who needs a change with deterministic rules based on Riot's published 2020 balance framework. The "too strong" line slides with ban rate. The rules also set a target band for how far solo queue and pro power should move.
3. **Proposes:** a Claude agent picks the ability and the number, and tests ideas in the simulator. Its only tools are `read_stats`, `read_kit`, `read_complaints`, `run_sim` and `submit_proposal`.
4. **Verifies** each proposal with code the agent can't edit: schema and allowlist, at most 3 fields and 20% per value, a SHA-256 lock on the simulator, verifier and data, the target band, and hidden holdout scenarios.
5. **Writes patch notes and tooltips.** A deterministic checker matches every number, every direction word and every tooltip value against the diff.

Raw Reddit text never reaches the agent. Posts are turned into fixed complaint tags first, which also blocks prompt injection.

## Results (patch 26.22)

- 171 champions scanned, 27 flagged, 6 patched. All 6 passed the verifier and the notes checker on the first try.
- The verifier rejected 15 of 15 planted bad patches.
- The notes checker caught 8 of 8 planted mistakes in patch notes.
- A planted prompt-injection post was blocked: the agent received one complaint tag.
- Backtest against Riot's next-patch changes for six champions, patches 26.16 to 26.21:

  | System | Riot changes caught | False alarms | Proposals that passed the verifier |
  |---|---|---|---|
  | Rule baseline | 0/5 | 6 | n/a |
  | One-shot LLM | 3/5 | 23 | 8/12 |
  | SplitPatch | 2/5 | 12 | 14/14 |

Limits are listed in `SIMPLIFICATIONS.md` and on the slides. In short:

- The simulator is a model, not the game.
- The backtest is small.
- The champion kits were copied from the wiki by hand.

## Run it

```
pip install -r requirements.txt        # Python 3.11
pytest                                 # 88 tests
python -m agent.scan --patch 26.22     # whole-roster scan
python -m agent.run_patch --patch 26.22 --from-scan   # needs ANTHROPIC_API_KEY in .env
python eval/mutation_test.py           # verifier attack cases
python eval/workflow_data.py && python eval/build_page.py   # build the demo page -> runs/demo.html
```

See `PLAN.md` and `docs/WORKFLOW.md` for the design.
