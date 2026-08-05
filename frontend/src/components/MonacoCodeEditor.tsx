import Editor, { type OnMount } from "@monaco-editor/react";
import { useRef } from "react";

export type EditorSelection = {
  text: string;
  startLine: number;
  endLine: number;
  startColumn: number;
  endColumn: number;
};

type MonacoCodeEditorProps = {
  path: string;
  value: string;
  language: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
  onSelectionChange?: (selection: EditorSelection | null) => void;
};

/** Thin Monaco wrapper for the developer workspace (selection callbacks for Stage D). */
export default function MonacoCodeEditor({
  path,
  value,
  language,
  readOnly = false,
  onChange,
  onSelectionChange,
}: MonacoCodeEditorProps) {
  const onSelRef = useRef(onSelectionChange);
  onSelRef.current = onSelectionChange;

  const handleMount: OnMount = (editor) => {
    const emit = () => {
      const cb = onSelRef.current;
      if (!cb) return;
      const sel = editor.getSelection();
      if (!sel || sel.isEmpty()) {
        cb(null);
        return;
      }
      const model = editor.getModel();
      if (!model) {
        cb(null);
        return;
      }
      const text = model.getValueInRange(sel);
      if (!text.trim()) {
        cb(null);
        return;
      }
      cb({
        text,
        startLine: sel.startLineNumber,
        endLine: sel.endLineNumber,
        startColumn: sel.startColumn,
        endColumn: sel.endColumn,
      });
    };
    emit();
    editor.onDidChangeCursorSelection(() => emit());
  };

  return (
    <div className="h-full min-h-[320px] border border-slate-200 rounded-lg overflow-hidden" data-testid="monaco-editor">
      <Editor
        key={path}
        height="100%"
        path={path}
        language={language}
        value={value}
        theme="vs"
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 13,
          wordWrap: "on",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
        }}
        onMount={handleMount}
        onChange={(v) => onChange?.(v ?? "")}
      />
    </div>
  );
}
