#include <iostream>
#include <iomanip>
#include "../firmware/skysafe_esp32/ResponseModel.h"
int main() {
  SkySafe::ResponseModel model;
  model.start();
  int n; double f,s,v;
  std::cin>>n;
  for(int i=0;i<n;++i) {std::cin>>f>>s>>v; model.evaluate(f,s,v,true,true);}
  if(const char* error=model.stop()) {std::cerr<<error;return 1;}
  const auto& b=model.baseline;
  std::cout<<std::setprecision(15)<<b.k<<" "<<b.b<<" "<<b.residualStd<<" "<<b.vibrationMean<<" "<<b.vibrationStd<<" "<<b.rSquared<<"\n";
  std::cin>>n;
  for(int i=0;i<n;++i) {
    std::cin>>f>>s>>v;const auto r=model.evaluate(f,s,v,true,true);
    std::cout<<r.expected<<" "<<r.deviation<<" "<<r.anomaly<<" "<<r.health<<" "<<r.rated<<" "<<r.status<<"\n";
  }
}
