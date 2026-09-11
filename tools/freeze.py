#!/usr/bin/env python3
"""Freezes the winner of a parameter search and writes it into the suites.

Separated from the search so that freezing is an explicit, repeatable step: the
configuration that goes into the campaigns is always the one recorded here, with
the date, the split it was chosen on and the search that produced it.
"""
from __future__ import annotations
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, write_atomic  # noqa: E402

REFERENCE = {"algorithm": "ratio-closure", "basis_update": "full", "pricing": "full",
             "entering_rule": "bland", "canonicalization": "sequential", "ratio_test": "full",
             "initial_basis": "sink", "degeneracy_trigger": 32, "rebuild_interval": 256,
             "transitive_reduction": "off", "node_order": "input"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", type=Path, default=ROOT / "experiments/tuning/forest-v2")
    parser.add_argument("--output", type=Path, default=ROOT / "configs/frozen/ratio-closure-tuned.json")
    options = parser.parse_args()
    summary = json.loads((options.search / "summary.json").read_text())
    best = summary["best"]
    configuration = dict(best["configuration"])
    write_atomic(options.output, json.dumps({
        "configuration": configuration,
        "frozen_on": datetime.date.today().isoformat(),
        "search": str(options.search.resolve().relative_to(ROOT)),
        "space": summary["space"], "split": summary["split"], "budget": summary["budget"],
        "sampled_instances": summary.get("max_instances"),
        "per_run_time_limit_seconds": summary["time_limit"],
        "total_tuning_seconds": round(summary["total_tuning_seconds"], 1),
        "attempt": best["label"], "score_on_training": best["score"],
        "rationale": ("Best of the recorded search under the lexicographic criterion: no incorrect "
                      "result, instances solved and verified, PAR-2, peak memory. Frozen before the "
                      "test manifest was measured; the test set was never used to adjust it."),
    }, indent=2) + "\n")

    def merged(**over):
        c = dict(configuration)
        c.update(over)
        return c

    suites = {
        "main": {"ratio-closure-reference": REFERENCE, "ratio-closure-tuned": dict(configuration),
                 "dinkelbach": {"algorithm": "dinkelbach"}, "parametric": {"algorithm": "parametric"}},
        "smoke": {"ratio-closure-reference": REFERENCE, "ratio-closure-tuned": dict(configuration),
                  "dinkelbach": {"algorithm": "dinkelbach"}, "parametric": {"algorithm": "parametric"}},
        "pilot": {"ratio-closure-reference": REFERENCE, "ratio-closure-tuned": dict(configuration),
                  "dinkelbach": {"algorithm": "dinkelbach"}, "parametric": {"algorithm": "parametric"}},
        "scalability": {"ratio-closure-tuned": dict(configuration), "dinkelbach": {"algorithm": "dinkelbach"},
                        "parametric": {"algorithm": "parametric"}},
        "ablation": {"ratio-closure-tuned": dict(configuration),
                     "no-early-ratio-test": merged(ratio_test="restricted"),
                     "no-restricted-ratio-test": merged(ratio_test="full"),
                     "close-degeneracy-trigger": merged(degeneracy_trigger=32),
                     "bland-entering": merged(entering_rule="bland", pricing="full"),
                     "full-pricing": merged(pricing="full"),
                     "no-local-update": merged(basis_update="full"),
                     "sequential-canonicalization": merged(canonicalization="sequential"),
                     "sink-initial-basis": merged(initial_basis="sink"),
                     "with-transitive-reduction": merged(transitive_reduction="on")},
        "capacities": {"ratio-closure-q1": merged(capacity="instance"), "ratio-closure-q5": merged(capacity={"grid": 5}),
                       "ratio-closure-q20": merged(capacity={"grid": 20}),
                       "ratio-closure-q100": merged(capacity={"grid": 100}),
                       "parametric-q1": {"algorithm": "parametric", "capacity": "instance"},
                       "parametric-q100": {"algorithm": "parametric", "capacity": {"grid": 100}}},
        "full_sweep": {"ratio-closure-tuned": dict(configuration),
                       "ratio-closure-warm": merged(warm_start="residual"),
                       "dinkelbach": {"algorithm": "dinkelbach"},
                       "parametric": {"algorithm": "parametric"}},
        "warm_solve": {"ratio-closure-tuned": dict(configuration),
                       "ratio-closure-warm": merged(warm_start="residual"),
                       "dinkelbach": {"algorithm": "dinkelbach"},
                       "parametric": {"algorithm": "parametric"}},
        "canonical_path": {"ratio-closure-tuned": dict(configuration),
                           "ratio-closure-warm": merged(warm_start="residual"),
                           "ratio-closure-dual": merged(simplex="dual"),
                           "ratio-closure-warm-dual": merged(warm_start="residual", simplex="dual"),
                           "dinkelbach": {"algorithm": "dinkelbach"},
                           "parametric": {"algorithm": "parametric"}},
        "dual": {"ratio-closure-primal": dict(configuration), "ratio-closure-dual": merged(simplex="dual"),
                 "ratio-closure-dual-largest-tree": merged(simplex="dual", dual_leaving="largest-tree"),
                 "parametric": {"algorithm": "parametric"}},
    }
    for name, configurations in suites.items():
        path = ROOT / f"configs/suites/{name}.json"
        suite = json.loads(path.read_text())
        suite["configurations"] = configurations
        write_atomic(path, json.dumps(suite, indent=2) + "\n")
    print(f"frozen {best['label']} from {options.search.name}; {len(suites)} suites updated")


if __name__ == "__main__":
    main()
