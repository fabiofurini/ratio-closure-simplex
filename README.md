# Ratio-Closure Simplex

[![C++ validation](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A C++20 primal and dual simplex specialised to the **maximum-ratio closure**
problem on an arbitrary precedence DAG, and to the **canonical decomposition**
it produces.

## What it computes

Each vertex of a directed acyclic precedence graph carries a profit `p_i` of
arbitrary sign and a strictly positive weight `w_i`; an arc `(i,j)` means
`x_i <= x_j`. The solver answers two questions.

**One ratio.** The closure of maximum ratio, `max_C p(C)/w(C)` over the nonempty
closures `C`, with an optimal support and the dual multipliers certifying it.

**The whole canonical sequence.** Extract that block, delete it, ask again on the
residual, until nothing is left: the blocks in strictly decreasing order of
ratio, the threshold of every vertex, and the breakpoints of the parametric
closure value. A capacity, if there is one, is then a query against a sequence
already in hand, so many capacities cost one decomposition.

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

# one capacity, or many, answered from a single decomposition
build/pclp solve --instance <file> --capacity 1000
build/pclp solve --instance <file> --capacities '[100,200,400]'

# re-check a saved certificate without re-optimising
build/pclp verify --instance <file> --result path.json

build/pclp --help
```

A C++20 compiler and CMake are all that is required; `nlohmann/json` is vendored
in [`third_party/`](third_party/) under its own MIT licence. Python 3 is used by
the test suite and the tools.

## Documentation

| Page | Contents |
|---|---|
| [`docs/ALGORITHM.md`](docs/ALGORITHM.md) | How the method works: the basis as a forest, `O(n)` pricing, merge/split pivots, the ratio test, degeneracy, the canonical path and its warm restart, certificates |
| [`docs/BUILDING.md`](docs/BUILDING.md) | Requirements, build presets, what each test checks, running the solver, generating instances, running a campaign |
| [`docs/INSTANCE_FORMAT.md`](docs/INSTANCE_FORMAT.md) | The instance JSON field by field, the six tasks, and every field of the result |
| [`docs/PARAMETERS.md`](docs/PARAMETERS.md) | Every command-line option, its values and its default |

## Correctness

Three independent routes must agree:

- an **exhaustive rational oracle** enumerates the closures of small instances
  with `fractions.Fraction` and is compared against the solver on 308 exact
  instances, in every configuration of the rotation, with the basis invariants
  and primal feasibility verified at *every* pivot;
- **two cross-check backends** built on maximum flow, selectable with
  `--algorithm`, answer the same instances through their own certificates rather
  than through the simplex code;
- a **separate verifier** re-checks the primal-dual certificate in the original
  units and on the original arcs, after the condensation and the scaling have
  been undone.

Continuous integration runs all of it on every push.

## Instances

171 instances are included, from 200 to 20000 vertices, covering empty graphs,
chains, precedence forests, layered DAGs with and without skips, sparse and
dense DAGs, transitively redundant arcs, diamonds, disconnected components,
bilevel graphs and digraphs with cycles. Each is registered in
`data/generated/index.json` by name, SHA-256, size and family, and

```bash
sha256sum -c data/MANIFEST.sha256
```

checks them. `tools/generate/instances.py` builds a fresh deterministic set of
the same families at sizes of your choosing.

Importers for two external formats are included — single-capacity PCKP
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
| [`configs/`](configs/) | solver configurations, the tuned configuration, benchmark suites |
| [`data/`](data/) | instances, checksums and the frozen splits |
| [`tests/`](tests/) | unit tests and the acceptance suite |
| [`tools/`](tools/) | instance generator, importers, benchmark runner |
| [`docs/`](docs/) | the four pages above |

## Attribution

The maximum-closure problem and the classical machinery around it have a long
history. The work this implementation stands on, and the sources of the two
cross-check backends, are credited here:

- **maximum closure via minimum cut** — Picard (1976); the pseudoflow algorithm,
  Hochbaum (2008);
- **linear fractional programming** — the equality normalisation that turns
  `max p(S)/w(S)` into the program above is Charnes and Cooper (1962); the
  parametric treatment is Dinkelbach (1967);
- **parametric maximum flow and the nested cut sequence** — Gallo, Grigoriadis
  and Tarjan (1989); the divide-and-conquer scheme, Eisner and Severance (1976);
- **the residual decomposition** — Sidney (1975), developed by Lawler (1978);
  the version closest to the ratio reading, Margot, Queyranne and Wang (2003);
- **a forest on the closure graph, carrying branch masses and classifying arcs
  by the sign of the mass they support** — Lerchs and Grossmann (1965), whose
  normalized tree is the closest antecedent of the basis maintained here, and
  whose parametric version is Hochbaum (2001);
- **the simplex on an incidence matrix with side rows** — Chen and Saigal (1977)
  for `k` rows, Caliskan (2011) for a single budget row on maximum flow,
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
