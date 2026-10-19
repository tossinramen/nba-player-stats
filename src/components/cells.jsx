const heatColor = p =>
  p == null ? "var(--none)" : p >= 0.8 ? "var(--g3)" : p >= 0.6 ? "var(--g2)" : p >= 0.5 ? "var(--g1)" : p >= 0.4 ? "var(--r1)" : "var(--r2)";

export function HeatCell({ a }) {
  return (
    <td className="heat" style={{ background: heatColor(a.p) }}>
      {a.n ? (
        <>
          <b>{Math.round(a.p * 100)}%</b>
          <small>{a.h}/{a.n}</small>
        </>
      ) : (
        <b className="dim">—</b>
      )}
    </td>
  );
}

export function ScoreRing({ score }) {
  if (score == null) return "—";
  const color = score >= 70 ? "#3fbf68" : score >= 60 ? "#e0b030" : "#d0505a";
  return (
    <svg className="ring" width="32" height="32" viewBox="0 0 36 36" role="img" aria-label={`Score ${score}`}>
      <circle cx="18" cy="18" r="15" fill="none" stroke="#2a2e37" strokeWidth="3" />
      <circle cx="18" cy="18" r="15" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round"
        strokeDasharray={`${(score / 100) * 94.25} 94.25`} transform="rotate(-90 18 18)" />
      <text x="18" y="22" textAnchor="middle">{score}</text>
    </svg>
  );
}

const GROUP_NAME = { G: "guards", F: "forwards", C: "centers" };

export function MatchupCell({ D, r, side }) {
  if (!r.opp) return <td className="mu" style={{ background: "var(--none)" }}><b className="dim">—</b></td>;
  const { rank, allowed } = r.c;
  const g = D.gamesById[r.game];
  const at = g && g.home === r.opp ? "@ " : "vs ";
  let bg = "var(--none)";
  if (rank) {
    const good = side === "over" ? rank >= 21 : rank <= 10;
    const bad = side === "over" ? rank <= 10 : rank >= 21;
    bg = good ? "var(--g2)" : bad ? "var(--r1)" : "var(--gold)";
  }
  const tip = rank
    ? `${r.opp} allows ${allowed} ${D.cats[r.cat]} per game to ${GROUP_NAME[D.players[r.pid].g]} (rank ${rank}/30, 30 = most allowed)`
    : "";
  return (
    <td className="mu" style={{ background: bg }} title={tip}>
      <b>{at}{r.opp}</b>
      <small>{rank ? `Rank ${rank}` : ""}</small>
    </td>
  );
}
