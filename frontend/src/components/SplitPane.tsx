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
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(`${storageKey}:collapsed`) === "1";
    } catch {
      return false;
    }
  });
  const lastPct = useRef(pct);
  const dragging = useRef(false);
  const wrap = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, String(pct));
      localStorage.setItem(`${storageKey}:collapsed`, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [pct, storageKey, collapsed]);

  const onMove = useCallback(
    (clientX: number, clientY: number) => {
      const el = wrap.current;
      if (!el || !dragging.current) return;
      const box = el.getBoundingClientRect();
      const next =
        axis === "horizontal"
          ? ((clientX - box.left) / Math.max(1, box.width)) * 100
          : ((clientY - box.top) / Math.max(1, box.height)) * 100;
      const clamped = Math.min(max, Math.max(min, next));
      lastPct.current = clamped;
      setCollapsed(false);
      setPct(clamped);
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
    setCollapsed(false);
    setPct((prev) => {
      const next = Math.min(max, Math.max(min, prev + delta));
      lastPct.current = next;
      return next;
    });
  };
  const toggleCollapse = () => {
    setCollapsed((was) => {
      if (was) {
        setPct(Math.min(max, Math.max(min, lastPct.current || initial)));
        return false;
      }
      lastPct.current = pct;
      setPct(min);
      return true;
    });
  };
  const shown = collapsed ? min : pct;

  return (
    <div
      ref={wrap}
      data-testid={testId}
      data-collapsed={collapsed ? "true" : "false"}
      className={`flex h-full min-h-0 min-w-0 flex-1 ${horizontal ? "flex-row" : "flex-col"}`}
    >
      <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden" style={horizontal ? { width: `${shown}%` } : { height: `${shown}%` }}>
        {children[0]}
      </div>
      <button
        type="button"
        role="separator"
        aria-orientation={horizontal ? "vertical" : "horizontal"}
        aria-valuenow={Math.round(shown)}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuetext={`${Math.round(shown)} percent`}
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
        onDoubleClick={(e) => {
          e.preventDefault();
          toggleCollapse();
        }}
        onKeyDown={(e) => {
          const step = e.shiftKey ? 5 : 2;
          if (e.key === "Escape") {
            e.preventDefault();
            dragging.current = false;
            return;
          }
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleCollapse();
            return;
          }
          if (e.key === "Home") {
            e.preventDefault();
            setCollapsed(false);
            setPct(min);
            return;
          }
          if (e.key === "End") {
            e.preventDefault();
            setCollapsed(false);
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
