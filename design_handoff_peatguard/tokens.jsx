// PeatGuard design tokens. Three palette variants ship: forest (default),
// peat-brown (briefed), teal-institutional (alternative). The active palette
// is set on document.documentElement via data-palette and the tokens are
// CSS custom props so any component can read them with var(--pg-…).

const PG_PALETTES = {
  forest: {
    label: 'Forest',
    sub: 'Deep restoration green primary',
    primary: '#1f4d3a',
    primaryHover: '#163829',
    primarySoft: '#e6efeb',
    primaryFg: '#ffffff',
    accent: '#57a773',
    accentSoft: '#e0eddf',
    peat: '#3d2818',
    gold: '#c89b3c',
    goldSoft: '#f5ecd6',
    risk: '#b3261e',
    riskSoft: '#fae8e6',
    warn: '#e08c0c',
    info: '#2c6e9b',
    surface: '#faf8f3',
    surfaceRaised: '#ffffff',
    surfaceSunken: '#f2efe7',
    surfaceInverse: '#1a1f1c',
    ink: '#1a1f1c',
    inkSecondary: '#5a6160',
    inkMuted: '#8a918f',
    border: '#e3e5e0',
    borderStrong: '#c7ccc4',
  },
  peat: {
    label: 'Peat brown',
    sub: 'Deep peat-brown primary as briefed',
    primary: '#3d2818',
    primaryHover: '#2a1a0e',
    primarySoft: '#f0e9e1',
    primaryFg: '#ffffff',
    accent: '#57a773',
    accentSoft: '#e0eddf',
    peat: '#3d2818',
    gold: '#c89b3c',
    goldSoft: '#f5ecd6',
    risk: '#bd0026',
    riskSoft: '#fae3e6',
    warn: '#e08c0c',
    info: '#2c6e9b',
    surface: '#faf6ef',
    surfaceRaised: '#ffffff',
    surfaceSunken: '#f1eadd',
    surfaceInverse: '#1f140b',
    ink: '#1f140b',
    inkSecondary: '#6a5a4b',
    inkMuted: '#9a8d7e',
    border: '#e6dfd1',
    borderStrong: '#c7bba4',
  },
  teal: {
    label: 'Institutional teal',
    sub: 'Bank-Mandiri-adjacent civic chrome',
    primary: '#0a4f5e',
    primaryHover: '#063944',
    primarySoft: '#dceaee',
    primaryFg: '#ffffff',
    accent: '#57a773',
    accentSoft: '#e0eddf',
    peat: '#3d2818',
    gold: '#c89b3c',
    goldSoft: '#f5ecd6',
    risk: '#b3261e',
    riskSoft: '#fae8e6',
    warn: '#e08c0c',
    info: '#2c6e9b',
    surface: '#f7f9f9',
    surfaceRaised: '#ffffff',
    surfaceSunken: '#eef2f3',
    surfaceInverse: '#0a1416',
    ink: '#0a1416',
    inkSecondary: '#48595d',
    inkMuted: '#8295a0',
    border: '#dce4e6',
    borderStrong: '#bbc7cb',
  },
};

const PG_DARK = {
  surface: '#0e1411',
  surfaceRaised: '#161d18',
  surfaceSunken: '#080a09',
  ink: '#f1f3ee',
  inkSecondary: '#a2a8a4',
  inkMuted: '#6c726f',
  border: '#222a25',
  borderStrong: '#3a443d',
  primarySoft: '#0f2419',
  accentSoft: '#0f2419',
  riskSoft: '#2a0d0b',
};

function applyPalette(name, dark) {
  const p = PG_PALETTES[name] || PG_PALETTES.forest;
  const merged = dark ? { ...p, ...PG_DARK } : p;
  const root = document.documentElement;
  for (const [k, v] of Object.entries(merged)) {
    root.style.setProperty('--pg-' + k.replace(/[A-Z]/g, m => '-' + m.toLowerCase()), v);
  }
  root.dataset.palette = name;
  root.dataset.theme = dark ? 'dark' : 'light';
}

// One-time global stylesheet — typography, base reset, utility classes.
if (typeof document !== 'undefined' && !document.getElementById('pg-tokens')) {
  const s = document.createElement('style');
  s.id = 'pg-tokens';
  s.textContent = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --pg-font-sans: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --pg-font-mobile: 'Noto Sans', 'Inter', system-ui, sans-serif;
  --pg-font-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
  --pg-r-sm: 6px;
  --pg-r-md: 10px;
  --pg-r-lg: 16px;
  --pg-r-pill: 999px;
  --pg-shadow-sm: 0 1px 2px rgba(20,20,15,0.04), 0 0 0 1px var(--pg-border);
  --pg-shadow-md: 0 2px 6px rgba(20,20,15,0.06), 0 0 0 1px var(--pg-border);
  --pg-shadow-lg: 0 8px 24px rgba(20,20,15,0.10), 0 1px 2px rgba(20,20,15,0.06);
  --pg-shadow-pop: 0 16px 40px rgba(20,20,15,0.18), 0 2px 4px rgba(20,20,15,0.08);
  --pg-ease: cubic-bezier(.2,.7,.3,1);
}

.pg-scope {
  font-family: var(--pg-font-sans);
  color: var(--pg-ink);
  background: var(--pg-surface);
  font-feature-settings: 'cv11', 'ss01', 'ss03';
  -webkit-font-smoothing: antialiased;
}
.pg-mobile { font-family: var(--pg-font-mobile); }
.pg-mono { font-family: var(--pg-font-mono); font-feature-settings: 'tnum'; }

.pg-scope *, .pg-scope *::before, .pg-scope *::after { box-sizing: border-box; }
.pg-scope button { font: inherit; color: inherit; }
.pg-scope p { margin: 0; }
.pg-scope h1, .pg-scope h2, .pg-scope h3, .pg-scope h4, .pg-scope h5 { margin: 0; font-weight: 600; letter-spacing: -0.01em; }

/* Striped placeholder for raster GeoTIFF previews — TiTiller will fill these */
.pg-raster-stub {
  background-image:
    repeating-linear-gradient(135deg, rgba(31,77,58,0.12) 0 4px, transparent 4px 9px),
    radial-gradient(circle at 30% 40%, rgba(189,0,38,0.18), transparent 50%),
    radial-gradient(circle at 70% 65%, rgba(87,167,115,0.20), transparent 55%),
    linear-gradient(180deg, #d8d3c0, #c5beb0);
  position: relative;
}
.pg-raster-stub::after {
  content: attr(data-layer);
  position: absolute; left: 8px; bottom: 6px;
  font-family: var(--pg-font-mono); font-size: 10px;
  color: rgba(20,20,15,0.65); background: rgba(255,255,255,0.7);
  padding: 2px 6px; border-radius: 3px;
  letter-spacing: -0.01em;
}

/* TiTiller-friendly: real tile URLs go on an img/div positioned inside this container.
   Until then the stub provides a believable basemap-with-canal-risk look. */
.pg-tile-canvas { position: relative; overflow: hidden; }
.pg-tile-canvas > .pg-tile-layer { position: absolute; inset: 0; pointer-events: none; }
`;
  document.head.appendChild(s);
}

Object.assign(window, { PG_PALETTES, applyPalette });
