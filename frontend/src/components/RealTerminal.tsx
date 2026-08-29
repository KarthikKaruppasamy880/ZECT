import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { ptyCreateSession, ptyCloseSession, ptyStreamUrl } from "@/lib/api";

type RealTerminalProps = {
  workspaceRoot: string;
  cwd?: string;
  label?: string;
  onExit?: (exitCode: number | null) => void;
};

/**
 * A genuine workspace-scoped pseudo-terminal (V2 closure §10): real shell,
 * real cwd, streaming stdin/stdout over a WebSocket, resize, Ctrl+C. Not the
 * subprocess.Popen command-form / 2s-polling terminal this replaces.
 */
export default function RealTerminal({ workspaceRoot, cwd, label, onExit }: RealTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const disposedRef = useRef(false);

  useEffect(() => {
    disposedRef.current = false;
    if (!containerRef.current || !workspaceRoot) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 12,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
      theme: { background: "#0f172a" },
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    termRef.current = term;

    let ws: WebSocket | null = null;
    let resizeObserver: ResizeObserver | null = null;

    const connect = async () => {
      try {
        const session = await ptyCreateSession(workspaceRoot, { cwd, label });
        if (disposedRef.current) return;
        sessionIdRef.current = session.id;
        fitAddon.fit();
        ws = new WebSocket(ptyStreamUrl(session.id));
        wsRef.current = ws;
        ws.binaryType = "arraybuffer";

        ws.onmessage = (ev) => {
          if (typeof ev.data === "string") {
            try {
              const msg = JSON.parse(ev.data);
              if (msg.type === "exited") {
                term.write(`\r\n[process exited: ${msg.exit_code ?? "—"}]\r\n`);
                onExit?.(typeof msg.exit_code === "number" ? msg.exit_code : null);
              }
            } catch {
              term.write(ev.data);
            }
            return;
          }
          const text = new TextDecoder().decode(ev.data as ArrayBuffer);
          term.write(text);
        };
        ws.onopen = () => {
          fitAddon.fit();
          ws?.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }));
        };

        term.onData((data) => {
          ws?.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: "input", data }));
        });

        resizeObserver = new ResizeObserver(() => {
          fitAddon.fit();
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }));
          }
        });
        resizeObserver.observe(containerRef.current!);
      } catch (e) {
        term.write(`\r\n[error] ${e instanceof Error ? e.message : "failed to start terminal"}\r\n`);
      }
    };
    void connect();

    return () => {
      disposedRef.current = true;
      resizeObserver?.disconnect();
      ws?.close();
      wsRef.current = null;
      const sid = sessionIdRef.current;
      if (sid) void ptyCloseSession(sid).catch(() => {});
      term.dispose();
      termRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceRoot, cwd]);

  return <div ref={containerRef} data-testid="real-terminal" className="h-full min-h-0 w-full" />;
}
