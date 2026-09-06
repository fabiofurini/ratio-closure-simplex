#include "pclp/engine.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
namespace pclp {
namespace {
constexpr Index nil=BasisForest::npos();
bool close(Real a,Real b,const Options& o) {
  return std::isfinite(a)&&std::isfinite(b)&&std::fabs(a-b)<=o.feasibility_abs_tol+o.feasibility_rel_tol*std::max(std::fabs(a),std::fabs(b));
}
}
void validate(const Options& o) {
  auto one=[](const std::string& v,std::initializer_list<const char*> values){for(auto x:values)if(v==x)return true;return false;};
  if(!one(o.algorithm,{"ratio-closure","closure-simplex","forest","dinkelbach","parametric"}))throw std::invalid_argument("algorithm must be ratio-closure (short form closure-simplex, legacy spelling forest), dinkelbach or parametric");
  if(!one(o.basis_update,{"full","local","adaptive"})||!one(o.pricing,{"full","partial","candidate-list"})||
     !one(o.entering_rule,{"bland","first-improving","best-improving"}))throw std::invalid_argument("unsupported basis-update/pricing/entering option");
  if(o.entering_rule=="bland"&&o.pricing!="full")throw std::invalid_argument("Bland entering requires full pricing");
  if(o.canonicalization!="sequential"&&o.canonicalization!="dual")throw std::invalid_argument("canonicalization must be sequential or dual");
  if(!one(o.node_order,{"input","topological","seeded"}))throw std::invalid_argument("node_order must be input, topological or seeded");
  if(!one(o.transitive_reduction,{"off","on"}))throw std::invalid_argument("transitive_reduction must be off or on");
  if(!one(o.initial_basis,{"sink","closure","full"}))throw std::invalid_argument("initial_basis must be sink, closure or full");
  if(!one(o.ratio_test,{"full","restricted","early"}))throw std::invalid_argument("ratio_test must be full, restricted or early");
  if(!one(o.warm_start,{"off","residual"}))throw std::invalid_argument("warm_start must be off or residual");
  if(!one(o.simplex,{"primal","dual"}))throw std::invalid_argument("simplex must be primal or dual");
  if(!one(o.dual_leaving,{"first","best-head","largest-tree","deepest","incremental"}))throw std::invalid_argument("dual_leaving must be first, best-head, largest-tree, deepest or incremental");
  if(!o.initial_seeds)throw std::invalid_argument("initial_seeds must be positive");
  if(o.node_order!="seeded"&&o.seed)throw std::invalid_argument("seed applies to node_order=seeded only");
  if(!o.pricing_block_size||!o.candidate_limit||!o.degeneracy_trigger)throw std::invalid_argument("block/candidate/degeneracy sizes must be positive");
  for(auto x:{o.time_limit,o.feasibility_abs_tol,o.feasibility_rel_tol,o.optimality_abs_tol,o.optimality_rel_tol})
    if(!std::isfinite(x)||x<0)throw std::invalid_argument("limits and tolerances must be finite and nonnegative");
  if(!std::isfinite(o.rebuild_fraction)||o.rebuild_fraction<=0||o.rebuild_fraction>1)throw std::invalid_argument("rebuild_fraction must be in (0,1]");
}
Engine::Engine(const Instance& graph,const Options& options,Statistics& counters,std::vector<Pivot>& log,Clock::time_point begin)
 :g(graph),opt(options),stats(counters),trace(log),start(begin),n(g.node_ids.size()),m(g.arcs.size()),none(n+m),
  forest(n,g.arcs),outgoing(n,g.arcs,false),incoming(n,g.arcs,true),active(n,true),anchor(n,true),inset(n,0),best_set(n,0),positive(n,0),queued(m,0),root(n),parent(n),parent_edge(n,m),child(n,n),sibling(n,n),member_next(n,n),
  subp(n),subw(n),dy(n),y(n),old_y(n),alpha(m),row(n) {
  for(auto* v:{&nodes,&nb,&stack,&order,&affected,&collect,&cache})v->reserve(n);
  edges.reserve(m);
}
void Engine::initialize() {
  for(Index e=0;e<m;++e)if(forest.contains(e))forest.cut(e);
  nodes.clear();edges.clear();nb.clear();cache.clear();cursor=0;zero_streak=0;
  bland=opt.entering_rule=="bland";
  std::fill(alpha.begin(),alpha.end(),0);
  std::fill(parent_edge.begin(),parent_edge.end(),m);
  for(Index i=0;i<n;++i)if(active[i]){nodes.push_back(i);anchor[i]=true;parent[i]=0;}
  for(Index e=0;e<m;++e)if(active[g.arcs[e].tail]&&active[g.arcs[e].head]){
    edges.push_back(e);++parent[g.arcs[e].tail];
  }
  if(!(opt.initial_basis!="sink"&&seed_closure())){
    positive_root=n;
    for(auto i:nodes)if(parent[i]==0){positive_root=i;break;}
    if(positive_root==n)throw std::logic_error("condensed residual has no sink");
    anchor[positive_root]=false;
    for(auto i:nodes)if(anchor[i])nb.push_back(i);
  }
  affected=nodes;rebuild(true);
}
// Starts the positive component on the closure of a promising node instead of a
// single sink.  Any closed subset of the residual induces a feasible basis: the
// values are constant on it and zero elsewhere, so every non-basic precedence
// arc is satisfied.  The seed closure is connected by construction, so a
// spanning tree of it is a valid forest.  Without this the pivot loop has to
// absorb the residual one node at a time, and almost every such step is
// degenerate.
bool Engine::seed_closure() {
  // Chooses the initial positive component.  Any closed subset of the residual
  // gives a feasible basis: the values are constant on it and zero elsewhere,
  // so no non-basic precedence arc is violated.  "closure" starts from the
  // closure of a promising seed, "full" from the best undirected component of
  // the whole residual, which is the basis the historical prototype used when
  // the residual is connected.  Everything outside the positive component is
  // spanned as well and its tree roots are anchored at zero.
  for(auto i:nodes)best_set[i]=0;
  bool found=false;
  if(opt.initial_basis=="full"){
    for(auto i:nodes)inset[i]=0;
    Real best=0;
    for(auto s:nodes){
      if(inset[s])continue;
      collect.clear();stack.clear();stack.push_back(s);inset[s]=1;
      Real profit=0,weight=0;
      while(!stack.empty()){
        Index u=stack.back();stack.pop_back();collect.push_back(u);profit+=g.profit[u];weight+=g.weight[u];
        for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k){
          Index v=g.arcs[outgoing.edge[k]].head;
          if(active[v]&&!inset[v]){inset[v]=1;stack.push_back(v);}
        }
        for(Index k=incoming.offset[u];k<incoming.offset[u+1];++k){
          Index v=g.arcs[incoming.edge[k]].tail;
          if(active[v]&&!inset[v]){inset[v]=1;stack.push_back(v);}
        }
      }
      ++stats.seed_closures;
      Real ratio=profit/weight;
      if(!found||ratio>best){
        best=ratio;found=true;
        for(auto i:nodes)best_set[i]=0;
        for(auto u:collect)best_set[u]=1;
      }
    }
  }else{
    cache.clear();
    for(auto i:nodes)if(g.profit[i]>0)cache.push_back(i);
    if(cache.empty())return false;
    std::sort(cache.begin(),cache.end(),[&](Index a,Index b){
      Real ra=g.profit[a]/g.weight[a],rb=g.profit[b]/g.weight[b];
      return ra!=rb?ra>rb:a<b;});
    if(cache.size()>opt.initial_seeds)cache.resize(opt.initial_seeds);
    Real best=0;
    for(auto s:cache){
      for(auto i:nodes)inset[i]=0;
      stack.clear();stack.push_back(s);inset[s]=1;
      Real profit=0,weight=0;
      while(!stack.empty()){
        Index u=stack.back();stack.pop_back();profit+=g.profit[u];weight+=g.weight[u];
        for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k){
          Index v=g.arcs[outgoing.edge[k]].head;
          if(active[v]&&!inset[v]){inset[v]=1;stack.push_back(v);}
        }
      }
      ++stats.seed_closures;
      Real ratio=profit/weight;
      if(!found||ratio>best){best=ratio;found=true;for(auto i:nodes)best_set[i]=inset[i];}
    }
    cache.clear();
  }
  if(!found)return false;
  Index start=n;
  for(auto i:nodes)if(best_set[i]){start=i;break;}
  if(start==n)return false;
  // Spanning forest that never crosses the boundary of the positive component:
  // the positive tree carries no anchor, every other tree is anchored at its
  // seed, which keeps exactly one unanchored root in the whole basis.
  for(auto i:nodes){inset[i]=0;anchor[i]=false;}
  Index members=0;
  auto span=[&](Index seed){
    stack.clear();stack.push_back(seed);inset[seed]=1;
    Index size=1;
    while(!stack.empty()){
      Index u=stack.back();stack.pop_back();
      auto grow=[&](Index e){
        auto a=g.arcs[e];Index v=a.tail==u?a.head:a.tail;
        if(!active[v]||inset[v]||best_set[v]!=best_set[u])return;
        inset[v]=1;++size;forest.link(e);stack.push_back(v);
      };
      for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k)grow(outgoing.edge[k]);
      for(Index k=incoming.offset[u];k<incoming.offset[u+1];++k)grow(incoming.edge[k]);
    }
    return size;
  };
  members=span(start);
  for(auto i:nodes)if(!inset[i]){span(i);anchor[i]=true;}
  positive_root=start;
  stats.seeded_nodes+=members;
  nb.clear();
  for(auto i:nodes)if(anchor[i])nb.push_back(i);
  for(Index e=0;e<m;++e)if(forest.contains(e))nb.push_back(n+e);
  return true;
}
void Engine::gather(Index q) {
  // Each old component is visited once; at most three distinct components change.
  auto add=[&](Index v) {
    Index r=root[v];
    if(std::find(collect.begin(),collect.end(),r)!=collect.end())return;
    collect.push_back(r);
    for(Index u=r;u!=n;u=member_next[u])affected.push_back(u);
  };
  if(q<n)add(q);else{add(g.arcs[q-n].tail);add(g.arcs[q-n].head);}
}
void Engine::rebuild(bool full) {
  auto begin=Clock::now();
  if(full){affected=nodes;++stats.full_rebuilds;}else ++stats.local_rebuilds;
  stats.rebuilt_nodes+=affected.size();
  for(auto u:affected){root[u]=n;parent[u]=n;child[u]=n;sibling[u]=n;parent_edge[u]=m;}
  for(auto s:affected)if(root[s]==n) {
    collect.clear();stack.clear();stack.push_back(s);root[s]=s;
    Index r=n,minimum=s;
    while(!stack.empty()) {
      Index u=stack.back();stack.pop_back();collect.push_back(u);minimum=std::min(minimum,u);
      if(anchor[u]){if(r!=n)throw std::logic_error("two anchors in one forest tree");r=u;}
      for(Index slot=forest.first_slot(u);slot!=nil;slot=forest.next_slot(slot)){
        Index v=forest.other_endpoint(slot);
        if(root[v]==n){root[v]=s;stack.push_back(v);}
      }
    }
    if(r==n){r=minimum;positive_root=r;}
    order.clear();stack.clear();stack.push_back(r);parent[r]=r;
    while(!stack.empty()) {
      Index u=stack.back();stack.pop_back();order.push_back(u);root[u]=r;
      subp[u]=g.profit[u];subw[u]=g.weight[u];
      for(Index slot=forest.first_slot(u);slot!=nil;slot=forest.next_slot(slot)) {
        Index v=forest.other_endpoint(slot);
        if(v==parent[u])continue;
        if(parent[v]!=n)throw std::logic_error("cycle in forest basis");
        parent[v]=u;parent_edge[v]=forest.edge_of_slot(slot);
        sibling[v]=child[u];child[u]=v;stack.push_back(v);
      }
    }
    for(Index k=0;k<order.size();++k)member_next[order[k]]=k+1<order.size()?order[k+1]:n;
    for(auto it=order.rbegin();it!=order.rend();++it)if(*it!=r){subp[parent[*it]]+=subp[*it];subw[parent[*it]]+=subw[*it];}
  }
  rho=subp[positive_root]/subw[positive_root];
  if(!std::isfinite(rho))throw std::runtime_error("nonfinite forest ratio");
  stats.update_seconds+=seconds(begin);
}
Real Engine::reduced(Index q) const {
  if(q<n){Index r=root[q];return subp[r]-rho*subw[r];}
  Index e=q-n;auto a=g.arcs[e];
  Index c=parent_edge[a.tail]==e?a.tail:a.head;
  Real sign=a.head==c?1:-1;
  return sign*(subp[c]-rho*subw[c]);
}
Index Engine::price() {
  auto begin=Clock::now();
  Index chosen=none;Real best=0;
  auto consider=[&](Index q){
    ++stats.candidates_examined;
    Real rc=reduced(q);
    Index r=q<n?root[q]:(parent_edge[g.arcs[q-n].tail]==q-n?g.arcs[q-n].tail:g.arcs[q-n].head);
    Real tol=opt.optimality_abs_tol+opt.optimality_rel_tol*std::max(std::fabs(subp[r]),std::fabs(rho*subw[r]));
    if(rc>tol&&(chosen==none||((bland||opt.entering_rule=="first-improving")?q<chosen:rc>best))){
      chosen=q;best=rc;
    }
  };
  if(!bland&&opt.pricing=="candidate-list") {
    for(auto q:cache)if(q<n?anchor[q]:forest.contains(q-n))consider(q);
    if(chosen!=none){stats.pricing_seconds+=seconds(begin);return chosen;}
    cache.clear();
  }
  if(!bland&&opt.pricing=="partial"&&!nb.empty()) {
    Index scanned=0;
    while(scanned<nb.size()) {
      Index take=std::min(opt.pricing_block_size,nb.size()-scanned);
      for(Index k=0;k<take;++k){consider(nb[cursor]);cursor=(cursor+1)%nb.size();}
      scanned+=take;if(chosen!=none)break;
    }
  }else {
    for(auto q:nb) {
      consider(q);
      if(!bland&&opt.pricing=="candidate-list"&&reduced(q)>0&&cache.size()<opt.candidate_limit)cache.push_back(q);
    }
  }
  stats.pricing_seconds+=seconds(begin);return chosen;
}
// `feasible` says whether the basis is expected to be primal feasible.  The
// dual phase deliberately runs through primal infeasible bases, so the closure
// test is asserted only where it must hold.
void Engine::check(bool feasible) {
  Index unanchored=0,nonbasic=0;
  Real weight=0;
  for(auto u:nodes){
    if(parent[u]==u&&!anchor[u])++unanchored;
    if(anchor[u]){++nonbasic;if(root[u]!=u)throw std::logic_error("anchor is not a root");}
    if(parent[u]!=u){
      ++nonbasic;Index e=parent_edge[u];auto a=g.arcs[e];
      if(!forest.contains(e)||!((a.tail==u&&a.head==parent[u])||(a.head==u&&a.tail==parent[u])))throw std::logic_error("invalid parent edge");
    }
    Real p=g.profit[u],w=g.weight[u];
    for(Index v=child[u];v!=n;v=sibling[v]){p+=subp[v];w+=subw[v];}
    if(!close(p,subp[u],opt)||!close(w,subw[u],opt))throw std::runtime_error("subtree aggregate mismatch");
    y[u]=root[u]==positive_root?1/subw[positive_root]:0;
    weight+=g.weight[u]*y[u];
  }
  if(unanchored!=1||nonbasic+1!=nodes.size()||nb.size()!=nonbasic||!close(weight,1,opt))throw std::logic_error("invalid forest basis count or normalization");
  if(feasible)for(auto e:edges)if(y[g.arcs[e].tail]>y[g.arcs[e].head])throw std::runtime_error("primal forest support is not closed");
}
// Riavvio a caldo sul residuo (opt.warm_start=residual).  Il blocco appena
// estratto e la componente positiva, cioe un albero della foresta di base: gli
// altri alberi sopravvivono intatti e restano ancorati a zero.  Si riusa quella
// foresta invece di ripartire dalla base vuota.
//
// Vincolo di ammissibilita: i valori valgono 1/w(T) sull'albero positivo T e
// zero altrove, quindi ogni arco attivo che esce da T violerebbe y_tail<=y_head
// se la testa fosse fuori.  L'albero positivo deve percio essere *chiuso* nel
// residuo.  Si sceglie il migliore per rapporto fra gli alberi chiusi; se non
// ne esiste nessuno la funzione fallisce e il chiamante riparte a freddo.
bool Engine::warm_restart() {
  for(Index e=0;e<m;++e)
    if(forest.contains(e)&&(!active[g.arcs[e].tail]||!active[g.arcs[e].head]))forest.cut(e);
  nodes.clear();edges.clear();nb.clear();cache.clear();cursor=0;zero_streak=0;
  bland=opt.entering_rule=="bland";
  std::fill(alpha.begin(),alpha.end(),0);
  std::fill(parent_edge.begin(),parent_edge.end(),m);
  for(Index i=0;i<n;++i)if(active[i])nodes.push_back(i);
  if(nodes.empty())return false;
  for(Index e=0;e<m;++e)if(active[g.arcs[e].tail]&&active[g.arcs[e].head])edges.push_back(e);
  // Componenti della foresta superstite: parent porta l'indice+1 dell'albero.
  // Serve un intero, non un char: gli alberi possono essere migliaia, e inset e
  // un vector<char> che andrebbe in overflow silenzioso.  parent viene comunque
  // ricostruito da rebuild() subito dopo.
  for(auto i:nodes)parent[i]=0;
  std::vector<Index>& members=collect;
  Index trees=0;Index best=n;Real best_ratio=0;bool found=false;
  std::vector<Index> roots;std::vector<Real> tp,tw;std::vector<char> closed;
  for(auto s:nodes){
    if(parent[s])continue;
    ++trees;members.clear();stack.clear();stack.push_back(s);parent[s]=trees;
    Real profit=0,weight=0;Index low=s;
    while(!stack.empty()){
      Index u=stack.back();stack.pop_back();members.push_back(u);
      profit+=g.profit[u];weight+=g.weight[u];low=std::min(low,u);
      for(Index slot=forest.first_slot(u);slot!=nil;slot=forest.next_slot(slot)){
        Index v=forest.other_endpoint(slot);
        if(!parent[v]){parent[v]=trees;stack.push_back(v);}
      }
    }
    // Un solo ancoraggio per albero: si tiene quello di indice minimo.
    for(auto u:members)anchor[u]=(u==low);
    roots.push_back(low);tp.push_back(profit);tw.push_back(weight);closed.push_back(1);
    if(weight<=0)closed.back()=0;
  }
  // Chiusura: nessun arco attivo puo uscire dall'albero positivo.
  for(auto e:edges){
    Index a=parent[g.arcs[e].tail],b=parent[g.arcs[e].head];
    if(a!=b)closed[a-1]=0;
  }
  for(Index t=0;t<trees;++t)if(closed[t]){
    Real ratio=tp[t]/tw[t];
    if(!found||ratio>best_ratio){found=true;best_ratio=ratio;best=t;}
  }
  if(!found)return false;
  anchor[roots[best]]=false;
  affected=nodes;rebuild(true);
  // Le non basiche sono i vertici ancorati piu gli slack degli archi di
  // foresta: insieme fanno |nodes|-1, come pretende check().
  for(auto i:nodes)if(anchor[i])nb.push_back(i);
  for(auto e:edges)if(forest.contains(e))nb.push_back(n+e);
  return true;
}
std::string Engine::run_residual() {
  if(opt.warm_start!="residual"||!warm_restart()){++stats.cold_restarts;return run();}
  ++stats.oracle_calls;++stats.warm_restarts;
  return primal_loop();
}
std::string Engine::run() { return opt.simplex=="dual"?run_dual():run_primal(); }
std::string Engine::run_primal() {
  initialize();++stats.oracle_calls;
  return primal_loop();
}
// The pivot loop proper, from whatever basis is currently installed.  The dual
// finishes through it, so a dual basis that loses feasibility numerically is
// repaired instead of abandoned, and the certificate is produced by the same
// verified code in both cases.
std::string Engine::primal_loop() {
  for(;;){
    if(opt.verify_every&&stats.pivots%opt.verify_every==0)check();
    if(opt.time_limit>0&&seconds(start)>=opt.time_limit)return "time_limit";
    Index q=price();
    if(q==none){
      check();
      for(auto v:nodes)if(parent[v]!=v){Index e=parent_edge[v];alpha[e]=-reduced(n+e);}
      return "optimal";
    }
    if(stats.pivots>=opt.iteration_limit)return "iteration_limit";
    Real rc=reduced(q);
    auto begin=Clock::now();
    for(auto i:nodes)dy[i]=0;
    Index r;Real sign=1;
    if(q<n)r=root[q];else{
      auto a=g.arcs[q-n];r=parent_edge[a.tail]==q-n?a.tail:a.head;sign=a.head==r?1:-1;
    }
    stack.clear();stack.push_back(r);collect.clear();
    while(!stack.empty()){
      Index u=stack.back();stack.pop_back();dy[u]=sign;collect.push_back(u);inset[u]=1;
      for(Index v=child[u];v!=n;v=sibling[v])stack.push_back(v);
    }
    Real kappa=sign*subw[r]/subw[positive_root];
    for(auto i:nodes){y[i]=root[i]==positive_root?1/subw[positive_root]:0;if(root[i]==positive_root)dy[i]-=kappa;}
    stats.direction_seconds+=seconds(begin);begin=Clock::now();
    Real step=std::numeric_limits<Real>::infinity();Index leave=none;
    // A zero step is the smallest possible one, so the scan may stop at the
    // first blocker that attains it.  Bland's rule needs the smallest index
    // among ties, so the shortcut is suspended while the fallback is active.
    const bool early=opt.ratio_test=="early"&&!bland;
    bool settled=false;
    auto consider=[&](Real z,Real d,Index b){
      if(settled||d>=0)return; // Strict sign: a fixed absolute tolerance can hide a blocker.
      Real t=z/(-d);
      if(t<step||(t==step&&b<leave)){step=t;leave=b;}
      if(early&&step==0){settled=true;++stats.early_exits;}
    };
    for(auto i:nodes)if(!anchor[i])consider(y[i],dy[i],i);
    auto arc=[&](Index e){
      auto a=g.arcs[e];
      if(forest.contains(e)||!active[a.tail]||!active[a.head])return;
      consider(y[a.head]-y[a.tail],dy[a.head]-dy[a.tail],n+e);++stats.ratio_arcs;
    };
    if(opt.ratio_test!="full"){
      // The direction is sign on the entering subtree S and -kappa on the
      // positive component P, zero elsewhere, so an arc can block only if it
      // crosses the boundary of S or of P.  P is closed, so a P-crossing arc
      // has its tail outside P; if that tail is also outside S the first sweep
      // would miss it, which is what the second sweep covers.
      for(auto u:collect){
        if(settled)break;
        for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k)arc(outgoing.edge[k]);
        for(Index k=incoming.offset[u];k<incoming.offset[u+1];++k)arc(incoming.edge[k]);
      }
      for(auto u:nodes)if(!settled&&root[u]!=positive_root&&!inset[u])
        for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k){
          Index e=outgoing.edge[k];
          if(root[g.arcs[e].head]==positive_root)arc(e);
        }
    }else for(auto e:edges){if(settled)break;arc(e);}
    for(auto u:collect)inset[u]=0;
    stats.ratio_test_seconds+=seconds(begin);
    if(leave==none||!std::isfinite(step)||step<0)return "numerical_failure";
    if(opt.trace){
      Pivot t;t.oracle=stats.oracle_calls-1;t.entering=q;t.leaving=leave;t.reduced=rc;t.step=step;t.rho=rho;
      t.active=nodes;t.nonbasic=nb;t.values.assign(n+m,0);t.direction.assign(n+m,0);
      for(auto i:nodes){t.values[i]=y[i];t.direction[i]=dy[i];}
      for(auto e:edges){auto a=g.arcs[e];t.values[n+e]=y[a.head]-y[a.tail];t.direction[n+e]=dy[a.head]-dy[a.tail];}
      trace.push_back(std::move(t));
    }
    bool diagnose=opt.verify_every&&stats.pivots%opt.verify_every==0;
    Real before=rho;
    if(diagnose){
      Real wd=0,pd=0;
      for(auto i:nodes){wd+=g.weight[i]*dy[i];pd+=g.profit[i]*dy[i];old_y[i]=y[i]+step*dy[i];}
      if(!close(wd,0,opt)||!close(pd,rc,opt))return "numerical_failure";
      for(auto b:nb){Real d=b<n?dy[b]:dy[g.arcs[b-n].head]-dy[g.arcs[b-n].tail];if(!close(d,b==q?1:0,opt))return "numerical_failure";}
    }
    affected.clear();collect.clear();gather(q);gather(leave);
    if(q<n)anchor[q]=false;else forest.cut(q-n);
    if(leave<n)anchor[leave]=true;else forest.link(leave-n);
    nb.erase(std::lower_bound(nb.begin(),nb.end(),q));
    nb.insert(std::lower_bound(nb.begin(),nb.end(),leave),leave);
    bool full=opt.basis_update=="full"||
      (opt.rebuild_interval&&(stats.pivots+1)%opt.rebuild_interval==0)||
      (opt.basis_update=="adaptive"&&static_cast<Real>(affected.size())>=opt.rebuild_fraction*static_cast<Real>(nodes.size()));
    rebuild(full);
    if(diagnose){
      check();
      for(auto i:nodes)if(!close(y[i],old_y[i],opt))return "numerical_failure";
      if(!close(rho,before+step*rc,opt))return "numerical_failure";
      // Independently rebuild metadata on all components and compare values/aggregates.
      old_y=subp;dy=subw;Real old_rho=rho;rebuild(true);
      for(auto i:nodes)if(!close(old_y[i],subp[i],opt)||!close(dy[i],subw[i],opt))return "numerical_failure";
      if(!close(old_rho,rho,opt))return "numerical_failure";
    }
    ++stats.pivots;
    // Anti-cycling: Bland's rule takes over after a run of zero-step pivots and
    // is released again by the first pivot with a positive step.  Termination
    // still holds: an episode is a genuine Bland run on a fixed basic solution,
    // so it cannot cycle, and each episode ends with a strict increase of the
    // ratio, so only finitely many episodes are possible.
    if(step==0){++stats.degenerate_pivots;++zero_streak;}
    else{
      zero_streak=0;
      if(bland&&opt.entering_rule!="bland"){bland=false;cache.clear();++stats.bland_releases;}
    }
    if(!bland&&zero_streak>=opt.degeneracy_trigger){bland=true;cache.clear();++stats.bland_fallbacks;}
  }
}
// Dual Forest Simplex.
//
// The primal loop is dominated by zero-step pivots because the basic solution
// puts every node outside the positive component at zero.  The dual is exposed
// to the opposite defect, degeneracy of the reduced costs, which here is caused
// only by ties between ratios and is therefore rare.  Two structural facts make
// the dual particularly simple on this problem:
//
//   * the node variables are never primal infeasible, since their value is
//     1/w(P) on the positive component P and zero elsewhere, so every primal
//     infeasibility is a precedence slack y_head - y_tail < 0, that is an arc
//     leaving P.  Choosing the leaving variable is a purely combinatorial
//     search for an unsatisfied prerequisite;
//   * the basis is primal feasible exactly when P is closed, which is the
//     stopping rule.
//
// The starting basis is dual feasible by construction: every node is its own
// tree and P is the node of maximum ratio, so the reduced cost of any other
// node k is w_k (p_k/w_k - rho) <= 0 and there are no forest edges yet.
void Engine::initialize_dual() {
  for(Index e=0;e<m;++e)if(forest.contains(e))forest.cut(e);
  nodes.clear();edges.clear();nb.clear();cache.clear();cursor=0;zero_streak=0;
  bland=false;
  std::fill(alpha.begin(),alpha.end(),0);
  std::fill(parent_edge.begin(),parent_edge.end(),m);
  for(Index i=0;i<n;++i)if(active[i]){nodes.push_back(i);anchor[i]=true;}
  for(Index e=0;e<m;++e)if(active[g.arcs[e].tail]&&active[g.arcs[e].head])edges.push_back(e);
  positive_root=n;
  Real best=0;
  for(auto i:nodes){
    Real ratio=g.profit[i]/g.weight[i];
    if(positive_root==n||ratio>best){best=ratio;positive_root=i;}
  }
  if(positive_root==n)throw std::logic_error("empty residual");
  anchor[positive_root]=false;
  for(auto i:nodes)if(anchor[i])nb.push_back(i);
  affected=nodes;rebuild(true);
  if(opt.dual_leaving=="incremental")seed_violations();
}
// The only primal infeasibilities are the arcs that leave the positive
// component.  The smallest arc index is taken so that the choice is
// deterministic and independent of adjacency order.
// Incremental maintenance of the arcs that leave the positive component.  The
// scanning rules re-examine the whole component at every pivot, which is the
// largest single cost of the dual loop; here only the nodes whose membership
// changed are examined, and stale entries are discarded when they are popped.
void Engine::seed_violations() {
  violated.clear();
  std::fill(queued.begin(),queued.end(),0);
  for(auto u:nodes)positive[u]=root[u]==positive_root;
  for(Index u=positive_root;u!=n;u=member_next[u])
    for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k){
      Index e=outgoing.edge[k];Index h=g.arcs[e].head;
      if(active[h]&&!positive[h]&&!queued[e]){queued[e]=1;violated.push_back(e);}
    }
}
void Engine::refresh_violations() {
  auto push=[&](Index e){if(!queued[e]){queued[e]=1;violated.push_back(e);}};
  for(auto u:affected){
    bool now=root[u]==positive_root;
    if(now==(positive[u]!=0))continue;
    positive[u]=now?1:0;
    if(now){
      for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k){
        Index e=outgoing.edge[k];Index h=g.arcs[e].head;
        if(active[h]&&root[h]!=positive_root)push(e);
      }
    }else{
      for(Index k=incoming.offset[u];k<incoming.offset[u+1];++k){
        Index e=incoming.edge[k];Index t=g.arcs[e].tail;
        if(active[t]&&root[t]==positive_root)push(e);
      }
    }
  }
}
Index Engine::violation() {
  // Every violated slack has the same value, -1/w(P), so the classical "most
  // infeasible row" rule cannot discriminate and a structural criterion is
  // needed.  "first" is the dual analogue of Bland's rule and is the reference;
  // the others prefer the prerequisite that looks most worth repairing.
  if(opt.dual_leaving=="incremental"){
    // Last in, first out over the maintained list, dropping stale entries as
    // they surface.  Scanning the list for the smallest index instead was
    // measured and is slower: it restores the pivot sequence of the "first"
    // rule but costs a pass over the list at every pivot, and on a sparse DAG
    // of two thousand nodes it doubled the running time.
    while(!violated.empty()){
      Index e=violated.back();
      auto a=g.arcs[e];
      ++stats.violations_scanned;
      if(active[a.tail]&&active[a.head]&&root[a.tail]==positive_root&&root[a.head]!=positive_root)return n+e;
      violated.pop_back();queued[e]=0;
    }
    return none;
  }
  Index found=m;Real best=0;
  for(Index u=positive_root;u!=n;u=member_next[u])
    for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k){
      Index e=outgoing.edge[k];
      ++stats.violations_scanned;
      Index h=g.arcs[e].head;
      if(!active[h]||root[h]==positive_root)continue;
      if(opt.dual_leaving=="first"){if(e<found)found=e;continue;}
      Real score;
      if(opt.dual_leaving=="best-head")score=g.profit[h]/g.weight[h];
      else if(opt.dual_leaving=="largest-tree")score=subw[root[h]];
      else score=subp[root[h]]-rho*subw[root[h]];
      if(found==m||score>best||(score==best&&e<found)){best=score;found=e;}
    }
  return found==m?none:n+found;
}
// Row of the leaving basic slack over the nonbasic variables.  Entering a
// nonbasic q by one unit moves every node by
//   dy_u(q) = sigma_q [u in S_q] - kappa_q [u in P],
// with S_q the whole tree of an anchored node, or the subtree below a forest
// edge.  The row of the slack of arc (t,h) is the difference of the two node
// entries, so it is nonzero only for the anchor of each endpoint's tree, for
// the forest edges on the two paths to their roots, and through the rank-one
// term kappa_q whenever exactly one endpoint lies in P.
void Engine::pivot_row(Index leaving) {
  auto a=g.arcs[leaving-n];
  Real weight=subw[positive_root];
  collect.clear();
  for(Index u=a.head;;u=parent[u]){if(!inset[u])collect.push_back(u);inset[u]|=1;if(parent[u]==u)break;}
  for(Index u=a.tail;;u=parent[u]){if(!inset[u])collect.push_back(u);inset[u]|=2;if(parent[u]==u)break;}
  Real correction=(root[a.head]==positive_root?1:0)-(root[a.tail]==positive_root?1:0);
  row.resize(nb.size());
  for(Index at=0;at<nb.size();++at){
    Index q=nb[at];
    Real sign=1,structural;
    Index component;
    if(q<n){
      component=q;
      structural=(root[a.head]==q?1:0)-(root[a.tail]==q?1:0);
    }else{
      Index e=q-n;auto b=g.arcs[e];
      component=parent_edge[b.tail]==e?b.tail:b.head;
      sign=b.head==component?1:-1;
      structural=sign*(((inset[component]&1)?1:0)-((inset[component]&2)?1:0));
    }
    row[at]=structural-sign*(subw[component]/weight)*correction;
  }
  for(auto u:collect)inset[u]=0;
}
std::string Engine::run_dual() {
  initialize_dual();++stats.oracle_calls;
  for(;;){
    if(opt.verify_every&&stats.pivots%opt.verify_every==0)check(false);
    if(opt.time_limit>0&&seconds(start)>=opt.time_limit)return "time_limit";
    auto begin=Clock::now();
    Index leaving=violation();
    stats.ratio_test_seconds+=seconds(begin);
    if(leaving==none){
      check();
      for(auto v:nodes)if(parent[v]!=v){Index e=parent_edge[v];alpha[e]=-reduced(n+e);}
      return "optimal";
    }
    if(stats.pivots>=opt.iteration_limit)return "iteration_limit";
    begin=Clock::now();
    pivot_row(leaving);
    stats.direction_seconds+=seconds(begin);
    begin=Clock::now();
    // Dual ratio test: keep every reduced cost nonpositive.  Bland's dual rule
    // takes over in degeneracy and is released by the first pivot with a
    // positive step, exactly as on the primal side.
    Index entering=none;Real step=std::numeric_limits<Real>::infinity();
    bool infeasible=false;
    for(Index at=0;at<nb.size();++at){
      Index q=nb[at];
      ++stats.candidates_examined;
      Real coefficient=row[at];
      if(coefficient<=0)continue;
      Real cost=-reduced(q);
      // Same scale as the primal pricing test: a reduced cost is judged against
      // the magnitude of the aggregates it is built from, not against itself.
      Index component=q<n?root[q]:(parent_edge[g.arcs[q-n].tail]==q-n?g.arcs[q-n].tail:g.arcs[q-n].head);
      Real tol=opt.optimality_abs_tol+opt.optimality_rel_tol*
               std::max(std::fabs(subp[component]),std::fabs(rho*subw[component]));
      if(cost<-tol){infeasible=true;break;}
      // Smallest index among the columns attaining the minimum ratio: this is
      // already Bland's dual rule, and the leaving arc is chosen by smallest
      // index too, so no separate fallback is needed or admissible here.
      Real candidate=std::max(Real(0),cost)/coefficient;
      if(candidate<step||(candidate==step&&q<entering)){step=candidate;entering=q;}
    }
    stats.pricing_seconds+=seconds(begin);
    // Dual feasibility lost to rounding, or no admissible column: hand the
    // current basis to the primal loop, which is the verified reference and
    // needs no restart.
    // The primal loop needs a primal feasible basis, so the fallback restarts
    // from the primal initialization rather than inheriting the dual's basis.
    if(infeasible||entering==none){++stats.dual_handoffs;initialize();return primal_loop();}
    if(opt.trace){
      Pivot t;t.oracle=stats.oracle_calls-1;t.entering=entering;t.leaving=leaving;
      t.reduced=reduced(entering);t.step=step;t.rho=rho;t.active=nodes;t.nonbasic=nb;
      trace.push_back(std::move(t));
    }
    affected.clear();collect.clear();gather(entering);gather(leaving);
    if(entering<n)anchor[entering]=false;else forest.cut(entering-n);
    if(leaving<n)anchor[leaving]=true;else forest.link(leaving-n);
    nb.erase(std::lower_bound(nb.begin(),nb.end(),entering));
    nb.insert(std::lower_bound(nb.begin(),nb.end(),leaving),leaving);
    bool full=opt.basis_update=="full"||
      (opt.rebuild_interval&&(stats.pivots+1)%opt.rebuild_interval==0)||
      (opt.basis_update=="adaptive"&&static_cast<Real>(affected.size())>=opt.rebuild_fraction*static_cast<Real>(nodes.size()));
    rebuild(full);
    if(opt.dual_leaving=="incremental"){
      if(full){seed_violations();}else refresh_violations();
    }
    ++stats.pivots;++stats.dual_pivots;
    if(step==0)++stats.dual_degenerate;
  }
}
void Engine::remove_support(std::vector<Index>& block) {
  support(block,false);
  for(auto u:block)active[u]=false;
}
void Engine::support(std::vector<Index>& block,bool maximal) {
  block.clear();
  if(!maximal){
    for(Index u=positive_root;u!=n;u=member_next[u])block.push_back(u);
    return;
  }
  // Complementarity: exclude strictly positive node residuals; propagate
  // backwards along precedence arcs and forwards along positive dual arcs.
  // The complement is the largest closure attaining the certified ratio.
  std::vector<char> excluded(n,false);
  stack.clear();
  for(auto u:nodes)if(anchor[u]){
    Real tol=opt.optimality_abs_tol+opt.optimality_rel_tol*std::max(std::fabs(subp[u]),std::fabs(rho*subw[u]));
    if(reduced(u)<-tol){excluded[u]=true;stack.push_back(u);}
  }
  while(!stack.empty()){
    Index u=stack.back();stack.pop_back();
    auto exclude=[&](Index v){if(active[v]&&!excluded[v]){excluded[v]=true;stack.push_back(v);}};
    for(Index k=incoming.offset[u];k<incoming.offset[u+1];++k)exclude(g.arcs[incoming.edge[k]].tail);
    for(Index k=outgoing.offset[u];k<outgoing.offset[u+1];++k){
      Index e=outgoing.edge[k];
      if(alpha[e]>0)exclude(g.arcs[e].head);
    }
  }
  for(auto u:nodes)if(!excluded[u])block.push_back(u);
  if(block.empty())throw std::runtime_error("empty maximal optimal support");
}
} // namespace pclp
