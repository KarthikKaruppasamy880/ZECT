export type PresentChartTypeId =
  | "column"
  | "bar"
  | "stacked"
  | "stacked_horizontal"
  | "line"
  | "pie"
  | "area"
  | "donut"
  | "scatter"
  | "radar"
  | "polar"
  | "progress"
  | "gauge";

export const PRESENT_CHART_TYPES: Array<{ id: PresentChartTypeId; label: string }> = [
  { id: "column", label: "Bar Chart" },
  { id: "bar", label: "Horizontal Bar" },
  { id: "stacked", label: "Stacked Bar" },
  { id: "stacked_horizontal", label: "Horizontal Stack Bar" },
  { id: "line", label: "Line Chart" },
  { id: "pie", label: "Pie Chart" },
  { id: "area", label: "Area Chart" },
  { id: "donut", label: "Donut Chart" },
  { id: "scatter", label: "Scatter Chart" },
  { id: "radar", label: "Radar Chart" },
  { id: "polar", label: "Polar Area" },
  { id: "progress", label: "Progress Bar" },
  { id: "gauge", label: "Gauge Chart" },
];

export function chartTypeLabel(id: string): string {
  return PRESENT_CHART_TYPES.find((row) => row.id === id)?.label || id;
}

export function chartTypeFromPrompt(prompt: string): PresentChartTypeId | null {
  const text = prompt.toLowerCase();
  const hits: Array<[PresentChartTypeId, RegExp]> = [
    ["radar", /\bradar\b/],
    ["donut", /\bdonut\b|\bdoughnut\b/],
    ["pie", /\bpie\b/],
    ["area", /\barea\b/],
    ["line", /\bline\b/],
    ["scatter", /\bscatter\b/],
    ["polar", /\bpolar\b/],
    ["gauge", /\bgauge\b/],
    ["progress", /\bprogress\b/],
    ["stacked_horizontal", /\bhorizontal stack/],
    ["stacked", /\bstacked\b/],
    ["bar", /\bhorizontal bar\b/],
    ["column", /\bbar chart\b|\bcolumn\b/],
  ];
  for (const [id, re] of hits) {
    if (re.test(text)) return id;
  }
  return null;
}
