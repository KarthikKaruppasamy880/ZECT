/** Default insert payloads for user-created blank-deck objects (clearly editable sample data). */

export function defaultChartContent(chartType = "column"): Record<string, unknown> {
  return {
    title: "Chart title",
    chart_type: chartType,
    categories: ["Q1", "Q2", "Q3", "Q4"],
    series: [{ name: "Series 1", values: [12, 19, 8, 15] }],
    legend: true,
  };
}

export function defaultTableContent(rows = 4, cols = 3): Record<string, unknown> {
  const headers = Array.from({ length: cols }, (_, i) => `Column ${i + 1}`);
  const dataRows = Array.from({ length: Math.max(1, rows - 1) }, (_, r) =>
    Array.from({ length: cols }, (_, c) => (r === 0 && c === 0 ? "Cell" : "")),
  );
  return {
    title: "Table",
    headers,
    rows: dataRows,
  };
}

export function defaultTextContent(role: "title" | "subtitle" | "bullets" | "quote" | "body"): Record<string, unknown> {
  const map: Record<string, Record<string, unknown>> = {
    title: { text: "Title", role: "title", font_size_pt: 32, align: "left" },
    subtitle: { text: "Subtitle", role: "subtitle", font_size_pt: 20, align: "left" },
    bullets: { text: "• Point one\n• Point two", role: "body", font_size_pt: 16, align: "left" },
    quote: { text: "Quote", role: "quote" },
    body: { text: "Body text", role: "body", font_size_pt: 16, align: "left" },
  };
  return map[role] || map.body;
}

export function defaultDiagramContent(diagramType = "flow", nodes: string[] = ["Step 1", "Step 2", "Step 3"]): Record<string, unknown> {
  return {
    diagram_type: diagramType,
    nodes: nodes.slice(0, 6),
    fill: "#00628B",
  };
}

export const PRESENT_ICON_GLYPHS = [
  { id: "star", label: "Star", glyph: "★" },
  { id: "check", label: "Check", glyph: "✓" },
  { id: "info", label: "Info", glyph: "ℹ" },
  { id: "warning", label: "Warning", glyph: "!" },
  { id: "user", label: "User", glyph: "👤" },
  { id: "settings", label: "Settings", glyph: "⚙" },
  { id: "chart", label: "Chart", glyph: "📊" },
  { id: "target", label: "Target", glyph: "◎" },
] as const;

export function defaultIconContent(iconId: string): Record<string, unknown> {
  const icon = PRESENT_ICON_GLYPHS.find((i) => i.id === iconId) || PRESENT_ICON_GLYPHS[0];
  return {
    icon: icon.id,
    glyph: icon.glyph,
    fill: "#00628B",
    color: "#FFFFFF",
  };
}

export const CHART_SERIES_COLORS = ["#00628B", "#FF7500", "#4CAF50", "#44546A", "#9C27B0"];
