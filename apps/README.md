# PeatGuard apps

Implementation of the design handoff in `../design_handoff_peatguard/`. Two apps + the backend that ties them together.

```
apps/
  web/        Next.js 14 operator console (W1-W9)
  mobile/     Expo villager app (M1-M8)
peatguard/peatguard/src/peatguard/api/   FastAPI REST backend
```

## Run the full demo locally

In three terminals:

```bash
# Terminal 1 — backend (FastAPI + TiTiler + SQLite ledger)
cd peatguard/peatguard
pip install -e '.[dashboard]'
peatguard dashboard --port 8080
# health: curl http://localhost:8080/health
# seeded ledger lives at ~/.peatguard/ledger.db

# Terminal 2 — web operator app
cd apps/web
npm install
npm run dev
# open http://localhost:3000

# Terminal 3 — mobile villager app
cd apps/mobile
npm install
npx expo start
# scan QR with Expo Go (Android) or 'i' for iOS simulator / 'a' for Android emulator
```

## Demo path (matches the plan §Verification)

1. Web: sign in (any email/password) → AOI dashboard → click *Sebangau Block C*.
2. Web: *Create task* → publish "Block canal — demo".
3. Mobile: onboard as Sumardi in Hampangen Jaya → the new task appears on the map.
4. Mobile: tap → Accept → Arrive → take 3 photos → Submit.
5. Web: Validation queue → the submission appears with auto-checks → Approve.
6. Web: Payments → check the row → *Release batch*.
7. Mobile: Wallet tab pull-to-refresh → payment shows as paid.

## Architecture

```
operator (web)              villager (mobile)
   |                              |
   | tasks · validation           | accept · arrive ·
   | payments · workers           | photo · submit
   v                              v
        FastAPI /api/v1 (extends dashboard/app.py)
        · SQLite ledger ~/.peatguard/ledger.db
        · TiTiler /cog/* (existing — raster tiles from GCS COGs)
```

Auth in v1 is a stub bearer token (`dev-<email>`); see plan §Out of scope.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `PEATGUARD_API__DB_PATH` | `~/.peatguard/ledger.db` | SQLite ledger location |
| `PEATGUARD_API__BLOB_DIR` | `~/.peatguard/photo_blobs` | Photo blob storage |
| `PEATGUARD_API__CORS_ORIGINS` | localhost dev origins | CORS allowlist |
| `NEXT_PUBLIC_API_BASE` (web) | `http://localhost:8080` | Backend URL the Next.js rewrites proxy to |
| `apiBase` in `app.json` (mobile) | `http://localhost:8080` | Backend URL the Expo client hits |

## Type / build verification

```bash
# backend
cd peatguard/peatguard && python -c "from peatguard.dashboard.app import app; print('ok')"

# web
cd apps/web && npm run typecheck && npm run build

# mobile
cd apps/mobile && npx tsc --noEmit
```
