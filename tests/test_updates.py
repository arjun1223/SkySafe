"""Reliability and measured-response tests for the judging enhancements."""
import csv
import json
import math
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from dashboard.anomaly_detection import Detector
from dashboard.demo_test import DemoTest
from dashboard.engine import Engine
from dashboard.serial_reader import parse_message, SerialReader
from dashboard.simulator import Simulator
from dashboard.ultrasonic import DistanceFilter
from dashboard.app import create_app
from dashboard.config import SERIAL_BAUD, TELEMETRY_HZ
from tests.test_skysafe import healthy_model, device_message

ROOT = Path(__file__).resolve().parents[1]


def baseline(strain=True, vibration=True, tip=True):
    d=Detector();d.start()
    for i in range(120):
        f=1+12*i/119
        d.evaluate(f,80*f if strain else None,.12 if vibration else None,
                   tip_deflection_mm=.8*f if tip else None,
                   strain_valid=strain,vibration_valid=vibration)
    d.stop()
    return d


def sample(d, force=10, altered=False, t=0, strain=True, vibration=True, tip=True):
    s=dict(force_n=force,strain_delta=(124 if altered else 80)*force if strain else None,
           accel_rms=.5 if altered else .12,tip_deflection_mm=(1.4 if altered else .8)*force if tip else None,
           time_ms=t,timestamp='2026-10-10T22:00:00+00:00',simulation=True,zeroed=True,force_calibrated=True)
    if not vibration:s['accel_rms']=None
    s.update(d.evaluate(force,s['strain_delta'],s['accel_rms'],tip_deflection_mm=s['tip_deflection_mm'],
                        strain_valid=strain,vibration_valid=vibration))
    return s


