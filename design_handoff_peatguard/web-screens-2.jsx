// PeatGuard — web screens 4-9 (task creator, validation, payments, workers, reports, settings)

// ───────────────────────── 4. Task creator ─────────────────────────
function W4_TaskCreator() {
  return (
    <WebShell active="map" dense title="Sebangau Block C · canal_risk" subtitle="Drawing task polygon"
      headerRight={<div style={{ display: 'flex', gap: 8 }}><Btn kind="ghost" size="md">Cancel</Btn><Btn kind="primary" size="md" icon="upload">Publish to mobile app</Btn></div>}>
      <div style={{ position: 'relative', height: '100%', background: 'var(--pg-surface-sunken)' }}>
        <MapStub layer="canal_risk" bg="assets/aoi-satellite.png" overlay="assets/aoi-classified.png" overlayOpacity={0.6} full style={{ borderRadius: 0, height: '100%' }}>
          {/* drawn polygon */}
          <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
            <path d="M 600 200 L 760 220 L 820 320 L 760 420 L 620 410 L 560 320 Z" fill="rgba(31,77,58,0.18)" stroke="var(--pg-primary)" strokeWidth="2" strokeDasharray="6 3"/>
            {[[600,200],[760,220],[820,320],[760,420],[620,410],[560,320]].map(([x,y],i) => (
              <circle key={i} cx={x} cy={y} r="5" fill="#fff" stroke="var(--pg-primary)" strokeWidth="2"/>
            ))}
          </svg>
        </MapStub>
        {/* drawing tools floating left */}
        <div style={{ position: 'absolute', top: 16, left: 16, display: 'flex', gap: 6, padding: 6, background: 'var(--pg-surface-raised)', border: '1px solid var(--pg-border)', borderRadius: 10 }}>
          {['polygon','pin','sliders'].map((i,j) => (
            <button key={i} style={{ width: 36, height: 36, borderRadius: 6, background: j === 0 ? 'var(--pg-primary-soft)' : 'transparent', color: j === 0 ? 'var(--pg-primary)' : 'var(--pg-ink-secondary)', border: 'none', cursor: 'pointer', display: 'grid', placeItems: 'center' }}><Icon name={i} size={18}/></button>
          ))}
          <div style={{ width: 1, background: 'var(--pg-border)', margin: '0 2px' }}/>
          <button style={{ height: 36, padding: '0 12px', borderRadius: 6, background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 12.5, fontWeight: 600, color: 'var(--pg-ink-secondary)' }}>Snap to canal_mask</button>
        </div>
        {/* MODAL */}
        <div style={{ position: 'absolute', top: 24, right: 24, bottom: 24, width: 460, background: 'var(--pg-surface-raised)', borderRadius: 14, boxShadow: 'var(--pg-shadow-pop)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--pg-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 12, color: 'var(--pg-ink-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.05 }}>New task · draft</div>
              <div style={{ fontSize: 16, fontWeight: 600, marginTop: 2 }}>Block canal — Sebangau C-04</div>
            </div>
            <Icon name="x" size={18} style={{ color: 'var(--pg-ink-muted)', cursor: 'pointer' }}/>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div>
              <Label>Task type</Label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 6 }}>
                {[{i:'shield',l:'Canal block',sel:true},{i:'leaf',l:'Revegetation'},{i:'eye',l:'Monitor patrol'},{i:'flame',l:'Fire watch'}].map(t => (
                  <div key={t.l} style={{ padding: '10px 12px', border: `1.5px solid ${t.sel ? 'var(--pg-primary)' : 'var(--pg-border)'}`, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8, background: t.sel ? 'var(--pg-primary-soft)' : 'var(--pg-surface-raised)', cursor: 'pointer' }}>
                    <Icon name={t.i} size={17} style={{ color: t.sel ? 'var(--pg-primary)' : 'var(--pg-ink-secondary)' }}/>
                    <span style={{ fontSize: 13, fontWeight: 600, color: t.sel ? 'var(--pg-primary)' : 'var(--pg-ink)' }}>{t.l}</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <Label>Payout (IDR)</Label>
                <div style={{ marginTop: 6, height: 44, padding: '0 12px', border: '1px solid var(--pg-border-strong)', borderRadius: 8, display: 'flex', alignItems: 'center' }}>
                  <span style={{ fontFamily: 'var(--pg-font-mono)', fontSize: 12, color: 'var(--pg-ink-muted)', marginRight: 6 }}>Rp</span>
                  <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--pg-ink)' }}>250,000</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', marginTop: 4 }}>≈ daily-wage × 1.4 (district)</div>
              </div>
              <div>
                <Label>Deadline</Label>
                <div style={{ marginTop: 6, height: 44, padding: '0 12px', border: '1px solid var(--pg-border-strong)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Icon name="clock" size={15} style={{ color: 'var(--pg-ink-muted)' }}/>
                  <span style={{ fontSize: 14, color: 'var(--pg-ink)' }}>2026-05-18 · 17:00 WIB</span>
                </div>
              </div>
            </div>
            <div>
              <Label>Assigned village</Label>
              <div style={{ marginTop: 6, padding: 12, border: '1px solid var(--pg-border)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 36, height: 36, borderRadius: 7, background: 'var(--pg-primary-soft)', color: 'var(--pg-primary)', display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: 13 }}>HJ</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>Desa Hampangen Jaya</div>
                  <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>1.8 km · 22 verified workers</div>
                </div>
                <Btn kind="ghost" size="sm">Change</Btn>
              </div>
            </div>
            <div>
              <Label>Required deliverables</Label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                {['3 photos: before, mid, after canal block','GPS track of dam edge (≥ 8 m linear)','Timestamp within working window 06:00–17:00 WIB','Voice note: rationale for blockage'].map(d => (
                  <div key={d} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
                    <span style={{ width: 16, height: 16, borderRadius: 4, background: 'var(--pg-primary)', display: 'grid', placeItems: 'center' }}><Icon name="check" size={12} style={{ color: '#fff' }}/></span>
                    {d}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <Label>Reference photos (expected outcome)</Label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8, marginTop: 6 }}>
                {[1,2,3].map(i => <div key={i} className="pg-raster-stub" data-layer={`ref_${i}.jpg`} style={{ aspectRatio: '4/3', borderRadius: 6 }}/>)}
              </div>
            </div>
          </div>
          <div style={{ borderTop: '1px solid var(--pg-border)', padding: 14, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--pg-surface-sunken)' }}>
            <div style={{ fontSize: 11.5, color: 'var(--pg-ink-secondary)', flex: 1 }}>
              <div>Polygon area: <b>0.42 ha</b> · Mean risk <b style={{ fontFamily: 'var(--pg-font-mono)' }}>0.74</b></div>
              <div style={{ marginTop: 2 }}>3 canal segments intersect · 0 water_mask conflicts</div>
            </div>
            <Btn kind="secondary" size="md">Save draft</Btn>
            <Btn kind="primary" size="md" icon="upload">Publish</Btn>
          </div>
        </div>
      </div>
    </WebShell>
  );
}

function Label({ children }) {
  return <div style={{ fontSize: 11.5, color: 'var(--pg-ink-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.05 }}>{children}</div>;
}

// ───────────────────────── 5. Validation queue ─────────────────────────
function W5_Validation() {
  const items = [
    { name: 'Sumardi B.', village: 'Hampangen Jaya', task: 'Canal block · SBG C-04', age: '2 h ago', auto: { gps: true, time: true, blur: true } },
    { name: 'Rina A.', village: 'Pangkoh Hilir', task: 'Revegetation · MWE-1 plot 12', age: '4 h ago', auto: { gps: true, time: true, blur: false } },
    { name: 'Joko P.', village: 'Hampangen Jaya', task: 'Canal block · SBG C-02', age: '7 h ago', auto: { gps: true, time: true, blur: true } },
    { name: 'Siti R.', village: 'Bukit Batu', task: 'Fire watch patrol · KPN-3', age: '11 h ago', auto: { gps: false, time: true, blur: true } },
    { name: 'Agus W.', village: 'Pangkoh Hilir', task: 'Canal block · MWE-1', age: '18 h ago', auto: { gps: true, time: true, blur: true } },
  ];
  return (
    <WebShell active="validate" title="Validation queue" subtitle="14 submissions awaiting review · oldest 36 h"
      headerRight={<div style={{ display: 'flex', gap: 8 }}><Btn kind="ghost" size="md" icon="sliders">Filters</Btn><Btn kind="secondary" size="md" icon="check">Bulk approve passed (8)</Btn></div>}>
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', height: '100%' }}>
        <aside style={{ borderRight: '1px solid var(--pg-border)', overflow: 'auto', background: 'var(--pg-surface-raised)' }}>
          {items.map((it, idx) => <ValRow key={it.name} {...it} active={idx === 0}/>)}
        </aside>
        <section style={{ padding: 24, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 48, height: 48, borderRadius: 10, background: 'linear-gradient(135deg,#3d2818,#c89b3c)', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: 16 }}>SB</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 17, fontWeight: 600 }}>Sumardi B. · Canal block SBG C-04</div>
              <div style={{ fontSize: 12.5, color: 'var(--pg-ink-secondary)' }}>Desa Hampangen Jaya · submitted 2 h ago · payout <b style={{ color: 'var(--pg-ink)', fontFamily: 'var(--pg-font-mono)' }}>Rp 250,000</b></div>
            </div>
            <Btn kind="secondary" size="md" icon="msg">Message</Btn>
            <Btn kind="ghost" size="md" icon="x">Reject</Btn>
            <Btn kind="secondary" size="md">Request revision</Btn>
            <Btn kind="success" size="md" icon="check">Approve & release Rp 250,000</Btn>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Card pad={0} style={{ overflow: 'hidden' }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--pg-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12.5, fontWeight: 600 }}>Before / After</span>
                <span style={{ fontSize: 11, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>P-01 ↔ P-03</span>
              </div>
              <div className="pg-raster-stub" data-layer="before · 2026-05-04 06:42 WIB" style={{ height: 280, position: 'relative' }}>
                <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(60,40,24,0.3) 0 52%, transparent 52%)' }}/>
                {/* slider handle */}
                <div style={{ position: 'absolute', left: '52%', top: 0, bottom: 0, width: 2, background: '#fff', boxShadow: '0 0 0 1px rgba(0,0,0,0.2)' }}/>
                <div style={{ position: 'absolute', left: '52%', top: '50%', transform: 'translate(-50%,-50%)', width: 32, height: 32, borderRadius: 16, background: '#fff', border: '1px solid var(--pg-border-strong)', display: 'grid', placeItems: 'center' }}>
                  <Icon name="arrowRight" size={14}/>
                </div>
                <div style={{ position: 'absolute', top: 8, left: 8, fontSize: 11, fontFamily: 'var(--pg-font-mono)', color: '#fff', background: 'rgba(0,0,0,0.45)', padding: '2px 6px', borderRadius: 4 }}>BEFORE</div>
                <div style={{ position: 'absolute', top: 8, right: 8, fontSize: 11, fontFamily: 'var(--pg-font-mono)', color: '#fff', background: 'rgba(0,0,0,0.45)', padding: '2px 6px', borderRadius: 4 }}>AFTER</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 1, background: 'var(--pg-border)', padding: 1 }}>
                {['P-01 06:42','P-02 09:18','P-03 11:53'].map(p => <div key={p} className="pg-raster-stub" data-layer={p} style={{ aspectRatio: '4/3' }}/>)}
              </div>
            </Card>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Card pad={0} style={{ overflow: 'hidden' }}>
                <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--pg-border)', fontSize: 12.5, fontWeight: 600 }}>GPS track on canal_mask</div>
                <div style={{ height: 188, position: 'relative' }}>
                  <MapStub layer="canal_mask · GPS track" bg="assets/aoi-satellite.png" style={{ borderRadius: 0, height: '100%' }}>
                    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
                      <path d="M 60 110 Q 120 80 180 90 T 320 100" stroke="var(--pg-risk)" strokeWidth="3" fill="none" strokeLinecap="round"/>
                      <circle cx="60" cy="110" r="6" fill="var(--pg-risk)" stroke="#fff" strokeWidth="2"/>
                      <circle cx="320" cy="100" r="6" fill="var(--pg-accent)" stroke="#fff" strokeWidth="2"/>
                    </svg>
                  </MapStub>
                </div>
              </Card>
              <Card pad={14}>
                <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>Auto-checks</div>
                {[
                  { l: 'GPS within 18 m of expected polygon', ok: true, v: '8.4 m mean offset' },
                  { l: 'Timestamps inside working window', ok: true, v: '06:42 → 11:53 WIB' },
                  { l: 'Photo blur / quality score', ok: true, v: '0.91 (≥ 0.8 required)' },
                  { l: 'Hash chain · device-sealed', ok: true, v: 'sha256 · 7 segments verified' },
                  { l: 'Track linear length ≥ 8 m', ok: true, v: '24.1 m' },
                ].map(c => (
                  <div key={c.l} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', fontSize: 12.5 }}>
                    <span style={{ width: 18, height: 18, borderRadius: 9, background: c.ok ? 'var(--pg-accent-soft)' : 'var(--pg-risk-soft)', color: c.ok ? 'var(--pg-accent)' : 'var(--pg-risk)', display: 'grid', placeItems: 'center' }}>
                      <Icon name={c.ok ? 'check' : 'x'} size={11} stroke={2.4}/>
                    </span>
                    <span style={{ flex: 1, color: 'var(--pg-ink)' }}>{c.l}</span>
                    <span style={{ color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)', fontSize: 11 }}>{c.v}</span>
                  </div>
                ))}
              </Card>
              <Card pad={14}>
                <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>Worker note (Bahasa)</div>
                <p style={{ fontSize: 13, color: 'var(--pg-ink)', lineHeight: 1.5 }}>"Saya pasang dam di mulut kanal sesuai instruksi. Air mulai naik di sisi hulu setelah 2 jam. Tidak ada gangguan."</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10 }}>
                  <Btn kind="ghost" size="sm" icon="play">Play voice (0:24)</Btn>
                  <span style={{ fontSize: 11, color: 'var(--pg-ink-muted)' }}>· Auto-translated EN available</span>
                </div>
              </Card>
            </div>
          </div>
        </section>
      </div>
    </WebShell>
  );
}

function ValRow({ name, village, task, age, auto, active }) {
  const okCount = Object.values(auto).filter(Boolean).length;
  return (
    <div style={{ padding: 14, borderBottom: '1px solid var(--pg-border)', display: 'flex', gap: 12, background: active ? 'var(--pg-primary-soft)' : 'transparent', borderLeft: `3px solid ${active ? 'var(--pg-primary)' : 'transparent'}`, cursor: 'pointer' }}>
      <div className="pg-raster-stub" data-layer="" style={{ width: 56, height: 56, borderRadius: 6, flexShrink: 0 }}/>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13.5, fontWeight: 600 }}>{name}</div>
        <div style={{ fontSize: 12, color: 'var(--pg-ink-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{task}</div>
        <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', display: 'flex', gap: 8, marginTop: 4 }}>
          <span>{village}</span>·<span>{age}</span>
        </div>
        <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
          <Chip size="sm" tone={auto.gps ? 'success' : 'risk'}>GPS</Chip>
          <Chip size="sm" tone={auto.time ? 'success' : 'risk'}>Time</Chip>
          <Chip size="sm" tone={auto.blur ? 'success' : 'warn'}>Blur</Chip>
          <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>{okCount}/3</span>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────── 6. Payments ─────────────────────────
function W6_Payments() {
  const pending = [
    { id: 'PG-58241', name: 'Sumardi B.', task: 'Canal block', amt: 250_000, rail: 'DANA', flag: null },
    { id: 'PG-58242', name: 'Rina A.', task: 'Revegetation', amt: 180_000, rail: 'BRI direct', flag: null },
    { id: 'PG-58243', name: 'Joko P.', task: 'Canal block', amt: 250_000, rail: 'DANA', flag: null },
    { id: 'PG-58244', name: 'Agus W.', task: 'Canal block', amt: 250_000, rail: 'OVO', flag: 'velocity' },
    { id: 'PG-58245', name: 'Siti R.', task: 'Fire patrol', amt: 120_000, rail: 'PT Pos cash', flag: null },
    { id: 'PG-58246', name: 'Toni H.', task: 'Canal block', amt: 250_000, rail: 'GoPay', flag: null },
  ];
  return (
    <WebShell active="pay" title="Payments" subtitle="Review and release approved task payouts"
      headerRight={<div style={{ display: 'flex', gap: 8 }}><Btn kind="ghost" size="md" icon="download">Export PDF</Btn><Btn kind="primary" size="md" icon="handCoin">Release batch (Rp 38.4 jt)</Btn></div>}>
      <div style={{ padding: 28, display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24, height: '100%', overflow: 'hidden' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
            <Card pad={14}><Stat label="Due this week" value="Rp 38,400,000" sub="32 villagers · 6 villages"/></Card>
            <Card pad={14}><Stat label="Released MTD" value="Rp 142,750,000" delta="+12%" sub="vs Apr"/></Card>
            <Card pad={14}><Stat label="Avg payout" value="Rp 218,750"/></Card>
            <Card pad={14}><Stat label="Disputed" value="2" delta="−1" deltaTone="success" sub="of 217 last 30 d"/></Card>
          </div>
          <Card pad={0} style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--pg-border)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600 }}>Pending payouts</span>
              <Chip tone="gold" size="sm">32 ready</Chip>
              <Chip tone="risk" size="sm">1 flagged</Chip>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                <Btn kind="ghost" size="sm" icon="search">Find worker</Btn>
                <Btn kind="ghost" size="sm" icon="sliders">Filter</Btn>
              </div>
            </div>
            <div style={{ overflow: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--pg-surface-sunken)', textAlign: 'left' }}>
                    {['', 'Worker', 'Task', 'Rail', 'Amount', 'Approved', ''].map(h => (
                      <th key={h} style={{ padding: '10px 16px', fontSize: 11, color: 'var(--pg-ink-muted)', textTransform: 'uppercase', letterSpacing: 0.04, fontWeight: 600, borderBottom: '1px solid var(--pg-border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pending.map(p => (
                    <tr key={p.id} style={{ borderBottom: '1px solid var(--pg-border)' }}>
                      <td style={{ padding: '12px 16px' }}><span style={{ width: 16, height: 16, border: '1.5px solid var(--pg-border-strong)', borderRadius: 4, background: 'var(--pg-primary)', display: 'inline-grid', placeItems: 'center' }}><Icon name="check" size={11} style={{ color: '#fff' }}/></span></td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600 }}>{p.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>{p.id}</div>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--pg-ink-secondary)' }}>{p.task}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5 }}>
                          <span style={{ width: 18, height: 18, borderRadius: 4, background: 'var(--pg-surface-sunken)', display: 'inline-grid', placeItems: 'center', fontSize: 9, fontWeight: 700 }}>{p.rail.slice(0,2).toUpperCase()}</span>
                          {p.rail}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: 600, fontFamily: 'var(--pg-font-mono)' }}>Rp {p.amt.toLocaleString('id-ID')}</td>
                      <td style={{ padding: '12px 16px', color: 'var(--pg-ink-muted)', fontSize: 12 }}>2 h ago</td>
                      <td style={{ padding: '12px 16px' }}>{p.flag && <Chip tone="warn" size="sm">flagged: {p.flag}</Chip>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
        <aside style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card pad={16}>
            <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>Batch summary</div>
            {[['Workers','32'],['Tasks completed','38'],['Subtotal','Rp 38,400,000'],['Service fee 0%','Rp 0'],['Total to disburse','Rp 38,400,000']].map(([k,v],i,a) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 13, fontWeight: i === a.length - 1 ? 600 : 400, borderTop: i === a.length - 1 ? '1px solid var(--pg-border)' : 'none', marginTop: i === a.length - 1 ? 6 : 0, paddingTop: i === a.length - 1 ? 12 : 6 }}>
                <span style={{ color: 'var(--pg-ink-secondary)' }}>{k}</span>
                <span style={{ fontFamily: 'var(--pg-font-mono)' }}>{v}</span>
              </div>
            ))}
            <Btn kind="primary" size="lg" full icon="handCoin" style={{ marginTop: 12 }}>Release Rp 38.4 jt now</Btn>
            <p style={{ fontSize: 11, color: 'var(--pg-ink-muted)', marginTop: 10, lineHeight: 1.4 }}>Funds settle DANA/OVO/GoPay in &lt; 60 s · BRI direct in 1 business day · PT Pos cash 24–48 h.</p>
          </Card>
          <Card pad={16}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <Icon name="warn" size={16} style={{ color: 'var(--pg-warn)' }}/>
              <span style={{ fontSize: 12.5, fontWeight: 600 }}>Anti-fraud · 1 flag</span>
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--pg-ink)' }}>
              <b>Agus W.</b> · 4 task completions in 6 hours, &gt;3× village median.
            </div>
            <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', marginTop: 4, lineHeight: 1.45 }}>Hold until manual review. Pattern match: <span style={{ fontFamily: 'var(--pg-font-mono)' }}>velocity-anomaly-v2</span></div>
            <div style={{ marginTop: 10, display: 'flex', gap: 6 }}>
              <Btn kind="secondary" size="sm">Open dispute</Btn>
              <Btn kind="ghost" size="sm">Override</Btn>
            </div>
          </Card>
        </aside>
      </div>
    </WebShell>
  );
}

// ───────────────────────── 7. Workers ─────────────────────────
function W7_Workers() {
  const workers = [
    { name: 'Sumardi B.', village: 'Hampangen Jaya', tasks: 38, rate: 95, paid: 8_750_000, rating: 4.8, badge: 'Team lead', verified: true },
    { name: 'Rina Anggraini', village: 'Pangkoh Hilir', tasks: 21, rate: 92, paid: 4_120_000, rating: 4.7, badge: null, verified: true },
    { name: 'Joko Pramono', village: 'Hampangen Jaya', tasks: 29, rate: 87, paid: 6_440_000, rating: 4.5, badge: null, verified: true },
    { name: 'Siti Rahmawati', village: 'Bukit Batu', tasks: 12, rate: 82, paid: 2_260_000, rating: 4.4, badge: null, verified: false },
    { name: 'Agus Wijaya', village: 'Pangkoh Hilir', tasks: 47, rate: 78, paid: 9_980_000, rating: 4.2, badge: null, verified: true, flag: 'velocity' },
    { name: 'Toni Hidayat', village: 'Bukit Batu', tasks: 18, rate: 100, paid: 3_960_000, rating: 4.9, badge: null, verified: true },
    { name: 'Maria Sinaga', village: 'Sungai Putri', tasks: 33, rate: 91, paid: 7_020_000, rating: 4.6, badge: 'Team lead', verified: true },
  ];
  return (
    <WebShell active="workers" title="Workers" subtitle="284 registered · 217 active in last 30 d"
      headerRight={<div style={{ display: 'flex', gap: 8 }}>
        <Btn kind="ghost" size="md" icon="msg">Broadcast message</Btn>
        <Btn kind="secondary" size="md" icon="download">Export CSV</Btn>
        <Btn kind="primary" size="md" icon="plus">Invite workers</Btn>
      </div>}>
      <div style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflow: 'hidden' }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ height: 38, padding: '0 14px', border: '1px solid var(--pg-border-strong)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8, flex: 1, background: 'var(--pg-surface-raised)' }}>
            <Icon name="search" size={16} style={{ color: 'var(--pg-ink-muted)' }}/>
            <span style={{ fontSize: 13, color: 'var(--pg-ink-muted)' }}>Search by name, village, NIK…</span>
          </div>
          <Btn kind="secondary" size="md" icon="sliders">All villages</Btn>
          <Btn kind="secondary" size="md">Verified only</Btn>
          <Btn kind="secondary" size="md">Sort: completion rate ↓</Btn>
        </div>
        <Card pad={0} style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--pg-surface-sunken)', textAlign: 'left' }}>
                  {['Worker','Village','Tasks','Completion %','Total paid','Rating','Status',''].map(h => (
                    <th key={h} style={{ padding: '12px 18px', fontSize: 11, color: 'var(--pg-ink-muted)', textTransform: 'uppercase', letterSpacing: 0.04, fontWeight: 600, borderBottom: '1px solid var(--pg-border)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {workers.map(w => (
                  <tr key={w.name} style={{ borderBottom: '1px solid var(--pg-border)' }}>
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{ width: 36, height: 36, borderRadius: 18, background: 'var(--pg-primary-soft)', color: 'var(--pg-primary)', display: 'grid', placeItems: 'center', fontSize: 12, fontWeight: 700 }}>{w.name.split(' ').map(p => p[0]).slice(0,2).join('')}</div>
                        <div>
                          <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                            {w.name}
                            {w.verified && <Icon name="shield" size={13} style={{ color: 'var(--pg-accent)' }}/>}
                            {w.badge && <Chip tone="gold" size="sm">{w.badge}</Chip>}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>NIK ••••••8421</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 18px', color: 'var(--pg-ink-secondary)' }}>{w.village}</td>
                    <td style={{ padding: '14px 18px', fontFamily: 'var(--pg-font-mono)' }}>{w.tasks}</td>
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 80, height: 5, background: 'var(--pg-surface-sunken)', borderRadius: 2.5, overflow: 'hidden' }}>
                          <div style={{ width: `${w.rate}%`, height: '100%', background: w.rate > 90 ? 'var(--pg-accent)' : w.rate > 80 ? 'var(--pg-warn)' : 'var(--pg-risk)' }}/>
                        </div>
                        <span style={{ fontFamily: 'var(--pg-font-mono)', fontSize: 12 }}>{w.rate}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '14px 18px', fontFamily: 'var(--pg-font-mono)', fontWeight: 600 }}>Rp {w.paid.toLocaleString('id-ID')}</td>
                    <td style={{ padding: '14px 18px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontWeight: 600 }}>★ {w.rating.toFixed(1)}</span>
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      {w.flag ? <Chip tone="warn" size="sm">flag: {w.flag}</Chip> : w.verified ? <Chip tone="success" size="sm">Verified</Chip> : <Chip tone="neutral" size="sm">Unverified</Chip>}
                    </td>
                    <td style={{ padding: '14px 18px' }}><Icon name="chev" size={16} style={{ color: 'var(--pg-ink-muted)' }}/></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </WebShell>
  );
}

// ───────────────────────── 8. Reports & impact ─────────────────────────
function W8_Reports() {
  return (
    <WebShell active="reports" title="Reports & impact" subtitle="Auto-generated monthly · public transparency view"
      headerRight={<div style={{ display: 'flex', gap: 8 }}><Btn kind="ghost" size="md" icon="eye">Preview public view</Btn><Btn kind="primary" size="md" icon="download">Download April 2026 PDF</Btn></div>}>
      <div style={{ padding: 28, display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24, height: '100%', overflow: 'auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <Card pad={20}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 14 }}>
              <div>
                <div style={{ fontSize: 11.5, color: 'var(--pg-ink-muted)', textTransform: 'uppercase', letterSpacing: 0.04, fontWeight: 600 }}>April 2026 · Programme report</div>
                <h2 style={{ fontSize: 22, fontWeight: 600, letterSpacing: -0.02, marginTop: 4 }}>PeatGuard · Kalimantan programme</h2>
                <div style={{ fontSize: 13, color: 'var(--pg-ink-secondary)', marginTop: 4 }}>Reporting period 1–30 Apr · 6 AOIs · 14 villages · partner: BRGM</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <Chip tone="success" size="sm">On track</Chip>
                <Chip tone="primary" size="sm">v4.2.1</Chip>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginTop: 18 }}>
              <Stat label="Canal blocks built" value="412" delta="+47" sub="vs Mar"/>
              <Stat label="Hectares restored" value="3,282" delta="+8.4%"/>
              <Stat label="tCO₂/yr avoided" value="142,180" delta="+11%"/>
              <Stat label="Payments disbursed" value="Rp 142.7 jt"/>
            </div>
          </Card>
          <Card pad={20}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <div style={{ fontSize: 13.5, fontWeight: 600 }}>Restoration progress · 12-month trend</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <Chip size="sm" tone="primary">Restored ha</Chip>
                <Chip size="sm" tone="success">Canal blocks</Chip>
              </div>
            </div>
            <ChartStub/>
          </Card>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Card pad={18}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>By AOI · hectares restored</div>
              {[['Mawas East',880,72],['Sungai Putri',1120,90],['Padang Sugihan',540,44],['Sebangau Block C',412,36],['Berbak-Sembilang',240,18],['Kampar Peninsula N',90,7]].map(([n,h,p]) => (
                <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', fontSize: 12.5 }}>
                  <span style={{ width: 130, color: 'var(--pg-ink-secondary)' }}>{n}</span>
                  <div style={{ flex: 1, height: 8, background: 'var(--pg-surface-sunken)', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: `${p}%`, height: '100%', background: 'var(--pg-accent)' }}/>
                  </div>
                  <span style={{ fontFamily: 'var(--pg-font-mono)', minWidth: 56, textAlign: 'right' }}>{h} ha</span>
                </div>
              ))}
            </Card>
            <Card pad={18}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Public transparency</div>
              <p style={{ fontSize: 12.5, color: 'var(--pg-ink-secondary)', lineHeight: 1.5 }}>Donors and journalists can read this report at a permanent URL. No login. Personally identifying data is hashed.</p>
              <div style={{ marginTop: 12, padding: 12, background: 'var(--pg-surface-sunken)', borderRadius: 8, fontFamily: 'var(--pg-font-mono)', fontSize: 12, color: 'var(--pg-ink)', wordBreak: 'break-all' }}>
                peatguard.id/r/clk-2026-04
              </div>
              <div style={{ marginTop: 10, display: 'flex', gap: 6 }}>
                <Btn kind="secondary" size="sm" icon="upload">Copy URL</Btn>
                <Btn kind="ghost" size="sm" icon="eye">Open</Btn>
              </div>
            </Card>
          </div>
        </div>
        <aside style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Card pad={16}>
            <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>Reporting cadence</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[['Monthly programme','Auto · 1st of month',true],['Quarterly donor','Manual sign-off',true],['Verra MRV bundle','Annual',false],['BRGM ministerial','Quarterly',true]].map(([n,m,on]) => (
                <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', fontSize: 12.5, borderBottom: '1px solid var(--pg-border)' }}>
                  <Icon name="file" size={16} style={{ color: 'var(--pg-ink-muted)' }}/>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>{n}</div>
                    <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)' }}>{m}</div>
                  </div>
                  <Chip size="sm" tone={on ? 'success' : 'neutral'}>{on ? 'On' : 'Off'}</Chip>
                </div>
              ))}
            </div>
          </Card>
          <Card pad={16}>
            <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 10 }}>Recent exports</div>
            {[['BRGM_CLK_2026-04.pdf','2.4 MB · 12 May'],['Verra_MRV_2026Q1.zip','18.1 MB · 04 May'],['Public_2026-04.html','220 KB · 02 May']].map(([n,m]) => (
              <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', fontSize: 12 }}>
                <Icon name="file" size={15} style={{ color: 'var(--pg-ink-muted)' }}/>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: 'var(--pg-font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n}</div>
                  <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)' }}>{m}</div>
                </div>
                <Icon name="download2" size={15} style={{ color: 'var(--pg-ink-muted)', cursor: 'pointer' }}/>
              </div>
            ))}
          </Card>
        </aside>
      </div>
    </WebShell>
  );
}

