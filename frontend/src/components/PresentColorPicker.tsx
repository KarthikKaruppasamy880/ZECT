import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const RECENT_KEY = "zect_present_recent_colors";

type Props = {
  value: string;
  onChange: (color: string) => void;
  themeColors?: string[];
  label?: string;
  testId?: string;
  allowAlpha?: boolean;
};

function parseHex(input: string): { r: number; g: number; b: number; a: number } | null {
  const raw = (input || "").trim();
  if (!raw.startsWith("#")) return null;
  const hex = raw.slice(1);
  if (hex.length === 3) {
    const r = parseInt(hex[0] + hex[0], 16);
    const g = parseInt(hex[1] + hex[1], 16);
    const b = parseInt(hex[2] + hex[2], 16);
    return { r, g, b, a: 1 };
  }
  if (hex.length === 6) {
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return Number.isFinite(r) && Number.isFinite(g) && Number.isFinite(b) ? { r, g, b, a: 1 } : null;
  }
  if (hex.length === 8) {
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const a = parseInt(hex.slice(6, 8), 16) / 255;
    return Number.isFinite(r) && Number.isFinite(g) && Number.isFinite(b) ? { r, g, b, a } : null;
  }
  return null;
}

function toHex(r: number, g: number, b: number, a = 1): string {
  const rr = Math.max(0, Math.min(255, Math.round(r))).toString(16).padStart(2, "0");
  const gg = Math.max(0, Math.min(255, Math.round(g))).toString(16).padStart(2, "0");
  const bb = Math.max(0, Math.min(255, Math.round(b))).toString(16).padStart(2, "0");
  if (a >= 0.999) return `#${rr}${gg}${bb}`.toUpperCase();
  const aa = Math.max(0, Math.min(255, Math.round(a * 255))).toString(16).padStart(2, "0");
  return `#${rr}${gg}${bb}${aa}`.toUpperCase();
}

function loadRecent(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    const parsed = raw ? (JSON.parse(raw) as string[]) : [];
    return Array.isArray(parsed) ? parsed.filter((c) => String(c).startsWith("#")).slice(0, 8) : [];
  } catch {
    return [];
  }
}

function pushRecent(color: string) {
  if (!color.startsWith("#")) return;
  const next = [color, ...loadRecent().filter((c) => c.toLowerCase() !== color.toLowerCase())].slice(0, 8);
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
}

export default function PresentColorPicker({
  value,
  onChange,
  themeColors = [],
  label = "Color",
  testId = "present-color-picker",
  allowAlpha = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [hexInput, setHexInput] = useState(value || "#000000");
  const [alpha, setAlpha] = useState(1);
  const [recent, setRecent] = useState<string[]>(() => loadRecent());
  const rootRef = useRef<HTMLDivElement | null>(null);

  const parsed = useMemo(() => parseHex(value || hexInput) || { r: 0, g: 0, b: 0, a: 1 }, [value, hexInput]);

  useEffect(() => {
    setHexInput(value || "#000000");
    const p = parseHex(value);
    if (p) setAlpha(p.a);
  }, [value]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const apply = useCallback(
    (hex: string) => {
      const normalized = hex.startsWith("#") ? hex.toUpperCase() : `#${hex}`.toUpperCase();
      onChange(normalized);
      setHexInput(normalized);
      pushRecent(normalized);
      setRecent(loadRecent());
    },
    [onChange],
  );

  const applyRgb = (r: number, g: number, b: number, a = alpha) => {
    apply(toHex(r, g, b, allowAlpha ? a : 1));
  };

  const swatches = [...new Set([...themeColors, ...recent].filter((c) => c.startsWith("#")))].slice(0, 12);

  return (
    <div className="relative" ref={rootRef} data-testid={testId}>
      <label className="block text-[11px] text-slate-600">
        {label}
        <div className="mt-0.5 flex items-center gap-1">
          <button
            type="button"
            data-testid={`${testId}-trigger`}
            className="h-7 w-7 shrink-0 rounded border border-slate-300"
            style={{ background: value || "#000000" }}
            aria-label={`${label} picker`}
            onClick={() => setOpen((v) => !v)}
          />
          <input
            type="color"
            data-testid={`${testId}-native`}
            className="h-7 w-8 cursor-pointer rounded border border-slate-200 p-0"
            value={(value || "#000000").slice(0, 7)}
            onChange={(e) => apply(e.target.value)}
          />
          <input
            type="text"
            data-testid={`${testId}-hex`}
            className="min-w-0 flex-1 rounded border border-slate-300 px-1 py-0.5 font-mono text-[10px]"
            value={hexInput}
            onChange={(e) => setHexInput(e.target.value)}
            onBlur={() => {
              const p = parseHex(hexInput);
              if (p) apply(toHex(p.r, p.g, p.b, allowAlpha ? p.a : 1));
            }}
          />
        </div>
      </label>
      {open ? (
        <div
          className="absolute z-50 mt-1 w-52 rounded-lg border border-slate-200 bg-white p-2 shadow-lg"
          data-testid={`${testId}-popover`}
        >
          {swatches.length ? (
            <div className="mb-2">
              <p className="mb-1 text-[9px] font-medium uppercase text-slate-500">Theme & recent</p>
              <div className="flex flex-wrap gap-1">
                {swatches.map((c) => (
                  <button
                    key={c}
                    type="button"
                    data-testid={`${testId}-swatch-${c.replace("#", "")}`}
                    className="h-5 w-5 rounded border border-slate-200"
                    style={{ background: c }}
                    onClick={() => apply(c)}
                  />
                ))}
              </div>
            </div>
          ) : null}
          <div className="grid grid-cols-3 gap-1 text-[10px]">
            {(["r", "g", "b"] as const).map((ch) => (
              <label key={ch} className="flex flex-col uppercase text-slate-500">
                {ch}
                <input
                  type="range"
                  min={0}
                  max={255}
                  value={parsed[ch]}
                  data-testid={`${testId}-${ch}`}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    applyRgb(ch === "r" ? n : parsed.r, ch === "g" ? n : parsed.g, ch === "b" ? n : parsed.b);
                  }}
                />
              </label>
            ))}
          </div>
          {allowAlpha ? (
            <label className="mt-1 block text-[10px] text-slate-500">
              Opacity
              <input
                type="range"
                min={0}
                max={100}
                value={Math.round(alpha * 100)}
                data-testid={`${testId}-alpha`}
                className="w-full"
                onChange={(e) => {
                  const a = Number(e.target.value) / 100;
                  setAlpha(a);
                  applyRgb(parsed.r, parsed.g, parsed.b, a);
                }}
              />
            </label>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
