# Ratio-Closure Simplex

[![C++ validation](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A C++20 primal and dual simplex specialised to the **maximum-ratio closure**
problem on an arbitrary precedence DAG, and to the **canonical decomposition**
it produces.

## What it computes

Given a directed acyclic precedence graph with a profit `p_i` of arbitrary sign
and a strictly positive weight `w_i` on each vertex, where an arc `(i,j)` means
`x_i <= x_j`, the method solves

```
max  sum_i p_i y_i     s.t.   y_i <= y_j  for every arc (i,j),
                              sum_i w_i y_i = 1,   y >= 0
```

whose optimum is `max_C p(C)/w(C)` over the nonempty closures `C` of the graph.
Driving it to exhaustion produces the whole canonical sequence: the blocks in
strictly decreasing order of ratio, the threshold of every vertex, and the
breakpoints of the parametric closure value.

## Quick start

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure

# the maximum-ratio closure of one instance
build/pclp ratio --instance data/generated/gen_chain_plain_n200_uniform_neg0_r0.json

# the whole canonical decomposition
build/pclp full-path --instance data/generated/gen_sparse_degree3_n2000_uniform_neg30_r0.json \
                     --warm-start residual --output path.json

# a capacity, or many, answered from one decomposition
build/pclp solve --instance <file> --capacity 1000
build/pclp solve --instance <file> --capacities '[100,200,400]'

# re-check a saved certificate without re-optimising
build/pclp verify --instance <file> --result path.json

build/pclp --help
```

A C++20 compiler and CMake are all that is required; `nlohmann/json` is vendored
in [`third_party/`](third_party/) under its own MIT licence. Python 3 is needed
for the test suite and the tools.

## The algorithm

### The basis is a forest

A basic feasible solution of that program has a shape. The tight precedence arcs
form a **forest** on the vertices: one tree carries the positive values, every
other tree is anchored at zero. So the basis is not a matrix but a forest plus a
root, and the algebra collapses accordingly. Writing `b_i = p_i - rho*w_i` for
the current ratio, the reduced cost of a nonbasic vertex variable is the
aggregate of `b` over its tree, and the reduced cost of a nonbasic precedence
slack is the signed aggregate over the subtree hanging below its arc:

```
c(y_T) = p(T) - rho*w(T)          c(s_e) = +/- [ p(D_e) - rho*w(D_e) ]
```

Every one of those aggregates comes out of a single postorder walk, and there
are exactly `n-1` candidates to price. **Complete pricing therefore costs `O(n)`
arithmetic, regardless of how many precedence arcs the graph has**, and no
non-forest arc is ever priced.

A pivot links one arc and cuts another, so two trees **merge** or one tree
**splits**. The ratio test asks which basic slack reaches zero first; only arcs
crossing the boundary of the entering subtree or of the positive component can
block, which is what keeps the exact test cheap. On exit the method carries a
primal-dual certificate, and `pclp verify` re-checks it in the original units and
on the original arcs without re-optimising.

### Single ratio

`pclp ratio` is one call of the oracle: the maximum-ratio closure, an optimal
basic support, and the dual multipliers that certify it.

### Canonical path

`pclp full-path` extracts a block, deletes it, and asks again on the residual
until nothing is left; `pclp positive-path` stops where the ratios turn
nonpositive, which is already enough to answer any capacity.

This is where the shape of the basis pays off a second time. The extracted block
*is* the positive tree, so the other trees survive untouched and stay anchored:
one tree detaches at a time. `--warm-start residual` reuses that forest for the
next oracle instead of rebuilding from the empty basis. It is admissible exactly
when the tree chosen to carry the positive values is closed in the residual --
otherwise an arc leaving it would violate `y_i <= y_j` -- and that condition is
checked in `O(m)` per oracle rather than assumed; when no surviving tree is
closed, the oracle restarts cold. The decomposition it produces is identical
block by block to the one obtained without it, and on the shipped instances it
takes a small fraction of the pivots.

### The capacity is outside the linear program

It never enters the program the simplex solves. It only decides how far along
the canonical sequence one walks and which fraction of the critical block is
taken, so many capacities are answered from a single decomposition. That is why
the method is named after the closure problem.

## Input and output

One JSON object per instance. `node_ids` fixes the order that `profit` and
`weight` follow; arc endpoints are **IDs, not positions**, and `[i,j]` means that
`i` requires `j`, that is `x_i <= x_j`:

```json
{
  "format_version": 1,
  "id": "example4",
  "node_ids": [1, 2, 3, 4],
  "profit": [4, -1, 7, -3],
  "weight": [1, 2, 1, 1],
  "arcs": [[1, 2], [1, 3], [2, 4], [3, 4]],
  "capacity": 4
}
```

Weights must be strictly positive, profits may have any sign, capacities must be
nonnegative. Numbers may also be written as decimal or rational strings such as
`"1/3"`; the core computes in `long double`, so a rational input records where a
number came from without making the arithmetic exact. Digraphs with cycles are
accepted: strongly connected components are condensed internally and the
solution is expanded back onto the original vertices and arcs. Unknown fields,
unknown versions and invalid IDs are rejected rather than ignored.

The result carries the answer and everything needed to re-check it: the resolved
configuration and its SHA-256, the SHA-256 of the canonically re-encoded input,
the source fingerprint of the build, compiler and flags, per-phase timings,
pivot and oracle counters, and peak resident memory. `support` and
`macroitems[].nodes` are zero-based indices into `node_ids`; `solution`, `mu`
and `node_bound` follow the same order; `alpha` follows the original arc list.

The tasks are `inspect`, `ratio`, `positive-path`, `full-path`, `solve` and
`verify`.

## Parameters

Every implementation choice is an explicit option, so that an experiment can
change one thing at a time. Precedence is defaults, then `--config FILE`, then
the command line.

| Option | Values | What it selects |
|---|---|---|
| `--simplex` | `primal`, `dual` | the primal is the verifiable reference; the dual starts dual feasible and repairs precedence violations |
| `--warm-start` | `off`, `residual` | reuse the previous final basis on the residual |
| `--pricing` | `full`, `partial`, `candidate-list` | every partial scheme ends with a global scan before declaring optimality |
| `--entering-rule` | `bland`, `first-improving`, `best-improving` | `bland` requires full pricing |
| `--pricing-block-size`, `--candidate-limit` | integers | size of the partial scan, length of the candidate list |
| `--basis-update` | `full`, `local`, `adaptive` | rebuild the whole forest after a pivot, only the components touched, or decide by size |
| `--rebuild-interval`, `--rebuild-fraction` | integer, `(0,1]` | periodic full rebuild; threshold of the adaptive rule |
| `--ratio-test` | `full`, `restricted`, `early` | exhaustive; only arcs that can block; stop at the first zero-step blocker |
| `--degeneracy-trigger` | integer | consecutive degenerate pivots before falling back to Bland's rule, released by the first positive step |
| `--initial-basis`, `--initial-seeds` | `sink`, `closure`, `full` | where the positive component starts |
| `--canonicalization` | `sequential`, `dual` | `dual` extracts the maximal set by complementarity, `sequential` aggregates equal-ratio increments |
| `--node-order`, `--seed` | `input`, `topological`, `seeded` | numbering of the condensation, for sensitivity |
| `--transitive-reduction` | `off`, `on` | exact reduction under a memory budget; skipped rather than approximated above it |
| `--time-limit`, `--iteration-limit` | seconds, integer | monotonic clock; neither implies optimality |
| `--verify-every` | integer | verify the basis invariants and primal feasibility every N pivots |
| `--capacity`, `--capacities` | number, JSON array | one capacity, or many from a single decomposition |
| `--trace` | `off`, `pivots` | full pivot log; it allocates, so keep it out of timings |

Tolerances (`--feasibility-abs-tol` and its three siblings) are deliberately kept
out of tuning: loosening them to gain time would invalidate any comparison.
`build/pclp --help` lists every option with its accepted values.

## Correctness

Three independent routes must agree:

- an **exhaustive rational oracle** enumerates the closures of small instances
  with `fractions.Fraction` and is compared against the solver on 308 exact
  instances, in every configuration of the rotation, with the basis invariants
  and primal feasibility verified at *every* pivot;
- **two cross-check backends** built on maximum flow, shipped in `src/` and
  selectable with `--algorithm`, answer the same instances through their own
  certificates rather than through the simplex code;
- a **separate verifier** re-checks the primal-dual certificate in the original
  units and on the original arcs, after the condensation and the scaling have
  been undone.

Continuous integration runs all of it on every push.

## Instances

171 instances are included, covering empty graphs, chains, precedence forests,
layered DAGs with and without skips, sparse and dense DAGs, transitively
redundant arcs, diamonds, disconnected components and digraphs with cycles, from
200 to 20000 vertices. Each is registered in `data/generated/index.json` by
name, SHA-256, size and family, and

```bash
sha256sum -c data/MANIFEST.sha256
```

checks them. `tools/generate/instances.py` builds a fresh deterministic set of
the same families at sizes of your choosing.

Importers for two external formats are included -- single-capacity PCKP
instances, and open-pit instances derived from MineLib. They read the original
formats and write the same JSON, validating the model instead of adapting it:

```bash
python3 tools/import/pckp_dat.py --help
python3 tools/import/minelib.py --help
```

## Layout

| Path | Contents |
|---|---|
| [`src/`](src/), [`include/`](include/) | the core: engine, basis forest, graph, backends, certificates, I/O, CLI |
| [`configs/`](configs/) | solver configurations and the tuned configuration |
| [`data/`](data/) | instances, checksums and the frozen splits |
| [`tests/`](tests/) | unit tests and the acceptance suite |
| [`tools/`](tools/) | instance generator, importers, benchmark runner |

## Attribution

The ideas this method builds on are not ours and are credited here:

- **maximum closure via minimum cut** -- Picard (1976); the pseudoflow algorithm,
  Hochbaum (2008);
- **linear fractional programming** -- the equality normalisation that turns
  `max p(S)/w(S)` into the program above is Charnes and Cooper (1962); the
  parametric treatment is Dinkelbach (1967);
- **parametric maximum flow and the nested cut sequence** -- Gallo, Grigoriadis
  and Tarjan (1989); the divide-and-conquer scheme, Eisner and Severance (1976);
- **the residual decomposition** -- Sidney (1975), developed by Lawler (1978);
  the version closest to the ratio reading, Margot, Queyranne and Wang (2003);
- **a forest on the closure graph, carrying branch masses and classifying arcs
  by the sign of the mass they support** -- Lerchs and Grossmann (1965), whose
  normalized tree is the closest antecedent of the basis maintained here, and
  whose parametric version is Hochbaum (2001);
- **the simplex on an incidence matrix with side rows** -- Chen and Saigal
  (1977) for `k` rows, Caliskan (2011) for a single budget row on maximum flow,
  Holzhauser, Krumke and Thielen (2017) for minimum cost flow.

## Companion work

The same canonical sequence, restricted to precedence graphs that are directed
forests, is the subject of a companion paper and repository, whose aggregation
algorithms reach `O(n log n)`:

> **"On parametric Maximum Closure Problems over precedence forests"**
> Valerio Dose, Fabio Furini, Marco Locatelli
> <https://github.com/fabiofurini/parametric-closure-forests>

The vocabulary is shared: a *closure layer* there is a block here, an *optimal
sequence of closure layers* is the canonical decomposition, the *threshold* of a
vertex is the per-vertex bound, and their parameter `lambda` is the ratio `rho`
of the oracle. Those algorithms are specialised to forests; this repository
handles arbitrary DAGs.

## Citing

See [`CITATION.cff`](CITATION.cff). A manuscript is in preparation.

## Licence

MIT, see [`LICENSE`](LICENSE). The vendored `nlohmann/json` keeps its own MIT
licence in [`third_party/nlohmann/LICENSE.MIT`](third_party/nlohmann/LICENSE.MIT).
