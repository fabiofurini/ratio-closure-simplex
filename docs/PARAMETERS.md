# Parameters

Every implementation choice is an explicit option, so that an experiment can
change one thing at a time. Precedence is defaults, then `--config FILE`, then
the command line. A configuration file is a JSON object using the same names
with underscores instead of dashes.

```bash
build/pclp full-path --instance <file> --config configs/frozen/ratio-closure-tuned.json \
                     --warm-start residual
```

## Algorithm

| Option | Values | Default | What it selects |
|---|---|---|---|
| `--algorithm` | `ratio-closure`, `dinkelbach`, `parametric` | `ratio-closure` | the simplex, or one of the two maximum-flow backends used as cross-checks |
| `--simplex` | `primal`, `dual` | `primal` | the primal is the verifiable reference; the dual starts dual feasible and repairs precedence violations, falling back to the primal if rounding costs it dual feasibility |
| `--dual-leaving` | `first`, `best-head`, `largest-tree`, `deepest`, `incremental` | `first` | which violated constraint the dual leaves on |
| `--warm-start` | `off`, `residual` | `off` | on the canonical path, restart each oracle from the previous final basis instead of the empty one |

## Pricing and pivoting

| Option | Values | Default | What it selects |
|---|---|---|---|
| `--pricing` | `full`, `partial`, `candidate-list` | `full` | every partial scheme ends with a global scan before optimality is declared |
| `--entering-rule` | `bland`, `first-improving`, `best-improving`, `highest-ratio` | `bland` | `bland` requires full pricing. `highest-ratio` ranks the eligible candidates by the ratio of the block of mass the pivot would move rather than by reduced cost; eligibility stays the reduced-cost test, so optimality is unchanged. Measured slower than `best-improving` on every configuration tried and kept as an explicit option, not a recommendation |
| `--pricing-block-size` | integer > 0 | 64 | size of the block scanned, with `partial` |
| `--candidate-limit` | integer > 0 | 32 | length of the candidate list, with `candidate-list` |
| `--ratio-test` | `full`, `restricted`, `early` | `full` | scan every non-forest arc; only those that can block; or stop at the first blocker with a zero step |
| `--degeneracy-trigger` | integer > 0 | 32 | consecutive degenerate pivots before falling back to Bland's rule, released by the first positive step |

## Basis

| Option | Values | Default | What it selects |
|---|---|---|---|
| `--basis-update` | `full`, `local`, `adaptive` | `local` | rebuild the whole forest after a pivot, only the components the pivot touched, or decide by the size of what changed |
| `--rebuild-fraction` | in `(0,1]` | 0.5 | threshold of the adaptive rule |
| `--rebuild-interval` | integer, `0` disables | 256 | periodic full rebuild, to bound drift |
| `--initial-basis` | `sink`, `closure`, `full` | `sink` | start the positive component at a sink of the residual, at the closure of the most promising seed, or at the best undirected component |
| `--initial-seeds` | integer > 0 | 8 | seeds tried with `closure` |

## Model

| Option | Values | Default | What it selects |
|---|---|---|---|
| `--canonicalization` | `sequential`, `dual` | `dual` | `dual` extracts the maximal set by complementarity; `sequential` aggregates equal-ratio increments |
| `--transitive-reduction` | `off`, `on` | `off` | exact reduction under a memory budget; above the budget it is skipped rather than approximated |
| `--node-order` | `input`, `topological`, `seeded` | `input` | numbering of the condensation, for sensitivity studies |
| `--seed` | integer | 0 | only with `--node-order seeded` |

## Limits, checks, output

| Option | Values | Default | What it selects |
|---|---|---|---|
| `--capacity` | number | — | one capacity; `solve` only |
| `--capacities` | JSON array | — | many capacities answered from a single decomposition |
| `--time-limit` | seconds, `0` disables | 0 | monotonic clock; the status becomes `time_limit` |
| `--iteration-limit` | integer | 1000000 | the status becomes `iteration_limit`; neither limit implies optimality |
| `--verify-every` | integer, `0` disables | 0 | check the basis invariants and primal feasibility every N pivots; the final verification always runs |
| `--trace` | `off`, `pivots` | `off` | full pivot log; it allocates, so keep it out of timings |
| `--config`, `--output`, `--result` | paths | — | configuration file, result file, result to verify |

## Tolerances

`--feasibility-abs-tol`, `--feasibility-rel-tol`, `--optimality-abs-tol` and
`--optimality-rel-tol` default to `1e-12`, `1e-10`, `1e-18` and `1e-14`.

They are deliberately kept out of tuning. Every configuration compared uses the
same acceptance thresholds: loosening them to gain time would invalidate the
comparison rather than win it.
