import { useEffect, useState } from "react";

/** useState that remembers its value in localStorage (silently skips storage if it's blocked). */
export function usePersistentState(key, initial) {
  const storageKey = `nbaprops.${key}`;
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved == null ? initial : JSON.parse(saved);
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(value));
    } catch {
      /* private mode / storage disabled */
    }
  }, [storageKey, value]);
  return [value, setValue];
}
