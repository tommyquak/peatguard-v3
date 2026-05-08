import { cn } from "@/lib/cn";

// Port of design_handoff_peatguard/components.jsx:109-120 (Card).
export function Card({
  children,
  className,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "bg-pg-surface-raised border border-pg-border rounded-md",
        onClick && "cursor-pointer",
        className,
      )}
    >
      {children}
    </div>
  );
}
