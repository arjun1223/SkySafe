import csv
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import threading
import select
import unittest
from pathlib import Path
from unittest.mock import patch
from dashboard.anomaly_detection import Detector
from dashboard.app import create_app
from dashboard.engine import Engine
from dashboard.serial_reader import parse_message, SerialReader
from dashboard.simulator import Simulator, VibrationWindow
from dashboard.data_logging import RunLogger, COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def healthy_model():
    detector = Detector()
    detector.start()
    for i in range(120):
        f = 1 + 12 * i / 119
        detector.evaluate(f,80*f + math.sin(i)*5,.125 + .005*math.cos(i))
    detector.stop()
    return detector


def device_message():
    detector = healthy_model()
    sim = Simulator()
    for _ in range(100):
        sample = sim.sample()
    sample.update(detector.evaluate(7,560,.125))
    sample.update(type="sample", force_n=7, strain_delta=560, sensors_ok=True,
                  baseline_state=detector.state())
    return sample


class DetectorTests(unittest.TestCase):
    def test_no_baseline_is_unrated(self):
        result = Detector().evaluate(5,400,.13)
        self.assertEqual(result['status'],'NEEDS_BASELINE')
        self.assertIsNone(result['health_score'])

    def test_fit_and_healthy_score(self):
        d = healthy_model()
        self.assertAlmostEqual(d.baseline.k,80,delta=.2)
        self.assertGreater(d.baseline.r_squared,.999)
        for _ in range(30): result=d.evaluate(7,560,.125)
        self.assertEqual(result['status'],'NORMAL')
        self.assertGreaterEqual(result['health_score'],95)

    def test_damage_and_recovery(self):
        d=healthy_model()
        for _ in range(30): result=d.evaluate(7,868,.51)
        self.assertEqual(result['status'],'STRUCTURAL ANOMALY')
        self.assertLess(result['health_score'],25)
        for _ in range(30): result=d.evaluate(7,560,.125)
        self.assertEqual(result['status'],'NORMAL')
        self.assertGreater(result['health_score'],95)

    def test_warning(self):
        d=healthy_model()
        expected=d.baseline.k*7+d.baseline.b
        tolerance=50+.1*abs(expected)
        for _ in range(30): result=d.evaluate(7,expected+tolerance,.125)
        self.assertEqual(result['status'],'WARNING')

    def test_insufficient_samples(self):
        d=Detector();d.start()
        for i in range(30):d.evaluate(i,80*i,.1)
        with self.assertRaisesRegex(ValueError,'at least'):d.stop()
        self.assertTrue(d.collecting)

    def test_constant_force_rejected(self):
        d=Detector();d.start()
        for _ in range(80):d.evaluate(7,560,.1)
        with self.assertRaisesRegex(ValueError,'Sweep'):d.stop()

    def test_poor_fit_rejected(self):
        d=Detector();d.start()
        for i in range(80):d.evaluate(i/5,(-1)**i*300,.1)
        with self.assertRaisesRegex(ValueError,'Poor'):d.stop()

    def test_negative_slope_supported(self):
        d=Detector();d.start()
        for i in range(80):d.evaluate(i/5,-80*i/5,.1)
        d.stop();self.assertEqual(d.evaluate(7,-560,.1)['status'],'NORMAL')

    def test_invalid_sensor_and_nan_not_scored(self):
        d=healthy_model()
        for kwargs in [dict(valid=False),dict(calibrated=False)]:
            self.assertIsNone(d.evaluate(7,560,.1,**kwargs)['health_score'])
        self.assertEqual(d.evaluate(float('nan'),560,.1)['status'],'SENSOR_FAULT')

    def test_out_of_range_is_unrated(self):
        result=healthy_model().evaluate(16,1280,.1)
        self.assertEqual(result['status'],'OUT_OF_RANGE')
        self.assertIsNone(result['health_score'])
        self.assertIsNotNone(result['expected_strain'])

    def test_reset_and_capacity(self):
        d=Detector();d.start()
        for i in range(700):d.evaluate(i%100,80*(i%100),.1)
        self.assertEqual(len(d.samples),600)
        d.stop();d.reset()
        self.assertIsNone(d.baseline)
        self.assertEqual(len(d.samples),0)

    def test_firmware_model_matches_python(self):
        compiler=shutil.which('clang++') or shutil.which('g++')
        if not compiler:self.skipTest('No native C++ compiler installed')
        rows=[(1+12*i/119,80*(1+12*i/119)+5*math.sin(i),.125+.005*math.cos(i)) for i in range(120)]
        checks=[(7,560,.125)]*10+[(7,868,.51)]*30+[(7,560,.125)]*30+[(16,1280,.125)]
        d=Detector();d.start()
        for row in rows:d.evaluate(*row)
        d.stop()
        with tempfile.TemporaryDirectory() as temp:
            binary=Path(temp)/'model'
            subprocess.run([compiler,'-std=c++11','-Wall','-Wextra',str(ROOT/'tests/model_runner.cpp'),'-o',str(binary)],check=True,capture_output=True,text=True)
            data=f'{len(rows)}\n'+''.join(' '.join(map(str,row))+'\n' for row in rows)+f'{len(checks)}\n'+''.join(' '.join(map(str,row))+'\n' for row in checks)
            lines=subprocess.run([str(binary)],input=data,check=True,capture_output=True,text=True).stdout.splitlines()
        values=list(map(float,lines[0].split()))
        python_values=[d.baseline.k,d.baseline.b,d.baseline.residual_std,d.baseline.vibration_mean,d.baseline.vibration_std,d.baseline.r_squared]
        for a,b in zip(values,python_values):self.assertAlmostEqual(a,b,places=7)
        for row,line in zip(checks,lines[1:]):
            result=d.evaluate(*row);parts=line.split(maxsplit=5)
            self.assertEqual(parts[5],result['status'])
            if result['health_score'] is not None:
                self.assertEqual(int(parts[3]),result['health_score'])
                self.assertAlmostEqual(float(parts[2]),result['anomaly_score'],places=7)


