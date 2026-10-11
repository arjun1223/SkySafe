/* Local-only Plotly dashboard: metrics at 5 Hz, charts at <= 2.5 Hz. */
const $ = (id) => document.getElementById(id);
let lastSeq = 0, points = [], source = null, state = null, polling = false, chartTime = 0;
let lastMessage = '', toastTimer, plotBusy = false;
const colors = {};
const loadCheck = new LoadCellDiagnostics.Check();
let devReference=null, devPhysical=false, devStuck=false;
function resetDeveloperCheck() {loadCheck.reset();devReference=null;}
function renderDeveloper(s) {
  const m=s.latest || {}, now=performance.now();
  devPhysical=s.source==='serial' && !m.simulation && s.connection.connected && sensorOK(m,'load') && Number.isFinite(m.load_raw);
  const rawPoints=points.filter(p=>p.source==='serial' && !p.simulation && sensorOK(p,'load') && Number.isFinite(p.load_raw));
  const recent=rawPoints.filter(p=>p.time_ms>=m.time_ms-10000);
  devStuck=devPhysical && LoadCellDiagnostics.stuckZero(rawPoints);
  loadCheck.update(now,m,devPhysical);
  $('dev-raw').textContent=devPhysical?fmt(m.load_raw,0):'—';
  const strainLive=s.source==='serial'&&!m.simulation&&s.connection.connected&&sensorOK(m,'strain')&&Number.isFinite(m.strain_raw);
  $('dev-strain-raw').textContent=strainLive?fmt(m.strain_raw,0):'—';
  $('dev-strain-note').textContent=strainLive?'Second HX711 / before zeroing':s.connection.connected?'Second HX711 / '+(m.sensor_status?.strain||'unavailable'):'Second HX711 / offline';
  $('dev-delta').textContent=devPhysical && devReference!==null?fmt(m.load_raw-devReference,0):'—';
  $('dev-span').textContent=devPhysical && recent.length?fmt(Math.max(...recent.map(p=>p.load_raw))-Math.min(...recent.map(p=>p.load_raw)),0):'—';
  $('dev-range').textContent=devPhysical && recent.length?`${fmt(Math.min(...recent.map(p=>p.load_raw)),0)} / ${fmt(Math.max(...recent.map(p=>p.load_raw)),0)} counts`:'Minimum / maximum counts';
  $('dev-stream').textContent=!devPhysical?(s.source==='demo'||m.simulation?'SIMULATION / NO HARDWARE CHECK':'NO LIVE RAW DATA'):devStuck?'SUSPECTED STUCK AT ZERO':'LIVE RAW DATA';
  $('dev-stream').className='chip '+(devStuck?'warning':devPhysical?'ready':'');
  $('dev-stream-message').textContent=!devPhysical?'Select ESP32 · USB serial and connect the physical board. This panel does not substitute simulated sensor readings.':devStuck?'Raw output has stayed exactly zero for at least 5 seconds. This is separate from an uncalibrated 0 N display. Check power and HX711 connections; calibration is blocked.':'Watch the raw number and graph while gently pressing the free hanger. Either direction is valid; counts are not newtons.';
  $('dev-reference').disabled=!devPhysical || devStuck || loadCheck.running || recent.length<6;
  $('dev-check-start').disabled=!devPhysical || loadCheck.running;
  const result=loadCheck.result, phase=loadCheck.phase(now);
  $('dev-check-phase').textContent=phase;
  $('dev-check-phase').className=result?.tone||'';
  const elapsed=loadCheck.started===null?0:Math.min(12,(now-loadCheck.started)/1000);
  $('dev-check-progress').value=elapsed;
  const messages={'KEEP UNLOADED':'Leave the hanger unloaded and still. Collecting the starting reading.',
    'GENTLY PRESS & HOLD':'Gently press down on the free hanger and hold. Keep it clear of the wing and platform.',
    'RELEASE COMPLETELY':'Remove your hand completely and let the hanger settle.'};
  $('dev-check-message').textContent=result?result.message:loadCheck.running?`${messages[phase]} · ${Math.ceil(12-elapsed)} s remaining`:'Secure the root and keep the hanger clear. Start unloaded, gently press the free hanger when prompted, then release. No known weight needed.';
  $('dev-check-detail').textContent=result && Number.isFinite(result.reference)?`Reference ${fmt(result.reference,0)} · sustained change ${fmt(result.change,0)} · after-release change ${fmt(result.returnDelta,0)} · detection threshold ${fmt(result.threshold,0)} counts`:'Detects at least 3 readings above max(100 counts, 6 × measured idle noise). Return tolerance: max(detection threshold, 10% of response).';
  $('dev-calibrate').disabled=Boolean(s.pending)||!devPhysical||devStuck||!m.zeroed||loadCheck.running;
}
function themeColors() {
  const css = getComputedStyle(document.documentElement);
  const read = name => css.getPropertyValue(name).trim();
  Object.assign(colors, {teal:read('--green'), amber:read('--amber'), red:read('--red'),
    neutral:read('--chart-neutral'), muted:read('--muted'), text:read('--text'),
    grid:read('--line'), panel:read('--panel'), soft:read('--chart-soft')});
  const dark = document.documentElement.dataset.theme === 'dark';
  $('theme-toggle').checked = dark; $('theme-label').textContent = dark ? 'Dark' : 'Light';
}
themeColors();
const fmt = (value, digits=1) => Number.isFinite(value) ? value.toFixed(digits) : '—';
const plotConfig = {responsive:true, displayModeBar:false, scrollZoom:false};
function layout(xTitle, yTitle, small=false) {
  return {paper_bgcolor:'transparent', plot_bgcolor:'transparent', showlegend:false,
    margin:{l:small?50:64,r:20,t:small?16:24,b:small?36:47},
    font:{family:'-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif',color:colors.muted,size:10},
    xaxis:{title:{text:xTitle,font:{size:10}},gridcolor:colors.grid,zeroline:false,fixedrange:true,tickfont:{size:9}},
    yaxis:{title:{text:yTitle,font:{size:10}},gridcolor:colors.grid,zeroline:false,fixedrange:true,tickfont:{size:9}},
    uirevision:'skysafe', hovermode:small?'x unified':'closest'};
}
function toast(message, error=false) {
  $('toast').textContent = message; $('toast').className = error ? 'error' : '';
  $('toast').hidden = false; clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $('toast').hidden = true, error ? 7000 : 4300);
}
async function post(path, body={}) {
  try {
    const response = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(5000)});
    const result = await response.json();
    if (!response.ok || result.ok === false) throw new Error(result.message || 'Request failed.');
    if (result.message) toast(result.message);
    return result;
  } catch (error) {toast(error.message, true); return null;}
}
const statusNotes = {
  'NORMAL':'Response agrees with the healthy baseline.',
  'WARNING':'Response is departing from the healthy baseline.',
  'STRUCTURAL ANOMALY':'Large change in measured structural response.',
  'NEEDS_BASELINE':'Run a healthy baseline sweep to begin scoring.',
  'CALIBRATING':'Collecting healthy force and strain samples.',
  'NEEDS_CALIBRATION':'Zero sensors, then calibrate with a known load.',
  'OUT_OF_RANGE':'Load is outside the calibrated force envelope.',
  'SENSOR_FAULT':'Sensor data is unavailable, stale, or settling.',
  'ZEROING':'Keep the wing unloaded and motionless.'
};
function sensorOK(sample, name) {return sample.sensor_status ? sample.sensor_status[name] === 'ok' : sample.sensors_ok;}
function render(s) {
  const m = s.latest || {}, baseline = s.baseline_state.baseline;
  SkySafeLiveAlarm.render(s);
  renderDeveloper(s);
  const label = s.connection.connected ? m.status : (m.status || 'AWAITING DATA');
  const color = label === 'STRUCTURAL ANOMALY' ? colors.red : label === 'WARNING' ? colors.amber : colors.teal;
  const sensorsLive = s.connection.connected && m.sensors_ok;
  $('force-value').textContent = s.connection.connected && sensorOK(m,'load') && m.force_calibrated && m.zeroed ? fmt(m.force_n,2) : '—';
  $('strain-value').textContent = s.connection.connected && sensorOK(m,'strain') && m.zeroed ? fmt(m.strain_delta,0) : '—';
  $('vibration-value').textContent = s.connection.connected && sensorOK(m,'vibration') ? fmt(m.accel_rms,3) : '—';
  $('deflection-value').textContent = s.connection.connected && sensorOK(m,'ultrasonic') ? fmt(m.tip_deflection_mm) : '—';
  const sensorNames = {load:'LOAD CELL',strain:'STRAIN BRIDGE',vibration:'MPU IMU',ultrasonic:'TIP SENSOR'};
  $('sensor-indicators').replaceChildren(...Object.entries(sensorNames).map(([key,name])=>{
    const indicator=document.createElement('span');
    const sensorState = !s.connection.connected ? 'offline' : (m.sensor_status?.[key] || (key==='ultrasonic'?'disabled':m.sensors_ok?'ok':'fault'));
    indicator.className=sensorState;indicator.textContent=name+' / '+sensorState.toUpperCase().replaceAll('_',' ');return indicator;
  }));
  const test=s.demo_test, result=test.result;
  const liveForce=s.connection.connected && sensorOK(m,'load') && m.zeroed && m.force_calibrated ? m.force_n : null;
  $('test-force').textContent=fmt(liveForce,2);
  $('test-force-progress').max=test.target_force_n;
  $('test-force-progress').value=Number.isFinite(liveForce)?Math.max(0,liveForce):0;
  $('test-phase').textContent=s.connection.connected?(test.phase==='HOLDING'?'TARGET REACHED':test.phase):'NO LIVE DATA';
  $('test-message').textContent=s.connection.connected?test.message:'Telemetry unavailable. Reconnect before testing.';
  if($('test-target').dataset.target!==String(test.target_force_n)) { $('test-target').value=test.target_force_n; $('test-target').dataset.target=String(test.target_force_n); }
  $('test-start').disabled=Boolean(s.pending)||!s.connection.connected||!baseline||!['NORMAL','WARNING','STRUCTURAL ANOMALY','OUT_OF_RANGE'].includes(m.status)||s.baseline_state.collecting||['LOADING','HOLDING'].includes(test.phase);
  $('test-zero').disabled=Boolean(s.pending)||!s.connection.connected||s.baseline_state.collecting;
  $('test-result-status').textContent=result?result.status:'NO TEST YET';
  $('test-result').className='judge-result '+(result?.status==='NORMAL'?'normal':result?.status==='WARNING'?'warning':result?.status==='STRUCTURAL ANOMALY'?'anomaly':'');
  $('test-result-health').textContent=fmt(result?.health_score,0);
  $('test-result-force').textContent=fmt(result?.force_n,2)+' N';
  $('test-result-deflection').textContent=fmt(result?.tip_deflection_mm)+' mm';
  $('test-result-strain').textContent=(result?.strain_deviation_pct>0?'+':'')+fmt(result?.strain_deviation_pct)+'%';
  $('test-result-stiffness').textContent=fmt(result?.stiffness_n_per_mm,2)+' N/mm';
  $('test-result-coverage').classList.toggle('fault',Boolean(result&&!s.connection.connected));
  $('test-provenance').textContent=result?(result.simulation?' / SIMULATED':' / MEASURED'):'';
  $('test-result-coverage').textContent=result?`${result.samples} samples · ${result.coverage.join(' + ')} · ${new Date(result.timestamp).toLocaleTimeString()} · Retained test result${!s.connection.connected?' · NO LIVE CONNECTION':''}`:'A measured healthy baseline is required.';
  $('ultrasonic-sim').checked=s.demo.ultrasonic;
  $('ultrasonic-sim').disabled=s.baseline_state.collecting||['LOADING','HOLDING'].includes(test.phase);
  const df=baseline?.deflection;
  document.querySelector('.deflection-panel').hidden=m.sensor_status?.ultrasonic==='disabled'&&!df;
  $('deflection-timeline').hidden=m.sensor_status?.ultrasonic==='disabled'&&!df;
  $('stiffness-label').textContent=df?`Healthy stiffness ${fmt(1/df.k,2)} N/mm`:'Stiffness unavailable';
  $('deflection-fit-label').textContent=df?`deflection = ${fmt(df.k,3)} × force + ${fmt(df.b,2)} mm · R² ${fmt(df.r_squared,4)}`:'Enable the tip sensor, ZERO unloaded, then repeat a healthy sweep.';
  $('health-value').textContent = fmt(m.health_score,0);
  $('health-value').style.color = color;
  $('health-bar').style.width = (Number.isFinite(m.health_score) ? m.health_score : 0) + '%';
  $('health-bar').style.background = color;
  $('score-note').textContent = Number.isFinite(m.health_score) ? ((baseline?.vibration_available!==false && !(m.coverage||['strain','vibration']).includes('vibration')) || (baseline?.strain_available!==false && !(m.coverage||['strain','vibration']).includes('strain')) || (baseline?.deflection && !(m.coverage||[]).includes('deflection')) ? 'Limited coverage · ' : 'Experimental score · ')+(m.coverage||['strain','vibration']).join(' + ') : 'Unrated · ' + (label || 'awaiting data').toLowerCase().replaceAll('_',' ');
  $('status-value').textContent = label.replaceAll('_',' ');
  $('status-note').textContent = statusNotes[label] || 'Waiting for a live sensor stream.';
  $('status-card').className = 'metric status-metric ' + (label === 'NORMAL' ? 'normal' : label === 'STRUCTURAL ANOMALY' ? 'anomaly' : label === 'WARNING' ? 'warning' : '');
  $('connection').className = 'connection ' + (s.connection.connected ? 'live' : '');
  $('connection').replaceChildren(Object.assign(document.createElement('i'),{}), document.createTextNode(s.connection.connected ? s.source==='demo'?'Live · Simulation':'Live · USB' : 'Waiting for telemetry'));
  $('connection').title = s.connection.error || `${s.connection.invalid_lines} invalid serial lines discarded`;
  // Keep the source selector on an unconnected serial choice until Connect is pressed.
  if (source !== s.source) {
    source = s.source; $('source').value = source; syncSourceControls();
  }
  const localDemo = s.source === 'demo';
  $('demo-controls').hidden = !localDemo;
  $('hardware-help').hidden = localDemo;
  $('calibration-controls').hidden = localDemo;
  $('source-badge').textContent = localDemo ? 'SIMULATED' : (m.simulation ? 'ESP32 SIM' : 'HARDWARE');
  const simMode = localDemo ? s.demo.mode : m.simulation_mode;
  $('normal-wing').classList.toggle('selected',simMode === 'NORMAL');
  $('anomaly-wing').classList.toggle('selected',simMode === 'ANOMALY');
  $('normal-wing').disabled = $('anomaly-wing').disabled = !localDemo && !m.simulation;
  $('auto-force').checked = s.demo.auto_force;
  $('manual-force').disabled = s.demo.auto_force || !localDemo;
  if (document.activeElement !== $('manual-force')) $('manual-force').value = s.demo.force;
  $('manual-force-label').textContent = fmt(s.demo.force) + ' N';
  $('prepare-demo').disabled = s.demo.preparing;
  $('prepare-demo').textContent = s.demo.preparing ? 'Collecting healthy response…' : 'Run healthy baseline sweep ↗';
  const bs = s.baseline_state;
  $('baseline-badge').textContent = bs.collecting ? 'Collecting' : baseline ? 'Baseline ready' : 'No baseline';
  $('baseline-badge').className = 'chip ' + (baseline ? 'ready' : '');
  $('baseline-count').textContent = bs.samples + ' samples';
  $('baseline-progress-label').textContent = bs.collecting ? 'Sweeping the healthy wing' : baseline ? 'Healthy response captured' : 'Baseline not established';
  $('baseline-progress').max = s.demo.preparing ? 160 : Math.max(60,bs.samples);
  $('baseline-progress').value = baseline ? $('baseline-progress').max : bs.samples;
  $('baseline-slope').textContent = baseline ? fmt(baseline.k,2) + ' counts/N' : '— counts/N';
  $('baseline-r2').textContent = baseline ? fmt(baseline.r_squared,4) + ' R²' : '— R²';
  $('baseline-range').textContent = baseline ? fmt(baseline.force_min) + '–' + fmt(baseline.force_max) + ' N' : '— N';
  $('fit-label').textContent = baseline ? `strain = ${fmt(baseline.k,2)} × force ${baseline.b<0?'−':'+'} ${fmt(Math.abs(baseline.b),1)} · R² ${fmt(baseline.r_squared,4)}` : 'Establish a healthy sweep to draw the expected response.';
  $('residual-label').textContent = 'Deviation ' + fmt(m.strain_deviation,0) + ' counts';
  document.querySelectorAll('[data-command]').forEach(b => b.disabled = Boolean(s.pending));
  $('calibrate').disabled = Boolean(s.pending)||!devPhysical||devStuck||!m.zeroed||loadCheck.running;
  if (s.last_command && s.last_command.message !== lastMessage) {
    lastMessage = s.last_command.message; toast(lastMessage, !s.last_command.ok);
  }
  $('recording-badge').textContent = s.recording.active ? '● RECORDING' : 'NOT RECORDING';
  $('recording-badge').className = 'chip ' + (s.recording.active ? 'ready' : '');
  $('record-start').hidden = s.recording.active;
  $('record-stop').hidden = !s.recording.active;
  if (s.recording.filename) $('recording-info').textContent = `${s.recording.rows} samples · ${s.recording.active ? 'Recording' : 'Saved'} ${s.recording.filename}`;
  $('wing-shape').setAttribute('d',simMode === 'ANOMALY' ? 'M44 45Q200 64 348 93L344 107Q200 80 44 75Z' : 'M44 45L348 68 344 81 44 75Z');
  $('wing-shape').setAttribute('stroke',simMode === 'ANOMALY' ? colors.amber : colors.teal);
}
async function charts(s) {
  if (plotBusy) return;
  plotBusy = true;
  try {
    const b = s.baseline_state.baseline, current = s.latest || {};
    const recent = points.filter(p => sensorOK(p,'load') && sensorOK(p,'strain') && p.force_calibrated && p.zeroed).slice(-240);
    const healthy = {x:b&&b.strain_available!==false?[b.force_min,b.force_max]:[], y:b&&b.strain_available!==false?[b.k*b.force_min+b.b,b.k*b.force_max+b.b]:[], mode:'lines', line:{color:colors.teal,width:2,dash:'dash'},hovertemplate:'Healthy: %{y:.1f} counts at %{x:.2f} N<extra></extra>'};
    const observations = {x:recent.map(p=>p.force_n),y:recent.map(p=>p.strain_delta),mode:'markers',marker:{size:5,color:recent.map(p=>p.status==='STRUCTURAL ANOMALY'?colors.red:p.status==='WARNING'?colors.amber:colors.neutral),opacity:.55},hovertemplate:'%{x:.2f} N<br>%{y:.0f} counts<extra></extra>'};
    const currentValid = s.connection.connected && sensorOK(current,'load') && sensorOK(current,'strain') && current.force_calibrated && current.zeroed;
    const active = {x:currentValid?[current.force_n]:[],y:currentValid?[current.strain_delta]:[],mode:'markers',marker:{size:11,color:colors.text,line:{color:colors.panel,width:2}},hovertemplate:'Current: %{x:.2f} N<br>%{y:.0f} counts<extra></extra>'};
    const time = points.map(p=>p.time_ms/1000);
    if(!$('developer-panel').hidden) {
      const raw=points.filter(p=>p.source==='serial'&&!p.simulation&&sensorOK(p,'load')&&Number.isFinite(p.load_raw));
      await Plotly.react('dev-raw-chart',[{x:raw.map(p=>p.time_ms/1000),y:raw.map(p=>p.load_raw),mode:'lines',line:{color:colors.text,width:1.8},hovertemplate:'%{y:.0f} counts<extra></extra>'}],layout('Device elapsed time (s)','Raw ADC counts',true),plotConfig);
      const strain=points.filter(p=>p.source==='serial'&&!p.simulation&&sensorOK(p,'strain')&&Number.isFinite(p.strain_raw));
      await Plotly.react('dev-strain-chart',[{x:strain.map(p=>p.time_ms/1000),y:strain.map(p=>p.strain_raw),mode:'lines',line:{color:colors.text,width:1.8},hovertemplate:'%{y:.0f} counts<extra></extra>'}],layout('Device elapsed time (s)','Raw ADC counts',true),plotConfig);
    }
    const df=b?.deflection;
    const tipPoints=points.filter(p=>sensorOK(p,'load')&&sensorOK(p,'ultrasonic')&&p.force_calibrated&&p.zeroed&&Number.isFinite(p.tip_deflection_mm)).slice(-240);
    await Promise.all([
      Plotly.react('deflection-response-chart',[
        {x:df?[df.force_min,df.force_max]:[],y:df?[df.k*df.force_min+df.b,df.k*df.force_max+df.b]:[],mode:'lines',line:{color:colors.teal,dash:'dash',width:2}},
        {x:tipPoints.map(p=>p.force_n),y:tipPoints.map(p=>p.tip_deflection_mm),mode:'markers',marker:{color:colors.neutral,size:5}},
        {x:s.connection.connected&&sensorOK(current,'load')&&sensorOK(current,'ultrasonic')&&current.force_calibrated&&current.zeroed?[current.force_n]:[],y:s.connection.connected&&sensorOK(current,'ultrasonic')?[current.tip_deflection_mm]:[],mode:'markers',marker:{color:colors.text,size:11}}
      ],layout('Applied force (N)','Tip deflection (mm)'),plotConfig),
      Plotly.react('deflection-chart',[{x:time,y:points.map(p=>sensorOK(p,'ultrasonic')?p.tip_deflection_mm:null),mode:'lines',line:{color:colors.text,width:1.8}}],layout('Elapsed time (s)','',true),plotConfig),
      Plotly.react('response-chart',[healthy,observations,active],layout('Applied force (N)','Strain response (ADC counts)'),plotConfig),
      Plotly.react('force-chart',[{x:time,y:points.map(p=>sensorOK(p,'load')&&p.force_calibrated&&p.zeroed?p.force_n:null),mode:'lines',line:{color:colors.neutral,width:1.8}}],layout('Elapsed time (s)','',true),plotConfig),
      Plotly.react('strain-chart',[{x:time,y:points.map(p=>sensorOK(p,'strain')&&p.zeroed?p.strain_delta:null),mode:'lines',line:{color:colors.text,width:1.8}},{x:time,y:points.map(p=>p.expected_strain),mode:'lines',line:{color:colors.teal,width:1,dash:'dash'}}],layout('Elapsed time (s)','',true),plotConfig),
      Plotly.react('vibration-chart',[{x:time,y:points.map(p=>sensorOK(p,'vibration')?p.accel_rms:null),mode:'lines',line:{color:colors.neutral,width:1.8}},{x:time,y:points.map(p=>sensorOK(p,'vibration')?p.vibration_peak:null),mode:'lines',line:{color:colors.soft,width:1}}],layout('Elapsed time (s)','',true),plotConfig)
    ]);
  } finally {plotBusy=false;}
}
async function poll() {
  if (polling) return;
  polling = true;
  try {
    const response = await fetch('/api/state?after='+lastSeq,{cache:'no-store',signal:AbortSignal.timeout(3000)});
    if (!response.ok) throw new Error('Telemetry request failed.');
    const s = await response.json();
    // A restarted server begins a fresh sequence, even when the source is unchanged.
    if (s.latest && (s.latest.seq < lastSeq || (points.length && s.latest.time_ms<points.at(-1).time_ms))) {loadCheck.abort('Device or dashboard restarted. Restart the check.');devReference=null;points=[];lastSeq=0;}
    if (source !== null && source !== s.source) {resetDeveloperCheck();points=[];lastSeq=0;}
    if (s.history.length) {points=points.concat(s.history).slice(-600);lastSeq=s.history.at(-1).seq;}
    state=s;render(s);
    if (performance.now()-chartTime>400) {chartTime=performance.now();await charts(s);}
  } catch(error) {
    devPhysical=false;loadCheck.abort('Dashboard disconnected. Reconnect and restart the check.');
    ['dev-raw','dev-delta','dev-span','dev-strain-raw'].forEach(id=>$(id).textContent='—');
    $('dev-stream').textContent='NO LIVE RAW DATA';$('dev-stream').className='chip';
    $('dev-stream-message').textContent='Dashboard disconnected. Waiting for live data.';
    $('dev-check-start').disabled=true;$('dev-reference').disabled=true;$('dev-calibrate').disabled=true;$('calibrate').disabled=true;
    if(loadCheck.result){$('dev-check-phase').textContent=loadCheck.result.status;$('dev-check-message').textContent=loadCheck.result.message;}
    $('connection').className='connection';
    $('connection').textContent='Dashboard disconnected';
    $('status-value').textContent='NO LIVE DATA';$('status-card').className='metric status-metric';
    ['force-value','strain-value','vibration-value','health-value','deflection-value','test-force'].forEach(id=>$(id).textContent='—');
    $('test-phase').textContent='NO LIVE DATA';$('test-message').textContent='Local server disconnected. Reconnect before testing.';$('test-start').disabled=true;$('test-zero').disabled=true;$('test-force-progress').value=0;
    $('health-bar').style.width='0%';$('status-note').textContent='Reconnect to the local server.';
  } finally {polling=false;}
}
function syncSourceControls() {$('serial-controls').hidden=$('source').value!=='serial';}
async function refreshPorts() {
  try {
    const data=await (await fetch('/api/ports')).json();
    $('serial-port').replaceChildren(new Option('Choose serial port',''),...data.ports.map(p=>new Option(`${p.device} · ${p.description}`,p.device)));
  } catch {toast('Unable to list serial ports.',true);}
}
async function refreshRuns() {
  try {
    const data=await (await fetch('/api/runs')).json();
    $('run-files').replaceChildren();
    if (!data.files.length) $('run-files').textContent='No saved runs yet.';
    data.files.forEach(file=>{const a=document.createElement('a');a.href='/api/runs/'+encodeURIComponent(file.name);a.download=file.name;const name=document.createElement('span');name.textContent=file.name;const size=document.createElement('small');size.textContent=(file.bytes/1024).toFixed(1)+' KB ↓';a.append(name,size);$('run-files').append(a);});
  } catch {toast('Unable to list saved CSV runs.',true);}
}
$('source').addEventListener('change',async()=>{syncSourceControls();if($('source').value==='demo'){const result=await post('/api/source',{source:'demo'});if(!result){$('source').value=source;syncSourceControls();}else{points=[];lastSeq=0;}}else await refreshPorts();});
$('refresh-ports').addEventListener('click',refreshPorts);
$('connect-serial').addEventListener('click',async()=>{const result=await post('/api/source',{source:'serial',port:$('serial-port').value});if(result){points=[];lastSeq=0;source=null;}});
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>post('/api/command',{command:button.dataset.command})));
$('calibrate').addEventListener('click',()=>post('/api/command',{command:'CALIBRATE',force:Number($('known-force').value)}));
$('developer-toggle').addEventListener('change',()=>{
  $('developer-panel').hidden=!$('developer-toggle').checked;
  if($('developer-panel').hidden && loadCheck.running)loadCheck.abort('Developer mode closed. Restart the check when ready.');
  chartTime=0;if(state)renderDeveloper(state);
});
$('dev-reference').addEventListener('click',()=>{
  if(!devPhysical||devStuck)return;
  const recent=points.filter(p=>p.source==='serial'&&!p.simulation&&sensorOK(p,'load')&&Number.isFinite(p.load_raw)).slice(-10);
  if(recent.length<6)return toast('Wait for fresh readings before capturing a reference.',true);
  devReference=LoadCellDiagnostics.median(recent.map(p=>p.load_raw));
  toast('Raw reference captured. This does not zero or calibrate the ESP32.');renderDeveloper(state);
});
$('dev-check-start').addEventListener('click',()=>{
  if(!devPhysical)return;
  loadCheck.start(performance.now(),state.latest);renderDeveloper(state);
});
$('dev-check-reset').addEventListener('click',()=>{resetDeveloperCheck();if(state)renderDeveloper(state);});
function showKnownMass() {
  const force=Number($('dev-mass').value)*9.80665/1000;
  $('dev-known-force').textContent=force>0&&Number.isFinite(force)?fmt(force,4)+' N':'Enter a positive mass';
}
$('dev-mass').addEventListener('input',showKnownMass);
$('dev-calibrate').addEventListener('click',()=>{
  const force=Number($('dev-mass').value)*9.80665/1000;
  if(!devPhysical||devStuck||!state.latest.zeroed||loadCheck.running)return toast('Restore live raw response and zero unloaded sensors before calibration.',true);
  if(!Number.isFinite(force)||force<=0||force>49)return toast('Enter a positive total mass corresponding to at most 49 N.',true);
  $('known-force').value=force.toFixed(6);
  post('/api/command',{command:'CALIBRATE',force});
});
showKnownMass();
async function wingMode(mode){if(state?.source==='serial')await post('/api/command',{command:'SIM_'+mode});else await post('/api/demo',{mode});}
$('normal-wing').addEventListener('click',()=>wingMode('NORMAL'));
$('anomaly-wing').addEventListener('click',()=>wingMode('ANOMALY'));
$('auto-force').addEventListener('change',()=>post('/api/demo',{auto_force:$('auto-force').checked}));
$('manual-force').addEventListener('input',()=>{$('manual-force-label').textContent=Number($('manual-force').value).toFixed(1)+' N';});
$('manual-force').addEventListener('change',()=>post('/api/demo',{force:Number($('manual-force').value)}));
$('unload').addEventListener('click',()=>post('/api/demo',{auto_force:false,force:0}));
$('prepare-demo').addEventListener('click',()=>post('/api/demo',{prepare:true}));
$('record-start').addEventListener('click',async()=>{if(await post('/api/runs/start',{name:$('run-name').value}))toast('Recording started.');});
$('record-stop').addEventListener('click',async()=>{if(await post('/api/runs/stop')){toast('Run saved. Download the CSV below.');await refreshRuns();}});
$('theme-toggle').addEventListener('change',()=>{
  const theme=$('theme-toggle').checked?'dark':'light';
  document.documentElement.dataset.theme=theme;
  try {localStorage.setItem('skysafe-theme',theme);} catch {}
  themeColors();chartTime=0;if(state)render(state);
});
poll();refreshRuns();setInterval(poll,200);

$('test-zero').addEventListener('click',()=>post('/api/test',{action:'zero'}));
$('test-start').addEventListener('click',()=>post('/api/test',{action:'start',target:Number($('test-target').value)}));
$('test-reset').addEventListener('click',()=>post('/api/test',{action:'reset'}));
$('ultrasonic-sim').addEventListener('change',()=>post('/api/demo',{ultrasonic:$('ultrasonic-sim').checked}));
