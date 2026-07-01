"use client";

import { useEffect, useState } from "react";
import type { TrafficEvent } from "../lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:4000/ws";

export function Traffic() {
  const [events, setEvents] = useState<TrafficEvent[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/events`)
      .then((r) => r.json())
      .then(setEvents);

    const ws = new WebSocket(WS_URL);
    ws.onmessage = (msg) => {
      const payload = JSON.parse(msg.data);
      if (payload.type === "event") {
        setEvents((prev) => [...prev.slice(-99), payload.event]);
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="traffic">
      {events
        .slice()
        .reverse()
        .map((e) => (
          <div key={e.id} className={`event ${e.status}`}>
            <span className="ts">{new Date(e.ts).toLocaleTimeString()}</span>
            <span className="path">
              {e.fromAgentId} → {e.toAgentId}
            </span>
            <span className="method">{e.method}</span>
            <span className="latency">{Math.round(e.latencyMs)}ms</span>
          </div>
        ))}
    </div>
  );
}
