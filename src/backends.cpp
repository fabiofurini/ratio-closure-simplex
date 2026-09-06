#include "pclp/flow.hpp"
#include "pclp/graph.hpp"
#include "pclp/engine.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
namespace pclp {
namespace {
bool tied(Real a,Real b,const Options& o) {
  return std::fabs(a-b)<=o.optimality_rel_tol*std::max(std::fabs(a),std::fabs(b));
}
// Shared state of the two flow backends on the condensed, scaled graph.
struct Deadline{};
struct Context {
  const Prepared& prepared;
  const Options& opt;
  Statistics& stats;
  const Instance& g;
  Index n;
  ClosureFlow flow;
  Clock::time_point start;
  std::vector<Real> excess,alpha;
  std::vector<char> side;
  Context(const Prepared& p,const Options& o,Statistics& s,Clock::time_point begin)
   :prepared(p),opt(o),stats(s),g(p.graph),n(g.node_ids.size()),flow(g),start(begin),excess(n),alpha(g.arcs.size(),0),side(n,0) {}
  // The limit is checked before every maximum flow: the backends share the
  // protocol's exit statuses instead of running past the budget.
  void deadline() const { if(opt.time_limit>0&&seconds(start)>=opt.time_limit)throw Deadline{}; }
  Real closure_value(Real lambda,const std::vector<char>& mask) {
    deadline();
    for(Index i=0;i<n;++i)excess[i]=g.profit[i]-lambda*g.weight[i];
    return flow.solve(excess,mask);
  }
  void aggregate(const std::vector<char>& set,Real& profit,Real& weight,Index& count) const {
    profit=0;weight=0;count=0;
    for(Index i=0;i<n;++i)if(set[i]){profit+=g.profit[i];weight+=g.weight[i];++count;}
  }
  // Duals of the last solved network, restricted to arcs inside `set`.
  void harvest(const std::vector<char>& set) {
    for(Index e=0;e<g.arcs.size();++e){
      auto a=g.arcs[e];
      if(set[a.tail]&&set[a.head])alpha[e]=flow.arc_flow(e)*prepared.profit_scale;
    }
  }
  void account() {
    stats.flow_solves=flow.maxflows;stats.flow_augmentations=flow.augmentations;stats.flow_phases=flow.phases;
  }
};
// Newton/Dinkelbach ascent from a strict lower bound: every iterate is the ratio
// of a nonempty closure, so a negative maximum ratio needs no special start.
Real dinkelbach(Context& c,const std::vector<char>& mask,std::vector<char>& block) {
  Real lambda=std::numeric_limits<Real>::infinity();
  Index members=0;
  for(Index i=0;i<c.n;++i)if(mask[i]){lambda=std::min(lambda,c.g.profit[i]/c.g.weight[i]);++members;}
  if(!members)throw std::logic_error("ratio oracle on an empty residual");
  lambda-=1;
  for(Index iteration=0;iteration<=members+1;++iteration){
    c.closure_value(lambda,mask);
    c.flow.source_side(c.side,false);
    Real profit,weight;Index count;
    c.aggregate(c.side,profit,weight,count);
    if(!count){c.flow.source_side(block,true);return lambda;}
    Real next=profit/weight;
    if(!(next>lambda))throw std::runtime_error("Dinkelbach iterate did not increase");
    lambda=next;
  }
  throw std::runtime_error("Dinkelbach iteration limit reached");
}
struct Block {
  Real ratio=0;
  std::vector<Index> nodes;
};
// Sequential residual extraction: one ratio oracle per canonical macroitem.
void dinkelbach_blocks(Context& c,bool positive_only,std::vector<Block>& blocks,
                       std::vector<Real>& bound,std::vector<char>& active,bool& complete) {
  std::vector<char> block(c.n,0);
  Index remaining=c.n;
  while(remaining){
    ++c.stats.oracle_calls;
    Real ratio=dinkelbach(c,active,block);
    if(positive_only&&ratio<=0){
      for(Index i=0;i<c.n;++i)if(active[i])bound[i]=ratio;
      c.harvest(active);
      return;
    }
    Block emitted;emitted.ratio=ratio;
    for(Index i=0;i<c.n;++i)if(block[i]){emitted.nodes.push_back(i);bound[i]=ratio;active[i]=0;}
    if(emitted.nodes.empty())throw std::runtime_error("empty canonical macroitem");
    remaining-=emitted.nodes.size();
    // Recompute the duals inside the block so that no multiplier crosses blocks.
    c.closure_value(ratio,block);
    c.harvest(block);
    blocks.push_back(std::move(emitted));
  }
  complete=true;
}
// Divide and conquer on the difference set: the mean ratio of a candidate
// interval is either a breakpoint or splits it into two smaller intervals.
void parametric_blocks(Context& c,bool positive_only,std::vector<Block>& blocks,
                       std::vector<Real>& bound,std::vector<char>& active,bool& complete) {
  std::vector<char> start(c.n,0);
  if(positive_only){
    ++c.stats.oracle_calls;
    c.closure_value(0,active);
    c.flow.source_side(start,false);
    bool leftover=false;
    for(Index i=0;i<c.n;++i)if(active[i]&&!start[i])leftover=true;
    if(leftover){
      std::vector<char> rest(c.n,0);
      for(Index i=0;i<c.n;++i)rest[i]=active[i]&&!start[i];
      c.closure_value(0,rest);
      c.harvest(rest);
      for(Index i=0;i<c.n;++i)if(rest[i])bound[i]=0;
    }
  }else start=active;
  std::vector<std::vector<char>> pending;
  Index members=0;
  for(Index i=0;i<c.n;++i)members+=start[i]?1:0;
  if(members)pending.push_back(start);
  std::vector<char> split(c.n,0);
  while(!pending.empty()){
    std::vector<char> region=std::move(pending.back());pending.pop_back();
    Real profit,weight;Index count;
    c.aggregate(region,profit,weight,count);
    Real lambda=profit/weight;
    ++c.stats.oracle_calls;
    c.closure_value(lambda,region);
    c.flow.source_side(split,false);
    Index selected=0;
    for(Index i=0;i<c.n;++i)selected+=split[i]?1:0;
    if(!selected){
      Block emitted;emitted.ratio=lambda;
      for(Index i=0;i<c.n;++i)if(region[i]){emitted.nodes.push_back(i);bound[i]=lambda;active[i]=0;}
      c.harvest(region);
      blocks.push_back(std::move(emitted));
      continue;
    }
    if(selected==count)throw std::runtime_error("parametric split did not reduce the interval");
    std::vector<char> lower(c.n,0);
    for(Index i=0;i<c.n;++i)lower[i]=region[i]&&!split[i];
    pending.push_back(lower);
    pending.push_back(split);
  }
  std::sort(blocks.begin(),blocks.end(),[](const Block& a,const Block& b){return a.ratio>b.ratio;});
  complete=!positive_only;
}
void expand(const Prepared& prepared,const Instance& g,const std::vector<Block>& blocks,PathResult& result,const Options& opt) {
  for(auto& source:blocks){
    Macroitem b;b.ratio=source.ratio*prepared.profit_scale/prepared.weight_scale;
    for(auto component:source.nodes)
      for(Index k=prepared.offsets[component];k<prepared.offsets[component+1];++k){
        Index i=prepared.members[k];b.nodes.push_back(i);b.profit+=g.profit[i];b.weight+=g.weight[i];
      }
    if(!result.macroitems.empty()&&tied(result.macroitems.back().ratio,b.ratio,opt)){
      auto& back=result.macroitems.back();back.profit+=b.profit;back.weight+=b.weight;
      back.nodes.insert(back.nodes.end(),b.nodes.begin(),b.nodes.end());back.ratio=back.profit/back.weight;
    }else{
      if(!result.macroitems.empty()&&b.ratio>result.macroitems.back().ratio)throw std::runtime_error("increasing residual ratios");
      result.macroitems.push_back(std::move(b));
    }
  }
  for(auto& b:result.macroitems)std::sort(b.nodes.begin(),b.nodes.end());
  result.prefix_weight={0};result.prefix_profit={0};
  for(auto& b:result.macroitems){
    result.prefix_weight.push_back(result.prefix_weight.back()+b.weight);
    result.prefix_profit.push_back(result.prefix_profit.back()+b.profit);
  }
}
}
RatioResult flow_ratio(const Instance& g,const Options& opt) {
  RatioResult result;auto start=Clock::now();
  try{
    validate(g);validate(opt);
    Prepared prepared(g,opt);result.stats.removed_arcs=prepared.removed_arcs;result.stats.preprocessing_seconds=seconds(start);
    Context c(prepared,opt,result.stats,start);
    std::vector<char> mask(c.n,1),block(c.n,0);
    ++result.stats.oracle_calls;
    Real ratio=dinkelbach(c,mask,block);
    c.harvest(mask);c.account();
    result.ratio=ratio*prepared.profit_scale/prepared.weight_scale;
    for(Index component=0;component<c.n;++component)if(block[component])
      for(Index k=prepared.offsets[component];k<prepared.offsets[component+1];++k)result.support.push_back(prepared.members[k]);
    std::sort(result.support.begin(),result.support.end());
    auto begin=Clock::now();
    std::vector<Real> node_bound(c.n,result.ratio);
    result.certificate.beta=result.ratio;result.certificate.alpha=prepared.lift(c.alpha,node_bound);
    result.certificate.residual.assign(g.node_ids.size(),0);
    for(Index i=0;i<g.node_ids.size();++i)result.certificate.residual[i]=g.weight[i]*result.ratio-g.profit[i];
    for(Index e=0;e<g.arcs.size();++e){
      auto a=g.arcs[e];result.certificate.residual[a.tail]+=result.certificate.alpha[e];result.certificate.residual[a.head]-=result.certificate.alpha[e];
    }
    result.status="optimal";
    result.certificate.feasible=verify_ratio(g,result,opt);
    if(!result.certificate.feasible){result.status="numerical_failure";result.message="original-unit ratio certificate failed";}
    result.stats.certification_seconds=seconds(begin);
  }catch(const Deadline&){result.status="time_limit";result.message="time limit reached before a maximum flow";}
   catch(const std::invalid_argument& e){result.status="invalid_input";result.message=e.what();}
   catch(const std::bad_alloc&){result.status="memory_limit";result.message="allocation failed";}
   catch(const std::exception& e){result.status="numerical_failure";result.message=e.what();}
  result.stats.total_seconds=seconds(start);
  return result;
}
PathResult flow_path(const Instance& g,bool positive_only,const Options& opt) {
  PathResult result;auto start=Clock::now();
  try{
    validate(g);validate(opt);
    Prepared prepared(g,opt);result.stats.removed_arcs=prepared.removed_arcs;result.stats.preprocessing_seconds=seconds(start);
    Context c(prepared,opt,result.stats,start);
    std::vector<Real> bound(c.n,0);
    std::vector<char> active(c.n,1);
    std::vector<Block> blocks;
    bool complete=false;
    if(opt.algorithm=="parametric")parametric_blocks(c,positive_only,blocks,bound,active,complete);
    else dinkelbach_blocks(c,positive_only,blocks,bound,active,complete);
    c.account();
    result.complete=complete;result.positive_complete=true;result.status="optimal";
    expand(prepared,g,blocks,result,opt);
    auto begin=Clock::now();
    std::vector<Real> scaled(c.n);
    for(Index i=0;i<c.n;++i)scaled[i]=bound[i]*prepared.profit_scale/prepared.weight_scale;
    result.node_bound.resize(g.node_ids.size());
    for(Index i=0;i<g.node_ids.size();++i)result.node_bound[i]=scaled[prepared.component[i]];
    result.alpha=prepared.lift(c.alpha,scaled);
    result.pivots=result.stats.pivots;result.degenerate_pivots=result.stats.degenerate_pivots;result.oracle_calls=result.stats.oracle_calls;
    if(!verify_path(g,result,opt)){result.status="numerical_failure";result.message="original-unit path certificate failed";}
    result.stats.certification_seconds=seconds(begin);
  }catch(const Deadline&){result.status="time_limit";result.message="time limit reached before a maximum flow";}
   catch(const std::invalid_argument& e){result.status="invalid_input";result.message=e.what();}
   catch(const std::bad_alloc&){result.status="memory_limit";result.message="allocation failed";}
   catch(const std::exception& e){result.status="numerical_failure";result.message=e.what();}
  result.stats.total_seconds=seconds(start);
  return result;
}
RatioResult max_ratio(const Instance& g,const Options& opt) {
  return uses_ratio_closure(opt)?ratio_closure_ratio(g,{},opt):flow_ratio(g,opt);
}
PathResult decompose(const Instance& g,bool positive_only,const Options& opt) {
  return uses_ratio_closure(opt)?canonical_path(g,positive_only,opt):flow_path(g,positive_only,opt);
}
} // namespace pclp
