"use client";
// W3 · AOI deep-dive map view (+ W4 Task creator dialog).
// Source: web-screens-1.jsx:236-376 (W3) and web-screens-2.jsx:4-105 (W4).

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import {
  Download,
  Eye,
  Flag,
  Layers,
  Leaf,
  MapIcon,
  Plus,
  Pyramid,
  Settings as SettingsIcon,
  Shield,
  X,
} from "lucide-react";
import { WebShell } from "@/components/WebShell";
import { Btn } from "@/components/ui/Btn";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { MapStub } from "@/components/ui/MapStub";
import { Field } from "@/components/ui/Stat";
import { useAois } from "@/lib/api";
import { TaskCreatorDialog } from "@/components/TaskCreatorDialog";

interface LayerRow {
  id: string;
  label: string;
  file: string;
  on: boolean;
  opacity: number;
  swatch: string;
  conf?: boolean;
}

const SEED_LAYERS: LayerRow[] = [
  { id: "canal_risk", label: "Canal risk", file: "canal_risk.tif", on: true, opacity: 78, swatch: "risk", conf: true },
  { id: "subsidence_velocity", label: "Subsidence velocity", file: "subsidence_velocity_utm.tif", on: true, opacity: 55, swatch: "warn" },
  { id: "subsidence_class", label: "Subsidence class", file: "subsidence_class_utm.tif", on: false, opacity: 60, swatch: "warn" },
  { id: "canal_mask", label: "Canal mask", file: "canal_mask.tif", on: true, opacity: 100, swatch: "primary" },
  { id: "canal_distance", label: "Distance to canal", file: "canal_distance.tif", on: false, opacity: 60, swatch: "info" },
  { id: "water_mask", label: "Open water", file: "water_mask.tif", on: false, opacity: 70, swatch: "info" },
  { id: "peat_extent", label: "Peat extent (WRI)", file: "peat_extent_binary.tif", on: false, opacity: 35, swatch: "primary" },
  { id: "vv_basemap", label: "SAR backscatter (VV dB)", file: "vv_median_db.tif", on: true, opacity: 100, swatch: "neutral" },
  { id: "deforestation", label: "Hansen forest loss", file: "deforestation_year.tif", on: false, opacity: 70, swatch: "risk" },
  { id: "carbon", label: "Carbon loss tCO₂/ha/yr", file: "carbon_loss.tif", on: false, opacity: 70, swatch: "gold" },
];

const SWATCH_BG: Record<string, string> = {
  risk: "bg-pg-risk",
  warn: "bg-pg-warn",
  primary: "bg-pg-primary",
  info: "bg-pg-info",
  gold: "bg-pg-gold",
  neutral: "bg-pg-border-strong",
};

