# Ratio-Closure Simplex

[![C++ validation](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiofurini/ratio-closure-simplex/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A C++20 primal and dual simplex specialised to the **maximum-ratio closure**
problem on an arbitrary precedence DAG, and to the **canonical decomposition**
it produces.

Each vertex carries a profit `p_i` of arbitrary sign and a strictly positive
weight `w_i`; an arc `(i,j)` means `x_i <= x_j`. The solver answers two
questions:

- **one ratio** — the closure maximising `p(C)/w(C)`, with a certificate;
- **the whole canonical sequence** — every block, in strictly decreasing order of
  ratio, with the threshold of each vertex. A capacity, if there is one, is then
  a query against a sequence already computed.

## Quick start

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure

build/pclp ratio     --instance data/generated/gen_chain_plain_n200_uniform_neg0_r0.json
build/pclp full-path --instance <file> --warm-start residual --output path.json
build/pclp solve     --instance <file> --capacities '[100,200,400]'
build/pclp --help
```

A C++20 compiler and CMake are all that is required; `nlohmann/json` is vendored
under its own MIT licence. Python 3 is used by the test suite and the tools.

## Documentation

| Page | Contents |
|---|---|
| [How it works](docs/ALGORITHM.md) | the basis as a forest, `O(n)` pricing, merge/split pivots, the ratio test, degeneracy, the canonical path and its warm restart |
| [Building and running](docs/BUILDING.md) | requirements, presets, the tasks, generating instances, running a campaign |
| [Input and output](docs/INSTANCE_FORMAT.md) | the instance JSON field by field, the six tasks, every field of the result |
| [Parameters](docs/PARAMETERS.md) | every command-line option, its values and its default |
| [Validation](docs/VALIDATION.md) | the exact oracle, the cross-check backends, the independent verifier |
| [Instances](docs/INSTANCES.md) | the thirteen families included, the generator, the importers |
| [References](docs/REFERENCES.md) | attribution, companion work, how to cite |

## Licence

MIT, see [`LICENSE`](LICENSE).
