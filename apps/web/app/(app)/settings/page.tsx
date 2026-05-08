"use client";
// W9 · Programme settings.
// Source: design_handoff_peatguard/web-screens-2.jsx:529-621.

import {
  Bell,
  CheckCircle2,
  Layers,
  RefreshCcw,
  Settings as SettingsIcon,
  Users,
  Wallet,
  Check,
  X,
} from "lucide-react";
import { WebShell } from "@/components/WebShell";
import { Btn } from "@/components/ui/Btn";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Stat";
import { useState } from "react";

const NAV = [
  { id: "gen", label: "General", icon: SettingsIcon },
  { id: "pay", label: "Payouts & rails", icon: Wallet },
  { id: "val", label: "Validation rules", icon: CheckCircle2 },
  { id: "aoi", label: "AOIs & layers", icon: Layers },
  { id: "sat", label: "Satellite refresh", icon: RefreshCcw },
  { id: "al", label: "Alerts", icon: Bell },
  { id: "tm", label: "Team & roles", icon: Users },
];

export default function SettingsPage() {
  const [active] = useState("gen");
  return (
    <WebShell title="Programme settings" subtitle="PeatGuard · Kalimantan ops">
      <div className="grid grid-cols-[232px_1fr] h-full">
        <aside className="border-r border-pg-border p-3.5 flex flex-col gap-0.5 bg-pg-surface-raised">
          {NAV.map((n) => {
            const Icon = n.icon;
            const on = n.id === active;
            return (
              <a
                key={n.id}
                className={`flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm cursor-pointer ${on ? "text-pg-primary bg-pg-primary-soft font-semibold" : "text-pg-ink-secondary font-medium hover:bg-pg-surface-sunken"}`}
              >
                <Icon size={15} />
                {n.label}
              </a>
            );
          })}
        </aside>
        <div className="overflow-auto p-7 flex flex-col gap-4.5">
          <SetSection title="Default payouts by task type" sub="Used as starting amount when an operator creates a task. Editable per task.">
            <div className="grid grid-cols-4 gap-3">
              {[
                ["Canal block", "250,000", "per dam"],
                ["Revegetation", "180,000", "per 1-ha plot"],
                ["Monitor patrol", "120,000", "per 5 km route"],
                ["Fire watch", "150,000", "per 6 h shift"],
              ].map(([n, a, u]) => (
                <Card key={n} className="p-3.5">
                  <div className="text-xs text-pg-ink-muted">{n}</div>
                  <div className="text-lg font-semibold font-mono mt-1">Rp {a}</div>
                  <div className="text-[11px] text-pg-ink-muted">{u}</div>
                </Card>
              ))}
            </div>
          </SetSection>

          <SetSection title="Validation rules" sub="Auto-checks applied to every submission before operator review.">
            <div className="flex flex-col gap-2.5">
              {[
                ["GPS within polygon", "accept ≤ 18 m offset", true],
                ["Photo blur score", "advisory; never blocks submission (handoff #2)", true],
                ["Working window", "06:00–17:00 WIB", true],
                ["Linear length minimum", "≥ 8 m for canal blocks", true],
                ["Sealed-hash chain", "reject if broken", true],
                ["Operator manual review", "always required for > Rp 500,000", false],
              ].map(([k, v, on]) => (
                <div key={k as string} className="flex items-center gap-3 px-3.5 py-2.5 border border-pg-border rounded-md">
                  {on ? <Check size={16} className="text-pg-accent" /> : <X size={16} className="text-pg-ink-muted" />}
                  <div className="flex-1">
                    <div className="text-sm font-semibold">{k}</div>
                    <div className="text-[11.5px] text-pg-ink-muted font-mono">{v}</div>
                  </div>
                  <button className={`w-8 h-4.5 rounded-full relative ${on ? "bg-pg-primary" : "bg-pg-border-strong"}`} style={{ width: 32, height: 18 }}>
                    <span className="absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white" style={{ left: on ? 16 : 2 }} />
                  </button>
                </div>
              ))}
            </div>
          </SetSection>

          <SetSection title="Satellite & pipeline" sub="Inputs to the science workflow. Changes take effect next refresh.">
            <div className="grid grid-cols-2 gap-3.5">
              <Card className="p-3.5">
                <Field label="Refresh cadence" value="Every 12 days · S1 IW VV+VH" />
                <div className="h-px bg-pg-border my-2.5" />
                <Field label="Hansen-cohort gradient threshold" value="0.18 (loose)" mono />
                <div className="mt-2 flex gap-1.5">
                  <Btn kind="ghost" size="sm">Strict</Btn>
                  <Btn kind="soft" size="sm">Loose</Btn>
                  <Btn kind="ghost" size="sm">Custom…</Btn>
                </div>
              </Card>
              <Card className="p-3.5">
                <Field label="Velocity-backed confidence threshold" value="|v| ≥ 8 mm/yr" mono />
                <div className="h-px bg-pg-border my-2.5" />
                <Field label="Output projection" value="UTM 49S · EPSG:32749" mono />
                <div className="h-px bg-pg-border my-2.5" />
                <Field label="Tile server (TiTiler)" value="tiles.peatguard.id" mono />
              </Card>
            </div>
          </SetSection>

          <SetSection title="Partner agencies" sub="Outside organisations consuming PeatGuard outputs and co-funding tasks.">
            <div className="flex gap-2.5 flex-wrap">
              {[
                ["BRGM", "Central Kalimantan", "Co-funder"],
                ["WWF-ID", "Sumatra", "Donor"],
                ["KLHK", "National", "Reviewer"],
                ["IDH", "Riau", "Donor"],
              ].map(([n, r, role]) => (
                <Card key={n} className="p-3 min-w-[200px]">
                  <div className="text-sm font-semibold">{n}</div>
                  <div className="text-[11.5px] text-pg-ink-muted">{r} · {role}</div>
                </Card>
              ))}
            </div>
          </SetSection>
        </div>
      </div>
    </WebShell>
  );
}

function SetSection({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="mb-3">
        <h3 className="text-base font-semibold">{title}</h3>
        {sub && <p className="text-[12.5px] text-pg-ink-secondary mt-0.5">{sub}</p>}
      </div>
      {children}
    </section>
  );
}
