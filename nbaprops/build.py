"""Turn players + game logs + schedule + book offers into data/board.js for index.html."""
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime

import pandas as pd

from . import config

POS_GROUPS = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C"}


def pos_group(pos):
    return POS_GROUPS.get((pos or "").split("-")[0].strip().upper(), "")


def norm_name(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'’]", "", s).replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return config.NAME_ALIASES.get(s, s)


def et_date(iso_utc):
    return datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).astimezone(config.ET).date().isoformat()


class PlayerMatcher:
    def __init__(self, players):
        self.by_name = defaultdict(list)
        self.by_last = defaultdict(list)
        for p in players.itertuples():
            key = norm_name(p.name)
            self.by_name[key].append(p)
            parts = key.split(" ")
            self.by_last[(parts[-1], parts[0][:1])].append(p)

    def match(self, name, teams):
        key = norm_name(name)
        cands = self.by_name.get(key, [])
        if not cands:
            parts = key.split(" ")
            cands = [p for p in self.by_last.get((parts[-1], parts[0][:1]), []) if p.team in teams]
        if len(cands) > 1:
            cands = [p for p in cands if p.team in teams] or cands
        return cands[0] if len(cands) == 1 else None


def build_games(schedule, offers):
    """Schedule games plus any game a book lists that the schedule didn't have."""
    games = {}
    for g in schedule:
        games[f"{g['date']}_{g['away']}_{g['home']}"] = g
    for o in offers:
        d = et_date(o["tipoff"])
        key = f"{d}_{o['away']}_{o['home']}"
        if key not in games:
            t = datetime.fromisoformat(o["tipoff"].replace("Z", "+00:00")).astimezone(config.ET)
            games[key] = {"date": d, "time": t.strftime("%I:%M %p").lstrip("0"), "tipoff": o["tipoff"],
                          "home": o["home"], "away": o["away"], "status": ""}
    out = [{"id": k, **g} for k, g in games.items()]
    return sorted(out, key=lambda g: (g["tipoff"], g["id"]))


def build_props(offers, players, matcher):
    """Group book offers into one row per (player, category, line)."""
    rows, unmatched, ud_pos = {}, set(), {}
    team_of = dict(zip(players.player_id, players.team))
    for o in offers:
        p = matcher.match(o["name"], {o["away"], o["home"]})
        if p is None:
            unmatched.add(f"{o['name']} ({o['away']} @ {o['home']})")
            continue
        team = team_of[p.player_id]
        if team == o["home"]:
            opp = o["away"]
        elif team == o["away"]:
            opp = o["home"]
        else:
            unmatched.add(f"{o['name']} (roster says {team}, book says {o['away']} @ {o['home']})")
            continue
        if o["pos"]:
            ud_pos[p.player_id] = o["pos"]
        game = f"{et_date(o['tipoff'])}_{o['away']}_{o['home']}"
        key = (p.player_id, o["cat"], o["line"], game)
        row = rows.setdefault(key, {"pid": p.player_id, "cat": o["cat"], "line": o["line"],
                                    "game": game, "opp": opp, "main": False, "books": {}})
        row["main"] = row["main"] or o["main"]
        prev = row["books"].get(o["book"])
        # Prefer a book's main market over its alt/milestone market at the same line.
        if prev is None or (o["main"] and not prev["main"]):
            row["books"][o["book"]] = {"o": o["over"], "u": o["under"], "main": o["main"]}
    props = []
    for r in rows.values():
        r["books"] = [{"b": b, "o": v["o"], "u": v["u"]} for b, v in sorted(r["books"].items())]
        props.append(r)
    return props, sorted(unmatched), ud_pos


def defense_ranks(logs, positions):
    """Per opponent and position group: stat allowed per game and its rank (1 = allows the least)."""
    df = logs[logs.season_type == "Regular Season"].copy()
    cur = df[df.season == config.CURRENT_SEASON]
    gp = cur.groupby("opp").game_id.nunique()
    if len(gp) == 30 and gp.min() >= config.DEF_MIN_CURRENT_GAMES:
        df = cur
    else:
        df = df[df.season.isin(config.SEASONS[-2:])]
    df["pg"] = df.player_id.map(positions).map(pos_group)
    df = df[df.pg != ""]
    if df.empty:
        return {}, {}
    vals = pd.DataFrame(config.category_values(df))
    vals["opp"], vals["pg"] = df.opp.values, df.pg.values
    games = df.groupby("opp").game_id.nunique()
    allowed = vals.groupby(["opp", "pg"]).sum().div(games, axis=0, level="opp")
    ranks = allowed.groupby(level="pg").rank(method="min").astype(int)
    league = allowed.groupby(level="pg").mean()
    defense = defaultdict(dict)
    for (team, pg), row in allowed.iterrows():
        defense[team][pg] = {c: [int(ranks.loc[(team, pg), c]), round(float(row[c]), 2)] for c in config.CATEGORIES}
    league_avg = {pg: {c: round(float(league.loc[pg, c]), 2) for c in config.CATEGORIES} for pg in league.index}
    return dict(defense), league_avg


def compact_logs(logs, player_ids):
    seasons = {s: i for i, s in enumerate(config.SEASONS)}
    types = {t: i for i, t in enumerate(config.SEASON_TYPES)}
    df = logs[logs.player_id.isin(player_ids)].sort_values("game_date", ascending=False)
    out = defaultdict(list)
    for r in df.itertuples(index=False):
        row = [r.game_date, r.opp, int(r.home), seasons.get(r.season, -1), types.get(r.season_type, 0), r.wl]
        row += [_num(getattr(r, f)) for f in config.STAT_FIELDS]
        out[r.player_id].append(row)
    return dict(out)


def _num(v):
    v = float(v)
    return int(v) if v.is_integer() else round(v, 1)


def write_board(path, *, players, logs, positions, schedule, offers, source, ud_pos_cache):
    matcher = PlayerMatcher(players)
    games = build_games(schedule, offers)
    props, unmatched, ud_pos = build_props(offers, players, matcher)
    ud_pos_cache.update(ud_pos)
    defense, league = defense_ranks(logs, positions)

    pmap = {}
    for p in players.itertuples():
        pmap[p.player_id] = {
            "n": p.name, "t": p.team,
            "p": ud_pos_cache.get(p.player_id) or p.pos,
            "g": pos_group(p.pos) or pos_group(ud_pos_cache.get(p.player_id, "")),
            "x": int(p.exp), "img": p.headshot,
        }

    board = {
        "meta": {
            "updated": datetime.now(config.ET).strftime("%Y-%m-%d %I:%M %p ET"),
            "today": datetime.now(config.ET).date().isoformat(),
            "source": source, "seasons": config.SEASONS, "season_types": config.SEASON_TYPES,
            "current": config.CURRENT_SEASON, "stat_fields": config.STAT_FIELDS,
            "categories": config.CATEGORIES, "unmatched": unmatched,
        },
        "players": pmap,
        "logs": compact_logs(logs, set(pmap)),
        "games": games,
        "props": props,
        "defense": defense,
        "league": league,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(board, separators=(",", ":"))
    path.write_text(f"window.BOARD = {payload};\n", encoding="utf-8")
    return board
