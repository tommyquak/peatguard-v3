"use client";
// W6 · Payments dashboard.
// Source: design_handoff_peatguard/web-screens-2.jsx:229-323.

import { useMemo, useState } from "react";
import { Check, Download, HandCoins, Search, SlidersHorizontal, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { WebShell } from "@/components/WebShell";
import { Btn } from "@/components/ui/Btn";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Stat } from "@/components/ui/Stat";
import { useBatchRelease, usePayments, usePaymentSummary } from "@/lib/api";
import { formatIDR, formatIDRShort } from "@/lib/cn";

export default function PaymentsPage() {
  const { data: pending = [] } = usePayments("pending");
  const { data: summary } = usePaymentSummary();
  const release = useBatchRelease();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const allSelected = pending.length > 0 && selected.size === pending.length;
  const totalSelected = pending.filter((p) => selected.has(p.id)).reduce((s, p) => s + p.amount, 0);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function toggleAll() {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(pending.map((p) => p.id)));
  }

  async function releaseBatch(ids: string[]) {
    if (!ids.length) {
      toast.error("No payments selected");
      return;
    }
    try {
      const released = await release.mutateAsync(ids);
      toast.success(`Released ${released.length} payment${released.length === 1 ? "" : "s"}`);
      setSelected(new Set());
    } catch (err: any) {
      toast.error(err.message || "Release failed");
    }
  }

  return (
    <WebShell
      title="Payments"
      subtitle="Review and release approved task payouts"
      headerRight={
        <div className="flex gap-2">
          <Btn kind="ghost" icon={<Download size={15} />}>Export PDF</Btn>
          <Btn kind="primary" icon={<HandCoins size={15} />} onClick={() => releaseBatch(pending.map((p) => p.id))} disabled={release.isPending || !pending.length}>
            Release batch ({summary ? formatIDRShort(summary.pending_total) : "—"})
          </Btn>
        </div>
      }
    >
      <div className="p-7 grid grid-cols-[1fr_360px] gap-6 h-full overflow-hidden">
        <div className="flex flex-col gap-4 overflow-hidden">
          <div className="grid grid-cols-4 gap-3">
            <Card className="p-3.5"><Stat label="Due this week" value={summary ? formatIDR(summary.pending_total) : "—"} sub={`${summary?.pending_count ?? 0} villagers`} /></Card>
            <Card className="p-3.5"><Stat label="Released MTD" value={summary ? formatIDR(summary.released_total_mtd) : "—"} delta="+12%" sub="vs Apr" /></Card>
            <Card className="p-3.5"><Stat label="Avg payout" value={summary && summary.pending_count ? formatIDR(Math.round(summary.pending_total / summary.pending_count)) : "—"} /></Card>
            <Card className="p-3.5"><Stat label="Disputed" value="0" delta="−1" deltaTone="success" sub="of 217 last 30 d" /></Card>
          </div>
          <Card className="p-0 flex-1 overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-pg-border flex items-center gap-2.5">
              <span className="text-[13.5px] font-semibold">Pending payouts</span>
              <Chip tone="gold" size="sm">{pending.length} ready</Chip>
              <Chip tone="risk" size="sm">{pending.filter((p) => p.flag).length} flagged</Chip>
              <div className="ml-auto flex gap-2">
                <Btn kind="ghost" size="sm" icon={<Search size={14} />}>Find worker</Btn>
                <Btn kind="ghost" size="sm" icon={<SlidersHorizontal size={14} />}>Filter</Btn>
              </div>
            </div>
            <div className="overflow-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-pg-surface-sunken text-left">
                    <th className="px-4 py-2.5">
                      <input type="checkbox" checked={allSelected} onChange={toggleAll} />
                    </th>
                    {["Worker", "Task", "Rail", "Amount", "Approved", ""].map((h) => (
                      <th key={h} className="px-4 py-2.5 text-[11px] text-pg-ink-muted uppercase tracking-wider font-semibold border-b border-pg-border">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pending.map((p) => (
                    <tr key={p.id} className="border-b border-pg-border">
                      <td className="px-4 py-3">
                        <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold">{p.worker_name ?? p.worker_id}</div>
                        <div className="text-[11px] text-pg-ink-muted font-mono">{p.id}</div>
                      </td>
                      <td className="px-4 py-3 text-pg-ink-secondary">{p.task_title}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1.5 text-xs">
                          <span className="w-4.5 h-4.5 rounded-sm bg-pg-surface-sunken inline-grid place-items-center text-[9px] font-bold" style={{ width: 18, height: 18 }}>{p.rail.slice(0, 2).toUpperCase()}</span>
                          {p.rail}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-semibold font-mono">{formatIDR(p.amount)}</td>
                      <td className="px-4 py-3 text-pg-ink-muted text-xs">{p.created_at}</td>
                      <td className="px-4 py-3">{p.flag && <Chip tone="warn" size="sm">flagged: {p.flag}</Chip>}</td>
                    </tr>
                  ))}
                  {!pending.length && (
                    <tr><td colSpan={7} className="px-4 py-10 text-center text-pg-ink-muted text-sm">No pending payments. Approve a submission in Validation to queue a payout.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
        <aside className="flex flex-col gap-3.5">
          <Card className="p-4">
            <div className="text-[12.5px] font-semibold mb-2.5">Batch summary</div>
            {[
              ["Workers", `${selected.size || pending.length}`],
              ["Tasks completed", `${selected.size || pending.length}`],
              ["Subtotal", formatIDR(totalSelected || (summary?.pending_total ?? 0))],
              ["Service fee 0%", formatIDR(0)],
              ["Total to disburse", formatIDR(totalSelected || (summary?.pending_total ?? 0))],
            ].map(([k, v], i, a) => (
              <div key={k} className={`flex justify-between py-1.5 text-sm ${i === a.length - 1 ? "font-semibold border-t border-pg-border pt-3 mt-1.5" : ""}`}>
                <span className="text-pg-ink-secondary">{k}</span>
                <span className="font-mono">{v}</span>
              </div>
            ))}
            <Btn kind="primary" size="lg" full icon={<HandCoins size={16} />} className="mt-3" onClick={() => releaseBatch(selected.size ? Array.from(selected) : pending.map((p) => p.id))} disabled={release.isPending || !pending.length}>
              {release.isPending ? "Releasing…" : `Release ${formatIDRShort(totalSelected || (summary?.pending_total ?? 0))} now`}
            </Btn>
            <p className="text-[11px] text-pg-ink-muted mt-2.5 leading-snug">
              Funds settle DANA/OVO/GoPay in &lt; 60 s · BRI direct in 1 business day · PT Pos cash 24–48 h.
            </p>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2.5">
              <AlertTriangle size={16} className="text-pg-warn" />
              <span className="text-[12.5px] font-semibold">Anti-fraud · {pending.filter((p) => p.flag).length} flag</span>
            </div>
            <div className="text-[12.5px] text-pg-ink">
              <b>Agus W.</b> · 4 task completions in 6 hours, &gt;3× village median.
            </div>
            <div className="text-[11px] text-pg-ink-muted mt-1 leading-snug">
              Hold until manual review. Pattern match: <span className="font-mono">velocity-anomaly-v2</span>
            </div>
            <div className="mt-2.5 flex gap-1.5">
              <Btn kind="secondary" size="sm">Open dispute</Btn>
              <Btn kind="ghost" size="sm">Override</Btn>
            </div>
          </Card>
        </aside>
      </div>
    </WebShell>
  );
}
