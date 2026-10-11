#include <iostream>
#include "../firmware/skysafe_esp32/skysafe_esp32.ino"
void advance(unsigned long duration){unsigned long end=clockMs+duration;while(clockMs<end){++clockMs;loop();}}
void show(){std::cout<<Serial.latest;}
int main(){
  setup();advance(1500);handleCommand("SIM_FORCE 0");advance(2000);
  handleCommand("ZERO");advance(2500);show();
  handleCommand("SIM_AUTO");handleCommand("BASELINE_START");advance(17000);handleCommand("BASELINE_STOP");advance(Config::TELEMETRY_PERIOD_MS);show();
  handleCommand("SIM_FORCE 10");advance(3000);show();
  handleCommand("SIM_ANOMALY");advance(3000);show();
  strainConfigured=false;imuAvailable=false;advance(2000);show();
  loadConfigured=false;advance(Config::TELEMETRY_PERIOD_MS);show();
  loadConfigured=true;strainConfigured=true;imuAvailable=true;
  handleCommand("SIM_FORCE 0");advance(3000);handleCommand("DEMO_ZERO");advance(2500);show();
  handleCommand("SIM_FORCE 10");advance(3000);show();
  for(const auto& ack:Serial.acks)std::cout<<ack;
  std::cout<<"{\"max_frame_bytes\":"<<Serial.maxBytes<<"}\n";
}
