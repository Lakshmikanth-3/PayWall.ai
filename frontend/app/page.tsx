"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { AnimatePresence } from "framer-motion";
import {
  ShieldCheck, ArrowRight, Code2, ScanSearch, BrainCircuit, Gavel,
  Sparkles, TrendingUp, Ban, GitBranch, CheckCircle2, XCircle, ArrowDown,
} from "lucide-react";
import { motion, Reveal, StaggerGroup, fadeUp, stagger } from "@/components/motion";
import DecisionBadge from "@/components/DecisionBadge";
import RiskMeter from "@/components/RiskMeter";

const GITHUB_URL = "https://github.com/Lakshmikanth-3/PayWall.ai";

const LIVE_EXAMPLES = [
  {
    product: "Nike Running Shoes", amount: "4,799", decision: "ALLOW", risk: 4,
    reason: "Matches user intent, within budget, low-risk merchant.",
  },
  {
    product: "Premium Protection Plan", amount: "14,999", decision: "BLOCK", risk: 96,
    reason: "Unrelated to user intent, exceeds authorized limit.",
  },
  {
    product: "Moisture-wicking Running Socks", amount: "149", decision: "ALLOW", risk: 3,
    reason: "Relevant upsell, fits remaining budget, same Guard pipeline.",
  },
  {
    product: "Monthly Grocery Pack", amount: "3,500", decision: "REVIEW", risk: 52,
    reason: "Medium-risk merchant — routed to human approval.",
  },
];