class ResponseTests(unittest.TestCase):
    def test_measured_compliance_stiffness_and_same_force_change(self):
        d=baseline()
        self.assertAlmostEqual(d.baseline.deflection['k'],.8)
        a=d.evaluate(10,800,.12,tip_deflection_mm=8,instantaneous=True)
        b=d.evaluate(10,1240,.5,tip_deflection_mm=14,instantaneous=True)
        self.assertEqual(a['status'],'NORMAL');self.assertEqual(a['health_score'],100)
        self.assertAlmostEqual(a['stiffness_n_per_mm'],1.25)
        self.assertEqual(b['status'],'STRUCTURAL ANOMALY')
        self.assertAlmostEqual(b['strain_deviation_pct'],55)
        self.assertLess(b['stiffness_n_per_mm'],a['stiffness_n_per_mm'])

    def test_optional_disabled_and_failed_tip_do_not_break_mvp(self):
        d=baseline(tip=False)
        self.assertIsNone(d.baseline.deflection)
        for _ in range(20):r=d.evaluate(10,800,.12,tip_deflection_mm=None)
        self.assertEqual(r['status'],'NORMAL')
        self.assertIsNone(r['stiffness_n_per_mm'])
        d=baseline();r=d.evaluate(10,800,.12,tip_deflection_mm=float('nan'))
        self.assertEqual(r['coverage'],['strain','vibration'])
        self.assertIsNotNone(r['health_score'])

    def test_each_secondary_sensor_can_fail(self):
        d=baseline()
        for strain,vibration,tip in [(False,True,True),(True,False,True),(True,True,False),(False,False,True),(True,False,False)]:
            r=sample(d,strain=strain,vibration=vibration,tip=tip)
            self.assertEqual(r['status'],'NORMAL')
            self.assertIsNotNone(r['health_score'])
        r=sample(d,strain=False,tip=False)
        self.assertEqual(r['status'],'SENSOR_FAULT');self.assertIsNone(r['health_score'])
        self.assertIsNone(d.evaluate(10,800,.12,valid=False,tip_deflection_mm=8)['health_score'])

    def test_baseline_without_mpu_or_strain(self):
        d=baseline(strain=False,vibration=False)
        self.assertFalse(d.baseline.strain_available)
        self.assertFalse(d.baseline.vibration_available)
        self.assertEqual(sample(d,strain=False,vibration=False)['coverage'],['deflection'])
        with self.assertRaises(ValueError):baseline(strain=False,vibration=True,tip=False)

    def test_bad_tip_fit_excluded_instead_of_inventing_stiffness(self):
        d=Detector();d.start()
        for i in range(120):
            f=1+i/10;d.evaluate(f,80*f,.12,tip_deflection_mm=4)
        d.stop();self.assertIsNone(d.baseline.deflection)
        self.assertIsNone(d.evaluate(10,800,.12,tip_deflection_mm=4)['stiffness_n_per_mm'])

    def test_rebase_preserves_same_physical_response(self):
        d=baseline();original=d.evaluate(10,800,.12,tip_deflection_mm=8,instantaneous=True)
        d.rebase(force_shift=.1,strain_shift=-20,deflection_shift=.4)
        moved=d.evaluate(9.9,780,.12,tip_deflection_mm=8.4,instantaneous=True)
        self.assertEqual(moved['health_score'],original['health_score'])
        self.assertAlmostEqual(moved['expected_deflection_mm'],8.4)
        self.assertAlmostEqual(d.baseline.deflection['k'],.8)

    def test_distance_filter_rejects_spikes_and_out_of_range(self):
        f=DistanceFilter()
        for _ in range(20):f.add(150)
        self.assertTrue(f.ready)
        self.assertFalse(f.add(float('nan')));self.assertFalse(f.add(10));self.assertFalse(f.add(2000))
        f.add(900);self.assertEqual(f.value,150)
        for _ in range(30):f.add(142)
        self.assertAlmostEqual(150-f.value,8,places=3)

    def test_simulation_optional_filter_and_same_force(self):
        a,b=Simulator(),Simulator();a.ultrasonic_enabled=True;b.ultrasonic_enabled=True;b.mode='ANOMALY'
        a.auto_force=b.auto_force=False;a.manual_force=b.manual_force=10
        for _ in range(300):
            x,y=a.sample(),b.sample();self.assertEqual(x['force_n'],y['force_n'])
        self.assertAlmostEqual(x['tip_deflection_mm'],8,delta=.5)
        self.assertAlmostEqual(y['tip_deflection_mm'],14,delta=.5)
        self.assertAlmostEqual(x['tip_deflection_mm'],a.distance_zero-x['distance_mm'])


