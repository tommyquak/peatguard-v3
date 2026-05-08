"use client";
// W8 · Reports & impact.
// Source: design_handoff_peatguard/web-screens-2.jsx:408-527.

import { Download, Eye, File as FileIcon } from "lucide-react";
import { WebShell } from "@/components/WebShell";
import { Btn } from "@/components/ui/Btn";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Stat } from "@/components/ui/Stat";

export default function ReportsPage() {
  return (
    <WebShell
      title="Reports & impact"
      subtitle="Auto-generated monthly · public transparency view"
      headerRight={
        <div className="flex gap-2">
          <Btn kind="ghost" icon={<Eye size={15} />}>Preview public view</Btn>
          <Btn kind="primary" icon={<Download size={15} />}>Download April 2026 PDF</Btn>
        </div>
      }
    >
      <div className="p-7 grid grid-cols-[1fr_360px] gap-6 h-full overflow-auto">
        <div className="flex flex-col gap-4.5">
          <Card className="p-5">
            <div className="flex items-start justify-between gap-3.5">
              <div>
                <div className="text-[11.5px] text-pg-ink-muted uppercase tracking-wider font-semibold">
                  April 2026 · Programme report
                </div>
                <h2 className="text-xl font-semibold tracking-tight mt-1">PeatGuard · Kalimantan programme</h2>
                <div className="text-sm text-pg-ink-secondary mt-1">
                  Reporting period 1–30 Apr · 6 AOIs · 14 villages · partner: BRGM
                </div>
              </div>
              <div className="flex gap-1.5">
                <Chip tone="success" size="sm">On track</Chip>
                <Chip tone="primary" size="sm">v4.2.1</Chip>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-3.5 mt-4.5">
              <Stat label="Canal blocks built" value="412" delta="+47" sub="vs Mar" />
              <Stat label="Hectares restored" value="3,282" delta="+8.4%" />
              <Stat label="tCO₂/yr avoided" value="142,180" delta="+11%" />
              <Stat label="Payments disbursed" value="Rp 142.7 jt" />
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center justify-between mb-3.5">
              <div className="text-[13.5px] font-semibold">Restoration progress · 12-month trend</div>
              <div className="flex gap-1.5">
                <Chip size="sm" tone="primary">Restored ha</Chip>
                <Chip size="sm" tone="success">Canal blocks</Chip>
              </div>
            </div>
            <ChartStub />
          </Card>

          <div className="grid grid-cols-2 gap-4">
            <Card className="p-4.5">
              <div className="text-sm font-semibold mb-2.5">By AOI · hectares restored</div>
              {[
                ["Mawas East", 880, 72],
                ["Sungai Putri", 1120, 90],
                ["Padang Sugihan", 540, 44],
                ["Sebangau Block C", 412, 36],
                ["Berbak-Sembilang", 240, 18],
                ["Kampar Peninsula N", 90, 7],
              ].map(([name, ha, p]) => (
                <div key={name as string} className="flex items-center gap-2.5 py-1.5 text-[12.5px]">
                  <span className="w-32 text-pg-ink-secondary">{name}</span>
                  <div className="flex-1 h-2 bg-pg-surface-sunken rounded-sm overflow-hidden">
                    <div className="h-full bg-pg-accent" style={{ width: `${p}%` }} />
                  </div>
                  <span className="font-mono min-w-[56px] text-right">{ha} ha</span>
                </div>
              ))}
            </Card>
            <Card className="p-4.5">
              <div className="text-sm font-semibold mb-2.5">Public transparency</div>
              <p className="text-[12.5px] text-pg-ink-secondary leading-relaxed">
                Donors and journalists can read this report at a permanent URL. No login. Personally
                identifying data is hashed.
              </p>
              <div className="mt-3 p-3 bg-pg-surface-sunken rounded-md font-mono text-xs text-pg-ink break-all">
                peatguard.id/r/clk-2026-04
              </div>
              <div className="mt-2.5 flex gap-1.5">
                <Btn kind="secondary" size="sm" icon={<Download size={13} />}>Copy URL</Btn>
                <Btn kind="ghost" size="sm" icon={<Eye size={13} />}>Open</Btn>
              </div>
            </Card>
          </div>
        </div>
        <aside className="flex flex-col gap-3.5">
          <Card className="p-4">
            <div className="text-[12.5px] font-semibold mb-2.5">Reporting cadence</div>
            <div className="flex flex-col gap-2">
              {[
                ["Monthly programme", "Auto · 1st of month", true],
                ["Quarterly donor", "Manual sign-off", true],
                ["Verra MRV bundle", "Annual", false],
                ["BRGM ministerial", "Quarterly", true],
              ].map(([n, m, on]) => (
                <div key={n as string} className="flex items-center gap-2.5 py-2 text-[12.5px] border-b border-pg-border">
                  <FileIcon size={16} className="text-pg-ink-muted" />
                  <div className="flex-1">
                    <div className="font-medium">{n}</div>
                    <div className="text-[11px] text-pg-ink-muted">{m}</div>
                  </div>
                  <Chip size="sm" tone={on ? "success" : "neutral"}>{on ? "On" : "Off"}</Chip>
                </div>
              ))}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-[12.5px] font-semibold mb-2.5">Recent exports</div>
            {[
              ["BRGM_CLK_2026-04.pdf", "2.4 MB · 12 May"],
              ["Verra_MRV_2026Q1.zip", "18.1 MB · 04 May"],
              ["Public_2026-04.html", "220 KB · 02 May"],
            ].map(([n, m]) => (
              <div key={n} className="flex items-center gap-2.5 py-1.5 text-xs">
                <FileIcon size={15} className="text-pg-ink-muted" />
                <div className="flex-1 min-w-0">
                  <div className="font-mono truncate">{n}</div>
                  <div className="text-[11px] text-pg-ink-muted">{m}</div>
                </div>
                <Download size={15} className="text-pg-ink-muted cursor-pointer" />
              </div>
            ))}
          </Card>
        </aside>
      </div>
    </WebShell>
  );
}

function ChartStub() {
  const pts = [10, 12, 18, 22, 30, 42, 55, 68, 84, 96, 108, 142];
  const max = Math.max(...pts);
  const path = pts.map((v, i) => `${i === 0 ? "M" : "L"} ${(i / (pts.length - 1)) * 100} ${100 - (v / max) * 92}`).join(" ");
  const area = path + " L 100 100 L 0 100 Z";
  return (
    <div className="relative h-[220px] pb-5.5">
      <svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="cg" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgba(31,77,58,0.3)" />
            <stop offset="100%" stopColor="rgba(31,77,58,0)" />
          </linearGradient>
        </defs>
        {[20, 40, 60, 80].map((y) => (
          <line key={y} x1="0" x2="100" y1={y} y2={y} stroke="rgba(20,20,15,0.06)" strokeWidth="0.3" />
        ))}
        <path d={area} fill="url(#cg)" />
        <path d={path} fill="none" stroke="#1f4d3a" strokeWidth="0.7" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="absolute bottom-0 left-0 right-0 flex justify-between text-[10px] text-pg-ink-muted font-mono">
        {["May", "Jul", "Sep", "Nov", "Jan", "Mar", "Apr"].map((m) => <span key={m}>{m}</span>)}
      </div>
    </div>
  );
}
