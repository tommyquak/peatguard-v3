# Handoff: PeatGuard — Operator Web App + Villager Mobile App

## Overview

PeatGuard is a satellite-based peatland restoration system for Indonesia. The product turns radar-derived `canal_risk` rasters into paid restoration tasks, distributes those tasks to rural villagers via a mobile app, and pays them on transparent rails (DANA / OVO / GoPay / BRI / PT Pos) once an operator validates the photo evidence.

This handoff covers the **two paired applications**:

1. **Web Operator Dashboard** — desktop app for NGO staff, BRGM Indonesia officers, district forestry desks, and PeatGuard analysts. Covers 9 screens.
2. **Mobile Villager App** — Android-first, English copy (Bahasa Indonesia is the production target — copy is parallel, swap the `i18n` keys), low-end device, intermittent 3G/4G, offline-first. Covers 8 screens.

Both apps share a single source of truth: a "task" record that flows operator → villager → operator (validation) → payment rail.

---

## About the Design Files

The files in this bundle are **design references created in HTML** — interactive prototypes showing the intended look and behavior. They are **not** production code to copy directly. The task is to **recreate these HTML designs in the target codebase's existing environment** (e.g., Next.js + Tailwind for the web app, React Native or native Android for the mobile app), using its established patterns and libraries. If no codebase exists yet, the recommended stack is:

- **Web operator dashboard** → Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui + MapLibre GL JS for map tiles + react-query for data fetching.
- **Mobile villager app** → React Native (Expo) + TypeScript + react-native-maps with offline tile caching (`react-native-mbtiles` or similar) + react-native-mmkv for offline queue persistence + i18next.

The HTML uses inline-Babel React with ad-hoc JSX in `<script type="text/babel">` blocks — that scaffolding is for prototyping speed, not architecture guidance.

## Fidelity

**High-fidelity (hi-fi).** Real colors, real type, real interactions, polished spacing, full English copy, light + dark variants for mobile screens 2/4/5. Recreate pixel-perfectly using the codebase's existing primitives (replace the bespoke `<Btn>`, `<Card>`, `<Chip>`, `<Stat>`, `<Field>` with shadcn/ui or your equivalent — the look should match the design tokens below).

---

## Files in this bundle

| File | What it is |
|---|---|
| `PeatGuard.html` | Master design canvas — rationale 1-pager + all 17 screens + component library, side-by-side. **Open this first.** |
| `PeatGuard Prototype.html` | Clickable interactive prototype of both flows wired together (mobile state machine + web sidebar nav). The mobile state machine is the contract for backend endpoints. |
| `tokens.jsx` | Three palettes (Forest / Peat / Teal) as CSS custom properties. Convert to Tailwind config or Figma variables. |
| `components.jsx` | Primitives: `Btn`, `Card`, `Chip`, `Stat`, `Field`, `Icon`, `MapStub`, `Logomark`. |
| `web-screens-1.jsx` | Web screens 1–5 (Login, AOI Dashboard, Map Deep-dive, Task creator, Validation queue). |
| `web-screens-2.jsx` | Web screens 6–9 (Payments, Workers, Reports, Settings) + Component library. |
| `mobile-screens.jsx` | All 8 mobile screens. |
| `android-frame.jsx` / `design-canvas.jsx` / `tweaks-panel.jsx` | Frame chrome and canvas-presentation scaffolding — discard for production. |
| `assets/` | `aoi-satellite.png` (Sentinel-2 RGB basemap) + `aoi-classified.png` (canal_risk colormap, GDAL nodata border still present — strip it server-side or via `clip-path: polygon()`). |

---

## Design Tokens

