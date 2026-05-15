/**
 * WebSocket client for ZECT real-time collaboration.
 */

const WS_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8001").replace(/^http/, "ws");

export type MessageHandler = (data: Record<string, unknown>) => void;

export class ZectWebSocket {
  private ws: WebSocket | null = null;
  private room: string;
  private user: string;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 3000;

  constructor(room: string, user = "anonymous") {
    this.room = room;
    this.user = user;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(`${WS_BASE}/ws/${this.room}?user=${encodeURIComponent(this.user)}`);

    this.ws.onopen = () => {
      this.emit("connected", {});
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const type = data.type as string;
        if (type) {
          this.emit(type, data);
        }
        this.emit("message", data);
      } catch { /* ignore parse errors */ }
    };

    this.ws.onclose = () => {
      this.emit("disconnected", {});
      this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectDelay);
    };

    this.ws.onerror = () => {
      this.emit("error", {});
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  send(type: string, data: Record<string, unknown> = {}): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...data }));
    }
  }

  on(type: string, handler: MessageHandler): void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler: MessageHandler): void {
    const list = this.handlers.get(type);
    if (list) {
      this.handlers.set(type, list.filter((h) => h !== handler));
    }
  }

  private emit(type: string, data: Record<string, unknown>): void {
    const list = this.handlers.get(type);
    if (list) {
      for (const handler of list) {
        handler(data);
      }
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
