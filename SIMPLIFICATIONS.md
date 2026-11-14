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
