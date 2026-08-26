import type { PresentBlock, PresentSlide } from "@/lib/api";
import { CHART_SERIES_COLORS } from "@/lib/presentInsertDefaults";
import { blockLayerLabel, blockSemanticKindLabel, isParserDebugLabel } from "@/lib/presentEditorLabels";
import PresentColorPicker from "@/components/PresentColorPicker";

type PresentEditorSidePanelProps = {
  visualBlocks: PresentBlock[];
  selectedBlock: PresentBlock | null;
  selectedBlockId: string | null;
  showAdvanced: boolean;
  onToggleAdvanced: () => void;
  onSelectBlock: (id: string | null) => void;
  onReorderBlock: (id: string, dir: -1 | 1) => void;
  onPatchContent: (patch: Record<string, unknown>) => void;
  onPatchGeometry: (geo: { x: number; y: number; cx: number; cy: number }) => void;
  speakerNotes?: string;
  onSpeakerNotesChange?: (value: string) => void;
  themeColors?: string[];
  slideBackground?: string;
  onSlideBackground?: (fill: string) => void;
};

export default function PresentEditorSidePanel({
  visualBlocks,
  selectedBlock,
  selectedBlockId,
  showAdvanced,
  onToggleAdvanced,
  onSelectBlock,
  onReorderBlock,
  onPatchContent,
  onPatchGeometry,
  speakerNotes = "",
  onSpeakerNotesChange,
  themeColors = [],
  slideBackground = "#FFFFFF",
  onSlideBackground,
}: PresentEditorSidePanelProps) {
  return (
    <div className="flex flex-col gap-2" data-testid="present-editor-side-panel">
      <div className="rounded border border-slate-200 p-2" data-testid="present-editor-layers">
        <p className="mb-1 text-[11px] font-medium text-slate-600">Layers</p>
        {visualBlocks.length === 0 ? (
          <p className="text-[11px] text-slate-500">No selectable objects on this slide.</p>
        ) : (
          <ul className="max-h-40 space-y-1 overflow-auto">
            {visualBlocks.map((block, i) => (
              <li key={block.id || `${block.kind}-${i}`} className="flex items-center gap-1">
                <button
                  type="button"
                  data-testid={`present-editor-layer-${block.kind}`}
                  className={`flex-1 truncate rounded px-1 py-0.5 text-left text-[11px] ${
                    block.id === selectedBlockId ? "bg-teal-50 text-teal-900" : "text-slate-700"
                  }`}
                  onClick={() => onSelectBlock(block.id || null)}
                >
                  {blockLayerLabel(block)}
                </button>
                <button
                  type="button"
                  data-testid="present-editor-layer-back"
                  className="text-[10px] text-slate-500"
                  onClick={() => block.id && onReorderBlock(block.id, -1)}
                >
                  Back
                </button>
                <button
                  type="button"
                  data-testid="present-editor-layer-front"
                  className="text-[10px] text-slate-500"
                  onClick={() => block.id && onReorderBlock(block.id, 1)}
                >
                  Front
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="rounded border border-slate-200 p-2" data-testid="present-editor-props">
        <div className="mb-1 flex items-center justify-between">
          <p className="text-[11px] font-medium text-slate-600">Properties</p>
          <button
            type="button"
            data-testid="present-editor-advanced-toggle"
            className="text-[10px] text-teal-800"
            onClick={onToggleAdvanced}
          >
            {showAdvanced ? "Standard" : "Advanced"}
          </button>
        </div>
        {selectedBlock ? (
          <div className="space-y-2 text-[11px] text-slate-700">
            <p data-testid="present-editor-props-kind">{blockSemanticKindLabel(selectedBlock)}</p>
            {!showAdvanced ? (
              <>
                {(selectedBlock.kind === "text" ||
                  selectedBlock.kind === "quote" ||
                  selectedBlock.kind === "metric" ||
                  selectedBlock.kind === "shape") && (
                  <>
                    <label className="block">
                      Text
                      <input
                        type="text"
                        data-testid="present-editor-props-text"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.text || selectedBlock.content?.label || "")}
                        onChange={(e) => onPatchContent({ text: e.target.value })}
                      />
                    </label>
                    <PresentColorPicker
                      label="Text color"
                      testId="present-editor-props-text-color"
                      themeColors={themeColors}
                      value={String(selectedBlock.content?.color || "#1A1A1A")}
                      onChange={(color) => onPatchContent({ color })}
                    />
                    <label className="block">
                      Size (pt)
                      <input
                        type="number"
                        min={8}
                        max={96}
                        data-testid="present-editor-props-font-size"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={Number(selectedBlock.content?.font_size_pt) || 16}
                        onChange={(e) => onPatchContent({ font_size_pt: Number(e.target.value) || 16 })}
                      />
                    </label>
                    <label className="block">
                      Align
                      <select
                        data-testid="present-editor-props-align"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.align || "left")}
                        onChange={(e) => onPatchContent({ align: e.target.value })}
                      >
                        <option value="left">Left</option>
                        <option value="center">Center</option>
                        <option value="right">Right</option>
                      </select>
                    </label>
                  </>
                )}
                {selectedBlock.kind === "image" && (
                  <>
                    <label className="block">
                      Caption
                      <input
                        type="text"
                        data-testid="present-editor-props-alt"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={
                          isParserDebugLabel(String(selectedBlock.content?.alt || ""))
                            ? ""
                            : String(selectedBlock.content?.alt || "")
                        }
                        placeholder="Optional caption"
                        onChange={(e) => onPatchContent({ alt: e.target.value || "Photo" })}
                      />
                    </label>
                    <label className="block">
                      Fit
                      <select
                        data-testid="present-editor-props-fit"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.fit || "contain")}
                        onChange={(e) => onPatchContent({ fit: e.target.value })}
                      >
                        <option value="contain">Contain</option>
                        <option value="cover">Cover</option>
                        <option value="stretch">Stretch</option>
                      </select>
                    </label>
                  </>
                )}
                {selectedBlock.kind === "chart" && (
                  <>
                    <label className="block">
                      Chart type
                      <select
                        data-testid="present-editor-props-chart-type"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.chart_type || "column")}
                        onChange={(e) => onPatchContent({ chart_type: e.target.value })}
                      >
                        <option value="column">Column</option>
                        <option value="bar">Bar</option>
                        <option value="line">Line</option>
                        <option value="pie">Pie</option>
                        <option value="donut">Donut</option>
                        <option value="area">Area</option>
                        <option value="scatter">Scatter</option>
                        <option value="radar">Radar</option>
                      </select>
                    </label>
                    <label className="block">
                      Title
                      <input
                        type="text"
                        data-testid="present-editor-props-chart-title"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.title || "")}
                        onChange={(e) => onPatchContent({ title: e.target.value })}
                      />
                    </label>
                    <label className="block">
                      Show legend
                      <select
                        data-testid="present-editor-props-chart-legend"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={selectedBlock.content?.legend === false ? "false" : "true"}
                        onChange={(e) => onPatchContent({ legend: e.target.value === "true" })}
                      >
                        <option value="true">Yes</option>
                        <option value="false">No</option>
                      </select>
                    </label>
                    <PresentColorPicker
                      label="Series color"
                      testId="present-editor-props-chart-series-color"
                      themeColors={themeColors.length ? themeColors : CHART_SERIES_COLORS}
                      value={String(selectedBlock.content?.series_color || CHART_SERIES_COLORS[0])}
                      onChange={(series_color) => onPatchContent({ series_color })}
                    />
                    <p className="text-[10px] text-slate-500">Double-click chart to edit categories and values.</p>
                  </>
                )}
                {selectedBlock.kind === "diagram" && (
                  <>
                    <label className="block">
                      Diagram type
                      <select
                        data-testid="present-editor-props-diagram-type"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.diagram_type || "flow")}
                        onChange={(e) => onPatchContent({ diagram_type: e.target.value })}
                      >
                        <option value="flow">Flow</option>
                        <option value="process">Process</option>
                        <option value="timeline">Timeline</option>
                        <option value="architecture">Architecture</option>
                        <option value="comparison">Comparison</option>
                      </select>
                    </label>
                    <label className="block">
                      Labels (one per line)
                      <textarea
                        data-testid="present-editor-props-diagram-nodes"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        rows={3}
                        value={((selectedBlock.content?.nodes as string[]) || []).join("\n")}
                        onChange={(e) =>
                          onPatchContent({
                            nodes: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean).slice(0, 6),
                          })
                        }
                      />
                    </label>
                    <PresentColorPicker
                      label="Node fill"
                      testId="present-editor-props-diagram-fill"
                      themeColors={themeColors}
                      value={String(selectedBlock.content?.fill || "#00628B")}
                      onChange={(fill) => onPatchContent({ fill })}
                    />
                  </>
                )}
                {selectedBlock.kind === "icon" && (
                  <>
                    <p className="text-[11px] text-slate-600">Icon: {String(selectedBlock.content?.icon || "star")}</p>
                    <PresentColorPicker
                      label="Icon fill"
                      testId="present-editor-props-icon-fill"
                      themeColors={themeColors}
                      value={String(selectedBlock.content?.fill || "#00628B")}
                      onChange={(fill) => onPatchContent({ fill })}
                    />
                  </>
                )}
                {selectedBlock.kind === "shape" && (
                  <>
                    <PresentColorPicker
                      label="Fill"
                      testId="present-editor-props-fill"
                      themeColors={themeColors}
                      value={String(selectedBlock.content?.fill || "#e8eef3")}
                      onChange={(fill) => onPatchContent({ fill })}
                    />
                    <label className="block">
                      Stroke
                      <input
                        type="text"
                        data-testid="present-editor-props-stroke"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.stroke || "")}
                        placeholder="#44546A"
                        onChange={(e) => onPatchContent({ stroke: e.target.value })}
                      />
                    </label>
                  </>
                )}
                {selectedBlock.kind === "table" && (
                  <>
                    <label className="block">
                      Table title
                      <input
                        type="text"
                        data-testid="present-editor-props-table-title"
                        className="mt-0.5 w-full rounded border border-slate-300 px-1 py-0.5"
                        value={String(selectedBlock.content?.title || "")}
                        onChange={(e) => onPatchContent({ title: e.target.value })}
                      />
                    </label>
                    <p className="text-[10px] text-slate-500">Double-click the table on canvas to edit cells, rows, and columns.</p>
                  </>
                )}
                {onSlideBackground ? (
                  <PresentColorPicker
                    label="Slide background"
                    testId="present-editor-props-slide-bg"
                    themeColors={themeColors}
                    value={slideBackground.startsWith("#") ? slideBackground : "#FFFFFF"}
                    onChange={onSlideBackground}
                  />
                ) : null}
              </>
            ) : (
              <div className="grid grid-cols-2 gap-1">
                {(["x", "y", "cx", "cy"] as const).map((key) => (
                  <label key={key} className="flex items-center gap-1">
                    {key}
                    <input
                      data-testid={`present-editor-props-${key}`}
                      type="number"
                      className="w-full rounded border border-slate-300 px-1 py-0.5"
                      value={selectedBlock.geometry?.[key] || 0}
                      onChange={(e) => {
                        const geo = selectedBlock.geometry || { x: 0, y: 0, cx: 1, cy: 1 };
                        onPatchGeometry({
                          x: geo.x || 0,
                          y: geo.y || 0,
                          cx: geo.cx || 1,
                          cy: geo.cy || 1,
                          [key]: Number(e.target.value) || 0,
                        });
                      }}
                    />
                  </label>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-[11px] text-slate-500">Select an object on the slide.</p>
        )}
      </div>
      {onSpeakerNotesChange ? (
        <label className="block rounded border border-slate-200 p-2 text-[11px] font-medium text-slate-600">
          Speaker notes
          <textarea
            data-testid="present-editor-notes"
            value={speakerNotes}
            onChange={(e) => onSpeakerNotesChange(e.target.value)}
            rows={4}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm font-normal text-slate-900"
          />
        </label>
      ) : null}
    </div>
  );
}
