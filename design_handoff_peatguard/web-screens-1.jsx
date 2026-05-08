// PeatGuard — 9 web operator dashboard screens.
// All screens render at 1440×900 inside DCArtboard cards.

const W = 1440, H = 900;

// ───────────────────────── Shared chrome ─────────────────────────
function WebShell({ active = 'home', children, headerRight, title, subtitle, dense }) {
  const items = [
    { id: 'home', label: 'AOI Dashboard', icon: 'home' },
    { id: 'map', label: 'Map view', icon: 'map' },
    { id: 'tasks', label: 'Tasks', icon: 'list' },
    { id: 'validate', label: 'Validation', icon: 'check' },
    { id: 'pay', label: 'Payments', icon: 'wallet' },
    { id: 'workers', label: 'Workers', icon: 'users' },
    { id: 'reports', label: 'Reports', icon: 'chart' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ];
  return (
    <div className="pg-scope" style={{ width: W, height: H, display: 'grid', gridTemplateColumns: '232px 1fr', background: 'var(--pg-surface)', overflow: 'hidden' }}>
      <aside style={{ background: 'var(--pg-surface-raised)', borderRight: '1px solid var(--pg-border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px 18px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <Logomark/>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: 14.5, fontWeight: 700, letterSpacing: -0.01, color: 'var(--pg-ink)' }}>PeatGuard</span>
            <span style={{ fontSize: 11, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>v4.2.1</span>
          </div>
        </div>
        <WorkspacePicker/>
        <nav style={{ padding: '10px 10px', display: 'flex', flexDirection: 'column', gap: 1 }}>
          {items.map(it => (
            <a key={it.id} href={`#${it.id}`} style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 8,
              fontSize: 13.5, fontWeight: it.id === active ? 600 : 500, textDecoration: 'none',
              color: it.id === active ? 'var(--pg-primary)' : 'var(--pg-ink-secondary)',
              background: it.id === active ? 'var(--pg-primary-soft)' : 'transparent',
            }}>
              <Icon name={it.icon} size={17}/>
              <span>{it.label}</span>
              {it.id === 'validate' && <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 600, background: 'var(--pg-risk)', color: '#fff', padding: '2px 6px', borderRadius: 99 }}>14</span>}
              {it.id === 'pay' && <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 600, background: 'var(--pg-gold-soft)', color: '#7a5400', padding: '2px 6px', borderRadius: 99 }}>32</span>}
            </a>
          ))}
        </nav>
        <div style={{ marginTop: 'auto', padding: 14, borderTop: '1px solid var(--pg-border)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 16, background: 'linear-gradient(135deg,#3d2818,#57a773)', color: '#fff', display: 'grid', placeItems: 'center', fontSize: 12, fontWeight: 700 }}>NA</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--pg-ink)' }}>Nadia Arifin</div>
            <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)' }}>PeatGuard · Analyst</div>
          </div>
          <Icon name="chevDown" size={14} style={{ color: 'var(--pg-ink-muted)' }}/>
        </div>
      </aside>
      <main style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {(title || headerRight) && (
          <header style={{ padding: dense ? '14px 28px' : '20px 28px 18px', borderBottom: '1px solid var(--pg-border)', display: 'flex', alignItems: 'center', gap: 16, background: 'var(--pg-surface-raised)' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              {subtitle && <div style={{ fontSize: 12, color: 'var(--pg-ink-muted)', fontWeight: 500, marginBottom: 3 }}>{subtitle}</div>}
              {title && <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: -0.02, color: 'var(--pg-ink)' }}>{title}</h1>}
            </div>
            {headerRight}
          </header>
        )}
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>{children}</div>
      </main>
    </div>
  );
}

function Logomark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32">
      <rect width="32" height="32" rx="8" fill="var(--pg-primary)"/>
      <path d="M8 22c0-4 3-7 6-7 4 0 4 4 8 4 2 0 4-1 4-1v6H8z" fill="var(--pg-accent)"/>
      <circle cx="22" cy="11" r="2.5" fill="var(--pg-gold)"/>
      <path d="M8 22c0-4 3-7 6-7 4 0 4 4 8 4 2 0 4-1 4-1" stroke="rgba(255,255,255,0.4)" strokeWidth="0.6" fill="none"/>
    </svg>
  );
}

