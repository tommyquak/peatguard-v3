// PeatGuard mobile — 8 screens. 393 × 852 (Pixel 8a). Wrapped externally
// in <AndroidFrame/> on the canvas; the screen components emit raw inner
// content. English copy throughout (Bahasa kept for backend i18n keys).

const M_W = 393, M_H = 852 - 86;

function MobBg({ children, dark, style }) {
  return (
    <div className="pg-scope pg-mobile" data-mob-theme={dark ? 'dark' : 'light'}
      style={{ width: M_W, height: M_H + 86, background: dark ? '#0e1411' : 'var(--pg-surface)', color: dark ? '#f1f3ee' : 'var(--pg-ink)', display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative', ...style }}>
      {children}
    </div>
  );
}

function MobHeader({ title, sub, lead = 'menu', trail, dark }) {
  return (
    <header style={{ padding: '14px 16px 10px', display: 'flex', alignItems: 'center', gap: 12, background: dark ? '#161d18' : 'var(--pg-surface-raised)', borderBottom: `1px solid ${dark ? '#222a25' : 'var(--pg-border)'}` }}>
      <button style={{ width: 38, height: 38, borderRadius: 10, background: dark ? '#222a25' : 'var(--pg-surface-sunken)', display: 'grid', placeItems: 'center', border: 'none' }}>
        <Icon name={lead === 'back' ? 'chev' : lead} size={20} style={{ color: dark ? '#f1f3ee' : 'var(--pg-ink)', transform: lead === 'back' ? 'scaleX(-1)' : undefined }}/>
      </button>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15.5, fontWeight: 700, letterSpacing: -0.01 }}>{title}</div>
        {sub && <div style={{ fontSize: 11.5, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)' }}>{sub}</div>}
      </div>
      {trail}
    </header>
  );
}

function MobTabBar({ active = 'home', dark }) {
  const tabs = [
    { id: 'home', i: 'map', l: 'Map' },
    { id: 'tasks', i: 'list', l: 'Tasks' },
    { id: 'wallet', i: 'wallet', l: 'Wallet' },
    { id: 'msg', i: 'msg', l: 'Messages' },
    { id: 'me', i: 'user', l: 'Me' },
  ];
  return (
    <nav style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', borderTop: `1px solid ${dark ? '#222a25' : 'var(--pg-border)'}`, background: dark ? '#161d18' : 'var(--pg-surface-raised)', padding: '6px 4px 8px' }}>
      {tabs.map(t => (
        <button key={t.id} style={{ background: 'transparent', border: 'none', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '8px 4px', color: active === t.id ? 'var(--pg-primary)' : (dark ? '#a2a8a4' : 'var(--pg-ink-muted)') }}>
          <span style={{ width: 56, height: 28, borderRadius: 14, background: active === t.id ? (dark ? 'rgba(87,167,115,0.16)' : 'var(--pg-primary-soft)') : 'transparent', display: 'grid', placeItems: 'center' }}>
            <Icon name={t.i} size={20} stroke={active === t.id ? 2 : 1.6}/>
          </span>
          <span style={{ fontSize: 11, fontWeight: active === t.id ? 700 : 500 }}>{t.l}</span>
        </button>
      ))}
    </nav>
  );
}

// 1. Onboarding
function M1_Onboarding() {
  return (
    <MobBg>
      <div style={{ flex: 1, padding: '32px 24px 24px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
          <Logomark size={32}/>
          <span style={{ fontSize: 17, fontWeight: 700 }}>PeatGuard</span>
        </div>
        <div className="pg-raster-stub" data-layer="welcome · peatland illustration" style={{ width: '100%', aspectRatio: '4/3', borderRadius: 14, marginBottom: 24 }}/>
        <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.02, lineHeight: 1.15 }}>Peat protection work. Transparent pay.</h1>
        <p style={{ fontSize: 14, color: 'var(--pg-ink-secondary)', marginTop: 10, lineHeight: 1.5 }}>Restoration work in your village. Photos prove it. PeatGuard pays you within minutes after the operator approves.</p>
        <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <StepRow n={1} t="Choose language" v="English · Bahasa · Dayak Ngaju" done/>
          <StepRow n={2} t="Phone number & OTP" v="+62 ••• ••• 4218" done/>
          <StepRow n={3} t="Pick your village" v="Hampangen Jaya (auto-detected by GPS)" active/>
          <StepRow n={4} t="ID verification (NIK + selfie)" v="Optional · unlocks higher payouts"/>
        </div>
        <div style={{ marginTop: 'auto', paddingTop: 24, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Btn kind="primary" size="lg" full iconRight="arrowRight">Continue</Btn>
          <Btn kind="ghost" size="md" full>Skip for now</Btn>
        </div>
      </div>
      <MobHomeIndicator/>
    </MobBg>
  );
}

function StepRow({ n, t, v, done, active }) {
  return (
    <div style={{ padding: '12px 14px', borderRadius: 12, background: active ? 'var(--pg-primary-soft)' : 'var(--pg-surface-raised)', border: `1px solid ${active ? 'var(--pg-primary)' : 'var(--pg-border)'}`, display: 'flex', alignItems: 'center', gap: 12 }}>
      <span style={{ width: 28, height: 28, borderRadius: 14, background: done ? 'var(--pg-accent)' : active ? 'var(--pg-primary)' : 'var(--pg-surface-sunken)', color: (done || active) ? '#fff' : 'var(--pg-ink-muted)', display: 'grid', placeItems: 'center', fontSize: 12, fontWeight: 700 }}>{done ? <Icon name="check" size={14}/> : n}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13.5, fontWeight: 600 }}>{t}</div>
        <div style={{ fontSize: 11.5, color: 'var(--pg-ink-muted)' }}>{v}</div>
      </div>
      {done && <Icon name="check" size={16} style={{ color: 'var(--pg-accent)' }}/>}
      {active && <Icon name="chev" size={16} style={{ color: 'var(--pg-primary)' }}/>}
    </div>
  );
}

function MobHomeIndicator() {
  return <div style={{ height: 24, display: 'grid', placeItems: 'center' }}><div style={{ width: 130, height: 4, borderRadius: 2, background: 'rgba(20,20,15,0.4)' }}/></div>;
}

// 2. Home / Map (light + dark)
function M2_Home({ dark }) {
  const tasks = [
    { i: 1, status: 'gold', title: 'Block canal · 1.2 km', sub: '0.42 ha · needs 3 photos + GPS', amt: 250_000, dist: '1.2 km', deadline: 'May 14' },
    { i: 2, status: 'gold', title: 'Replant plot 12', sub: '1 ha · seedlings provided', amt: 180_000, dist: '2.4 km', deadline: 'May 20' },
    { i: 3, status: 'blue', title: 'Fire patrol · sector B', sub: 'Afternoon shift 2pm–8pm', amt: 150_000, dist: '0.8 km', deadline: 'Today' },
  ];
  return (
    <MobBg dark={dark}>
      <header style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, background: dark ? '#161d18' : 'var(--pg-surface-raised)', borderBottom: `1px solid ${dark ? '#222a25' : 'var(--pg-border)'}` }}>
        <div style={{ width: 38, height: 38, borderRadius: 19, background: 'linear-gradient(135deg,#3d2818,#c89b3c)', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: 13 }}>SB</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>Good morning, Sumardi</div>
          <div style={{ fontSize: 11.5, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)' }}>Hampangen Jaya · 3 tasks available</div>
        </div>
        <button style={{ width: 38, height: 38, borderRadius: 10, background: dark ? '#222a25' : 'var(--pg-surface-sunken)', border: 'none', position: 'relative' }}>
          <Icon name="bell" size={18}/>
          <span style={{ position: 'absolute', top: 6, right: 6, width: 8, height: 8, borderRadius: 4, background: 'var(--pg-risk)', border: '2px solid currentColor', color: dark ? '#161d18' : '#fff' }}/>
        </button>
      </header>
      <div style={{ height: 280, position: 'relative' }}>
        <MapStub layer="tasks · offline tiles" full style={{ borderRadius: 0, height: '100%' }}>
          {dark && <div style={{ position: 'absolute', inset: 0, background: 'rgba(8,12,10,0.55)' }}/>}
          <div style={{ position: 'absolute', top: '54%', left: '40%', width: 18, height: 18, borderRadius: 9, background: 'var(--pg-info)', border: '3px solid #fff', boxShadow: '0 0 0 6px rgba(44,110,155,0.2)' }}/>
          <Pin x={62} y={24} tone="gold" amt="Rp 250k"/>
          <Pin x={28} y={36} tone="gold" amt="Rp 180k"/>
          <Pin x={50} y={68} tone="info" amt="Patrol"/>
          <Pin x={78} y={56} tone="success" amt="Done"/>
          <div style={{ position: 'absolute', top: 12, left: 12, right: 12, display: 'flex', gap: 6 }}>
            <Chip size="sm" tone="gold">3 available</Chip>
            <Chip size="sm" tone="info">1 active</Chip>
            <div style={{ marginLeft: 'auto', padding: '4px 8px', background: 'rgba(255,255,255,0.9)', borderRadius: 6, fontSize: 11, fontWeight: 600, color: 'var(--pg-ink)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 3, background: 'var(--pg-accent)' }}/>Offline OK
            </div>
          </div>
        </MapStub>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 14px', background: dark ? '#0e1411' : 'var(--pg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <span style={{ fontSize: 14, fontWeight: 700 }}>Tasks near you</span>
          <span style={{ fontSize: 12, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)' }}>Pull to refresh</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {tasks.map(t => <TaskCard key={t.i} {...t} dark={dark}/>)}
        </div>
      </div>
      <MobTabBar active="home" dark={dark}/>
      <MobHomeIndicator/>
    </MobBg>
  );
}

function Pin({ x, y, tone, amt }) {
  const colors = { gold: 'var(--pg-gold)', info: 'var(--pg-info)', success: 'var(--pg-accent)', risk: 'var(--pg-risk)' };
  return (
    <div style={{ position: 'absolute', left: `${x}%`, top: `${y}%`, transform: 'translate(-50%,-100%)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div style={{ padding: '3px 8px', background: colors[tone], color: '#fff', borderRadius: 999, fontSize: 11, fontWeight: 700, boxShadow: '0 2px 6px rgba(0,0,0,0.25)', whiteSpace: 'nowrap' }}>{amt}</div>
      <div style={{ width: 0, height: 0, borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderTop: `7px solid ${colors[tone]}` }}/>
    </div>
  );
}

function TaskCard({ status, title, sub, amt, dist, deadline, dark }) {
  const tones = { gold: ['var(--pg-gold)', 'Available'], blue: ['var(--pg-info)', 'Accepted'], green: ['var(--pg-accent)', 'Submitted'], grey: ['var(--pg-ink-muted)', 'Done'] };
  const [c, l] = tones[status];
  return (
    <div style={{ padding: 14, background: dark ? '#161d18' : 'var(--pg-surface-raised)', border: `1px solid ${dark ? '#222a25' : 'var(--pg-border)'}`, borderRadius: 14, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
      <div style={{ width: 44, height: 44, borderRadius: 22, background: dark ? 'rgba(200,155,60,0.16)' : 'var(--pg-gold-soft)', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
        <Icon name="shield" size={22} style={{ color: c }}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10.5, fontWeight: 700, color: c, textTransform: 'uppercase', letterSpacing: 0.05 }}>
            <span style={{ width: 6, height: 6, borderRadius: 3, background: c }}/>{l}
          </span>
          <span style={{ fontSize: 11, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)' }}>· {dist} · {deadline}</span>
        </div>
        <div style={{ fontSize: 14.5, fontWeight: 700 }}>{title}</div>
        <div style={{ fontSize: 12, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)', marginTop: 2 }}>{sub}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--pg-font-mono)' }}>Rp {amt.toLocaleString('id-ID')}</div>
        <Icon name="chev" size={16} style={{ color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)', marginTop: 4 }}/>
      </div>
    </div>
  );
}

// 3. Task detail
function M3_TaskDetail() {
  return (
    <MobBg>
      <MobHeader title="Block canal C-04" sub="Sebangau · 1.2 km away" lead="back" trail={<Btn kind="ghost" size="sm" icon="info"/>} />
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ height: 200, position: 'relative' }}>
          <MapStub layer="task location · offline" full style={{ borderRadius: 0, height: '100%' }}>
            <Pin x={50} y={45} tone="gold" amt="Rp 250k"/>
            <div style={{ position: 'absolute', top: 10, right: 10, padding: '4px 8px', background: 'rgba(255,255,255,0.9)', borderRadius: 6, fontSize: 10.5, fontFamily: 'var(--pg-font-mono)' }}>
              -2.341°S · 113.91°E
            </div>
          </MapStub>
        </div>
        <div style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 10 }}>
            <div>
              <Chip tone="gold" size="sm">Available</Chip>
              <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.02, marginTop: 8 }}>Block canal at C-04 mouth</h1>
              <div style={{ fontSize: 12, color: 'var(--pg-ink-muted)', marginTop: 2 }}>Deadline: May 18 · 5pm WIB</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Pay</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--pg-font-mono)' }}>Rp 250k</div>
            </div>
          </div>

          <Card pad={14}>
            <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 8 }}>What to do</div>
            <ol style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.55, color: 'var(--pg-ink)' }}>
              <li>Bring dam materials (sandbags, timber) to the canal point.</li>
              <li>Build the dam across the canal mouth, at least 8 m wide.</li>
              <li>Wait until water rises on the upstream side (≈ 2 hours).</li>
              <li>Take photos: before, during, and after.</li>
            </ol>
          </Card>

          <Card pad={0} style={{ overflow: 'hidden' }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--pg-border)', fontSize: 12.5, fontWeight: 700 }}>Examples of accepted work</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 1, background: 'var(--pg-border)' }}>
              {['example_1','example_2','example_3'].map(p => <div key={p} className="pg-raster-stub" data-layer={p} style={{ aspectRatio: '1' }}/>)}
            </div>
          </Card>

          <Card pad={14}>
            <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 10 }}>Required deliverables</div>
            {['3 photos: before, during, after','GPS track of dam (≥ 8 m)','Work between 6am–5pm WIB','Voice note (optional)'].map(d => (
              <div key={d} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', fontSize: 13 }}>
                <span style={{ width: 18, height: 18, borderRadius: 9, background: 'var(--pg-accent-soft)', color: 'var(--pg-accent)', display: 'grid', placeItems: 'center' }}><Icon name="check" size={11} stroke={2.5}/></span>
                {d}
              </div>
            ))}
          </Card>

          <div style={{ padding: 12, background: 'var(--pg-primary-soft)', borderRadius: 10, fontSize: 12, color: 'var(--pg-primary)', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <Icon name="shield" size={16} style={{ flexShrink: 0, marginTop: 1 }}/>
            <div><b>Payment is secured.</b> Once the operator approves your photos, money lands in your DANA wallet in ≈ 1 minute.</div>
          </div>
        </div>
      </div>
      <div style={{ padding: '12px 16px 8px', background: 'var(--pg-surface-raised)', borderTop: '1px solid var(--pg-border)', display: 'flex', gap: 10 }}>
        <Btn kind="secondary" size="lg" icon="msg">Ask</Btn>
        <Btn kind="primary" size="lg" full icon="check">Accept task · Rp 250k</Btn>
      </div>
      <MobHomeIndicator/>
    </MobBg>
  );
}

