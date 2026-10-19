export const fmtOdds = n => (n == null ? "—" : n > 0 ? `+${n}` : String(n));

export const fmt1 = n => (n == null ? "—" : (Math.round(n * 10) / 10).toFixed(1));

export const pctText = a => (a.n ? `${Math.round(a.p * 100)}% (${a.h}/${a.n})` : "");

const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** "2026-10-20" -> "Tue 10/20" */
export function dateLabel(d) {
  const [y, m, day] = d.split("-").map(Number);
  return `${DOW[new Date(y, m - 1, day).getDay()]} ${m}/${day}`;
}

export function gameText(D, id) {
  const g = D.gamesById[id];
  return g ? `${g.away} @ ${g.home} ${dateLabel(g.date)} ${g.time}` : "";
}
