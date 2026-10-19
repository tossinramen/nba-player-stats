"""Player prop lines + odds from Underdog and FanDuel.

Both are the unofficial JSON feeds their own websites use (no API key). They can
change without notice; if one breaks, update.py keeps going with the other.

Every offer is normalized to:
  {book, name, cat, line, over, under, main, away, home, tipoff, pos}
`over`/`under` are American odds (int) or None, `main` is False for alt lines.
"""
import re
import time
from datetime import datetime, timedelta, timezone

import requests
from nba_api.stats.static import teams as nba_teams

from . import config

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "application/json"})

# Nickname ("Celtics") -> tricode, for books that use full team names.
NICKNAMES = {t["nickname"]: t["abbreviation"] for t in nba_teams.get_teams()}


def team_from_name(full_name):
    for nick, code in NICKNAMES.items():
        if full_name.strip().endswith(nick):
            return code
    return None


def _american(v):
    if v in (None, ""):
        return None
    try:
        return int(str(v).replace("+", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------- Underdog
UD_URL = "https://api.underdogfantasy.com/v1/over_under_lines"
UD_STATS = {
    "points": "pts", "rebounds": "reb", "assists": "ast", "three_points_made": "fg3m",
    "steals": "stl", "blocks": "blk", "turnovers": "tov", "pts_rebs_asts": "pra",
    "pts_rebs": "pr", "pts_asts": "pa", "rebs_asts": "ra", "blks_stls": "stocks",
    "field_goals_made": "fgm", "field_goals_att": "fga", "three_points_att": "fg3a",
    "free_throws_made": "ftm", "double_doubles": "dd", "triple_doubles": "td",
}


def underdog():
    d = SESSION.get(UD_URL, timeout=60).json()
    players = {p["id"]: p for p in d["players"] if p.get("sport_id") == "NBA"}
    games = {g["id"]: g for g in d["games"] if g.get("sport_id") == "NBA"}
    apps = {a["id"]: a for a in d["appearances"] if a["player_id"] in players}
    offers = []
    for line in d["over_under_lines"]:
        stat = line["over_under"]["appearance_stat"]
        app = apps.get(stat["appearance_id"])
        cat = UD_STATS.get(stat["stat"])
        if not app or not cat or line.get("status") != "active":
            continue
        game = games.get(app["match_id"])
        if not game or " @ " not in game["title"]:
            continue
        away, home = game["title"].split(" @ ")
        p = players[app["player_id"]]
        odds = {o["choice"]: _american(o.get("american_price")) for o in line["options"]}
        offers.append({
            "book": "UD", "name": f"{p['first_name']} {p['last_name']}", "cat": cat,
            "line": float(line["stat_value"]), "over": odds.get("higher"), "under": odds.get("lower"),
            "main": True, "away": away, "home": home,
            "tipoff": game["scheduled_at"], "pos": p.get("position_name") or "",
        })
    return offers


# ---------------------------------------------------------------- FanDuel
FD_BASE = "https://sbapi.nj.sportsbook.fanduel.com/api"
FD_KEY = "FhMFpcPWXMeyZxOx"  # public key embedded in sportsbook.fanduel.com
FD_TABS = ["player-points", "player-rebounds", "player-assists",
           "player-threes", "player-combos", "player-defense"]
FD_MAIN = {
    "TOTAL_POINTS": "pts", "TOTAL_REBOUNDS": "reb", "TOTAL_ASSISTS": "ast",
    "TOTAL_MADE_3_POINT_FIELD_GOALS": "fg3m", "TOTAL_STEALS": "stl", "TOTAL_BLOCKS": "blk",
    "TOTAL_TURNOVERS": "tov", "TOTAL_POINTS_+_REB_+_AST": "pra", "TOTAL_POINTS_+_REBOUNDS": "pr",
    "TOTAL_POINTS_+_ASSISTS": "pa", "TOTAL_REBOUNDS_+_ASSISTS": "ra",
    "TOTAL_STEALS_+_BLOCKS": "stocks",
}
FD_ALT = {
    "ALT_TOTAL_POINTS": "pts", "ALT_TOTAL_REBOUNDS": "reb", "ALT_TOTAL_ASSISTS": "ast",
    "ALT_TOTAL_PTS_+_REB_+_AST": "pra", "ALT_TOTAL_PTS_+_REB": "pr",
    "ALT_TOTAL_PTS_+_AST": "pa", "ALT_TOTAL_REB_+_AST": "ra",
}
# "N+" milestone markets: one runner per player, over-only, line N - 0.5.
FD_MILESTONE = {
    "POINTS": "pts", "REBOUNDS": "reb", "ASSISTS": "ast", "STEALS": "stl", "BLOCKS": "blk",
    "PTS_+_REB_+_AST": "pra", "PTS_+_REB": "pr", "PTS_+_AST": "pa", "REB_+_AST": "ra",
    "MADE_THREES": "fg3m",
}
MILESTONE_RE = re.compile(r"^(?:TO_SCORE_|TO_RECORD_)?(\d+)\+_(.+)$")


def _fd_get(path, **params):
    r = SESSION.get(f"{FD_BASE}/{path}", params={"_ak": FD_KEY, **params}, timeout=60)
    r.raise_for_status()
    return r.json()


def _fd_events(now):
    d = _fd_get("content-managed-page", page="CUSTOM", customPageId="nba", timezone="America/New_York")
    horizon = now + timedelta(days=config.LOOKAHEAD_DAYS + 1)
    events = []
    for e in d["attachments"]["events"].values():
        name = e["name"]
        if " @ " not in name or "(" in name:  # skip futures and virtual "NBA 2K" games
            continue
        away, home = (team_from_name(s) for s in name.split(" @ "))
        start = datetime.fromisoformat(e["openDate"].replace("Z", "+00:00"))
        if away and home and now < start < horizon:
            events.append({"id": e["eventId"], "away": away, "home": home, "tipoff": e["openDate"]})
    return events


def _odds(runner):
    try:
        return int(runner["winRunnerOdds"]["americanDisplayOdds"]["americanOdds"])
    except (KeyError, TypeError, ValueError):
        return None


def _fd_parse_market(m, ev):
    mtype = re.sub(r"^PLAYER_[A-Z]_", "", m["marketType"])
    runners = [r for r in m.get("runners", []) if r.get("runnerStatus") == "ACTIVE"]
    base = {"book": "FD", "away": ev["away"], "home": ev["home"], "tipoff": ev["tipoff"], "pos": ""}
    out = []
    if mtype in FD_MAIN:
        sides = {}
        for r in runners:
            mm = re.match(r"^(.*) (Over|Under)$", r["runnerName"])
            if mm:
                sides.setdefault((mm.group(1), r.get("handicap")), {})[mm.group(2)] = _odds(r)
        for (name, line), s in sides.items():
            out.append({**base, "name": name, "cat": FD_MAIN[mtype], "line": float(line),
                        "over": s.get("Over"), "under": s.get("Under"), "main": True})
    elif mtype in FD_ALT:
        for r in runners:
            mm = re.match(r"^(.*) Over ([\d.]+)$", r["runnerName"])
            if mm:
                out.append({**base, "name": mm.group(1), "cat": FD_ALT[mtype], "line": float(mm.group(2)),
                            "over": _odds(r), "under": None, "main": False})
    elif mtype in ("TO_RECORD_A_DOUBLE_DOUBLE", "TO_RECORD_A_TRIPLE_DOUBLE"):
        cat = "dd" if "DOUBLE_DOUBLE" in mtype else "td"
        for r in runners:
            out.append({**base, "name": r["runnerName"], "cat": cat, "line": 0.5,
                        "over": _odds(r), "under": None, "main": True})
    else:
        mm = MILESTONE_RE.match(mtype)
        if mm and mm.group(2) in FD_MILESTONE:
            for r in runners:
                out.append({**base, "name": r["runnerName"], "cat": FD_MILESTONE[mm.group(2)],
                            "line": int(mm.group(1)) - 0.5, "over": _odds(r), "under": None, "main": False})
    return out


def fanduel():
    now = datetime.now(timezone.utc)
    offers = []
    for ev in _fd_events(now):
        seen = set()
        for tab in FD_TABS:
            try:
                d = _fd_get("event-page", eventId=ev["id"], tab=tab)
            except requests.RequestException as e:
                print(f"  FanDuel {ev['away']}@{ev['home']} {tab}: {e}")
                continue
            for mid, m in d.get("attachments", {}).get("markets", {}).items():
                if mid in seen or m.get("marketStatus") != "OPEN" or m.get("eventId") != ev["id"]:
                    continue
                seen.add(mid)
                offers.extend(_fd_parse_market(m, ev))
            time.sleep(0.4)
        print(f"  FanDuel {ev['away']} @ {ev['home']}: done")
    return offers


def fetch_all():
    """All offers from every book that responds; failures are reported, not raised."""
    offers = []
    for name, fn in [("Underdog", underdog), ("FanDuel", fanduel)]:
        try:
            got = fn()
            print(f"  {name}: {len(got)} lines")
            offers.extend(got)
        except Exception as e:
            print(f"  {name} failed: {type(e).__name__}: {e}")
    return offers