function ChartStub() {
  // Hand-built area chart (no SVG draw of imagery — this is data viz, allowed).
  const pts = [10,12,18,22,30,42,55,68,84,96,108,142];
  const max = Math.max(...pts);
  const path = pts.map((v,i) => `${i === 0 ? 'M' : 'L'} ${(i/(pts.length-1))*100} ${100 - (v/max)*92}`).join(' ');
  const area = path + ` L 100 100 L 0 100 Z`;
  return (
    <div style={{ position: 'relative', height: 220, padding: '0 0 22px' }}>
      <svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="cg" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="rgba(31,77,58,0.3)"/><stop offset="100%" stopColor="rgba(31,77,58,0)"/></linearGradient>
        </defs>
        {[20,40,60,80].map(y => <line key={y} x1="0" x2="100" y1={y} y2={y} stroke="rgba(20,20,15,0.06)" strokeWidth="0.3"/>)}
        <path d={area} fill="url(#cg)"/>
        <path d={path} fill="none" stroke="var(--pg-primary)" strokeWidth="0.7" vectorEffect="non-scaling-stroke"/>
        <path d={pts.map((v,i) => `${i === 0 ? 'M' : 'L'} ${(i/(pts.length-1))*100} ${100 - (v/max*0.6)*92}`).join(' ')} fill="none" stroke="var(--pg-accent)" strokeWidth="0.5" strokeDasharray="1.5 1" vectorEffect="non-scaling-stroke"/>
      </svg>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }}>
        {['May','Jul','Sep','Nov','Jan','Mar','Apr'].map(m => <span key={m}>{m}</span>)}
      </div>
    </div>
  );
}