export default function MapPage() {
  const params = useSearchParams();
  const aoiCode = params.get("aoi") || "SBG-C";
  const { data: aois = [] } = useAois();
  const aoi = aois.find((a) => a.code === aoiCode);

  const [layers, setLayers] = useState<LayerRow[]>(SEED_LAYERS);
  const [creatorOpen, setCreatorOpen] = useState(false);
  const canalRisk = layers.find((l) => l.id === "canal_risk");

  const toggle = (id: string) =>
    setLayers((ls) => ls.map((l) => (l.id === id ? { ...l, on: !l.on } : l)));

  return (
    <WebShell
      dense
      title={`${aoi?.name ?? "Sebangau Block C"} · canal_risk`}
      subtitle={aoi
        ? `AOI · ${aoi.area_ha.toLocaleString()} ha · last refresh ${aoi.refresh_date} · S1 + InSAR pipeline`
        : "AOI · S1 + InSAR pipeline"}
      headerRight={
        <div className="flex gap-2">
          <Btn kind="ghost" icon={<Layers size={15} />}>Compare</Btn>
          <Btn kind="secondary" icon={<Download size={15} />}>Export view</Btn>
          <Btn kind="primary" icon={<Pyramid size={15} />} onClick={() => setCreatorOpen(true)}>Create task</Btn>
        </div>
      }
    >
      <div className="grid grid-cols-[288px_1fr_320px] h-full">
        {/* Layers panel */}
        <aside className="border-r border-pg-border bg-pg-surface-raised flex flex-col overflow-hidden">
          <div className="px-4 py-3.5 border-b border-pg-border flex items-center gap-2">
            <Layers size={16} className="text-pg-ink-secondary" />
            <span className="text-sm font-semibold">Layers</span>
            <span className="text-[11px] text-pg-ink-muted ml-auto">{layers.length} available</span>
          </div>
          <div className="flex-1 overflow-auto">
            {layers.map((l) => (
              <LayerRowView key={l.id} l={l} onToggle={() => toggle(l.id)} />
            ))}
          </div>
          <div className="p-3 border-t border-pg-border flex flex-col gap-1.5">
            <div className="text-[11px] text-pg-ink-muted flex justify-between">
              <span>Confidence overlay</span>
              <span className="font-mono">velocity-backed</span>
            </div>
            <div className="h-1.5 rounded" style={{ background: "linear-gradient(90deg, #f5e0a8, #c89b3c, #1f4d3a)" }} />
            <div className="text-[10px] text-pg-ink-muted flex justify-between font-mono">
              <span>proximity-only</span>
              <span>InSAR-confirmed</span>
            </div>
          </div>
        </aside>

        {/* Map */}
        <div className="relative overflow-hidden">
          <MapStub
            layer={canalRisk?.on ? "canal_risk · vv_median_db basemap" : "vv_median_db basemap"}
            bg="/aoi-satellite.png"
            overlay={canalRisk?.on ? "/aoi-classified.png" : null}
            overlayOpacity={(canalRisk?.opacity || 78) / 100}
            full
            className="rounded-none h-full"
          >
            <svg width="100%" height="100%" className="absolute inset-0 pointer-events-none">
              <defs>
                <pattern id="hatch1" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <line x1="0" y1="0" x2="0" y2="6" stroke="rgba(31,77,58,0.4)" strokeWidth="1.5" />
                </pattern>
              </defs>
              <rect x="55%" y="20%" width="35%" height="55%" fill="url(#hatch1)" rx="40" />
            </svg>
            <div className="absolute" style={{ top: "46%", left: "52%" }}>
              <div className="w-4.5 h-4.5 border-2 border-white rounded-full bg-pg-risk shadow-[0_0_0_4px_rgba(179,38,30,0.25),0_2px_6px_rgba(0,0,0,0.3)]" style={{ width: 18, height: 18 }} />
            </div>
            <div className="absolute bottom-4 left-4 flex flex-col gap-2 font-mono text-[10px] text-black/75">
              <div className="flex items-center gap-1">
                <div className="w-20 h-1.5 border border-black/70 flex">
                  <div className="flex-1 bg-black/70" />
                  <div className="flex-1" />
                  <div className="flex-1 bg-black/70" />
                  <div className="flex-1" />
                </div>
                <span>2 km</span>
              </div>
            </div>
            <div className="absolute top-4 right-4 flex flex-col gap-1.5">
              {([Plus, X, MapIcon, SettingsIcon] as const).map((Icon, i) => (
                <button key={i} className="w-9 h-9 rounded-md bg-pg-surface-raised border border-pg-border-strong grid place-items-center">
                  <Icon size={16} />
                </button>
              ))}
            </div>
            <div className="absolute top-4 left-4 font-mono text-[11px] bg-white/85 border border-pg-border px-2.5 py-1.5 rounded-md">
              −2.342° S, 113.911° E · zoom 13 · EPSG:32749
            </div>
          </MapStub>
        </div>

        {/* Inspector */}
        <aside className="border-l border-pg-border bg-pg-surface-raised flex flex-col overflow-hidden">
          <div className="px-4 py-3.5 border-b border-pg-border">
            <div className="text-[11px] text-pg-ink-muted uppercase tracking-wider font-semibold">Pixel inspector</div>
            <div className="text-sm mt-1 font-mono">−2.3417, 113.9114</div>
          </div>
          <div className="p-4 flex flex-col gap-3.5 overflow-auto">
            <Card className="p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[12.5px] font-semibold">Restoration priority</span>
                <Chip tone="risk" size="sm">Critical</Chip>
              </div>
              <div className="text-[32px] font-semibold tracking-tight font-mono">0.81</div>
              <div className="mt-2 h-1.5 bg-pg-surface-sunken rounded-sm overflow-hidden">
                <div className="h-full" style={{ width: "81%", background: "linear-gradient(90deg, #57a773, #e08c0c, #b3261e)" }} />
              </div>
              <div className="text-[11px] text-pg-ink-muted mt-1 font-mono">velocity-backed (confidence = 2)</div>
            </Card>
            <div className="grid grid-cols-2 gap-3.5">
              <Field label="Subsidence velocity" value="−18.4 mm/yr" mono />
              <Field label="Subsidence class" value="5 / 6 (severe)" />
              <Field label="Distance to canal" value="42 m" mono />
              <Field label="Peat depth est." value="3.8 m" />
              <Field label="Hansen loss year" value="2016" />
              <Field label="Carbon loss" value="22.4 tCO₂/ha/yr" mono />
              <Field label="VV backscatter" value="−14.2 dB" mono />
              <Field label="Water mask" value="0 (dry)" />
            </div>
            <div className="border-t border-pg-border pt-3">
              <div className="text-[11px] text-pg-ink-muted uppercase tracking-wider font-semibold mb-2">Suggested actions</div>
              <div className="flex flex-col gap-1.5">
                <Btn kind="primary" size="sm" full icon={<Pyramid size={14} />} onClick={() => setCreatorOpen(true)}>Create canal-block task</Btn>
                <Btn kind="soft" size="sm" full icon={<Leaf size={14} />}>Queue revegetation plot</Btn>
                <Btn kind="ghost" size="sm" full icon={<Flag size={14} />}>Flag for review</Btn>
              </div>
            </div>
          </div>
        </aside>
      </div>

      <TaskCreatorDialog
        open={creatorOpen}
        aoiCode={aoiCode}
        onClose={() => setCreatorOpen(false)}
      />
    </WebShell>
  );
}

function LayerRowView({ l, onToggle }: { l: LayerRow; onToggle: () => void }) {
  return (
    <div className="px-3.5 py-2.5 flex items-center gap-2.5 border-b border-pg-surface-sunken">
      <button
        onClick={onToggle}
        className={`w-7 h-4 rounded-full relative shrink-0 ${l.on ? "bg-pg-primary" : "bg-pg-border-strong"}`}
      >
        <span
          className="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-[left]"
          style={{ left: l.on ? 14 : 2 }}
        />
      </button>
      <div className={`w-3 h-3 rounded-sm ${SWATCH_BG[l.swatch] || "bg-pg-border-strong"}`} />
      <div className="flex-1 min-w-0">
        <div className={`text-[12.5px] font-medium ${l.on ? "text-pg-ink" : "text-pg-ink-muted"}`}>
          {l.label}
          {l.conf && <span className="ml-1 text-pg-accent text-[10px]">●</span>}
        </div>
        <div className="text-[10.5px] text-pg-ink-muted font-mono">{l.file}</div>
      </div>
      <span className="text-[11px] text-pg-ink-muted font-mono w-7 text-right">{l.opacity}%</span>
    </div>
  );
}
