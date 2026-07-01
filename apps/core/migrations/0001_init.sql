-- Migration number: 0001 	 2026-07-01T18:28:03.467Z

CREATE TABLE agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT,
  version TEXT,
  skills TEXT NOT NULL DEFAULT '[]',       -- JSON array of {id, name, description}
  auth_schemes TEXT NOT NULL DEFAULT '[]', -- JSON array of strings
  registered_at REAL NOT NULL,
  last_seen_at REAL NOT NULL,
  reachable INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE traffic_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  from_agent_id TEXT NOT NULL,
  to_agent_id TEXT NOT NULL,
  method TEXT NOT NULL,
  task_id TEXT,
  status TEXT NOT NULL,
  latency_ms REAL NOT NULL,
  request TEXT NOT NULL,   -- JSON
  response TEXT            -- JSON
);

CREATE INDEX idx_traffic_events_ts ON traffic_events (ts);
