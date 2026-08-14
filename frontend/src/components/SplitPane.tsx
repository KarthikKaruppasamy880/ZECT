import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

type SplitPaneProps = {
  axis: "horizontal" | "vertical";
  storageKey: string;
  initial: number;
  min?: number;
  max?: number;
  children: [ReactNode, ReactNode];
  testId?: string;
};

export default function SplitPane({
  axis,
  storageKey,
  initial,
  min = 16,
  max = 80,
  children,
  testId,
}: SplitPaneProps) {
  const [pct, setPct] = useState(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      const n = raw ? Number(raw) : initial;
      return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : initial;
    } catch {
      return initial;
    }
  });
  const dragging = useRef(false);
  const wrap = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, String(pct));
    } catch {
      /* ignore */
    }
  }, [pct, storageKey]);

  const onMove = useCallback(
    (clientX: number, clientY: number) => {
      const el = wrap.current;
      if (!el || !dragging.current) return;
      const box = el.getBoundingClientRect();
      const next =
        axis === "horizontal"
          ? ((clientX - box.left) / Math.max(1, box.width)) * 100
          : ((clientY - box.top) / Math.max(1, box.height)) * 100;
      setPct(Math.min(max, Math.max(min, next)));
    },
    [axis, max, min],
  );

  useEffect(() => {
    const up = () => {
      dragging.current = false;
    };
    const move = (e: MouseEvent) => onMove(e.clientX, e.clientY);
    window.addEventListener("mouseup", up);
    window.addEventListener("mousemove", move);
    return () => {
      window.removeEventListener("mouseup", up);
      window.removeEventListener("mousemove", move);
    };
  }, [onMove]);

  const horizontal = axis === "horizontal";
  return (
    <div
      ref={wrap}
      data-testid={testId}
      className={`flex min-h-0 min-w-0 flex-1 ${horizontal ? "flex-row" : "flex-col"}`}
    >
      <div className="min-h-0 min-w-0 overflow-hidden" style={horizontal ? { width: `${pct}%` } : { height: `${pct}%` }}>
        {children[0]}
      </div>
      <button
        type="button"
        aria-label="Resize panels"
        data-testid={`${testId || "split"}-handle`}
        className={
          horizontal
            ? "w-1.5 shrink-0 cursor-col-resize bg-slate-200 hover:bg-teal-400"
            : "h-1.5 shrink-0 cursor-row-resize bg-slate-200 hover:bg-teal-400"
        }
        onMouseDown={(e) => {
          e.preventDefault();
          dragging.current = true;
        }}
      />
      <div className="min-h-0 min-w-0 flex-1 overflow-hidden">{children[1]}</div>
    </div>
  );
}

export function resetSplitLayout(keys: string[]) {
  for (const key of keys) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  }
}
