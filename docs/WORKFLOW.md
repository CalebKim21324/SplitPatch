# SplitPatch balance workflow (v2)

How SplitPatch decides **whether** to patch, **what** to change, and **proves** the change does what
it claims, for champions and items. Written against Riot's published frameworks so every step is
either borrowed from Riot or a stated improvement on it.

---

## 1. What Riot publishes today

From Riot's Champion Balance Framework update (June 2020) and Item Balance Framework (Sep 2020):

| Riot rule | Detail |
|---|---|
| Four audiences | Average, Skilled, Elite, Pro |
| Nerf/buff asymmetry | Nerf if overperforming in **any** group; buff only if underperforming in **all** groups |
| Ban-rate bands | The win-rate band tightens as ban rate rises above the average ban rate |
| Pro | Measured by presence (picks + bans), not win rate (small samples) |
| Feedback | "We now compare our estimated win rate changes to the actual win rates following the patch" |
| Items | Judged by purchase rate and win rate vs alternatives in the class, not raw win rate |
| Hardbinding | An item bound to 3+ champions gets an item fix; 1-2 champions get a champion fix |
| Per-champion item rules | No item bought > 75% by one champion; no item > 6% WR above that champion's alternatives; 10+ viable items |

**Limitations Riot names itself:**
- The framework "doesn't tell us *how* we should change a champion."
- Champions at "52-53% win rate with much higher pick/ban numbers" are hard to read.
- Item changes have "a much larger ripple effect" than champion changes.
- Item win rate is "unreliable" without a defined purchase slot, and late-slot items look strong
  because only players who are already ahead get to buy them.

---

## 2. What v2 does better (one line each)

| # | Riot gap | SplitPatch v2 |
|---|---|---|
| 1 | Raw win rate is skewed by popularity. Popular champions draw inexperienced players (Lee Sin, Viego); niche ones are inflated by one-tricks | **Popularity-adjusted WR**: the residual of WR vs log(pick rate), fit across the pool |
| 2 | Fixed thresholds ignore sample size | **Confidence intervals**: flag only when the interval clears the threshold |
| 3 | One global view (brackets, not servers) | **Region axis**: global + KR, with an explicit divergence check |
| 4 | Reacts to one patch | **Persistence rule**: the signal must hold for 2+ patches, unless it's extreme |
| 5 | Says *when*, not *how* | Sentiment picks the lever, the simulator sizes it, the verifier proves it |
| 6 | Predicted vs actual is checked after the fact | **Predicted ΔWR on every proposal**, plus a calibration loop that refits after each patch |
| 7 | Item ripple effects judged by eye | **Blast radius**: simulate every champion that builds the item, weighted by slot and exposure |
| 8 | Item WR biased by slot | **Same-slot lift**: compare an item only with alternatives bought in the same slot |
| 9 | Community feedback is informal | **Structured, injection-safe complaints** that can pick the lever but never the size |

We keep Riot's good parts unchanged: the nerf/buff asymmetry, ban-rate bands, presence for pro and hardbinding.

---

## 3. Champion pipeline

```
 stats (global, KR) ─► [1 Signals] ─► [2 Diagnose] ─► [3 Lever] ─► [4 Propose] ─► [5 Verify] ─► [6 Predict] ─► [7 Notes] ─► [8 Monitor]
 reddit ─► sentiment JSON ───────────────────────────────┘           ▲    LLM          │ no LLM         │                       │
                                                                     └──── FAIL + deltas (max 5) ───────┘                       │
                                                       calibration refit after the next patch ◄────────────────────────────────┘
```

### Step 1. Signals (deterministic)
For each champion × patch × region:
- `wr`, `pr`, `br`, `games` (lolalytics, Emerald+), plus pro `presence` (gol.gg).
- **Wilson 95% interval** on WR from `games`.
- **Popularity-adjusted WR**: fit `wr ~ a + b·log(pr)` across all champion-patch rows of the
  region (train patches only). Then `adj_wr = wr − (a + b·log(pr)) + 50`. A high-pick-rate
  champion at 49.5% raw can be "average" once adjusted, or not. The slope `b` is reported as evidence.
