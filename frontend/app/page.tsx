"use client";
import { useEffect, useState } from "react";
import { fetchStats, fetchMetrics, fetchLive, fetchRevenueImpact } from "@/lib/api";
import { formatLargeNumber, riskColor, timeAgo } from "@/lib/utils";
import DecisionBadge from "@/components/DecisionBadge";
import RiskMeter from "@/components/RiskMeter";
import {
  ShieldCheck, TrendingUp, AlertTriangle, DollarSign,
  Activity, Clock, Zap, BarChart2, Sparkles, ShieldAlert
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from "recharts";

interface Stats {
  total_evaluated: number; total_allowed: number;
  total_reviewed: number; total_blocked: number;
  money_protected: number; total_gmv: number;
  avg_risk_score: number; p50_latency: number; p95_latency: number;
}

interface Metrics {
  precision: number; recall: number; f1: number; roc_auc: number;
  protection_rate: number;
}

interface LiveTxn {
  id: string; amount: number; decision: string;
  risk_score: number; merchant_name: string; product: string;
  created_at: string;
}

interface RevenueImpact {
  upsells_proposed: number; upsells_allowed: number;
  upsells_blocked: number; upsells_review: number;
  incremental_gmv: number; upsell_acceptance_rate: number;
  manipulative_exposure_blocked: number;
}

const PIE_COLORS = { ALLOW: "#10b981", REVIEW: "#f59e0b", BLOCK: "#ef4444" };

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [live, setLive] = useState<LiveTxn[]>([]);
  const [revenue, setRevenue] = useState<RevenueImpact | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [s, m, l, r] = await Promise.all([fetchStats(), fetchMetrics(), fetchLive(8), fetchRevenueImpact()]);
      setStats(s); setMetrics(m); setLive(l); setRevenue(r);
    } catch {/* backend may be offline */}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, []);

  const pieData = stats ? [
    { name: "ALLOW", value: stats.total_allowed },
    { name: "REVIEW", value: stats.total_reviewed },
    { name: "BLOCK", value: stats.total_blocked },
  ] : [];

  const StatCard = ({ icon: Icon, label, value, sub, color = "violet" }: {
    icon: React.ElementType; label: string; value: string | number; sub?: string; color?: string;
  }) => {
    const colorMap: Record<string, string> = {
      violet: "from-violet-500/20 to-purple-500/10 border-violet-500/20",
      green: "from-emerald-500/20 to-teal-500/10 border-emerald-500/20",
      amber: "from-amber-500/20 to-orange-500/10 border-amber-500/20",
      red: "from-red-500/20 to-rose-500/10 border-red-500/20",
      blue: "from-blue-500/20 to-cyan-500/10 border-blue-500/20",
    };
    const iconMap: Record<string, string> = {
      violet: "text-violet-400", green: "text-emerald-400",
      amber: "text-amber-400", red: "text-red-400", blue: "text-blue-400",
    };
    return (
      <div className={`glass bg-gradient-to-br ${colorMap[color]} p-5 rounded-2xl`}>
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-xl bg-white/5`}>
            <Icon className={`w-5 h-5 ${iconMap[color]}`} />
          </div>
        </div>
        <p className="text-2xl font-bold text-white mb-0.5">{value}</p>
        <p className="text-sm font-medium text-slate-300">{label}</p>
        {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-violet-500/40 border-t-violet-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Command Center</h1>
          <p className="text-slate-400 text-sm mt-0.5">PayWall.ai — Real-time AI agent payment oversight</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-medium text-emerald-400">Guard Active</span>
        </div>
      </div>

      {/* Merchant Revenue Impact — PRD Section 17.A */}
      <div className="glass p-5 rounded-2xl bg-gradient-to-br from-emerald-500/10 via-transparent to-transparent border-emerald-500/15">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">Merchant Revenue Impact</h2>
          </div>
          <p className="text-xs text-slate-500">Upsell Agent — same Guard pipeline, real incremental GMV</p>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-white/3 rounded-xl p-3">
            <p className="text-xs text-slate-400">Upsells Proposed</p>
            <p className="text-xl font-bold text-white">{revenue?.upsells_proposed?.toLocaleString() ?? "—"}</p>
          </div>
          <div className="bg-white/3 rounded-xl p-3">
            <p className="text-xs text-slate-400">Allowed</p>
            <p className="text-xl font-bold text-emerald-400">{revenue?.upsells_allowed?.toLocaleString() ?? "—"}</p>
          </div>
          <div className="bg-white/3 rounded-xl p-3">
            <p className="text-xs text-slate-400">Blocked (manipulative)</p>
            <p className="text-xl font-bold text-red-400">{revenue?.upsells_blocked?.toLocaleString() ?? "—"}</p>
          </div>
          <div className="bg-white/3 rounded-xl p-3">
            <p className="text-xs text-slate-400">Sent to Review</p>
            <p className="text-xl font-bold text-amber-400">{revenue?.upsells_review?.toLocaleString() ?? "—"}</p>
          </div>
          <div className="bg-white/3 rounded-xl p-3">
            <p className="text-xs text-slate-400">Acceptance Rate</p>
            <p className="text-xl font-bold text-white">{revenue ? `${(revenue.upsell_acceptance_rate * 100).toFixed(0)}%` : "—"}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-500/8 border border-emerald-500/20">
            <TrendingUp className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <p className="text-xs text-slate-400">Incremental GMV from Upsells</p>
              <p className="text-lg font-bold text-emerald-300">{formatLargeNumber(revenue?.incremental_gmv ?? 0)}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/8 border border-red-500/20">
            <ShieldAlert className="w-5 h-5 text-red-400 shrink-0" />
            <div>
              <p className="text-xs text-slate-400">Manipulative-Upsell Exposure Blocked</p>
              <p className="text-lg font-bold text-red-300">{formatLargeNumber(revenue?.manipulative_exposure_blocked ?? 0)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={ShieldCheck} label="Evaluated" value={stats?.total_evaluated?.toLocaleString() ?? "—"} sub="Total transactions" color="violet" />
        <StatCard icon={TrendingUp} label="Allowed" value={stats?.total_allowed?.toLocaleString() ?? "—"} sub={`${stats ? ((stats.total_allowed / (stats.total_evaluated || 1)) * 100).toFixed(1) : 0}% approval rate`} color="green" />
        <StatCard icon={AlertTriangle} label="Blocked" value={stats?.total_blocked?.toLocaleString() ?? "—"} sub={`${stats ? ((stats.total_blocked / (stats.total_evaluated || 1)) * 100).toFixed(1) : 0}% block rate`} color="red" />
        <StatCard icon={DollarSign} label="Protected" value={formatLargeNumber(stats?.money_protected ?? 0)} sub="Risky GMV stopped" color="amber" />
      </div>

      {/* Secondary stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={BarChart2} label="Avg Risk Score" value={`${stats?.avg_risk_score?.toFixed(1) ?? "—"}/100`} color="blue" />
        <StatCard icon={Activity} label="In Review" value={stats?.total_reviewed?.toLocaleString() ?? "—"} sub="Awaiting human" color="amber" />
        <StatCard icon={Clock} label="P50 Latency" value={`${stats?.p50_latency?.toFixed(0) ?? "—"}ms`} sub="Median decision time" color="violet" />
        <StatCard icon={Zap} label="P95 Latency" value={`${stats?.p95_latency?.toFixed(0) ?? "—"}ms`} sub="95th percentile" color="blue" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Decision Pie */}
        <div className="glass p-5 rounded-2xl">
          <h2 className="text-sm font-semibold text-white mb-4">Decision Distribution</h2>
          {pieData.some(d => d.value > 0) ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width={140} height={140}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={3} dataKey="value">
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={PIE_COLORS[entry.name as keyof typeof PIE_COLORS]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {pieData.map(d => (
                  <div key={d.name} className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ background: PIE_COLORS[d.name as keyof typeof PIE_COLORS] }} />
                    <span className="text-xs text-slate-300">{d.name}</span>
                    <span className="text-xs font-bold text-white ml-auto">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
              No transactions yet
            </div>
          )}
        </div>

        {/* ML Metrics */}
        {metrics && (
          <div className="glass p-5 rounded-2xl lg:col-span-2">
            <h2 className="text-sm font-semibold text-white mb-4">ML Performance Metrics</h2>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "Precision", value: metrics.precision, color: "#10b981" },
                { label: "Recall", value: metrics.recall, color: "#6366f1" },
                { label: "F1 Score", value: metrics.f1, color: "#8b5cf6" },
                { label: "ROC-AUC", value: metrics.roc_auc, color: "#f59e0b" },
              ].map(m => (
                <div key={m.label} className="bg-white/3 rounded-xl p-3">
                  <p className="text-xs text-slate-400 mb-1">{m.label}</p>
                  <p className="text-xl font-bold" style={{ color: m.color }}>
                    {(m.value * 100).toFixed(1)}%
                  </p>
                  <div className="mt-2 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${m.value * 100}%`, background: m.color }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Live feed */}
      <div className="glass p-5 rounded-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Live Decisions</h2>
          <div className="flex items-center gap-1.5 text-xs text-emerald-400">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Auto-refreshing
          </div>
        </div>
        {live.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">No transactions yet. Use the Evaluate page to test scenarios.</p>
        ) : (
          <div className="space-y-2">
            {live.map((t) => (
              <div key={t.id} className="flex items-center gap-4 px-4 py-3 rounded-xl bg-white/3 hover:bg-white/5 transition-colors slide-in">
                <RiskMeter score={t.risk_score ?? 50} size="sm" showLabel={false} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-slate-500">{t.id}</span>
                    <span className="text-xs text-slate-300 truncate">{t.product}</span>
                  </div>
                  <p className="text-xs text-slate-500">{t.merchant_name}</p>
                </div>
                <span className="text-sm font-bold text-white whitespace-nowrap">
                  ₹{t.amount?.toLocaleString("en-IN")}
                </span>
                <DecisionBadge decision={t.decision} size="sm" />
                <span className="text-xs text-slate-600 whitespace-nowrap">
                  {t.created_at ? timeAgo(t.created_at) : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
