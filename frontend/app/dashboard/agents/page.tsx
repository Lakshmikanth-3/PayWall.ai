"use client";
import { useEffect, useState } from "react";
import { fetchAgents } from "@/lib/api";
import { Bot, ShieldCheck, ShieldOff, Activity } from "lucide-react";

interface Agent {
  id: string; name: string; owner_id: string; status: string;
  payment_enabled: boolean; max_transaction: number; daily_limit: number;
  daily_spent: number; allowed_categories: string[]; blocked_categories: string[];
  requires_approval_above: number;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Agent | null>(null);

  useEffect(() => {
    fetchAgents().then(a => { setAgents(a); setSelected(a[0] ?? null); }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center h-full text-slate-400">Loading agents...</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Agents</h1>
        <p className="text-slate-400 text-sm mt-1">Registered AI agents and their authorization policies</p>
      </div>

      <div className="flex gap-5">
        {/* Agent list */}
        <div className="w-72 space-y-3 shrink-0">
          {agents.map(a => (
            <div
              key={a.id}
              onClick={() => setSelected(a)}
              className={`glass p-4 rounded-xl cursor-pointer transition-all ${selected?.id === a.id ? "border-violet-500/40 bg-violet-500/8" : "hover:bg-white/5"}`}
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500/30 to-purple-700/30 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-violet-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{a.name}</p>
                  <p className="text-xs text-slate-500 font-mono">{a.id}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${a.status === "ACTIVE" ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                  {a.status}
                </span>
                {a.payment_enabled && <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400">Payments ON</span>}
              </div>
            </div>
          ))}
        </div>

        {/* Agent detail */}
        {selected ? (
          <div className="flex-1 glass p-6 rounded-2xl space-y-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">{selected.name}</h2>
                <p className="text-sm font-mono text-violet-400">{selected.id}</p>
                <p className="text-xs text-slate-500 mt-0.5">Owner: {selected.owner_id}</p>
              </div>
              <span className={`px-3 py-1.5 rounded-full text-xs font-semibold ${selected.status === "ACTIVE" ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25" : "bg-red-500/15 text-red-400 border border-red-500/25"}`}>
                {selected.status}
              </span>
            </div>

            {/* Policy grid */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white/4 rounded-xl p-4">
                <p className="text-xs text-slate-400 mb-1">Max Transaction</p>
                <p className="text-xl font-bold text-white">₹{selected.max_transaction.toLocaleString("en-IN")}</p>
              </div>
              <div className="bg-white/4 rounded-xl p-4">
                <p className="text-xs text-slate-400 mb-1">Daily Limit</p>
                <p className="text-xl font-bold text-white">₹{selected.daily_limit.toLocaleString("en-IN")}</p>
              </div>
              <div className="bg-white/4 rounded-xl p-4">
                <p className="text-xs text-slate-400 mb-1">Daily Spent</p>
                <p className="text-xl font-bold text-amber-400">₹{(selected.daily_spent ?? 0).toLocaleString("en-IN")}</p>
              </div>
            </div>

            {/* Budget bar */}
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                <span>Daily Budget Usage</span>
                <span>{selected.daily_limit > 0 ? ((selected.daily_spent / selected.daily_limit) * 100).toFixed(1) : 0}%</span>
              </div>
              <div className="h-2.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(100, selected.daily_limit > 0 ? (selected.daily_spent / selected.daily_limit) * 100 : 0)}%`,
                    background: "linear-gradient(90deg, #10b981, #f59e0b)",
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Allowed categories */}
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Allowed Categories</p>
                <div className="flex flex-wrap gap-1.5">
                  {selected.allowed_categories.map(c => (
                    <span key={c} className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/12 text-emerald-400 border border-emerald-500/25">{c}</span>
                  ))}
                </div>
              </div>
              {/* Blocked categories */}
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Blocked Categories</p>
                <div className="flex flex-wrap gap-1.5">
                  {selected.blocked_categories.map(c => (
                    <span key={c} className="px-2 py-0.5 rounded-full text-xs bg-red-500/12 text-red-400 border border-red-500/25">{c}</span>
                  ))}
                </div>
              </div>
            </div>

            {selected.requires_approval_above > 0 && (
              <div className="flex items-center gap-3 px-4 py-3 bg-amber-500/8 border border-amber-500/20 rounded-xl">
                <Activity className="w-4 h-4 text-amber-400 shrink-0" />
                <p className="text-sm text-amber-300">
                  Human approval required for transactions above <strong>₹{selected.requires_approval_above.toLocaleString("en-IN")}</strong>
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 glass rounded-2xl flex items-center justify-center text-slate-500">
            No agents seeded yet. Run the seed script.
          </div>
        )}
      </div>
    </div>
  );
}
