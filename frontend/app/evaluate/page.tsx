"use client";
import { useState, useEffect } from "react";
import { fetchAgents, fetchMerchants, evaluateTransaction, fetchLlmStatus, toggleLlm, proposeUpsell } from "@/lib/api";
import DecisionBadge from "@/components/DecisionBadge";
import RiskMeter from "@/components/RiskMeter";
import { ShieldCheck, Loader2, CheckCircle, XCircle, AlertCircle, ChevronDown, PowerOff, Power, Sparkles } from "lucide-react";

const DEMO_SCENARIOS = [
  {
    label: "Normal Purchase — Running Shoes",
    tag: "ALLOW",
    agent_id: "AGT-001", merchant_id: "MER-001",
    amount: 4799, category: "sports", product: "Nike Running Shoes",
    user_intent: "Buy running shoes under 5000",
    is_upsell: false,
  },
  {
    label: "Manipulated Upsell — Protection Plan",
    tag: "BLOCK",
    agent_id: "AGT-001", merchant_id: "MER-001",
    amount: 14999, category: "insurance", product: "Premium Protection Plan",
    user_intent: "Buy running shoes under 5000",
    is_upsell: true,
  },
  {
    label: "Budget Violation — Over Limit",
    tag: "BLOCK",
    agent_id: "AGT-001", merchant_id: "MER-009",
    amount: 8500, category: "electronics", product: "Laptop Stand",
    user_intent: "Buy a cheap laptop stand",
    is_upsell: false,
  },
  {
    label: "Suspicious Merchant",
    tag: "BLOCK",
    agent_id: "AGT-001", merchant_id: "MER-007",
    amount: 2000, category: "electronics", product: "USB Hub",
    user_intent: "Buy a USB hub",
    is_upsell: false,
  },
  {
    label: "Human Review Required",
    tag: "REVIEW",
    agent_id: "AGT-001", merchant_id: "MER-010",
    amount: 3500, category: "groceries", product: "Monthly Grocery Pack",
    user_intent: "Order monthly groceries",
    is_upsell: false,
  },
];

interface Result {
  transaction_id: string;
  decision: string;
  risk_score: number;
  intent_match_score: number;
  policy_violations: string[];
  policy_checks: { check: string; passed: boolean; detail: string }[];
  reason: string;
  confidence: number;
  decision_latency_ms: number;
  is_upsell?: boolean;
}

interface UpsellResult {
  proposed: boolean;
  reason: string;
  decision?: Result;
}

