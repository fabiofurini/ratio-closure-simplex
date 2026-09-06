# Ratio-Closure Simplex — Source Code, Instances & Results

[![C++ validation](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

C++20 implementation, benchmark infrastructure, reproducible instances and
aggregated results for the **ratio-closure simplex**: the ordinary primal and
dual simplex specialised to the normalised maximum-ratio closure linear
program, used to produce the *entire* canonical sequence of closure layers and
not only the maximum-ratio one.

Given a directed acyclic precedence graph with a profit `p_i` of arbitrary sign
and a strictly positive weight `w_i` on each vertex, an arc `(i,j)` meaning
`x_i <= x_j`, the oracle solves

```
max  sum_i p_i y_i     s.t.   y_i <= y_j  for every arc (i,j),
                              sum_i w_i y_i = 1,   y >= 0
```

whose optimum is `max_C p(C)/w(C)` over the nonempty closures `C` of the graph.
Driving the oracle to exhaustion — extract a block, delete it, ask again on the
residual — yields the canonical decomposition: blocks of strictly decreasing
ratio, the threshold of every vertex, and the breakpoints of the parametric
closure value. A capacity, when there is one, never enters the linear program;
it only decides how far along the sequence one walks. That is why the method is
named after the closure problem and not after the knapsack.

## What this is not

The simplex is exact; that is not a contribution and is not offered as one.
What is specific here is what the simplex *becomes* on this program:
closure-specific closed forms for every nonbasic price and pivot direction,
complete pricing in `O(n)` arithmetic independently of the number of precedence
arcs, and a full ratio test over all potentially blocking basic slacks.

The forest structure of the basic feasible solutions, the merge/split reading of
pivots, the maximum-ratio closure formulation, the canonical decomposition and
the paradigm of a simplex on an incidence matrix with one side row are **not**
claimed as new. See *Attribution* below, and the novelty audit in
[`literature/`](literature/) — a document written to *reduce* the claim, with
the retracted statements listed one by one.

## Results in one paragraph

On the frozen test bed the two combinatorial reference backends are hard to
beat. On single-capacity solves the parametric decomposition and Dinkelbach
dominate. On the full canonical decomposition, restarting each residual oracle
from the previous final basis (`--warm-start residual`) cuts the pivot count by
up to a factor of 82 and makes the method 3.1 times faster than the cold
restart, enough to overtake Dinkelbach and to win the families whose sequence
has the most layers; the parametric backend still wins the majority and is 3.4
times faster in total. The numbers, the diagnosis — 98% to 100% of the pivots
are degenerate — and the limits of the comparison are in
[`report/ratio_closure_simplex_report.pdf`](report/ratio_closure_simplex_report.pdf),
generated from the stored campaign manifests.

## Build and run

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

Only a C++20 compiler and CMake are required; `nlohmann/json` is vendored in
[`third_party/`](third_party/) under its own MIT licence. Python 3 is needed for
the test suite, the campaign runner and the document builds.

```bash
# the maximum-ratio closure of an instance
build/pclp ratio --instance data/generated/gen_chain_plain_n200_uniform_neg0_r0.json

# the whole canonical decomposition, warm restart on the residual
build/pclp full-path --instance <file> --warm-start residual

# a capacity query, and many capacities from one decomposition
build/pclp solve --instance <file> --capacity 1000
build/pclp solve --instance <file> --capacities '[100,200,400]'

# re-check a saved certificate without re-optimising
build/pclp verify --instance <file> --result result.json

build/pclp --help
```

Every implementation choice is an explicit parameter — pricing rule, basis
update, initial basis, ratio test, canonicalisation, anti-cycling threshold,
primal or dual — so that an ablation measures each one in isolation. They are
documented in [`docs/parameters.md`](docs/parameters.md).

## Correctness

Three independent routes must agree, and the campaign discards any run whose
certificate does not re-verify:

- an **exhaustive rational oracle** enumerates the closures of small instances
  with `fractions.Fraction` and is compared against the solver on 308 exact
  instances, in every configuration of the rotation, with the basis invariants
  and primal feasibility verified at *every* pivot;
- two **independent backends** — Dinkelbach with maximum-closure minimum cuts,
  and a parametric divide-and-conquer decomposition — solve the same instances
  through their own certificates, not through the simplex code;
- a **separate verifier** re-checks the primal–dual certificate in the original
  units and on the original arcs, after the condensation and scaling have been
  undone.

## Layout

| Path | Contents |
|---|---|
| [`src/`](src/), [`include/`](include/) | the C++20 core: engine, basis forest, graph, backends, certificates, I/O, CLI |
| [`configs/`](configs/) | solver configurations, the frozen tuned configuration, the tuning space, the measurement suites |
| [`data/generated/`](data/generated/) | 171 synthetic instances, 13 structural families, 200 to 20000 vertices |
| [`data/splits/`](data/splits/) | the frozen training, validation and test manifests |
| [`experiments/`](experiments/) | measurement protocol, campaign manifests, aggregated CSVs |
| [`tests/`](tests/) | unit tests and the acceptance suite |
| [`tools/`](tools/) | generator, importers, campaign runner, tuning search, analysis, document builds |
| [`docs/`](docs/) | mathematical contract, notation, invariants, parameters, decisions, claims |
| [`report/`](report/) | the experimental report and its generated tables and plots |
| [`tutorial/`](tutorial/) | a didactic derivation of the method on general DAGs |
| [`literature/`](literature/) | the novelty audit and its bibliography |

## Reproducing

The commands are in [`docs/reproducibility.md`](docs/reproducibility.md) and the
measurement protocol in [`experiments/protocol.md`](experiments/protocol.md).

```bash
python3 tools/benchmark/run.py configs/suites/ci.json --root /tmp/runs
python3 tools/report/analyze.py
python3 tools/build_report.py
```

Campaign records are keyed by instance, task, capacity, configuration *content*
and source hash, so a campaign resumes where it stopped and a changed solver
produces new identifiers rather than silently overwriting old ones.

The synthetic instances are shipped rather than regenerated on purpose. An
earlier version of the generator derived each seed from Python's randomised
`hash()`, so two runs produced two different instance sets; the generator is now
deterministic, but the instances in `data/generated/` predate the fix and the
corrected generator builds a *different* set. The stored campaigns reference
instances by name and SHA-256, so they are reproducible by keeping the files,
not by regenerating them. `data/MANIFEST.sha256` checks them.

## What this repository deliberately does not contain

| Excluded | Why |
|---|---|
| the raw `result.json` of every run (6 GB, twelve files above GitHub's 100 MB limit) | the campaign **manifests** and the aggregated CSVs are here, and they carry the measured values, the statuses and the verification flags |
| the PDFs of the surveyed articles | copyright. [`literature/TO_OBTAIN.md`](literature/TO_OBTAIN.md) lists every entry and where to get it |
| the historical PCKP and MineLib-derived instances | not ours to redistribute. The importers in [`tools/import/`](tools/import/) rebuild them from the original sources |
| the 2023 prototype | historical code with interactive debug pauses; what was carried over from it is recorded in the project decisions |
| the parameter-search runs | the chosen configuration is in [`configs/frozen/`](configs/frozen/) with its date, split and rationale |

Because the historical instances are not shipped, the frozen splits and the
measurement suites reference names that are not in this repository. That is
deliberate: the splits are the record of what was measured, and rewriting them
would make the record say something that did not happen.

## Attribution

The reference algorithms are not ours and are implemented here to be measured
against:

- **maximum closure via minimum cut** — Picard (1976); the pseudoflow algorithm,
  Hochbaum (2008);
- **fractional programming by Newton iteration** — Dinkelbach (1967); the
  equality normalisation of a linear fractional program is Charnes and Cooper
  (1962);
- **parametric maximum flow and the nested cut sequence** — Gallo, Grigoriadis
  and Tarjan (1989); the divide-and-conquer scheme, Eisner and Severance (1976);
- **the residual decomposition** — Sidney (1975), developed by Lawler (1978);
  the version closest to the ratio reading, Margot, Queyranne and Wang (2003);
- **the forest on the closure graph, with branch masses and a sign test** —
  Lerchs and Grossmann (1965), whose normalized tree is the closest antecedent
  of the basis maintained here, and whose parametric version is Hochbaum (2001);
- **the simplex on an incidence matrix with side rows** — Chen and Saigal (1977)
  for `k` rows, Çalışkan (2011) for a single budget row on maximum flow,
  Holzhauser, Krumke and Thielen (2017) for minimum cost flow.

The full bibliography, with what each source removes from the claim, is in
[`literature/references.bib`](literature/references.bib).

## Companion work

The same canonical sequence, restricted to precedence graphs that are directed
forests, is the subject of a companion paper and repository, whose aggregation
algorithms reach `O(n log n)`:

> **"On parametric Maximum Closure Problems over precedence forests"**
> Valerio Dose, Fabio Furini, Marco Locatelli
> <https://github.com/fabiofurini/parametric-closure-forests>

The vocabulary is shared: a *closure layer* there is a canonical block here, an
*optimal sequence of closure layers* is the canonical decomposition, the
*threshold* of a vertex is the per-vertex bound, and their parameter `λ` is the
ratio `ρ` of the oracle. Their algorithms do not apply to general DAGs, which is
what this repository handles.

## Citing

See [`CITATION.cff`](CITATION.cff). The manuscript is in preparation; the
novelty audit in [`literature/`](literature/) states what it will and will not
claim.

## Licence

MIT, see [`LICENSE`](LICENSE). The vendored `nlohmann/json` keeps its own MIT
licence in [`third_party/nlohmann/LICENSE.MIT`](third_party/nlohmann/LICENSE.MIT).
