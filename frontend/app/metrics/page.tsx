"use client";
import { useEffect, useState } from "react";
import { fetchMetrics, fetchHoldoutMetrics } from "@/lib/api";
import { BarChart2, TrendingUp, ShieldCheck, Clock, Database } from "lucide-react";
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

interface Metrics {
  precision: number; recall: number; f1: number; roc_auc: number;
  false_positive_rate: number; false_positive_gmv: number;
  risky_gmv: number; risky_gmv_blocked: number; protection_rate: number;
  review_rate: number; avg_decision_latency_ms: number;
  p50_latency: number; p95_latency: number;
}

interface HoldoutReport {
  dataset: { holdout_size: number; seed: number; note: string };
  detection: { precision: number; recall: number; f1: number; roc_auc: number | null; tp: number; fp: number; fn: number; tn: number };
  false_positive_cost: { false_positive_rate: number; legitimate_transactions_blocked: number; legitimate_gmv_blocked: number };
  money_protected: { total_transactions: number; total_gmv: number; risky_gmv: number; risky_gmv_blocked: number; pct_risky_gmv_protected: number };
  decisions: { allow_rate: number; review_rate: number; block_rate: number };
  scenario_breakdown: Record<string, { count: number; allow_rate: number; review_rate: number; block_rate: number }>;
  latency_ms: { p50: number; p95: number; avg: number };
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [holdout, setHoldout] = useState<HoldoutReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(() => {}).finally(() => setLoading(false));
    fetchHoldoutMetrics().then(setHoldout).catch(() => {});
  }, []);

  if (loading) return <div className="flex items-center justify-center h-full text-slate-400">Loading metrics...</div>;
  if (!metrics) return <div className="flex items-center justify-center h-full text-slate-400">No data yet.</div>;

  const radarData = [
    { metric: "Precision", value: metrics.precision * 100 },
    { metric: "Recall", value: metrics.recall * 100 },
    { metric: "F1 Score", value: metrics.f1 * 100 },
    { metric: "ROC-AUC", value: metrics.roc_auc * 100 },
    { metric: "Protection", value: metrics.protection_rate * 100 },
  ];

  const barData = [
    { name: "P50", value: metrics.p50_latency },
    { name: "P95", value: metrics.p95_latency },
    { name: "Avg", value: metrics.avg_decision_latency_ms },
  ];

  const MetricCard = ({ label, value, sub, color = "#6366f1" }: { label: string; value: string; sub?: string; color?: string }) => (
    <div className="glass p-5 rounded-2xl">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Evaluation Metrics</h1>
        <p className="text-slate-400 text-sm mt-1">Model performance on live transaction data</p>
      </div>

      {/* Core ML metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Precision" value={`${(metrics.precision * 100).toFixed(1)}%`} sub="True positive accuracy" color="#10b981" />
        <MetricCard label="Recall" value={`${(metrics.recall * 100).toFixed(1)}%`} sub="Threat detection rate" color="#6366f1" />
        <MetricCard label="F1 Score" value={`${(metrics.f1 * 100).toFixed(1)}%`} sub="Balanced measure" color="#8b5cf6" />
        <MetricCard label="ROC-AUC" value={`${(metrics.roc_auc * 100).toFixed(1)}%`} sub="Discrimination power" color="#f59e0b" />
      </div>

      {/* Money metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard label="Risky GMV Protected" value={`₹${(metrics.risky_gmv_blocked / 100).toFixed(0)}`} sub="Blocked risky transactions value" color="#10b981" />
        <MetricCard label="Protection Rate" value={`${(metrics.protection_rate * 100).toFixed(1)}%`} sub="Of risky GMV stopped" color="#10b981" />
        <MetricCard label="False Positive Cost" value={`₹${(metrics.false_positive_gmv / 100).toFixed(0)}`} sub="Legitimate GMV blocked" color="#f59e0b" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar chart */}
        <div className="glass p-5 rounded-2xl">
          <h2 className="text-sm font-semibold text-white mb-4">Performance Radar</h2>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.06)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Radar name="Score" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Latency chart */}
        <div className="glass p-5 rounded-2xl">
          <h2 className="text-sm font-semibold text-white mb-1">Decision Latency (ms)</h2>
          <p className="text-xs text-slate-500 mb-4">Target: P50 &lt;200ms · P95 &lt;500ms</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} barSize={40}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#0c1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, color: "#fff" }}
                formatter={(v: number) => [`${v.toFixed(1)}ms`, "Latency"]}
              />
              <Bar dataKey="value" fill="#6366f1" radius={[6,6,0,0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-3">
            <span className={`text-xs font-medium ${metrics.p50_latency < 200 ? "text-emerald-400" : "text-red-400"}`}>
              P50: {metrics.p50_latency.toFixed(0)}ms {metrics.p50_latency < 200 ? "✓" : "✗"}
            </span>
            <span className={`text-xs font-medium ${metrics.p95_latency < 500 ? "text-emerald-400" : "text-red-400"}`}>
              P95: {metrics.p95_latency.toFixed(0)}ms {metrics.p95_latency < 500 ? "✓" : "✗"}
            </span>
          </div>
        </div>
      </div>

      {/* Review metrics */}
      <div className="glass p-5 rounded-2xl">
        <h2 className="text-sm font-semibold text-white mb-4">Review & False Positive Analysis</h2>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-slate-400 mb-1">False Positive Rate</p>
            <p className="text-2xl font-bold text-amber-400">{(metrics.false_positive_rate * 100).toFixed(2)}%</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1">Review Rate</p>
            <p className="text-2xl font-bold text-violet-400">{(metrics.review_rate * 100).toFixed(2)}%</p>
            <p className="text-xs text-slate-500">Transactions requiring human</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1">Avg Decision Time</p>
            <p className="text-2xl font-bold text-blue-400">{metrics.avg_decision_latency_ms.toFixed(0)}ms</p>
          </div>
        </div>
      </div>

      {/* Held-out dataset evaluation */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Database className="w-4 h-4 text-violet-400" />
          <h2 className="text-lg font-bold text-white">Held-Out Dataset Evaluation</h2>
        </div>
        <p className="text-slate-500 text-xs mb-4">
          {holdout
            ? `Computed once against a ${holdout.dataset.holdout_size.toLocaleString()}-row synthetic holdout split (seed ${holdout.dataset.seed}) — never used to tune thresholds. Independent of the live demo data above.`
            : "Run backend/scripts/generate_dataset.py then evaluate_dataset.py to populate this section."}
        </p>

        {holdout && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard label="Precision" value={`${(holdout.detection.precision * 100).toFixed(1)}%`} color="#10b981" />
              <MetricCard label="Recall" value={`${(holdout.detection.recall * 100).toFixed(1)}%`} sub="Attacks caught (REVIEW/BLOCK)" color="#6366f1" />
              <MetricCard label="F1 Score" value={`${(holdout.detection.f1 * 100).toFixed(1)}%`} color="#8b5cf6" />
              <MetricCard
                label="ROC-AUC"
                value={holdout.detection.roc_auc !== null ? `${(holdout.detection.roc_auc * 100).toFixed(1)}%` : "—"}
                color="#f59e0b"
              />
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              <MetricCard
                label="Legit Transactions Wrongly Blocked"
                value={holdout.false_positive_cost.legitimate_transactions_blocked.toLocaleString()}
                sub={`₹${holdout.false_positive_cost.legitimate_gmv_blocked.toLocaleString()} GMV`}
                color={holdout.false_positive_cost.legitimate_transactions_blocked === 0 ? "#10b981" : "#ef4444"}
              />
              <MetricCard
                label="Risky GMV Protected"
                value={`${(holdout.money_protected.pct_risky_gmv_protected * 100).toFixed(1)}%`}
                sub={`₹${holdout.money_protected.risky_gmv_blocked.toLocaleString()} of ₹${holdout.money_protected.risky_gmv.toLocaleString()}`}
                color="#10b981"
              />
              <MetricCard
                label="Batch Latency (Policy + ML)"
                value={`P95 ${holdout.latency_ms.p95}ms`}
                sub={`Avg ${holdout.latency_ms.avg}ms — excludes live LLM call`}
                color="#3b82f6"
              />
            </div>

            <div className="glass p-5 rounded-2xl">
              <h3 className="text-sm font-semibold text-white mb-3">Detection by Attack Type</h3>
              <div className="space-y-2">
                {Object.entries(holdout.scenario_breakdown).map(([scenario, s]) => (
                  <div key={scenario} className="flex items-center gap-3 text-xs">
                    <span className="w-40 shrink-0 text-slate-300 capitalize">{scenario.replace(/_/g, " ")}</span>
                    <span className="w-16 shrink-0 text-slate-500">{s.count.toLocaleString()} txns</span>
                    <div className="flex-1 flex h-2 rounded-full overflow-hidden bg-white/5">
                      <div className="bg-emerald-500" style={{ width: `${s.allow_rate * 100}%` }} />
                      <div className="bg-amber-500" style={{ width: `${s.review_rate * 100}%` }} />
                      <div className="bg-red-500" style={{ width: `${s.block_rate * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-4 mt-3 text-xs text-slate-500">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Allow</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> Review</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Block</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
