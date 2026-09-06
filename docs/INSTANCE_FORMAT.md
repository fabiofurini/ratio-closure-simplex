# Input and output

## Instance

One JSON object per instance. `node_ids` fixes the order that `profit` and
`weight` follow. Arc endpoints are **IDs, not positions**, and `[i,j]` means that
`i` requires `j`, that is `x_i <= x_j`.

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

| Field | Required | Meaning |
|---|---|---|
| `format_version` | no | must be `1` when present |
| `id` | no | name of the instance, defaults to `unnamed` |
| `node_ids` | yes | unique integers or strings; fixes the order of `profit` and `weight` |
| `profit` | yes | one per vertex, any sign |
| `weight` | yes | one per vertex, strictly positive |
| `arcs` | yes | pairs of IDs; `[i,j]` means `x_i <= x_j` |
| `capacity` | no | a single nonnegative capacity |
| `capacities` | no | an array of nonnegative capacities |
| `numeric_type` | no | `integer`, `rational` or `floating`; records where the numbers came from |
| `source`, `metadata` | no | free-form provenance |

Numbers may be JSON numbers, or decimal or rational strings such as `"1/3"`. The
core computes in `long double`: a rational input documents the origin of a value
but does not make the arithmetic exact.

Digraphs with cycles are accepted. Strongly connected components are condensed
internally, duplicate arcs and self-loops are dropped from the internal model,
and the solution and the multipliers are expanded back onto the original
vertices and arcs. Unknown fields, unknown versions, invalid IDs, nonpositive
weights and negative capacities are rejected rather than ignored.

## Tasks

| Task | Answers |
|---|---|
| `inspect` | sizes, the condensation and the component map, without optimising |
| `ratio` | one maximum-ratio closure, its support and its certificate |
| `positive-path` | the canonical sequence down to the last positive ratio |
| `full-path` | the whole canonical sequence, including zero and negative ratios |
| `solve` | the value at one capacity, or at each of many |
| `verify` | re-checks a saved result without re-optimising |

`positive-path` is already enough to answer any capacity.

## Result

```bash
build/pclp full-path --instance <file> --output path.json
build/pclp verify    --instance <file> --result path.json
```

The result carries the answer and everything needed to re-check it: the resolved
configuration and its SHA-256, the SHA-256 of the canonically re-encoded input,
the source fingerprint of the build, the compiler and its flags, per-phase
timings, pivot and oracle counters, and peak resident memory. The input
fingerprint is the hash of the re-encoded JSON, not of the original bytes.

| Field | Contents |
|---|---|
| `status` | `optimal`, `time_limit`, `iteration_limit`, `invalid_input`, … |
| `ratio` | the maximum ratio, for `ratio` |
| `support` | zero-based indices into `node_ids` |
| `macroitems[]` | one entry per block: `ratio`, `profit`, `weight`, `nodes` |
| `node_bound[]` | the threshold of every vertex, in `node_ids` order |
| `prefix_weight[]`, `prefix_profit[]` | cumulative sums along the sequence |
| `alpha[]` | arc multipliers, following the **original** arc list, duplicates included |
| `solution[]`, `mu[]`, `lambda` | primal solution and duals, for `solve` |
| `stats` | pivots, degenerate pivots, oracle calls, rebuilds, per-phase seconds |

`support`, `macroitems[].nodes`, `solution`, `mu` and `node_bound` are all in
`node_ids` order. `alpha` follows the original arcs. A trace, when enabled, uses
the indices of the condensed and scaled model, which is exported alongside it.

Writing to `--output` is atomic and never overwrites an existing file.
