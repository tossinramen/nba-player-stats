import { useEffect, useRef, useState } from "react";

/** Button that opens a menu; closes on outside click or Escape. */
export function Dropdown({ label, value, children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const onDown = e => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const onKey = e => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);
  return (
    <div className={`dd${open ? " open" : ""}`} ref={ref}>
      <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}>
        {label && <small>{label}</small>}
        <span>{value}</span>
      </button>
      {open && <div className="menu">{children}</div>}
    </div>
  );
}

export function Check({ checked, onChange, children, hint }) {
  return (
    <label>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
