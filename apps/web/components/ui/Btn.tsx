"use client";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef } from "react";
import { cn } from "@/lib/cn";

// Port of design_handoff_peatguard/components.jsx:71-104 (Btn).
const btnVariants = cva(
  "inline-flex items-center justify-center font-semibold leading-none whitespace-nowrap transition-[transform,filter,background] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed hover:brightness-95",
  {
    variants: {
      kind: {
        primary: "bg-pg-primary text-pg-primary-fg border border-pg-primary",
        secondary: "bg-pg-surface-raised text-pg-ink border border-pg-border-strong",
        ghost: "bg-transparent text-pg-ink border border-transparent hover:bg-pg-surface-sunken",
        soft: "bg-pg-primary-soft text-pg-primary border border-transparent",
        danger: "bg-pg-risk text-white border border-pg-risk",
        success: "bg-pg-accent text-white border border-pg-accent",
        gold: "bg-pg-gold text-[#1a1300] border border-pg-gold",
      },
      size: {
        sm: "h-[30px] px-2.5 text-[12.5px] gap-1.5 rounded-md",
        md: "h-[38px] px-3.5 text-[13.5px] gap-2 rounded-md",
        lg: "h-12 px-[18px] text-[15px] gap-2.5 rounded-md",
      },
      full: { true: "w-full" },
    },
    defaultVariants: { kind: "primary", size: "md" },
  },
);

export interface BtnProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof btnVariants> {
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
}

export const Btn = forwardRef<HTMLButtonElement, BtnProps>(
  ({ className, kind, size, full, icon, iconRight, children, ...rest }, ref) => (
    <button
      ref={ref}
      className={cn(btnVariants({ kind, size, full }), className)}
      {...rest}
    >
      {icon}
      {children}
      {iconRight}
    </button>
  ),
);
Btn.displayName = "Btn";
