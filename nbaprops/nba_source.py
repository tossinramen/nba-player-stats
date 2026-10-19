"""Primary data source: stats.nba.com via nba_api."""
import time
from datetime import datetime, timedelta

import pandas as pd
from nba_api.stats.endpoints import leaguegamelog, playerindex, scheduleleaguev2

from . import config

TIMEOUT = 60


def _call(fn, tries=3):
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # stats.nba.com times out / resets fairly often
            if attempt == tries - 1:
                raise
            wait = 5 * (attempt + 1)
            print(f"  nba_api error ({type(e).__name__}), retrying in {wait}s...")
            time.sleep(wait)


def _season_start_year(season):
    return int(season[:4])


def get_players(season):
    """Everyone currently on an NBA roster for `season`."""
    df = _call(lambda: playerindex.PlayerIndex(season=season, timeout=TIMEOUT).get_data_frames()[0])
    df = df[df.ROSTER_STATUS == 1]
    start = _season_start_year(season)
    return pd.DataFrame({
        "player_id": df.PERSON_ID.astype(str),
        "name": (df.PLAYER_FIRST_NAME + " " + df.PLAYER_LAST_NAME).str.strip(),
        "team": df.TEAM_ABBREVIATION,
        "pos": df.POSITION.fillna(""),
        "exp": (start - pd.to_numeric(df.FROM_YEAR, errors="coerce")).fillna(0).astype(int),
        "headshot": "https://cdn.nba.com/headshots/nba/latest/260x190/" + df.PERSON_ID.astype(str) + ".png",
    }).reset_index(drop=True)


def get_positions(seasons):
    """player_id -> position for everyone who appeared on a roster in `seasons` (used for defense-vs-position)."""
    pos = {}
    for season in seasons:
        df = _call(lambda: playerindex.PlayerIndex(season=season, timeout=TIMEOUT).get_data_frames()[0])
        pos.update(dict(zip(df.PERSON_ID.astype(str), df.POSITION.fillna(""))))
        time.sleep(0.6)
    return pos


def get_game_logs(season):
    """Every player-game for `season` across regular season, play-in and playoffs."""
    frames = []
    for stype in config.SEASON_TYPES:
        df = _call(lambda: leaguegamelog.LeagueGameLog(
            season=season, player_or_team_abbreviation="P",
            season_type_all_star=stype, timeout=TIMEOUT).get_data_frames()[0])
        if len(df):
            df["SEASON_TYPE"] = stype
            frames.append(df)
        time.sleep(0.6)
    if not frames:
        return empty_logs()
    df = pd.concat(frames, ignore_index=True)
    away = df.MATCHUP.str.contains("@")
    out = pd.DataFrame({
        "player_id": df.PLAYER_ID.astype(str),
        "player_name": df.PLAYER_NAME,
        "team": df.TEAM_ABBREVIATION,
        "opp": df.MATCHUP.str.split(r" @ | vs\. ", regex=True).str[-1].str.strip(),
        "home": (~away).astype(int),
        "game_date": pd.to_datetime(df.GAME_DATE).dt.strftime("%Y-%m-%d"),
        "game_id": df.GAME_ID.astype(str),
        "season": season,
        "season_type": df.SEASON_TYPE,
        "wl": df.WL.fillna(""),
        "min": pd.to_numeric(df.MIN, errors="coerce").fillna(0),
        "pts": df.PTS, "reb": df.REB, "ast": df.AST, "stl": df.STL, "blk": df.BLK,
        "tov": df.TOV, "fgm": df.FGM, "fga": df.FGA, "fg3m": df.FG3M, "fg3a": df.FG3A,
        "ftm": df.FTM, "fta": df.FTA, "oreb": df.OREB, "dreb": df.DREB,
    })
    return out


def empty_logs():
    cols = ["player_id", "player_name", "team", "opp", "home", "game_date", "game_id",
            "season", "season_type", "wl"] + config.STAT_FIELDS
    return pd.DataFrame(columns=cols)


def get_schedule(season, today, days=config.LOOKAHEAD_DAYS):
    """Games from `today` (ET date) through `today + days`."""
    df = _call(lambda: scheduleleaguev2.ScheduleLeagueV2(season=season, timeout=TIMEOUT).get_data_frames()[0])
    end = today + timedelta(days=days)
    games = []
    for _, g in df.iterrows():
        tipoff_utc = datetime.fromisoformat(g.gameDateTimeUTC.replace("Z", "+00:00"))
        et = tipoff_utc.astimezone(config.ET)
        if not (today <= et.date() <= end):
            continue
        if not g.homeTeam_teamTricode or not g.awayTeam_teamTricode:
            continue  # TBD playoff / cup slots
        if g.homeTeam_teamTricode not in config.NBA_TEAMS:
            continue  # preseason games vs. international clubs
        games.append({
            "date": et.date().isoformat(),
            "time": et.strftime("%I:%M %p").lstrip("0"),
            "tipoff": tipoff_utc.isoformat(),
            "home": g.homeTeam_teamTricode,
            "away": g.awayTeam_teamTricode,
            "status": g.gameStatusText,
        })
    return games
