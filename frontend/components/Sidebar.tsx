"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldCheck,
  LayoutDashboard,
  Zap,
  Search,
  Bot,
  Store,
  BarChart3,
  FlaskConical,
  ChevronRight,
  Sliders,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/live", label: "Live Feed", icon: Zap },
  { href: "/evaluate", label: "Evaluate", icon: FlaskConical },
  { href: "/audit", label: "Audit Trail", icon: Search },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/merchants", label: "Merchants", icon: Store },
  { href: "/metrics", label: "Metrics", icon: BarChart3 },
  { href: "/simulate", label: "Policy Simulator", icon: Sliders },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen bg-[#0c1220] border-r border-white/5 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-tight">Agent Commerce</p>
            <p className="text-xs text-violet-400 font-medium">Guard</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest px-3 mb-3">Navigation</p>
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group",
                active
                  ? "bg-violet-500/15 text-violet-300 border border-violet-500/25"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              )}
            >
              <Icon className={cn("w-4 h-4 shrink-0", active ? "text-violet-400" : "text-slate-500 group-hover:text-slate-300")} />
              <span>{label}</span>
              {active && <ChevronRight className="w-3.5 h-3.5 ml-auto text-violet-400/60" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/5">
        <div className="glass p-3 rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium">System Operational</span>
          </div>
          <p className="text-xs text-slate-500">Razorpay Buildathon 2026</p>
        </div>
      </div>
    </aside>
  );
}
