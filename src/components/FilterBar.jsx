import { dateLabel } from "../lib/format";
import { Check, Dropdown } from "./Dropdown";

function Toggle({ checked, onChange, title, children }) {
  return (
    <label className="toggle" title={title}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <i />
      {children}
    </label>
  );
}

const toggleIn = (list, item, on) => (on ? [...list, item] : list.filter(x => x !== item));

export function FilterBar({ D, f, set, count }) {
  const byDate = [];
  for (const g of D.games) {
    if (byDate.at(-1)?.date !== g.date) byDate.push({ date: g.date, games: [] });
    byDate.at(-1).games.push(g);
  }
  return (
    <header className="bar">
      <div className="seg" role="group" aria-label="Side">
        {["over", "under"].map(s => (
          <button key={s} type="button" className={f.side === s ? "on" : ""} onClick={() => set.side(s)}>
            {s.toUpperCase()}
          </button>
        ))}
      </div>

      <input className="field" placeholder="Search Player" autoComplete="off"
        value={f.query} onChange={e => set.query(e.target.value)} />

      <Dropdown label="Categories" value={`${f.cats.length} selected`}>
        <div className="acts">
          <button type="button" className="linkbtn" onClick={() => set.cats(Object.keys(D.cats))}>All</button>
          <button type="button" className="linkbtn" onClick={() => set.cats([])}>None</button>
        </div>
        {Object.entries(D.cats).map(([k, label]) => (
          <Check key={k} checked={f.cats.includes(k)} onChange={on => set.cats(toggleIn(f.cats, k, on))}>{label}</Check>
        ))}
      </Dropdown>

      <Dropdown label="Games" value={D.games.length ? `${f.games.length} selected` : "none scheduled"}>
        {D.games.length ? (
          <>
            <div className="acts">
              <button type="button" className="linkbtn" onClick={() => set.games(D.games.map(g => g.id))}>All</button>
              <button type="button" className="linkbtn" onClick={() => set.games([])}>None</button>
            </div>
            {byDate.map(day => (
              <div key={day.date}>
                <div className="grp">
                  <span>{dateLabel(day.date)}</span>
                  <button type="button" className="linkbtn" onClick={() => set.games(day.games.map(g => g.id))}>only this day</button>
                </div>
                {day.games.map(g => (
                  <Check key={g.id} checked={f.games.includes(g.id)} hint={g.time}
                    onChange={on => set.games(toggleIn(f.games, g.id, on))}>
                    {g.away} @ {g.home}
                  </Check>
                ))}
              </div>
            ))}
          </>
        ) : (
          <div className="grp">No upcoming games in the schedule.</div>
        )}
      </Dropdown>

      <Toggle checked={f.alt} onChange={set.alt}>Show Alt Lines</Toggle>
      <Toggle checked={f.all} onChange={set.all}
        title="Add every rostered player in the selected games, using a model line where no book has one">
        All Players
      </Toggle>
      <span className="count">{count}</span>
    </header>
  );
}