class SimulatorTests(unittest.TestCase):
    def test_same_force_when_damage_changes(self):
        a,b=Simulator(),Simulator();b.mode='ANOMALY'
        for _ in range(500):
            healthy,damage=a.sample(),b.sample()
            self.assertEqual(healthy['force_n'],damage['force_n'])
        self.assertGreater(damage['strain_delta'],healthy['strain_delta']*1.4)
        self.assertGreater(damage['accel_rms'],healthy['accel_rms']*3)

    def test_simulated_baseline_and_anomaly(self):
        sim=Simulator();d=Detector()
        for _ in range(100):sim.sample()
        d.start()
        for i in range(1700):
            sample=sim.sample()
            if i%10==0:d.evaluate(sample['force_n'],sample['strain_delta'],sample['accel_rms'])
        b=d.stop();self.assertAlmostEqual(b.k,80,delta=.5)
        for i in range(200):
            sample=sim.sample()
            if i%10==0:result=d.evaluate(sample['force_n'],sample['strain_delta'],sample['accel_rms'])
        self.assertEqual(result['status'],'NORMAL')
        sim.mode='ANOMALY'
        for i in range(500):
            sample=sim.sample()
            if i%10==0:result=d.evaluate(sample['force_n'],sample['strain_delta'],sample['accel_rms'])
        self.assertEqual(result['status'],'STRUCTURAL ANOMALY')

    def test_zero_requires_unloaded_wing(self):
        sim=Simulator()
        with self.assertRaisesRegex(ValueError,'Unload'):sim.zero()
        sim.auto_force=False;sim.manual_force=0;sim.zero()
        self.assertFalse(sim.window.ready)

    def test_gravity_removed(self):
        window=VibrationWindow()
        for _ in range(200):accel,rms,peak=window.add((0,0,9.80665))
        self.assertTrue(window.ready)
        self.assertEqual((accel,rms,peak),(0,0,0))


