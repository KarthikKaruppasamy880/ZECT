import Editor from "@monaco-editor/react";

type MonacoCodeEditorProps = {
  path: string;
  value: string;
  language: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
};

/** Thin Monaco wrapper for the developer workspace. */
export default function MonacoCodeEditor({
  path,
  value,
  language,
  readOnly = false,
  onChange,
}: MonacoCodeEditorProps) {
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
        onChange={(v) => onChange?.(v ?? "")}
      />
    </div>
  );
}
