#include "pclp/core.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
namespace pclp {
namespace {
bool finite(const std::vector<Real>& a){return std::all_of(a.begin(),a.end(),[](Real x){return std::isfinite(x);});}
bool near(Real a,Real b,const Options& o){
  return std::isfinite(a)&&std::isfinite(b)&&std::fabs(a-b)<=o.feasibility_abs_tol+o.feasibility_rel_tol*std::max(std::fabs(a),std::fabs(b));
}
bool ge(Real a,Real b,const Options& o){return std::isfinite(a)&&std::isfinite(b)&&(a>=b||near(a,b,o));}
bool zero(Real error,Real scale,const Options& o){
  return std::isfinite(error)&&std::isfinite(scale)&&std::fabs(error)<=o.feasibility_abs_tol+o.feasibility_rel_tol*scale;
}
bool dual(const Instance& g,const std::vector<Real>& b,const std::vector<Real>& alpha,std::vector<Real>& lhs,const Options& o,std::vector<Real>* row_scale=nullptr){
  Index n=g.node_ids.size();
  if(b.size()!=n||alpha.size()!=g.arcs.size()||!finite(b)||!finite(alpha))return false;
  lhs.resize(n);
  std::vector<Real> scale(n);
  for(Index i=0;i<n;++i){lhs[i]=g.weight[i]*b[i];scale[i]=std::fabs(lhs[i])+std::fabs(g.profit[i]);}
  for(Index e=0;e<alpha.size();++e){
    if(!ge(alpha[e],0,o))return false;
    auto a=g.arcs[e];lhs[a.tail]+=alpha[e];lhs[a.head]-=alpha[e];
    scale[a.tail]+=std::fabs(alpha[e]);scale[a.head]+=std::fabs(alpha[e]);
  }
  for(Index i=0;i<n;++i)if(!std::isfinite(lhs[i])||(lhs[i]<g.profit[i]&&!zero(lhs[i]-g.profit[i],scale[i],o)))return false;
  if(row_scale)*row_scale=std::move(scale);
  return true;
}
}
bool verify_ratio(const Instance& g,const RatioResult& r,const Options& o){
  Index n=g.node_ids.size();
  if(r.support.empty()||!std::isfinite(r.ratio)||!near(r.ratio,r.certificate.beta,o))return false;
  std::vector<char> chosen(n,false);Real p=0,w=0;
  for(auto i:r.support){if(i>=n||chosen[i])return false;chosen[i]=true;p+=g.profit[i];w+=g.weight[i];}
  for(auto a:g.arcs)if(chosen[a.tail]&&!chosen[a.head])return false;
  if(!near(p/w,r.ratio,o))return false;
  std::vector<Real> lhs;
  return dual(g,std::vector<Real>(n,r.ratio),r.certificate.alpha,lhs,o);
}
bool verify_path(const Instance& g,const PathResult& path,const Options& o){
  Index n=g.node_ids.size();std::vector<Real> lhs,scale;
  if(!dual(g,path.node_bound,path.alpha,lhs,o,&scale))return false;
  if(path.prefix_weight.size()!=path.macroitems.size()+1||path.prefix_profit.size()!=path.macroitems.size()+1||
     !near(path.prefix_weight[0],0,o)||!near(path.prefix_profit[0],0,o))return false;
  std::vector<Index> block(n,path.macroitems.size());
  Real previous=std::numeric_limits<Real>::infinity();
  for(Index k=0;k<path.macroitems.size();++k){
    auto& b=path.macroitems[k];Real p=0,w=0;
    if(b.nodes.empty()||!std::isfinite(b.ratio)||b.ratio>=previous)return false;
    previous=b.ratio;
    for(auto i:b.nodes){
      if(i>=n||block[i]!=path.macroitems.size())return false;
      block[i]=k;p+=g.profit[i];w+=g.weight[i];
      if(!near(path.node_bound[i],b.ratio,o)||!zero(lhs[i]-g.profit[i],scale[i],o))return false;
    }
    if(!near(p,b.profit,o)||!near(w,b.weight,o)||!near(p/w,b.ratio,o))return false;
    if(!near(path.prefix_weight[k+1],path.prefix_weight[k]+w,o)||!near(path.prefix_profit[k+1],path.prefix_profit[k]+p,o))return false;
  }
  for(Index i=0;i<n;++i)if(block[i]==path.macroitems.size()&&(path.complete||!path.positive_complete||path.node_bound[i]>0))return false;
  for(Index e=0;e<g.arcs.size();++e){
    auto a=g.arcs[e];
    if(block[a.tail]<block[a.head])return false;
    // No certificate flow across distinct blocks: each bound applies separately.
    if(block[a.tail]!=block[a.head]&&!near(path.alpha[e],0,o))return false;
  }
  return path.complete||path.positive_complete;
}
bool verify_solution(const Instance& g,const SolveResult& r,const Options& o){
  Index n=g.node_ids.size();
  if(r.solution.size()!=n||r.mu.size()!=n||r.alpha.size()!=g.arcs.size()||!finite(r.solution)||!finite(r.mu)||!finite(r.alpha)||
     !std::isfinite(r.capacity)||r.capacity<0||!std::isfinite(r.lambda)||r.lambda<0)return false;
  std::vector<Real> lhs(n),scale(n);Real p=0,w=0,bound=r.capacity*r.lambda;
  for(Index i=0;i<n;++i){
    if(!ge(r.solution[i],0,o)||!ge(1,r.solution[i],o)||!ge(r.mu[i],0,o))return false;
    p+=g.profit[i]*r.solution[i];w+=g.weight[i]*r.solution[i];
    lhs[i]=g.weight[i]*r.lambda+r.mu[i];bound+=r.mu[i];
    scale[i]=std::fabs(g.weight[i]*r.lambda)+std::fabs(r.mu[i])+std::fabs(g.profit[i]);
    if(!near(r.mu[i],r.mu[i]*r.solution[i],o))return false;
  }
  for(Index e=0;e<g.arcs.size();++e){
    auto a=g.arcs[e];
    if(!ge(r.solution[a.head],r.solution[a.tail],o)||!ge(r.alpha[e],0,o))return false;
    lhs[a.tail]+=r.alpha[e];lhs[a.head]-=r.alpha[e];
    scale[a.tail]+=std::fabs(r.alpha[e]);scale[a.head]+=std::fabs(r.alpha[e]);
    if(!near(r.alpha[e]*r.solution[a.head],r.alpha[e]*r.solution[a.tail],o))return false;
  }
  for(Index i=0;i<n;++i)if(!std::isfinite(lhs[i])||(lhs[i]<g.profit[i]&&!zero(lhs[i]-g.profit[i],scale[i],o))||
     !zero(r.solution[i]*(lhs[i]-g.profit[i]),std::fabs(r.solution[i])*scale[i],o))return false;
  return ge(r.capacity,w,o)&&near(p,r.objective,o)&&near(w,r.used_weight,o)&&near(bound,r.dual_bound,o)&&near(bound,p,o)&&near(r.lambda*r.capacity,r.lambda*w,o);
}
} // namespace pclp
