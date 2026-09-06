#pragma once
#include "basis_forest.hpp"
#include "graph.hpp"
#include <chrono>
namespace pclp {
using Clock = std::chrono::steady_clock;
inline Real seconds(Clock::time_point start){return std::chrono::duration<Real>(Clock::now()-start).count();}
// One workspace per solve/path. Normal untraced pivots perform no allocations.
class Engine {
 public:
  const Instance& g;
  const Options& opt;
  Statistics& stats;
  std::vector<Pivot>& trace;
  Clock::time_point start;
  Index n,m,none,positive_root=0;
  BasisForest forest;
  CSR outgoing,incoming;
  std::vector<char> active,anchor,inset,best_set,positive,queued;
  std::vector<Index> nodes,edges,nb,root,parent,parent_edge,child,sibling,member_next;
  std::vector<Index> stack,order,affected,collect,cache,violated;
  std::vector<Real> subp,subw,dy,y,old_y,alpha,row;
  Real rho=0;
  Engine(const Instance&,const Options&,Statistics&,std::vector<Pivot>&,Clock::time_point);
  std::string run();
  // Warm restart on the residual: reuse the forest of the previous final basis.
  std::string run_residual();
  bool warm_restart();
  std::string run_primal();
  std::string primal_loop();
  std::string run_dual();
  void remove_support(std::vector<Index>&);
  void support(std::vector<Index>&,bool maximal);
 private:
  Index cursor=0,zero_streak=0;
  bool bland=false;
  void initialize();
  bool seed_closure();
  void initialize_dual();
  Index violation();
  void seed_violations();
  void refresh_violations();
  void pivot_row(Index leaving);
  void rebuild(bool full);
  void gather(Index variable);
  Real reduced(Index variable) const;
  Index price();
  void check(bool feasible = true);
};
} // namespace pclp