```css
/* Forest palette (default — chosen over the original peat-brown brief; rationale on canvas). */
--pg-primary:        #1f4d3a;   /* deep restoration-forest green */
--pg-primary-soft:   #e3efe7;
--pg-accent:         #57a773;   /* lighter restoration green */
--pg-accent-soft:    #d8ecdf;
--pg-gold:           #c89b3c;   /* paid / available task pin */
--pg-gold-soft:      #f4e8cf;
--pg-info:           #2c6e9b;   /* user GPS, accepted task pin */
--pg-warn:           #c87a3c;
--pg-risk:           #b3261e;   /* high canal risk, anti-fraud flags */
--pg-risk-soft:      #f4d4d2;

--pg-ink:            #1a221d;
--pg-ink-secondary:  #3a443d;
--pg-ink-muted:      #6b7570;
--pg-surface:        #fafbf7;   /* off-white, never #fff (mobile sun glare) */
--pg-surface-raised: #ffffff;
--pg-surface-sunken: #f0f1ec;
--pg-border:         #e2e4dd;
--pg-border-strong:  #c8ccc2;

/* Type */
--pg-font-sans: 'Inter', 'Noto Sans', system-ui, sans-serif;
--pg-font-mono: 'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace;

/* Scale: 11 / 12 / 13 / 14 / 15.5 / 18 / 22 / 26 / 32 px
   Weights: 400 / 500 / 600 / 700 only.
   Mono is reserved for: GPS coords, currency amounts, IDs, timestamps. */

/* Spacing — 4 px base. Used: 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32. */
/* Radii — 6 (chips), 10 (inputs), 12 (cards), 14 (large cards), 22 (avatar small), 24 (hero card bottom), 999 (pills). */
/* Elevation — 0 1px 2px rgba(0,0,0,0.05) (raised), 0 4px 12px rgba(0,0,0,0.10) (sticky banner), 0 -8px 24px rgba(0,0,0,0.18) (bottom sheet). */
```

Two alternate palettes (Peat, Teal) are in `tokens.jsx` — select via the Tweaks panel in the prototype. Default is Forest.

### Task pin / status color semantics

| State | Color token | Meaning |
|---|---|---|
| `available` | `--pg-gold` | Open task, anyone in village can accept |
| `accepted` | `--pg-info` | Worker has claimed it but not submitted |
| `submitted` | `--pg-accent` | Photos uploaded, awaiting operator validation |
| `paid` / `done` | `--pg-ink-muted` | Closed, payment released |
| `rejected` / `flagged` | `--pg-risk` | Anti-fraud flag or operator rejection |

These five states are the entire task lifecycle — any backend schema must round-trip them.

---

## Web App — 9 screens

For each screen, see `web-screens-1.jsx` / `web-screens-2.jsx`. Layout target: 1440 × 900 viewport, breakpoints down to 1024 px supported.

### W1 · Login + workspace switcher
Two-pane: left brand panel (full-bleed forest gradient + PeatGuard logomark + tagline "satellite-driven peat restoration · operator console"), right form column with email / password / "use SSO" button. After auth, modal lists workspaces ("BRGM Central Kalimantan", "WWF-ID Sumatra", "Wetlands International — Riau") with role badge per row.

### W2 · AOI dashboard (default home)
Top: 6 KPI tiles (`hectares monitored`, `hectares restored YTD`, `tCO₂/yr avoided`, `active tasks`, `pending validations`, `payments due this week`). Below: filter bar + grid of AOI tiles. Each tile: 1:1 thumbnail of `canal_risk` colormap, mean risk value, % critical, last-refresh date, restoration-progress bar.

### W3 · AOI deep-dive map view
Three-column: left layer panel (10 toggleable raster layers per the brief table, each with on/off + opacity slider + confidence-overlay flag for `canal_risk`), center full-bleed map (Sentinel-2 basemap + classified `canal_risk.tif` overlay clipped to AOI quad, task pins on top), right inspector panel (click pixel → velocity, risk score, confidence, distance-to-canal, peat depth, deforestation year, suggested action). Bottom strip: time-slider scrubbing monthly snapshots Jan 2023 → present.

### W4 · Task creator
Full-bleed map with a polygon-draw / segment-select tool. Right-side modal slides in: task type (canal block / revegetation / monitoring patrol / fire watch), payout in IDR, required deliverables (photo count, GPS track, timestamp window), assigned village (autocomplete), deadline, optional reference photos. CTA: "Publish to mobile app" → broadcasts to subscribed villagers in that AOI.

### W5 · Validation queue
Table of submissions awaiting review. Each row: villager name + avatar, task type, AOI thumbnail, before/after photo slider, GPS track on inset map, auto-check pills (GPS lock ✓, time-in-window ✓, photo blur score ✓, sha256 chain intact ✓). Three buttons per row: Approve (releases payment), Request Revision (writes a Message thread), Reject (requires reason; appealable for 14 days).

### W6 · Payment dashboard
Header card: pending payouts total + batch-release button. Body: tabs for `pending` / `released` / `disputed`. Each row shows villager, task ID, amount, rail (DANA / OVO / GoPay / BRI / PT Pos cash-out), status, anti-fraud flags. Side panel: this week's disbursement breakdown by rail.

