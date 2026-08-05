import Editor, { type OnMount } from "@monaco-editor/react";
import { useEffect, useRef } from "react";
import type { editor as MonacoEditor } from "monaco-editor";

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
  /** 1-based line to reveal after mount / when changed. */
  revealLine?: number | null;
  onChange?: (value: string) => void;
  onSelectionChange?: (selection: EditorSelection | null) => void;
};

/** Thin Monaco wrapper for the developer workspace (selection + go-to-line). */
export default function MonacoCodeEditor({
  path,
  value,
  language,
  readOnly = false,
  revealLine = null,
  onChange,
  onSelectionChange,
}: MonacoCodeEditorProps) {
  const onSelRef = useRef(onSelectionChange);
  onSelRef.current = onSelectionChange;
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const revealRef = useRef(revealLine);
  revealRef.current = revealLine;

  const goTo = (ed: MonacoEditor.IStandaloneCodeEditor, line: number) => {
    if (!line || line < 1) return;
    ed.revealLineInCenter(line);
    ed.setPosition({ lineNumber: line, column: 1 });
    ed.focus();
  };

  useEffect(() => {
    if (revealLine && editorRef.current) {
      goTo(editorRef.current, revealLine);
    }
  }, [revealLine, path, value]);

  const handleMount: OnMount = (editor) => {
    editorRef.current = editor;
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
    if (revealRef.current) goTo(editor, revealRef.current);
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
