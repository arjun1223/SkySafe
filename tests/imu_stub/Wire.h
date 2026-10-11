#pragma once
#include <array>
#include <vector>
class TwoWire {
  std::vector<unsigned char> tx,rx;
  unsigned char selected=0;
  unsigned int cursor=0;
public:
  std::array<unsigned char,256> registers{};
  bool connected=true,shortRead=false,ignoreRangeWrite=false;
  void beginTransmission(unsigned char){tx.clear();}
  void write(unsigned char b){tx.push_back(b);}
  int endTransmission(bool=true){
    if(!connected)return 2;
    selected=tx.at(0);
    if(tx.size()==2 && !(selected==0x1C && ignoreRangeWrite))registers[selected]=tx[1];
    return 0;
  }
  unsigned char requestFrom(unsigned char,unsigned char count){
    rx.clear();cursor=0;
    unsigned char received=shortRead?count-1:count;
    for(unsigned char i=0;i<received;++i)rx.push_back(registers[selected+i]);
    return received;
  }
  int available(){return rx.size()-cursor;}
  unsigned char read(){return rx.at(cursor++);}
};
