"""Daily refresh: pulls rosters, every game log, schedule and prop lines, then
rebuilds data/board.js for index.html.

    python update.py                  # nba_api, falls back to Basketball-Reference if it fails
    python update.py --source bbref   # force the Basketball-Reference (pydoll) scraper
    python update.py --no-props       # skip sportsbook lines
    python update.py --refresh        # also re-download cached past seasons
    python update.py --open           # open the board in your browser when done
"""
import argparse
import json
import sys
import time
import webbrowser
from datetime import datetime

import pandas as pd

from nbaprops import books, build, config, nba_source

BOARD_JS = config.DATA_DIR / "board.js"
POS_CACHE = config.CACHE_DIR / "positions.json"


def load_nba(refresh):
    print(f"Rosters ({config.CURRENT_SEASON}) from nba_api...")
    players = nba_source.get_players(config.CURRENT_SEASON)
    print(f"  {len(players)} players on {players.team.nunique()} teams")

    frames = []
    for season in config.SEASONS:
        cache = config.CACHE_DIR / f"nba_logs_{season}.csv"
        if season != config.CURRENT_SEASON and cache.exists() and not refresh:
            df = pd.read_csv(cache, dtype={"player_id": str, "game_id": str})
            print(f"Game logs {season}: {len(df)} player-games (cached)")
        else:
            df = nba_source.get_game_logs(season)
            print(f"Game logs {season}: {len(df)} player-games")
            if season != config.CURRENT_SEASON and len(df):
                cache.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(cache, index=False)
        frames.append(df)
    logs = pd.concat([f for f in frames if len(f)], ignore_index=True)
    positions = nba_source.get_positions(config.SEASONS)
    return players, logs, positions


def load_bbref():
    from nbaprops import bbref_source
    print("Scraping Basketball-Reference with pydoll (this takes a while; cached pages are skipped)...")
    players, logs = bbref_source.get_players_and_logs()
    print(f"  {len(players)} players, {len(logs)} player-games")
    positions = dict(zip(players.player_id, players.pos))
    return players, logs, positions


def main():
    sys.stdout.reconfigure(errors="replace")  # Windows consoles choke on accented names
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["auto", "nba", "bbref"], default="auto")
    ap.add_argument("--no-props", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    source = "nba_api"
    if args.source == "bbref":
        players, logs, positions = load_bbref()
        source = "basketball-reference"
    else:
        try:
            players, logs, positions = load_nba(args.refresh)
        except Exception as e:
            if args.source == "nba":
                raise
            print(f"nba_api failed ({type(e).__name__}: {e}); switching to Basketball-Reference.")
            players, logs, positions = load_bbref()
            source = "basketball-reference"

    today = datetime.now(config.ET).date()
    try:
        schedule = nba_source.get_schedule(config.CURRENT_SEASON, today)
        print(f"Schedule: {len(schedule)} games in the next {config.LOOKAHEAD_DAYS} days")
    except Exception as e:
        print(f"Schedule unavailable ({type(e).__name__}); using the books' game list instead.")
        schedule = []

    offers = []
    if not args.no_props:
        print("Prop lines...")
        offers = books.fetch_all()

    pos_cache = json.loads(POS_CACHE.read_text()) if POS_CACHE.exists() else {}
    board = build.write_board(BOARD_JS, players=players, logs=logs, positions=positions,
                              schedule=schedule, offers=offers, source=source, ud_pos_cache=pos_cache)
    POS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    POS_CACHE.write_text(json.dumps(pos_cache))
    logs.sort_values(["game_date", "player_name"]).to_csv(config.DATA_DIR / "gamelogs.csv", index=False)

    print(f"\nBoard: {len(board['players'])} players, {len(board['props'])} prop lines, "
          f"{len(board['games'])} games -> {BOARD_JS.relative_to(config.ROOT)}")
    print(f"All game logs -> data/gamelogs.csv")
    if board["meta"]["unmatched"]:
        print(f"{len(board['meta']['unmatched'])} book names didn't match a roster player "
              f"(add fixes to NAME_ALIASES in nbaprops/config.py):")
        for n in board["meta"]["unmatched"][:15]:
            print("   ", n)
    print(f"Done in {time.time() - t0:.0f}s. Open index.html to view.")
    if args.open:
        webbrowser.open((config.ROOT / "index.html").as_uri())


if __name__ == "__main__":
    main()
