import { useEffect, useState } from "react";
import { BOOKS, isHit } from "../lib/board";
import { fmt1, fmtOdds } from "../lib/format";

function seasonAvg(D, r, idx) {
  const logs = D.logs[r.pid] || [], v = D.values(r.pid, r.cat);
  let sum = 0, n = 0;
  logs.forEach((g, i) => { if (g[3] === idx) { sum += v[i]; n++; } });
  return n ? `${fmt1(sum / n)} avg · ${n} gp` : "no games";
}

/** Last 20 games as bars against the line, oldest on the left. */
function GameChart({ D, r, side }) {
  const logs = (D.logs[r.pid] || []).slice(0, 20).reverse();
  const v = D.values(r.pid, r.cat).slice(0, 20).reverse();
  if (!v.length) return <div className="dim">No NBA games logged yet.</div>;
  const L = r.c.L, hit = isHit(side, L);
  const W = Math.max(520, v.length * 38), H = 170, top = 18, bottom = 34, bw = 26;
  const max = Math.max(L * 1.25, ...v, 1);
  const y = x => top + (H - top - bottom) * (1 - x / max);
  const step = (W - 40) / v.length;
  return (
    <svg className="chart" width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      {v.map((x, i) => {
        const g = logs[i], cx = 20 + i * step, yy = y(x);
        return (
          <g key={i}>
            <rect x={cx} y={yy} width={bw} height={Math.max(1, H - bottom - yy)} rx="3" fill={hit(x) ? "#2c9a4e" : "#c9434c"}>
              <title>{`${g[0]} ${g[2] ? "vs" : "@"} ${g[1]}: ${x} (${g[D.I.min]} min)`}</title>
            </rect>
            <text className="val" x={cx + bw / 2} y={yy - 4} textAnchor="middle">{x}</text>
            <text x={cx + bw / 2} y={H - bottom + 13} textAnchor="middle">{g[1]}</text>
            <text x={cx + bw / 2} y={H - bottom + 25} textAnchor="middle">{`${+g[0].slice(5, 7)}/${+g[0].slice(8)}`}</text>
          </g>
        );
      })}
      <line x1="10" x2={W - 10} y1={y(L)} y2={y(L)} stroke="#e7e9ee" strokeDasharray="4 4" opacity=".7" />
      <text x={W - 12} y={y(L) - 4} textAnchor="end">{L}</text>
    </svg>
  );
}

export function DetailRow({ D, r, side, colSpan, hasCustom, onLine }) {
  const P = D.players[r.pid];
  const [draft, setDraft] = useState(String(r.c.L));
  useEffect(() => setDraft(String(r.c.L)), [r.c.L]);
  const commit = () => {
    const x = parseFloat(draft);
    if (Number.isNaN(x)) setDraft(String(r.c.L));
    else if (x !== r.c.L) onLine(x);
  };
  const books = r.books.map(b => `${BOOKS[b.b] || b.b} ${fmtOdds(b.o)}/${fmtOdds(b.u)}`).join(" · ");
  return (
    <tr className="detail">
      <td colSpan={colSpan}>
        <div className="detail-head">
          <span><b>{P.n}</b> · {P.t} · {P.p} · {P.x ? `${P.x} yrs` : "Rookie"}</span>
          {D.last >= 0 && <span>{D.meta.seasons[D.last]}: <b>{seasonAvg(D, r, D.last)}</b></span>}
          <span>{D.meta.seasons[D.cur]}: <b>{seasonAvg(D, r, D.cur)}</b></span>
          {books && <span>{books}</span>}
          <label>
            Line{" "}
            <input type="number" step="0.5" value={draft} onChange={e => setDraft(e.target.value)}
              onBlur={commit} onKeyDown={e => e.key === "Enter" && commit()} />
          </label>
          {hasCustom && <button type="button" className="linkbtn" onClick={() => onLine(null)}>reset to {r.line}</button>}
        </div>
        <GameChart D={D} r={r} side={side} />
      </td>
    </tr>
  );
}
