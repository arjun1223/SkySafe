#pragma once
#include <string>
#include <sstream>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <cstdarg>
#include <vector>
#define PI 3.14159265358979323846
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define INPUT 0
#define CHANGE 2
static unsigned long clockMs=0;
inline unsigned long millis(){return clockMs;}
inline unsigned long micros(){return clockMs*1000;}
inline void delay(unsigned long){}
inline void delayMicroseconds(unsigned long){}
inline void pinMode(int,int){}
inline void digitalWrite(int,int){}
inline long random(long lo,long hi){return lo+std::rand()%(hi-lo);}
class String {
 std::string s;
 public:
 String(const char* v=""):s(v){} String(std::string v):s(v){}
 void trim(){size_t a=s.find_first_not_of(" \t\r\n"),b=s.find_last_not_of(" \t\r\n");s=a==std::string::npos?"":s.substr(a,b-a+1);}
 int indexOf(char c)const{auto p=s.find(c);return p==std::string::npos?-1:static_cast<int>(p);}
 String substring(int a)const{return s.substr(a);} String substring(int a,int b)const{return s.substr(a,b-a);}
 void toUpperCase(){std::transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return std::toupper(c);});}
 size_t length()const{return s.size();} const char* c_str()const{return s.c_str();}
 void reserve(int n){s.reserve(n);} String& operator+=(char c){s+=c;return *this;}
 bool operator==(const char* c)const{return s==c;}
};
struct FakeSerial {
 std::ostringstream buffer;std::string latest;std::vector<std::string> acks;size_t maxBytes=0;
 void begin(unsigned long){} void setTxBufferSize(int){} int available(){return 0;} char read(){return 0;}
 void printf(const char* fmt,...){char out[4096];va_list args;va_start(args,fmt);vsnprintf(out,sizeof(out),fmt,args);va_end(args);buffer<<out;if(std::strlen(out) && out[std::strlen(out)-1]=='\n')finish();}
 template<typename T>void print(T v){buffer<<v;}
 void println(const char* v){buffer<<v<<'\n';finish();}
 void finish(){auto s=buffer.str();if(s.find("\"type\":\"sample\"")!=std::string::npos){latest=s;maxBytes=std::max(maxBytes,s.size());}else acks.push_back(s);buffer.str("");buffer.clear();}
};
static FakeSerial Serial;
