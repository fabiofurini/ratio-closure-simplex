#include "pclp/io.hpp"
#include <cerrno>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <fcntl.h>
#include <unistd.h>
namespace pclp {
Json read_json(const std::string& path){
  std::ifstream in(path);
  if(!in)throw std::invalid_argument("cannot read "+path);
  Json j;in>>j;in>>std::ws;
  if(!in.eof())throw std::invalid_argument("trailing data after JSON object");
  return j;
}
Real parse_number(const Json& j){
  Real value;
  if(j.is_number())value=j.get<Real>();
  else if(j.is_string()){
    auto s=j.get<std::string>();auto slash=s.find('/');
    auto parse=[](const std::string& t){std::size_t end=0;Real v=std::stold(t,&end);if(end!=t.size())throw std::invalid_argument("invalid numeric text");return v;};
    if(slash==std::string::npos)value=parse(s);
    else {Real denominator=parse(s.substr(slash+1));if(denominator==0)throw std::invalid_argument("zero rational denominator");value=parse(s.substr(0,slash))/denominator;}
  }else throw std::invalid_argument("number or decimal/rational string required");
  if(!std::isfinite(value))throw std::invalid_argument("finite number required");
  return value;
}
Instance read_instance(const Json& j){
  if(!j.is_object())throw std::invalid_argument("instance must be a JSON object");
  for(auto it=j.begin();it!=j.end();++it){
    const auto& key=it.key();
    if(key!="format_version"&&key!="id"&&key!="node_ids"&&key!="profit"&&key!="weight"&&key!="arcs"&&key!="capacity"&&key!="capacities"&&key!="source"&&key!="metadata"&&key!="numeric_type")
      throw std::invalid_argument("unsupported instance field: "+key);
  }
  if(j.contains("format_version")&&(!j["format_version"].is_number_integer()||j["format_version"]!=1))throw std::invalid_argument("unsupported format_version");
  for(auto key:{"node_ids","profit","weight","arcs"})if(!j.contains(key)||!j[key].is_array())throw std::invalid_argument(std::string("missing array: ")+key);
  Instance g;g.id=j.value("id","unnamed");
  std::unordered_map<std::string,Index> ids;
  for(auto& id:j["node_ids"]){
    if(!id.is_string()&&!id.is_number_integer())throw std::invalid_argument("node ID must be integer or string");
    auto encoded=id.dump();
    if(!ids.emplace(encoded,g.node_ids.size()).second)throw std::invalid_argument("duplicate node ID");
    g.node_ids.push_back(encoded);
  }
  for(auto& p:j["profit"])g.profit.push_back(parse_number(p));
  for(auto& w:j["weight"])g.weight.push_back(parse_number(w));
  for(auto& a:j["arcs"]){
    if(!a.is_array()||a.size()!=2||!ids.contains(a[0].dump())||!ids.contains(a[1].dump()))throw std::invalid_argument("arc must reference two existing node IDs");
    g.arcs.push_back({ids.at(a[0].dump()),ids.at(a[1].dump())});
  }
  if(j.contains("capacity")){g.capacity=parse_number(j["capacity"]);g.has_capacity=true;}
  if(j.contains("capacities")){
    if(!j["capacities"].is_array())throw std::invalid_argument("capacities must be an array");
    for(auto& c:j["capacities"])if(parse_number(c)<0)throw std::invalid_argument("negative capacity");
  }
  if(j.contains("numeric_type")&&j["numeric_type"]!="integer"&&j["numeric_type"]!="rational"&&j["numeric_type"]!="floating")
    throw std::invalid_argument("unsupported numeric_type");
  validate(g);return g;
}
// Nomi storici accettati in lettura.  I resolved_config.json salvati dalle
// campagne del 6 settembre 2026 scrivono "forest_update": sono il registro di
// cosa e stato eseguito e non vengono riscritti, quindi devono restare
// rileggibili.  La chiave nuova vince solo se quella storica non c'e: se ci
// sono entrambe la configurazione e ambigua ed e un errore.
Json migrate_options(Json j){
  if(!j.is_object())return j;
  if(j.contains("forest_update")){
    if(j.contains("basis_update"))throw std::invalid_argument("configuration sets both basis_update and its legacy name forest_update");
    j["basis_update"]=j["forest_update"];j.erase("forest_update");
  }
  return j;
}
Options read_options(const Json& raw){
  if(!raw.is_object())throw std::invalid_argument("configuration must be an object");
  Json j=migrate_options(raw);
  Json defaults=Options{};
  for(auto it=j.begin();it!=j.end();++it){
    if(!defaults.contains(it.key()))throw std::invalid_argument("unsupported option: "+it.key());
    auto& expected=defaults[it.key()];
    if(expected.is_number_unsigned()&&(!it->is_number_integer()||it->get<Real>()<0))throw std::invalid_argument("nonnegative integer required: "+it.key());
    if(expected.is_boolean()&&!it->is_boolean())throw std::invalid_argument("boolean required: "+it.key());
  }
  Options o=j.get<Options>();validate(o);return o;
}
void write_result(const std::string& path,const Json& j){
  auto data=j.dump(2)+"\n";
  if(path.empty()){std::cout<<data;return;}
  // Same-directory temporary + exclusive hard link: complete output or nothing,
  // with no overwrite of an existing result, even under concurrent writers.
  std::string tmp=path+".incomplete."+std::to_string(getpid());
  int fd=::open(tmp.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
  if(fd<0)throw std::runtime_error("cannot create output temporary: "+std::string(std::strerror(errno)));
  bool closed=false;
  try{
    std::size_t at=0;
    while(at<data.size()){
      auto written=::write(fd,data.data()+at,data.size()-at);
      if(written<0&&errno==EINTR)continue;
      if(written<=0)throw std::runtime_error("output write failed");
      at+=static_cast<std::size_t>(written);
    }
    if(::fsync(fd)!=0)throw std::runtime_error("output sync failed");
    int code=::close(fd);closed=true;
    if(code!=0)throw std::runtime_error("output close failed");
    if(::link(tmp.c_str(),path.c_str())!=0)throw std::runtime_error("cannot publish output (destination may already exist): "+path);
    ::unlink(tmp.c_str());
  }catch(...){if(!closed)::close(fd);::unlink(tmp.c_str());throw;}
}
} // namespace pclp
