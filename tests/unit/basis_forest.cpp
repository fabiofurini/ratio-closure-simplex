#include "pclp/basis_forest.hpp"

#include <stdexcept>
#include <vector>

int main() {
  const std::vector<pclp::Arc> edges{{0, 1}, {1, 2}, {2, 3}, {0, 3}};
  pclp::BasisForest forest(4, edges);
  forest.link(0);
  forest.link(1);
  forest.link(2);
  if(!(forest.contains(0) && forest.contains(1) && forest.contains(2)))throw std::runtime_error("link membership");
  if(forest.edge_of_slot(forest.first_slot(1)) != 1U)throw std::runtime_error("adjacency order");
  forest.cut(1);
  if(forest.contains(1))throw std::runtime_error("cut membership");
  forest.link(3);
  if(!forest.contains(3))throw std::runtime_error("relink membership");
  std::size_t seen = 0;
  for (auto slot = forest.first_slot(0); slot != pclp::BasisForest::npos(); slot = forest.next_slot(slot)) ++seen;
  if(seen!=2U)throw std::runtime_error("degree after cut/link");
}