class SerialTests(unittest.TestCase):
    def test_parse_valid_telemetry_and_ack(self):
        sample=device_message()
        self.assertEqual(parse_message(json.dumps(sample))['status'],'NORMAL')
        self.assertTrue(parse_message('{"type":"ack","command":"ZERO","ok":true}')['ok'])

    def test_bad_lines_rejected(self):
        for bad in ['not JSON','[]','{}','{"type":"ack","command":"ZERO","ok":"yes"}']:
            with self.assertRaises(ValueError):parse_message(bad)
        for field,value in [('force_n',float('nan')),('accel_rms',None),('health_score',101),('sensors_ok',False),('baseline_state',None)]:
            msg=device_message();msg[field]=value
            with self.assertRaises(ValueError):parse_message(json.dumps(msg))

    def test_fragmentation_long_lines_and_recovery(self):
        msg=json.dumps(device_message()).encode()+b'\n'
        chunks=[msg[:40],msg[40:],b'x'*5000+b'\n'+msg]
        class FakePort:
            in_waiting=16384
            def read(self,n):return chunks.pop(0) if chunks else b''
            def close(self):pass
        reader=SerialReader.__new__(SerialReader)
        reader.port=FakePort();reader.buffer=bytearray();reader.discard_line=False;reader.errors=0
        self.assertEqual(reader.read(),[])
        self.assertEqual(len(reader.read()),1)
        self.assertEqual(len(reader.read()),1)
        self.assertEqual(reader.errors,1)

    @unittest.skipUnless(os.name=='posix','Virtual serial pair requires POSIX')
    def test_real_pyserial_virtual_device(self):
        import pty
        master,slave=pty.openpty()
        try:
            reader=SerialReader(os.ttyname(slave))
            writer=threading.Thread(target=os.write,args=(master,json.dumps(device_message()).encode()+b'\n'),daemon=True)
            writer.start()
            received=[];end=time.monotonic()+1
            while not received and time.monotonic()<end:
                received=reader.read();time.sleep(.01)
            self.assertEqual(received[0]['status'],'NORMAL')
            reader.send('BASELINE_START')
            self.assertTrue(select.select([master],[],[],1)[0], 'Serial command not received')
            self.assertIn(b'BASELINE_START\n',os.read(master,100))
            writer.join(timeout=1)
            reader.close()
        finally:os.close(master);os.close(slave)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.engine=Engine(self.temp.name)
        self.app=create_app(self.engine)
        self.client=self.app.test_client()
    def tearDown(self):
        self.engine.close();self.temp.cleanup()
    def post(self,path,data):return self.client.post(path,json=data)

    def test_page_plotly_and_initial_state(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/static/vendor/plotly.min.js').status_code,200)
        self.assertIsNone(self.client.get('/api/state').json['latest'])

    def test_validation_and_cross_origin(self):
        for path,data in [('/api/source',{'source':'bad'}),('/api/command',{'command':[]}),('/api/command',{'command':'CALIBRATE'}),('/api/demo',{'mode':'INVALID'}),('/api/demo',{'force':'NaN'}),('/api/demo',{'auto_force':'yes'}),('/api/demo',{'prepare':'yes'}),('/api/demo',{'unknown':1})]:
            self.assertEqual(self.post(path,data).status_code,400)
        self.assertEqual(self.client.post('/api/demo',json={},headers={'Origin':'https://other.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/demo',data='{}').status_code,415)

    def test_zero_resets_baseline_and_unloads(self):
        self.engine.detector=healthy_model()
        self.assertEqual(self.post('/api/command',{'command':'ZERO'}).status_code,400)
        self.post('/api/demo',{'auto_force':False,'force':0})
        self.assertEqual(self.post('/api/command',{'command':'ZERO'}).status_code,200)
        self.assertIsNone(self.engine.detector.baseline)

    def test_damaged_simulation_cannot_define_healthy_baseline(self):
        self.engine.simulator.mode='ANOMALY'
        self.assertEqual(self.post('/api/command',{'command':'BASELINE_START'}).status_code,400)
        self.engine.simulator.mode='NORMAL'
        for _ in range(100):self.engine.simulator.sample()
        self.assertEqual(self.post('/api/demo',{'prepare':True}).status_code,200)
        self.assertEqual(self.post('/api/demo',{'mode':'ANOMALY'}).status_code,400)
        self.assertEqual(self.engine.simulator.mode,'NORMAL')

    def test_stale_serial_never_healthy(self):
        self.engine.source='serial';self.engine.latest=device_message();self.engine.last_received=time.monotonic()-3
        state=self.client.get('/api/state').json
        self.assertEqual(state['latest']['status'],'SENSOR_FAULT')
        self.assertIsNone(state['latest']['health_score'])

    def test_csv_runs_unique_and_downloadable(self):
        for _ in range(2):
            self.assertEqual(self.post('/api/runs/start',{'name':'healthy / wing'}).status_code,200)
            sample=device_message();sample.update(timestamp='2026-10-10T12:00:00+00:00',source='demo',load_raw=179238)
            self.engine.logger.write(sample)
            self.post('/api/runs/stop',{})
        files=self.client.get('/api/runs').json['files']
        self.assertEqual(len(files),2)
        self.assertNotEqual(files[0]['name'],files[1]['name'])
        response=self.client.get('/api/runs/'+files[0]['name'])
        self.assertEqual(response.status_code,200)
        response.close()
        with (Path(self.temp.name)/files[0]['name']).open() as file:
            rows=list(csv.DictReader(file));self.assertEqual(len(rows),1);self.assertEqual(list(rows[0]),COLUMNS)
            self.assertEqual(rows[0]['load_raw'],'179238')
        self.assertTrue((Path(self.temp.name)/files[0]['name']).with_suffix('.json').exists())

    def test_cannot_mix_sources_in_recording(self):
        self.post('/api/runs/start',{'name':'healthy'})
        self.assertEqual(self.post('/api/source',{'source':'demo'}).status_code,400)

    def test_pending_serial_acknowledgement(self):
        with patch('dashboard.engine.SerialReader') as transport:
            self.engine.switch_source('serial','virtual-test-port')
            self.engine.last_received=time.monotonic()
            self.assertEqual(self.post('/api/command',{'command':'ZERO'}).status_code,200)
            transport.return_value.send.assert_called_once_with('ZERO')
            self.assertEqual(self.post('/api/command',{'command':'BASELINE_START'}).status_code,400)
            self.assertEqual(self.engine.snapshot()['pending'],'ZERO')

    def test_serial_ack_and_timeout_are_reported(self):
        with patch('dashboard.engine.SerialReader') as transport:
            reader=transport.return_value
            reader.errors=0
            self.engine.switch_source('serial','virtual-test-port')
            self.engine.last_received=time.monotonic()
            self.engine.command('ZERO')
            reader.read.return_value=[dict(type='ack',command='ZERO',ok=True,message='Zero complete')]
            self.engine.start();time.sleep(.05)
            self.assertIsNone(self.engine.pending)
            self.assertEqual(self.engine.last_command['message'],'Zero complete')
            reader.read.return_value=[]
            self.engine.command('BASELINE_START')
            with self.engine.lock:self.engine.pending['deadline']=time.monotonic()-1
            time.sleep(.05)
            self.assertIsNone(self.engine.pending)
            self.assertFalse(self.engine.last_command['ok'])
            self.assertIn('timed out',self.engine.last_command['message'])
            self.engine.close()

    def test_thread_acquires_live_samples(self):
        self.engine.start();time.sleep(1.15)
        state=self.engine.snapshot()
        self.assertTrue(state['connection']['connected'])
        self.assertTrue(state['latest']['sensors_ok'])
        self.assertEqual(state['latest']['status'],'NEEDS_BASELINE')
        self.assertGreaterEqual(len(state['history']),4)  # 5 Hz telemetry, allowing scheduling jitter.


if __name__=='__main__':unittest.main()
