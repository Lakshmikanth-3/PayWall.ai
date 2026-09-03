import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatLargeNumber(n: number): string {
  if (n >= 10_00_000) return `₹${(n / 10_00_000).toFixed(2)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}K`;
  return `₹${n.toFixed(0)}`;
}

export function riskColor(score: number): string {
  if (score <= 30) return "text-emerald-400";
  if (score <= 70) return "text-amber-400";
  return "text-red-400";
}

export function decisionColor(decision: string): string {
  switch (decision) {
    case "ALLOW": return "text-emerald-400";
    case "REVIEW": return "text-amber-400";
    case "BLOCK": return "text-red-400";
    default: return "text-slate-400";
  }
}

export function decisionBg(decision: string): string {
  switch (decision) {
    case "ALLOW": return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
    case "REVIEW": return "bg-amber-500/10 text-amber-400 border border-amber-500/30";
    case "BLOCK": return "bg-red-500/10 text-red-400 border border-red-500/30";
    default: return "bg-slate-500/10 text-slate-400";
  }
}

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  return `${Math.round(diff / 3600)}h ago`;
}
