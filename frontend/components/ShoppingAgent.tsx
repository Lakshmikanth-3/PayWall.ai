"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchAgents, runShoppingAgent, type ShoppingResult } from "@/lib/api";
import DecisionBadge from "@/components/DecisionBadge";

export default function ShoppingAgent() {
  const [agents, setAgents] = useState<{ id: string; name: string }[]>([]);
  const [agentId, setAgentId] = useState("");
  const [intent, setIntent] = useState("Buy running shoes under 5000");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ShoppingResult | null>(null);

  useEffect(() => {
    let active = true;
    fetchAgents().then((items) => {
      if (!active) return;
      setAgents(items);
      setAgentId(items.find((a: { id: string }) => a.id === "AGT-001")?.id ?? items[0]?.id ?? "");
    }).catch(() => { if (active) setError("Could not load agents. Check the API connection."); });
    return () => { active = false; };
  }, []);

  async function run(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try { setResult(await runShoppingAgent(agentId, intent.trim())); }
    catch (err) { setError(err instanceof Error ? err.message : "Request failed"); }
    finally { setBusy(false); }
  }

  return (
    <section aria-labelledby="shopping-agent-heading" className="glass p-5 rounded-2xl space-y-4">
      <div>
        <h2 id="shopping-agent-heading" className="text-lg font-semibold text-white">Shopping Agent</h2>
        <p className="text-sm text-slate-400 mt-1">Your intent → agent proposal → Guard decision. Catalog from Zetaris, memory from Meterless H-MEM, reasoning by Nemotron through Nightshift. No payment is executed here.</p>
      </div>
      <form onSubmit={run} className="flex flex-col sm:flex-row gap-3">
        <div className="text-xs text-slate-400 sm:w-48">
          <label htmlFor="shopping-agent-selector">Agent</label>
          <select id="shopping-agent-selector" value={agentId} onChange={(event) => setAgentId(event.target.value)} disabled={busy} required
            className="block w-full mt-1 rounded-lg bg-slate-900 border border-white/15 p-2.5 text-sm text-white">
            <option value="" disabled>Select an agent</option>
            {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
          </select>
        </div>
        <label className="flex-1 text-xs text-slate-400">
          Purchase intent
          <input value={intent} onChange={(event) => setIntent(event.target.value)} disabled={busy} required minLength={3} maxLength={2000}
            className="block w-full mt-1 rounded-lg bg-slate-900 border border-white/15 p-2.5 text-sm text-white"
            placeholder="Buy running shoes under 5000" />
        </label>
        <button type="submit" disabled={busy || !agentId || intent.trim().length < 3}
          className="self-end rounded-lg px-5 py-2.5 bg-violet-600 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed">
          {busy ? "Reasoning…" : "Run"}
        </button>
      </form>
      {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
      <div aria-live="polite" aria-busy={busy}>
        {result && <div className="rounded-xl border border-white/10 p-4 space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-semibold text-white">{result.agent_proposal.product} · ₹{result.agent_proposal.amount.toLocaleString("en-IN")}</p>
            <span className="text-slate-400">→ Guard</span>
            <DecisionBadge decision={result.decision} />
          </div>
          <p className="text-slate-300">{result.agent_reasoning}</p>
          <p className="text-slate-400">Merchant: {result.agent_proposal.merchant_id} · Risk: {result.risk_score.toFixed(1)}/100 · Intent: {(result.intent_score * 100).toFixed(0)}%</p>
          <ul className="list-disc pl-5 text-slate-300 space-y-1">{result.reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul>
          <p className="text-xs text-slate-400 break-all">Agent model: {result.model} · Guard model: {result.guard_model}</p>
          <p className="text-xs text-slate-400 break-all">Catalog: {result.catalog_source === 'zetaris' ? 'Zetaris (live SQL)' : 'labelled sample copy'} · Guard retries: {result.guard_retries ?? 0}{result.run_id ? ` · Trace: ${result.run_id}` : ''}</p>
          {result.memories_recalled && result.memories_recalled.length > 0 && (
            <div className="text-xs text-slate-400">
              <p className="text-slate-300">Recalled from H-MEM:</p>
              <ul className="list-disc pl-4">{result.memories_recalled.slice(0, 3).map((m, i) => <li key={i}>{m}</li>)}</ul>
            </div>
          )}
          <Link href="/dashboard/audit" className="inline-block text-xs text-violet-300 underline">Audit trail · {result.transaction_id}</Link>
        </div>}
      </div>
    </section>
  );
}
