"""Accelerated deterministic judging sequence; writes explicitly simulated CSVs."""
import json
from datetime import datetime, timezone
from dashboard.anomaly_detection import Detector
from dashboard.simulator import Simulator
from dashboard.data_logging import RunLogger, DATA_DIR


def main():
    sim=Simulator();detector=Detector();logger=RunLogger()
    for _ in range(100):sim.sample()
    detector.start()
    for i in range(1700):
        s=sim.sample()
        if i%10==0:detector.evaluate(s['force_n'],s['strain_delta'],s['accel_rms'])
    baseline=detector.stop()
    result={'baseline':baseline.to_dict(),'runs':[]}
    for mode,name in [('NORMAL','verification_healthy_simulated'),('ANOMALY','verification_reduced_stiffness_simulated')]:
        sim.mode=mode
        # Allow the one-second RMS window and EMA to respond to a mode change.
        for i in range(300):
            s=sim.sample()
            if i%10==0:detector.evaluate(s['force_n'],s['strain_delta'],s['accel_rms'])
        logger.start(name,{'simulation':True,'accelerated_verification':True,'baseline':baseline.to_dict()})
        scores=[];statuses=[]
        for i in range(1600):
            s=sim.sample()
            if i%10:continue
            s.update(detector.evaluate(s['force_n'],s['strain_delta'],s['accel_rms']))
            s.update(timestamp=datetime.now(timezone.utc).isoformat(),source='verification_demo')
            logger.write(s);scores.append(s['health_score']);statuses.append(s['status'])
        logger.stop()
        result['runs'].append(dict(mode=mode,file=logger.filename,samples=len(scores),min_health=min(scores),max_health=max(scores),statuses=sorted(set(statuses))))
    assert result['runs'][0]['min_health']>=90,result
    assert result['runs'][0]['statuses']==['NORMAL'],result
    # With little applied load, the strain change is less distinguishable from
    # the noise floor. Low-force WARNING and high-force ANOMALY are expected.
    assert result['runs'][1]['max_health']<=55,result
    assert result['runs'][1]['min_health']<10,result
    assert set(result['runs'][1]['statuses']) <= {'WARNING','STRUCTURAL ANOMALY'},result
    assert 'STRUCTURAL ANOMALY' in result['runs'][1]['statuses'],result
    (DATA_DIR/'verification_report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