export default function EvaluatePage() {
  const [agents, setAgents] = useState<{ id: string; name: string }[]>([]);
  const [merchants, setMerchants] = useState<{ id: string; name: string }[]>([]);
  const [form, setForm] = useState({
    agent_id: "AGT-001", merchant_id: "MER-001",
    amount: 4799, currency: "INR",
    category: "sports", product: "Nike Running Shoes",
    user_intent: "Buy running shoes under 5000",
    is_upsell: false,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [llmDisabled, setLlmDisabled] = useState(false);
  const [llmToggling, setLlmToggling] = useState(false);
  const [upsell, setUpsell] = useState<UpsellResult | null>(null);
  const [upsellLoading, setUpsellLoading] = useState(false);

  useEffect(() => {
    fetchAgents().then(setAgents).catch(() => {});
    fetchMerchants().then(setMerchants).catch(() => {});
    fetchLlmStatus().then(s => setLlmDisabled(s.llm_disabled)).catch(() => {});
  }, []);

  const handleToggleLlm = async () => {
    setLlmToggling(true);
    try {
      const next = !llmDisabled;
      const r = await toggleLlm(next);
      setLlmDisabled(r.llm_disabled);
    } catch {
      // ignore
    } finally {
      setLlmToggling(false);
    }
  };

  const handleScenario = (s: typeof DEMO_SCENARIOS[0]) => {
    const { label, tag, ...rest } = s;
    setForm({ ...form, ...rest });
    setResult(null);
    setUpsell(null);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setUpsell(null);
    setError("");
    try {
      const r = await evaluateTransaction(form);
      setResult(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleProposeUpsell = async () => {
    if (!result) return;
    setUpsellLoading(true);
    setUpsell(null);
    try {
      const r = await proposeUpsell(result.transaction_id);
      setUpsell(r);
    } catch (err: unknown) {
      setUpsell({ proposed: false, reason: err instanceof Error ? err.message : "Upsell proposal failed" });
    } finally {
      setUpsellLoading(false);
    }
  };

  const inputClass = "w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-violet-500/60 focus:bg-white/8 transition-all";

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Transaction Evaluator</h1>
          <p className="text-slate-400 text-sm mt-1">Test PayWall.ai against any payment scenario in real-time</p>
        </div>
        <button
          onClick={handleToggleLlm}
          disabled={llmToggling}
          title="Simulate the LLM (Layer 3) going down to demonstrate fail-closed behavior"
          className={`flex items-center gap-2 px-3 py-2 text-xs rounded-xl border transition-all shrink-0 ${
            llmDisabled
              ? "bg-red-500/15 border-red-500/30 text-red-300 hover:bg-red-500/25"
              : "bg-emerald-500/10 border-emerald-500/25 text-emerald-300 hover:bg-emerald-500/20"
          }`}
        >
          {llmDisabled ? <PowerOff className="w-3.5 h-3.5" /> : <Power className="w-3.5 h-3.5" />}
          AI Reasoning: {llmDisabled ? "Disabled" : "Online"}
        </button>
      </div>

      {/* Scenarios */}
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Demo Scenarios</p>
        <div className="flex flex-wrap gap-2">
          {DEMO_SCENARIOS.map((s) => (
            <button
              key={s.label}
              onClick={() => handleScenario(s)}
              className="flex items-center gap-2 px-3 py-2 text-xs rounded-xl bg-white/5 hover:bg-violet-500/15 border border-white/8 hover:border-violet-500/30 text-slate-300 hover:text-violet-300 transition-all"
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                s.tag === 'ALLOW' ? 'bg-emerald-400' :
                s.tag === 'BLOCK' ? 'bg-red-400' : 'bg-amber-400'
              }`} />
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <form onSubmit={handleSubmit} className="glass p-6 rounded-2xl space-y-4">
          <h2 className="text-sm font-semibold text-white">Payment Request</h2>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Agent</label>
              <select value={form.agent_id} onChange={e => setForm({...form, agent_id: e.target.value})} className={inputClass}>
                {agents.map(a => <option key={a.id} value={a.id} className="bg-slate-900">{a.name}</option>)}
                <option value="AGT-001" className="bg-slate-900">Shopping Assistant</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Merchant</label>
              <select value={form.merchant_id} onChange={e => setForm({...form, merchant_id: e.target.value})} className={inputClass}>
                {merchants.map(m => <option key={m.id} value={m.id} className="bg-slate-900">{m.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Amount (₹)</label>
              <input type="number" value={form.amount} onChange={e => setForm({...form, amount: Number(e.target.value)})} className={inputClass} min={1} required />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Category</label>
              <input value={form.category} onChange={e => setForm({...form, category: e.target.value})} className={inputClass} required />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">Product Description</label>
            <input value={form.product} onChange={e => setForm({...form, product: e.target.value})} className={inputClass} required />
          </div>

          <div>
            <label className="text-xs text-slate-400 mb-1 block">User&apos;s Original Intent</label>
            <textarea
              value={form.user_intent}
              onChange={e => setForm({...form, user_intent: e.target.value})}
              rows={2}
              className={`${inputClass} resize-none`}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white transition-all disabled:opacity-50 shadow-lg shadow-violet-500/25"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            {loading ? "Evaluating..." : "Evaluate Transaction"}
          </button>

          {error && (
            <div className="px-3 py-2.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-400 text-sm">
              {error}
            </div>
          )}
        </form>

        {/* Result */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* Decision card */}
              <div className={`glass p-6 rounded-2xl border-2 ${
                result.decision === "ALLOW" ? "border-emerald-500/30 glow-green" :
                result.decision === "BLOCK" ? "border-red-500/30 glow-red" :
                "border-amber-500/30 glow-amber"
              }`}>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Decision</p>
                    <DecisionBadge decision={result.decision} />
                  </div>
                  <RiskMeter score={result.risk_score} size="lg" />
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-white/4 rounded-xl p-3">
                    <p className="text-xs text-slate-400">Intent Match</p>
                    <p className="text-lg font-bold text-white">{(result.intent_match_score * 100).toFixed(0)}%</p>
                  </div>
                  <div className="bg-white/4 rounded-xl p-3">
                    <p className="text-xs text-slate-400">Confidence</p>
                    <p className="text-lg font-bold text-white">{(result.confidence * 100).toFixed(0)}%</p>
                  </div>
                  <div className="bg-white/4 rounded-xl p-3">
                    <p className="text-xs text-slate-400">Latency</p>
                    <p className="text-lg font-bold text-white">{result.decision_latency_ms.toFixed(0)}ms</p>
                  </div>
                  <div className="bg-white/4 rounded-xl p-3">
                    <p className="text-xs text-slate-400">TXN ID</p>
                    <p className="text-xs font-mono font-bold text-violet-400">{result.transaction_id}</p>
                  </div>
                </div>

                <div className="bg-white/4 rounded-xl p-3 mb-4">
                  <p className="text-xs text-slate-400 mb-1">AI Explanation</p>
                  <p className="text-sm text-slate-200">{result.reason}</p>
                </div>

                {result.decision === "ALLOW" && !result.is_upsell && (
                  <button
                    onClick={handleProposeUpsell}
                    disabled={upsellLoading}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-xs bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 transition-all disabled:opacity-50"
                  >
                    {upsellLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                    {upsellLoading ? "Upsell Agent proposing..." : "Propose Upsell (Section 2a)"}
                  </button>
                )}
              </div>

              {/* Upsell proposal result */}
              {upsell && (
                <div className={`glass p-5 rounded-2xl border ${
                  !upsell.proposed ? "border-white/10" :
                  upsell.decision?.decision === "ALLOW" ? "border-emerald-500/30" :
                  upsell.decision?.decision === "BLOCK" ? "border-red-500/30" : "border-amber-500/30"
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Upsell Agent</p>
                  </div>
                  <p className="text-sm text-slate-200 mb-2">{upsell.reason}</p>
                  {upsell.decision && (
                    <div className="flex items-center gap-3 mt-3">
                      <DecisionBadge decision={upsell.decision.decision} size="sm" />
                      <RiskMeter score={upsell.decision.risk_score} size="sm" showLabel={false} />
                      <span className="text-xs text-slate-400">
                        Intent match {(upsell.decision.intent_match_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Policy checks */}
              <div className="glass p-5 rounded-2xl">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Policy Checks</p>
                <div className="space-y-2">
                  {result.policy_checks.map((c, i) => (
                    <div key={i} className="flex items-start gap-3 px-3 py-2.5 rounded-xl bg-white/3">
                      {c.passed
                        ? <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        : <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                      }
                      <div>
                        <p className={`text-xs font-medium ${c.passed ? "text-slate-200" : "text-red-300"}`}>{c.check}</p>
                        <p className="text-xs text-slate-500">{c.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="glass p-8 rounded-2xl flex items-center justify-center h-full">
              <div className="text-center">
                <ShieldCheck className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm">Select a scenario or fill the form</p>
                <p className="text-slate-600 text-xs mt-1">Results will appear here</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
