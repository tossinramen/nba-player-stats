"""Backup data source: Basketball-Reference scraped with pydoll (a real Chrome).

Walks every team page (e.g. /teams/BOS/2027.html) for the current roster, then
each player's gamelog page (e.g. /players/g/garzalu01/gamelog/2026/) for every
season in config.SEASONS. Basketball-Reference bans clients that make more than
20 requests a minute, so pages are spaced REQUEST_GAP seconds apart and cached:
past seasons are fetched once, the current season once per day.
"""
import asyncio
import json
import time
from datetime import date

import pandas as pd
from bs4 import BeautifulSoup, Comment

from . import config

BASE = "https://www.basketball-reference.com"
REQUEST_GAP = 3.5
CACHE = config.CACHE_DIR / "bbref"


def bbref_year(season):
    """'2025-26' -> 2026 (Basketball-Reference names seasons by their end year)."""
    return int(season[:4]) + 1


def _team(code):
    return config.BBREF_TO_NBA.get(code, code)


def _find_table(soup, ids):
    for tid in ids:
        t = soup.find("table", id=tid)
        if t is not None:
            return t
    # Some tables ship inside HTML comments until JS un-hides them.
    for c in soup.find_all(string=lambda s: isinstance(s, Comment) and "<table" in s):
        inner = BeautifulSoup(c, "lxml")
        for tid in ids:
            t = inner.find("table", id=tid)
            if t is not None:
                return t
    return None


def _cells(tr):
    return {c.get("data-stat"): c for c in tr.find_all(["th", "td"])}


def parse_roster(html):
    soup = BeautifulSoup(html, "lxml")
    table = _find_table(soup, ["roster"])
    if table is None:
        return []
    players = []
    for tr in table.tbody.find_all("tr"):
        c = _cells(tr)
        link = c.get("player") and c["player"].find("a")
        if not link:
            continue
        exp = c["years_experience"].get_text(strip=True) if "years_experience" in c else ""
        players.append({
            "player_id": link["href"].rsplit("/", 1)[-1].replace(".html", ""),
            "name": link.get_text(strip=True),
            "pos": c["pos"].get_text(strip=True) if "pos" in c else "",
            "exp": 0 if exp in ("R", "") else int(exp),
        })
    return players


def _num(c, key):
    v = c[key].get_text(strip=True) if key in c else ""
    try:
        return float(v)
    except ValueError:
        return 0.0


def _minutes(text):
    if ":" in text:
        m, s = text.split(":")
        return round(int(m) + int(s) / 60, 1)
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_gamelog(html, season):
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for stype, ids in [("Regular Season", ["player_game_log_reg", "pgl_basic"]),
                       ("Playoffs", ["player_game_log_post", "pgl_basic_playoffs"])]:
        table = _find_table(soup, ids)
        if table is None or table.tbody is None:
            continue
        for tr in table.tbody.find_all("tr"):
            if "thead" in (tr.get("class") or []):
                continue
            c = _cells(tr)
            if "mp" not in c or not c["mp"].get_text(strip=True):
                continue  # inactive / DNP
            get = lambda *keys: next((c[k].get_text(strip=True) for k in keys if k in c), "")
            gdate = get("date", "date_game")
            team, opp = _team(get("team_name_abbr", "team_id")), _team(get("opp_name_abbr", "opp_id"))
            if not gdate or not opp:
                continue
            rows.append({
                "team": team, "opp": opp,
                "home": 0 if get("game_location") == "@" else 1,
                "game_date": gdate,
                "game_id": f"{gdate}_{min(team, opp)}_{max(team, opp)}",
                "season": season, "season_type": stype,
                "wl": get("game_result")[:1],
                "min": _minutes(c["mp"].get_text(strip=True)),
                "pts": _num(c, "pts"), "reb": _num(c, "trb"), "ast": _num(c, "ast"),
                "stl": _num(c, "stl"), "blk": _num(c, "blk"), "tov": _num(c, "tov"),
                "fgm": _num(c, "fg"), "fga": _num(c, "fga"), "fg3m": _num(c, "fg3"),
                "fg3a": _num(c, "fg3a"), "ftm": _num(c, "ft"), "fta": _num(c, "fta"),
                "oreb": _num(c, "orb"), "dreb": _num(c, "drb"),
            })
    return rows


class _Browser:
    def __init__(self, tab):
        self.tab = tab
        self.last = 0.0

    async def html(self, url):
        gap = REQUEST_GAP - (time.time() - self.last)
        if gap > 0:
            await asyncio.sleep(gap)
        self.last = time.time()
        await self.tab.go_to(url, timeout=90)
        title = await self.tab.title
        if "Too Many Requests" in title or "429" in title:
            raise RuntimeError("Basketball-Reference rate limit hit; wait an hour before retrying.")
        if "Page Not Found" in title or "404" in title:
            return None
        return await self.tab.page_source


def _cached(path, fresh_today):
    """Cached JSON if present (and fetched today when fresh_today is set)."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if fresh_today and data.get("fetched") != date.today().isoformat():
        return None
    return data["rows"]


def _store(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched": date.today().isoformat(), "rows": rows}), encoding="utf-8")


async def _scrape(seasons, current):
    from pydoll.browser.chromium import Chrome
    from pydoll.browser.options import ChromiumOptions

    opts = ChromiumOptions()
    opts.headless = True
    opts.add_argument("--blink-settings=imagesEnabled=false")
    players, logs = [], []
    async with Chrome(options=opts) as chrome:
        br = _Browser(await chrome.start())

        cur_year = bbref_year(current)
        for i, team in enumerate(config.NBA_TEAMS, 1):
            path = CACHE / f"team_{team}_{cur_year}.json"
            roster = _cached(path, fresh_today=True)
            if roster is None:
                code = config.NBA_TO_BBREF.get(team, team)
                html = await br.html(f"{BASE}/teams/{code}/{cur_year}.html")
                roster = parse_roster(html) if html else []
                _store(path, roster)
            for p in roster:
                p["team"] = team
            players.extend(roster)
            print(f"  roster {i:2}/30 {team}: {len(roster)} players")

        for i, p in enumerate(players, 1):
            pid = p["player_id"]
            for season in seasons:
                yr = bbref_year(season)
                path = CACHE / f"log_{pid}_{yr}.json"
                rows = _cached(path, fresh_today=(season == current))
                if rows is None:
                    html = await br.html(f"{BASE}/players/{pid[0]}/{pid}/gamelog/{yr}/")
                    rows = parse_gamelog(html, season) if html else []
                    _store(path, rows)
                for r in rows:
                    r.update(player_id=pid, player_name=p["name"])
                logs.extend(rows)
            if i % 25 == 0 or i == len(players):
                print(f"  gamelogs {i}/{len(players)}")
    return players, logs


def get_players_and_logs(seasons=config.SEASONS, current=config.CURRENT_SEASON):
    players, logs = asyncio.run(_scrape(seasons, current))
    pdf = pd.DataFrame(players)
    # Two-way / injured lists can repeat a player; keep the first team seen.
    pdf = pdf.drop_duplicates("player_id").reset_index(drop=True)
    pdf["headshot"] = ""
    ldf = pd.DataFrame(logs)
    return pdf, ldf
