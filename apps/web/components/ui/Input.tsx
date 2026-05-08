import { cn } from "@/lib/cn";
import { forwardRef } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  icon?: React.ReactNode;
  trailing?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, icon, trailing, className, ...rest }, ref) => (
    <label className="flex flex-col gap-1.5">
      {label && <span className="text-xs text-pg-ink-secondary font-medium">{label}</span>}
      <div className="h-11 px-3.5 border border-pg-border-strong rounded-md flex items-center gap-2.5 bg-pg-surface-raised focus-within:border-pg-primary transition-colors">
        {icon && <span className="text-pg-ink-muted shrink-0">{icon}</span>}
        <input
          ref={ref}
          className={cn("flex-1 text-base text-pg-ink bg-transparent outline-none placeholder:text-pg-ink-muted", className)}
          {...rest}
        />
        {trailing}
      </div>
    </label>
  ),
);
Input.displayName = "Input";
