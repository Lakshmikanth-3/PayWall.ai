"use client";

interface Props {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export default function RiskMeter({ score, size = "md", showLabel = true }: Props) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct <= 30 ? "#10b981" : pct <= 70 ? "#f59e0b" : "#ef4444";
  const label = pct <= 30 ? "LOW" : pct <= 70 ? "MEDIUM" : "HIGH";

  const r = size === "lg" ? 36 : size === "sm" ? 20 : 28;
  const sw = size === "lg" ? 5 : size === "sm" ? 3 : 4;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (pct / 100) * circumference;
  const sz = (r + sw) * 2;

  return (
    <div className="flex items-center gap-3">
      <div style={{ position: "relative", width: sz, height: sz }}>
        <svg width={sz} height={sz} style={{ transform: "rotate(-90deg)" }}>
          <circle
            cx={r + sw}
            cy={r + sw}
            r={r}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={sw}
          />
          <circle
            cx={r + sw}
            cy={r + sw}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={sw}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.4s ease" }}
          />
        </svg>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            style={{ color, fontSize: size === "lg" ? 14 : 10, fontWeight: 700 }}
          >
            {Math.round(pct)}
          </span>
        </div>
      </div>
      {showLabel && (
        <div>
          <p className="text-xs font-semibold" style={{ color }}>
            {label}
          </p>
          <p className="text-xs text-slate-500">Risk</p>
        </div>
      )}
    </div>
  );
}
