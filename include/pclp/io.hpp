#pragma once
#include "core.hpp"
#include <nlohmann/json.hpp>
namespace pclp {
using Json=nlohmann::json;
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Options,algorithm,basis_update,pricing,entering_rule,canonicalization,node_order,transitive_reduction,initial_basis,ratio_test,simplex,dual_leaving,warm_start,initial_seeds,seed,pricing_block_size,candidate_limit,rebuild_interval,degeneracy_trigger,rebuild_fraction,iteration_limit,verify_every,time_limit,feasibility_abs_tol,feasibility_rel_tol,optimality_abs_tol,optimality_rel_tol,trace)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Statistics,pivots,degenerate_pivots,oracle_calls,full_rebuilds,local_rebuilds,rebuilt_nodes,candidates_examined,ratio_arcs,bland_fallbacks,bland_releases,early_exits,flow_solves,flow_augmentations,flow_phases,removed_arcs,seed_closures,seeded_nodes,warm_restarts,cold_restarts,dual_pivots,dual_degenerate,violations_scanned,dual_handoffs,preprocessing_seconds,pricing_seconds,direction_seconds,ratio_test_seconds,update_seconds,certification_seconds,total_seconds)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Pivot,oracle,entering,leaving,reduced,step,rho,active,nonbasic,values,direction)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Certificate,beta,alpha,residual,feasible)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(RatioResult,status,message,ratio,support,certificate,pivots,degenerate_pivots,stats,trace)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Macroitem,ratio,profit,weight,nodes)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(PathResult,status,message,macroitems,node_bound,alpha,prefix_weight,prefix_profit,complete,positive_complete,oracle_calls,pivots,degenerate_pivots,stats,trace)
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(SolveResult,status,message,objective,capacity,used_weight,lambda,dual_bound,gap,solution,mu,alpha,path)
Json read_json(const std::string&);
Instance read_instance(const Json&);
Json migrate_options(Json);
Options read_options(const Json&);
Real parse_number(const Json&);
void write_result(const std::string& path,const Json&);
} // namespace pclp
