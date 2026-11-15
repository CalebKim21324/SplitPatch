# SplitPatch: 3-minute video script

Read at a calm, steady pace (about 160 words a minute). **[click]** means advance one step on the slide. Each slide's speaker notes hold the same text.

Before recording:
- Open the slides in Present mode.
- Open the demo in a second tab, on the **Agent run** tab.
- Total: about 3:00.

---

**1 · Cover** (0:00–0:07)
Hi, I'm Caleb. This is SplitPatch, an AI agent that balances League of Legends champions and only ships the changes it can verify.

**2 · Balancing 171 champions every two weeks** (0:07–0:22)
League has 171 champions and a new patch every two weeks. For a balance designer, the evidence is scattered: solo queue stats, pro play and Reddit.
**[click]** And mistakes happen. A nerf aimed at pro play hits solo queue players, or a tooltip still shows last patch's number.

**3 · Which balance work should an agent do?** (0:22–0:52)
So why this scope? League's development has a lot of parts, and most of them shouldn't be automated.
**[click]** New champions, art and skins are creative design. People should own that.
**[click]** Objectives and mid-scope updates are big system changes. They need deep exploration and playtesting.
**[click]** Items change rarely, there's little public data on them, and right now the meta is driven by champion strength, not items.
**[click]** Feel adjustments lean on intuition and close feedback from players.
**[click]** But champion buffs and nerfs happen every two weeks. They're measured in win, pick and ban rates, and they follow known rules. That's the part worth automating.

**4 · One job, every two weeks** (0:52–1:00)
So SplitPatch does one job. Every two weeks, it decides who needs a buff or a nerf, and by how much, and writes the patch notes to match.

**5 · One loop, every patch** (1:00–1:17)
Here's the loop.
**[click]** Code scans every champion and decides who needs a change, and by how much.
**[click]** The agent proposes the exact number and tests it in a simulator.
**[click]** Code verifies it, and a designer approves it.
**[click]** Finally the agent writes the patch notes, and a checker matches them against the change.

**6 · The agent chooses. Code decides.** (1:17–1:30)
The agent has freedom where judgment matters: which ability to change, and how.
**[click]** Code decides everything you need to trust: who needs a change, whether it passes, and what Reddit is allowed to say. Raw posts never reach the agent.

**7 · The agent never grades its own work** (1:30–1:36)
That's the rule we built around: the agent never grades its own work.

**8 · The whole roster, scanned** (1:36–1:46)
Here it is on the live patch, 26.22. It scanned 171 champions, **[click]** flagged 27, **[click]** and planned six changes for patch 26.23. All six passed on the first try. Let me show you one.

**DEMO** (1:46–2:20). Switch to the demo tab.
- *Agent run tab: Blitzcrank is already selected. Click **Replay run**.*
  Blitzcrank wins 53% of games and gets banned in over a quarter of Korean games. The agent tests three ideas. Less damage and less range miss their targets, but one more second on the hook cooldown lands in both, and the verifier passes it.
- *Click the **Patch notes** tab and scroll slowly.*
  Then it writes the patch notes, in the same format players already read every two weeks, with every number checked against the change.
- *Click the **Safety checks** tab, then **Run attacks**.*
  And we attacked our own checks. Fifteen of fifteen bad patches were rejected, and eight of eight wrong notes were caught.

**9 · Patch 26.23, written by the agent** (2:20–2:26). Switch back to the slides.
Here's the full patch 26.23 it wrote. Each change is aimed at a specific group of players.

**10 · Backtest against Riot's real patches** (2:26–2:41)
We backtested against Riot's real decisions. A simple win-rate rule never caught a single real change. A one-shot LLM raised 23 false alarms, and a third of its patches were invalid.
**[click]** SplitPatch caught two of five, before Riot made them, and every patch it wrote was valid.

**11 · What's new here** (2:41–2:50)
What's new? We start from Riot's published balance framework, **[click]** then run it on every champion every patch, aim each change at specific players, and check the notes against the change.

**12 · What it can't do yet** (2:50–2:57)
The limits: the simulator is a model, not the game, and the backtest is small. Next come real match replays and a review screen for designers.

**13 · Try it out** (2:57–3:00)
That's SplitPatch. The links are on screen. Thanks for watching.

---

Slides 14–15 are an appendix for live Q&A: a full behavior trace and the attack results. They aren't in the video.
