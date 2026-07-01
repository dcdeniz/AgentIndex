import { DurableObject, WorkerEntrypoint } from "cloudflare:workers";

export interface Env {
  HUB: DurableObjectNamespace<Hub>;
}

// Single global hub: this DO exists purely to fan out live TrafficEvents to
// connected dashboards. It holds no durable state of its own — agents and
// events live in D1 (see apps/core) — so losing a hibernated instance just
// means clients reconnect and refetch from /api/events.
export class Hub extends DurableObject<Env> {
  async fetch(request: Request): Promise<Response> {
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("expected websocket upgrade", { status: 426 });
    }
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.ctx.acceptWebSocket(server);
    return new Response(null, { status: 101, webSocket: client });
  }

  async broadcast(payload: unknown): Promise<void> {
    const data = JSON.stringify(payload);
    for (const ws of this.ctx.getWebSockets()) {
      try {
        ws.send(data);
      } catch {
        // stale socket; hibernation API drops it on next GC
      }
    }
  }

  async webSocketClose(ws: WebSocket, code: number, reason: string): Promise<void> {
    ws.close(code, reason);
  }
}

export default class extends WorkerEntrypoint<Env> {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/ws") {
      const stub = this.env.HUB.getByName("global");
      return stub.fetch(request);
    }
    return new Response("not found", { status: 404 });
  }

  // Called over a service binding from apps/core (the Python gateway) after
  // it records a TrafficEvent, so it never needs to know Durable Objects exist.
  async broadcast(payload: unknown): Promise<void> {
    const stub = this.env.HUB.getByName("global");
    await stub.broadcast(payload);
  }
}
