/**
 * Realtime WebSocket client (singleton).
 *
 * Connects to NEXT_PUBLIC_WS_URL, auto-reconnects with capped backoff, and
 * dispatches typed events to subscribers. Fully degrades when the server has no
 * WS endpoint — it just reports `disconnected`/`error` and keeps retrying; it
 * never throws into the React tree. Consumed by hooks/useWebSocketEvents.ts.
 */
'use client';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// Known agent/event kinds; `string` keeps it permissive for future server events,
// and '*' (used at the subscribe site) is a wildcard for "all events".
export type AgentEventType =
  | 'agent_started'
  | 'agent_completed'
  | 'agent_failed'
  | 'insight_created'
  | 'trend_detected'
  | 'goal_milestone'
  | 'competitor_move'
  | 'notification'
  | (string & {});

export interface AgentEvent {
  type: AgentEventType;
  data: unknown;
  agent_type?: string;
  [key: string]: unknown;
}

type EventHandler = (event: AgentEvent) => void;
type StatusListener = (status: ConnectionStatus) => void;

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;

function resolveWsUrl(token?: string): string {
  let base = process.env.NEXT_PUBLIC_WS_URL || '';
  if (!base && typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    base = `${proto}//${window.location.host}`;
  }
  base = base.replace(/\/+$/, '');
  const url = `${base}/ws`;
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = 'disconnected';
  private token?: string;
  private manualClose = false;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly handlers = new Map<string, Set<EventHandler>>();
  private readonly statusListeners = new Set<StatusListener>();

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  connect(token?: string): void {
    if (typeof window === 'undefined') return;
    if (token !== undefined) this.token = token;
    // Already open/connecting with the same intent — no-op.
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.manualClose = false;
    this.setStatus('connecting');
    try {
      this.ws = new WebSocket(resolveWsUrl(this.token));
    } catch {
      this.setStatus('error');
      this.scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setStatus('connected');
    };
    this.ws.onmessage = (ev) => this.handleMessage(ev);
    this.ws.onerror = () => this.setStatus('error');
    this.ws.onclose = () => {
      this.setStatus('disconnected');
      if (!this.manualClose) this.scheduleReconnect();
    };
  }

  disconnect(): void {
    this.manualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try { this.ws.close(); } catch { /* ignore */ }
      this.ws = null;
    }
    this.setStatus('disconnected');
  }

  /** Subscribe to an event type (or '*' for all). Returns an unsubscribe fn. */
  on(eventType: AgentEventType | '*', handler: EventHandler): () => void {
    const key = String(eventType);
    let set = this.handlers.get(key);
    if (!set) {
      set = new Set();
      this.handlers.set(key, set);
    }
    set.add(handler);
    return () => {
      const s = this.handlers.get(key);
      if (s) {
        s.delete(handler);
        if (s.size === 0) this.handlers.delete(key);
      }
    };
  }

  /** Subscribe to connection-status changes. Fires immediately with current status. */
  onConnectionStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    try { listener(this.status); } catch { /* ignore */ }
    return () => this.statusListeners.delete(listener);
  }

  emit(event: string, data: unknown): void {
    if (this.isConnected()) {
      try { this.ws!.send(JSON.stringify({ type: event, data })); } catch { /* ignore */ }
    }
  }

  private setStatus(status: ConnectionStatus): void {
    if (status === this.status) return;
    this.status = status;
    for (const listener of this.statusListeners) {
      try { listener(status); } catch { /* ignore */ }
    }
  }

  private handleMessage(ev: MessageEvent): void {
    let event: AgentEvent;
    try {
      const parsed = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data;
      if (!parsed || typeof parsed !== 'object' || typeof parsed.type !== 'string') return;
      event = parsed as AgentEvent;
    } catch {
      return;
    }
    this.dispatch(this.handlers.get(event.type), event);
    this.dispatch(this.handlers.get('*'), event);
  }

  private dispatch(set: Set<EventHandler> | undefined, event: AgentEvent): void {
    if (!set) return;
    for (const handler of set) {
      try { handler(event); } catch { /* ignore */ }
    }
  }

  private scheduleReconnect(): void {
    if (this.manualClose || this.reconnectTimer) return;
    const delay = Math.min(RECONNECT_BASE_MS * 2 ** this.reconnectAttempts, RECONNECT_MAX_MS);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }
}

let client: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!client) client = new WebSocketClient();
  return client;
}

export type { WebSocketClient };
