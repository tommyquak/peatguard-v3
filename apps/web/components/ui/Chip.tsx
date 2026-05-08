import { cn } from "@/lib/cn";

// Port of design_handoff_peatguard/components.jsx:122-148 (Chip).
type Tone = "neutral" | "primary" | "success" | "risk" | "warn" | "gold" | "info";

const tones: Record<Tone, { bg: string; text: string; dot: string }> = {
  neutral: { bg: "bg-pg-surface-sunken", text: "text-pg-ink-secondary", dot: "bg-pg-ink-muted" },
  primary: { bg: "bg-pg-primary-soft", text: "text-pg-primary", dot: "bg-pg-primary" },
  success: { bg: "bg-pg-accent-soft", text: "text-[#2d6e44]", dot: "bg-pg-accent" },
  risk: { bg: "bg-pg-risk-soft", text: "text-pg-risk", dot: "bg-pg-risk" },
  warn: { bg: "bg-[#fdf1d8]", text: "text-[#7a4d00]", dot: "bg-pg-warn" },
  gold: { bg: "bg-pg-gold-soft", text: "text-[#7a5400]", dot: "bg-pg-gold" },
  info: { bg: "bg-[#dde9f1]", text: "text-[#1f5278]", dot: "bg-pg-info" },
};

export function Chip({
  children,
  tone = "neutral",
  size = "md",
  className,
}: {
  children: React.ReactNode;
  tone?: Tone;
  size?: "sm" | "md";
  className?: string;
}) {
  const t = tones[tone];
  const sizing = size === "sm"
    ? "h-5 px-1.5 text-[11px] gap-1"
    : "h-6 px-2.5 text-xs gap-1.5";
  return (
    <span
      className={cn(
        "inline-flex items-center font-semibold leading-none rounded-full whitespace-nowrap",
        sizing,
        t.bg,
        t.text,
        className,
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full", t.dot)} />
      {children}
    </span>
  );
}
