#pragma once
#include "core.hpp"
namespace pclp {
struct CSR {
  std::vector<Index> offset, edge;
  CSR(Index n, const std::vector<Arc>& arcs, bool reverse);
};
struct Prepared {
  const Instance& original;
  CSR out, in;
  Instance graph;
  std::vector<Index> component, representative, members, offsets;
  std::vector<Index> inward_parent, outward_parent, inward_order, outward_order;
  Real profit_scale = 1, weight_scale = 1;
  // Arcs dropped by the optional transitive reduction, and whether the exact
  // reduction fitted in the reachability budget.  A partial run drops nothing.
  Index removed_arcs = 0;
  bool transitively_reduced = false;
  explicit Prepared(const Instance&, const Options& = {});
  std::vector<Real> lift(const std::vector<Real>& alpha, const std::vector<Real>& bound) const;
 private:
  void reduce(Index condensed_nodes);
};
} // namespace pclp
