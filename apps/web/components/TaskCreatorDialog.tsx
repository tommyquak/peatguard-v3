"use client";
// W4 · Task creator (modal over the W3 map).
// Source: design_handoff_peatguard/web-screens-2.jsx:4-105.

import { useEffect, useMemo, useState } from "react";
import { Check, Clock, Eye, Flame, Leaf, Shield, Upload, X } from "lucide-react";
import { toast } from "sonner";
import { Btn } from "@/components/ui/Btn";
import { useCreateTask, useVillages } from "@/lib/api";
import type { TaskType } from "@/lib/types";

const TYPES: { id: TaskType; label: string; icon: typeof Shield }[] = [
  { id: "canal_block", label: "Canal block", icon: Shield },
  { id: "revegetation", label: "Revegetation", icon: Leaf },
  { id: "patrol", label: "Monitor patrol", icon: Eye },
  { id: "fire_watch", label: "Fire watch", icon: Flame },
];

const DELIVERABLES_BY_TYPE: Record<TaskType, string[]> = {
  canal_block: [
    "3 photos: before, mid, after canal block",
    "GPS track of dam edge (≥ 8 m linear)",
    "Timestamp within working window 06:00–17:00 WIB",
    "Voice note: rationale for blockage",
  ],
  revegetation: [
    "Photos of seedlings planted (3+)",
    "GPS perimeter walk of plot",
    "Headcount of seedlings",
  ],
  patrol: [
    "GPS track for full route",
    "Photos at 4 checkpoints",
    "Voice note of any incidents",
  ],
  fire_watch: ["Photos of patrol area", "GPS log of route", "Incident voice note if any"],
};

const PAYOUT_DEFAULTS: Record<TaskType, number> = {
  canal_block: 250_000,
  revegetation: 180_000,
  patrol: 120_000,
  fire_watch: 150_000,
};

