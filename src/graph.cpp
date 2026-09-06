#include "pclp/graph.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <tuple>
#include <unordered_set>
#include <cstdint>
namespace pclp {
CSR::CSR(Index n,const std::vector<Arc>& arcs,bool reverse):offset(n+1,0),edge(arcs.size()) {
  for(auto a:arcs) ++offset[(reverse?a.head:a.tail)+1];
  std::partial_sum(offset.begin(),offset.end(),offset.begin());
  auto pos=offset;
  for(Index e=0;e<arcs.size();++e)edge[pos[reverse?arcs[e].head:arcs[e].tail]++]=e;
}
void validate(const Instance& g) {
  Index n=g.node_ids.size();
  if(!n||g.profit.size()!=n||g.weight.size()!=n)throw std::invalid_argument("nonempty node_ids/profit/weight arrays must have equal lengths");
  std::unordered_set<std::string> ids;
  for(Index i=0;i<n;++i) {
    if(!ids.insert(g.node_ids[i]).second)throw std::invalid_argument("duplicate node ID");
    if(!std::isfinite(g.profit[i])||!std::isfinite(g.weight[i])||g.weight[i]<=0)throw std::invalid_argument("finite profits and strictly positive finite weights required");
  }
  for(auto a:g.arcs)if(a.tail>=n||a.head>=n)throw std::invalid_argument("invalid arc endpoint");
  if(g.has_capacity&&(!std::isfinite(g.capacity)||g.capacity<0))throw std::invalid_argument("capacity must be finite and nonnegative");
}
Prepared::Prepared(const Instance& g,const Options& opt):original(g),out(g.node_ids.size(),g.arcs,false),in(g.node_ids.size(),g.arcs,true) {
  Index n=g.node_ids.size(),none=n;
  std::vector<char> seen(n,false);
  std::vector<Index> order,stack,cursor=out.offset;
  order.reserve(n);stack.reserve(n);
  for(Index s=0;s<n;++s)if(!seen[s]) {
    stack.push_back(s);seen[s]=true;
    while(!stack.empty()) {
      Index u=stack.back();
      if(cursor[u]==out.offset[u+1]){order.push_back(u);stack.pop_back();continue;}
      Index v=g.arcs[out.edge[cursor[u]++]].head;
      if(!seen[v]){seen[v]=true;stack.push_back(v);}
    }
  }
  component.assign(n,none);
  Index count=0;
  for(auto it=order.rbegin();it!=order.rend();++it)if(component[*it]==none) {
    stack.push_back(*it);component[*it]=count;
    while(!stack.empty()) {
      Index u=stack.back();stack.pop_back();
      for(Index k=in.offset[u];k<in.offset[u+1];++k) {
        Index v=g.arcs[in.edge[k]].tail;
        if(component[v]==none){component[v]=count;stack.push_back(v);}
      }
    }
    ++count;
  }
  // Condensation numbering. "input" keeps the smallest original index first and
  // preserves DAG variable order; "topological" keeps the order produced by the
  // condensation itself, in which a node precedes its prerequisites; "seeded"
  // permutes deterministically so that order sensitivity can be measured.
  std::vector<Index> minima(count,n),rank(count),permutation(count);
  for(Index i=0;i<n;++i)minima[component[i]]=std::min(minima[component[i]],i);
  std::iota(permutation.begin(),permutation.end(),0);
  if(opt.node_order=="input")
    std::sort(permutation.begin(),permutation.end(),[&](Index a,Index b){return minima[a]<minima[b];});
  else if(opt.node_order=="seeded"){
    // splitmix64 keeps the permutation reproducible from the recorded seed.
    std::uint64_t state=opt.seed+0x9e3779b97f4a7c15ULL;
    auto next=[&]{
      std::uint64_t z=(state+=0x9e3779b97f4a7c15ULL);
      z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;z=(z^(z>>27))*0x94d049bb133111ebULL;return z^(z>>31);
    };
    for(Index k=count;k>1;--k)std::swap(permutation[k-1],permutation[next()%k]);
  }
  for(Index i=0;i<count;++i)rank[permutation[i]]=i;
  for(auto& c:component)c=rank[c];
  offsets.assign(count+1,0);
  for(auto c:component)++offsets[c+1];
  std::partial_sum(offsets.begin(),offsets.end(),offsets.begin());
  members.resize(n);cursor=offsets;
  graph.profit.assign(count,0);graph.weight.assign(count,0);graph.node_ids.resize(count);
  for(Index i=0;i<n;++i) {
    Index c=component[i];members[cursor[c]++]=i;
    graph.profit[c]+=g.profit[i];graph.weight[c]+=g.weight[i];
  }
  for(Index c=0;c<count;++c) {
    graph.node_ids[c]=std::to_string(c);
    if(!std::isfinite(graph.profit[c])||!std::isfinite(graph.weight[c]))throw std::invalid_argument("SCC aggregate overflow");
  }
  std::vector<Index> edges(g.arcs.size());std::iota(edges.begin(),edges.end(),0);
  std::sort(edges.begin(),edges.end(),[&](Index a,Index b){
    auto x=g.arcs[a],y=g.arcs[b];
    return std::tuple(component[x.tail],component[x.head],a)<std::tuple(component[y.tail],component[y.head],b);
  });
  Index last_u=count,last_v=count;
  for(auto e:edges) {
    auto a=g.arcs[e];Index u=component[a.tail],v=component[a.head];
    if(u==v||(u==last_u&&v==last_v))continue;
    representative.push_back(e);last_u=u;last_v=v;
  }
  std::sort(representative.begin(),representative.end());
  if(opt.transitive_reduction=="on")reduce(count);
  for(auto e:representative)graph.arcs.push_back({component[g.arcs[e].tail],component[g.arcs[e].head]});
  profit_scale=0;weight_scale=0;
  for(auto p:graph.profit)profit_scale=std::max(profit_scale,std::fabs(p));
  for(auto w:graph.weight)weight_scale=std::max(weight_scale,w);
  if(!profit_scale)profit_scale=1;
  // Binary scaling is exact in binary floating point; dividing by an arbitrary
  // maximum can turn an integer zero-profit sum into a spurious nonzero ratio.
  int pe=0,we=0;
  std::frexp(profit_scale,&pe);std::frexp(weight_scale,&we);
  profit_scale=std::ldexp(Real(1),pe-1);weight_scale=std::ldexp(Real(1),we-1);
  for(auto& p:graph.profit)p/=profit_scale;
  for(auto& w:graph.weight)w/=weight_scale;
  inward_parent.assign(n,g.arcs.size());outward_parent=inward_parent;
  inward_order.reserve(n);outward_order.reserve(n);
  auto tree=[&](bool reverse,std::vector<Index>& parent,std::vector<Index>& visit){
    std::fill(seen.begin(),seen.end(),false);
    const CSR& csr=reverse?in:out;
    for(Index c=0;c<count;++c) {
      Index r=members[offsets[c]];stack.push_back(r);seen[r]=true;
      while(!stack.empty()) {
        Index u=stack.back();stack.pop_back();visit.push_back(u);
        for(Index k=csr.offset[u];k<csr.offset[u+1];++k) {
          Index e=csr.edge[k],v=reverse?g.arcs[e].tail:g.arcs[e].head;
          if(component[v]==c&&!seen[v]){seen[v]=true;parent[v]=e;stack.push_back(v);}
        }
      }
    }
  };
  tree(true,inward_parent,inward_order);tree(false,outward_parent,outward_order);
}
void Prepared::reduce(Index count) {
  // Exact reduction: an arc (u,v) is implied when v is a strict descendant of
  // another out-neighbour of u.  The descendant bitsets need count^2 bits, so
  // above the memory budget the reduction is skipped, never approximated.
  constexpr Index budget=64ull<<20;
  Index words=(count+63)/64;
  if(!count||words*count*8>budget)return;
  std::vector<Arc> condensed;condensed.reserve(representative.size());
  for(auto e:representative)condensed.push_back({component[original.arcs[e].tail],component[original.arcs[e].head]});
  CSR csr(count,condensed,false);
  std::vector<std::uint64_t> descendant(words*count,0),reachable(words,0);
  std::vector<char> visit(count,0),keep(representative.size(),1);
  std::vector<Index> order,todo;
  order.reserve(count);
  for(Index s=0;s<count;++s)if(!visit[s]){
    todo.push_back(s);visit[s]=1;
    while(!todo.empty()){
      Index u=todo.back();
      if(visit[u]==2){order.push_back(u);todo.pop_back();continue;}
      visit[u]=2;
      for(Index k=csr.offset[u];k<csr.offset[u+1];++k){
        Index v=condensed[csr.edge[k]].head;
        if(!visit[v]){visit[v]=1;todo.push_back(v);}
      }
    }
  }
  for(auto u:order){
    std::fill(reachable.begin(),reachable.end(),0);
    for(Index k=csr.offset[u];k<csr.offset[u+1];++k){
      Index v=condensed[csr.edge[k]].head;
      for(Index w=0;w<words;++w)reachable[w]|=descendant[v*words+w];
    }
    for(Index k=csr.offset[u];k<csr.offset[u+1];++k){
      Index slot=csr.edge[k],v=condensed[slot].head;
      if(reachable[v/64]>>(v%64)&1){keep[slot]=0;++removed_arcs;}
    }
    std::copy(reachable.begin(),reachable.end(),descendant.begin()+static_cast<std::ptrdiff_t>(u*words));
    for(Index k=csr.offset[u];k<csr.offset[u+1];++k){
      Index v=condensed[csr.edge[k]].head;
      descendant[u*words+v/64]|=std::uint64_t(1)<<(v%64);
    }
  }
  std::vector<Index> kept;
  for(Index k=0;k<representative.size();++k)if(keep[k])kept.push_back(representative[k]);
  representative=std::move(kept);
  transitively_reduced=true;
}
std::vector<Real> Prepared::lift(const std::vector<Real>& alpha,const std::vector<Real>& bound) const {
  const auto& g=original;Index n=g.node_ids.size();
  std::vector<Real> lifted(g.arcs.size(),0),d(n),positive(n,0),negative(n,0),sums(graph.node_ids.size(),0);
  for(Index i=0;i<n;++i)d[i]=g.profit[i]-g.weight[i]*bound[component[i]];
  for(Index e=0;e<alpha.size();++e) {
    Index oe=representative[e];Real a=alpha[e];lifted[oe]=a;
    d[g.arcs[oe].tail]-=a;d[g.arcs[oe].head]+=a;
  }
  for(Index i=0;i<n;++i)sums[component[i]]+=d[i];
  for(Index c=0;c<sums.size();++c)d[members[offsets[c]]]-=sums[c];
  for(Index i=0;i<n;++i){positive[i]=std::max(d[i],Real(0));negative[i]=std::max(-d[i],Real(0));}
  for(auto it=inward_order.rbegin();it!=inward_order.rend();++it) {
    Index e=inward_parent[*it];if(e==g.arcs.size())continue;
    lifted[e]+=positive[*it];positive[g.arcs[e].head]+=positive[*it];
  }
  for(auto it=outward_order.rbegin();it!=outward_order.rend();++it) {
    Index e=outward_parent[*it];if(e==g.arcs.size())continue;
    lifted[e]+=negative[*it];negative[g.arcs[e].tail]+=negative[*it];
  }
  return lifted;
}
} // namespace pclp
