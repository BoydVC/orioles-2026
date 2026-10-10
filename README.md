# Orioles 2026 · Camden Yards Night Wall

A **dark Camden Yards night wall** for Boyd: the Orioles’ **2026 regular season** (Stats API only) plus an **offseason board** from on-disk `/workspace/ij_*` research. Nothing baseball-factual is invented — gaps are labeled on the wall.

## What’s new — Sat Oct 10 afternoon remaster
- **Night wall aesthetic:** deep yard void, Oriole orange floodlight glow, gold trim (replaces the parchment scrapbook sheet).
- **Multi-panel layout:** offseason board + labeled gaps, hero chips, game-by-game chart, months/splits, AL East race, leaders, streaks, best/worst nights.
- **Offseason honesty:** `data/research_notes.json` from `ij_2026-09-25` through `ij_2026-10-07` (layoffs, GM search open, crowded 2027 infield commentary). **No GM hire name**, **no invented roster moves**.
- **Ship pattern:** `dist/orioles-2026-snapshot.html` (offline, data inlined); `screenshots/00-best-home.png`; `run.sh` + stdlib server on **127.0.0.1:4278**.

## Open it
- Live: http://127.0.0.1:4278 (`./run.sh start`, 127.0.0.1 only)
- Offline: `dist/orioles-2026-snapshot.html`
- Best screenshot: `screenshots/00-best-home.png`

## Headline numbers (MLB Stats API, fetched Oct 7, 2026 ET)
| | |
|---|---|
| Final record | **79–82** (.491) in **161** games |
| Run differential | 718–739 (**−21**) · Pythagorean ~78–83 |
| AL East | **4th**, **18.5 GB** |
| Wild Card | **4.5 GB** of the last spot · missed postseason |
| Season notes | Sep 27 @ NYY cancelled (rain, never made up); Aug 2 vs PHI rain-shortened |

Standings/stats above are recomputed in `build.py` from `data/*.json` and cross-checked by `tests/smoke_test.py` against the raw schedule and official standings.

## Commands
```
./run.sh start|stop|restart|status
./run.sh ship      # research + build + restart + screenshots + smoke
./run.sh build     # research + build + screenshots
./run.sh test      # python3 tests/smoke_test.py
./run.sh fetch     # re-pull Stats API then build (optional; remaster used on-disk data)
```

## Data
- **Season wall:** public MLB Stats API (`statsapi.mlb.com`, team 110) — schedule, AL East rivals, standings, player/team stats, postseason schedule. Cached under `data/`, fetched `2026-10-07T17:25:59-04:00`.
- **Offseason board:** `/workspace/ij_*` research only via `build_research.py` → `data/research_notes.json`.

## Privacy and scope
Public MLB JSON + local research files only. No accounts, no keys, nothing sent. Server binds **127.0.0.1**. Not affiliated with MLB or the Baltimore Orioles.


---
## Repo notes
- **Built:** Oct 7, 2026, by TokenMax (Boyd's Grok Bot) on the Grok Bot box.
- **Run:** `./run.sh` (then open the localhost URL it prints).
- Imported from `/workspace/tokenmax/orioles-2026` on Oct 23, 2026. node_modules, virtualenvs, logs and files over 20 MB were left out.