class JudgeTests(unittest.TestCase):
    def setUp(self):self.d=baseline();self.test=DemoTest()
    def start(self):self.test.start(self.d.baseline.to_dict(),10,True,None)
    def complete(self,altered=False,strain=True,vibration=True,tip=True):
        for i in range(35):self.test.add(sample(self.d,altered=altered,t=i*100,strain=strain,vibration=vibration,tip=tip),i*.1)

    def test_healthy_and_altered_results_come_from_data(self):
        self.start();self.complete();a=self.test.result
        self.assertEqual(self.test.phase,'COMPLETE');self.assertEqual(a['health_score'],100)
        self.assertAlmostEqual(a['force_n'],10);self.assertAlmostEqual(a['tip_deflection_mm'],8)
        self.test.reset();self.start();self.complete(altered=True)
        self.assertEqual(self.test.result['status'],'STRUCTURAL ANOMALY')
        self.assertLess(self.test.result['health_score'],a['health_score'])
        self.assertAlmostEqual(self.test.result['tip_deflection_mm'],14)

    def test_result_latches_after_release_and_reset_keeps_baseline(self):
        self.start();self.complete();held=self.test.result
        self.test.add(sample(self.d,force=0,t=3000),3)
        self.assertEqual(self.test.result,held)
        self.test.reset();self.assertIsNone(self.test.result);self.assertIsNotNone(self.d.baseline)

    def test_target_validation_and_no_baseline(self):
        for target in [float('nan'),0,-1,50,True,1,13]:
            with self.assertRaises(ValueError):self.test.start(self.d.baseline.to_dict(),target,True,None)
        with self.assertRaises(ValueError):self.test.start(None,10,True,None)
        with self.assertRaises(ValueError):self.test.start(self.d.baseline.to_dict(),10,False,None)
        with self.assertRaises(ValueError):self.test.start(self.d.baseline.to_dict(),10,True,'ZERO')

    def test_unloaded_start_and_ramp_to_target(self):
        self.start()
        for i in range(10):
            self.test.add(sample(self.d,force=i,t=i*100),i*.1)
            self.assertEqual(self.test.phase,'LOADING')
        for i in range(10,45):self.test.add(sample(self.d,t=i*100),i*.1)
        self.assertEqual(self.test.phase,'COMPLETE')
        self.assertEqual(self.test.result['status'],'NORMAL')

    def test_brief_target_hit_is_not_a_result(self):
        self.start()
        for i in range(5):self.test.add(sample(self.d,t=i*100),i*.1)
        self.assertEqual(self.test.phase,'HOLDING');self.assertIsNone(self.test.result)
        self.test.add(sample(self.d,force=8,t=500),.5)
        self.assertEqual(self.test.phase,'LOADING');self.assertEqual(len(self.test.samples),0)

    def test_fault_coverage_change_and_repeated_device_time_interrupt(self):
        for failure in ('force','coverage','clock'):
            self.start();self.test.add(sample(self.d,t=0),0)
            self.test.add(sample(self.d,t=800),.8)
            s=sample(self.d,t=900,strain=failure!='coverage')
            if failure=='force':s['status']='SENSOR_FAULT'
            if failure=='clock':s['time_ms']=800
            self.test.add(s,.9)
            self.assertEqual(self.test.phase,'INTERRUPTED');self.assertIsNone(self.test.result)

    def test_backlogged_serial_cannot_complete_a_hold(self):
        self.start()
        for i in range(30):self.test.add(sample(self.d,t=i*100),0)
        self.assertIsNone(self.test.result)

    def test_limited_sensor_result(self):
        self.start();self.complete(strain=False,vibration=False)
        self.assertEqual(self.test.result['coverage'],['deflection'])
        self.assertIsNone(self.test.result['strain_delta'])