### W7 · Worker management
Searchable list: avatar, name, village, completion rate, total paid (IDR), star rating, role (worker / team lead). Detail drawer: task history, payment history, ratings timeline, message thread. Actions: suspend (with 14-day appeal lane — see pushback #3), promote to team lead, message.

### W8 · Reports & impact
Auto-generated monthly PDF preview. Public shareable transparency view (URL-shareable, no auth). Charts: canal blocks completed, hectares restored, tCO₂/yr avoided, payments disbursed by rail, before/after AOI thumbnails.

### W9 · Programme settings
Three vertical sections: defaults (payout per task type, validation rules, alert recipients), AOI list (add / archive / set Hansen-cohort gradient threshold per AOI), satellite refresh schedule.

---

## Mobile App — 8 screens

For each screen, see `mobile-screens.jsx`. Target: 393 × 852 (Pixel 8a). Android-first; iOS treatment is similar with rounded-corner adjustments. Bottom-of-screen primary CTAs throughout (one-handed reach). All copy in English in this bundle — the production target is Bahasa Indonesia, with English and Dayak Ngaju as alternates.

### M1 · Onboarding
Hero illustration → 4-step checklist: choose language, phone+OTP, pick village (auto-detect via GPS), optional NIK+selfie. Step 4 unlocks higher payouts.

### M2 · Home / Map (light + dark)
Header (avatar + greeting + village + tasks-available count + bell). Map block (280 px tall) with task pins (gold available / blue accepted / green submitted / grey done). Below: "Tasks near you" card list, pull-to-refresh, offline-OK chip.

### M3 · Task detail
Top map (location pin, GPS coordinates). Below: status chip + title + deadline + payout. Cards: "What to do" (numbered steps), "Examples of accepted work" (3 reference photos), "Required deliverables" (4 checks), payment-security reassurance card. Bottom-fixed CTA: "Accept task · Rp 250k".

### M4 · Active task / navigation (light + dark)
Full-bleed map with offline-routed dashed path, user dot, target dot, turn-by-turn banner pinned to top. Bottom sheet: arrived-on-site chip + GPS coordinates + photo-capture prompt + 3 photo slots (BEF / DUR / AFT) + "Take before photo" CTA. Each captured photo is sealed with `(lat, lng, accuracy_m, ts, sha256_of_prev)` — sha256 chain must be reproducible server-side.

### M5 · Submit for review (light + dark)
Header card with task summary. Photo grid (3/3 with timestamps). Auto-checks card with 4 pass/fail rows. Voice note card with waveform + play. Offline-tolerance reassurance banner. Bottom CTAs: "Save draft" + "Submit for review".

### M6 · Earnings
Forest-green hero card: total approved + this-month + pending + "Withdraw to DANA" CTA. Below: task history list with paid / pending status pills.

### M7 · Notifications + messages
Threaded conversation with operator (Nadia avatar). System messages render as centered green pills ("Payment Rp 250,000 released"). Bottom composer: + button, text input ("Type a message…"), mic button (voice notes are first-class).

### M8 · Profile
Avatar + name + village + chips (NIK verified / Team lead / ★ rating). Stats row (tasks done / approval rate / total paid). Settings list (verification, payout accounts, privacy, notifications, language). Sign out.

---

## State Management & Backend Contract

The mobile state machine in `PeatGuard Prototype.html` is the contract for backend endpoints. Four mutations:

```ts
acceptTask(taskId)              → POST /tasks/:id/accept       → returns Task
arriveAtSite(taskId, gps)       → POST /tasks/:id/arrive       → returns Task with arrivedAt timestamp
capturePhoto(taskId, photo)     → POST /tasks/:id/photos       → returns Task with photos[]
submitTask(taskId)              → POST /tasks/:id/submit       → returns Task with status='submitted'
```

Each photo object carries:

```ts
type Photo = {
  phase: 'before' | 'during' | 'after';
  ts: number;                      // ms epoch
  gps: { lat: number; lng: number; acc: number };
  blob: Blob;                      // jpeg, sealed-hash chain
  prevSha256?: string;             // links to previous photo's hash for tamper detection
}
```

Operator-side mutations:

```ts
approveSubmission(taskId)        → triggers payment rail
requestRevision(taskId, note)    → opens Message thread, status stays 'submitted'
rejectSubmission(taskId, reason) → status='rejected', appealable for 14 days
batchReleasePayments(taskIds[])  → fan-out to DANA/OVO/GoPay/BRI/PT-Pos
```

### Data model — 23 raster layers

The web map view consumes GeoTIFFs already produced by the science pipeline. Serve via TiTiler:

| Layer | Type | Tile use |
|---|---|---|
| `canal_risk.tif` | float, 0–1 | Headline overlay (with classified colormap) |
| `canal_risk_confidence.tif` | uint8 (0/1/2) | Hatched overlay over canal_risk |
| `subsidence_velocity_utm.tif` | float, mm/yr | Evidence layer |
| `subsidence_class_utm.tif` | uint8, 1–6 | Stakeholder map |
| `canal_mask.tif` | binary | Task selection geometry |
| `canal_distance.tif` | float, m | Drainage-zone gradient |
| `water_mask.tif` | binary | Excluded from task creation |
| `peat_extent_binary.tif` | binary | Bounds the working area |
| `vv_median_db.tif` | float, dB | SAR backscatter basemap |
| `deforestation_year.tif` | uint16, year | Hansen cohort overlay |
| `carbon_loss.tif` | float, tCO₂/ha/yr | Impact layer |

Mobile app **does not** load these directly — it consumes derived task pins + a small offline MBTiles basemap cached around the user's accepted tasks.

---

## Offline-first behavior (mobile)

Every mobile screen has an offline state. Required behaviors:

1. **Map tiles**: pre-cache 5 km radius around any accepted task. Fall back to OSM tiles cached in MBTiles.
2. **Photo queue**: photos taken offline persist in MMKV / SQLite + filesystem. Auto-upload retries with exponential backoff on connectivity restore.
3. **Submissions**: queue locally with `status='pending_upload'`, surface in UI as "Submitted, awaiting upload" until server ack.
4. **Auth**: short-lived JWT with refresh; if both expire offline, app stays usable in read-only mode for 7 days against last sync.
5. **Voice notes**: record locally as opus, attach to submission payload.

---

## Accessibility

- WCAG AA on web. All interactive targets ≥ 40 × 40 px.
- Mobile must support 200%+ font scaling — every screen tested at 200% with no text clipping.
- One-handed reach: all primary CTAs are bottom-of-screen, ≥ 44 px tall.
- Dark mode: required for screens M2 / M4 / M5; web operator UI is light-only for v1.
- Localisation buffer: layouts must accommodate Bahasa Indonesia strings, which are typically 25–35% longer than English. Test with the longest Bahasa string for each label.
- Voice prompts: optional but supported in M3 (read-task-aloud) and M4 (capture-prompt-aloud).

---

## Three things pushed back from the original brief

(The full one-pager rationale is in `PeatGuard.html` § "Rationale". TL;DR for backend:)

1. **Palette: peat-brown demoted to accent.** Brown chrome on a payments app reads as muddy / clinical. Default primary is `#1f4d3a` deep restoration-forest green; peat-brown lives on the avatar gradient and section headers.
2. **Photo blur auto-rejection is advisory, not blocking.** Surface the blur score as one of four auto-checks; never block submission. Operators decide.
3. **Worker suspension has a 14-day appeal lane.** A one-click suspend action with no recourse erodes trust. The Worker management screen surfaces appeal status.

---

## Implementation order suggestion

1. Tokens → component primitives → MapStub replacement with MapLibre.
2. Web auth + workspace switcher (W1).
3. Web AOI dashboard + deep-dive map (W2 / W3) — biggest engineering load (TiTiler integration).
4. Task creator + validation queue (W4 / W5) — the core operational loop.
5. Mobile shell + offline scaffolding (M1 / M2).
6. Mobile capture + submit flow (M3 / M4 / M5) — the most-used screens.
7. Payments + reports (W6 / W8).
8. Worker management + settings + messages (W7 / W9 / M7).

---

## Brand & assets

PeatGuard logomark is rendered in `components.jsx` as inline SVG (`<Logomark/>`). The "tile" satellite imagery in `assets/` is sample Sentinel-2 RGB; production should pull from the science pipeline's basemap output.

---

Questions about any screen — open the corresponding `.jsx` file alongside `PeatGuard.html` and the implementation should be unambiguous.
