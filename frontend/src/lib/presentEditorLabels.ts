import type { PresentBlock } from "@/lib/api";

export function blockLayerLabel(block: PresentBlock): string {
  const role = String(block.content?.role || block.content?.placeholder || "").trim();
  if (role) return role.charAt(0).toUpperCase() + role.slice(1);
  const shapeName = String(block.content?.shape_name || "").trim();
  if (shapeName && !/^(image|picture)\s*\d+$/i.test(shapeName)) return shapeName;
  const text = String(block.content?.text || block.content?.label || "").trim();
  if (text) return text.length > 36 ? `${text.slice(0, 36)}…` : text;
  const labels: Record<string, string> = {
    text: "Text",
    image: "Photo",
    shape: "Shape",
    chart: "Chart",
    table: "Table",
    diagram: "Diagram",
    group: "Group",
    quote: "Quote",
    metric: "Metric",
  };
  return labels[String(block.kind)] || String(block.kind);
}

export function blockSemanticKindLabel(block: PresentBlock): string {
  const role = String(block.content?.role || "").trim();
  if (role) return role;
  const labels: Record<string, string> = {
    text: "Text",
    image: "Image",
    shape: "Shape",
    chart: "Chart",
    table: "Table",
    diagram: "Diagram",
    group: "Group",
    quote: "Quote",
    metric: "Metric",
  };
  return labels[String(block.kind)] || String(block.kind);
}

export function isParserDebugLabel(value: string): boolean {
  const v = value.trim();
  return /^(image|picture|shape)\s*\d+$/i.test(v);
}