class ReliabilityTests(unittest.TestCase):
    def test_nullable_faulted_sensor_parses_and_missing_force_never_rates(self):
        m=device_message();m['sensor_status']['vibration']='fault'
        for key in ('acceleration','accel_rms','vibration_peak'):m[key]=None
        m['coverage']=['strain']
        self.assertEqual(parse_message(json.dumps(m))['status'],'NORMAL')
        m['sensor_status']['load']='fault';m['force_n']=None
        with self.assertRaises(ValueError):parse_message(json.dumps(m))
        m['status']='SENSOR_FAULT';m['sensors_ok']=False
        self.assertIsNone(parse_message(json.dumps(m))['health_score'])

    def test_old_firmware_without_optional_fields_remains_parseable(self):
        m=device_message()
        for key in ('sensor_status','tip_deflection_mm','distance_mm','coverage'):m.pop(key,None)
        self.assertEqual(parse_message(json.dumps(m))['coverage'],['strain','vibration'])

    def test_invalid_optional_models_and_coverage_rejected(self):
        for value in ('strain',['bad'],['strain','strain']):
            m=device_message();m['coverage']=value
            with self.assertRaises(ValueError):parse_message(json.dumps(m))
        m=device_message();m['baseline_state']['baseline']['deflection']={'k':float('inf')}
        with self.assertRaises(ValueError):parse_message(json.dumps(m))

    def test_demo_api_zero_retains_baseline_and_csv_has_deflection(self):
        with tempfile.TemporaryDirectory() as temp:
            e=Engine(temp);e.detector=baseline();e.simulator.auto_force=False
            c=create_app(e).test_client();before=e.detector.baseline.to_dict()
            self.assertEqual(c.post('/api/test',json={'action':'zero'}).status_code,200)
            self.assertEqual(e.detector.baseline.to_dict(),before)
            m=device_message();m['tip_deflection_mm']=8
            e._ingest(m)
            self.assertEqual(c.post('/api/test',json={'action':'start','target':10}).status_code,200)
            for target in [True,'NaN',None,50]:
                self.assertEqual(c.post('/api/test',json={'action':'start','target':target}).status_code,400 if target is not None else 200)
            e.start_run('enhancement-check');e._ingest(m);name=e.stop_run()['filename']
            with (Path(temp)/name).open() as f:row=list(csv.DictReader(f))[0]
            self.assertEqual(float(row['tip_deflection_mm']),8)
            self.assertEqual(row['demo_target_force_n'],'10')
            e.close()

    def test_reconnect_follows_same_usb_identity_only(self):
        from types import SimpleNamespace
        original=SimpleNamespace(device='/dev/old',serial_number='ESP-123',vid=1,pid=2)
        moved=SimpleNamespace(device='/dev/new',serial_number='ESP-123',vid=1,pid=2)
        other=SimpleNamespace(device='/dev/other',serial_number='ESP-999',vid=1,pid=2)
        with patch('dashboard.serial_reader.list_ports.comports',return_value=[original]):identity=SerialReader.identity('/dev/old')
        with patch('dashboard.serial_reader.list_ports.comports',return_value=[other,moved]):self.assertEqual(SerialReader.resolve_port('/dev/old',identity),'/dev/new')
        with patch('dashboard.serial_reader.list_ports.comports',return_value=[other]):self.assertEqual(SerialReader.resolve_port('/dev/old',identity),'/dev/old')

    def test_disconnect_retry_ack_loss_and_recovery(self):
        with tempfile.TemporaryDirectory() as temp, patch('dashboard.engine.SerialReader') as transport:
            first,second=transport.return_value,unittest.mock.Mock()
            first.read.side_effect=OSError('USB removed');first.errors=0
            second.read.return_value=[];second.errors=0
            transport.side_effect=[first,second]
            e=Engine(temp);e.switch_source('serial','virtual-port');e.last_received=time.monotonic()
            e.command('ZERO');e.start();time.sleep(.05)
            self.assertIsNone(e.reader);self.assertIsNone(e.pending)
            self.assertFalse(e.snapshot()['connection']['connected'])
            with e.lock:e.reconnect_at=0
            time.sleep(.05)
            self.assertIs(e.reader,second);self.assertEqual(transport.call_args.args,('virtual-port',))
            second.read.return_value=[device_message()]
            time.sleep(.05)
            self.assertTrue(e.snapshot()['connection']['connected'])
            e.close()

    def test_stale_stream_interrupts_judge_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            e=Engine(temp);e.source='serial';e.serial_state=baseline().state()
            e.demo_test.start(e.serial_state['baseline'],10,True,None)
            e.last_received=time.monotonic()-3;e.latest=device_message()
            state=e.snapshot()
            self.assertEqual(state['demo_test']['phase'],'INTERRUPTED')
            self.assertIsNone(state['latest']['health_score']);e.close()


