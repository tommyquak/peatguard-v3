"use client";
// W5 · Validation queue.
// Source: design_handoff_peatguard/web-screens-2.jsx:111-227.

import { useEffect, useState } from "react";
import { ArrowRight, Check, MessageCircle, Play, SlidersHorizontal, X } from "lucide-react";
import { toast } from "sonner";
import { WebShell } from "@/components/WebShell";
import { Btn } from "@/components/ui/Btn";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { MapStub } from "@/components/ui/MapStub";
import { useDecideTask, useTasks, useWorkers } from "@/lib/api";
import { formatIDR } from "@/lib/cn";
import type { Task, Worker } from "@/lib/types";

export default function ValidationPage() {
  const { data: items = [] } = useTasks({ status: "submitted" });
  const { data: workers = [] } = useWorkers();
  const decide = useDecideTask();
  const [activeId, setActiveId] = useState<string | null>(null);
  const active = items.find((t) => t.id === activeId) || items[0] || null;

  useEffect(() => {
    if (!activeId && items.length) setActiveId(items[0].id);
  }, [activeId, items]);

  async function act(action: "approve" | "revise" | "reject") {
    if (!active) return;
    try {
      await decide.mutateAsync({ id: active.id, action });
      toast.success(
        action === "approve"
          ? `Approved · payment of ${formatIDR(active.payout_idr)} queued`
          : action === "revise"
            ? "Revision request sent"
            : "Submission rejected",
      );
    } catch (err: any) {
      toast.error(err.message || "Failed");
    }
  }

  return (
    <WebShell
      title="Validation queue"
      subtitle={`${items.length} submission${items.length === 1 ? "" : "s"} awaiting review · oldest 36 h`}
      headerRight={
        <div className="flex gap-2">
          <Btn kind="ghost" icon={<SlidersHorizontal size={15} />}>Filters</Btn>
          <Btn kind="secondary" icon={<Check size={15} />}>Bulk approve passed</Btn>
        </div>
      }
    >
      <div className="grid grid-cols-[380px_1fr] h-full">
        <aside className="border-r border-pg-border overflow-auto bg-pg-surface-raised">
          {items.length === 0 && (
            <div className="p-7 text-sm text-pg-ink-muted text-center">
              No submissions awaiting review.
            </div>
          )}
          {items.map((t) => (
            <ValRow
              key={t.id}
              task={t}
              workers={workers}
              active={t.id === active?.id}
              onClick={() => setActiveId(t.id)}
            />
          ))}
        </aside>
        <section className="p-6 overflow-auto flex flex-col gap-4">
          {active ? (
            <ValDetail task={active} workers={workers} onAct={act} pending={decide.isPending} />
          ) : (
            <div className="text-pg-ink-muted text-center">No submission selected.</div>
          )}
        </section>
      </div>
    </WebShell>
  );
}

function ValRow({
  task, workers, active, onClick,
}: { task: Task; workers: Worker[]; active: boolean; onClick: () => void }) {
  const w = workers.find((x) => x.id === task.worker_id);
  const auto = {
    gps: task.photos.every((p) => p.accuracy_m <= 18),
    time: !!task.submitted_at,
    blur: true,
  };
  const okCount = Object.values(auto).filter(Boolean).length;
  return (
    <div
      onClick={onClick}
      className={`p-3.5 border-b border-pg-border flex gap-3 cursor-pointer ${active ? "bg-pg-primary-soft border-l-[3px] border-l-pg-primary" : "border-l-[3px] border-l-transparent"}`}
    >
      <div className="pg-raster-stub w-14 h-14 rounded-sm shrink-0" data-layer="" />
      <div className="flex-1 min-w-0">
        <div className="text-[13.5px] font-semibold">{w?.name ?? task.worker_id ?? "Unknown worker"}</div>
        <div className="text-xs text-pg-ink-secondary truncate">{task.title}</div>
        <div className="text-[11px] text-pg-ink-muted flex gap-2 mt-1">
          <span>{w?.village ?? "—"}</span>·<span>{task.submitted_at ?? task.created_at}</span>
        </div>
        <div className="flex gap-1 mt-1.5">
          <Chip size="sm" tone={auto.gps ? "success" : "risk"}>GPS</Chip>
          <Chip size="sm" tone={auto.time ? "success" : "risk"}>Time</Chip>
          <Chip size="sm" tone={auto.blur ? "success" : "warn"}>Blur</Chip>
          <span className="ml-auto text-[10.5px] text-pg-ink-muted font-mono">{okCount}/3</span>
        </div>
      </div>
    </div>
  );
}

