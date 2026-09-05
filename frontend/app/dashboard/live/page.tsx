"use client";
import { useEffect, useState, useCallback } from "react";
import { fetchLive, humanReview } from "@/lib/api";
import DecisionBadge from "@/components/DecisionBadge";
import RiskMeter from "@/components/RiskMeter";
import { RefreshCw, CheckCircle, XCircle } from "lucide-react";
import { timeAgo } from "@/lib/utils";

interface LiveTxn {
  id: string; amount: number; decision: string;
  risk_score: number; merchant_name: string; product: string; created_at: string;
}

export default function LivePage() {
  const [txns, setTxns] = useState<LiveTxn[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { const d = await fetchLive(20); setTxns(d); } catch {}
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, [load]);

  const handleReview = async (id: string, approved: boolean) => {
    setReviewing(id);
    try { await humanReview(id, approved); await load(); } catch {}
    finally { setReviewing(null); }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Feed</h1>
          <p className="text-slate-400 text-sm mt-1">Real-time transaction decisions</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 text-sm transition-all">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-400">Loading...</div>
      ) : txns.length === 0 ? (
        <div className="glass p-12 rounded-2xl text-center">
          <p className="text-slate-400">No transactions yet. Head to Evaluate to create some.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {txns.map((t) => (
            <div key={t.id} className={`glass p-4 rounded-2xl flex items-center gap-4 slide-in ${
              t.decision === "REVIEW" ? "border-amber-500/20" : ""
            }`}>
              <RiskMeter score={t.risk_score ?? 50} size="md" showLabel={false} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-mono text-slate-500">{t.id}</span>
                  <span className="text-sm font-medium text-white truncate">{t.product}</span>
                </div>
                <p className="text-xs text-slate-500">{t.merchant_name} · {t.created_at ? timeAgo(t.created_at) : ""}</p>
              </div>
              <span className="text-base font-bold text-white whitespace-nowrap">
                ₹{t.amount?.toLocaleString("en-IN")}
              </span>
              <DecisionBadge decision={t.decision} />
              {t.decision === "REVIEW" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleReview(t.id, true)}
                    disabled={reviewing === t.id}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 text-xs font-medium border border-emerald-500/25 transition-all"
                  >
                    <CheckCircle className="w-3.5 h-3.5" /> Approve
                  </button>
                  <button
                    onClick={() => handleReview(t.id, false)}
                    disabled={reviewing === t.id}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-500/15 hover:bg-red-500/25 text-red-400 text-xs font-medium border border-red-500/25 transition-all"
                  >
                    <XCircle className="w-3.5 h-3.5" /> Deny
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