export function TaskCreatorDialog({
  open,
  aoiCode,
  onClose,
}: {
  open: boolean;
  aoiCode: string;
  onClose: () => void;
}) {
  const { data: villages = [] } = useVillages();
  const createTask = useCreateTask();
  const [type, setType] = useState<TaskType>("canal_block");
  const [title, setTitle] = useState("Block canal — Sebangau C-04");
  const [payout, setPayout] = useState(250_000);
  const [deadline, setDeadline] = useState("2026-05-18T17:00");
  const [villageId, setVillageId] = useState<string | null>(null);

  useEffect(() => {
    if (open && villages.length && !villageId) {
      const fallback = villages.find((v) => v.aoi_code === aoiCode) || villages[0];
      setVillageId(fallback.id);
    }
  }, [open, villages, aoiCode, villageId]);

  useEffect(() => {
    setPayout(PAYOUT_DEFAULTS[type]);
  }, [type]);

  if (!open) return null;

  const village = villages.find((v) => v.id === villageId);

  async function publish() {
    try {
      await createTask.mutateAsync({
        aoi_code: aoiCode,
        type,
        title,
        sub: undefined,
        payout_idr: payout,
        deadline,
        village_id: villageId,
        polygon: {
          type: "Polygon",
          coordinates: [
            [
              [113.91, -2.342],
              [113.92, -2.342],
              [113.92, -2.352],
              [113.91, -2.352],
              [113.91, -2.342],
            ],
          ],
        },
        deliverables: DELIVERABLES_BY_TYPE[type],
      });
      toast.success("Task published to mobile app");
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to publish");
    }
  }

  return (
    <div className="absolute top-6 right-6 bottom-6 w-[460px] bg-pg-surface-raised rounded-xl shadow-pop flex flex-col overflow-hidden z-30">
      <div className="px-5 py-4 border-b border-pg-border flex items-center justify-between">
        <div>
          <div className="text-xs text-pg-ink-muted font-semibold uppercase tracking-wider">
            New task · draft
          </div>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="text-base font-semibold mt-0.5 outline-none bg-transparent w-full"
          />
        </div>
        <button onClick={onClose}>
          <X size={18} className="text-pg-ink-muted cursor-pointer" />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-5 flex flex-col gap-4.5">
        <div>
          <Label>Task type</Label>
          <div className="grid grid-cols-2 gap-2 mt-1.5">
            {TYPES.map((t) => {
              const sel = t.id === type;
              const Icon = t.icon;
              return (
                <button
                  key={t.id}
                  onClick={() => setType(t.id)}
                  className={`px-3 py-2.5 border rounded-md flex items-center gap-2 text-left ${
                    sel
                      ? "border-pg-primary bg-pg-primary-soft text-pg-primary border-[1.5px]"
                      : "border-pg-border bg-pg-surface-raised text-pg-ink"
                  }`}
                >
                  <Icon size={17} className={sel ? "text-pg-primary" : "text-pg-ink-secondary"} />
                  <span className="text-sm font-semibold">{t.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Payout (IDR)</Label>
            <div className="mt-1.5 h-11 px-3 border border-pg-border-strong rounded-md flex items-center">
              <span className="font-mono text-xs text-pg-ink-muted mr-1.5">Rp</span>
              <input
                type="number"
                value={payout}
                onChange={(e) => setPayout(parseInt(e.target.value || "0", 10))}
                className="text-base font-semibold text-pg-ink bg-transparent outline-none w-full"
              />
            </div>
            <div className="text-[11px] text-pg-ink-muted mt-1">≈ daily-wage × 1.4 (district)</div>
          </div>
          <div>
            <Label>Deadline</Label>
            <div className="mt-1.5 h-11 px-3 border border-pg-border-strong rounded-md flex items-center gap-2">
              <Clock size={15} className="text-pg-ink-muted" />
              <input
                type="datetime-local"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="text-sm text-pg-ink bg-transparent outline-none w-full"
              />
            </div>
          </div>
        </div>

        <div>
          <Label>Assigned village</Label>
          <div className="mt-1.5 p-3 border border-pg-border rounded-md flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-pg-primary-soft text-pg-primary grid place-items-center font-bold text-sm">
              {village?.name?.[0] ?? "?"}
            </div>
            <div className="flex-1">
              <div className="text-[13.5px] font-semibold">{village?.name ?? "—"}</div>
              <div className="text-[11px] text-pg-ink-muted font-mono">
                1.8 km · 22 verified workers
              </div>
            </div>
            <select
              value={villageId ?? ""}
              onChange={(e) => setVillageId(e.target.value)}
              className="bg-transparent text-xs text-pg-primary font-semibold outline-none"
            >
              {villages.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <Label>Required deliverables</Label>
          <div className="flex flex-col gap-1.5 mt-1.5">
            {DELIVERABLES_BY_TYPE[type].map((d) => (
              <div key={d} className="flex items-center gap-2 text-[12.5px]">
                <span className="w-4 h-4 rounded-sm bg-pg-primary grid place-items-center">
                  <Check size={12} className="text-white" />
                </span>
                {d}
              </div>
            ))}
          </div>
        </div>

        <div>
          <Label>Reference photos (expected outcome)</Label>
          <div className="grid grid-cols-3 gap-2 mt-1.5">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="pg-raster-stub rounded-sm"
                data-layer={`ref_${i}.jpg`}
                style={{ aspectRatio: "4/3" }}
              />
            ))}
          </div>
        </div>
      </div>
      <div className="border-t border-pg-border p-3.5 flex items-center gap-2.5 bg-pg-surface-sunken">
        <div className="text-[11.5px] text-pg-ink-secondary flex-1">
          <div>
            Polygon area: <b>0.42 ha</b> · Mean risk{" "}
            <b className="font-mono">0.74</b>
          </div>
          <div className="mt-0.5">3 canal segments intersect · 0 water_mask conflicts</div>
        </div>
        <Btn kind="secondary">Save draft</Btn>
        <Btn kind="primary" icon={<Upload size={15} />} onClick={publish} disabled={createTask.isPending}>
          {createTask.isPending ? "Publishing…" : "Publish"}
        </Btn>
      </div>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11.5px] text-pg-ink-secondary font-semibold uppercase tracking-wider">
      {children}
    </div>
  );
}
