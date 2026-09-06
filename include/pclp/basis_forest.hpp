#pragma once

#include "pclp/core.hpp"

#include <cstddef>
#include <vector>

namespace pclp {

// A mutable subset of a fixed edge list.  It deliberately does not implement
// a general dynamic-graph API: Forest Simplex maintains the acyclicity
// invariant, while this type makes the two operations used by a pivot cheap.
class BasisForest {
 public:
  BasisForest(std::size_t node_count, const std::vector<Arc>& edges);

  [[nodiscard]] bool contains(std::size_t edge) const;
  void link(std::size_t edge);
  void cut(std::size_t edge);

  [[nodiscard]] std::size_t first_slot(std::size_t node) const;
  [[nodiscard]] std::size_t next_slot(std::size_t slot) const;
  [[nodiscard]] std::size_t edge_of_slot(std::size_t slot) const;
  [[nodiscard]] std::size_t other_endpoint(std::size_t slot) const;
  [[nodiscard]] static constexpr std::size_t npos() { return static_cast<std::size_t>(-1); }

 private:
  const std::vector<Arc>& edges_;
  std::vector<std::size_t> first_;
  std::vector<std::size_t> next_;
  std::vector<std::size_t> previous_;
  std::vector<char> present_;

  [[nodiscard]] std::size_t owner(std::size_t slot) const;
  void attach(std::size_t slot);
  void detach(std::size_t slot);
};

}  // namespace pclp
