#include <iostream>
#include <iomanip>
#include "../firmware/skysafe_esp32/ResponseModel.h"
int main(){
  SkySafe::ResponseModel m;m.start();int n;double f,s,v,t;bool sv,vv,tv,valid;
  std::cin>>n;
  for(int i=0;i<n;++i){std::cin>>f>>s>>v>>t;m.evaluate(f,s,v,true,true,t);}
  if(const char* error=m.stop()){std::cerr<<error;return 1;}
  const auto& b=m.baseline;
  std::cout<<std::setprecision(17)<<b.deflection.k<<" "<<b.deflection.b<<" "<<b.deflection.residualStd<<" "<<b.deflection.rSquared<<"\n";
  std::cin>>n;
  for(int i=0;i<n;++i){
    std::cin>>f>>s>>v>>t>>sv>>vv>>tv>>valid;
    auto r=m.evaluate(f,s,v,valid,true,tv?t:NAN,sv,vv);
    std::cout<<r.anomaly<<" "<<r.health<<" "<<r.rated<<" "<<r.status<<"\n";
  }
}
