import { useCallback, useEffect, useMemo, useState } from "react";
import { BOOKS, calcRow, favKey, modelRows, normalize, prepareBoard } from "./lib/board";
import { usePersistentState } from "./lib/usePersistentState";
import { ASCENDING_FIRST, getColumns } from "./components/columns";
import { Check, Dropdown } from "./components/Dropdown";
import { FilterBar } from "./components/FilterBar";
import { MarketsPopover } from "./components/MarketsPopover";
import { Pager } from "./components/Pager";
import { PropTable } from "./components/PropTable";

export default function App() {
  const [board, setBoard] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetch("/board.json", { cache: "no-store" })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(raw => setBoard(prepareBoard(raw)))
      .catch(setError);
  }, []);

  if (error) {
    return (
      <div className="empty">
        No data yet. Run <code>npm run update</code> (or <code>python update.py</code>) in this folder;
        the page reloads when it finishes.
      </div>
    );
  }
  if (!board) return <div className="empty">Loading board…</div>;
  return <Board D={board} />;
}

function downloadCsv(rows, columns, ctx, filename) {
  const cols = columns.filter(c => c.csv);
  const q = s => `"${String(s ?? "").replace(/"/g, '""')}"`;
  const lines = [cols.map(c => q(c.l)).join(","), ...rows.map(r => cols.map(c => q(c.csv(r, ctx))).join(","))];
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function Board({ D }) {
  const columns = useMemo(() => getColumns(D), [D]);
  const firstDate = useMemo(() => (D.games.find(g => g.date >= D.meta.today) || D.games[0])?.date, [D]);

  const [side, setSide] = useState("over");
  const [query, setQuery] = useState("");
  const [savedCats, setCats] = usePersistentState("cats", Object.keys(D.cats));
  const cats = useMemo(() => savedCats.filter(c => c in D.cats), [savedCats, D]);
  const [games, setGames] = useState(() => D.games.filter(g => g.date === firstDate).map(g => g.id));
  const [alt, setAlt] = useState(false);
  const [all, setAll] = useState(D.bookRows.length === 0);
  const [favOnly, setFavOnly] = useState(false);
  const [favList, setFavList] = usePersistentState("favs", []);
  const favs = useMemo(() => new Set(favList), [favList]);
  const [visible, setVisible] = usePersistentState("cols", columns.filter(c => !c.hidden).map(c => c.k));
  const [sort, setSort] = useState({ k: "score", dir: -1 });
  const [per, setPer] = usePersistentState("per", 100);
  const [page, setPage] = useState(0);
  const [openKey, setOpenKey] = useState(null);
  const [custom, setCustom] = useState({}); // row key -> user-entered line
  const [markets, setMarkets] = useState(null); // { row, rect }

  // Back to page 1 whenever the filters change.
  useEffect(() => setPage(0), [side, query, cats, games, alt, all, favOnly]);

  const rows = useMemo(() => {
    const gameSet = new Set(games), catSet = new Set(cats);
    const anyGames = D.games.length > 0;
    let out = D.bookRows.filter(r => (alt || r.main) && catSet.has(r.cat) && (!anyGames || gameSet.has(r.game)));
    if (all) out = out.concat(modelRows(D, gameSet, cats));
    const q = normalize(query.trim());
    if (q) out = out.filter(r => D.nameKey[r.pid].includes(q));
    if (favOnly) out = out.filter(r => favs.has(favKey(r)));
    out = out
      .map(r => calcRow(D, r, side, custom[r.key]))
      // Over-only markets (alt ladders, FanDuel DD/TD) can't be bet as unders, and vice versa.
      .filter(r => r.model || r.c.best);
    const col = columns.find(c => c.k === sort.k) ?? columns[1];
    const ctx = { side };
    return out
      .map(r => [col.sort(r, ctx), r])
      .sort(([x], [y]) => (x == null ? (y == null ? 0 : 1) : y == null ? -1 : (x < y ? -1 : x > y ? 1 : 0) * sort.dir))
      .map(([, r]) => r);
  }, [D, columns, side, query, cats, games, alt, all, favOnly, favs, custom, sort]);

  const pages = Math.max(1, Math.ceil(rows.length / per));
  const pageNow = Math.min(page, pages - 1);
  const pageRows = rows.slice(pageNow * per, (pageNow + 1) * per);

  // After a custom line re-sorts the table, jump to wherever the open row landed.
  useEffect(() => {
    if (!openKey) return;
    const i = rows.findIndex(r => r.key === openKey);
    if (i >= 0) setPage(Math.floor(i / per));
  }, [custom]);

  const onFav = useCallback(r => {
    const k = favKey(r);
    setFavList(list => (list.includes(k) ? list.filter(x => x !== k) : [...list, k]));
  }, [setFavList]);
  const onMarkets = useCallback((row, rect) => setMarkets({ row, rect }), []);
  const closeMarkets = useCallback(() => setMarkets(null), []);
  const onSort = k => setSort(s => (s.k === k ? { k, dir: -s.dir } : { k, dir: ASCENDING_FIRST.has(k) ? 1 : -1 }));
  const onLine = (key, x) => setCustom(c => {
    const next = { ...c };
    if (x == null) delete next[key];
    else next[key] = x;
    return next;
  });

  const shown = columns.filter(c => visible.includes(c.k));
  const ctx = { D, side, favs, custom, onFav, onMarkets };
  const books = [...new Set(D.props.flatMap(p => p.books.map(b => BOOKS[b.b] || b.b)))].join(", ") || "none";

  return (
    <>
      <FilterBar D={D}
        f={{ side, query, cats, games, alt, all }}
        set={{ side: setSide, query: setQuery, cats: setCats, games: setGames, alt: setAlt, all: setAll }}
        count={`${rows.length}/${D.bookRows.length}`} />

      <div className="tools">
        <Dropdown value="▥ COLUMNS">
          {columns.filter(c => c.l).map(c => (
            <Check key={c.k} checked={visible.includes(c.k)}
              onChange={on => setVisible(v => (on ? [...v, c.k] : v.filter(x => x !== c.k)))}>
              {c.l}
            </Check>
          ))}
        </Dropdown>
        <button type="button" onClick={() => downloadCsv(rows, shown, ctx, `nba-props-${side}-${D.meta.today}.csv`)}>
          ⤓ EXPORT
        </button>
        <button type="button" className={favOnly ? "on" : ""} onClick={() => setFavOnly(x => !x)}>♥ FAVORITES</button>
        <span className="meta">
          Updated {D.meta.updated} · stats: {D.meta.source} · {Object.keys(D.players).length} players · books: {books}
        </span>
      </div>

      <PropTable D={D} rows={pageRows} columns={shown} ctx={ctx} sort={sort} onSort={onSort}
        openKey={openKey} onOpen={k => setOpenKey(o => (o === k ? null : k))} onLine={onLine}
        onScroll={markets ? closeMarkets : undefined}
        emptyText={`No props match these filters.${D.games.length && !games.length ? " Pick a game." : ""}`} />

      <Pager page={pageNow} pages={pages} per={per} total={rows.length}
        onPage={p => { setPage(p); document.querySelector(".wrap")?.scrollTo(0, 0); }}
        onPer={n => { setPer(n); setPage(0); }} />

      {markets && <MarketsPopover row={markets.row} rect={markets.rect} side={side} onClose={closeMarkets} />}
    </>
  );
}
