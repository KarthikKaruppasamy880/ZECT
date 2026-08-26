import type { PresentBlock } from "@/lib/api";

const NODE_FILL = "#00628B";
const ARROW_FILL = "#FF7500";

type Props = { block: PresentBlock; testId?: string };

export default function PresentDiagramPreview({ block, testId }: Props) {
  const dtype = String(block.content?.diagram_type || "flow").toLowerCase();
  const nodes = ((block.content?.nodes as string[]) || []).filter(Boolean).slice(0, 6);
  const fill = String(block.content?.fill || NODE_FILL);

  if (nodes.length < 2) {
    return (
      <div className="flex h-full items-center justify-center text-[8px] text-slate-500" data-testid={testId}>
        Diagram
      </div>
    );
  }

  if (dtype === "process" || dtype === "sequence") {
    return (
      <div className="flex h-full flex-col gap-0.5 p-0.5" data-testid={testId}>
        {nodes.map((n, i) => (
          <div key={`${n}-${i}`} className="flex items-center gap-0.5">
            <span className="flex-1 truncate rounded px-1 py-0.5 text-[7px] font-medium text-white" style={{ backgroundColor: fill }}>
              {n}
            </span>
            {i < nodes.length - 1 ? <span className="text-[8px]" style={{ color: ARROW_FILL }}>↓</span> : null}
          </div>
        ))}
      </div>
    );
  }

  if (dtype === "architecture" && nodes.length >= 3) {
    const mid = Math.ceil(nodes.length / 2);
    const top = nodes.slice(0, mid);
    const bottom = nodes.slice(mid);
    return (
      <div className="flex h-full flex-col justify-center gap-1 p-0.5" data-testid={testId}>
        <div className="flex gap-0.5">
          {top.map((n, i) => (
            <span key={i} className="flex-1 truncate rounded px-0.5 py-0.5 text-[7px] text-white" style={{ backgroundColor: fill }}>
              {n}
            </span>
          ))}
        </div>
        <div className="flex gap-0.5">
          {bottom.map((n, i) => (
            <span key={i} className="flex-1 truncate rounded px-0.5 py-0.5 text-[7px] text-white" style={{ backgroundColor: "#44546A" }}>
              {n}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full items-center gap-0.5 p-0.5" data-testid={testId}>
      {nodes.map((n, i) => (
        <div key={`${n}-${i}`} className="flex flex-1 items-center gap-0.5">
          <span className="flex-1 truncate rounded px-0.5 py-1 text-[7px] font-medium text-white" style={{ backgroundColor: fill }}>
            {n}
          </span>
          {i < nodes.length - 1 ? <span className="text-[8px]" style={{ color: ARROW_FILL }}>→</span> : null}
        </div>
      ))}
    </div>
  );
}
