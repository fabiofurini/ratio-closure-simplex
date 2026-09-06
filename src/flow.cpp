#include "pclp/flow.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace pclp {
ClosureFlow::ClosureFlow(const Instance& g)
 :g_(g),n_(g.node_ids.size()),m_(g.arcs.size()),source_(n_),sink_(n_+1),vertices_(n_+2),none_(2*(m_+2*n_)+1),
  head_(2*(m_+2*n_)),first_(vertices_,none_),next_(2*(m_+2*n_),none_),level_(vertices_),cursor_(vertices_),
  capacity_(2*(m_+2*n_),0),flow_(2*(m_+2*n_),0) {
  queue_.reserve(vertices_);stack_.reserve(vertices_);
  auto attach=[&](Index slot,Index tail,Index head){head_[slot]=head;next_[slot]=first_[tail];first_[tail]=slot;};
  for(Index e=0;e<m_;++e){attach(2*e,g.arcs[e].tail,g.arcs[e].head);attach(2*e+1,g.arcs[e].head,g.arcs[e].tail);}
  for(Index i=0;i<n_;++i){
    attach(2*m_+2*i,source_,i);attach(2*m_+2*i+1,i,source_);
    attach(2*m_+2*n_+2*i,i,sink_);attach(2*m_+2*n_+2*i+1,sink_,i);
  }
}
Real ClosureFlow::solve(const std::vector<Real>& excess,const std::vector<char>& mask) {
  if(excess.size()!=n_||mask.size()!=n_)throw std::logic_error("excess/mask size mismatch");
  mask_=&mask;++maxflows;
  std::fill(flow_.begin(),flow_.end(),Real(0));
  std::fill(capacity_.begin(),capacity_.end(),Real(0));
  Real positive=0,negative=0;
  for(Index i=0;i<n_;++i){
    if(!mask[i])continue;
    if(!std::isfinite(excess[i]))throw std::runtime_error("nonfinite closure excess");
    if(excess[i]>0){capacity_[2*m_+2*i]=excess[i];positive+=excess[i];}
    else if(excess[i]<0){capacity_[2*m_+2*n_+2*i]=-excess[i];negative-=excess[i];}
  }
  Real unbounded=1+positive+negative;
  for(Index e=0;e<m_;++e)if(mask[g_.arcs[e].tail]&&mask[g_.arcs[e].head])capacity_[2*e]=unbounded;
  epsilon_=std::max(std::numeric_limits<Real>::min(),Real(1e-16L)*std::max(Real(1),positive+negative));
  Real cut=0;
  for(Index phase=0;phase<vertices_+2;++phase){
    if(!layer())return positive-cut;
    ++phases;
    Real pushed=blocking();
    if(pushed<=0)return positive-cut;
    cut+=pushed;
  }
  throw std::runtime_error("maximum-flow phase limit reached");
}
bool ClosureFlow::layer() {
  std::fill(level_.begin(),level_.end(),none_);
  queue_.clear();queue_.push_back(source_);level_[source_]=0;
  for(Index at=0;at<queue_.size();++at){
    Index u=queue_[at];
    for(Index k=first_[u];k!=none_;k=next_[k]){
      Index v=head_[k];
      if(level_[v]==none_&&capacity_[k]-flow_[k]>epsilon_){level_[v]=level_[u]+1;queue_.push_back(v);}
    }
  }
  for(Index u=0;u<vertices_;++u)cursor_[u]=first_[u];
  return level_[sink_]!=none_;
}
Real ClosureFlow::blocking() {
  Real total=0;
  stack_.clear();
  Index u=source_;
  for(;;){
    if(u==sink_){
      Real bottleneck=std::numeric_limits<Real>::infinity();
      for(auto k:stack_)bottleneck=std::min(bottleneck,capacity_[k]-flow_[k]);
      Index cut=stack_.size();
      for(Index at=0;at<stack_.size();++at){
        Index k=stack_[at];flow_[k]+=bottleneck;flow_[k^1]-=bottleneck;
        if(cut==stack_.size()&&capacity_[k]-flow_[k]<=epsilon_)cut=at;
      }
      total+=bottleneck;++augmentations;
      stack_.resize(cut);
      u=stack_.empty()?source_:head_[stack_.back()];
      continue;
    }
    Index k=cursor_[u];
    while(k!=none_&&!(level_[head_[k]]==level_[u]+1&&capacity_[k]-flow_[k]>epsilon_))k=next_[k];
    cursor_[u]=k;
    if(k!=none_){stack_.push_back(k);u=head_[k];continue;}
    level_[u]=none_;
    if(u==source_)break;
    stack_.pop_back();
    u=stack_.empty()?source_:head_[stack_.back()];
    cursor_[u]=next_[cursor_[u]];
  }
  return total;
}
void ClosureFlow::reach(std::vector<char>& seen,Index from,bool backward) {
  std::fill(seen.begin(),seen.end(),0);
  queue_.clear();queue_.push_back(from);seen[from]=1;
  for(Index at=0;at<queue_.size();++at){
    Index u=queue_[at];
    for(Index k=first_[u];k!=none_;k=next_[k]){
      Index v=head_[k],residual=backward?(k^1):k;
      if(!seen[v]&&capacity_[residual]-flow_[residual]>epsilon_){seen[v]=1;queue_.push_back(v);}
    }
  }
}
void ClosureFlow::source_side(std::vector<char>& side,bool maximal) {
  if(!mask_)throw std::logic_error("source_side requires a solved network");
  std::vector<char> seen(vertices_,0);
  reach(seen,maximal?sink_:source_,maximal);
  side.assign(n_,0);
  for(Index i=0;i<n_;++i)side[i]=(*mask_)[i]&&(maximal?!seen[i]:seen[i]);
}
} // namespace pclp
