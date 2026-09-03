"use client";
import { cn, decisionBg } from "@/lib/utils";

interface Props {
  decision: string;
  size?: "sm" | "md";
}

const LABELS: Record<string, string> = {
  ALLOW: "Allow",
  REVIEW: "Review",
  BLOCK: "Block",
};

export default function DecisionBadge({ decision, size = "md" }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-semibold tracking-wide uppercase",
        decisionBg(decision),
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-xs"
      )}
    >
      {LABELS[decision] ?? decision}
    </span>
  );
}
