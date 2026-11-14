# Stats sources

## soloq.csv
lolalytics.com, Ranked Solo/Duo, Emerald+, champion's main lane
(Azir mid, Kalista bottom, Garen top, Viego jungle, Qiyana mid, Lee Sin jungle). Read 2026-11-14.
`region` = `global` or `kr` (Korean server, `&region=kr`).
URL pattern: `https://lolalytics.com/lol/<champ>/build/?tier=emerald_plus&lane=<lane>[&region=kr]&patch=16.<n>`
(lolalytics labels patch 26.n as 16.n). Azir 26.21 WR shown on the page only as "49%".
26.22 is the live patch, so its sample is still growing.

## pro.csv
gol.gg season S16, all tournaments, "Presence by patch" chart on each champion-stats page
(`scripts/fetch_golgg.py`). Whole-number presence %. Per-patch picks/bans/wr are not
published there, so those columns are blank. gol.gg lists no pro games on 26.19, 26.21, 26.22.
Season aggregate (all S16 patches) for reference: Azir 899 picks / 964 bans / 44.5% WR;
Kalista 359 / 294 / 51.5%; Viego 110 / 93 / 37.3%; Garen 28 / 9 / 46.4%.
