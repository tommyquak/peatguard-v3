"use client";
// W2 · AOI Dashboard.
// Source: design_handoff_peatguard/web-screens-1.jsx:158-233.

import Link from "next/link";
import { Download, Grid3x3, Layers, Plus, RefreshCcw, Search, SlidersHorizontal } from "lucide-react";
import { WebShell } from "@/components/WebShell";
import { Btn } from "@/components/ui/Btn";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { MapStub } from "@/components/ui/MapStub";
import { Field, Stat } from "@/components/ui/Stat";
import { useAois, usePaymentSummary, useTasks } from "@/lib/api";
import type { Aoi } from "@/lib/types";
import { formatIDRShort } from "@/lib/cn";

export default function DashboardPage() {
  const { data: aois = [] } = useAois();
  const { data: pendingValidation = [] } = useTasks({ status: "submitted" });
  const { data: pmtSummary } = usePaymentSummary();

  const totalArea = aois.reduce((s, a) => s + a.area_ha, 0);
  const totalRestored = aois.reduce((s, a) => s + a.restored_ha, 0);

  return (
    <WebShell
      title="Programme overview"
      subtitle={`PeatGuard ops · Kalimantan · ${aois.length} active AOIs`}
      headerRight={
        <div className="flex gap-2">
          <Btn kind="ghost" icon={<RefreshCcw size={15} />}>Refresh data</Btn>
          <Btn kind="secondary" icon={<Download size={15} />}>Export</Btn>
          <Btn kind="primary" icon={<Plus size={15} />}>New AOI</Btn>
        </div>
      }
    >
      <div className="p-7 flex flex-col gap-5 h-full overflow-auto">
        <div className="grid grid-cols-6 gap-3.5">
          <Card className="p-4"><Stat label="Hectares monitored" value={totalArea.toLocaleString()} sub={`across ${aois.length} AOIs`} /></Card>
          <Card className="p-4"><Stat label="Restored YTD" value={`${totalRestored.toLocaleString()} ha`} delta="+8.4%" sub="vs Apr" /></Card>
          <Card className="p-4"><Stat label="tCO₂/yr avoided" value="142,180" delta="+11%" sub="last 30 d" /></Card>
          <Card className="p-4"><Stat label="Active tasks" value="217" sub="in 14 villages" /></Card>
          <Card className="p-4"><Stat label="Pending review" value={pendingValidation.length.toString()} delta="+4" deltaTone="risk" sub="oldest 36 h" /></Card>
          <Card className="p-4"><Stat label="Payouts due wk" value={pmtSummary ? formatIDRShort(pmtSummary.pending_total) : "—"} sub={`${pmtSummary?.pending_count ?? 0} villagers`} /></Card>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            <Chip tone="primary"><Layers size={11} className="mr-0.5"/>All AOIs · {aois.length}</Chip>
            <Chip tone="risk">{aois.filter(a => a.risk > 0.7).length} critical</Chip>
            <Chip tone="warn">{aois.filter(a => a.risk > 0.55 && a.risk <= 0.7).length} elevated</Chip>
            <Chip tone="success">{aois.filter(a => a.risk <= 0.55).length} stable</Chip>
          </div>
          <div className="flex gap-2">
            <Btn kind="ghost" size="sm" icon={<Search size={14} />}>Search AOIs</Btn>
            <Btn kind="ghost" size="sm" icon={<SlidersHorizontal size={14} />}>Sort: priority</Btn>
            <Btn kind="ghost" size="sm" icon={<Grid3x3 size={14} />}>Grid</Btn>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {aois.map((a) => <AoiTile key={a.code} a={a} />)}
        </div>
      </div>
    </WebShell>
  );
}

function AoiTile({ a }: { a: Aoi }) {
  const tone: "risk" | "warn" | "success" = a.risk > 0.7 ? "risk" : a.risk > 0.55 ? "warn" : "success";
  return (
    <Link href={`/map?aoi=${a.code}`}>
      <Card className="p-0 overflow-hidden hover:shadow-sticky transition-shadow cursor-pointer">
        <div className="h-[132px] relative">
          <MapStub
            layer={`${a.code} · canal_risk.tif`}
            bg="/aoi-satellite.png"
            overlay="/aoi-classified.png"
            overlayOpacity={0.62}
            className="rounded-none h-full"
          >
            <div
              className="absolute inset-0"
              style={{ background: "linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.35))" }}
            />
            <div className="absolute top-2.5 left-2.5 flex gap-1.5">
              <Chip tone={tone} size="sm">Risk {a.risk.toFixed(2)}</Chip>
            </div>
            <div className="absolute top-2.5 right-2.5 text-[10px] text-white font-mono bg-black/45 px-1.5 py-0.5 rounded">
              {a.code}
            </div>
          </MapStub>
        </div>
        <div className="p-3.5 flex flex-col gap-2.5">
          <div>
            <div className="text-[14.5px] font-semibold text-pg-ink tracking-tight">{a.name}</div>
            <div className="text-[11.5px] text-pg-ink-muted font-mono">
              {a.area_ha.toLocaleString()} ha · refresh {a.refresh_date}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2.5 pt-2 border-t border-dashed border-pg-border">
            <Field label="% critical" value={`${a.pct_critical.toFixed(1)}%`} />
            <Field label="Restored" value={`${a.restored_ha} ha`} />
            <Field label="Progress" value={`${a.progress_pct}%`} />
          </div>
          <div className="h-1 bg-pg-surface-sunken rounded-sm overflow-hidden">
            <div className="h-full bg-pg-accent" style={{ width: `${a.progress_pct}%` }} />
          </div>
        </div>
      </Card>
    </Link>
  );
}
