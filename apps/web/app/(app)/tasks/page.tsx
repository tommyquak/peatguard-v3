"use client";
// Auxiliary list view for tasks (sidebar link). Quick table of every task in the ledger.

import Link from "next/link";
import { WebShell } from "@/components/WebShell";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { useTasks } from "@/lib/api";
import { formatIDR } from "@/lib/cn";
import type { TaskStatus } from "@/lib/types";

const STATUS_TONES: Record<TaskStatus, "gold" | "info" | "success" | "neutral" | "risk"> = {
  available: "gold",
  accepted: "info",
  submitted: "success",
  approved: "success",
  rejected: "risk",
  paid: "neutral",
};

export default function TasksPage() {
  const { data: tasks = [] } = useTasks();
  return (
    <WebShell title="All tasks" subtitle={`${tasks.length} tasks in ledger`}>
      <div className="p-7">
        <Card className="p-0 overflow-hidden">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-pg-surface-sunken text-left">
                {["Task", "AOI", "Status", "Worker", "Payout", "Deadline"].map((h) => (
                  <th key={h} className="px-4 py-3 text-[11px] text-pg-ink-muted uppercase tracking-wider font-semibold border-b border-pg-border">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className="border-b border-pg-border">
                  <td className="px-4 py-3">
                    <Link href={`/map?aoi=${t.aoi_code}`} className="font-semibold text-pg-primary">
                      {t.title}
                    </Link>
                    <div className="text-[11px] text-pg-ink-muted font-mono">{t.id}</div>
                  </td>
                  <td className="px-4 py-3 text-pg-ink-secondary">{t.aoi_code}</td>
                  <td className="px-4 py-3"><Chip size="sm" tone={STATUS_TONES[t.status]}>{t.status}</Chip></td>
                  <td className="px-4 py-3 text-pg-ink-secondary">{t.worker_id ?? "—"}</td>
                  <td className="px-4 py-3 font-mono">{formatIDR(t.payout_idr)}</td>
                  <td className="px-4 py-3 font-mono text-pg-ink-muted">{t.deadline}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </WebShell>
  );
}
