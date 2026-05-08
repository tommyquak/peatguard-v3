"use client";
// Port of design_handoff_peatguard/web-screens-1.jsx:7-67 (WebShell + sidebar).

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bell,
  CheckCircle2,
  ChevronDown,
  Layers,
  Map,
  Settings,
  ShieldCheck,
  Users,
  Wallet,
  Home,
} from "lucide-react";
import { Logomark } from "@/components/ui/Logomark";
import { useAuth } from "@/lib/authStore";
import { usePayments, useTasks } from "@/lib/api";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "AOI Dashboard", icon: Home, key: "home" },
  { href: "/map", label: "Map view", icon: Map, key: "map" },
  { href: "/tasks", label: "Tasks", icon: Layers, key: "tasks" },
  { href: "/validation", label: "Validation", icon: CheckCircle2, key: "validate" },
  { href: "/payments", label: "Payments", icon: Wallet, key: "pay" },
  { href: "/workers", label: "Workers", icon: Users, key: "workers" },
  { href: "/reports", label: "Reports", icon: BarChart3, key: "reports" },
  { href: "/settings", label: "Settings", icon: Settings, key: "settings" },
];

interface ShellProps {
  title?: string;
  subtitle?: string;
  headerRight?: React.ReactNode;
  dense?: boolean;
  children: React.ReactNode;
}

export function WebShell({ title, subtitle, headerRight, dense, children }: ShellProps) {
  const pathname = usePathname();
  const user = useAuth((s) => s.user);
  const { data: validation = [] } = useTasks({ status: "submitted" });
  const { data: pending = [] } = usePayments("pending");

  return (
    <div className="grid grid-cols-[232px_1fr] h-screen bg-pg-surface overflow-hidden">
      <aside className="bg-pg-surface-raised border-r border-pg-border flex flex-col">
        <div className="p-5 pb-3 flex items-center gap-2.5">
          <Logomark />
          <div className="flex flex-col">
            <span className="text-[14.5px] font-bold tracking-tight text-pg-ink">PeatGuard</span>
            <span className="text-[11px] text-pg-ink-muted font-mono">v4.2.1</span>
          </div>
        </div>
        <WorkspacePicker />
        <nav className="px-2.5 py-2 flex flex-col gap-px">
          {NAV.map((n) => {
            const active =
              n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
            const Icon = n.icon;
            const badge =
              n.key === "validate" && validation.length > 0
                ? { value: validation.length, color: "bg-pg-risk text-white" }
                : n.key === "pay" && pending.length > 0
                  ? { value: pending.length, color: "bg-pg-gold-soft text-[#7a5400]" }
                  : null;
            return (
              <Link
                key={n.key}
                href={n.href}
                className={cn(
                  "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm",
                  active
                    ? "font-semibold text-pg-primary bg-pg-primary-soft"
                    : "font-medium text-pg-ink-secondary hover:bg-pg-surface-sunken",
                )}
              >
                <Icon size={17} />
                <span>{n.label}</span>
                {badge && (
                  <span
                    className={cn(
                      "ml-auto text-[11px] font-semibold rounded-full px-1.5 py-px",
                      badge.color,
                    )}
                  >
                    {badge.value}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto p-3.5 border-t border-pg-border flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full grid place-items-center text-white text-xs font-bold"
            style={{ background: "linear-gradient(135deg,#3d2818,#57a773)" }}>
            {(user?.name || "NA").slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[12.5px] font-semibold text-pg-ink truncate">{user?.name || "Operator"}</div>
            <div className="text-[11px] text-pg-ink-muted">PeatGuard · Analyst</div>
          </div>
          <ChevronDown size={14} className="text-pg-ink-muted" />
        </div>
      </aside>
      <main className="flex flex-col overflow-hidden">
        {(title || headerRight) && (
          <header
            className={cn(
              "border-b border-pg-border flex items-center gap-4 bg-pg-surface-raised",
              dense ? "px-7 py-3.5" : "px-7 pt-5 pb-4.5",
            )}
          >
            <div className="flex-1 min-w-0">
              {subtitle && <div className="text-xs text-pg-ink-muted font-medium mb-0.5">{subtitle}</div>}
              {title && (
                <h1 className="text-xl font-semibold tracking-tight text-pg-ink">{title}</h1>
              )}
            </div>
            {headerRight}
          </header>
        )}
        <div className="flex-1 overflow-hidden relative">{children}</div>
      </main>
    </div>
  );
}

function WorkspacePicker() {
  return (
    <div className="mx-3 mt-1 mb-2 px-3 py-2.5 border border-pg-border rounded-md flex items-center gap-2.5 cursor-pointer bg-pg-surface-sunken">
      <div className="w-6 h-6 rounded-[5px] grid place-items-center text-white text-[11px] font-bold bg-pg-primary">
        PG
      </div>
      <div className="flex-1 min-w-0 leading-tight">
        <div className="text-[12.5px] font-semibold text-pg-ink truncate">PeatGuard · Kalimantan ops</div>
        <div className="text-[11px] text-pg-ink-muted">Switch programme</div>
      </div>
      <ChevronDown size={14} className="text-pg-ink-muted" />
    </div>
  );
}

export function HeaderBell() {
  return (
    <button className="relative w-9 h-9 rounded-md bg-pg-surface-sunken grid place-items-center">
      <Bell size={17} />
      <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-pg-risk border-2 border-white" />
    </button>
  );
}

export { ShieldCheck };