- **Ban pressure**: `br / mean_br` across the pool (Riot's ABR idea).
- **Trend**: WR slope over the last 3 patches.

### Step 2. Diagnose (deterministic rules, tunable on train patches only)

| Category | Rule | Target given to the patcher |
|---|---|---|
| `STRONG` | WR interval lower bound > `hi(br)` in **any** region, held 2 patches. `hi` slides from 53.5% at average ban rate to 52.5% at 5× average (Riot-style) | `soloq_index` −3% to −8% |
| `POPULAR_WEAK` | PR ≥ 5% and WR < 49.5% in **any** region, held 2 patches, not `STRONG` anywhere | `soloq_index` +2% to +6%, `pro_index` ≤ +3% |
| `WEAK` | WR interval upper bound < 48% in **all** regions | `soloq_index` +3% to +8% |
| `FRUSTRATION` | BR ≥ 5× average with WR in band (e.g. KR Lee Sin, 56% BR at 52% WR) | Fix the hated lever: same total power (`soloq_index` ±1%), shift away from the complained-about tag |
| `PRO_STRONG` | Pro presence ≥ 50% on 2+ pro patches (Riot measures pro by presence) | `pro_index` −5% to −10%, **`soloq_index` ≥ −1%**: nerf pro-weighted levers (late ratios, utility, range) and leave solo queue alone |
| `SOLOQ_ONLY_STRONG` / `PRO_JAIL` | As before; secondary | As before |
| `HOLD` | Otherwise | No change |

**Region divergence:** when regions disagree by more than 1.5 WR points, the proposal must stay inside the band in *every* region,
and the verifier checks each one separately. This is how Viego (KR 48.8%, global 50.4%) can get a buff that
doesn't make him a problem globally.

**Extreme override:** a WR interval beyond ±3 points from the band skips the persistence rule (the equivalent of a hotfix).

### Step 3. Lever (sentiment JSON + stats, deterministic)
- Complaint tags are ranked by count, and requests that disagree with the stats are dropped
  (a "buff" request for a `STRONG` champion is ignored).
- Map tags to kit fields: `mana`→`mana_cost`/`mp_per_lvl`, `survivability`→`hp`/`armor`/`shield`,
  `damage`→`base`/ratios, `cooldown`→`cooldown`, `cc`→`cc_duration`, `mobility`→`ms`/dash cooldowns.
- **Popular champions get early-game levers:** for `POPULAR_WEAK`, prefer levers that help in the first
  10 minutes (base stats, early ranks). Inexperienced players gain most there, and it doesn't raise the
  champion's ceiling in expert hands. Late ranks and ratios are where experts gain.

### Step 4. Propose (LLM tool loop, unchanged from PLAN.md 3.5)
`read_kit`, `read_stats`, `read_complaints`, `run_sim`, `submit_proposal`. At most 3 fields, each changed by at most 20%.
`read_kit(champ, patch)` returns that patch's kit snapshot only, never a later one.

### Step 5. Verify (deterministic, unchanged + region check)
Schema → limits → integrity hash → sim rerun against the target bands **per region** → hidden holdout scenarios.

### Step 6. Predict
Convert the simulated index change into a predicted WR change with an elasticity fit on train patches:
`ΔWR_pred = k · Δsoloq_index`, where `k` is fit from Riot's real changes (Δindex from our sim vs the
observed ΔWR in the next patch). Every proposal ships with "expected WR 48.8% → 50.1% (±0.6)".

### Step 7. Patch notes + checker (PLAN.md 3.7, unchanged)

### Step 8. Monitor (closed loop)
After the next patch: observed ΔWR vs predicted. Refit `k`, and log the overshoot or undershoot as a correction
candidate for the next patch, even when the champion is back inside the band (Riot's rule, made
automatic). In the backtest, this runs over 26.16 → 26.22.

---

## 4. Item pipeline

Items are harder because one change hits every champion that builds the item, and how much depends on
**when** they build it. A +10 AD change on a first item lands around minute 10 and affects laning. On a
fourth item, it lands around minute 28 and affects late fights only.

### Data
| File | Contents | Source |
|---|---|---|
| `data/items/items.yaml` | stats, cost, passive numbers per item | Data Dragon `item.json` + wiki for passives |
| `data/items/usage.csv` | `patch, region, champion, item, slot, pick_pct, wr, games` | lolalytics build pages (1st/2nd/3rd item tables) |
| `data/items/gold.csv` | gold per minute by role | lolalytics / gol.gg |

### I-1. Exposure
`E[c, i, s]` = share of champion `c`'s games where item `i` is bought in slot `s`.
Population weight of champion `c` = its pick rate. An item's **reach** is `Σ_c pr_c · Σ_s E[c,i,s]`.

### I-2. Timing model
Slot `s` completes at `t_s = cumulative_cost_s / gpm_role`. A cost change of `Δg` shifts completion
by `Δg / gpm`. The sim already runs fixed snapshots (1 item @ lvl 6, 2 @ lvl 9, 4 @ lvl 16). An
earlier or later completion moves the champion's stats between snapshots by linear interpolation.
So a cost cut on a first item mainly moves `lane_trade_l6` and `duel_ttk_l9`, and a stat buff on a
4th item mainly moves `late_dps_l16`.

