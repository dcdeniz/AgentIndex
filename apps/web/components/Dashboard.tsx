"use client";

import { useState } from "react";
import { Inventory } from "./Inventory";
import { Traffic } from "./Traffic";

export function Dashboard() {
  const [tab, setTab] = useState<"traffic" | "inventory">("traffic");
  return (
    <div className="app">
      <header>
        <h1>AgentIndex</h1>
        <nav>
          <button className={tab === "traffic" ? "active" : ""} onClick={() => setTab("traffic")}>
            Live Traffic
          </button>
          <button className={tab === "inventory" ? "active" : ""} onClick={() => setTab("inventory")}>
            Inventory
          </button>
        </nav>
      </header>
      <main>{tab === "traffic" ? <Traffic /> : <Inventory />}</main>
    </div>
  );
}
