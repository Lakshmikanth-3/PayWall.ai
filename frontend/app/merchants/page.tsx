"use client";
import { useEffect, useState } from "react";
import { fetchMerchants } from "@/lib/api";
import { Store, AlertTriangle, ShieldCheck, TrendingDown } from "lucide-react";

interface Merchant {
  id: string; name: string; category: string;
  risk_score: number; risk_level: string; age_days: number;
  refund_rate: number; chargeback_rate: number; failed_payment_rate: number;
  is_blocked: boolean;
}

const RISK_COLORS: Record<string, string> = {
  LOW: "text-emerald-400", MEDIUM: "text-amber-400", HIGH: "text-red-400",
};
const RISK_BG: Record<string, string> = {
  LOW: "bg-emerald-500/12 border-emerald-500/25",
  MEDIUM: "bg-amber-500/12 border-amber-500/25",
  HIGH: "bg-red-500/12 border-red-500/25",
};

export default function MerchantsPage() {
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Merchant | null>(null);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    fetchMerchants().then(m => { setMerchants(m); setSelected(m[0] ?? null); }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = filter === "ALL" ? merchants : merchants.filter(m => m.risk_level === filter);

  if (loading) return <div className="flex items-center justify-center h-full text-slate-400">Loading merchants...</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Merchants</h1>
          <p className="text-slate-400 text-sm mt-1">Merchant risk profiles and signals</p>
        </div>
        <div className="flex gap-1.5">
          {["ALL", "LOW", "MEDIUM", "HIGH"].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${filter === f ? "bg-violet-500/20 text-violet-300 border border-violet-500/30" : "bg-white/4 text-slate-400 hover:bg-white/8"}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Table */}
        <div className="glass rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Merchant</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Category</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Risk</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(m => (
                <tr key={m.id} onClick={() => setSelected(m)}
                  className={`border-b border-white/3 hover:bg-white/4 cursor-pointer transition-colors ${selected?.id === m.id ? "bg-violet-500/8" : ""}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center">
                        <Store className="w-3.5 h-3.5 text-slate-400" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-white">{m.name}</p>
                        <p className="text-xs text-slate-600 font-mono">{m.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">{m.category}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-bold ${RISK_COLORS[m.risk_level]}`}>{m.risk_score.toFixed(0)}</span>
                    <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full border ${RISK_BG[m.risk_level]} ${RISK_COLORS[m.risk_level]}`}>{m.risk_level}</span>
                  </td>
                  <td className="px-4 py-3">
                    {m.is_blocked
                      ? <span className="text-xs text-red-400 font-medium">BLOCKED</span>
                      : <span className="text-xs text-emerald-400 font-medium">ACTIVE</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Detail */}
        {selected && (
          <div className="glass p-5 rounded-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">{selected.name}</h2>
                <p className="text-xs text-slate-500 font-mono">{selected.id} · {selected.category}</p>
              </div>
              <span className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${RISK_BG[selected.risk_level]} ${RISK_COLORS[selected.risk_level]}`}>
                {selected.risk_level} RISK
              </span>
            </div>

            {/* Risk score big */}
            <div className="bg-white/4 rounded-xl p-4 text-center">
              <p className="text-4xl font-black" style={{ color: selected.risk_level === "LOW" ? "#10b981" : selected.risk_level === "MEDIUM" ? "#f59e0b" : "#ef4444" }}>
                {selected.risk_score.toFixed(0)}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">Risk Score (0–100)</p>
              <div className="mt-3 h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{
                  width: `${selected.risk_score}%`,
                  background: selected.risk_level === "LOW" ? "#10b981" : selected.risk_level === "MEDIUM" ? "#f59e0b" : "#ef4444",
                }} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Metric icon={TrendingDown} label="Age" value={`${selected.age_days} days`} />
              <Metric icon={AlertTriangle} label="Refund Rate" value={`${(selected.refund_rate * 100).toFixed(1)}%`} />
              <Metric icon={AlertTriangle} label="Chargeback Rate" value={`${(selected.chargeback_rate * 100).toFixed(1)}%`} />
              <Metric icon={TrendingDown} label="Failed Payments" value={`${(selected.failed_payment_rate * 100).toFixed(1)}%`} />
            </div>

            {selected.is_blocked && (
              <div className="flex items-center gap-2 px-4 py-3 bg-red-500/10 border border-red-500/25 rounded-xl">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <p className="text-sm text-red-300 font-medium">Merchant is blocked — all transactions will be rejected</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="bg-white/4 rounded-xl p-3 flex items-center gap-2.5">
      <Icon className="w-4 h-4 text-slate-500 shrink-0" />
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm font-semibold text-white">{value}</p>
      </div>
    </div>
  );
}
