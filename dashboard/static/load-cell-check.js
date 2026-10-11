/* Raw response diagnostics only; never assigns force calibration or health. */
(function(root) {
  'use strict';
  const CONFIG = Object.freeze({baselineMs:3000, pressMs:6000, releaseMs:3000,
    minimumSamples:6, sustainedSamples:3, minimumChangeCounts:100,
    noiseMultiplier:6, returnFraction:0.1, stuckZeroMs:5000});
  const median = values => {
    const a=values.slice().sort((x,y)=>x-y), n=a.length;
    return n ? (a[Math.floor(n/2)]+a[Math.floor((n-1)/2)])/2 : null;
  };
  function assess(baseline, pressed, released) {
    if ([baseline,pressed,released].some(a=>a.length<CONFIG.minimumSamples))
      return {status:'INSUFFICIENT DATA',tone:'warning',message:'Not enough fresh readings. Check the connection and retry.'};
    const reference=median(baseline);
    const noise=1.4826*median(baseline.map(v=>Math.abs(v-reference)));
    const threshold=Math.max(CONFIG.minimumChangeCounts,CONFIG.noiseMultiplier*noise);
    // Require several samples in the same direction: one isolated spike cannot pass.
    const positive=pressed.map(v=>v-reference).filter(v=>v>threshold).sort((a,b)=>b-a);
    const negative=pressed.map(v=>reference-v).filter(v=>v>threshold).sort((a,b)=>b-a);
    const n=CONFIG.sustainedSamples;
    const up=positive.length>=n?median(positive.slice(0,n)):0;
    const down=negative.length>=n?median(negative.slice(0,n)):0;
    const change=up>=down?up:-down;
    const returned=median(released.slice(-CONFIG.minimumSamples))-reference;
    const details={reference,noise,threshold,change,returnDelta:returned};
    if (!change) return {...details,status:baseline.concat(pressed,released).every(v=>v===0)?'STUCK AT ZERO':'NO RESPONSE DETECTED',tone:'warning',message:'No sustained response detected. Check the load path and HX711 wiring; do not calibrate yet.'};
    if (Math.abs(returned)>Math.max(threshold,Math.abs(change)*CONFIG.returnFraction))
      return {...details,status:'RESPONSE / NOT RETURNED',tone:'warning',message:'A response was measured, but it did not return close to the reference. Fully release the hanger and check for contact or mounting movement.'};
    return {...details,status:'RESPONSE / RETURNED',tone:'ready',message:'Sustained response detected and returned near the reference. This is a sensor response check, not a calibrated force or strength result.'};
  }
  class Check {
    constructor() {this.reset();}
    reset() {this.started=null;this.lastSeq=null;this.lastDeviceTime=null;this.groups=[[],[],[]];this.result=null;}
    start(now,sample) {this.reset();this.started=now;this.lastSeq=sample.seq;this.lastDeviceTime=sample.time_ms;}
    get running() {return this.started!==null && !this.result;}
    abort(message) {if(this.running)this.result={status:'CHECK INTERRUPTED',tone:'warning',message};}
    update(now,sample,live) {
      if(!this.running)return;
      if(!live || !Number.isFinite(sample?.load_raw)) {this.abort('Live physical load-cell data was lost. Reconnect and restart the check.');return;}
      if(sample.seq<this.lastSeq || sample.time_ms<this.lastDeviceTime) {this.abort('The device or dashboard restarted. Restart the check with fresh data.');return;}
      const elapsed=now-this.started;
      if(elapsed>=CONFIG.baselineMs+CONFIG.pressMs+CONFIG.releaseMs) {this.result=assess(...this.groups);return;}
      if(sample.seq===this.lastSeq || sample.time_ms===this.lastDeviceTime)return;
      this.lastSeq=sample.seq;this.lastDeviceTime=sample.time_ms;
      const phase=elapsed<CONFIG.baselineMs?0:elapsed<CONFIG.baselineMs+CONFIG.pressMs?1:2;
      this.groups[phase].push(sample.load_raw);
    }
    phase(now) {
      if(this.result)return this.result.status;
      if(!this.running)return 'READY TO CHECK';
      const elapsed=now-this.started;
      if(elapsed<CONFIG.baselineMs)return 'KEEP UNLOADED';
      if(elapsed<CONFIG.baselineMs+CONFIG.pressMs)return 'GENTLY PRESS & HOLD';
      return 'RELEASE COMPLETELY';
    }
  }
  function stuckZero(samples) {
    if(samples.length<CONFIG.minimumSamples)return false;
    const last=samples.at(-1), recent=samples.filter(p=>p.time_ms>=last.time_ms-CONFIG.stuckZeroMs-1000);
    return recent.length>=CONFIG.minimumSamples && last.time_ms-recent[0].time_ms>=CONFIG.stuckZeroMs && recent.every(p=>p.load_raw===0);
  }
  const api={CONFIG,median,assess,Check,stuckZero};
  if(typeof module==='object' && module.exports)module.exports=api;
  else root.LoadCellDiagnostics=api;
})(globalThis);
