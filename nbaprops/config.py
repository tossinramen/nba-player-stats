"""Shared settings. Edit SEASONS to pull more (or fewer) seasons of history."""
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"

ET = ZoneInfo("America/New_York")

# Oldest first. The last entry is treated as the current season and is
# re-downloaded on every run; earlier seasons are cached after the first pull.
SEASONS = ["2025-26", "2026-27"]
CURRENT_SEASON = SEASONS[-1]

# nba_api season types to pull for every season.
SEASON_TYPES = ["Regular Season", "PlayIn", "Playoffs"]

# How many days ahead of today to list games / fetch props for.
LOOKAHEAD_DAYS = 3

# Defense-vs-position ranks use the current season once every team has played
# this many games; before that, last season's games are blended in.
DEF_MIN_CURRENT_GAMES = 10

# Raw box-score fields kept for every player-game (order matters: the front end
# reads logs positionally using this list, which is shipped in board.js).
STAT_FIELDS = ["min", "pts", "reb", "ast", "stl", "blk", "tov",
               "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb"]

# Prop categories. Keys must match CATS in index.html.
CATEGORIES = {
    "pts":    "Points",
    "reb":    "Rebounds",
    "ast":    "Assists",
    "fg3m":   "Three Pointers",
    "stl":    "Steals",
    "blk":    "Blocks",
    "tov":    "Turnovers",
    "pra":    "Pts + Reb + Ast",
    "pr":     "Pts + Reb",
    "pa":     "Pts + Ast",
    "ra":     "Reb + Ast",
    "stocks": "Blocks + Steals",
    "fgm":    "Field Goals Made",
    "fga":    "FG Attempted",
    "fg3a":   "3PT Attempted",
    "ftm":    "Free Throws Made",
    "dd":     "Double Double",
    "td":     "Triple Double",
}


def category_values(df):
    """Per-game value of every category for a DataFrame of player-games."""
    dd_count = sum((df[c] >= 10).astype(int) for c in ["pts", "reb", "ast", "stl", "blk"])
    return {
        "pts": df.pts, "reb": df.reb, "ast": df.ast, "fg3m": df.fg3m,
        "stl": df.stl, "blk": df.blk, "tov": df.tov,
        "pra": df.pts + df.reb + df.ast, "pr": df.pts + df.reb,
        "pa": df.pts + df.ast, "ra": df.reb + df.ast, "stocks": df.stl + df.blk,
        "fgm": df.fgm, "fga": df.fga, "fg3a": df.fg3a, "ftm": df.ftm,
        "dd": (dd_count >= 2).astype(int), "td": (dd_count >= 3).astype(int),
    }


# Name fixes for matching sportsbook names to NBA names (lowercase, no punctuation or
# Jr./III). Applied to both sides, so either spelling can be the key. Add entries here
# if update.py reports unmatched players.
NAME_ALIASES = {
    "nic claxton": "nicolas claxton",
    "herb jones": "herbert jones",
    "gg jackson": "gregory jackson",
    "cam johnson": "cameron johnson",
    "bub carrington": "carlton carrington",
    "moe wagner": "moritz wagner",
    "alex sarr": "alexandre sarr",
}

# Basketball-Reference uses a few different team codes.
BBREF_TO_NBA = {"BRK": "BKN", "CHO": "CHA", "PHO": "PHX"}
NBA_TO_BBREF = {v: k for k, v in BBREF_TO_NBA.items()}
NBA_TEAMS = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
             "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
             "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]
