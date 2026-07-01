export interface RegisteredAgent {
  id: string;
  name: string;
  url: string;
  description?: string;
  version?: string;
  skills: { id: string; name: string; description?: string }[];
  authSchemes: string[];
  registeredAt: number;
  lastSeenAt: number;
  reachable: boolean;
  riskFlags: string[];
}

export interface TrafficEvent {
  id: number;
  ts: number;
  fromAgentId: string;
  toAgentId: string;
  method: string;
  taskId?: string;
  status: "ok" | "error";
  latencyMs: number;
  request: unknown;
  response: unknown;
}
