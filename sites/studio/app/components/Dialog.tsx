"use client";

import { useEffect, useRef, type ReactNode } from "react";

export default function Dialog({ children, labelledBy, onClose, className = "", busy = false }: {
  children: ReactNode;
  labelledBy: string;
  onClose: () => void;
  className?: string;
  busy?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  const locked = useRef(busy);
  close.current = onClose;
  locked.current = busy;
  useEffect(() => {
    const origin = document.activeElement as HTMLElement | null;
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const node = panel.current;
    node?.querySelector<HTMLElement>("[data-dialog-focus], button")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !locked.current) { event.preventDefault(); close.current(); }
      if (event.key !== "Tab" || !node) return;
      const items = [...node.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex="0"]')]
        .filter((item) => !item.closest('[aria-hidden="true"], [hidden]'));
      const first = items[0];
      const last = items[items.length - 1];
      if (!first) { event.preventDefault(); node.focus(); return; }
      if (event.shiftKey && (document.activeElement === first || !node.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !node.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = before; document.removeEventListener("keydown", onKey); if (origin?.isConnected) origin.focus(); };
  }, []);
  return <div className="boj-dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <div ref={panel} role="dialog" aria-modal="true" aria-labelledby={labelledBy} tabIndex={-1} className={`boj-dialog ${className}`}>
      <button type="button" className="boj-dialog-close" onClick={onClose} disabled={busy} aria-label="Fermer la fenêtre">×</button>
      {children}
    </div>
  </div>;
}
