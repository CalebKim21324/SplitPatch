# SplitPatch: short video script (about 2:30)

**[click]** means advance the slide one step. Use the short deck: https://claude.ai/artifact/G8rs8kxiCkJDF1RSQ5RC68

**Slide 1** (0:00)
Hi, I'm Caleb. This is SplitPatch, an AI agent that balances League champions and only ships changes it can verify.

**Slide 2** (0:07)
League has 171 champions and a patch every two weeks. The evidence is scattered, **[click]** and mistakes slip through.

**Slide 3** (0:17)
Most balance work shouldn't be automated. **[click]** Champions and art are creative. **[click]** Big system changes need playtesting. **[click]** Items change rarely and have little data. **[click]** Feel tweaks need player feedback. **[click]** But buffs and nerfs happen every two weeks, they're measurable, and they follow rules. That's what I automated.

**Slide 4** (0:40)
**[click]** Code scans every champion and decides who needs a change. **[click]** The agent picks the exact number and tests it in a simulator. **[click]** Code verifies it, and a designer approves it. **[click]** Then the agent writes the patch notes, and a checker matches them to the change.

**Slide 5** (0:55)
On the live patch, it scanned 171 champions, **[click]** flagged 27, **[click]** and planned six changes for 26.23. Here's the demo.

**Demo** (1:05)
- *Agent run tab: Blitzcrank is already selected. Click **Replay run**.*
  Blitzcrank wins 53% of games and gets banned in over a quarter of Korean games. The agent tests three ideas. Less damage and less range miss their targets, but one more second on the hook cooldown lands in both, and the verifier passes it.
- *Patch notes tab: scroll slowly.*
  It writes the patch notes in the format players already know, with every number checked against the change.
- *Safety checks tab: click **Run attacks**.*
  We attacked our own checks. Fifteen of fifteen bad patches were rejected, and eight of eight wrong notes were caught.
- *Backtest tab.*
  We replayed six past patches against Riot's real notes. SplitPatch's picks matched Riot more often than a win-rate rule, and about three times as often as random picks.

**Slide 6** (2:10)
The limits: the simulator is a model, not the game, and stats can't see everything Riot weighs.

**Slide 7** (2:17)
The demo link is on screen. Thanks for watching.
