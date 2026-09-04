"use client";
import { useEffect, useState } from "react";
import { fetchAgents, simulatePolicy } from "@/lib/api";
import { Sliders, ArrowRight, TrendingUp, TrendingDown, AlertTriangle, Loader2, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import DecisionBadge from "@/components/DecisionBadge";

interface Agent {
  id: string;
  name: string;
  max_transaction: number;
  daily_limit: number;
  allowed_categories: string[];
  blocked_categories: string[];
  requires_approval_above: number;
}

interface SimResult {
  agent_id: string;
  transactions_analyzed: number;
  current_policy: Policy;
  proposed_policy: Policy;
  before: DecisionCounts;
  after: DecisionCounts;
  now_allowed_count: number;
  now_allowed_gmv: number;
  additional_risky_exposure: number;
  now_blocked_count: number;
  now_blocked_gmv: number;
  flipped_transactions: FlippedTxn[];
}

interface Policy {
  max_transaction: number;
  daily_limit: number;
  allowed_categories: string[];
  blocked_categories: string[];
  requires_approval_above: number;
}

interface DecisionCounts { ALLOW: number; REVIEW: number; BLOCK: number; }

interface FlippedTxn {
  transaction_id: string;
  amount: number;
  category: string;
  product: string;
  merchant_name?: string;
  risk_score?: number;
  before: string;
  after: string;
}

const ALL_CATEGORIES = [
  "food", "groceries", "sports", "electronics", "travel",
  "hotel", "office", "stationery", "gambling", "financial_services",
];

function formatINR(n: number) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(2)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}k`;
  return `₹${Math.round(n)}`;
}

function DecisionBar({ before, after }: { before: DecisionCounts; after: DecisionCounts }) {
  const total = Math.max(before.ALLOW + before.REVIEW + before.BLOCK, 1);
  const afterTotal = Math.max(after.ALLOW + after.REVIEW + after.BLOCK, 1);
  return (
    <div className="space-y-3">
      {[
        { label: "Before", counts: before, tot: total },
        { label: "After", counts: after, tot: afterTotal },
      ].map(({ label, counts, tot }) => (
        <div key={label}>
          <div className="flex justify-between text-xs text-slate-400 mb-1.5">
            <span className="font-medium">{label}</span>
            <span className="flex gap-3">
              <span className="text-emerald-400">{counts.ALLOW} allow</span>
              <span className="text-amber-400">{counts.REVIEW} review</span>
              <span className="text-red-400">{counts.BLOCK} block</span>
            </span>
          </div>
          <div className="flex h-3 rounded-full overflow-hidden bg-white/5">
            <div className="bg-emerald-500 transition-all duration-700" style={{ width: `${(counts.ALLOW / tot) * 100}%` }} />
            <div className="bg-amber-500 transition-all duration-700" style={{ width: `${(counts.REVIEW / tot) * 100}%` }} />
            <div className="bg-red-500 transition-all duration-700" style={{ width: `${(counts.BLOCK / tot) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SimulatePage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selected, setSelected] = useState<Agent | null>(null);
  const [form, setForm] = useState({
    max_transaction: 0,
    daily_limit: 0,
    requires_approval_above: 0,
    allowed_categories: [] as string[],
    blocked_categories: [] as string[],
  });
  const [result, setResult] = useState<SimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showFlipped, setShowFlipped] = useState(false);

  useEffect(() => {
    fetchAgents().then((a: Agent[]) => {
      setAgents(a);
      if (a[0]) selectAgent(a[0]);
    }).catch(() => {});
  }, []);

  const selectAgent = (a: Agent) => {
    setSelected(a);
    setForm({
      max_transaction: a.max_transaction,
      daily_limit: a.daily_limit,
      requires_approval_above: a.requires_approval_above,
      allowed_categories: [...a.allowed_categories],
      blocked_categories: [...a.blocked_categories],
    });
    setResult(null);
    setError("");
  };

  const toggleCat = (cat: string, field: "allowed_categories" | "blocked_categories") => {
    const arr = form[field];
    setForm({
      ...form,
      [field]: arr.includes(cat) ? arr.filter(c => c !== cat) : [...arr, cat],
    });
  };

  const handleSimulate = async () => {
    if (!selected) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const payload: Record<string, unknown> = {};
      if (form.max_transaction !== selected.max_transaction) payload.max_transaction = form.max_transaction;
      if (form.daily_limit !== selected.daily_limit) payload.daily_limit = form.daily_limit;
      if (form.requires_approval_above !== selected.requires_approval_above) payload.requires_approval_above = form.requires_approval_above;
      const allowedChanged = JSON.stringify(form.allowed_categories.sort()) !== JSON.stringify([...selected.allowed_categories].sort());
      const blockedChanged = JSON.stringify(form.blocked_categories.sort()) !== JSON.stringify([...selected.blocked_categories].sort());
      if (allowedChanged) payload.allowed_categories = form.allowed_categories;
      if (blockedChanged) payload.blocked_categories = form.blocked_categories;
      const r = await simulatePolicy(selected.id, payload);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-violet-500/60 transition-all";

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Sliders className="w-5 h-5 text-violet-400" />
          <h1 className="text-2xl font-bold text-white">Policy Simulator</h1>
        </div>
        <p className="text-slate-400 text-sm">
          Propose a policy change and instantly see how it would have affected your historical transactions — without touching the live policy.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Agent selector + form */}
        <div className="space-y-4">
          {/* Agent selector */}
          <div className="glass p-4 rounded-2xl space-y-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Select Agent</p>
            {agents.map(a => (
              <div
                key={a.id}
                onClick={() => selectAgent(a)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all text-sm ${
                  selected?.id === a.id
                    ? "bg-violet-500/15 border border-violet-500/30 text-violet-300"
                    : "hover:bg-white/5 text-slate-300"
                }`}
              >
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500/25 to-purple-700/25 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-violet-400">{a.name[0]}</span>
                </div>
                <div className="min-w-0">
                  <p className="font-medium truncate">{a.name}</p>
                  <p className="text-xs text-slate-500 font-mono">{a.id}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Proposed policy form */}
          {selected && (
            <div className="glass p-5 rounded-2xl space-y-4">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Proposed Policy</p>

              <div>
                <label className="text-xs text-slate-400 mb-1 block">Max Transaction (₹)</label>
                <input
                  type="number"
                  value={form.max_transaction}
                  onChange={e => setForm({ ...form, max_transaction: Number(e.target.value) })}
                  className={inputClass}
                  min={1}
                />
                {form.max_transaction !== selected.max_transaction && (
                  <p className="text-xs text-amber-400 mt-1">
                    Was ₹{selected.max_transaction.toLocaleString("en-IN")}
                  </p>
                )}
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-1 block">Daily Limit (₹)</label>
                <input
                  type="number"
                  value={form.daily_limit}
                  onChange={e => setForm({ ...form, daily_limit: Number(e.target.value) })}
                  className={inputClass}
                  min={1}
                />
                {form.daily_limit !== selected.daily_limit && (
                  <p className="text-xs text-amber-400 mt-1">
                    Was ₹{selected.daily_limit.toLocaleString("en-IN")}
                  </p>
                )}
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-1 block">Approval Threshold (₹)</label>
                <input
                  type="number"
                  value={form.requires_approval_above}
                  onChange={e => setForm({ ...form, requires_approval_above: Number(e.target.value) })}
                  className={inputClass}
                  min={0}
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-2 block">Allowed Categories</label>
                <div className="flex flex-wrap gap-1.5">
                  {ALL_CATEGORIES.filter(c => !form.blocked_categories.includes(c)).map(cat => (
                    <button
                      key={cat}
                      onClick={() => toggleCat(cat, "allowed_categories")}
                      className={`px-2 py-0.5 rounded-full text-xs border transition-all ${
                        form.allowed_categories.includes(cat)
                          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                          : "bg-white/4 text-slate-400 border-white/8 hover:border-white/20"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 mb-2 block">Blocked Categories</label>
                <div className="flex flex-wrap gap-1.5">
                  {ALL_CATEGORIES.filter(c => !form.allowed_categories.includes(c)).map(cat => (
                    <button
                      key={cat}
                      onClick={() => toggleCat(cat, "blocked_categories")}
                      className={`px-2 py-0.5 rounded-full text-xs border transition-all ${
                        form.blocked_categories.includes(cat)
                          ? "bg-red-500/15 text-red-400 border-red-500/30"
                          : "bg-white/4 text-slate-400 border-white/8 hover:border-white/20"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleSimulate}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white transition-all disabled:opacity-50 shadow-lg shadow-violet-500/25"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                {loading ? "Simulating..." : "Run Simulation"}
              </button>

              {error && (
                <div className="px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/25 text-red-400 text-sm">
                  {error}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 space-y-4">
          {!result ? (
            <div className="glass p-12 rounded-2xl flex items-center justify-center h-64">
              <div className="text-center">
                <Sliders className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm">Configure a policy change and run the simulation</p>
                <p className="text-slate-600 text-xs mt-1">All historical transactions will be replayed against the proposed policy</p>
              </div>
            </div>
          ) : (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="glass p-4 rounded-xl">
                  <p className="text-xs text-slate-400 mb-1">Transactions Analyzed</p>
                  <p className="text-2xl font-bold text-white">{result.transactions_analyzed.toLocaleString()}</p>
                </div>
                <div className={`glass p-4 rounded-xl ${result.now_allowed_count > 0 ? "border-emerald-500/20" : ""}`}>
                  <p className="text-xs text-slate-400 mb-1">Now Allowed</p>
                  <p className="text-2xl font-bold text-emerald-400">+{result.now_allowed_count}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{formatINR(result.now_allowed_gmv)} GMV</p>
                </div>
                <div className={`glass p-4 rounded-xl ${result.additional_risky_exposure > 0 ? "border-red-500/20" : ""}`}>
                  <p className="text-xs text-slate-400 mb-1">Added Risk Exposure</p>
                  <p className={`text-2xl font-bold ${result.additional_risky_exposure > 0 ? "text-red-400" : "text-emerald-400"}`}>
                    {result.additional_risky_exposure > 0 ? `+${formatINR(result.additional_risky_exposure)}` : "₹0"}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">from high-risk txns</p>
                </div>
                <div className={`glass p-4 rounded-xl ${result.now_blocked_count > 0 ? "border-amber-500/20" : ""}`}>
                  <p className="text-xs text-slate-400 mb-1">Newly Blocked</p>
                  <p className="text-2xl font-bold text-amber-400">{result.now_blocked_count}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{formatINR(result.now_blocked_gmv)} GMV</p>
                </div>
              </div>

              {/* Decision distribution comparison */}
              <div className="glass p-5 rounded-2xl">
                <h2 className="text-sm font-semibold text-white mb-4">Decision Distribution Shift</h2>
                <DecisionBar before={result.before} after={result.after} />
              </div>

              {/* Policy diff */}
              <div className="glass p-5 rounded-2xl">
                <h2 className="text-sm font-semibold text-white mb-4">Policy Comparison</h2>
                <div className="grid grid-cols-2 gap-6">
                  {[
                    { label: "Current Policy", p: result.current_policy, accent: "text-slate-300" },
                    { label: "Proposed Policy", p: result.proposed_policy, accent: "text-violet-300" },
                  ].map(({ label, p, accent }) => (
                    <div key={label}>
                      <p className={`text-xs font-semibold uppercase tracking-wider mb-3 ${accent}`}>{label}</p>
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Max Transaction</span>
                          <span className="text-white font-medium">₹{p.max_transaction.toLocaleString("en-IN")}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Daily Limit</span>
                          <span className="text-white font-medium">₹{p.daily_limit.toLocaleString("en-IN")}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Approval Above</span>
                          <span className="text-white font-medium">₹{p.requires_approval_above.toLocaleString("en-IN")}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block mb-1">Allowed</span>
                          <div className="flex flex-wrap gap-1">
                            {p.allowed_categories.map(c => (
                              <span key={c} className="px-1.5 py-0.5 rounded-full bg-emerald-500/12 text-emerald-400 border border-emerald-500/25">{c}</span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="text-slate-500 block mb-1">Blocked</span>
                          <div className="flex flex-wrap gap-1">
                            {p.blocked_categories.map(c => (
                              <span key={c} className="px-1.5 py-0.5 rounded-full bg-red-500/12 text-red-400 border border-red-500/25">{c}</span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Flipped transactions */}
              {result.flipped_transactions.length > 0 && (
                <div className="glass rounded-2xl overflow-hidden">
                  <button
                    onClick={() => setShowFlipped(!showFlipped)}
                    className="w-full flex items-center justify-between px-5 py-4 text-sm font-semibold text-white hover:bg-white/3 transition-colors"
                  >
                    <span>Changed Decisions ({result.flipped_transactions.length} transactions)</span>
                    {showFlipped ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                  </button>
                  {showFlipped && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-white/5">
                            {["TXN ID", "Product", "Amount", "Risk", "Before", "", "After"].map(h => (
                              <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {result.flipped_transactions.map(t => (
                            <tr key={t.transaction_id} className="border-b border-white/3 hover:bg-white/3">
                              <td className="px-4 py-3 font-mono text-xs text-violet-400">{t.transaction_id}</td>
                              <td className="px-4 py-3 text-slate-200 max-w-32 truncate">{t.product}</td>
                              <td className="px-4 py-3 font-semibold text-white whitespace-nowrap">₹{t.amount.toLocaleString("en-IN")}</td>
                              <td className="px-4 py-3">
                                <span className={`text-xs font-bold ${(t.risk_score ?? 50) <= 30 ? "text-emerald-400" : (t.risk_score ?? 50) <= 70 ? "text-amber-400" : "text-red-400"}`}>
                                  {t.risk_score?.toFixed(0) ?? "—"}
                                </span>
                              </td>
                              <td className="px-4 py-3"><DecisionBadge decision={t.before} size="sm" /></td>
                              <td className="px-4 py-3"><ArrowRight className="w-3.5 h-3.5 text-slate-600" /></td>
                              <td className="px-4 py-3"><DecisionBadge decision={t.after} size="sm" /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Economic tradeoff summary */}
              <div className={`p-4 rounded-2xl border ${
                result.additional_risky_exposure > 50000
                  ? "bg-red-500/8 border-red-500/20"
                  : result.now_allowed_count > 0
                  ? "bg-amber-500/8 border-amber-500/20"
                  : "bg-emerald-500/8 border-emerald-500/20"
              }`}>
                <div className="flex items-start gap-3">
                  {result.additional_risky_exposure > 50000
                    ? <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                    : result.now_allowed_count > 0
                    ? <TrendingUp className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                    : <TrendingDown className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                  }
                  <div>
                    <p className={`text-sm font-semibold mb-0.5 ${
                      result.additional_risky_exposure > 50000 ? "text-red-300"
                      : result.now_allowed_count > 0 ? "text-amber-300"
                      : "text-emerald-300"
                    }`}>
                      Economic Tradeoff Analysis
                    </p>
                    <p className="text-xs text-slate-400">
                      {result.now_allowed_count > 0
                        ? `This change would allow ${result.now_allowed_count} additional transactions (${formatINR(result.now_allowed_gmv)} GMV), `
                        : "No additional transactions would be allowed. "}
                      {result.additional_risky_exposure > 0
                        ? `exposing ${formatINR(result.additional_risky_exposure)} of additional risky GMV.`
                        : "with no increase in risky exposure."}
                      {result.now_blocked_count > 0
                        ? ` Additionally, ${result.now_blocked_count} transactions (${formatINR(result.now_blocked_gmv)} GMV) would be newly blocked.`
                        : ""}
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
