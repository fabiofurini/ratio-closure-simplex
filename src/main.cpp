#include "pclp/io.hpp"
#include "pclp/graph.hpp"
#include "pclp/engine.hpp"
#include "pclp/sha256.hpp"
#include "pclp/build_info.hpp"
#include <algorithm>
#include <iostream>
#include <sys/resource.h>
#include <sys/utsname.h>
using namespace pclp;
int main(int argc,char** argv){
  std::string output_path;
  try{
    if(argc==2&&std::string(argv[1])=="--help"){
      std::cout<<"pclp <inspect|ratio|solve|positive-path|full-path|verify> --instance FILE\n"
        <<"  --capacity C | --capacities JSON_ARRAY   --config FILE   --output FILE\n"
        <<"  --algorithm ratio-closure|closure-simplex|dinkelbach|parametric\n"
        <<"  --basis-update full|local|adaptive      --pricing full|partial|candidate-list\n"
        <<"  --entering-rule bland|first-improving|best-improving|highest-ratio\n"
        <<"  --initial-basis sink|closure|full        --initial-seeds K\n"
        <<"  --ratio-test full|restricted|early       --degeneracy-trigger N\n"
        <<"  --warm-start off|residual              (decomposizione canonica)\n"
        <<"  --canonicalization sequential|dual       --node-order input|topological|seeded --seed N\n"
        <<"  --transitive-reduction off|on            --rebuild-interval N --rebuild-fraction F\n"
        <<"  --pricing-block-size N --candidate-limit N\n"
        <<"  --iteration-limit N --time-limit SECONDS --verify-every N --trace pivots|off\n"
        <<"  verify --result FILE checks saved certificates without optimizing\n";
      return 0;
    }
    if(argc<2)throw std::invalid_argument("task required; use --help");
    std::string task=argv[1],instance_path,config_path,result_path;
    Json overrides=Json::object(),capacities=nullptr;bool has_capacity=false;Real capacity=0;
    Json defaults=Options{};
    for(int i=2;i<argc;++i){
      std::string flag=argv[i];
      if(!flag.starts_with("--")||i+1==argc)throw std::invalid_argument("option and value required: "+flag);
      std::string value=argv[++i],key=flag.substr(2);
      if(key=="instance")instance_path=value;
      else if(key=="output")output_path=value;
      else if(key=="config")config_path=value;
      else if(key=="result")result_path=value;
      else if(key=="capacity"){capacity=parse_number(Json(value));has_capacity=true;}
      else if(key=="capacities"){capacities=Json::parse(value);if(!capacities.is_array()||capacities.empty())throw std::invalid_argument("capacities must be a nonempty JSON array");}
      else{
        std::replace(key.begin(),key.end(),'-','_');
        // Nome storico dell'opzione, accettato come in read_options.
        if(key=="forest_update")key="basis_update";
        if(!defaults.contains(key))throw std::invalid_argument("unknown option: "+flag);
        if(key=="trace"){
          if(value!="pivots"&&value!="off")throw std::invalid_argument("trace must be pivots or off");
          overrides[key]=value=="pivots";
        }else if(defaults[key].is_string())overrides[key]=value;
        else overrides[key]=Json::parse(value);
      }
    }
    if(instance_path.empty())throw std::invalid_argument("--instance required");
    if(has_capacity&&!capacities.is_null())throw std::invalid_argument("choose capacity or capacities");
    if(task!="solve"&&(has_capacity||!capacities.is_null()))throw std::invalid_argument("capacity options apply to solve only");
    Json config=config_path.empty()?Json::object():read_json(config_path);
    if(!config.is_object())throw std::invalid_argument("configuration must be an object");
    // Legacy names in the file are normalised before the command-line overrides,
    // which are already canonical, are merged in: otherwise a legacy file plus a
    // legacy flag would produce both keys and the ambiguity would be spurious.
    config=migrate_options(std::move(config));
    config.update(overrides);Options opt=read_options(config);config=opt;
    auto begin=Clock::now();Json source=read_json(instance_path);Instance g=read_instance(source);
    Real read_seconds=seconds(begin);auto hash=sha256(source.dump());
    Json result;
    if(task=="verify"){
      if(result_path.empty())throw std::invalid_argument("--result required");
      Json saved=read_json(result_path);
      bool ok=saved.value("format_version",0)==1&&saved.value("instance_sha256","")==hash&&saved.value("status","")=="optimal";
      std::string saved_task=saved.value("task","");
      if(ok){
        if(saved_task=="ratio")ok=verify_ratio(g,saved.get<RatioResult>(),opt);
        else if(saved_task=="full-path"||saved_task=="positive-path")ok=verify_path(g,saved.get<PathResult>(),opt);
        else if(saved_task=="solve"){
          if(saved.contains("solutions")){
            ok=saved["solutions"].is_array()&&!saved["solutions"].empty();
            for(auto& solution:saved["solutions"])ok=ok&&verify_solution(g,solution.get<SolveResult>(),opt);
          }else ok=verify_solution(g,saved.get<SolveResult>(),opt);
        }else ok=false;
      }
      result={{"status",ok?"valid":"invalid_certificate"},{"verified_result",result_path}};
    }else if(task=="inspect"){
      Prepared p(g,opt);
      result={{"status","valid"},{"nodes",g.node_ids.size()},{"arcs",g.arcs.size()},
        {"condensed_nodes",p.graph.node_ids.size()},{"condensed_arcs",p.graph.arcs.size()},{"scc_map",p.component}};
    }else if(task=="ratio")result=max_ratio(g,opt);
    else if(task=="full-path"||task=="positive-path")result=decompose(g,task=="positive-path",opt);
    else if(task=="solve"){
      if(!has_capacity&&capacities.is_null()&&!g.has_capacity&&source.contains("capacities"))capacities=source["capacities"];
      if(capacities.is_null()){
        if(!has_capacity){if(!g.has_capacity)throw std::invalid_argument("solve requires a capacity");capacity=g.capacity;}
        result=solve(g,capacity,opt);
      }else{
        for(auto& c:capacities)if(parse_number(c)<0)throw std::invalid_argument("negative capacity");
        auto path=decompose(g,true,opt);
        result={{"status",path.status},{"message",path.message},{"path",path},{"solutions",Json::array()}};
        if(path.status=="optimal")for(auto& c:capacities){
          auto solution=solve_from_path(g,parse_number(c),path,opt);
          if(solution.status!="optimal")result["status"]=solution.status;
          Json entry=solution;entry.erase("path");result["solutions"].push_back(std::move(entry));
        }
      }
    }else throw std::invalid_argument("unknown task: "+task);
    if(opt.trace&&task!="verify"&&task!="inspect"){
      Prepared p(g,opt);Json arcs=Json::array();
      for(auto a:p.graph.arcs)arcs.push_back({a.tail,a.head});
      result["trace_model"]={{"profit",p.graph.profit},{"weight",p.graph.weight},{"arcs",arcs},{"scc_map",p.component}};
    }
    rusage usage{};getrusage(RUSAGE_SELF,&usage);utsname machine{};uname(&machine);
    result["format_version"]=1;result["task"]=task;result["id"]=g.id;
    result["node_ids"]=source["node_ids"];result["instance_sha256"]=hash;
    result["configuration"]=config;result["configuration_sha256"]=sha256(config.dump());
    result["algorithm"]=opt.algorithm;result["read_seconds"]=read_seconds;result["end_to_end_seconds"]=seconds(begin);
    result["peak_rss_bytes"]=usage.ru_maxrss*1024;result["memory_measurement"]="getrusage(RUSAGE_SELF).ru_maxrss, Linux";
    result["build"]={{"source_sha256",PCLP_SOURCE_HASH},{"compiler",PCLP_COMPILER},{"type",PCLP_BUILD_TYPE},{"flags",PCLP_BUILD_FLAGS},
      {"long_double_bytes",sizeof(Real)},{"system",machine.sysname},{"machine",machine.machine}};
    auto status=result.value("status","");
    write_result(output_path,result);
    return status=="optimal"||status=="valid"?0:1;
  }catch(const std::exception& error){
    Json failure={{"status","invalid_input"},{"message",error.what()}};
    std::cerr<<"pclp: "<<error.what()<<'\n';
    std::cout<<failure.dump()<<'\n';return 2;
  }
}