// ───────────────────────── 9. Programme settings ─────────────────────────
function W9_Settings() {
  const navi = [{ id: 'gen', l: 'General', i: 'settings', on: true },{ id: 'pay', l: 'Payouts & rails', i: 'wallet' },{ id: 'val', l: 'Validation rules', i: 'check' },{ id: 'aoi', l: 'AOIs & layers', i: 'layers' },{ id: 'sat', l: 'Satellite refresh', i: 'refresh' },{ id: 'al', l: 'Alerts', i: 'bell' },{ id: 'tm', l: 'Team & roles', i: 'users' }];
  return (
    <WebShell active="settings" title="Programme settings" subtitle="PeatGuard · Kalimantan ops">
      <div style={{ display: 'grid', gridTemplateColumns: '232px 1fr', height: '100%' }}>
        <aside style={{ borderRight: '1px solid var(--pg-border)', padding: 14, display: 'flex', flexDirection: 'column', gap: 2, background: 'var(--pg-surface-raised)' }}>
          {navi.map(n => (
            <a key={n.id} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '8px 10px', borderRadius: 6, fontSize: 13, color: n.on ? 'var(--pg-primary)' : 'var(--pg-ink-secondary)', background: n.on ? 'var(--pg-primary-soft)' : 'transparent', fontWeight: n.on ? 600 : 500 }}>
              <Icon name={n.i} size={15}/>{n.l}
            </a>
          ))}
        </aside>
        <div style={{ overflow: 'auto', padding: 28, display: 'flex', flexDirection: 'column', gap: 18 }}>
          <SetSection title="Default payouts by task type" sub="Used as starting amount when an operator creates a task. Editable per task.">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
              {[['Canal block','250,000','per dam'],['Revegetation','180,000','per 1-ha plot'],['Monitor patrol','120,000','per 5 km route'],['Fire watch','150,000','per 6 h shift']].map(([n,a,u]) => (
                <Card key={n} pad={14}>
                  <div style={{ fontSize: 12, color: 'var(--pg-ink-muted)' }}>{n}</div>
                  <div style={{ fontSize: 20, fontWeight: 600, fontFamily: 'var(--pg-font-mono)', marginTop: 4 }}>Rp {a}</div>
                  <div style={{ fontSize: 11, color: 'var(--pg-ink-muted)' }}>{u}</div>
                </Card>
              ))}
            </div>
          </SetSection>
          <SetSection title="Validation rules" sub="Auto-checks applied to every submission before operator review.">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                ['GPS within polygon','accept ≤ 18 m offset',true],
                ['Photo blur score','reject &lt; 0.80',true],
                ['Working window','06:00–17:00 WIB',true],
                ['Linear length minimum','≥ 8 m for canal blocks',true],
                ['Sealed-hash chain','reject if broken',true],
                ['Operator manual review','always required for &gt; Rp 500,000',false],
              ].map(([k,v,on]) => (
                <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', border: '1px solid var(--pg-border)', borderRadius: 8 }}>
                  <Icon name={on ? 'check' : 'x'} size={16} style={{ color: on ? 'var(--pg-accent)' : 'var(--pg-ink-muted)' }}/>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{k}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--pg-ink-muted)', fontFamily: 'var(--pg-font-mono)' }} dangerouslySetInnerHTML={{__html: v}}/>
                  </div>
                  <button style={{ width: 32, height: 18, borderRadius: 9, background: on ? 'var(--pg-primary)' : 'var(--pg-border-strong)', border: 'none', position: 'relative', cursor: 'pointer' }}>
                    <div style={{ position: 'absolute', top: 2, left: on ? 16 : 2, width: 14, height: 14, borderRadius: 7, background: '#fff' }}/>
                  </button>
                </div>
              ))}
            </div>
          </SetSection>
          <SetSection title="Satellite & pipeline" sub="Inputs to the science workflow. Changes take effect next refresh.">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <Card pad={14}>
                <Field label="Refresh cadence" value="Every 12 days · S1 IW VV+VH"/>
                <div style={{ height: 1, background: 'var(--pg-border)', margin: '10px 0' }}/>
                <Field label="Hansen-cohort gradient threshold" value="0.18 (loose)" mono/>
                <div style={{ marginTop: 8, display: 'flex', gap: 6 }}><Btn kind="ghost" size="sm">Strict</Btn><Btn kind="soft" size="sm">Loose</Btn><Btn kind="ghost" size="sm">Custom…</Btn></div>
              </Card>
              <Card pad={14}>
                <Field label="Velocity-backed confidence threshold" value="|v| ≥ 8 mm/yr" mono/>
                <div style={{ height: 1, background: 'var(--pg-border)', margin: '10px 0' }}/>
                <Field label="Output projection" value="UTM 49S · EPSG:32749" mono/>
                <div style={{ height: 1, background: 'var(--pg-border)', margin: '10px 0' }}/>
                <Field label="Tile server (TiTiller)" value="tiles.peatguard.id" mono/>
              </Card>
            </div>
          </SetSection>
          <SetSection title="Partner agencies" sub="Outside organisations consuming PeatGuard outputs and co-funding tasks.">
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {[['BRGM','Central Kalimantan','Co-funder'],['WWF-ID','Sumatra','Donor'],['KLHK','National','Reviewer'],['IDH','Riau','Donor']].map(([n,r,role]) => (
                <Card key={n} pad={12} style={{ minWidth: 200 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{n}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--pg-ink-muted)' }}>{r} · {role}</div>
                </Card>
              ))}
            </div>
          </SetSection>
        </div>
      </div>
    </WebShell>
  );
}

function SetSection({ title, sub, children }) {
  return (
    <section>
      <div style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600 }}>{title}</h3>
        {sub && <p style={{ fontSize: 12.5, color: 'var(--pg-ink-secondary)', marginTop: 2 }}>{sub}</p>}
      </div>
      {children}
    </section>
  );
}

Object.assign(window, { W4_TaskCreator, W5_Validation, W6_Payments, W7_Workers, W8_Reports, W9_Settings });
