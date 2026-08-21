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
    const move = (e: PointerEvent) => onMove(e.clientX, e.clientY);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    window.addEventListener("pointermove", move);
    return () => {
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      window.removeEventListener("pointermove", move);
    };
  }, [onMove]);

  const horizontal = axis === "horizontal";
  const nudge = (delta: number) => {
    setPct((prev) => Math.min(max, Math.max(min, prev + delta)));
  };

  return (
    <div
      ref={wrap}
      data-testid={testId}
      className={`flex h-full min-h-0 min-w-0 flex-1 ${horizontal ? "flex-row" : "flex-col"}`}
    >
      <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden" style={horizontal ? { width: `${pct}%` } : { height: `${pct}%` }}>
        {children[0]}
      </div>
      <button
        type="button"
        role="separator"
        aria-orientation={horizontal ? "vertical" : "horizontal"}
        aria-valuenow={Math.round(pct)}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuetext={`${Math.round(pct)} percent`}
        aria-label="Resize panels"
        data-testid={`${testId || "split"}-handle`}
        className={
          horizontal
            ? "w-1.5 shrink-0 cursor-col-resize bg-slate-200 hover:bg-teal-400"
            : "h-1.5 shrink-0 cursor-row-resize bg-slate-200 hover:bg-teal-400"
        }
        style={{ touchAction: "none" }}
        onPointerDown={(e) => {
          e.preventDefault();
          dragging.current = true;
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onKeyDown={(e) => {
          const step = e.shiftKey ? 5 : 2;
          if (e.key === "Escape") {
            e.preventDefault();
            dragging.current = false;
            return;
          }
          if (e.key === "Home") {
            e.preventDefault();
            setPct(min);
            return;
          }
          if (e.key === "End") {
            e.preventDefault();
            setPct(max);
            return;
          }
          if (horizontal && e.key === "ArrowLeft") {
            e.preventDefault();
            nudge(-step);
          } else if (horizontal && e.key === "ArrowRight") {
            e.preventDefault();
            nudge(step);
          } else if (!horizontal && e.key === "ArrowUp") {
            e.preventDefault();
            nudge(-step);
          } else if (!horizontal && e.key === "ArrowDown") {
            e.preventDefault();
            nudge(step);
          }
        }}
      />
      <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden">{children[1]}</div>
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
