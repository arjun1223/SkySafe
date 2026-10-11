/* SkySafe — experimental BENCHTOP wing response monitor.
 * USB protocol: one JSON object per line at the baud rate in Config.h.
 * All board pins and thresholds are in Config.h. No pin assumptions.
 * Real sensor dependencies: bogde HX711, Adafruit MPU6050 (+ BusIO,
 * Adafruit Unified Sensor). Simulation builds require only ESP32 core.
 * No OLED is required; the laptop provides the full live display.
 */
#include <Arduino.h>
#include "Config.h"
#include "ResponseModel.h"
#if !SIMULATION_MODE
#include <Wire.h>
#include <HX711.h>
#include "ImuReader.h"
HX711 loadCell, strainBridge;
SkySafeImu mpu;
#endif

SkySafe::ResponseModel model;
long loadRaw=0, strainRaw=0;
double loadOffset=0, strainOffset=0;
double countsPerNewton=SIMULATION_MODE ? 10000.0 : 0.0;
bool zeroed=SIMULATION_MODE, sensorConfigured=SIMULATION_MODE, imuAvailable=SIMULATION_MODE;
bool loadConfigured=SIMULATION_MODE, strainConfigured=SIMULATION_MODE, imuConfigured=SIMULATION_MODE;
bool distanceConfigured=false, distanceZeroed=false, demoZero=false;
int imuIdentity=-1; // Raw WHO_AM_I value; not a claim about the module's label.
double distanceMm=0, unloadedDistanceMm=0, distances[Config::DISTANCE_MEDIAN_SAMPLES]={0};
int distanceCount=0,distanceIndex=0;
unsigned long lastDistance=0,lastTrigger=0,triggerStartUs=0,distanceVersion=0,captureDistanceVersion=0;
double captureDistanceSum=0; int captureDistanceCount=0,captureStrainCount=0;
volatile unsigned long echoStart=0,echoWidth=0;
volatile bool echoDone=false,echoArmed=false;
#if !SIMULATION_MODE
void ARDUINO_ISR_ATTR echoEdge() {
  if(!echoArmed) return;
  if(digitalRead(Config::ULTRASONIC_ECHO)) echoStart=micros();
  else if(echoStart) {echoWidth=micros()-echoStart;echoDone=true;echoArmed=false;}
}
#endif
bool simAnomaly=false, simAutoForce=true;
double simManualForce=0;
unsigned long lastLoad=0,lastStrain=0,lastAccel=0,lastTelemetry=0,lastImuCheck=0;
unsigned long loadVersion=0,strainVersion=0;
double accelX=0,accelY=0,accelZ=9.80665,acceleration=0,accelRms=0,vibrationPeak=0;
double gravity[3]={0,0,9.80665}, vibSamples[Config::VIBRATION_WINDOW]={0};
int vibCount=0,vibIndex=0;
bool gravityInitialized=false;

enum Capture {IDLE, ZERO_CAPTURE, FORCE_CAPTURE};
Capture capture=IDLE;
unsigned long captureStart=0,captureLoadVersion=0,captureStrainVersion=0;
int captureCount=0;
double captureLoadSum=0,captureStrainSum=0,captureLoadSq=0,knownForce=0;
String serialLine;
bool discardCommand=false;

