import { Fragment } from "react";
import { DetailRow } from "./DetailRow";

export function PropTable({ D, rows, columns, ctx, sort, onSort, openKey, onOpen, onLine, onScroll, emptyText }) {
  return (
    <div className="wrap" onScroll={onScroll}>
      <table>
        <thead>
          <tr>
            {columns.map(c => (
              <th key={c.k} title={c.title} className={c.nosort ? "nosort" : ""} onClick={() => !c.nosort && onSort(c.k)}>
                {c.l}
                {sort.k === c.k && <span className="arr">{sort.dir < 0 ? "↓" : "↑"}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={columns.length} className="empty">{emptyText}</td></tr>
          )}
          {rows.map(r => (
            <Fragment key={r.key}>
              <tr className={`row${openKey === r.key ? " open" : ""}`} onClick={() => onOpen(r.key)}>
                {columns.map(c => <Fragment key={c.k}>{c.td(r, ctx)}</Fragment>)}
              </tr>
              {openKey === r.key && (
                <DetailRow D={D} r={r} side={ctx.side} colSpan={columns.length}
                  hasCustom={r.key in ctx.custom} onLine={x => onLine(r.key, x)} />
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
