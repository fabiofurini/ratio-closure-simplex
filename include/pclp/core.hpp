#pragma once
#include <cstddef>
#include <string>
#include <vector>
namespace pclp {
using Real = long double;
using Index = std::size_t;
struct Arc { Index tail, head; };
struct Instance {
  std::string id;
  std::vector<std::string> node_ids;
  std::vector<Real> profit, weight;
  std::vector<Arc> arcs;
  Real capacity = 0;
  bool has_capacity = false;
};
struct Options {
  std::string algorithm = "ratio-closure";
  std::string basis_update = "local", pricing = "full", entering_rule = "bland";
  std::string canonicalization = "dual";
  std::string node_order = "input", transitive_reduction = "off";
  std::string initial_basis = "sink", ratio_test = "full", simplex = "primal";
  std::string dual_leaving = "first";
  std::string warm_start = "off";
  Index initial_seeds = 8, seed = 0;
  Index pricing_block_size = 64, candidate_limit = 32;
  Index rebuild_interval = 256, degeneracy_trigger = 32;
  Real rebuild_fraction = 0.5L;
  Index iteration_limit = 1000000, verify_every = 0;
  Real time_limit = 0;
  Real feasibility_abs_tol = 1e-12L, feasibility_rel_tol = 1e-10L;
  Real optimality_abs_tol = 1e-18L, optimality_rel_tol = 1e-14L;
  bool trace = false;
};
struct Statistics {
  Index pivots = 0, degenerate_pivots = 0, oracle_calls = 0;
  Index full_rebuilds = 0, local_rebuilds = 0, rebuilt_nodes = 0;
  Index candidates_examined = 0, ratio_arcs = 0, bland_fallbacks = 0, bland_releases = 0, early_exits = 0;
  Index flow_solves = 0, flow_augmentations = 0, flow_phases = 0;
  Index removed_arcs = 0, seed_closures = 0, seeded_nodes = 0;
  Index warm_restarts = 0, cold_restarts = 0;
  Index dual_pivots = 0, dual_degenerate = 0, violations_scanned = 0, dual_handoffs = 0;
  Real preprocessing_seconds = 0, pricing_seconds = 0, direction_seconds = 0;
  Real ratio_test_seconds = 0, update_seconds = 0, certification_seconds = 0, total_seconds = 0;
};
struct Pivot {
  Index oracle = 0, entering = 0, leaving = 0;
  Real reduced = 0, step = 0, rho = 0;
  std::vector<Index> active, nonbasic;
  std::vector<Real> values, direction;
};
struct Certificate {
  Real beta = 0;
  std::vector<Real> alpha, residual;
  bool feasible = false;
};
struct RatioResult {
  std::string status, message;
  Real ratio = 0;
  std::vector<Index> support;
  Certificate certificate;
  Index pivots = 0, degenerate_pivots = 0;
  Statistics stats;
  std::vector<Pivot> trace;
};
struct Macroitem {
  Real ratio = 0, profit = 0, weight = 0;
  std::vector<Index> nodes;
};
struct PathResult {
  std::string status, message;
  std::vector<Macroitem> macroitems;
  // Compact blockwise dual: w_i * node_bound_i + div(alpha)_i >= p_i.
  std::vector<Real> node_bound, alpha;
  std::vector<Real> prefix_weight, prefix_profit;
  bool complete = false, positive_complete = false;
  Index oracle_calls = 0, pivots = 0, degenerate_pivots = 0;
  Statistics stats;
  std::vector<Pivot> trace;
};
struct SolveResult {
  std::string status, message;
  Real objective = 0, capacity = 0, used_weight = 0;
  Real lambda = 0, dual_bound = 0, gap = 0;
  std::vector<Real> solution, mu, alpha;
  PathResult path;
};
void validate(const Instance&);
void validate(const Options&);
// "ratio-closure" is the canonical value; "closure-simplex" is the short form.
// "forest" is the legacy spelling, accepted on input so that configurations
// saved before the rename keep resolving to the same algorithm.
inline bool uses_ratio_closure(const Options& o) {
  return o.algorithm=="ratio-closure"||o.algorithm=="closure-simplex"||o.algorithm=="forest";
}
RatioResult ratio_closure_ratio(const Instance&, const std::vector<Index>& active_nodes = {}, const Options& = {});
PathResult canonical_path(const Instance&, bool positive_only, const Options& = {});
RatioResult flow_ratio(const Instance&, const Options& = {});
PathResult flow_path(const Instance&, bool positive_only, const Options& = {});
// Backend dispatch on Options::algorithm; every backend returns the same
// certified structures and is checked by the same verifiers.
RatioResult max_ratio(const Instance&, const Options& = {});
PathResult decompose(const Instance&, bool positive_only, const Options& = {});
SolveResult solve(const Instance&, Real capacity, const Options& = {});
SolveResult solve_from_path(const Instance&, Real capacity, const PathResult&, const Options& = {});
Real value_from_path(const PathResult&, Real capacity);
bool verify_ratio(const Instance&, const RatioResult&, const Options& = {});
bool verify_path(const Instance&, const PathResult&, const Options& = {});
bool verify_solution(const Instance&, const SolveResult&, const Options& = {});
} // namespace pclp
