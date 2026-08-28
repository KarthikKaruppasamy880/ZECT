import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import RealTerminal from "./RealTerminal";

const writeSpy = vi.fn();
let onDataHandler: ((data: string) => void) | null = null;

vi.mock("@xterm/xterm", () => ({
  Terminal: vi.fn().mockImplementation(function FakeTerminal() {
    return {
      loadAddon: vi.fn(),
      open: vi.fn(),
      write: writeSpy,
      onData: (cb: (data: string) => void) => {
        onDataHandler = cb;
      },
      dispose: vi.fn(),
      rows: 24,
      cols: 80,
    };
  }),
}));

vi.mock("@xterm/addon-fit", () => ({
  FitAddon: vi.fn().mockImplementation(function FakeFitAddon() {
    return { fit: vi.fn() };
  }),
}));

const ptyCreateSession = vi.fn(async () => ({ id: "sess-1", cwd: "/tmp", label: "term" }));
const ptyCloseSession = vi.fn(async () => ({ ok: true }));
const ptyStreamUrl = vi.fn((id: string) => `ws://localhost/api/workspace/pty/sessions/${id}/stream?token=t`);

vi.mock("@/lib/api", () => ({
  ptyCreateSession: (...args: unknown[]) => ptyCreateSession(...(args as [])),
  ptyCloseSession: (...args: unknown[]) => ptyCloseSession(...(args as [])),
  ptyStreamUrl: (...args: unknown[]) => ptyStreamUrl(...(args as [string])),
}));

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  binaryType = "blob";
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string | ArrayBuffer }) => void) | null = null;
  sent: string[] = [];
  readyState = 0;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = 3;
  }

  triggerOpen() {
    this.readyState = 1;
    this.onopen?.();
  }

  triggerMessage(data: string | ArrayBuffer) {
    this.onmessage?.({ data });
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  onDataHandler = null;
  writeSpy.mockClear();
  ptyCreateSession.mockClear();
  ptyCloseSession.mockClear();
  // @ts-expect-error -- test double for the global WebSocket constructor
  global.WebSocket = FakeWebSocket;
  // @ts-expect-error -- static constant read by RealTerminal (ws.readyState === WebSocket.OPEN)
  global.WebSocket.OPEN = 1;
});

describe("RealTerminal", () => {
  it("creates a session and opens a websocket to the returned session's stream URL", async () => {
    render(<RealTerminal workspaceRoot="/tmp/ws" />);
    await waitFor(() => expect(ptyCreateSession).toHaveBeenCalledWith("/tmp/ws", { cwd: undefined, label: undefined }));
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    expect(ptyStreamUrl).toHaveBeenCalledWith("sess-1");
  });

  it("writes real streamed output bytes into the terminal", async () => {
    render(<RealTerminal workspaceRoot="/tmp/ws" />);
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const ws = FakeWebSocket.instances[0];
    const bytes = new TextEncoder().encode("hello from the real shell\n").buffer;
    ws.triggerMessage(bytes);
    await waitFor(() => expect(writeSpy).toHaveBeenCalledWith("hello from the real shell\n"));
  });

  it("forwards typed input (including raw control bytes like Ctrl+C) as input frames", async () => {
    render(<RealTerminal workspaceRoot="/tmp/ws" />);
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const ws = FakeWebSocket.instances[0];
    ws.triggerOpen();
    expect(onDataHandler).toBeTruthy();
    onDataHandler?.("\x03");
    expect(ws.sent.some((s) => JSON.parse(s).type === "input" && JSON.parse(s).data === "\x03")).toBe(true);
  });

  it("shows the exit message and reports the exit code on an exited frame", async () => {
    const onExit = vi.fn();
    render(<RealTerminal workspaceRoot="/tmp/ws" onExit={onExit} />);
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
    const ws = FakeWebSocket.instances[0];
    ws.triggerMessage(JSON.stringify({ type: "exited", exit_code: 130 }));
    await waitFor(() => expect(onExit).toHaveBeenCalledWith(130));
    expect(writeSpy).toHaveBeenCalledWith(expect.stringContaining("130"));
  });
});
