import { cn } from "@/lib/cn";

// Port of design_handoff_peatguard/components.jsx:150-163 (Stat).
export function Stat({
  label,
  value,
  sub,
  delta,
  deltaTone = "success",
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  delta?: string;
  deltaTone?: "success" | "risk" | "neutral";
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="text-[11.5px] uppercase tracking-wider text-pg-ink-secondary font-medium">{label}</div>
      <div className="text-2xl font-semibold tracking-tight text-pg-ink leading-none">{value}</div>
      {(sub || delta) && (
        <div className="text-xs text-pg-ink-secondary flex items-center gap-1.5">
          {delta && (
            <span
              className={cn(
                "font-semibold",
                deltaTone === "success" && "text-pg-accent",
                deltaTone === "risk" && "text-pg-risk",
                deltaTone === "neutral" && "text-pg-ink-secondary",
              )}
            >
              {delta}
            </span>
          )}
          {sub}
        </div>
      )}
    </div>
  );
}

export function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-[3px]">
      <span className="text-[11px] text-pg-ink-muted font-medium uppercase tracking-wider">{label}</span>
      <span className={cn("text-sm text-pg-ink font-medium", mono && "font-mono")}>{value}</span>
    </div>
  );
}
