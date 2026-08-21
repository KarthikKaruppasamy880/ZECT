import { useEffect, useRef, useState } from "react";

type Props = {
  canRemoveFolder: boolean;
  canSave: boolean;
  terminalOpen: boolean;
  canRunApp: boolean;
  onAddFolder: () => void;
  onRemoveFolder: () => void;
  onSave: () => void;
  onCloseTerminal: () => void;
  onShowTerminal: () => void;
  onRunAppLocally: () => void;
};

type MenuId = "file" | "terminal" | null;

export default function WorkspaceIdeMenu({
  canRemoveFolder,
  canSave,
  terminalOpen,
  canRunApp,
  onAddFolder,
  onRemoveFolder,
  onSave,
  onCloseTerminal,
  onShowTerminal,
  onRunAppLocally,
}: Props) {
  const [open, setOpen] = useState<MenuId>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(null);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, []);

  const item = (testId: string, label: string, action: () => void, disabled = false) => (
    <button
      type="button"
      role="menuitem"
      data-testid={testId}
      disabled={disabled}
      className="block w-full px-3 py-1.5 text-left text-xs text-slate-800 hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400"
      onClick={() => {
        if (disabled) return;
        setOpen(null);
        action();
      }}
    >
      {label}
    </button>
  );

  return (
    <div
      ref={rootRef}
      className="flex items-center gap-1 text-xs text-slate-700"
      data-testid="workspace-ide-menu"
    >
      <div className="relative">
        <button
          type="button"
          data-testid="workspace-menu-file"
          aria-expanded={open === "file"}
          className={`rounded px-2 py-1 ${open === "file" ? "bg-slate-200" : "hover:bg-slate-100"}`}
          onClick={() => setOpen((v) => (v === "file" ? null : "file"))}
        >
          File
        </button>
        {open === "file" ? (
          <div
            role="menu"
            data-testid="workspace-menu-file-dropdown"
            className="absolute left-0 z-30 mt-0.5 min-w-[16rem] rounded-md border border-slate-200 bg-white py-1 shadow-lg"
          >
            {item("workspace-menu-add-folder", "Add Folder to Workspace…", onAddFolder)}
            {item(
              "workspace-menu-remove-folder",
              "Remove Folder from Workspace",
              onRemoveFolder,
              !canRemoveFolder,
            )}
            <div className="my-1 border-t border-slate-100" />
            {item("workspace-menu-save", "Save", onSave, !canSave)}
          </div>
        ) : null}
      </div>
      <div className="relative">
        <button
          type="button"
          data-testid="workspace-menu-terminal"
          aria-expanded={open === "terminal"}
          className={`rounded px-2 py-1 ${open === "terminal" ? "bg-slate-200" : "hover:bg-slate-100"}`}
          onClick={() => setOpen((v) => (v === "terminal" ? null : "terminal"))}
        >
          Terminal
        </button>
        {open === "terminal" ? (
          <div
            role="menu"
            data-testid="workspace-menu-terminal-dropdown"
            className="absolute left-0 z-30 mt-0.5 min-w-[18rem] rounded-md border border-slate-200 bg-white py-1 shadow-lg"
          >
            {item(
              "workspace-menu-close-terminal",
              "Close Terminal Panel",
              onCloseTerminal,
              !terminalOpen,
            )}
            {item("workspace-menu-show-terminal", "Show Terminal Panel", onShowTerminal, terminalOpen)}
            <div className="my-1 border-t border-slate-100" />
            {item(
              "workspace-menu-run-app",
              "Run App Locally (discovered recipe)…",
              onRunAppLocally,
              !canRunApp,
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
