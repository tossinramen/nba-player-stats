# NBA Prop Board

A local prop research board: every player on every 2026-27 NBA roster, every game they
played in 2025-26 (regular season, play-in, playoffs) plus 2026-27 as it happens, and
today's player prop lines and odds from FanDuel and Underdog.

The site is React (Vite); the data is pulled by Python.

## Setup (once)

```
pip install -r requirements.txt
npm install
```

## Daily use

```
npm run update      # pull stats + lines (~1 minute); same as: python update.py
npm run dev         # start the site at http://localhost:5173 (opens your browser)
```

Leave `npm run dev` running if you like: every time you run `npm run update` in another
terminal, the open page reloads with the new data. Each update pulls last night's games,
so L5/L10/L20, streaks and the 2026-27 column move forward automatically.

`python update.py` options:

| Option | What it does |
|---|---|
| `--no-props` | skip the sportsbooks (stats only) |
| `--source bbref` | use the Basketball-Reference backup instead of nba_api |
| `--refresh` | re-download cached past seasons (normally pulled once) |

## Columns

| Column | Meaning |
|---|---|
| Score | 0-100 blend of the hit-rate columns (small samples count less), the matchup rank and projection vs. line |
| Team / Pos / Exp | current team, position, years in the NBA (R = rookie) |
| Prop | `o`/`u` + line + category. `ALT` = alternate line, `MODEL` = no book line (see *All Players*) |
| L10 Avg / L5 Avg | average over the last 10 / 5 games (green = clears the line) |
| Projection | recency-weighted average adjusted for the opponent's defense vs. the position; the small number is projection minus line |
| Odds | best price for the chosen side. Click for every book's line and odds |
| Streak | consecutive most-recent games hitting the chosen side |
| Matchup | opponent and their rank (1-30) for the stat allowed to the player's position. 30 = allows the most; green = favorable for the chosen side |
| 2025-26 / 2026-27 | hit rate over that whole season |
| H2H | hit rate vs. this opponent across both seasons |
| L5 / L10 / L20 | hit rate over the last 5 / 10 / 20 games played |

Click a row to see the last 20 games as a bar chart against the line, and to type a
custom line (all the hit rates recalculate). **All Players** adds every rostered player
in the selected games for categories with no book line, using their recent average
rounded to x.5. **Export** saves the current filtered view as CSV.

Every raw player-game is also written to `data/gamelogs.csv`.

## Where the data comes from

- **Stats:** `nba_api` (stats.nba.com): rosters via `PlayerIndex`, every player-game via
  `LeagueGameLog`, schedule via `ScheduleLeagueV2`. A handful of requests total.
- **Backup:** if nba_api fails, `update.py` switches to Basketball-Reference, scraped with
  pydoll: each `/teams/XXX/2027.html` roster, then every player's
  `/players/x/id/gamelog/YYYY/` page. Basketball-Reference bans clients doing more than
  20 requests a minute, so this is paced at one page every 3.5s: the first run takes about
  an hour, and later runs about 35 minutes (past seasons are cached; rosters and the current
  season are re-fetched once a day). If a run is interrupted, re-running resumes where it
  stopped.
- **Props/odds:** the public JSON feeds behind underdogfantasy.com and sportsbook.fanduel.com
  (no API key). FanDuel adds alternate lines and N+ milestone markets (shown with *Show Alt
  Lines*). These feeds are unofficial and can change; if one breaks the other keeps working.

## Settings

`nbaprops/config.py`:
- `SEASONS`: add `"2024-25"` to the front for a deeper H2H sample (adds a season column too)
- `LOOKAHEAD_DAYS`: how many days of upcoming games/props to pull
- `NAME_ALIASES`: if `update.py` reports a sportsbook name it couldn't match to a roster
  player, map it here

## Files

```
update.py                  run this daily (npm run update)
nbaprops/nba_source.py     nba_api fetchers
nbaprops/bbref_source.py   Basketball-Reference backup (pydoll)
nbaprops/books.py          Underdog + FanDuel lines
nbaprops/build.py          matches lines to players, defense ranks, writes public/board.json
src/App.jsx                page state: filters, sorting, paging, export
src/lib/board.js           hit rates, streaks, projection, score
src/components/            filter bar, table, columns, expanded row, markets popover
public/board.json          generated data the site loads (git-ignored)
data/                      caches + gamelogs.csv (git-ignored)
```

`npm run build` makes a static copy of the site in `dist/` (it includes the current
`board.json` snapshot); `npm run preview` serves that build.
