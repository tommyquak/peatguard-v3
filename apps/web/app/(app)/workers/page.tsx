"use client";
// W7 · Worker management.
// Source: design_handoff_peatguard/web-screens-2.jsx:325-406.

import { ChevronRight, Download, MessageCircle, Plus, Search, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { WebShell } from "@/components/WebShell";
import { Btn } from "@/components/ui/Btn";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { useWorkers } from "@/lib/api";
import { formatIDR } from "@/lib/cn";

export default function WorkersPage() {
  const { data: workers = [] } = useWorkers();
  return (
    <WebShell
      title="Workers"
      subtitle={`${workers.length} registered · ${workers.length} active in last 30 d`}
      headerRight={
        <div className="flex gap-2">
          <Btn kind="ghost" icon={<MessageCircle size={15} />}>Broadcast message</Btn>
          <Btn kind="secondary" icon={<Download size={15} />}>Export CSV</Btn>
          <Btn kind="primary" icon={<Plus size={15} />}>Invite workers</Btn>
        </div>
      }
    >
      <div className="p-7 flex flex-col gap-4 h-full overflow-hidden">
        <div className="flex gap-2.5">
          <div className="h-9 px-3.5 border border-pg-border-strong rounded-md flex items-center gap-2 flex-1 bg-pg-surface-raised">
            <Search size={16} className="text-pg-ink-muted" />
            <span className="text-sm text-pg-ink-muted">Search by name, village, NIK…</span>
          </div>
          <Btn kind="secondary" icon={<SlidersHorizontal size={14} />}>All villages</Btn>
          <Btn kind="secondary">Verified only</Btn>
          <Btn kind="secondary">Sort: completion rate ↓</Btn>
        </div>
        <Card className="p-0 flex-1 overflow-hidden flex flex-col">
          <div className="overflow-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-pg-surface-sunken text-left">
                  {["Worker", "Village", "Tasks", "Completion %", "Total paid", "Rating", "Status", ""].map((h) => (
                    <th key={h} className="px-4.5 py-3 text-[11px] text-pg-ink-muted uppercase tracking-wider font-semibold border-b border-pg-border">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {workers.map((w) => (
                  <tr key={w.id} className="border-b border-pg-border">
                    <td className="px-4.5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="w-9 h-9 rounded-full bg-pg-primary-soft text-pg-primary grid place-items-center text-xs font-bold">
                          {w.name.split(" ").slice(0, 2).map((p) => p[0]).join("")}
                        </div>
                        <div>
                          <div className="font-semibold flex items-center gap-1.5">
                            {w.name}
                            {w.nik_verified && <ShieldCheck size={13} className="text-pg-accent" />}
                            {w.role === "team_lead" && <Chip tone="gold" size="sm">Team lead</Chip>}
                          </div>
                          <div className="text-[11px] text-pg-ink-muted font-mono">NIK ••••••8421</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4.5 py-3.5 text-pg-ink-secondary">{w.village ?? "—"}</td>
                    <td className="px-4.5 py-3.5 font-mono">{w.tasks_done}</td>
                    <td className="px-4.5 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1 bg-pg-surface-sunken rounded-sm overflow-hidden">
                          <div
                            className={`h-full ${
                              w.completion_rate > 90
                                ? "bg-pg-accent"
                                : w.completion_rate > 80
                                  ? "bg-pg-warn"
                                  : "bg-pg-risk"
                            }`}
                            style={{ width: `${w.completion_rate}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs">{w.completion_rate}%</span>
                      </div>
                    </td>
                    <td className="px-4.5 py-3.5 font-mono font-semibold">{formatIDR(w.total_paid)}</td>
                    <td className="px-4.5 py-3.5">
                      <span className="inline-flex items-center gap-1 font-semibold">★ {w.rating.toFixed(1)}</span>
                    </td>
                    <td className="px-4.5 py-3.5">
                      {w.flag ? (
                        <Chip tone="warn" size="sm">flag: {w.flag}</Chip>
                      ) : w.nik_verified ? (
                        <Chip tone="success" size="sm">Verified</Chip>
                      ) : (
                        <Chip tone="neutral" size="sm">Unverified</Chip>
                      )}
                    </td>
                    <td className="px-4.5 py-3.5">
                      <ChevronRight size={16} className="text-pg-ink-muted" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </WebShell>
  );
}
