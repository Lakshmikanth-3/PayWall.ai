const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/dashboard/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/dashboard/metrics`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

export async function fetchHoldoutMetrics() {
  const res = await fetch(`${API_BASE}/dashboard/holdout-metrics`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchLive(limit = 10) {
  const res = await fetch(`${API_BASE}/dashboard/live?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch live feed");
  return res.json();
}

export async function fetchTransactions(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/transactions?${qs}&limit=100`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch transactions");
  return res.json();
}

export async function fetchAudit(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/dashboard/audit?${qs}&limit=100`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch audit");
  return res.json();
}

export async function fetchAgents() {
  const res = await fetch(`${API_BASE}/agents`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function fetchMerchants() {
  const res = await fetch(`${API_BASE}/merchants`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch merchants");
  return res.json();
}

export async function evaluateTransaction(payload: unknown) {
  const res = await fetch(`${API_BASE}/transactions/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Evaluation failed");
  }
  return res.json();
}

export async function humanReview(txnId: string, approved: boolean) {
  const res = await fetch(`${API_BASE}/transactions/${txnId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, reviewer: "ops-team" }),
  });
  if (!res.ok) throw new Error("Review failed");
  return res.json();
}

export async function fetchLlmStatus() {
  const res = await fetch(`${API_BASE}/dashboard/llm-status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch LLM status");
  return res.json();
}

export async function toggleLlm(disabled: boolean) {
  const res = await fetch(`${API_BASE}/dashboard/llm-toggle?disabled=${disabled}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to toggle LLM");
  return res.json();
}
export async function fetchRevenueImpact() {
  const res = await fetch(`${API_BASE}/dashboard/revenue-impact`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch revenue impact");
  return res.json();
}

export async function proposeUpsell(txnId: string) {
  const res = await fetch(`${API_BASE}/transactions/${txnId}/upsell`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Upsell proposal failed");
  }
  return res.json();
}

export async function simulatePolicy(agentId: string, payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/agents/${agentId}/simulate-policy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Simulation failed");
  }
  return res.json();
}
