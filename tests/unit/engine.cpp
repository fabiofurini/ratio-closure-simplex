#include "pclp/engine.hpp"
#include "pclp/sha256.hpp"
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
namespace {
std::atomic<std::size_t> allocations{0};
std::atomic<bool> count_allocations{false};
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
}
void* operator new(std::size_t size){
  if(count_allocations)++allocations;
  if(void* p=std::malloc(size?size:1))return p;
  throw std::bad_alloc();
}
void* operator new[](std::size_t size){return ::operator new(size);}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete[](void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
void operator delete[](void* p,std::size_t)noexcept{std::free(p);}
int main(){
  using namespace pclp;
  require(sha256("")=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","SHA empty");
  require(sha256("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","SHA abc");
  Instance g;
  for(Index i=0;i<256;++i){g.node_ids.push_back(std::to_string(i));g.profit.push_back(i%2?-1:3);g.weight.push_back(1);}
  for(Index i=0;i<256;i+=2)g.arcs.push_back({i,i+1});
  Options local;local.rebuild_interval=0;
  Statistics ls;std::vector<Pivot> log;
  Engine fast(g,local,ls,log,Clock::now());
  allocations=0;count_allocations=true;
  auto status=fast.run();
  count_allocations=false;
  require(status=="optimal","local solve");
  require(allocations==0,"heap allocation inside untraced oracle pivot loop");
  Options full=local;full.basis_update="full";Statistics fs;
  Engine reference(g,full,fs,log,Clock::now());
  require(reference.run()=="optimal","full solve");
  require(fast.rho==reference.rho&&ls.pivots==fs.pivots,"full/local disagree");
  require(ls.rebuilt_nodes<fs.rebuilt_nodes,"local updates failed to avoid untouched trees");
  require(ls.candidates_examined==(ls.pivots+1)*(g.node_ids.size()-1),"pricing scans more than n-1 nonbasic candidates");
  // Deep SCC: iterative preprocessing and original-arc dual lifting.
  Instance cycle;
  constexpr Index n=30000;
  for(Index i=0;i<n;++i){cycle.node_ids.push_back(std::to_string(i));cycle.profit.push_back(i%2?-1:3);cycle.weight.push_back(1);cycle.arcs.push_back({i,(i+1)%n});}
  auto ratio=ratio_closure_ratio(cycle);
  require(ratio.status=="optimal"&&ratio.support.size()==n&&ratio.ratio==1,"deep SCC and certificate lift");
  cycle.arcs.pop_back();
  for(auto& p:cycle.profit)p=1;
  auto chain=canonical_path(cycle,true);
  require(chain.status=="optimal"&&chain.macroitems.size()==1&&chain.macroitems[0].nodes.size()==n,"deep DAG chain");
  auto path=canonical_path(g,true);
  require(path.status=="optimal"&&path.macroitems.size()==1&&path.oracle_calls==1,"dual maximal union of tied components");
  for(Real c:{Real(0),Real(1),Real(100),Real(1000)}) {
    auto solution=solve_from_path(g,c,path);
    require(solution.status=="optimal"&&solution.objective==value_from_path(path,c),"many-capacity query");
  }
  std::cout<<"no pivot allocations; local rebuilt "<<ls.rebuilt_nodes<<" versus "<<fs.rebuilt_nodes<<"; deep SCC: "<<n<<" nodes\n";
}
