"use client";
import { useEffect, useState, useCallback } from "react";
import { fetchAudit } from "@/lib/api";
import DecisionBadge from "@/components/DecisionBadge";
import { Search, Filter } from "lucide-react";

interface AuditTxn {
  id: string; agent_id: string; merchant_name: string; amount: number;
  decision: string; risk_score: number; intent_match_score: number;
  policy_violations: string[]; reason: string; created_at: string;
  product: string; user_intent: string; category: string;
}

export default function AuditPage() {
  const [txns, setTxns] = useState<AuditTxn[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AuditTxn | null>(null);
  const [filters, setFilters] = useState({ txn_id: "", agent_id: "", merchant: "", decision: "" });

  const load = useCallback(async () => {
    const params: Record<string, string> = {};
    if (filters.txn_id) params.txn_id = filters.txn_id;
    if (filters.agent_id) params.agent_id = filters.agent_id;
    if (filters.merchant) params.merchant = filters.merchant;
    if (filters.decision) params.decision = filters.decision;
    try { const d = await fetchAudit(params); setTxns(d); } catch {}
    finally { setLoading(false); }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const inputClass = "px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-violet-500/60 transition-all";

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Audit Trail</h1>
        <p className="text-slate-400 text-sm mt-1">Complete immutable decision record</p>
      </div>

      {/* Filters */}
      <div className="glass p-4 rounded-2xl flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input placeholder="Transaction ID..." value={filters.txn_id}
            onChange={e => setFilters({...filters, txn_id: e.target.value})}
            className={`${inputClass} pl-9 w-full`} />
        </div>
        <input placeholder="Agent ID..." value={filters.agent_id}
          onChange={e => setFilters({...filters, agent_id: e.target.value})}
          className={`${inputClass} w-36`} />
        <input placeholder="Merchant..." value={filters.merchant}
          onChange={e => setFilters({...filters, merchant: e.target.value})}
          className={`${inputClass} w-36`} />
        <select value={filters.decision}
          onChange={e => setFilters({...filters, decision: e.target.value})}
          className={`${inputClass} w-36`}>
          <option value="" className="bg-slate-900">All Decisions</option>
          <option value="ALLOW" className="bg-slate-900">ALLOW</option>
          <option value="REVIEW" className="bg-slate-900">REVIEW</option>
          <option value="BLOCK" className="bg-slate-900">BLOCK</option>
        </select>
      </div>

      <div className="flex gap-5">
        {/* Table */}
        <div className="flex-1 glass rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  {["TXN ID", "Product", "Amount", "Agent", "Risk", "Decision", "Time"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={7} className="text-center py-12 text-slate-500">Loading...</td></tr>
                ) : txns.length === 0 ? (
                  <tr><td colSpan={7} className="text-center py-12 text-slate-500">No transactions found</td></tr>
                ) : txns.map(t => (
                  <tr
                    key={t.id}
                    onClick={() => setSelected(t)}
                    className={`border-b border-white/3 hover:bg-white/4 cursor-pointer transition-colors ${selected?.id === t.id ? "bg-violet-500/8" : ""}`}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-violet-400">{t.id}</td>
                    <td className="px-4 py-3 text-slate-200 max-w-32 truncate">{t.product}</td>
                    <td className="px-4 py-3 font-semibold text-white whitespace-nowrap">₹{t.amount?.toLocaleString("en-IN")}</td>
                    <td className="px-4 py-3 text-xs text-slate-400 font-mono">{t.agent_id}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-bold ${(t.risk_score ?? 50) <= 30 ? "text-emerald-400" : (t.risk_score ?? 50) <= 70 ? "text-amber-400" : "text-red-400"}`}>
                        {t.risk_score?.toFixed(0) ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3"><DecisionBadge decision={t.decision} size="sm" /></td>
                    <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">
                      {t.created_at ? new Date(t.created_at).toLocaleTimeString() : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Detail panel */}
        {selected && (
          <div className="w-80 glass p-5 rounded-2xl space-y-4 shrink-0">
            <div className="flex items-start justify-between">
              <p className="text-xs font-mono text-violet-400">{selected.id}</p>
              <DecisionBadge decision={selected.decision} size="sm" />
            </div>
            <div className="space-y-3">
              <Row label="Product" value={selected.product} />
              <Row label="Category" value={selected.category} />
              <Row label="Amount" value={`₹${selected.amount?.toLocaleString("en-IN")}`} />
              <Row label="Agent" value={selected.agent_id} mono />
              <Row label="Merchant" value={selected.merchant_name} />
              <Row label="Risk Score" value={`${selected.risk_score?.toFixed(1)}/100`} />
              <Row label="Intent Match" value={`${((selected.intent_match_score ?? 0) * 100).toFixed(0)}%`} />
            </div>
            <div className="bg-white/4 rounded-xl p-3">
              <p className="text-xs text-slate-400 mb-1">User Intent</p>
              <p className="text-xs text-slate-200">&quot;{selected.user_intent}&quot;</p>
            </div>
            <div className="bg-white/4 rounded-xl p-3">
              <p className="text-xs text-slate-400 mb-1">Reason</p>
              <p className="text-xs text-slate-200">{selected.reason}</p>
            </div>
            {selected.policy_violations?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-red-400 mb-2">Violations</p>
                <ul className="space-y-1">
                  {selected.policy_violations.map((v, i) => (
                    <li key={i} className="text-xs text-red-300 bg-red-500/8 px-2 py-1.5 rounded-lg">✕ {v}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={`text-xs font-medium text-slate-200 ${mono ? "font-mono" : ""}`}>{value}</span>
    </div>
  );
}
