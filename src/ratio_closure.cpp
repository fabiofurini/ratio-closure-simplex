#include "pclp/engine.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
namespace pclp {
namespace {
bool tied(Real a,Real b,const Options& o) {
  return std::fabs(a-b)<=o.optimality_rel_tol*std::max(std::fabs(a),std::fabs(b));
}
void finalize(PathResult& p) {
  p.pivots=p.stats.pivots;p.degenerate_pivots=p.stats.degenerate_pivots;p.oracle_calls=p.stats.oracle_calls;
  p.prefix_weight={0};p.prefix_profit={0};
  for(auto& b:p.macroitems){
    std::sort(b.nodes.begin(),b.nodes.end());
    p.prefix_weight.push_back(p.prefix_weight.back()+b.weight);
    p.prefix_profit.push_back(p.prefix_profit.back()+b.profit);
  }
}
}
RatioResult ratio_closure_ratio(const Instance& g,const std::vector<Index>& selected,const Options& opt) {
  RatioResult result;auto start=Clock::now();
  try {
    validate(g);validate(opt);
    if(!selected.empty()) {
      Instance sub;sub.id=g.id;
      Index n=g.node_ids.size();std::vector<Index> map(n,n),arcmap;
      for(auto i:selected){
        if(i>=n||map[i]!=n)throw std::invalid_argument("invalid or repeated residual index");
        map[i]=sub.node_ids.size();sub.node_ids.push_back(g.node_ids[i]);sub.profit.push_back(g.profit[i]);sub.weight.push_back(g.weight[i]);
      }
      for(Index e=0;e<g.arcs.size();++e){auto a=g.arcs[e];if(map[a.tail]!=n&&map[a.head]!=n){sub.arcs.push_back({map[a.tail],map[a.head]});arcmap.push_back(e);}}
      result=ratio_closure_ratio(sub,{},opt);
      for(auto& i:result.support)i=selected[i];
      std::vector<Real> alpha(g.arcs.size(),0);
      for(Index e=0;e<arcmap.size();++e)alpha[arcmap[e]]=result.certificate.alpha.empty()?0:result.certificate.alpha[e];
      result.certificate.alpha=std::move(alpha);return result;
    }
    Prepared prepared(g,opt);result.stats.removed_arcs=prepared.removed_arcs;result.stats.preprocessing_seconds=seconds(start);
    Engine engine(prepared.graph,opt,result.stats,result.trace,start);
    result.status=engine.run();
    result.ratio=engine.rho*prepared.profit_scale/prepared.weight_scale;
    for(auto c:engine.nodes)if(engine.root[c]==engine.positive_root)
      for(Index k=prepared.offsets[c];k<prepared.offsets[c+1];++k)result.support.push_back(prepared.members[k]);
    std::sort(result.support.begin(),result.support.end());
    if(result.status=="optimal"){
      auto begin=Clock::now();
      for(auto& a:engine.alpha)a*=prepared.profit_scale;
      std::vector<Real> bound(prepared.graph.node_ids.size(),result.ratio);
      result.certificate.beta=result.ratio;result.certificate.alpha=prepared.lift(engine.alpha,bound);
      result.certificate.residual.resize(g.node_ids.size());
      for(Index i=0;i<g.node_ids.size();++i)result.certificate.residual[i]=g.weight[i]*result.ratio-g.profit[i];
      for(Index e=0;e<g.arcs.size();++e){
        auto a=g.arcs[e];result.certificate.residual[a.tail]+=result.certificate.alpha[e];result.certificate.residual[a.head]-=result.certificate.alpha[e];
      }
      result.certificate.feasible=verify_ratio(g,result,opt);
      if(!result.certificate.feasible){result.status="numerical_failure";result.message="original-unit ratio certificate failed";}
      result.stats.certification_seconds=seconds(begin);
    }
  }catch(const std::invalid_argument& e){result.status="invalid_input";result.message=e.what();}
   catch(const std::bad_alloc&){result.status="memory_limit";result.message="allocation failed";}
   catch(const std::exception& e){result.status="numerical_failure";result.message=e.what();}
  result.stats.total_seconds=seconds(start);result.pivots=result.stats.pivots;result.degenerate_pivots=result.stats.degenerate_pivots;
  return result;
}
PathResult canonical_path(const Instance& g,bool positive_only,const Options& opt) {
  PathResult result;auto start=Clock::now();
  try {
    validate(g);validate(opt);
    Prepared prepared(g,opt);result.stats.removed_arcs=prepared.removed_arcs;result.stats.preprocessing_seconds=seconds(start);
    Engine engine(prepared.graph,opt,result.stats,result.trace,start);
    Index cn=prepared.graph.node_ids.size();
    std::vector<Real> bound(cn,0),alpha(prepared.graph.arcs.size(),0);
    std::vector<Index> block;block.reserve(cn);
    Index remaining=cn;
    bool first=true;
    while(remaining){
      auto status=first?engine.run():engine.run_residual();
      first=false;
      if(status!="optimal"){result.status=status;result.message="residual oracle did not certify optimality";break;}
      Real rho=engine.rho*prepared.profit_scale/prepared.weight_scale;
      if(positive_only&&rho<=0){
        for(auto i:engine.nodes)bound[i]=rho;
        for(auto e:engine.edges)alpha[e]=engine.alpha[e]*prepared.profit_scale;
        result.positive_complete=true;result.status="optimal";break;
      }
      engine.support(block,opt.canonicalization=="dual");
      for(auto i:block){bound[i]=rho;engine.active[i]=false;}
      // Keep multipliers internal to this certified optimal block, including
      // zero trees admitted by maximal complementarity extraction.
      for(auto e:engine.edges){auto a=prepared.graph.arcs[e];
        if(!engine.active[a.tail]&&!engine.active[a.head])alpha[e]=engine.alpha[e]*prepared.profit_scale;
      }
      remaining-=block.size();
      Macroitem b;b.ratio=rho;
      for(auto c:block)for(Index k=prepared.offsets[c];k<prepared.offsets[c+1];++k){
        Index i=prepared.members[k];b.nodes.push_back(i);b.profit+=g.profit[i];b.weight+=g.weight[i];
      }
      if(!result.macroitems.empty()&&tied(result.macroitems.back().ratio,rho,opt)){
        auto& back=result.macroitems.back();back.profit+=b.profit;back.weight+=b.weight;
        back.nodes.insert(back.nodes.end(),b.nodes.begin(),b.nodes.end());back.ratio=back.profit/back.weight;
      }else{
        if(!result.macroitems.empty()&&rho>result.macroitems.back().ratio)throw std::runtime_error("increasing residual ratios");
        result.macroitems.push_back(std::move(b));
      }
    }
    if(!remaining){result.status="optimal";result.complete=true;result.positive_complete=true;}
    if(result.status=="optimal"){
      auto begin=Clock::now();
      result.node_bound.resize(g.node_ids.size());
      for(Index i=0;i<g.node_ids.size();++i)result.node_bound[i]=bound[prepared.component[i]];
      result.alpha=prepared.lift(alpha,bound);finalize(result);
      if(!verify_path(g,result,opt)){result.status="numerical_failure";result.message="original-unit path certificate failed";}
      result.stats.certification_seconds=seconds(begin);
    }
  }catch(const std::invalid_argument& e){result.status="invalid_input";result.message=e.what();}
   catch(const std::bad_alloc&){result.status="memory_limit";result.message="allocation failed";}
   catch(const std::exception& e){result.status="numerical_failure";result.message=e.what();}
  result.stats.total_seconds=seconds(start);finalize(result);return result;
}
Real value_from_path(const PathResult& path,Real c) {
  if(path.status!="optimal"||!path.positive_complete||!std::isfinite(c)||c<0)throw std::invalid_argument("certified positive path and nonnegative capacity required");
  Index positive=static_cast<Index>(std::partition_point(path.macroitems.begin(),path.macroitems.end(),[](const Macroitem& b){return b.ratio>0;})-path.macroitems.begin());
  auto end=path.prefix_weight.begin()+static_cast<std::ptrdiff_t>(positive+1);
  auto it=std::upper_bound(path.prefix_weight.begin(),end,c);
  Index k=static_cast<Index>(it-path.prefix_weight.begin())-1;
  if(k==positive)return path.prefix_profit[k];
  return path.prefix_profit[k]+(c-path.prefix_weight[k])*path.macroitems[k].ratio;
}
SolveResult solve_from_path(const Instance& g,Real c,const PathResult& path,const Options& opt){
  SolveResult result;result.capacity=c;
  try{
    validate(g);validate(opt);
    if(!std::isfinite(c)||c<0)throw std::invalid_argument("finite nonnegative capacity required");
    if(path.status!="optimal"||!verify_path(g,path,opt))throw std::invalid_argument("path is not certified for this instance");
    result.solution.assign(g.node_ids.size(),0);result.mu.assign(g.node_ids.size(),0);
    Real remaining=c;
    for(auto& b:path.macroitems){
      if(b.ratio<=0)break;
      Real fraction=std::min(Real(1),remaining/b.weight);
      for(auto i:b.nodes)result.solution[i]=fraction;
      remaining-=fraction*b.weight;
      if(fraction<1){result.lambda=b.ratio;break;}
    }
    result.alpha=path.alpha;
    result.dual_bound=c*result.lambda;
    for(Index i=0;i<g.node_ids.size();++i){
      result.objective+=g.profit[i]*result.solution[i];result.used_weight+=g.weight[i]*result.solution[i];
      result.mu[i]=std::max(Real(0),g.weight[i]*(path.node_bound[i]-result.lambda));result.dual_bound+=result.mu[i];
    }
    result.gap=result.dual_bound-result.objective;
    result.status=verify_solution(g,result,opt)?"optimal":"numerical_failure";
    if(result.status!="optimal")result.message="original-unit LP certificate failed";
  }catch(const std::exception& e){result.status="invalid_input";result.message=e.what();}
  return result;
}
SolveResult solve(const Instance& g,Real c,const Options& opt){
  SolveResult result;result.capacity=c;
  if(!std::isfinite(c)||c<0){result.status="invalid_input";result.message="finite nonnegative capacity required";return result;}
  auto path=decompose(g,true,opt);
  if(path.status!="optimal"){result.status=path.status;result.message=path.message;result.path=std::move(path);return result;}
  result=solve_from_path(g,c,path,opt);result.path=std::move(path);return result;
}
} // namespace pclp
