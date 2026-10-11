#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include "Config.h"

// Preserve the existing MPU6050 initialization. Handle the observed 0x70
// identity separately using the MPU6500 register map, without authenticating
// the module's product label or accepting arbitrary unknown sensor IDs.
class SkySafeImu {
  Adafruit_MPU6050 legacy;
  TwoWire* bus=nullptr;
  unsigned char address=0;
  int chipIdentity=-1;
  bool ready=false;
  bool writeRegister(unsigned char reg,unsigned char value) {
    bus->beginTransmission(address);bus->write(reg);bus->write(value);
    return bus->endTransmission()==0;
  }
  bool readRegisters(unsigned char reg,unsigned char* bytes,unsigned char count) {
    bus->beginTransmission(address);bus->write(reg);
    if(bus->endTransmission(false)!=0 || bus->requestFrom(address,count)!=count) return false;
    for(unsigned char i=0;i<count;++i) {
      if(!bus->available()) return false;
      bytes[i]=bus->read();
    }
    return true;
  }
public:
  int identity() const {return chipIdentity;}
  bool begin(unsigned char addr,TwoWire* wire) {
    ready=false;bus=wire;address=addr;chipIdentity=-1;
    unsigned char id;
    if(!readRegisters(0x75,&id,1)) return false;
    chipIdentity=id;
    if(id==0x68) {
      if(!legacy.begin(addr,wire)) return false;
      legacy.setAccelerometerRange(MPU6050_RANGE_4_G);
      legacy.setFilterBandwidth(MPU6050_BAND_21_HZ);
    } else if(id==0x70 && Config::IMU_ALLOW_COMPAT_ID_70) {
      if(!writeRegister(0x6B,0x80)) return false; // Device reset.
      delay(100);
      if(!writeRegister(0x6B,0x01) || !writeRegister(0x6C,0x00) ||
         !writeRegister(0x19,Config::IMU_COMPAT_SAMPLE_DIVIDER) ||
         !writeRegister(0x1A,Config::IMU_COMPAT_FILTER) || !writeRegister(0x1B,0x00) ||
         !writeRegister(0x1C,Config::IMU_ACCEL_RANGE_REGISTER) ||
         !writeRegister(0x1D,Config::IMU_COMPAT_FILTER)) return false;
      delay(100);
    } else return false;
    // Confirm the chip stored the range and is awake; don't scale unverified data.
    unsigned char range,power;
    if(!readRegisters(0x1C,&range,1) || (range&0x18)!=Config::IMU_ACCEL_RANGE_REGISTER ||
       !readRegisters(0x6B,&power,1) || (power&0xC0)) return false;
    ready=true;return true;
  }
  static double decodeAxis(unsigned char high,unsigned char low) {
    int raw=(static_cast<int>(high)<<8)|low;
    if(raw>=32768) raw-=65536;
    return raw*Config::STANDARD_GRAVITY/Config::IMU_COUNTS_PER_G;
  }
  bool readAcceleration(double& x,double& y,double& z) {
    unsigned char bytes[6];
    if(!ready || !readRegisters(0x3B,bytes,6)) return false;
    x=decodeAxis(bytes[0],bytes[1]);y=decodeAxis(bytes[2],bytes[3]);z=decodeAxis(bytes[4],bytes[5]);
    return true;
  }
};