function WorkspacePicker({ open }) {
  return (
    <div style={{ margin: '4px 12px 8px', padding: '10px 12px', border: '1px solid var(--pg-border)', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', background: 'var(--pg-surface-sunken)' }}>
      <div style={{ width: 24, height: 24, borderRadius: 5, background: 'var(--pg-primary)', color: '#fff', display: 'grid', placeItems: 'center', fontSize: 11, fontWeight: 700 }}>PG</div>
      <div style={{ flex: 1, minWidth: 0, lineHeight: 1.25 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--pg-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>PeatGuard · Kalimantan ops</div>
        <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)' }}>Switch programme</div>
      </div>
      <Icon name="chevDown" size={14} style={{ color: 'var(--pg-ink-muted)' }}/>
    </div>
  );
}

// ───────────────────────── 1. Login ─────────────────────────
function W1_Login() {
  return (
    <div className="pg-scope" style={{ width: W, height: H, display: 'grid', gridTemplateColumns: '1fr 1fr', background: 'var(--pg-surface)', overflow: 'hidden' }}>
      <div style={{ position: 'relative', overflow: 'hidden' }}>
        <MapStub layer="canal_risk · Sebangau, Central Kalimantan" bg="assets/aoi-satellite.png" overlay="assets/aoi-classified.png" overlayOpacity={0.55} full style={{ height: '100%' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg, rgba(31,77,58,0.85), rgba(61,40,24,0.55))' }}/>
          <div style={{ position: 'absolute', left: 56, top: 56, color: '#fff', display: 'flex', alignItems: 'center', gap: 12 }}>
            <Logomark size={36}/>
            <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: -0.01 }}>PeatGuard</span>
          </div>
          <div style={{ position: 'absolute', left: 56, bottom: 56, right: 56, color: '#fff' }}>
            <div style={{ fontSize: 12, fontFamily: 'var(--pg-font-mono)', opacity: 0.75, marginBottom: 14, letterSpacing: 0.05, textTransform: 'uppercase' }}>Indonesia · Kalimantan · Sumatra</div>
            <h1 style={{ fontSize: 38, fontWeight: 600, letterSpacing: -0.025, lineHeight: 1.1, maxWidth: 420 }}>From satellite radar to canal blocks that actually get built.</h1>
            <p style={{ fontSize: 14, opacity: 0.8, marginTop: 14, maxWidth: 380, lineHeight: 1.5 }}>
              Operator dashboard for restoration agencies, NGOs and forestry desks. Turn priority maps into paid restoration tasks.
            </p>
          </div>
        </MapStub>
      </div>
      <div style={{ display: 'grid', placeItems: 'center', padding: 56 }}>
        <div style={{ width: 380 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--pg-primary)', textTransform: 'uppercase', letterSpacing: 0.06, marginBottom: 12 }}>Sign in</div>
          <h2 style={{ fontSize: 28, fontWeight: 600, letterSpacing: -0.02, marginBottom: 6 }}>Welcome back</h2>
          <p style={{ fontSize: 14, color: 'var(--pg-ink-secondary)', marginBottom: 28 }}>PeatGuard team sign-in. SSO available for partner agencies.</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Input label="Work email" value="tommy.quak@peatguard.id" icon="user"/>
            <Input label="Password" value="••••••••••••" icon="lock" trailing={<Icon name="eye" size={16} style={{ color: 'var(--pg-ink-muted)' }}/>}/>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, marginTop: 4 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 7, color: 'var(--pg-ink-secondary)' }}>
                <span style={{ width: 14, height: 14, borderRadius: 3, background: 'var(--pg-primary)', display: 'grid', placeItems: 'center' }}><Icon name="check" size={10} style={{ color: '#fff' }}/></span>
                Remember this device
              </label>
              <a href="#" style={{ color: 'var(--pg-primary)', fontWeight: 600, textDecoration: 'none' }}>Forgot password?</a>
            </div>
            <Btn kind="primary" size="lg" full style={{ marginTop: 6 }}>Sign in</Btn>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: 10, color: 'var(--pg-ink-muted)', fontSize: 11.5, margin: '6px 0' }}>
              <div style={{ height: 1, background: 'var(--pg-border)' }}/>OR<div style={{ height: 1, background: 'var(--pg-border)' }}/>
            </div>
            <Btn kind="secondary" size="lg" full icon="shield">Partner SSO (BRGM, WWF-ID, KLHK)</Btn>
          </div>
          <div style={{ marginTop: 28, padding: 14, background: 'var(--pg-primary-soft)', borderRadius: 10, fontSize: 12, color: 'var(--pg-primary)', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <Icon name="info" size={16} style={{ flexShrink: 0, marginTop: 1 }}/>
            <span>Your PeatGuard account manages <b>3 partner programmes</b>. Pick one after sign-in.</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Input({ label, value, icon, trailing }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={{ fontSize: 12, color: 'var(--pg-ink-secondary)', fontWeight: 500 }}>{label}</span>
      <div style={{ height: 44, padding: '0 14px', border: '1px solid var(--pg-border-strong)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--pg-surface-raised)' }}>
        {icon && <Icon name={icon} size={16} style={{ color: 'var(--pg-ink-muted)' }}/>}
        <span style={{ flex: 1, fontSize: 14, color: 'var(--pg-ink)' }}>{value}</span>
        {trailing}
      </div>
    </label>
  );
}

// ───────────────────────── 2. AOI Dashboard ─────────────────────────
function W2_Dashboard() {
  const aois = [
    { name: 'Sebangau Block C', code: 'SBG-C', risk: 0.71, critical: 18.4, refresh: '2026-05-04', progress: 34, restored: 412, area: 12_400 },
    { name: 'Mawas East', code: 'MWE-1', risk: 0.58, critical: 11.2, refresh: '2026-05-04', progress: 62, restored: 880, area: 8_900 },
    { name: 'Berbak-Sembilang', code: 'BBS-2', risk: 0.49, critical: 7.8, refresh: '2026-05-03', progress: 22, restored: 240, area: 18_200 },
    { name: 'Padang Sugihan', code: 'PSG-1', risk: 0.66, critical: 14.0, refresh: '2026-05-03', progress: 48, restored: 540, area: 6_700 },
    { name: 'Kampar Peninsula N', code: 'KPN-3', risk: 0.81, critical: 24.1, refresh: '2026-05-02', progress: 11, restored: 90, area: 22_500 },
    { name: 'Sungai Putri', code: 'SGP-1', risk: 0.42, critical: 6.4, refresh: '2026-05-02', progress: 71, restored: 1_120, area: 5_300 },
  ];
  return (
    <WebShell active="home" title="Programme overview" subtitle="PeatGuard ops · Kalimantan · 6 active AOIs"
      headerRight={<div style={{ display: 'flex', gap: 8 }}>
        <Btn kind="ghost" size="md" icon="refresh">Refresh data</Btn>
        <Btn kind="secondary" size="md" icon="download">Export</Btn>
        <Btn kind="primary" size="md" icon="plus">New AOI</Btn>
      </div>}>
      <div style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 20, height: '100%', overflow: 'auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 14 }}>
          <Card pad={16}><Stat label="Hectares monitored" value="74,000" sub="across 6 AOIs"/></Card>
          <Card pad={16}><Stat label="Restored YTD" value="3,282 ha" delta="+8.4%" sub="vs Apr"/></Card>
          <Card pad={16}><Stat label="tCO₂/yr avoided" value="142,180" delta="+11%" sub="last 30 d"/></Card>
          <Card pad={16}><Stat label="Active tasks" value="217" sub="in 14 villages"/></Card>
          <Card pad={16}><Stat label="Pending review" value="14" delta="+4" deltaTone="risk" sub="oldest 36 h"/></Card>
          <Card pad={16}><Stat label="Payouts due wk" value="Rp 38.4 jt" sub="32 villagers"/></Card>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <Chip tone="primary" icon="layers">All AOIs · 6</Chip>
            <Chip tone="risk">2 critical</Chip>
            <Chip tone="warn">3 elevated</Chip>
            <Chip tone="success">1 stable</Chip>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Btn kind="ghost" size="sm" icon="search">Search AOIs</Btn>
            <Btn kind="ghost" size="sm" icon="sliders">Sort: priority</Btn>
            <Btn kind="ghost" size="sm" icon="grid">Grid</Btn>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16 }}>
          {aois.map(a => <AoiTile key={a.code} {...a}/>)}
        </div>
      </div>
    </WebShell>
  );
}

