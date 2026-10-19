// Data helpers for public/board.json (written by update.py).
// Each player's log is newest-first; a log row is
//   [date, opp, home, seasonIdx, typeIdx, wl, ...meta.stat_fields]

export const BOOKS = { FD: "FanDuel", UD: "Underdog" };

export const normalize = s => s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

export const favKey = r => `${r.pid}|${r.cat}`;

export function prepareBoard(raw) {
  const I = {};
  raw.meta.stat_fields.forEach((f, i) => (I[f] = i + 6));
  const doubles = g => (g[I.pts] >= 10) + (g[I.reb] >= 10) + (g[I.ast] >= 10) + (g[I.stl] >= 10) + (g[I.blk] >= 10);
  const catValue = {
    pts: g => g[I.pts], reb: g => g[I.reb], ast: g => g[I.ast], fg3m: g => g[I.fg3m],
    stl: g => g[I.stl], blk: g => g[I.blk], tov: g => g[I.tov],
    pra: g => g[I.pts] + g[I.reb] + g[I.ast], pr: g => g[I.pts] + g[I.reb],
    pa: g => g[I.pts] + g[I.ast], ra: g => g[I.reb] + g[I.ast], stocks: g => g[I.stl] + g[I.blk],
    fgm: g => g[I.fgm], fga: g => g[I.fga], fg3a: g => g[I.fg3a], ftm: g => g[I.ftm],
    dd: g => (doubles(g) >= 2 ? 1 : 0), td: g => (doubles(g) >= 3 ? 1 : 0),
  };

  const cache = new Map();
  const values = (pid, cat) => {
    const k = `${pid}|${cat}`;
    if (!cache.has(k)) cache.set(k, (raw.logs[pid] || []).map(catValue[cat]));
    return cache.get(k);
  };

  const bookRows = raw.props.map(p => ({ ...p, key: `${p.pid}|${p.cat}|${p.line}|${p.game}`, model: false }));
  return {
    ...raw,
    I,
    values,
    bookRows,
    cats: raw.meta.categories,
    cur: raw.meta.seasons.length - 1,
    last: raw.meta.seasons.length - 2,
    gamesById: Object.fromEntries(raw.games.map(g => [g.id, g])),
    nameKey: Object.fromEntries(Object.entries(raw.players).map(([id, p]) => [id, normalize(p.n)])),
    mainLines: new Set(bookRows.filter(r => r.main).map(r => `${r.pid}|${r.cat}|${r.game}`)),
  };
}

/** Recency-weighted mean of the last 30 games (each game counts 0.9x the next newer one). */
export function recentMean(v) {
  let w = 1, sw = 0, s = 0;
  for (let i = 0; i < Math.min(v.length, 30); i++) { s += v[i] * w; sw += w; w *= 0.9; }
  return sw ? s / sw : null;
}

/** Rows for players in the selected games who have no main book line in a category. */
export function modelRows(D, gameIds, cats) {
  const byTeam = new Map();
  for (const g of D.games) {
    if (!gameIds.has(g.id)) continue;
    for (const [team, opp] of [[g.home, g.away], [g.away, g.home]]) {
      if (!byTeam.has(team)) byTeam.set(team, []);
      byTeam.get(team).push([g.id, opp]);
    }
  }
  const out = [];
  for (const [pid, p] of Object.entries(D.players)) {
    const slots = D.games.length ? byTeam.get(p.t) : [["", ""]];
    if (!slots) continue;
    for (const [game, opp] of slots) {
      for (const cat of cats) {
        if (D.mainLines.has(`${pid}|${cat}|${game}`)) continue;
        const v = D.values(pid, cat);
        if (!v.length) continue;
        const line = cat === "dd" || cat === "td" ? 0.5 : Math.floor(recentMean(v)) + 0.5;
        out.push({ pid, cat, line, game, opp, main: true, books: [], model: true, key: `${pid}|${cat}|${line}|${game}|m` });
      }
    }
  }
  return out;
}

export const isHit = (side, line) => (side === "over" ? x => x > line : x => x < line);

/** Hit rates, averages, projection, best odds and score for one row on one side. */
export function calcRow(D, r, side, customLine) {
  const P = D.players[r.pid], logs = D.logs[r.pid] || [], v = D.values(r.pid, r.cat);
  const L = customLine ?? r.line;
  const over = side === "over";
  const hit = isHit(side, L);
  const none = { h: 0, n: 0, p: null };
  const agg = (keep, limit = Infinity) => {
    let h = 0, n = 0;
    for (let i = 0; i < logs.length && n < limit; i++) {
      if (keep && !keep(logs[i])) continue;
      n++;
      if (hit(v[i])) h++;
    }
    return { h, n, p: n ? h / n : null };
  };
  const avg = k => {
    const s = v.slice(0, k);
    return s.length ? s.reduce((a, b) => a + b, 0) / s.length : null;
  };

  const c = {
    L,
    sLast: D.last >= 0 ? agg(g => g[3] === D.last) : none,
    sCur: agg(g => g[3] === D.cur),
    h2h: r.opp ? agg(g => g[1] === r.opp) : none,
    l5: agg(null, 5), l10: agg(null, 10), l20: agg(null, 20),
    l5avg: avg(5), l10avg: avg(10),
  };
  c.streak = 0;
  for (const x of v) { if (!hit(x)) break; c.streak++; }

  // Projection: recency-weighted average nudged by what this opponent allows to the position.
  const d = r.opp && P.g ? D.defense[r.opp]?.[P.g]?.[r.cat] : null;
  const lg = P.g ? D.league[P.g]?.[r.cat] : null;
  c.rank = d ? d[0] : null;
  c.allowed = d ? d[1] : null;
  c.proj = recentMean(v);
  if (c.proj != null && d && lg) c.proj *= 1 + (Math.min(1.15, Math.max(0.85, d[1] / lg)) - 1) * 0.5;

  // Best price for the chosen side across books (higher American odds pay more).
  c.best = null;
  for (const b of r.books) {
    const o = over ? b.o : b.u;
    if (o != null && (c.best == null || o > c.best.o)) c.best = { o, b: b.b };
  }

  // Score 0-100: hit rates (small samples count less) + matchup + projection edge.
  const parts = [[c.sLast, 0.1, 10], [c.sCur, 0.15, 10], [c.h2h, 0.1, 3], [c.l5, 0.2, 5], [c.l10, 0.2, 10], [c.l20, 0.15, 20]];
  let s = 0, w = 0;
  for (const [a, wt, full] of parts) {
    if (!a.n) continue;
    const ww = wt * Math.min(1, a.n / full);
    s += a.p * ww;
    w += ww;
  }
  if (c.rank) {
    const m = (c.rank - 1) / 29;
    s += (over ? m : 1 - m) * 0.1;
    w += 0.1;
  }
  if (c.proj != null) {
    const edge = ((c.proj - L) / Math.max(1, L)) * (over ? 1 : -1);
    s += Math.min(1, Math.max(0, 0.5 + edge)) * 0.1;
    w += 0.1;
  }
  c.score = w ? Math.round((100 * s) / w) : null;
  return { ...r, c };
}
