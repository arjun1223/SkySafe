#include <cassert>
#include <cmath>
#include "../firmware/skysafe_esp32/ImuReader.h"
int main(){
  for(unsigned char identity:{0x68,0x70}){
    TwoWire wire;wire.registers[0x75]=identity;
    SkySafeImu imu;assert(imu.begin(0x68,&wire));assert(imu.identity()==identity);
    // A measured +1 g/-1 g/zero fixture checks byte order, sign and units.
    wire.registers[0x3B]=0x20;wire.registers[0x3C]=0;
    wire.registers[0x3D]=0xE0;wire.registers[0x3E]=0;
    double x=99,y=99,z=99;assert(imu.readAcceleration(x,y,z));
    assert(std::abs(x-9.80665)<1e-8);assert(std::abs(y+9.80665)<1e-8);assert(z==0);
    wire.shortRead=true;x=y=z=99;
    assert(!imu.readAcceleration(x,y,z));assert(x==99 && y==99 && z==99);
    wire.shortRead=false;wire.connected=false;
    assert(!imu.readAcceleration(x,y,z));
    wire.connected=true;assert(imu.begin(0x68,&wire));
  }
  TwoWire unknown;unknown.registers[0x75]=0x42;
  SkySafeImu rejected;assert(!rejected.begin(0x68,&unknown));
  double x=99,y=99,z=99;assert(!rejected.readAcceleration(x,y,z));
  for(unsigned char identity:{0x68,0x70}){
    TwoWire bad;bad.registers[0x75]=identity;bad.ignoreRangeWrite=true;
    SkySafeImu imu;assert(!imu.begin(0x68,&bad));
  }
  assert(std::abs(SkySafeImu::decodeAxis(0x80,0)+39.2266)<1e-8);
  assert(SkySafeImu::decodeAxis(0xFF,0xFF)<0);
}