function AoiTile({ name, code, risk, critical, refresh, progress, restored, area }) {
  const tone = risk > 0.7 ? 'risk' : risk > 0.55 ? 'warn' : 'success';
  return (
    <Card pad={0} style={{ overflow: 'hidden' }}>
      <div style={{ height: 132, position: 'relative' }}>
        <MapStub layer={`${code} · canal_risk.tif`} bg="assets/aoi-satellite.png" overlay="assets/aoi-classified.png" overlayOpacity={0.62} style={{ borderRadius: 0, height: '100%' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.35))' }}/>
          <div style={{ position: 'absolute', top: 10, left: 10, display: 'flex', gap: 6 }}>
            <Chip tone={tone} size="sm">Risk {risk.toFixed(2)}</Chip>
          </div>
          <div style={{ position: 'absolute', top: 10, right: 10, fontSize: 10, color: '#fff', fontFamily: 'var(--pg-font-mono)', background: 'rgba(0,0,0,0.45)', padding: '3px 6px', borderRadius: 4 }}>{code}</div>
        </MapStub>
      </div>
      <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div>
          <div style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--pg-ink)', letterSpacing: -0.01 }}>{name}</div>
          <div style={{ fontSize: 11.5, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>{area.toLocaleString()} ha · refresh {refresh}</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, paddingTop: 8, borderTop: '1px dashed var(--pg-border)' }}>
          <Field label="% critical" value={`${critical.toFixed(1)}%`}/>
          <Field label="Restored" value={`${restored} ha`}/>
          <Field label="Progress" value={`${progress}%`}/>
        </div>
        <div style={{ height: 4, background: 'var(--pg-surface-sunken)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${progress}%`, height: '100%', background: 'var(--pg-accent)' }}/>
        </div>
      </div>
    </Card>
  );
}

// ───────────────────────── 3. AOI deep-dive map ─────────────────────────
function W3_MapView() {
  const SEED = [
    { id: 'canal_risk', label: 'Canal risk', file: 'canal_risk.tif', on: true, opacity: 78, swatch: 'risk', conf: true },
    { id: 'subsidence_velocity', label: 'Subsidence velocity', file: 'subsidence_velocity_utm.tif', on: true, opacity: 55, swatch: 'warn' },
    { id: 'subsidence_class', label: 'Subsidence class', file: 'subsidence_class_utm.tif', on: false, opacity: 60, swatch: 'warn' },
    { id: 'canal_mask', label: 'Canal mask', file: 'canal_mask.tif', on: true, opacity: 100, swatch: 'primary' },
    { id: 'canal_distance', label: 'Distance to canal', file: 'canal_distance.tif', on: false, opacity: 60, swatch: 'info' },
    { id: 'water_mask', label: 'Open water', file: 'water_mask.tif', on: false, opacity: 70, swatch: 'info' },
    { id: 'peat_extent', label: 'Peat extent (WRI)', file: 'peat_extent_binary.tif', on: false, opacity: 35, swatch: 'primary' },
    { id: 'vv_basemap', label: 'SAR backscatter (VV dB)', file: 'vv_median_db.tif', on: true, opacity: 100, swatch: 'neutral' },
    { id: 'deforestation', label: 'Hansen forest loss', file: 'deforestation_year.tif', on: false, opacity: 70, swatch: 'risk' },
    { id: 'carbon', label: 'Carbon loss tCO₂/ha/yr', file: 'carbon_loss.tif', on: false, opacity: 70, swatch: 'gold' },
  ];
  const [layers, setLayers] = React.useState(SEED);
  const toggle = (id) => setLayers(ls => ls.map(l => l.id === id ? { ...l, on: !l.on } : l));
  const setOpacity = (id, opacity) => setLayers(ls => ls.map(l => l.id === id ? { ...l, opacity } : l));
  const canalRisk = layers.find(l => l.id === 'canal_risk');
  const showRisk = canalRisk?.on;
  const riskOpacity = (canalRisk?.opacity || 78) / 100;
  return (
    <WebShell active="map" dense title="Sebangau Block C · canal_risk" subtitle="AOI · 12,400 ha · last refresh 2026-05-04 · S1 + InSAR pipeline"
      headerRight={<div style={{ display: 'flex', gap: 8 }}>
        <Btn kind="ghost" size="md" icon="layers">Compare</Btn>
        <Btn kind="secondary" size="md" icon="download">Export view</Btn>
        <Btn kind="primary" size="md" icon="polygon">Create task</Btn>
      </div>}>
      <div style={{ display: 'grid', gridTemplateColumns: '288px 1fr 320px', height: '100%' }}>
        {/* Layer panel */}
        <aside style={{ borderRight: '1px solid var(--pg-border)', background: 'var(--pg-surface-raised)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--pg-border)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon name="layers" size={16} style={{ color: 'var(--pg-ink-secondary)' }}/>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Layers</span>
            <span style={{ fontSize: 11, color: 'var(--pg-ink-muted)', marginLeft: 'auto' }}>11 available</span>
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            {layers.map(l => <LayerRow key={l.id} {...l} onToggle={() => toggle(l.id)} onOpacity={(v) => setOpacity(l.id, v)}/>)}
            <div style={{ padding: '10px 14px', borderTop: '1px solid var(--pg-border)', background: 'var(--pg-surface-sunken)' }}>
              <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', textTransform: 'uppercase', letterSpacing: 0.05, marginBottom: 6, fontWeight: 600 }}>Validation</div>
              <LayerRow id="time_since_clearing" label="Time since clearing" file="time_since_clearing.tif" on={false} opacity={70} swatch="risk"/>
            </div>
          </div>
          <div style={{ padding: 12, borderTop: '1px solid var(--pg-border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', display: 'flex', justifyContent: 'space-between' }}>
              <span>Confidence overlay</span><span style={{ fontFamily: 'var(--pg-font-mono)' }}>velocity-backed</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: 'linear-gradient(90deg, #f5e0a8, #c89b3c, #1f4d3a)' }}/>
            <div style={{ fontSize: 10, color: 'var(--pg-ink-muted)', display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--pg-font-mono)' }}>
              <span>proximity-only</span><span>InSAR-confirmed</span>
            </div>
          </div>
        </aside>
        {/* Map */}
        <div style={{ position: 'relative', overflow: 'hidden' }}>
          <MapStub layer={showRisk ? 'canal_risk · vv_median_db basemap' : 'vv_median_db basemap'} bg="assets/aoi-satellite.png" overlay={showRisk ? 'assets/aoi-classified.png' : null} overlayOpacity={riskOpacity} full style={{ borderRadius: 0 }}>
            {/* hatched confidence */}
            <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
              <defs>
                <pattern id="hatch1" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <line x1="0" y1="0" x2="0" y2="6" stroke="rgba(31,77,58,0.4)" strokeWidth="1.5"/>
                </pattern>
              </defs>
              <rect x="55%" y="20%" width="35%" height="55%" fill="url(#hatch1)" rx="40"/>
            </svg>
            {/* selected pixel marker */}
            <div style={{ position: 'absolute', top: '46%', left: '52%', width: 18, height: 18, border: '2px solid #fff', borderRadius: 9, background: 'var(--pg-risk)', boxShadow: '0 0 0 4px rgba(179,38,30,0.25), 0 2px 6px rgba(0,0,0,0.3)' }}/>
            {/* scale + N */}
            <div style={{ position: 'absolute', bottom: 18, left: 18, display: 'flex', flexDirection: 'column', gap: 8, fontFamily: 'var(--pg-font-mono)', fontSize: 10, color: 'rgba(20,20,15,0.75)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 80, height: 6, border: '1px solid rgba(20,20,15,0.7)', display: 'flex' }}>
                  <div style={{ flex: 1, background: 'rgba(20,20,15,0.7)' }}/><div style={{ flex: 1 }}/><div style={{ flex: 1, background: 'rgba(20,20,15,0.7)' }}/><div style={{ flex: 1 }}/>
                </div>
                <span>2 km</span>
              </div>
            </div>
            <div style={{ position: 'absolute', top: 18, right: 18, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {['plus','x','map','grid'].map(i => <button key={i} style={{ width: 36, height: 36, borderRadius: 8, background: 'var(--pg-surface-raised)', border: '1px solid var(--pg-border-strong)', display: 'grid', placeItems: 'center', cursor: 'pointer' }}><Icon name={i === 'x' ? 'x' : i} size={16}/></button>)}
            </div>
            {/* coords */}
            <div style={{ position: 'absolute', top: 18, left: 18, fontFamily: 'var(--pg-font-mono)', fontSize: 11, color: 'rgba(20,20,15,0.85)', background: 'rgba(255,255,255,0.85)', padding: '6px 10px', borderRadius: 6, border: '1px solid var(--pg-border)' }}>
              −2.342° S, 113.911° E · zoom 13 · EPSG:32749
            </div>
            {/* Time slider */}
            <div style={{ position: 'absolute', left: 18, right: 18, bottom: 18, padding: 12, background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(8px)', borderRadius: 10, border: '1px solid var(--pg-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                <Btn kind="ghost" size="sm" icon="play"/>
                <span style={{ fontFamily: 'var(--pg-font-mono)', color: 'var(--pg-ink-secondary)', minWidth: 84 }}>2024-11 → 2026-05</span>
                <div style={{ flex: 1, position: 'relative', height: 28, display: 'flex', alignItems: 'center' }}>
                  <div style={{ position: 'absolute', inset: '0 0 0 0', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <div style={{ height: 4, borderRadius: 2, background: 'var(--pg-surface-sunken)' }}/>
                    <div style={{ height: 4, borderRadius: 2, background: 'linear-gradient(90deg, var(--pg-primary), var(--pg-risk))', width: '72%', position: 'absolute', top: 12 }}/>
                  </div>
                  {[0,12,24,36,48,60,72,84].map(p => <div key={p} style={{ position: 'absolute', left: `${p}%`, top: 6, width: 1, height: 8, background: 'var(--pg-ink-muted)' }}/>)}
                  <div style={{ position: 'absolute', left: '72%', width: 16, height: 16, borderRadius: 8, background: '#fff', border: '2px solid var(--pg-primary)', boxShadow: '0 1px 4px rgba(0,0,0,0.15)', transform: 'translateX(-50%)' }}/>
                </div>
                <span style={{ fontFamily: 'var(--pg-font-mono)', color: 'var(--pg-ink)', fontWeight: 600, minWidth: 60 }}>2026-04</span>
              </div>
            </div>
          </MapStub>
        </div>
        {/* Inspector */}
        <aside style={{ borderLeft: '1px solid var(--pg-border)', background: 'var(--pg-surface-raised)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--pg-border)' }}>
            <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', textTransform: 'uppercase', letterSpacing: 0.05, fontWeight: 600 }}>Pixel inspector</div>
            <div style={{ fontSize: 13, marginTop: 4, fontFamily: 'var(--pg-font-mono)' }}>−2.3417, 113.9114</div>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 14, overflow: 'auto' }}>
            <Card pad={12}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 12.5, fontWeight: 600 }}>Restoration priority</span>
                <Chip tone="risk" size="sm">Critical</Chip>
              </div>
              <div style={{ fontSize: 32, fontWeight: 600, letterSpacing: -0.02, fontFamily: 'var(--pg-font-mono)' }}>0.81</div>
              <div style={{ marginTop: 8, height: 6, background: 'var(--pg-surface-sunken)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: '81%', height: '100%', background: 'linear-gradient(90deg, var(--pg-accent), var(--pg-warn), var(--pg-risk))' }}/>
              </div>
              <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', marginTop: 4, fontFamily: 'var(--pg-font-mono)' }}>velocity-backed (confidence = 2)</div>
            </Card>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <Field label="Subsidence velocity" value="−18.4 mm/yr" mono/>
              <Field label="Subsidence class" value="5 / 6 (severe)"/>
              <Field label="Distance to canal" value="42 m" mono/>
              <Field label="Peat depth est." value="3.8 m"/>
              <Field label="Hansen loss year" value="2016"/>
              <Field label="Carbon loss" value="22.4 tCO₂/ha/yr" mono/>
              <Field label="VV backscatter" value="−14.2 dB" mono/>
              <Field label="Water mask" value="0 (dry)"/>
            </div>
            <div style={{ borderTop: '1px solid var(--pg-border)', paddingTop: 12 }}>
              <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', textTransform: 'uppercase', letterSpacing: 0.05, fontWeight: 600, marginBottom: 8 }}>Suggested actions</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <Btn kind="primary" size="sm" full icon="polygon">Create canal-block task</Btn>
                <Btn kind="soft" size="sm" full icon="leaf">Queue revegetation plot</Btn>
                <Btn kind="ghost" size="sm" full icon="flag">Flag for review</Btn>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </WebShell>
  );
}

function LayerRow({ label, file, on, opacity, swatch, conf }) {
  return (
    <div style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid var(--pg-surface-sunken)' }}>
      <button style={{ width: 28, height: 16, borderRadius: 8, background: on ? 'var(--pg-primary)' : 'var(--pg-border-strong)', border: 'none', position: 'relative', cursor: 'pointer', flexShrink: 0 }}>
        <div style={{ position: 'absolute', top: 2, left: on ? 14 : 2, width: 12, height: 12, borderRadius: 6, background: '#fff', transition: 'left .15s' }}/>
      </button>
      <div style={{ width: 12, height: 12, borderRadius: 3, background: `var(--pg-${swatch === 'neutral' ? 'border-strong' : swatch})` }}/>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12.5, fontWeight: 500, color: on ? 'var(--pg-ink)' : 'var(--pg-ink-muted)' }}>{label}{conf && <span style={{ marginLeft: 4, color: 'var(--pg-accent)', fontSize: 10 }}>●</span>}</div>
        <div style={{ fontSize: 10.5, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>{file}</div>
      </div>
      <span style={{ fontSize: 11, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)', minWidth: 28, textAlign: 'right' }}>{opacity}%</span>
    </div>
  );
}

Object.assign(window, { WebShell, W1_Login, W2_Dashboard, W3_MapView, AoiTile, Logomark, Input });
