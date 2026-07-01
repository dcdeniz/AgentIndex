"use client";

import { useEffect, useState } from "react";
import type { RegisteredAgent } from "../lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

export function Inventory() {
  const [agents, setAgents] = useState<RegisteredAgent[]>([]);

  async function load() {
    const res = await fetch(`${API_URL}/api/agents`);
    setAgents(await res.json());
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <table className="inventory">
      <thead>
        <tr>
          <th>Agent</th>
          <th>Skills</th>
          <th>Last seen</th>
          <th>Risk</th>
        </tr>
      </thead>
      <tbody>
        {agents.map((a) => (
          <tr key={a.id}>
            <td>
              {a.name}
              <div className="url">{a.url}</div>
            </td>
            <td>{a.skills.map((s) => s.name).join(", ")}</td>
            <td>{new Date(a.lastSeenAt).toLocaleTimeString()}</td>
            <td>
              {a.riskFlags.map((f) => (
                <span key={f} className={`flag ${f}`}>
                  {f}
                </span>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
