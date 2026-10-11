/* Independent calibrated-load / gravity-removed RMS alerts. No health override. */
(function(root) {
  function evaluate(state) {
    const m=state.latest||{}, limits=state.alarm_limits||{force_n:0.75,vibration_m_s2:6};
    const ok=name=>m.sensor_status?m.sensor_status[name]==='ok':m.sensors_ok;
    const live=Boolean(state.connection?.connected);
    const force=live&&ok('load')&&m.zeroed&&m.force_calibrated&&Number.isFinite(m.force_n)&&Math.abs(m.force_n)>=limits.force_n;
    const vibration=live&&ok('vibration')&&Number.isFinite(m.accel_rms)&&m.accel_rms>=limits.vibration_m_s2;
    return {active:Boolean(force||vibration),force:Boolean(force),vibration:Boolean(vibration),live,limits};
  }
  if(typeof module!=='undefined'&&module.exports)module.exports={evaluate};
  if(typeof document==='undefined')return;
  const el=id=>document.getElementById(id);
  let context=null, oscillator=null, gain=null, enabled=false, active=false;
  function silence() {
    if(gain&&context){gain.gain.cancelScheduledValues(context.currentTime);gain.gain.setValueAtTime(0,context.currentTime);}
  }
  function sound() {
    if(!enabled||!active||!context||context.state!=='running'){silence();return;}
    const now=context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(0.10,now);
    // Audio expires without fresh UI updates, including a stalled browser/network.
    gain.gain.setValueAtTime(0,now+0.6);
    oscillator.frequency.setValueAtTime(Math.floor(performance.now()/350)%2?1100:680,now);
  }
  root.SkySafeLiveAlarm={render(state){
    const a=evaluate(state);active=a.active;
    el('live-alarm').classList.toggle('active',active);
    document.body.classList.toggle('live-alarm-active',active);
    const names=[a.force?'LOAD LIMIT EXCEEDED':null,a.vibration?'HIGH VIBRATION':null].filter(Boolean);
    const title=active?names.join(' + '):a.live?'LIVE LOAD / VIBRATION ALARM':'ALARM / WAITING FOR LIVE DATA';
    if(el('live-alarm-title').textContent!==title)el('live-alarm-title').textContent=title;
    el('live-alarm-note').textContent=`Force ≥ ${a.limits.force_n} N or vibration RMS ≥ ${a.limits.vibration_m_s2} m/s². `+(active?'Release the load. ':'')+'Independent of structural health.';
    sound();
  }};
  el('alarm-sound').addEventListener('click',async()=>{
    if(enabled){enabled=false;silence();}
    else {
      try {
        if(!context){
          const Audio=root.AudioContext||root.webkitAudioContext;
          if(!Audio)throw new Error('Audio unavailable');
          context=new Audio();gain=context.createGain();gain.gain.value=0;gain.connect(context.destination);
          oscillator=context.createOscillator();oscillator.type='square';oscillator.connect(gain);oscillator.start();
        }
        await context.resume();enabled=context.state==='running';sound();
      }catch{enabled=false;el('alarm-sound').textContent='Audio unavailable';return;}
    }
    el('alarm-sound').textContent=enabled?'Mute siren':'Enable siren';
    el('alarm-sound').setAttribute('aria-pressed',String(enabled));
  });
  root.addEventListener('pagehide',silence);
})(typeof window==='undefined'?globalThis:window);