### I-3. Item signals (fixes Riot's slot bias)
- **Same-slot lift:** `lift[c,i,s] = WR(i in slot s) − mean WR(alternatives in slot s)` for champion `c`,
  with Wilson intervals. Items are only ever compared within the same slot.
- **Share:** `E[c,i,s]` against Riot's 75% rule.

### I-4. Item diagnose
| Category | Rule | Fix |
|---|---|---|
| `ITEM_STRONG` | lift interval > +3 points for **3+ champions** in the same slot | item nerf |
| `ITEM_WEAK` | lift < −3 points for most users and below-median reach | item buff |
| `ITEM_HARDBOUND` | one or two champions buy it > 75% in a slot | **route to a champion fix** (Riot's hardbinding rule): adjust that champion's ratio that scales with the item's stat |
| `HOLD` | otherwise | no change |

The **champion-vs-item routing** is automatic: a problem concentrated in 1-2 champions is a champion
proposal, while one spread across 3+ champions is an item proposal.

### I-5. Propose
Same tool loop, diffing `items.yaml` (stat values, cost, passive numbers). Limits: at most 3 fields, stats changed by at most 15%,
cost changed by at most 10%.

### I-6. Verify: blast radius
For every champion that builds the item: apply the diff and run the sim at each slot the item is built in,
then weight by `E[c,i,s]`. Δindex for champion `c` = `Σ_s E[c,i,s] · Δindex(c, item in slot s)`.
- **Target users** (the champions that triggered the flag) must land inside the target band.
- **Bystanders** (everyone else who builds it) must move ≤ ±2% on both indices. This is the ripple guard.
- The verifier prints the blast-radius table: champion, exposure, Δsoloq, Δpro, PASS/FAIL.

### I-7. Joint patches
If a patch has a champion change **and** an item change that the champion builds, the verifier
applies both diffs together and reruns, so two individually safe changes can't stack into one unsafe one.

---

## 5. Evaluation (adds to PLAN.md section 4)
- **Direction agreement** with Riot on 26.17-26.22 changes (24 champion-patch rows per region).
- **Adjusted vs raw WR ablation:** how often each version agrees with Riot. Example from our data: Viego
  KR 48.9% at 7% PR in 26.16-26.17, then a Riot buff in 26.18.
- **Region ablation:** global-only vs global + KR.
- **Pro-spillover case (headline for the secondary pillar):** Lee Sin had 54-57% pro presence in 26.18/26.20.
  Riot's 26.21 nerf (R damage, W cooldown) took his global solo queue WR from 50.79% to 49.47%, which made
  him `POPULAR_WEAK`. We run Riot's diff and our `PRO_STRONG` proposal through the same sim and compare
  Δpro vs Δsoloq.
- **Persistence ablation:** false alarms with vs without the 2-patch rule.
- **Prediction error:** |ΔWR_pred − ΔWR_actual| on Riot's own changes, run through our sim.
- **Blast-radius demo:** one item proposal whose bystanders all stay within ±2%.

Caveat to say out loud: 5 Riot balance changes fall in the window (Azir, Viego, Qiyana ×2, Lee Sin). That's
enough for a demo, not for statistics. We report the counts, not percentages dressed up as significance.

---

## 6. Hackathon scope (by Sunday 10:30)

**Must**
1. Signals: Wilson interval, popularity-adjusted WR, ban pressure, persistence, regions.
2. Diagnoser v2 (section 3, step 2).
3. Sim + verifier with per-region target checks.
4. Patch agent loop, then patch notes.
5. Backtest + ablations (adjusted vs raw, regions).

**Should** (item path, minimal)
6. 3-5 items commonly built by our 6 champions: `items.yaml` from Data Dragon, `usage.csv` from lolalytics.
7. Exposure-weighted sim + blast-radius verifier, with one item proposal in the demo.

**Cut order if behind:** patch notes → item path (pitch it as designed) → prediction/calibration → FRUSTRATION category.
**Never cut:** verifier, one champion end-to-end, one baseline comparison.

---

## Sources
- Riot, /dev: Balance Framework Update (2020-06-30): https://www.leagueoflegends.com/en-us/news/dev/dev-balance-framework-update/
- Riot, /dev: Updated Approach to Item Balancing (2020-09-14): https://www.leagueoflegends.com/en-au/news/dev/dev-updated-approach-to-item-balancing/
- Both are 2020 posts. Riot may have changed its process since, so we compare against what is published.
