#pragma once
// Arduino-independent measured-response model; also exercised by host tests.
#include <cmath>
#include <algorithm>
#include "Config.h"
namespace SkySafe {
struct Fit {
  double k=0,b=0,residualStd=0,rSquared=0,forceMin=0,forceMax=0;
  int samples=0;
};
struct Regression {
  int n=0; double sx=0,sy=0,sxx=0,sxy=0,syy=0,lo=1e30,hi=-1e30;
  void add(double x,double y) {++n;sx+=x;sy+=y;sxx+=x*x;sxy+=x*y;syy+=y*y;lo=std::min(lo,x);hi=std::max(hi,x);}
  bool fit(Fit& f,bool quality=true) const {
    if(n<Config::MIN_BASELINE_SAMPLES || hi-lo<Config::MIN_FORCE_SPAN_N) return false;
    double xx=sxx-sx*sx/n,xy=sxy-sx*sy/n,yy=syy-sy*sy/n;
    if(xx<=1e-9) return false;
    double sse=std::max(0.0,yy-xy*xy/xx),r2=yy>1e-9?1-sse/yy:0;
    if(quality && (std::abs(xy/xx)<1e-6 || r2<Config::MIN_R_SQUARED)) return false;
    f.k=xy/xx;f.b=(sy-f.k*sx)/n;f.residualStd=std::sqrt(sse/(n-2));
    f.rSquared=r2;f.samples=n;f.forceMin=lo;f.forceMax=hi;return true;
  }
};
struct Baseline {
  double k=0,b=0,residualStd=0,vibrationMean=0,vibrationStd=0;
  double forceMin=0,forceMax=0,rSquared=0;int samples=0;
  bool strainAvailable=false,vibrationAvailable=false,deflectionAvailable=false,vibrationFitAvailable=false;
  Fit deflection,vibrationFit;
};
struct Result {
  const char* status="NEEDS_BASELINE";
  bool rated=false,expectedAvailable=false,deflectionAvailable=false,strainUsed=false,vibrationUsed=false;
  double expected=0,deviation=0,strainRatio=0,vibrationRatio=0,anomaly=0;
  double expectedDeflection=0,deflectionRatio=0,stiffness=0,strainPercent=0,deflectionPercent=0;
  bool stiffnessAvailable=false,strainPercentAvailable=false,deflectionPercentAvailable=false;
  int health=0;
};
class ResponseModel {
 public:
  Baseline baseline;bool ready=false,collecting=false;int count=0;
  void reset() {ready=false;collecting=false;count=0;smoothed=0;strainStats=Regression();tipStats=Regression();vibStats=Regression();baseline=Baseline();lo=1e30;hi=-1e30;}
  void start() {reset();collecting=true;}
  const char* stop() {
    if(!collecting) return "Start a healthy baseline sweep first.";
    if(count<Config::MIN_BASELINE_SAMPLES) return "Need at least 60 samples; keep sweeping.";
    if(hi-lo<Config::MIN_FORCE_SPAN_N) return "Sweep at least 4 N; constant load cannot establish stiffness.";
    Fit sf;
    baseline.strainAvailable=strainStats.fit(sf);
    baseline.deflectionAvailable=tipStats.fit(baseline.deflection) && baseline.deflection.k>0;
    if(!baseline.strainAvailable && !baseline.deflectionAvailable) return "Poor force/response fit; check sensors and repeat a healthy sweep.";
    baseline.k=sf.k;baseline.b=sf.b;baseline.residualStd=sf.residualStd;baseline.rSquared=sf.rSquared;
    baseline.vibrationAvailable=vibStats.n>=Config::MIN_BASELINE_SAMPLES;
    if(vibStats.n) {
      baseline.vibrationMean=vibStats.sy/vibStats.n;
      baseline.vibrationStd=std::sqrt(std::max(0.0,vibStats.syy-vibStats.sy*vibStats.sy/vibStats.n)/std::max(1,vibStats.n-1));
    }
    baseline.vibrationFitAvailable=vibStats.fit(baseline.vibrationFit,false);
    baseline.forceMin=baseline.strainAvailable?sf.forceMin:baseline.deflection.forceMin;
    baseline.forceMax=baseline.strainAvailable?sf.forceMax:baseline.deflection.forceMax;
    if(baseline.strainAvailable && baseline.deflectionAvailable) {
      baseline.forceMin=std::max(sf.forceMin,baseline.deflection.forceMin);
      baseline.forceMax=std::min(sf.forceMax,baseline.deflection.forceMax);
    }
    if(baseline.forceMax-baseline.forceMin<Config::MIN_FORCE_SPAN_N) return "Sensor fits need a shared load envelope of at least 4 N.";
    baseline.samples=count;
    collecting=false;ready=true;smoothed=0;return nullptr;
  }
  void rebase(double forceShift,double strainShift,double tipShift) {
    if(ready) {
      baseline.b+=baseline.k*forceShift+strainShift;baseline.forceMin-=forceShift;baseline.forceMax-=forceShift;
      baseline.deflection.b+=baseline.deflection.k*forceShift+tipShift;
      baseline.deflection.forceMin-=forceShift;baseline.deflection.forceMax-=forceShift;
      baseline.vibrationFit.b+=baseline.vibrationFit.k*forceShift;
      baseline.vibrationFit.forceMin-=forceShift;baseline.vibrationFit.forceMax-=forceShift;
    }
    smoothed=0;
  }
  Result evaluate(double force,double strain,double vibration,bool valid,bool calibrated,
                  double tip=NAN,bool strainValid=true,bool vibrationValid=true) {
    Result r;
    if(!valid || !std::isfinite(force) || (strainValid && !std::isfinite(strain)) || (vibrationValid && !std::isfinite(vibration))) {r.status="SENSOR_FAULT";return r;}
    if(!calibrated) {r.status="NEEDS_CALIBRATION";return r;}
    if(collecting) {
      if(count<Config::MAX_BASELINE_SAMPLES && (strainValid || std::isfinite(tip))) {
        ++count;lo=std::min(lo,force);hi=std::max(hi,force);
        if(strainValid) strainStats.add(force,strain);
        if(vibrationValid) vibStats.add(force,vibration);
        if(std::isfinite(tip)) tipStats.add(force,tip);
      }
      r.status="CALIBRATING";return r;
    }
    if(!ready) return r;
    if(baseline.strainAvailable && strainValid) {
      r.expectedAvailable=true;r.expected=baseline.k*force+baseline.b;r.deviation=std::abs(strain-r.expected);
    }
    if(force<baseline.forceMin-Config::RANGE_MARGIN_N || force>baseline.forceMax+Config::RANGE_MARGIN_N) {r.status="OUT_OF_RANGE";return r;}
    double total=0,weight=0;
    if(r.expectedAvailable) {
      double tolerance=std::max(Config::STRAIN_FLOOR_COUNTS,Config::NOISE_MULTIPLIER*baseline.residualStd)+Config::STRAIN_RELATIVE_TOLERANCE*std::abs(r.expected);
      r.strainRatio=r.deviation/tolerance;r.strainUsed=true;
      r.strainPercentAvailable=std::abs(r.expected)>Config::STRAIN_FLOOR_COUNTS;
      if(r.strainPercentAvailable) r.strainPercent=100*(strain-r.expected)/std::abs(r.expected);
      total+=Config::STRAIN_WEIGHT*std::min(r.strainRatio,2.0);weight+=Config::STRAIN_WEIGHT;
    }
    const Fit& df=baseline.deflection;
    if(baseline.deflectionAvailable && std::isfinite(tip) && force>=df.forceMin-Config::RANGE_MARGIN_N && force<=df.forceMax+Config::RANGE_MARGIN_N) {
      r.deflectionAvailable=true;r.expectedDeflection=df.k*force+df.b;
      r.deflectionRatio=std::abs(tip-r.expectedDeflection)/(std::max(Config::DEFLECTION_FLOOR_MM,Config::NOISE_MULTIPLIER*df.residualStd)+Config::DEFLECTION_RELATIVE_TOLERANCE*std::abs(r.expectedDeflection));
      r.stiffnessAvailable=tip-df.b>Config::DEFLECTION_FLOOR_MM && force>0;
      if(r.stiffnessAvailable) r.stiffness=force/(tip-df.b);
      r.deflectionPercentAvailable=std::abs(r.expectedDeflection)>Config::DEFLECTION_FLOOR_MM;
      if(r.deflectionPercentAvailable) r.deflectionPercent=100*(tip-r.expectedDeflection)/std::abs(r.expectedDeflection);
      total+=Config::STRAIN_WEIGHT*std::min(r.deflectionRatio,2.0);weight+=Config::STRAIN_WEIGHT;
    }
    if(weight==0) {r.status="SENSOR_FAULT";return r;}
    if(baseline.vibrationAvailable && vibrationValid) {
      r.vibrationUsed=true;r.vibrationRatio=std::abs(vibration-baseline.vibrationMean)/std::max(Config::VIBRATION_FLOOR,Config::NOISE_MULTIPLIER*baseline.vibrationStd);
      total+=(1-Config::STRAIN_WEIGHT)*std::min(r.vibrationRatio,2.0);weight+=1-Config::STRAIN_WEIGHT;
    }
    double raw=50*total/weight;smoothed+=Config::SCORE_SMOOTHING_ALPHA*(raw-smoothed);
    r.anomaly=smoothed;r.health=static_cast<int>(std::round(100-smoothed));r.rated=true;
    r.status=smoothed>=Config::ANOMALY_SCORE?"STRUCTURAL ANOMALY":smoothed>=Config::WARNING_SCORE?"WARNING":"NORMAL";return r;
  }
 private:
  Regression strainStats,tipStats,vibStats;double smoothed=0,lo=1e30,hi=-1e30;
};
}
