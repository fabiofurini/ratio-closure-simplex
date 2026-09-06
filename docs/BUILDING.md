# Building and running

## Requirements

A C++20 compiler and CMake 3.20 or newer. `nlohmann/json` is vendored in
`third_party/`, so there is nothing else to fetch. Python 3 is used by the test
suite, the instance generator, the importers and the benchmark runner.

## Build

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

The binary is `build/pclp`. Presets are also provided:

```bash
cmake --preset release      # -O3, assertions off
cmake --preset debug        # assertions on, invariants checked
cmake --preset sanitize     # AddressSanitizer and UndefinedBehaviorSanitizer
```

## Tests

```bash
ctest --test-dir build --output-on-failure
```

Five tests run. Four are fast unit checks: the worked example, an exhaustive
differential comparison on small random DAGs, the intrusive adjacency structure
of the basis forest, and the engine invariants — no allocation inside the pivot
loop, local against full basis updates, deep chains and strongly connected
components of thirty thousand vertices.

The fifth, `solver_acceptance`, is the one that matters. It enumerates the
closures of 308 small instances exactly, with `fractions.Fraction`, and compares
the solver against that oracle in every configuration of its rotation, with the
basis invariants and primal feasibility verified at *every* pivot. It also
reconstructs individual pivots against rational basis systems and cross-checks
the two maximum-flow backends.

Expect it to take around ten seconds in Release.

## Running

```bash
build/pclp ratio      --instance <file>
build/pclp full-path  --instance <file> --warm-start residual
build/pclp solve      --instance <file> --capacity 1000
build/pclp verify     --instance <file> --result result.json
build/pclp --help
```

Every task writes a JSON result to standard output, or to `--output FILE`. The
exit status is 0 when the answer is optimal or a certificate is valid, 1 when
the run ends in any other terminal state, and 2 on invalid input.

Writing to `--output` is atomic and never overwrites: the result goes to a
temporary file in the same directory and is published by an exclusive hard link,
so an interrupted run leaves no partial file behind.

## Generating instances

```bash
python3 tools/generate/instances.py --help
```

Thirteen structural families, deterministic from a declared seed: empty graphs,
chains, precedence forests, layered DAGs with and without skips, sparse and
dense DAGs, transitively redundant arcs, diamonds, disconnected components,
bilevel graphs and digraphs with cycles.

## Running a campaign

```bash
python3 tools/benchmark/run.py configs/suites/ci.json --root /tmp/runs
```

A campaign is described by a suite file: the task, the instances, the
configurations to compare, the replicas and the limits. Each run is identified
by the instance, the task, the capacity, the *content* of the configuration and
the hash of the sources, so a campaign resumes where it stopped and a changed
solver produces new identifiers rather than overwriting old ones. Every optimal
run is re-verified before being recorded.