class FirmwareTests(unittest.TestCase):
    def test_optional_firmware_model_matches_python(self):
        compiler=shutil.which('clang++') or shutil.which('g++')
        if not compiler:self.skipTest('Native C++ compiler unavailable')
        rows=[];d=Detector();d.start()
        for i in range(120):
            f=1+12*i/119;row=(f,80*f+5*math.sin(i),.125+.005*math.cos(i),.8*f+.2*math.sin(i))
            rows.append(row);d.evaluate(*row[:3],tip_deflection_mm=row[3])
        d.stop()
        checks=[(10,800,.125,8,1,1,1,1)]*10+[(10,1240,.5,14,1,1,1,1)]*30+[(10,1240,.5,14,0,0,1,1)]*10+[(10,800,.125,8,1,0,0,1)]*10+[(10,800,.125,8,1,1,1,0)]
        data=str(len(rows))+'\n'+'\n'.join(' '.join(map(str,r)) for r in rows)+'\n'+str(len(checks))+'\n'+'\n'.join(' '.join(map(str,r)) for r in checks)
        with tempfile.TemporaryDirectory() as temp:
            binary=Path(temp)/'model'
            subprocess.run([compiler,'-std=c++11',str(ROOT/'tests/extended_model_runner.cpp'),'-o',str(binary)],check=True,capture_output=True)
            output=subprocess.check_output([str(binary)],input=data,text=True).splitlines()
        fit=list(map(float,output[0].split()))
        for got,key in zip(fit,('k','b','residual_std','r_squared')):self.assertAlmostEqual(got,d.baseline.deflection[key],places=7)
        for row,line in zip(checks,output[1:]):
            f,s,v,t,sv,vv,tv,valid=row
            expected=d.evaluate(f,s,v,valid=bool(valid),strain_valid=bool(sv),vibration_valid=bool(vv),tip_deflection_mm=t if tv else None)
            parts=line.split(' ',3)
            self.assertEqual(parts[3],expected['status'])
            if expected['health_score'] is not None:
                self.assertEqual(int(parts[1]),expected['health_score'])
                self.assertAlmostEqual(float(parts[0]),expected['anomaly_score'],places=7)

    def test_actual_sketch_json_zeroing_baseline_and_sensor_failures(self):
        compiler=shutil.which('clang++') or shutil.which('g++')
        if not compiler:self.skipTest('Native C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as temp:
            binary=Path(temp)/'firmware'
            subprocess.run([compiler,'-std=c++11','-Wall','-Wextra','-DSIMULATION_MODE=1','-DSKYSAFE_ULTRASONIC=1',
                            '-I',str(ROOT/'tests/arduino_stub'),str(ROOT/'tests/firmware_runner.cpp'),
                            '-o',str(binary)],check=True,capture_output=True,text=True)
            lines=subprocess.check_output([str(binary)],text=True,timeout=10).splitlines()
        messages=[json.loads(line) for line in lines]
        frames=[parse_message(line) for line in lines if json.loads(line).get('type')=='sample']
        zero,base,healthy,altered,partial,fault,re_zero,re_altered=frames
        self.assertTrue(zero['zeroed']);self.assertAlmostEqual(zero['tip_deflection_mm'],0,delta=.6)
        self.assertIsNotNone(base['baseline_state']['baseline']['deflection'])
        self.assertEqual(healthy['status'],'NORMAL')
        self.assertEqual(altered['status'],'STRUCTURAL ANOMALY')
        self.assertEqual(partial['coverage'],['deflection']);self.assertEqual(partial['sensor_status']['strain'],'fault')
        self.assertIsNone(partial['strain_delta']);self.assertIsNotNone(partial['health_score'])
        self.assertEqual(fault['status'],'SENSOR_FAULT');self.assertIsNone(fault['force_n']);self.assertIsNone(fault['health_score'])
        self.assertAlmostEqual(base['baseline_state']['baseline']['deflection']['k'],re_zero['baseline_state']['baseline']['deflection']['k'])
        self.assertEqual(re_altered['status'],'STRUCTURAL ANOMALY')
        self.assertTrue(any(m.get('command')=='DEMO_ZERO' and m['ok'] for m in messages))
        self.assertLess(messages[-1]['max_frame_bytes'],4096)
        self.assertLess(messages[-1]['max_frame_bytes']*TELEMETRY_HZ,SERIAL_BAUD/10)


if __name__=='__main__':unittest.main()
