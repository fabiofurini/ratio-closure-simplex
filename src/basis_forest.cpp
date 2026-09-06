#include "pclp/basis_forest.hpp"

#include <stdexcept>

namespace pclp {

BasisForest::BasisForest(std::size_t node_count, const std::vector<Arc>& edges)
    : edges_(edges), first_(node_count, npos()), next_(2 * edges.size(), npos()),
      previous_(2 * edges.size(), npos()), present_(edges.size(), false) {
  for (const Arc& edge : edges_) {
    if (edge.tail >= node_count || edge.head >= node_count || edge.tail == edge.head) {
      throw std::invalid_argument("dynamic forest requires valid non-loop edges");
    }
  }
}

bool BasisForest::contains(std::size_t edge) const {
  if (edge >= present_.size()) throw std::out_of_range("forest edge index");
  return present_[edge];
}

std::size_t BasisForest::owner(std::size_t slot) const {
  const Arc& edge = edges_[edge_of_slot(slot)];
  return (slot & 1U) == 0U ? edge.tail : edge.head;
}

void BasisForest::attach(std::size_t slot) {
  const std::size_t node = owner(slot);
  const std::size_t old_first = first_[node];
  previous_[slot] = npos();
  next_[slot] = old_first;
  if (old_first != npos()) previous_[old_first] = slot;
  first_[node] = slot;
}

void BasisForest::detach(std::size_t slot) {
  const std::size_t node = owner(slot);
  const std::size_t before = previous_[slot];
  const std::size_t after = next_[slot];
  if (before == npos()) first_[node] = after;
  else next_[before] = after;
  if (after != npos()) previous_[after] = before;
  next_[slot] = npos();
  previous_[slot] = npos();
}

void BasisForest::link(std::size_t edge) {
  if (edge >= present_.size()) throw std::out_of_range("forest edge index");
  if (present_[edge]) throw std::logic_error("edge is already in the forest");
  attach(2 * edge);
  attach(2 * edge + 1);
  present_[edge] = true;
}

void BasisForest::cut(std::size_t edge) {
  if (edge >= present_.size()) throw std::out_of_range("forest edge index");
  if (!present_[edge]) throw std::logic_error("edge is not in the forest");
  detach(2 * edge);
  detach(2 * edge + 1);
  present_[edge] = false;
}

std::size_t BasisForest::first_slot(std::size_t node) const {
  if (node >= first_.size()) throw std::out_of_range("forest node index");
  return first_[node];
}

std::size_t BasisForest::next_slot(std::size_t slot) const {
  if (slot >= next_.size()) throw std::out_of_range("forest slot index");
  return next_[slot];
}

std::size_t BasisForest::edge_of_slot(std::size_t slot) const {
  if (slot >= next_.size()) throw std::out_of_range("forest slot index");
  return slot / 2;
}

std::size_t BasisForest::other_endpoint(std::size_t slot) const {
  const Arc& edge = edges_[edge_of_slot(slot)];
  return (slot & 1U) == 0U ? edge.head : edge.tail;
}

}  // namespace pclp
