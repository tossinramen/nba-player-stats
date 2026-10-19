import { favKey } from "../lib/board";
import { fmt1, fmtOdds, gameText, pctText } from "../lib/format";
import { HeatCell, MatchupCell, ScoreRing } from "./cells";

// Each column: k (id), l (header), td(row, ctx) -> <td>, sort(row, ctx) -> value, csv(row, ctx) -> text.
// ctx = { D, side, favs, custom, onFav, onMarkets }

const sideChar = side => (side === "over" ? "o" : "u");
const beats = (x, L, side) => (side === "over" ? x > L : x < L);
const lineClass = (x, L, side) => (x == null ? "dim" : beats(x, L, side) ? "pos" : "neg");

function heatColumn(k, l, pick) {
  return { k, l, sort: r => pick(r).p, csv: r => pctText(pick(r)), td: r => <HeatCell a={pick(r)} /> };
}

export function getColumns(D) {
  const P = r => D.players[r.pid];
  return [
    {
      k: "fav", l: "", nosort: true,
      td: (r, x) => {
        const on = x.favs.has(favKey(r));
        return (
          <td>
            <button type="button" className={`heart${on ? " on" : ""}`} title="Favorite"
              onClick={e => { e.stopPropagation(); x.onFav(r); }}>{on ? "♥" : "♡"}</button>
          </td>
        );
      },
    },
    { k: "score", l: "Score", sort: r => r.c.score, csv: r => r.c.score, td: r => <td><ScoreRing score={r.c.score} /></td> },
    { k: "team", l: "Team", sort: r => P(r).t, csv: r => P(r).t, td: r => <td>{P(r).t}</td> },
    { k: "pos", l: "Pos", sort: r => P(r).p, csv: r => P(r).p, td: r => <td>{P(r).p}</td> },
    {
      k: "exp", l: "Exp", title: "Years in the NBA (R = rookie)",
      sort: r => P(r).x, csv: r => P(r).x || "R", td: r => <td>{P(r).x || "R"}</td>,
    },
    {
      k: "player", l: "Player", sort: r => P(r).n, csv: r => P(r).n,
      td: r => (
        <td className="l">
          <div className="player">
            {P(r).img && <img src={P(r).img} loading="lazy" alt="" onError={e => (e.currentTarget.style.visibility = "hidden")} />}
            <span>{P(r).n}</span>
          </div>
        </td>
      ),
    },
    {
      k: "prop", l: "Prop", sort: r => D.cats[r.cat] + r.c.L,
      csv: (r, x) => `${sideChar(x.side)}${r.c.L} ${D.cats[r.cat]}`,
      td: (r, x) => (
        <td className="l">
          {sideChar(x.side)}{r.c.L} {D.cats[r.cat]}
          {r.model ? <span className="tag model" title="No book line: line = recent average rounded to x.5">MODEL</span>
            : !r.main && <span className="tag alt">ALT</span>}
          {r.key in x.custom && <span className="tag alt">CUSTOM</span>}
        </td>
      ),
    },
    {
      k: "l10avg", l: "L10 Avg", sort: r => r.c.l10avg, csv: r => fmt1(r.c.l10avg),
      td: (r, x) => <td className={lineClass(r.c.l10avg, r.c.L, x.side)}>{fmt1(r.c.l10avg)}</td>,
    },
    {
      k: "l5avg", l: "L5 Avg", sort: r => r.c.l5avg, csv: r => fmt1(r.c.l5avg),
      td: (r, x) => <td className={lineClass(r.c.l5avg, r.c.L, x.side)}>{fmt1(r.c.l5avg)}</td>,
    },
    {
      k: "proj", l: "Projection", sort: r => (r.c.proj == null ? null : r.c.proj - r.c.L), csv: r => fmt1(r.c.proj),
      td: (r, x) => {
        const p = r.c.proj;
        if (p == null) return <td className="dim">—</td>;
        const d = p - r.c.L;
        return <td className="proj">{fmt1(p)}<small className={lineClass(p, r.c.L, x.side)}>{d >= 0 ? "+" : ""}{fmt1(d)}</small></td>;
      },
    },
    {
      k: "odds", l: "Odds", sort: r => r.c.best?.o, csv: r => (r.c.best ? `${fmtOdds(r.c.best.o)} ${r.c.best.b}` : ""),
      td: (r, x) => r.books.length ? (
        <td>
          <span className="odds" role="button" tabIndex={0}
            onClick={e => { e.stopPropagation(); x.onMarkets(r, e.currentTarget.getBoundingClientRect()); }}>
            <b>{fmtOdds(r.c.best?.o)}</b>
            <span className="bk">{r.c.best ? r.c.best.b : r.books[0].b}</span>▾
          </span>
        </td>
      ) : <td className="dim">—</td>,
    },
    { k: "streak", l: "Streak", sort: r => r.c.streak, csv: r => r.c.streak, td: r => <td>{r.c.streak}</td> },
    {
      k: "matchup", l: "Matchup",
      sort: (r, x) => (r.c.rank == null ? null : x.side === "over" ? r.c.rank : 31 - r.c.rank),
      csv: r => `${r.opp} ${r.c.rank ?? ""}`.trim(),
      td: (r, x) => <MatchupCell D={D} r={r} side={x.side} />,
    },
    ...(D.last >= 0 ? [heatColumn("sLast", D.meta.seasons[D.last], r => r.c.sLast)] : []),
    heatColumn("sCur", D.meta.seasons[D.cur], r => r.c.sCur),
    heatColumn("h2h", "H2H", r => r.c.h2h),
    heatColumn("l5", "L5", r => r.c.l5),
    heatColumn("l10", "L10", r => r.c.l10),
    heatColumn("l20", "L20", r => r.c.l20),
    {
      k: "game", l: "Game", hidden: true,
      sort: r => D.gamesById[r.game]?.tipoff, csv: r => gameText(D, r.game),
      td: r => <td className="dim">{gameText(D, r.game)}</td>,
    },
  ];
}

export const ASCENDING_FIRST = new Set(["team", "pos", "player", "prop", "game"]);
