import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { BOOKS } from "../lib/board";
import { fmtOdds } from "../lib/format";

/** Every book's price for a row, anchored under the clicked odds button. */
export function MarketsPopover({ row, rect, side, onClose }) {
  const ref = useRef(null);
  const [left, setLeft] = useState(rect.left);
  useLayoutEffect(() => {
    setLeft(Math.max(8, Math.min(rect.left, window.innerWidth - ref.current.offsetWidth - 8)));
  }, [rect]);
  useEffect(() => {
    const onDown = e => { if (!ref.current?.contains(e.target)) onClose(); };
    const onKey = e => { if (e.key === "Escape") onClose(); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const over = side === "over";
  return (
    <div className="pop" ref={ref} style={{ left, top: rect.bottom + 4 }}>
      <table>
        <tbody>
          {row.books.map(b => (
            <tr key={b.b}>
              <td>{BOOKS[b.b] || b.b}</td>
              <td>{over ? "o" : "u"}{row.c.L}</td>
              <td className={row.c.best?.b === b.b ? "best" : ""}>{fmtOdds(over ? b.o : b.u)}</td>
              <td className="dim">{over ? "u" : "o"} {fmtOdds(over ? b.u : b.o)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
