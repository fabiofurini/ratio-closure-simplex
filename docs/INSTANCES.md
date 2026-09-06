# Instances

## What is included

171 instances, from 200 to 20000 vertices, in thirteen structural families:

| Family | Shape |
|---|---|
| `empty` | no arcs; the closure structure imposes nothing |
| `chain` | maximum depth, one long precedence path |
| `forest` | disjoint precedence trees |
| `layered` | levelled DAGs, with and without skips between levels |
| `sparse`, `dense` | random DAGs at low and high arc density |
| `transitive` | with transitively redundant arcs added on purpose |
| `diamonds` | repeated diamond modules |
| `disconnected` | several components, so the residual is disconnected |
| `bilevel` | two-level bipartite-like precedence |
| `cyclic` | digraphs with cycles, condensed internally |

Profits are drawn uniformly or heterogeneously, with a controlled fraction of
negative values. Each instance is registered in `data/generated/index.json` by
name, path, SHA-256, vertices, arcs, capacity, family and origin.

```bash
sha256sum -c data/MANIFEST.sha256
```

`data/splits/` holds frozen training, validation and test manifests, so that a
configuration chosen on one split can be reported on another.

## Generating your own

```bash
python3 tools/generate/instances.py --help
```

The generator is deterministic: every instance derives its seed from a SHA-256
of its own descriptive fields, so two runs on the same arguments produce
byte-identical files.

## Importing external formats

Two importers are included. They read the original formats and write the same
JSON, validating the model rather than adapting it — an instance that does not
fit the supported family is rejected with the reason.

```bash
python3 tools/import/pckp_dat.py --help   # single-capacity PCKP instances
python3 tools/import/minelib.py --help    # open-pit instances derived from MineLib
```

Imported files land in `data/processed/` and are registered in its `index.json`
the same way, which is how the benchmark suites refer to them.