// 4. Active task / navigation (light + dark)
function M4_ActiveTask({ dark }) {
  return (
    <MobBg dark={dark}>
      <MobHeader title="Capture before-photo" sub="Step 2 of 5 · GPS lock 8 m" lead="back" dark={dark}
        trail={<button style={{ width: 38, height: 38, borderRadius: 10, background: dark ? '#222a25' : 'var(--pg-surface-sunken)', border: 'none' }}><Icon name="info" size={18}/></button>}/>
      <div style={{ position: 'relative', flex: 1, overflow: 'hidden' }}>
        <MapStub layer="navigation · offline" full style={{ borderRadius: 0, height: '100%' }}>
          {dark && <div style={{ position: 'absolute', inset: 0, background: 'rgba(8,12,10,0.65)' }}/>}
          <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
            <path d="M 60 480 Q 140 380 200 320 T 340 180" stroke={dark ? '#83d5c6' : 'var(--pg-primary)'} strokeWidth="4" strokeDasharray="8 6" fill="none" strokeLinecap="round"/>
          </svg>
          <div style={{ position: 'absolute', top: '36%', left: '78%', width: 18, height: 18, borderRadius: 9, background: 'var(--pg-risk)', border: '3px solid #fff', boxShadow: '0 0 0 6px rgba(179,38,30,0.25)' }}/>
          <div style={{ position: 'absolute', top: '72%', left: '14%', width: 18, height: 18, borderRadius: 9, background: 'var(--pg-info)', border: '3px solid #fff' }}/>
          <div style={{ position: 'absolute', top: 12, left: 12, right: 12, padding: '12px 14px', background: dark ? '#1f4d3a' : 'var(--pg-primary)', color: '#fff', borderRadius: 14, display: 'flex', alignItems: 'center', gap: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.25)' }}>
            <Icon name="arrowRight" size={26}/>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Continue 240 m</div>
              <div style={{ fontSize: 12, opacity: 0.85 }}>then turn right onto canal track</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--pg-font-mono)' }}>0.6 km</div>
              <div style={{ fontSize: 10, opacity: 0.85 }}>≈ 9 min</div>
            </div>
          </div>
        </MapStub>

        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, background: dark ? '#161d18' : 'var(--pg-surface-raised)', borderRadius: '20px 20px 0 0', boxShadow: '0 -8px 24px rgba(0,0,0,0.18)', padding: 16 }}>
          <div style={{ width: 40, height: 4, borderRadius: 2, background: dark ? '#3a443d' : 'var(--pg-border-strong)', margin: '0 auto 14px' }}/>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <Chip tone="success" size="sm">Arrived on site</Chip>
            <span style={{ fontSize: 11, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>−2.341°S 113.91°E · ±8m</span>
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>Take a "before" photo facing the canal</div>
          <p style={{ fontSize: 12.5, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)', lineHeight: 1.5 }}>Stand at the canal mouth, point the camera at the water flow. Both banks should be visible.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 12 }}>
            {[1,2,3].map(i => (
              <div key={i} className={i === 1 ? 'pg-raster-stub' : ''} data-layer={i === 1 ? 'before_capture' : ''}
                style={{ aspectRatio: '1', borderRadius: 10, background: i === 1 ? undefined : (dark ? '#222a25' : 'var(--pg-surface-sunken)'), display: 'grid', placeItems: 'center', border: i === 1 ? '2px solid var(--pg-accent)' : `2px dashed ${dark ? '#3a443d' : 'var(--pg-border-strong)'}`, position: 'relative' }}>
                {i !== 1 && <Icon name="camera" size={20} style={{ color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)' }}/>}
                <div style={{ position: 'absolute', bottom: 4, left: 4, fontSize: 9, fontFamily: 'var(--pg-font-mono)', color: '#fff', background: 'rgba(0,0,0,0.5)', padding: '1px 4px', borderRadius: 3 }}>{['BEF','DUR','AFT'][i-1]}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
            <Btn kind="secondary" size="lg" icon="mic">Voice note</Btn>
            <Btn kind="primary" size="lg" full icon="camera">Take before photo</Btn>
          </div>
        </div>
      </div>
      <MobHomeIndicator/>
    </MobBg>
  );
}

// 5. Submit for review (light + dark)
function M5_Submit({ dark }) {
  return (
    <MobBg dark={dark}>
      <MobHeader title="Submit for review" sub="Check before sending" lead="back" dark={dark}/>
      <div style={{ flex: 1, overflow: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Card pad={14} style={{ background: dark ? '#161d18' : undefined, borderColor: dark ? '#222a25' : undefined }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--pg-accent-soft)', color: 'var(--pg-accent)', display: 'grid', placeItems: 'center' }}><Icon name="shield" size={18}/></span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Block canal C-04</div>
              <div style={{ fontSize: 12, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)' }}>Pay <b style={{ color: dark ? '#f1f3ee' : 'var(--pg-ink)', fontFamily: 'var(--pg-font-mono)' }}>Rp 250,000</b> · Sebangau C</div>
            </div>
            <Chip tone="success" size="sm">Ready</Chip>
          </div>
        </Card>

        <div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Photos (3/3)</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
            {['before 06:42','during 09:18','after 11:53'].map((p,i) => (
              <div key={p} style={{ position: 'relative' }}>
                <div className="pg-raster-stub" data-layer={`P-0${i+1}`} style={{ aspectRatio: '1', borderRadius: 10 }}/>
                <div style={{ position: 'absolute', bottom: 4, left: 4, right: 4, fontSize: 10, fontFamily: 'var(--pg-font-mono)', color: '#fff', background: 'rgba(0,0,0,0.55)', padding: '2px 4px', borderRadius: 4, textAlign: 'center' }}>{p}</div>
              </div>
            ))}
          </div>
        </div>

        <Card pad={14} style={{ background: dark ? '#161d18' : undefined, borderColor: dark ? '#222a25' : undefined }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 10 }}>Auto-checks</div>
          {[
            ['GPS lock', '8.4 m mean offset', true],
            ['Within work window', '06:42 → 11:53 WIB', true],
            ['Photos sealed (sha256)', 'chain intact, 3 photos', true],
            ['Dam track', '24.1 m linear', true],
          ].map(([l,v]) => (
            <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', fontSize: 12.5 }}>
              <span style={{ width: 18, height: 18, borderRadius: 9, background: 'var(--pg-accent-soft)', color: 'var(--pg-accent)', display: 'grid', placeItems: 'center' }}><Icon name="check" size={11} stroke={2.5}/></span>
              <span style={{ flex: 1 }}>{l}</span>
              <span style={{ fontSize: 11, color: dark ? '#a2a8a4' : 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>{v}</span>
            </div>
          ))}
        </Card>

        <Card pad={14} style={{ background: dark ? '#161d18' : undefined, borderColor: dark ? '#222a25' : undefined }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 6 }}>Voice note · 0:24</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button style={{ width: 36, height: 36, borderRadius: 18, background: 'var(--pg-primary)', color: '#fff', border: 'none', display: 'grid', placeItems: 'center' }}><Icon name="play" size={14}/></button>
            <svg width="100%" height="28" style={{ flex: 1 }} viewBox="0 0 200 28" preserveAspectRatio="none">
              {Array.from({length: 36}).map((_,i) => <rect key={i} x={i*5.5} y={14 - (Math.sin(i*0.7)*8 + 6)} width="2.5" height={Math.sin(i*0.7)*16 + 12} fill={dark ? '#83d5c6' : 'var(--pg-primary)'}/>)}
            </svg>
          </div>
        </Card>

        <Card pad={14} style={{ background: dark ? '#0f2419' : 'var(--pg-accent-soft)', border: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <Icon name="info" size={16} style={{ color: 'var(--pg-accent)', marginTop: 2 }}/>
            <div style={{ fontSize: 12.5, color: dark ? '#83d5c6' : '#2d6e44', lineHeight: 1.45 }}>
              <b>No signal?</b> Your submission is saved on this phone and uploads automatically when you're back online.
            </div>
          </div>
        </Card>
      </div>
      <div style={{ padding: '12px 16px 8px', background: dark ? '#161d18' : 'var(--pg-surface-raised)', borderTop: `1px solid ${dark ? '#222a25' : 'var(--pg-border)'}`, display: 'flex', gap: 10 }}>
        <Btn kind="secondary" size="lg">Save draft</Btn>
        <Btn kind="primary" size="lg" full icon="upload">Submit for review</Btn>
      </div>
      <MobHomeIndicator/>
    </MobBg>
  );
}

// 6. Earnings
function M6_Earnings() {
  const items = [
    { d: 'May 12', t: 'Block canal · SBG C-04', amt: 250_000, ok: true },
    { d: 'May 08', t: 'Replant · MWE plot 11', amt: 180_000, ok: true },
    { d: 'May 04', t: 'Fire patrol · sector B', amt: 150_000, ok: true },
    { d: 'May 02', t: 'Block canal · SBG C-02', amt: 250_000, ok: 'pending' },
    { d: 'Apr 28', t: 'Block canal · SBG C-01', amt: 250_000, ok: true },
  ];
  return (
    <MobBg>
      <div style={{ background: 'var(--pg-primary)', color: '#fff', padding: '20px 18px 28px', borderRadius: '0 0 24px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>Your earnings</div>
          <Icon name="history" size={20}/>
        </div>
        <div style={{ fontSize: 12.5, opacity: 0.85 }}>Total approved</div>
        <div style={{ fontSize: 32, fontWeight: 700, fontFamily: 'var(--pg-font-mono)', letterSpacing: -0.02, marginTop: 4 }}>Rp 1,080,000</div>
        <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12 }}>
          <div><div style={{ opacity: 0.75 }}>This month</div><div style={{ fontWeight: 700, fontFamily: 'var(--pg-font-mono)', marginTop: 2 }}>Rp 830,000</div></div>
          <div style={{ width: 1, background: 'rgba(255,255,255,0.18)' }}/>
          <div><div style={{ opacity: 0.75 }}>Pending</div><div style={{ fontWeight: 700, fontFamily: 'var(--pg-font-mono)', marginTop: 2 }}>Rp 250,000</div></div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <Btn kind="gold" size="lg" full icon="download2">Withdraw to DANA</Btn>
          <button style={{ width: 50, height: 48, borderRadius: 10, border: '1px solid rgba(255,255,255,0.3)', background: 'rgba(255,255,255,0.1)', color: '#fff' }}><Icon name="settings" size={18}/></button>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 700 }}>Task history</span>
          <Chip tone="primary" size="sm">5 entries</Chip>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map(it => (
            <div key={it.t} style={{ padding: 12, background: 'var(--pg-surface-raised)', border: '1px solid var(--pg-border)', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ width: 36, height: 36, borderRadius: 18, background: it.ok === true ? 'var(--pg-accent-soft)' : 'var(--pg-gold-soft)', color: it.ok === true ? 'var(--pg-accent)' : 'var(--pg-gold)', display: 'grid', placeItems: 'center' }}>
                <Icon name={it.ok === true ? 'check' : 'clock'} size={16}/>
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{it.t}</div>
                <div style={{ fontSize: 11.5, color: 'var(--pg-ink-muted)' }}>{it.d} · {it.ok === true ? 'paid to DANA · 47s' : 'awaiting operator review'}</div>
              </div>
              <div style={{ fontFamily: 'var(--pg-font-mono)', fontWeight: 700, fontSize: 13 }}>Rp {(it.amt/1000).toFixed(0)}k</div>
            </div>
          ))}
        </div>
      </div>
      <MobTabBar active="wallet"/>
      <MobHomeIndicator/>
    </MobBg>
  );
}

// 7. Notifications + messages
function M7_Messages() {
  return (
    <MobBg>
      <MobHeader title="Messages" sub="Operator · System" lead="back" trail={<button style={{ width: 38, height: 38, borderRadius: 10, background: 'var(--pg-surface-sunken)', border: 'none' }}><Icon name="search" size={18}/></button>}/>
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ padding: '16px 16px 8px', background: 'var(--pg-primary-soft)', borderBottom: '1px solid var(--pg-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: 18, background: 'var(--pg-primary)', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: 12 }}>NA</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Nadia · PeatGuard operator</div>
              <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)' }}>Online · usually replies within an hour</div>
            </div>
          </div>
        </div>
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <DateChip>Today · May 12</DateChip>
          <Bubble side="them" t="Pak Sumardi, the during & after photos look great. The before photo is a bit blurry — can you reshoot it?"/>
          <Bubble side="them" attach="P-01 before · blurry"/>
          <Bubble side="me" t="Sure, I'll head back to the spot and retake it now."/>
          <Bubble side="them" t="Thanks. Once it lands, I'll release payment right away."/>
          <Bubble side="me" t="Here's the new shot ✓"/>
          <Bubble side="me" attach="P-01b before · clear"/>
          <DateChip>System</DateChip>
          <Bubble side="sys" t="Payment Rp 250,000 released. Check your Wallet tab."/>
        </div>
      </div>
      <div style={{ padding: '10px 12px', background: 'var(--pg-surface-raised)', borderTop: '1px solid var(--pg-border)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <button style={{ width: 38, height: 38, borderRadius: 19, background: 'var(--pg-surface-sunken)', border: 'none' }}><Icon name="plus" size={18}/></button>
        <div style={{ flex: 1, height: 38, padding: '0 14px', borderRadius: 19, background: 'var(--pg-surface-sunken)', display: 'flex', alignItems: 'center', fontSize: 13, color: 'var(--pg-ink-muted)' }}>Type a message…</div>
        <button style={{ width: 38, height: 38, borderRadius: 19, background: 'var(--pg-primary)', color: '#fff', border: 'none', display: 'grid', placeItems: 'center' }}><Icon name="mic" size={18}/></button>
      </div>
      <MobHomeIndicator/>
    </MobBg>
  );
}

function DateChip({ children }) {
  return <div style={{ alignSelf: 'center', fontSize: 11, color: 'var(--pg-ink-muted)', padding: '3px 10px', background: 'var(--pg-surface-sunken)', borderRadius: 99, margin: '4px 0' }}>{children}</div>;
}

function Bubble({ side, t, attach }) {
  if (side === 'sys') {
    return <div style={{ alignSelf: 'center', maxWidth: '85%', padding: '10px 14px', background: 'var(--pg-accent-soft)', color: '#2d6e44', borderRadius: 12, fontSize: 12.5, display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="check" size={14}/>{t}</div>;
  }
  const me = side === 'me';
  return (
    <div style={{ alignSelf: me ? 'flex-end' : 'flex-start', maxWidth: '78%', display: 'flex', flexDirection: 'column', gap: 4 }}>
      {attach && <div className="pg-raster-stub" data-layer={attach} style={{ width: 140, aspectRatio: '4/3', borderRadius: 10 }}/>}
      {t && <div style={{ padding: '9px 13px', background: me ? 'var(--pg-primary)' : 'var(--pg-surface-raised)', color: me ? '#fff' : 'var(--pg-ink)', border: me ? 'none' : '1px solid var(--pg-border)', borderRadius: 14, borderBottomRightRadius: me ? 4 : 14, borderBottomLeftRadius: me ? 14 : 4, fontSize: 13, lineHeight: 1.45 }}>{t}</div>}
    </div>
  );
}

// 8. Profile
function M8_Profile() {
  return (
    <MobBg>
      <MobHeader title="My profile" lead="back"/>
      <div style={{ flex: 1, overflow: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '20px 0 14px' }}>
          <div style={{ width: 88, height: 88, borderRadius: 44, background: 'linear-gradient(135deg,#3d2818,#c89b3c)', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: 26 }}>SB</div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 18, fontWeight: 700 }}>Sumardi Budiman</div>
            <div style={{ fontSize: 12, color: 'var(--pg-ink-muted)' }}>Hampangen Jaya · since Feb 2025</div>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
            <Chip tone="success" size="sm" icon="shield">NIK verified</Chip>
            <Chip tone="gold" size="sm">Team lead</Chip>
            <Chip tone="primary" size="sm">★ 4.8</Chip>
          </div>
        </div>
        <Card pad={0} style={{ overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)' }}>
            {[['38','tasks done'],['95%','approval rate'],['8.7M','total paid']].map(([v,l],i) => (
              <div key={l} style={{ padding: 16, textAlign: 'center', borderRight: i < 2 ? '1px solid var(--pg-border)' : 'none' }}>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--pg-font-mono)' }}>{v}</div>
                <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', marginTop: 2 }}>{l}</div>
              </div>
            ))}
          </div>
        </Card>
        <Card pad={0} style={{ overflow: 'hidden' }}>
          {[
            ['fingerprint','Verification & documents','NIK · selfie · KTP'],
            ['wallet','Payout accounts','DANA · BRI · PT Pos'],
            ['lock','Privacy & data','Location history · photos'],
            ['bell','Notifications','Push · SMS · voice'],
            ['msg','Language','English'],
          ].map(([i,l,s]) => (
            <button key={l} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: 14, width: '100%', background: 'transparent', border: 'none', borderBottom: '1px solid var(--pg-border)', textAlign: 'left' }}>
              <span style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--pg-surface-sunken)', display: 'grid', placeItems: 'center', color: 'var(--pg-primary)' }}><Icon name={i} size={18}/></span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600 }}>{l}</div>
                <div style={{ fontSize: 11.5, color: 'var(--pg-ink-muted)' }}>{s}</div>
              </div>
              <Icon name="chev" size={16} style={{ color: 'var(--pg-ink-muted)' }}/>
            </button>
          ))}
        </Card>
        <Btn kind="ghost" size="md" full>Sign out</Btn>
        <div style={{ textAlign: 'center', fontSize: 11, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)', paddingBottom: 8 }}>PeatGuard v4.2.1 · build 2026.05.04</div>
      </div>
      <MobTabBar active="me"/>
      <MobHomeIndicator/>
    </MobBg>
  );
}

Object.assign(window, { M1_Onboarding, M2_Home, M3_TaskDetail, M4_ActiveTask, M5_Submit, M6_Earnings, M7_Messages, M8_Profile });
