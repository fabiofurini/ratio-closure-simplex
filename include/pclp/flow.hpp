#pragma once
#include "pclp/core.hpp"
namespace pclp {
// Maximum-closure network of a precedence graph: s -> i with capacity max(0,e_i),
// i -> t with capacity max(0,-e_i) and one infinite arc per precedence pair.
// The source side of a minimum cut is a closure attaining max sum(e_i) over closures.
class ClosureFlow {
 public:
  explicit ClosureFlow(const Instance& condensed);
  // Solves the network for the given node excesses, ignoring masked-out nodes.
  // Returns the maximum closure value; throws on a numerical breakdown.
  Real solve(const std::vector<Real>& excess, const std::vector<char>& mask);
  // Minimal source side: nodes reachable from s. Maximal source side: the
  // complement of the nodes that reach t. Both are closures of equal value.
  void source_side(std::vector<char>& side, bool maximal);
  [[nodiscard]] Real arc_flow(Index arc) const { return flow_[2 * arc]; }
  Index maxflows = 0, augmentations = 0, phases = 0;
 private:
  const Instance& g_;
  Index n_, m_, source_, sink_, vertices_, none_;
  std::vector<Index> head_, first_, next_, level_, cursor_, queue_, stack_;
  std::vector<Real> capacity_, flow_;
  const std::vector<char>* mask_ = nullptr;
  Real epsilon_ = 0;
  bool layer();
  Real blocking();
  void reach(std::vector<char>& seen, Index from, bool backward);
};
} // namespace pclp