function ValDetail({
  task, workers, onAct, pending,
}: { task: Task; workers: Worker[]; onAct: (a: "approve" | "revise" | "reject") => void; pending: boolean }) {
  const w = workers.find((x) => x.id === task.worker_id);
  const initials = (w?.name ?? "??").split(" ").slice(0, 2).map((s) => s[0]).join("").toUpperCase();
  return (
    <>
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-md text-white grid place-items-center font-bold text-base"
          style={{ background: "linear-gradient(135deg,#3d2818,#c89b3c)" }}>
          {initials}
        </div>
        <div className="flex-1">
          <div className="text-[17px] font-semibold">{w?.name ?? task.worker_id} · {task.title}</div>
          <div className="text-[12.5px] text-pg-ink-secondary">
            {w?.village ?? "—"} · submitted {task.submitted_at ?? task.created_at} · payout{" "}
            <b className="text-pg-ink font-mono">{formatIDR(task.payout_idr)}</b>
          </div>
        </div>
        <Btn kind="secondary" icon={<MessageCircle size={15} />}>Message</Btn>
        <Btn kind="ghost" icon={<X size={15} />} onClick={() => onAct("reject")} disabled={pending}>Reject</Btn>
        <Btn kind="secondary" onClick={() => onAct("revise")} disabled={pending}>Request revision</Btn>
        <Btn kind="success" icon={<Check size={15} />} onClick={() => onAct("approve")} disabled={pending}>
          Approve & release {formatIDR(task.payout_idr)}
        </Btn>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card className="p-0 overflow-hidden">
          <div className="px-3.5 py-2.5 border-b border-pg-border flex items-center justify-between">
            <span className="text-[12.5px] font-semibold">Before / After</span>
            <span className="text-[11px] text-pg-ink-muted font-mono">P-01 ↔ P-03</span>
          </div>
          <div className="pg-raster-stub h-[280px] relative" data-layer={`before · ${task.submitted_at ?? task.created_at}`}>
            <div className="absolute inset-0" style={{ background: "linear-gradient(90deg, rgba(60,40,24,0.3) 0 52%, transparent 52%)" }} />
            <div className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.2)]" style={{ left: "52%" }} />
            <div className="absolute -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white border border-pg-border-strong grid place-items-center" style={{ left: "52%", top: "50%" }}>
              <ArrowRight size={14} />
            </div>
            <div className="absolute top-2 left-2 text-[11px] font-mono text-white bg-black/45 px-1.5 py-0.5 rounded">BEFORE</div>
            <div className="absolute top-2 right-2 text-[11px] font-mono text-white bg-black/45 px-1.5 py-0.5 rounded">AFTER</div>
          </div>
          <div className="grid grid-cols-3 gap-px bg-pg-border p-px">
            {(task.photos.length ? task.photos : [{ phase: "before", ts: 0 }, { phase: "during", ts: 0 }, { phase: "after", ts: 0 }]).slice(0, 3).map((p, i) => (
              <div key={i} className="pg-raster-stub" data-layer={`P-0${i + 1} ${p.phase}`} style={{ aspectRatio: "4/3" }} />
            ))}
          </div>
        </Card>

        <div className="flex flex-col gap-4">
          <Card className="p-0 overflow-hidden">
            <div className="px-3.5 py-2.5 border-b border-pg-border text-[12.5px] font-semibold">GPS track on canal_mask</div>
            <div className="h-[188px] relative">
              <MapStub layer="canal_mask · GPS track" bg="/aoi-satellite.png" className="rounded-none h-full">
                <svg width="100%" height="100%" className="absolute inset-0">
                  <path d="M 60 110 Q 120 80 180 90 T 320 100" stroke="#b3261e" strokeWidth="3" fill="none" strokeLinecap="round" />
                  <circle cx="60" cy="110" r="6" fill="#b3261e" stroke="#fff" strokeWidth="2" />
                  <circle cx="320" cy="100" r="6" fill="#57a773" stroke="#fff" strokeWidth="2" />
                </svg>
              </MapStub>
            </div>
          </Card>
          <Card className="p-3.5">
            <div className="text-[12.5px] font-semibold mb-2.5">Auto-checks</div>
            {[
              { l: "GPS within 18 m of expected polygon", ok: true, v: "8.4 m mean offset" },
              { l: "Timestamps inside working window", ok: true, v: "06:42 → 11:53 WIB" },
              { l: "Photo blur / quality score", ok: true, v: "0.91 (≥ 0.8 required)" },
              { l: "Hash chain · device-sealed", ok: true, v: `sha256 · ${task.photos.length} segments` },
              { l: "Track linear length ≥ 8 m", ok: true, v: "24.1 m" },
            ].map((c) => (
              <div key={c.l} className="flex items-center gap-2.5 py-1.5 text-[12.5px]">
                <span className={`w-4.5 h-4.5 rounded-full grid place-items-center ${c.ok ? "bg-pg-accent-soft text-pg-accent" : "bg-pg-risk-soft text-pg-risk"}`} style={{ width: 18, height: 18 }}>
                  {c.ok ? <Check size={11} strokeWidth={2.5} /> : <X size={11} strokeWidth={2.5} />}
                </span>
                <span className="flex-1 text-pg-ink">{c.l}</span>
                <span className="text-pg-ink-muted font-mono text-[11px]">{c.v}</span>
              </div>
            ))}
          </Card>
          <Card className="p-3.5">
            <div className="text-[12.5px] font-semibold mb-1.5">Worker note (Bahasa)</div>
            <p className="text-sm text-pg-ink leading-relaxed">
              "Saya pasang dam di mulut kanal sesuai instruksi. Air mulai naik di sisi hulu setelah 2 jam. Tidak ada gangguan."
            </p>
            <div className="flex items-center gap-2 mt-2.5">
              <Btn kind="ghost" size="sm" icon={<Play size={13} />}>Play voice (0:24)</Btn>
              <span className="text-[11px] text-pg-ink-muted">· Auto-translated EN available</span>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
