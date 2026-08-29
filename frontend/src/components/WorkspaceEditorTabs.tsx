import { X } from "lucide-react";
import { editorTabLabel, type WorkspaceEditorTab } from "@/lib/workspaceSession";

type Props = {
  tabs: WorkspaceEditorTab[];
  activePath: string;
  dirtyPaths?: Set<string>;
  onSelect: (tab: WorkspaceEditorTab) => void;
  onClose: (tab: WorkspaceEditorTab) => void;
};

export default function WorkspaceEditorTabs({ tabs, activePath, dirtyPaths, onSelect, onClose }: Props) {
  if (!tabs.length) return null;
  return (
    <div
      className="flex shrink-0 min-h-0 min-w-0 items-stretch gap-0 overflow-x-auto border-b border-slate-200 bg-slate-50"
      data-testid="workspace-editor-tabs"
      role="tablist"
      aria-label="Open editors"
    >
      {tabs.map((tab) => {
        const active = tab.path === activePath;
        const dirty = Boolean(dirtyPaths?.has(tab.path));
        return (
          <div
            key={`${tab.repoId}:${tab.path}`}
            className={`group flex max-w-[14rem] shrink-0 items-center border-r border-slate-200 ${
              active ? "bg-white text-slate-900" : "bg-slate-50 text-slate-600 hover:bg-white"
            }`}
          >
            <button
              type="button"
              role="tab"
              aria-selected={active}
              title={tab.path}
              data-testid={`workspace-editor-tab-${editorTabLabel(tab.path)}`}
              data-active={active ? "true" : "false"}
              className="min-w-0 truncate px-2 py-1.5 text-left text-[11px] font-medium"
              onClick={() => onSelect(tab)}
            >
              {dirty ? "• " : ""}
              {editorTabLabel(tab.path)}
            </button>
            <button
              type="button"
              className="shrink-0 px-1 py-1.5 text-slate-400 hover:text-rose-700"
              data-testid={`workspace-editor-tab-close-${editorTabLabel(tab.path)}`}
              title="Close editor"
              onClick={(e) => {
                e.stopPropagation();
                onClose(tab);
              }}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
