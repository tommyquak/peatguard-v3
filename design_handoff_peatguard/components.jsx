// PeatGuard — shared UI primitives. Imported by web-screens.jsx and
// mobile-screens.jsx. All visual choices come through CSS custom props
// defined in tokens.jsx so palette tweaks reflow live.

// ──────────────────────────────────────────────────────────────────────
// Iconography — small inline strokes. Rounded, never filled illustration.
// 16/20/24px sizes; default stroke 1.6.
// ──────────────────────────────────────────────────────────────────────
function Icon({ name, size = 18, stroke = 1.6, fill = 'none', style }) {
  const paths = {
    map: <><path d="M3 6.5L9 4l6 2.5L21 4v13.5L15 20l-6-2.5L3 20z"/><path d="M9 4v13.5M15 6.5V20"/></>,
    layers: <><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5M3 17l9 5 9-5"/></>,
    shield: <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>,
    coin: <><circle cx="12" cy="12" r="9"/><path d="M9 9.5c0-1.4 1.3-2.5 3-2.5s3 1.1 3 2.5-1.3 2-3 2-3 .8-3 2.5 1.3 2.5 3 2.5 3-1.1 3-2.5M12 5.5v13"/></>,
    home: <><path d="M3 11l9-7 9 7v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><path d="M9 21v-7h6v7"/></>,
    list: <><path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/></>,
    users: <><circle cx="9" cy="8" r="3.5"/><path d="M2.5 21c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5"/><path d="M16 4.5a3.5 3.5 0 010 7M22 21a6.5 6.5 0 00-5-6.3"/></>,
    bell: <><path d="M6 9a6 6 0 0112 0v4l1.5 3h-15L6 13z"/><path d="M10 19a2 2 0 004 0"/></>,
    check: <path d="M4 12l5 5 11-12"/>,
    x: <path d="M5 5l14 14M19 5L5 19"/>,
    chev: <path d="M9 6l6 6-6 6"/>,
    chevDown: <path d="M6 9l6 6 6-6"/>,
    plus: <path d="M12 4v16M4 12h16"/>,
    search: <><circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/></>,
    camera: <><path d="M3 8a2 2 0 012-2h2l2-2h6l2 2h2a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><circle cx="12" cy="13" r="4"/></>,
    pin: <><path d="M12 22s7-7.5 7-13a7 7 0 10-14 0c0 5.5 7 13 7 13z"/><circle cx="12" cy="9" r="2.5"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 13.5c.1-.5.1-1 0-1.5l2-1.5-2-3.4-2.3.8c-.7-.6-1.6-1-2.5-1.3l-.4-2.6h-4l-.4 2.6c-.9.3-1.8.7-2.5 1.3L4.6 7.1l-2 3.4 2 1.5c-.1.5-.1 1 0 1.5l-2 1.5 2 3.4 2.3-.8c.7.6 1.6 1 2.5 1.3l.4 2.6h4l.4-2.6c.9-.3 1.8-.7 2.5-1.3l2.3.8 2-3.4z"/></>,
    upload: <><path d="M12 16V4"/><path d="M6 10l6-6 6 6"/><path d="M4 20h16"/></>,
    download: <><path d="M12 4v12"/><path d="M6 10l6 6 6-6"/><path d="M4 20h16"/></>,
    drop: <path d="M12 3s7 8 7 12a7 7 0 11-14 0c0-4 7-12 7-12z"/>,
    leaf: <><path d="M5 19c8 0 14-6 14-14h-4C9 5 5 11 5 19z"/><path d="M5 19c2-5 5-8 10-10"/></>,
    flame: <path d="M12 3c1 4 5 5 5 10a5 5 0 11-10 0c0-2 1.5-3 2.5-4-1-2 0-4 2.5-6z"/>,
    refresh: <><path d="M3 12a9 9 0 0115-6.7L21 8"/><path d="M21 4v4h-4"/><path d="M21 12a9 9 0 01-15 6.7L3 16"/><path d="M3 20v-4h4"/></>,
    file: <><path d="M14 3H6a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V9z"/><path d="M14 3v6h6"/></>,
    chart: <><path d="M3 3v18h18"/><path d="M7 14l4-4 4 4 5-5"/></>,
    msg: <path d="M21 15a2 2 0 01-2 2H8l-5 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>,
    play: <path d="M6 4l14 8-14 8z"/>,
    pause: <><path d="M8 4v16M16 4v16"/></>,
    mic: <><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8.5v.01"/></>,
    warn: <><path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.01"/></>,
    eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></>,
    eyeOff: <><path d="M3 3l18 18"/><path d="M10.5 6.2A10.6 10.6 0 0112 6c6 0 10 7 10 7a17.3 17.3 0 01-3.6 4.3M6.2 6.2C3.6 8 2 12 2 12s4 7 10 7c1.6 0 3-.4 4.4-1.1"/></>,
    lock: <><rect x="4.5" y="11" width="15" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/></>,
    arrowRight: <path d="M5 12h14M13 6l6 6-6 6"/>,
    pen: <><path d="M4 20l3.5-1 11-11-2.5-2.5-11 11z"/><path d="M14 6.5l3 3"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    folder: <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>,
    flag: <><path d="M5 21V4M5 4h11l-2 4 2 4H5"/></>,
    history: <><path d="M3 12a9 9 0 109-9 9 9 0 00-7 3.5"/><path d="M3 4v4h4M12 7v5l3.5 2"/></>,
    grid: <><rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/></>,
    polygon: <path d="M5 9l7-5 7 5-3 9H8z"/>,
    sliders: <><path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/></>,
    download2: <><path d="M5 20h14M12 4v11M7 10l5 5 5-5"/></>,
    wallet: <><path d="M3 7a2 2 0 012-2h12v4h2a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><circle cx="17" cy="13" r="1"/></>,
    fingerprint: <><path d="M5 12a7 7 0 0114 0v3"/><path d="M8 12a4 4 0 018 0v4M12 12v6"/><path d="M5 17v.5M19 17v.5"/></>,
    handCoin: <><circle cx="14" cy="7" r="3.5"/><path d="M3 18l4-2 6 1 4-3 4 1-6 5-7-1-5 1z"/></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
      strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={style}>
      {paths[name] || <circle cx="12" cy="12" r="3"/>}
    </svg>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Buttons — primary / secondary / ghost / danger. Pill or square.
// ──────────────────────────────────────────────────────────────────────
function Btn({ children, kind = 'primary', size = 'md', icon, iconRight, full, onClick, style }) {
  const sizes = {
    sm: { h: 30, px: 10, fs: 12.5, gap: 6, r: 6 },
    md: { h: 38, px: 14, fs: 13.5, gap: 8, r: 8 },
    lg: { h: 48, px: 18, fs: 15, gap: 10, r: 10 },
  }[size];
  const kinds = {
    primary: { bg: 'var(--pg-primary)', fg: 'var(--pg-primary-fg)', bd: 'var(--pg-primary)' },
    secondary: { bg: 'var(--pg-surface-raised)', fg: 'var(--pg-ink)', bd: 'var(--pg-border-strong)' },
    ghost: { bg: 'transparent', fg: 'var(--pg-ink)', bd: 'transparent' },
    soft: { bg: 'var(--pg-primary-soft)', fg: 'var(--pg-primary)', bd: 'transparent' },
    danger: { bg: 'var(--pg-risk)', fg: '#fff', bd: 'var(--pg-risk)' },
    success: { bg: 'var(--pg-accent)', fg: '#fff', bd: 'var(--pg-accent)' },
    gold: { bg: 'var(--pg-gold)', fg: '#1a1300', bd: 'var(--pg-gold)' },
  }[kind];
  return (
    <button onClick={onClick}
      style={{
        height: sizes.h, padding: `0 ${sizes.px}px`, fontSize: sizes.fs, gap: sizes.gap,
        borderRadius: sizes.r, background: kinds.bg, color: kinds.fg,
        border: `1px solid ${kinds.bd}`, cursor: 'pointer', fontWeight: 600,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: full ? '100%' : undefined, letterSpacing: -0.01, lineHeight: 1,
        transition: 'transform .12s var(--pg-ease), filter .12s', whiteSpace: 'nowrap',
        ...style,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.filter = 'brightness(0.96)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.filter = ''; }}>
      {icon && <Icon name={icon} size={sizes.fs + 2} />}
      {children}
      {iconRight && <Icon name={iconRight} size={sizes.fs + 2} />}
    </button>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Cards / surfaces / chips / status pills
// ──────────────────────────────────────────────────────────────────────
function Card({ children, pad = 16, style, raised, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: raised ? 'var(--pg-surface-raised)' : 'var(--pg-surface-raised)',
      border: '1px solid var(--pg-border)',
      borderRadius: 'var(--pg-r-md)',
      padding: pad,
      cursor: onClick ? 'pointer' : 'default',
      ...style,
    }}>{children}</div>
  );
}

function Chip({ children, tone = 'neutral', size = 'md', icon }) {
  const tones = {
    neutral: { bg: 'var(--pg-surface-sunken)', fg: 'var(--pg-ink-secondary)', dot: 'var(--pg-ink-muted)' },
    primary: { bg: 'var(--pg-primary-soft)', fg: 'var(--pg-primary)', dot: 'var(--pg-primary)' },
    success: { bg: 'var(--pg-accent-soft)', fg: '#2d6e44', dot: 'var(--pg-accent)' },
    risk: { bg: 'var(--pg-risk-soft)', fg: 'var(--pg-risk)', dot: 'var(--pg-risk)' },
    warn: { bg: '#fdf1d8', fg: '#7a4d00', dot: 'var(--pg-warn)' },
    gold: { bg: 'var(--pg-gold-soft)', fg: '#7a5400', dot: 'var(--pg-gold)' },
    info: { bg: '#dde9f1', fg: '#1f5278', dot: 'var(--pg-info)' },
  }[tone];
  const sizing = size === 'sm'
    ? { h: 20, px: 7, fs: 11, gap: 5 }
    : { h: 24, px: 10, fs: 12, gap: 6 };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: sizing.gap,
      height: sizing.h, padding: `0 ${sizing.px}px`, fontSize: sizing.fs,
      background: tones.bg, color: tones.fg, fontWeight: 600,
      borderRadius: 'var(--pg-r-pill)', letterSpacing: -0.01, lineHeight: 1,
      whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: 3, background: tones.dot }} />
      {icon && <Icon name={icon} size={sizing.fs} />}
      {children}
    </span>
  );
}

function Stat({ label, value, sub, delta, deltaTone = 'success' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 11.5, color: 'var(--pg-ink-secondary)', fontWeight: 500, letterSpacing: 0.04, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 600, letterSpacing: -0.02, color: 'var(--pg-ink)', lineHeight: 1 }}>{value}</div>
      {(sub || delta) && (
        <div style={{ fontSize: 12, color: 'var(--pg-ink-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
          {delta && <span style={{ color: deltaTone === 'success' ? 'var(--pg-accent)' : deltaTone === 'risk' ? 'var(--pg-risk)' : 'var(--pg-ink-secondary)', fontWeight: 600 }}>{delta}</span>}
          {sub}
        </div>
      )}
    </div>
  );
}

// Compact label/value used in panels, side rails, photo captions.
function Field({ label, value, mono }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontSize: 11, color: 'var(--pg-ink-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: 0.04 }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--pg-ink)', fontWeight: 500, fontFamily: mono ? 'var(--pg-font-mono)' : undefined }}>{value}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Map placeholder — striped TiTiller-friendly canvas with optional pins
// ──────────────────────────────────────────────────────────────────────
function MapStub({ children, layer = 'canal_risk.tif', tiles, style, full, bg, overlay, overlayOpacity = 0.78, overlayRotate = -8 }) {
  return (
    <div className="pg-tile-canvas pg-raster-stub" data-layer={layer}
      style={{
        width: '100%', height: '100%',
        borderRadius: full ? 0 : 'var(--pg-r-md)',
        position: 'relative', overflow: 'hidden',
        backgroundImage: bg ? `url(${bg})` : undefined,
        backgroundSize: 'cover', backgroundPosition: 'center',
        ...style,
      }}>
      {overlay && (
        <img src={overlay} alt="" style={{
          position: 'absolute', top: '50%', left: '50%',
          width: '128%', height: '128%', objectFit: 'cover',
          transform: `translate(-50%,-50%) rotate(${overlayRotate}deg)`,
          opacity: overlayOpacity,
          filter: 'saturate(1.1) contrast(1.02)',
          pointerEvents: 'none',
        }}/>
      )}
      {/* lat/long graticule */}
      <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, opacity: 0.18 }}>
        <defs>
          <pattern id="grat" x="0" y="0" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M80 0H0v80" fill="none" stroke="rgba(20,20,15,0.6)" strokeWidth="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grat)"/>
      </svg>
      {/* canal traces */}
      <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }} preserveAspectRatio="none" viewBox="0 0 400 300">
        <path d="M0 80 Q80 60 140 90 T260 100 T400 90" stroke="rgba(31,77,58,0.55)" strokeWidth="1.2" fill="none"/>
        <path d="M0 180 Q90 200 160 175 T320 165 T400 180" stroke="rgba(31,77,58,0.55)" strokeWidth="1.2" fill="none"/>
        <path d="M120 0 Q130 70 150 130 T180 300" stroke="rgba(31,77,58,0.45)" strokeWidth="1" fill="none"/>
        <path d="M280 0 Q260 80 270 160 T280 300" stroke="rgba(31,77,58,0.45)" strokeWidth="1" fill="none"/>
      </svg>
      {children}
    </div>
  );
}

Object.assign(window, { Icon, Btn, Card, Chip, Stat, Field, MapStub });
