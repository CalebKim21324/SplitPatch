# Simplifications

Every place the sim or data differs from real League mechanics. Judges will ask.

| Area | Simplification | Why |
|---|---|---|
| Kit DSL | Passives and complex mechanics become tagged flat effects | Numbers-only scope (PLAN.md 2) |
| Kit DSL | `hits` = fixed hits per cast in the standard combo (e.g. soldier count) | No positioning/pathing sim |
| Kit DSL | "Based on level" bonuses stored as [lvl1, lvl18] and interpolated linearly | Wiki gives only the endpoints |
| Viego W | Stun uses the max-channel value (1.25s); real range is 0.25-1.25s | No channel timing in the sim |
| Azir R | Knockback duration taken as 1.0s from "knocked away over 1 second" | Wiki lists no explicit CC duration |
| Passives | Sun Disc, Martial Poise, Perseverance regen and Viego's possession/heal are tags + notes only | Numbers-only scope |
| Base stats | AD growth from the wiki infobox; Data Dragon 16.x reports 0 for every champion | Data Dragon bug |
| Pro data | gol.gg per-patch presence is whole-number %; no pro games on 26.19/26.21/26.22 | Only per-patch figure gol.gg publishes |
| Abilities by patch | Kit YAML is the 26.22 kit; earlier patches are rebuilt by reversing Riot's changes (Qiyana Q 26.17/26.21, Lee Sin W/R 26.21) into per-patch snapshots | Only those champions changed ability numbers in window |
| Lee Sin | Energy stored in `mp` / `mana_cost`; energy regen and Flurry refunds not modeled yet | Kit DSL has one resource field |
| Lee Sin Q2 | Missing-health amplification (0-100%) in notes; sim must pick a target-health assumption | No fight-state model |
| Qiyana | Elements: only the terrain execute bonus is a candidate for modeling; river root and brush stealth are notes | Positional effects |
| Sim targets | Dummies = class-average base stats (Data Dragon primary tag Mage/Fighter/Tank), no items, never fight back | No opponent model |
| Sim builds | Every champion builds its 26.22 most common core + 4th item (lolalytics) on every patch; item passives not simulated | Data Dragon has no passive numbers |
| Sim combos | Trade combos and sustained rotations in `sim/combos.yaml` are design choices; cast times, travel time, positioning ignored | Deterministic, fast |
| Sim rotation | Execute abilities fire below 40% target hp; stacking abilities (Kalista E) at 5+ stacks | Simple, explainable policy |
| Bonus AS | Ability bonus AS counted at average uptime (duration / cooldown); passive-only AS (Lee Sin Flurry) excluded | No combat timeline for passives |
| Mana | Trades-to-oom ignores mana regen; manaless and energy champions capped at 10 | Lane-length proxy |
| Indices | Ratio to pool mean (not z-score) so relative changes are defined; equal weights until tuned on train patches | z-score near 0 makes "-8%" meaningless |
| Utility | CC seconds per 10 s at lvl 16 + 0.5 x slow seconds + 1.0 disengage tag bonus | Hand-set weights |
| Roster scan | Each champion is judged in its main role only (lolalytics `defaultLane`); servers below 20k (global) / 3k (KR) games are ignored | Off-role samples are small and noisy |
| Strong line | Slides with ban rate: 54% at or below the roster's average ban rate, down to 52.5% at 5x (Riot-style, per a secondary summary of Riot's framework) | Fixes flagging rarely banned champions like Garen |
| New kits | Ezreal, Blitzcrank, Malphite, Kog'Maw, Jayce use the generic combo (every non-ultimate damage ability + 2 attacks) and are judged against the original six-champion pool means | No hand-written combos yet |
| Jayce | Basic abilities have 6 ranks; the sim caps ranks at 5. Acceleration Gate and Mercury Hammer numbers omitted (not readable verbatim) | Partial kit |
| Pro presence | Latest gol.gg pro patch (26.20) for every champion, which predates Riot's 26.21 changes | No pro games on 26.21/26.22 |