void ack(const char* command, bool ok, const char* message) {
  // Messages are fixed strings without JSON control characters.
  Serial.printf("{\"type\":\"ack\",\"command\":\"%s\",\"ok\":%s,\"message\":\"%s\"}\n",command,ok?"true":"false",message);
}
void resetVibration() {
  vibCount=0; vibIndex=0; gravityInitialized=false;
  for (int i=0;i<Config::VIBRATION_WINDOW;++i) vibSamples[i]=0;
}
void updateVibration(double x,double y,double z) {
  double a[3]={x,y,z};
  if (!gravityInitialized) { for(int i=0;i<3;++i) gravity[i]=a[i]; gravityInitialized=true; }
  double squared=0;
  for(int i=0;i<3;++i) {
    gravity[i]+=Config::GRAVITY_FILTER_ALPHA*(a[i]-gravity[i]);
    const double d=a[i]-gravity[i]; squared+=d*d;
  }
  acceleration=std::sqrt(squared); vibSamples[vibIndex]=acceleration;
  vibIndex=(vibIndex+1)%Config::VIBRATION_WINDOW;
  vibCount=std::min(vibCount+1,Config::VIBRATION_WINDOW);
  double sum=0; vibrationPeak=0;
  for(int i=0;i<vibCount;++i) {sum+=vibSamples[i]*vibSamples[i]; vibrationPeak=std::max(vibrationPeak,vibSamples[i]);}
  accelRms=std::sqrt(sum/vibCount);
}
double forceNow() { return countsPerNewton!=0 ? (loadRaw-loadOffset)/countsPerNewton : 0; }
double simForce(unsigned long now) { return simAutoForce ? 7+6*std::sin(2*PI*now/16000.0) : simManualForce; }
double noise(double amplitude) { return amplitude*(random(-1000,1001)+random(-1000,1001)+random(-1000,1001))/1000.0; }
bool loadFresh(unsigned long now) {
  return loadConfigured && loadVersion>0 && now-lastLoad<=Config::HX_STALE_MS && std::abs(static_cast<double>(loadRaw))<8388000;
}
bool strainFresh(unsigned long now) {
  return strainConfigured && strainVersion>0 && now-lastStrain<=Config::HX_STALE_MS && std::abs(static_cast<double>(strainRaw))<8388000;
}
bool vibrationFresh(unsigned long now) {
  return imuAvailable && vibCount>=Config::VIBRATION_WINDOW && now-lastAccel<100;
}
bool distanceFresh(unsigned long now) {
  return distanceConfigured && distanceCount>=Config::DISTANCE_MEDIAN_SAMPLES && now-lastDistance<=Config::ULTRASONIC_STALE_MS;
}
double tipNow(unsigned long now) {return distanceZeroed && distanceFresh(now)?unloadedDistanceMm-distanceMm:NAN;}
bool hxFresh(unsigned long now) {return loadFresh(now);}
bool sensorsOk(unsigned long now) {return loadFresh(now) && (strainFresh(now) || std::isfinite(tipNow(now)));}
void updateDistance(double mm,unsigned long now) {
  if(!std::isfinite(mm) || mm<Config::ULTRASONIC_MIN_MM || mm>Config::ULTRASONIC_MAX_MM) return;
  distances[distanceIndex]=mm;distanceIndex=(distanceIndex+1)%Config::DISTANCE_MEDIAN_SAMPLES;
  distanceCount=std::min(distanceCount+1,Config::DISTANCE_MEDIAN_SAMPLES);
  double sorted[Config::DISTANCE_MEDIAN_SAMPLES];for(int i=0;i<distanceCount;++i) sorted[i]=distances[i];
  std::sort(sorted,sorted+distanceCount);double median=sorted[distanceCount/2];
  distanceMm=distanceVersion?distanceMm+Config::DISTANCE_FILTER_ALPHA*(median-distanceMm):median;
  ++distanceVersion;lastDistance=now;
}
void readDistance(unsigned long now) {
  if(!distanceConfigured) return;
#if SIMULATION_MODE
  if(now-lastTrigger>=Config::ULTRASONIC_PERIOD_MS) {
    lastTrigger=now;updateDistance(150-simForce(now)*(simAnomaly?Config::SIM_ALTERED_COMPLIANCE:Config::SIM_HEALTHY_COMPLIANCE)+noise(.25),now);
  }
#else
  if(echoDone) {
    noInterrupts();unsigned long width=echoWidth;echoDone=false;interrupts();
    updateDistance(width*Config::SOUND_MM_PER_US/2,now);
  }
  if(echoArmed && micros()-triggerStartUs>Config::ULTRASONIC_TIMEOUT_US) echoArmed=false;
  if(now-lastTrigger>=Config::ULTRASONIC_PERIOD_MS && !echoArmed) {
    lastTrigger=now;triggerStartUs=micros();echoStart=0;echoDone=false;echoArmed=true;
    digitalWrite(Config::ULTRASONIC_TRIG,HIGH);delayMicroseconds(10);digitalWrite(Config::ULTRASONIC_TRIG,LOW);
  }
#endif
}
void readSensors(unsigned long now) {
#if SIMULATION_MODE
  const double force=simForce(now);
  if (now-lastLoad>=100) {
    loadRaw=std::lround(100000+10000*force+noise(90)); strainRaw=std::lround(50000+(simAnomaly?124:80)*force+noise(5));
    lastLoad=lastStrain=now; ++loadVersion; ++strainVersion;
  }
  if (now-lastAccel>=Config::ACCEL_PERIOD_MS) {
    lastAccel=now;
    const double t=now/1000.0, amplitude=(simAnomaly?.70:.16)+.002*force;
    accelX=amplitude*std::sin(2*PI*(simAnomaly?7:11)*t)+noise(.018);
    accelY=.035*std::sin(2*PI*4*t)+noise(.008); accelZ=9.80665+noise(.010);
    updateVibration(accelX,accelY,accelZ);
  }
#else
  if (loadConfigured && loadCell.is_ready()) {loadRaw=loadCell.read();lastLoad=now;++loadVersion;}
  if (strainConfigured && strainBridge.is_ready()) {strainRaw=strainBridge.read();lastStrain=now;++strainVersion;}
  // getEvent can retain data on a failed I2C read; separately probe availability.
  if (imuConfigured && now-lastImuCheck>=1000) {
    lastImuCheck=now; Wire.beginTransmission(Config::MPU_ADDRESS);
    const bool available=Wire.endTransmission()==0;
    if (!available) {imuAvailable=false;resetVibration();}
    else if (!imuAvailable) {
      imuAvailable=mpu.begin(Config::MPU_ADDRESS,&Wire);
      imuIdentity=mpu.identity();
      if (imuAvailable) resetVibration();
    }
  }
  if (imuAvailable && now-lastAccel>=Config::ACCEL_PERIOD_MS) {
    double x,y,z;
    if (mpu.readAcceleration(x,y,z) && std::isfinite(x) && std::isfinite(y) && std::isfinite(z)) {
      lastAccel=now;accelX=x;accelY=y;accelZ=z;
      updateVibration(accelX,accelY,accelZ);
    } else {imuAvailable=false;resetVibration();}
  }
#endif
}
void beginCapture(Capture kind, double force=0) {
  capture=kind; captureStart=millis(); captureCount=0;
  captureLoadSum=captureStrainSum=captureLoadSq=0;
  captureLoadVersion=loadVersion;captureStrainVersion=strainVersion;knownForce=force;
  // A zero or scale change invalidates the previous response model immediately.
  if (!demoZero) model.reset();
  captureDistanceSum=0;captureDistanceCount=0;captureStrainCount=0;captureDistanceVersion=distanceVersion;
}
void updateCapture(unsigned long now) {
  if (capture==IDLE) return;
  const char* cmd=capture==ZERO_CAPTURE?(demoZero?"DEMO_ZERO":"ZERO"):"CALIBRATE";
  if (now-captureStart>Config::CAPTURE_TIMEOUT_MS) {capture=IDLE;ack(cmd,false,"Capture timed out. Check HX711 connections and retry.");return;}
  if(distanceFresh(now) && distanceVersion!=captureDistanceVersion) {
    captureDistanceVersion=distanceVersion;captureDistanceSum+=distanceMm;++captureDistanceCount;
  }
  if(strainFresh(now) && strainVersion!=captureStrainVersion) {
    captureStrainVersion=strainVersion;captureStrainSum+=strainRaw;++captureStrainCount;
  }
  if (!hxFresh(now) || loadVersion==captureLoadVersion) return;
  captureLoadVersion=loadVersion;
  captureLoadSum+=loadRaw;captureLoadSq+=static_cast<double>(loadRaw)*loadRaw;
  if (++captureCount<Config::ZERO_CALIBRATION_SAMPLES) return;
  const double mean=captureLoadSum/captureCount;
  const double sd=std::sqrt(std::max(0.0,captureLoadSq/captureCount-mean*mean));
  if (capture==ZERO_CAPTURE) {
    if (sd>1000) {capture=IDLE;ack(cmd,false,"Load changed during zeroing. Unload and hold still, then retry.");return;}
    const double newStrainOffset=captureStrainCount>=Config::ZERO_CALIBRATION_SAMPLES/2?captureStrainSum/captureStrainCount:strainOffset;
    const double newDistance=captureDistanceCount>=Config::DISTANCE_MEDIAN_SAMPLES?captureDistanceSum/captureDistanceCount:unloadedDistanceMm;
    if(demoZero && countsPerNewton!=0 && std::abs((mean-loadOffset)/countsPerNewton)>.25) {capture=IDLE;ack(cmd,false,"Load changed during demo zero; unload and retry.");return;}
    if(demoZero) model.rebase(countsPerNewton?(mean-loadOffset)/countsPerNewton:0,strainOffset-newStrainOffset,newDistance-unloadedDistanceMm);
    loadOffset=mean;strainOffset=newStrainOffset;zeroed=true;resetVibration();
    distanceZeroed=captureDistanceCount>=Config::DISTANCE_MEDIAN_SAMPLES;
    if(distanceZeroed) unloadedDistanceMm=newDistance;
    capture=IDLE;ack(cmd,true,demoZero?"Demo zero complete; healthy response slopes retained.":"Sensors zeroed. Calibrate force if needed, then establish a new healthy baseline.");
  } else {
    const double delta=mean-loadOffset;
    if (std::abs(delta)<1000 || sd>std::max(500.0,.02*std::abs(delta))) {
      capture=IDLE;ack(cmd,false,"Known load is too small or unstable. Hold a steady known load and retry.");return;
    }
    countsPerNewton=delta/knownForce;capture=IDLE;
    ack(cmd,true,"Force scale calibrated in newtons. Establish a new healthy baseline.");
  }
}
bool numericArgument(const String& value,double& result) {
  if (value.length()==0) return false;
  char* end=nullptr; result=strtod(value.c_str(),&end);
  return end!=value.c_str() && *end=='\0' && std::isfinite(result);
}
void handleCommand(String line) {
  line.trim();const int space=line.indexOf(' ');
  String cmd=space<0?line:line.substring(0,space),arg=space<0?"":line.substring(space+1);
  cmd.toUpperCase();arg.trim();
  if (capture!=IDLE) {ack("BUSY",false,"Wait for the active zero or calibration capture to finish.");return;}
  const unsigned long now=millis();
  if (cmd=="ZERO" || cmd=="DEMO_ZERO") {
    demoZero=cmd=="DEMO_ZERO";
    if(demoZero && model.collecting) {ack("DEMO_ZERO",false,"Finish the baseline before demo zero.");return;}
    if (arg.length()) {ack(cmd.c_str(),false,"ZERO takes no arguments.");return;}
    if (!hxFresh(now)) {ack(cmd.c_str(),false,"No fresh HX711 samples. Check wiring and retry.");return;}
#if SIMULATION_MODE
    if (simForce(now)>.25) {ack(cmd.c_str(),false,"Unload simulated wing with SIM_FORCE 0 before ZERO.");return;}
#endif
    if(demoZero && zeroed && countsPerNewton!=0 && std::abs(forceNow())>.25) {ack("DEMO_ZERO",false,"Unload the wing before demo zero.");return;}
    beginCapture(ZERO_CAPTURE);
  } else if (cmd=="IMU_CHECK") {
#if SIMULATION_MODE
    ack("IMU_CHECK",false,"IMU diagnostics require hardware mode.");
#else
    if (!imuConfigured) {ack("IMU_CHECK",false,"IMU pins are unassigned or disabled.");return;}
    const unsigned char addresses[]={0x68,0x69};
    int errors[2],identity[2]={-1,-1};
    for (int i=0;i<2;++i) {
      Wire.beginTransmission(addresses[i]);errors[i]=Wire.endTransmission();
      if (errors[i]==0) {
        Wire.beginTransmission(addresses[i]);Wire.write(0x75); // WHO_AM_I, read only.
        if (Wire.endTransmission(false)==0 && Wire.requestFrom(addresses[i],static_cast<unsigned char>(1))==1)
          identity[i]=Wire.read();
      }
    }
    char report[128];
    snprintf(report,sizeof(report),"0x68: bus_error=%d identity=%d; 0x69: bus_error=%d identity=%d. Identity -1 means unreadable.",errors[0],identity[0],errors[1],identity[1]);
    ack("IMU_CHECK",errors[0]==0 || errors[1]==0,report);
#endif
  } else if (cmd=="CALIBRATE") {
    double force=0;
    if (!numericArgument(arg,force) || force<=0 || force>Config::MAX_KNOWN_FORCE_N) {ack("CALIBRATE",false,"Use CALIBRATE <known_force_n>, positive and at most 49 N.");return;}
    if (!zeroed || !hxFresh(now)) {ack("CALIBRATE",false,"ZERO unloaded sensors first and wait for fresh readings.");return;}
    demoZero=false;beginCapture(FORCE_CAPTURE,force);
  } else if (cmd=="BASELINE_START") {
#if SIMULATION_MODE
    if(simAnomaly) {ack("BASELINE_START",false,"Select SIM_NORMAL before establishing a healthy baseline.");return;}
#endif
    if (!zeroed || countsPerNewton==0 || !sensorsOk(now)) {ack("BASELINE_START",false,"Zero, calibrate force, and wait for valid sensors before a healthy sweep.");return;}
    model.start();ack("BASELINE_START",true,"Healthy baseline collecting. Sweep your full test load range.");
  } else if (cmd=="BASELINE_STOP") {
    const char* error=model.stop();ack("BASELINE_STOP",error==nullptr,error?error:"Healthy baseline ready.");
  } else if (cmd=="RESET_BASELINE") {
    model.reset();ack("RESET_BASELINE",true,"Baseline reset. Health score is unrated until a new healthy sweep.");
  } else if (cmd=="SIM_NORMAL" || cmd=="SIM_ANOMALY" || cmd=="SIM_FORCE" || cmd=="SIM_AUTO") {
#if SIMULATION_MODE
    if (cmd=="SIM_FORCE") {
      double force=0;if (!numericArgument(arg,force) || force<0 || force>16) {ack("SIM_FORCE",false,"Use SIM_FORCE <0..16> in newtons.");return;}
      simAutoForce=false;simManualForce=force;ack("SIM_FORCE",true,"Manual simulation force set.");
    } else if (cmd=="SIM_AUTO") {simAutoForce=true;ack("SIM_AUTO",true,"Automatic simulation sweep enabled.");}
    else if (cmd=="SIM_NORMAL") {simAnomaly=false;ack("SIM_NORMAL",true,"Healthy wing simulation enabled.");}
    else {
      if(model.collecting) {ack("SIM_ANOMALY",false,"Finish or reset the healthy baseline before switching to reduced stiffness.");return;}
      simAnomaly=true;ack("SIM_ANOMALY",true,"Reduced stiffness simulation enabled at the same load.");
    }
#else
    ack(cmd=="SIM_NORMAL"?"SIM_NORMAL":cmd=="SIM_ANOMALY"?"SIM_ANOMALY":cmd=="SIM_FORCE"?"SIM_FORCE":"SIM_AUTO",false,"Rebuild with SIMULATION_MODE enabled to use virtual sensors.");
#endif
  } else {ack("UNKNOWN",false,"Unknown command. See README for the serial protocol.");}
}
void receiveCommands() {
  // Bounded work per loop to keep accelerometer sampling alive during bad input.
  int budget=128;
  while (Serial.available() && budget-- > 0) {
    const char c=Serial.read();
    if (c=='\n') {
      if (discardCommand) ack("INVALID",false,"Command too long; limit is 80 characters.");
      else if (serialLine.length()) handleCommand(serialLine);
      serialLine="";discardCommand=false;
    } else if (c!='\r' && !discardCommand) {
      serialLine+=c;if (serialLine.length()>80) {serialLine="";discardCommand=true;}
    }
  }
}
void setLed(int pin,bool enabled) {
  if (pin>=0) digitalWrite(pin,enabled==Config::LED_ACTIVE_HIGH?HIGH:LOW);
}
void outputs(const SkySafe::Result& r,unsigned long now) {
  const bool normal=strcmp(r.status,"NORMAL")==0, severe=strcmp(r.status,"STRUCTURAL ANOMALY")==0;
  setLed(Config::GREEN_LED,normal);setLed(Config::RED_LED,severe);
  setLed(Config::YELLOW_LED,!normal && !severe && (r.rated || (now/500)%2));
  if (Config::BUZZER_ENABLED && Config::BUZZER>=0) digitalWrite(Config::BUZZER,severe && (now/200)%2 ? HIGH:LOW);
}
void nullable(double value,bool available) {if(available)Serial.printf("%.6f",value);else Serial.print("null");}
void emitFit(const SkySafe::Fit& f,bool available) {
  if(!available) {Serial.print("null");return;}
  Serial.printf("{\"k\":%.8f,\"b\":%.8f,\"residual_std\":%.8f,\"r_squared\":%.8f,\"samples\":%d,\"force_min\":%.8f,\"force_max\":%.8f}",f.k,f.b,f.residualStd,f.rSquared,f.samples,f.forceMin,f.forceMax);
}
void emitSample(unsigned long now,const SkySafe::Result& r,bool valid) {
  Serial.printf("{\"type\":\"sample\",\"time_ms\":%lu,\"force_n\":",now);nullable(forceNow(),loadFresh(now));
  Serial.printf(",\"load_raw\":%ld,\"strain_raw\":",loadRaw);nullable(strainRaw,strainFresh(now));
  Serial.print(",\"strain_delta\":");nullable(strainRaw-strainOffset,strainFresh(now));
  Serial.print(",\"acceleration\":");nullable(acceleration,vibrationFresh(now));
  Serial.print(",\"accel_rms\":");nullable(accelRms,vibrationFresh(now));
  Serial.print(",\"vibration_peak\":");nullable(vibrationPeak,vibrationFresh(now));
  Serial.printf(",\"accel_x\":%.6f,\"accel_y\":%.6f,\"accel_z\":%.6f,",accelX,accelY,accelZ);
  Serial.printf("\"imu_identity\":%d,",imuIdentity);
  Serial.print("\"tip_deflection_mm\":");nullable(tipNow(now),std::isfinite(tipNow(now)));
  Serial.print(",\"distance_mm\":");nullable(distanceMm,distanceFresh(now));
  Serial.print(",\"expected_deflection_mm\":");nullable(r.expectedDeflection,r.deflectionAvailable);
  Serial.print(",\"deflection_deviation_pct\":");nullable(r.deflectionPercent,r.deflectionPercentAvailable);
  Serial.print(",\"strain_deviation_pct\":");nullable(r.strainPercent,r.strainPercentAvailable);
  Serial.print(",\"stiffness_n_per_mm\":");nullable(r.stiffness,r.stiffnessAvailable);
  Serial.print(",\"baseline_stiffness_n_per_mm\":");nullable(model.baseline.deflection.k>0?1/model.baseline.deflection.k:0,model.ready && model.baseline.deflectionAvailable);
  Serial.print(",\"deflection_ratio\":");nullable(r.deflectionRatio,r.deflectionAvailable);
  Serial.printf(",\"sensor_status\":{\"load\":\"%s\",\"strain\":\"%s\",\"vibration\":\"%s\",\"ultrasonic\":\"%s\"},",Config::LOAD_ENABLED?(loadFresh(now)?"ok":"fault"):"disabled",Config::STRAIN_ENABLED?(strainFresh(now)?"ok":"fault"):"disabled",Config::MPU_ENABLED?(vibrationFresh(now)?"ok":imuAvailable?"settling":"fault"):"disabled",Config::ULTRASONIC_ENABLED?(distanceFresh(now)?distanceZeroed?"ok":"needs_zero":"fault"):"disabled");
  Serial.print("\"coverage\":[");bool comma=false;
  if(r.strainUsed) {Serial.print("\"strain\"");comma=true;}
  if(r.deflectionAvailable) {if(comma)Serial.print(",");Serial.print("\"deflection\"");comma=true;}
  if(r.vibrationUsed) {if(comma)Serial.print(",");Serial.print("\"vibration\"");}
  Serial.print("],");
  Serial.print("\"expected_strain\":");nullable(r.expected,r.expectedAvailable);
  Serial.print(",\"strain_deviation\":");nullable(r.deviation,r.expectedAvailable);
  Serial.print(",\"health_score\":");if(r.rated)Serial.print(r.health);else Serial.print("null");
  Serial.print(",\"anomaly_score\":");nullable(r.anomaly,r.rated);
  Serial.print(",\"strain_ratio\":");nullable(r.strainRatio,r.strainUsed);
  Serial.print(",\"vibration_ratio\":");nullable(r.vibrationRatio,r.vibrationUsed);
  Serial.printf(",\"status\":\"%s\",\"sensors_ok\":%s,\"force_calibrated\":%s,\"zeroed\":%s,\"simulation\":%s,\"simulation_mode\":\"%s\",\"baseline_state\":{\"collecting\":%s,\"samples\":%d,\"capacity\":%d,\"baseline\":",r.status,valid?"true":"false",countsPerNewton!=0?"true":"false",zeroed?"true":"false",SIMULATION_MODE?"true":"false",simAnomaly?"ANOMALY":"NORMAL",model.collecting?"true":"false",model.count,Config::MAX_BASELINE_SAMPLES);
  if (!model.ready) Serial.print("null");
  else {
    const SkySafe::Baseline& b=model.baseline;
    Serial.printf("{\"k\":%.8f,\"b\":%.8f,\"residual_std\":%.8f,\"vibration_mean\":%.8f,\"vibration_std\":%.8f,\"force_min\":%.8f,\"force_max\":%.8f,\"r_squared\":%.8f,\"samples\":%d,\"strain_available\":%s,\"vibration_available\":%s,\"deflection\":",b.k,b.b,b.residualStd,b.vibrationMean,b.vibrationStd,b.forceMin,b.forceMax,b.rSquared,b.samples,b.strainAvailable?"true":"false",b.vibrationAvailable?"true":"false");
    emitFit(b.deflection,b.deflectionAvailable);
    Serial.print(",\"vibration_fit\":");emitFit(b.vibrationFit,b.vibrationFitAvailable);Serial.print("}");
  }
  Serial.println("}}");
}
void setup() {
#if !ARDUINO_USB_CDC_ON_BOOT
  Serial.setTxBufferSize(4096); // Queue full JSON frames without blocking 100 Hz acquisition.
#endif
  Serial.begin(Config::SERIAL_BAUD);serialLine.reserve(84);
  model.reset();
  const int ledPins[]={Config::GREEN_LED,Config::YELLOW_LED,Config::RED_LED};
  for(int pin:ledPins) if(pin>=0) {pinMode(pin,OUTPUT);setLed(pin,false);}
  if(Config::BUZZER_ENABLED && Config::BUZZER>=0) {pinMode(Config::BUZZER,OUTPUT);digitalWrite(Config::BUZZER,LOW);}
#if SIMULATION_MODE
  loadOffset=100000;strainOffset=50000;
  loadConfigured=Config::LOAD_ENABLED;strainConfigured=Config::STRAIN_ENABLED;imuAvailable=Config::MPU_ENABLED;
  distanceConfigured=Config::ULTRASONIC_ENABLED;unloadedDistanceMm=150;distanceZeroed=distanceConfigured;
  ack("BOOT",true,"SkySafe simulation ready. Start a healthy baseline sweep before scoring.");
#else
  // Each sensor is independent; unassigned optional pins do not disable the load cell.
  const int assigned[]={Config::LOAD_ENABLED?Config::LOAD_DOUT:-1,Config::LOAD_ENABLED?Config::LOAD_SCK:-1,
    Config::STRAIN_ENABLED?Config::STRAIN_DOUT:-1,Config::STRAIN_ENABLED?Config::STRAIN_SCK:-1,
    Config::MPU_ENABLED?Config::I2C_SDA:-1,Config::MPU_ENABLED?Config::I2C_SCL:-1,
    Config::ULTRASONIC_ENABLED?Config::ULTRASONIC_TRIG:-1,Config::ULTRASONIC_ENABLED?Config::ULTRASONIC_ECHO:-1};
  bool pinOk[8];
  for(int i=0;i<8;++i) {
    pinOk[i]=assigned[i]>=0;
    for(int j=0;j<8;++j) if(i!=j && assigned[i]>=0 && assigned[i]==assigned[j]) pinOk[i]=false;
    for(int pin:ledPins) if(assigned[i]>=0 && assigned[i]==pin) pinOk[i]=false;
    if(Config::BUZZER_ENABLED && assigned[i]==Config::BUZZER) pinOk[i]=false;
  }
  loadConfigured=pinOk[0] && pinOk[1];strainConfigured=pinOk[2] && pinOk[3];imuConfigured=pinOk[4] && pinOk[5];
  distanceConfigured=pinOk[6] && pinOk[7];sensorConfigured=loadConfigured;
  if(loadConfigured) loadCell.begin(Config::LOAD_DOUT,Config::LOAD_SCK,128);
  if(strainConfigured) strainBridge.begin(Config::STRAIN_DOUT,Config::STRAIN_SCK,128);
  if(imuConfigured) {
    Wire.begin(Config::I2C_SDA,Config::I2C_SCL);Wire.setClock(Config::IMU_I2C_HZ);Wire.setTimeOut(20);
    imuAvailable=mpu.begin(Config::MPU_ADDRESS,&Wire);
    imuIdentity=mpu.identity();
  }
  if(distanceConfigured) {
    pinMode(Config::ULTRASONIC_TRIG,OUTPUT);digitalWrite(Config::ULTRASONIC_TRIG,LOW);
    pinMode(Config::ULTRASONIC_ECHO,INPUT);attachInterrupt(digitalPinToInterrupt(Config::ULTRASONIC_ECHO),echoEdge,CHANGE);
  }
  ack("BOOT",sensorConfigured,"SkySafe hardware mode. Assign Config.h pins, ZERO unloaded sensors, and CALIBRATE with known force.");
#endif
}
void loop() {
  const unsigned long now=millis();
  receiveCommands();readSensors(now);readDistance(now);updateCapture(now);
  if(now-lastTelemetry>=Config::TELEMETRY_PERIOD_MS) {
    lastTelemetry=now;const bool valid=sensorsOk(now);
    SkySafe::Result r;
    if(capture!=IDLE) r.status="ZEROING";
    else r=model.evaluate(forceNow(),strainRaw-strainOffset,accelRms,valid,zeroed && countsPerNewton!=0,tipNow(now),strainFresh(now),vibrationFresh(now));
    outputs(r,now);emitSample(now,r,valid);
  }
  delay(1); // yield to ESP32 watchdog / USB tasks; never waits for HX711 readiness
}
