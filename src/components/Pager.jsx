export function Pager({ page, pages, per, total, onPage, onPer }) {
  const start = page * per;
  return (
    <footer className="pager">
      <label>
        Rows per page:{" "}
        <select value={per} onChange={e => onPer(+e.target.value)}>
          {[50, 100, 250, 500].map(n => <option key={n}>{n}</option>)}
        </select>
      </label>
      <span>{total ? `${start + 1}–${Math.min(start + per, total)} of ${total}` : "0 of 0"}</span>
      <button type="button" disabled={page === 0} onClick={() => onPage(page - 1)} aria-label="Previous page">‹</button>
      <button type="button" disabled={page >= pages - 1} onClick={() => onPage(page + 1)} aria-label="Next page">›</button>
    </footer>
  );
}
