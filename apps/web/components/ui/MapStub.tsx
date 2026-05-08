"use client";
// Port of design_handoff_peatguard/components.jsx:178-218 (MapStub).
// In v1 we render the bundled satellite + classified overlay PNGs as a
// believable basemap stand-in. When the TiTiler backend is reachable, the
// real raster tiles can be layered on top via <img>/<canvas> children.

import { cn } from "@/lib/cn";

export function MapStub({
  layer = "canal_risk.tif",
  bg = "/aoi-satellite.png",
  overlay = "/aoi-classified.png",
  overlayOpacity = 0.6,
  overlayRotate = -8,
  full,
  className,
  children,
}: {
  layer?: string;
  bg?: string | null;
  overlay?: string | null;
  overlayOpacity?: number;
  overlayRotate?: number;
  full?: boolean;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      data-layer={layer}
      className={cn(
        "pg-tile-canvas pg-raster-stub relative overflow-hidden w-full h-full",
        full ? "rounded-none" : "rounded-md",
        className,
      )}
      style={
        bg
          ? { backgroundImage: `url(${bg})`, backgroundSize: "cover", backgroundPosition: "center" }
          : undefined
      }
    >
      {overlay && (
        <img
          src={overlay}
          alt=""
          className="absolute pointer-events-none"
          style={{
            top: "50%",
            left: "50%",
            width: "128%",
            height: "128%",
            objectFit: "cover",
            transform: `translate(-50%,-50%) rotate(${overlayRotate}deg)`,
            opacity: overlayOpacity,
            filter: "saturate(1.1) contrast(1.02)",
          }}
        />
      )}
      <svg className="absolute inset-0 opacity-20 pointer-events-none" width="100%" height="100%">
        <defs>
          <pattern id="grat" x="0" y="0" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M80 0H0v80" fill="none" stroke="rgba(20,20,15,0.6)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grat)" />
      </svg>
      <svg className="absolute inset-0 pointer-events-none" width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 400 300">
        <path d="M0 80 Q80 60 140 90 T260 100 T400 90" stroke="rgba(31,77,58,0.55)" strokeWidth="1.2" fill="none" />
        <path d="M0 180 Q90 200 160 175 T320 165 T400 180" stroke="rgba(31,77,58,0.55)" strokeWidth="1.2" fill="none" />
        <path d="M120 0 Q130 70 150 130 T180 300" stroke="rgba(31,77,58,0.45)" strokeWidth="1" fill="none" />
        <path d="M280 0 Q260 80 270 160 T280 300" stroke="rgba(31,77,58,0.45)" strokeWidth="1" fill="none" />
      </svg>
      {children}
    </div>
  );
}
