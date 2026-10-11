#pragma once
#include "Wire.h"
#define MPU6050_RANGE_4_G 1
#define MPU6050_BAND_21_HZ 4
class Adafruit_MPU6050 {
  TwoWire* bus=nullptr;
public:
  bool begin(unsigned char,TwoWire* wire){bus=wire;bus->registers[0x6B]=1;return true;}
  void setAccelerometerRange(int){if(!bus->ignoreRangeWrite)bus->registers[0x1C]=8;}
  void setFilterBandwidth(int){}
};