function LiveDecisionCard() {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setIndex((i) => (i + 1) % LIVE_EXAMPLES.length), 3200);
    return () => clearInterval(t);
  }, []);
  const ex = LIVE_EXAMPLES[index];

  return (
    <div className="glass w-full max-w-md rounded-2xl p-6 relative overflow-hidden">
      <div className="flex items-center justify-between mb-5">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Guard Decision</p>
        <div className="flex items-center gap-1.5 text-xs text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Live simulation
        </div>
      </div>
      <AnimatePresence mode="wait">
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xs text-slate-500 mb-1">Payment request</p>
              <p className="text-sm font-semibold text-white">{ex.product}</p>
              <p className="text-lg font-bold text-white mt-1">₹{ex.amount}</p>
            </div>
            <RiskMeter score={ex.risk} size="md" showLabel={false} />
          </div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-slate-500">Decision</span>
            <DecisionBadge decision={ex.decision} />
          </div>
          <div className="bg-white/4 rounded-xl p-3">
            <p className="text-xs text-slate-400 leading-relaxed">{ex.reason}</p>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

const LAYERS = [
  {
    icon: Gavel,
    title: "Hard Policy Rules",
    desc: "Deterministic checks — agent status, merchant blocklist, transaction and daily limits, category authorization. Any violation blocks outright, no ML or LLM required.",
  },
  {
    icon: ScanSearch,
    title: "ML Risk Model",
    desc: "An XGBoost classifier scores every transaction 0–100 on amount deviation, merchant risk, velocity, and budget headroom.",
  },
  {
    icon: BrainCircuit,
    title: "LLM Intent Match",
    desc: "Compares what's being paid for against what the user actually asked for. Falls back to a deterministic scorer and fails closed to REVIEW if the LLM is unavailable — never guesses.",
  },
];

const FLOW_STEPS = [
  { label: "User states intent", detail: "“Buy running shoes under ₹5,000”" },
  { label: "Agent proposes a payment", detail: "POST /transactions/evaluate" },
  { label: "Guard decides", detail: "Policy → Risk → Intent, combined" },
  { label: "Razorpay executes", detail: "Only after ALLOW, or REVIEW + human approval" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#080c14] text-white overflow-x-hidden">
      {/* Nav */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[#080c14]/70 border-b border-white/5">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold tracking-tight">Agent Commerce Guard</span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors px-3 py-2"
            >
              <Code2 className="w-3.5 h-3.5" /> Source
            </a>
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 text-xs font-semibold bg-white text-[#080c14] px-4 py-2 rounded-xl hover:bg-slate-200 transition-colors"
            >
              Launch Dashboard <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative max-w-6xl mx-auto px-6 pt-20 pb-28">
        <div
          className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[900px] rounded-full opacity-20 blur-3xl"
          style={{ background: "radial-gradient(circle, #7c3aed 0%, transparent 70%)" }}
        />
        <div className="grid lg:grid-cols-2 gap-16 items-center relative">
          <motion.div initial="hidden" animate="show" variants={stagger(0.12)}>
            <motion.div variants={fadeUp} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/25 text-violet-300 text-xs font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              Razorpay AI Buildathon — Track 01: AI Growth &amp; Agentic Commerce
            </motion.div>
            <motion.h1 variants={fadeUp} className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.1] mb-6">
              The trust layer that lets{" "}
              <span className="gradient-text">AI agents</span>{" "}
              spend money safely.
            </motion.h1>
            <motion.p variants={fadeUp} className="text-slate-400 text-lg leading-relaxed mb-8 max-w-lg">
              An agent that can complete a purchase can also be manipulated into
              paying for something the user never asked for. Agent Commerce
              Guard authorizes every agent-initiated payment against the
              user&apos;s intent, policy, and risk — before it ever reaches Razorpay.
            </motion.p>
            <motion.div variants={fadeUp} className="flex flex-wrap items-center gap-4">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white font-semibold text-sm px-5 py-3 rounded-xl shadow-lg shadow-violet-500/25 transition-all"
              >
                Launch Dashboard <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#how-it-works"
                className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white px-5 py-3 transition-colors"
              >
                See how it decides <ArrowDown className="w-3.5 h-3.5" />
              </a>
            </motion.div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="flex justify-center lg:justify-end"
          >
            <LiveDecisionCard />
          </motion.div>
        </div>
      </section>

      {/* Problem statement */}
      <section className="max-w-6xl mx-auto px-6 py-20 border-t border-white/5">
        <Reveal className="max-w-2xl">
          <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-3">The problem</p>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-6">
            Traditional fraud detection asks the wrong question.
          </h2>
        </Reveal>
        <div className="grid md:grid-cols-2 gap-6 mt-10">
          <Reveal delay={0.05} className="glass p-6 rounded-2xl border-white/5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Traditional fraud detection</p>
            <p className="text-lg text-slate-300 leading-relaxed">&ldquo;Is this transaction fraudulent?&rdquo;</p>
          </Reveal>
          <Reveal delay={0.15} className="glass p-6 rounded-2xl border-violet-500/25 glow-blue">
            <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-3">Agent Commerce Guard</p>
            <p className="text-lg text-white leading-relaxed">
              &ldquo;Is this transaction authorized, consistent with the user&apos;s
              intent, within policy, and safe to execute?&rdquo;
            </p>
          </Reveal>
        </div>
      </section>

      {/* Three layers */}
      <section id="how-it-works" className="max-w-6xl mx-auto px-6 py-20 border-t border-white/5">
        <Reveal className="max-w-2xl mb-12">
          <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-3">How it decides</p>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Three layers, one bounded decision.
          </h2>
        </Reveal>
        <StaggerGroup className="grid md:grid-cols-3 gap-6">
          {LAYERS.map((layer, i) => (
            <motion.div key={layer.title} variants={fadeUp} className="glass p-6 rounded-2xl relative">
              <div className="w-10 h-10 rounded-xl bg-violet-500/15 border border-violet-500/25 flex items-center justify-center mb-4">
                <layer.icon className="w-5 h-5 text-violet-400" />
              </div>
              <p className="text-xs font-mono text-slate-600 mb-1">Layer {i + 1}</p>
              <h3 className="text-base font-semibold text-white mb-2">{layer.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{layer.desc}</p>
            </motion.div>
          ))}
        </StaggerGroup>

        <Reveal delay={0.1} className="mt-8 flex items-center justify-center gap-3">
          {(["ALLOW", "REVIEW", "BLOCK"] as const).map((d) => (
            <DecisionBadge key={d} decision={d} />
          ))}
        </Reveal>
      </section>

      {/* Revenue growth */}
      <section className="max-w-6xl mx-auto px-6 py-20 border-t border-white/5">
        <Reveal className="max-w-2xl mb-12">
          <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">Revenue growth, not just safety</p>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            One pipeline. Two outcomes.
          </h2>
          <p className="text-slate-400 mt-4 leading-relaxed">
            The Upsell Agent proposes one relevant, budget-aware add-on after
            a purchase — and it has no special authority. Its proposal is
            evaluated by the exact same Guard as any other payment.
          </p>
        </Reveal>
        <div className="grid md:grid-cols-2 gap-6">
          <Reveal delay={0.05} className="glass p-6 rounded-2xl border-emerald-500/20">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <p className="text-sm font-semibold text-emerald-300">Legitimate upsell</p>
            </div>
            <p className="text-sm text-slate-300 mb-1">Running socks, ₹149 — offered after a shoe purchase</p>
            <p className="text-xs text-slate-500 mb-4">Same category, within remaining budget, relevant to intent</p>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-emerald-300 font-medium">ALLOW → counts as incremental GMV</span>
            </div>
          </Reveal>
          <Reveal delay={0.15} className="glass p-6 rounded-2xl border-red-500/20">
            <div className="flex items-center gap-2 mb-4">
              <XCircle className="w-5 h-5 text-red-400" />
              <p className="text-sm font-semibold text-red-300">Manipulated &ldquo;upsell&rdquo;</p>
            </div>
            <p className="text-sm text-slate-300 mb-1">Protection plan, ₹14,999 — disguised as a checkout add-on</p>
            <p className="text-xs text-slate-500 mb-4">Unrelated category, exceeds authorization, low intent match</p>
            <div className="flex items-center gap-2">
              <Ban className="w-4 h-4 text-red-400" />
              <span className="text-xs text-red-300 font-medium">BLOCK → exposure prevented</span>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Flow diagram */}
      <section className="max-w-6xl mx-auto px-6 py-20 border-t border-white/5">
        <Reveal className="max-w-2xl mb-12">
          <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider mb-3">Architecture</p>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            The agent proposes. The Guard authorizes.
          </h2>
        </Reveal>
        <StaggerGroup delay={0.12} className="flex flex-col md:flex-row items-stretch gap-4">
          {FLOW_STEPS.map((step, i) => (
            <motion.div key={step.label} variants={fadeUp} className="flex-1 flex items-center gap-4">
              <div className="glass p-5 rounded-2xl flex-1 h-full">
                <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-xs font-bold text-violet-400 mb-3">
                  {i + 1}
                </div>
                <p className="text-sm font-semibold text-white mb-1">{step.label}</p>
                <p className="text-xs text-slate-500">{step.detail}</p>
              </div>
              {i < FLOW_STEPS.length - 1 && (
                <ArrowRight className="w-5 h-5 text-slate-700 shrink-0 hidden md:block" />
              )}
            </motion.div>
          ))}
        </StaggerGroup>
      </section>

      {/* CTA footer */}
      <section className="max-w-6xl mx-auto px-6 py-24 border-t border-white/5 text-center">
        <Reveal>
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center mx-auto mb-6">
            <GitBranch className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-4">
            Let AI agents transact.<br />Don&apos;t let them transact beyond what the user authorized.
          </h2>
          <div className="flex items-center justify-center gap-4 mt-8">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 bg-white text-[#080c14] font-semibold text-sm px-6 py-3 rounded-xl hover:bg-slate-200 transition-colors"
            >
              Launch Dashboard <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-white px-6 py-3 border border-white/10 rounded-xl transition-colors"
            >
              <Code2 className="w-4 h-4" /> View Source
            </a>
          </div>
        </Reveal>
      </section>

      <footer className="border-t border-white/5 py-8">
        <p className="text-center text-xs text-slate-600">
          Agent Commerce Guard — Razorpay AI Buildathon 2026
        </p>
      </footer>
    </div>
  );
}
