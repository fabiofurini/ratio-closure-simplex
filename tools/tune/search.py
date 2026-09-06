#!/usr/bin/env python3
"""Reproducible random search over the implemented solver parameters.

Only parameters the solver actually exposes take part, conditional parameters
are sampled only when their guard holds, and every attempt is appended to a
history file so that an interrupted search resumes without repeating work.
The evaluation is lexicographic: first correctness, then instances solved
within the limits, then PAR-2 time, then peak memory.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, canonical, digest, write_atomic  # noqa: E402

spec = importlib.util.spec_from_file_location("runner", ROOT / "tools/benchmark/run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def sample(space: dict, rng: random.Random) -> dict:
    for _ in range(1000):
        candidate = dict(space.get("base", {}))
        for name, definition in space["parameters"].items():
            requires = definition.get("requires", {})
            if any(candidate.get(key) not in values for key, values in requires.items()):
                continue
            candidate[name] = rng.choice(definition["values"])
        if all(any(candidate.get(key) in values for key, values in rule["then"].items())
               for rule in space.get("constraints", [])
               if all(candidate.get(key) in values for key, values in rule["if"].items())):
            return candidate
    raise RuntimeError("the constraints reject every sampled configuration")


def evaluate(program: Path, space: dict, configuration: dict, split: Path, campaign: Path,
             time_limit: float, label: str, sample: int = 0, cpu: int | None = None) -> dict:
    suite = {"campaign": campaign.name, "task": space.get("task", "solve"),
             "capacity": space.get("capacity", "instance"), "replicas": 1,
             "time_limit": time_limit, "wall_limit": time_limit * 4 + 60,
             "instances": {"index": [str(split.resolve().relative_to(ROOT))]},
             "configurations": {label: configuration}}
    fingerprint = runner.build_fingerprint(program)
    plan = runner.plan(suite, {"source_hash": fingerprint["source_sha256"], "type": fingerprint["type"]})
    if sample and len(plan) > sample:
        step = len(plan) / sample
        plan = [plan[int(k * step)] for k in range(sample)]
    solved, failures, penalty, memory, seconds = 0, 0, 0.0, 0, 0.0
    for run in plan:
        record = runner.execute(program, suite, run, campaign / label / run["run_id"], cpu,
                                fingerprint["source_sha256"])
        if record["status"] == "optimal" and record.get("verified"):
            solved += 1
            penalty += record["runner_seconds"]
            seconds += record["runner_seconds"]
        elif record["status"] in ("time_limit", "iteration_limit", "memory_limit"):
            penalty += 2 * time_limit
        else:
            failures += 1
            penalty += 2 * time_limit
        memory = max(memory, record.get("peak_rss_bytes") or 0)
    return {"solved": solved, "failures": failures, "par2": penalty, "seconds": seconds,
            "peak_rss_bytes": memory, "instances": len(plan)}


def key(score: dict):
    return (score["failures"], -score["solved"], score["par2"], score["peak_rss_bytes"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("space", type=Path)
    parser.add_argument("--split", type=Path, default=ROOT / "data/splits/train.json")
    parser.add_argument("--program", type=Path, default=ROOT / "build/release/pclp")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=24)
    parser.add_argument("--time-limit", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--cpu", type=int, default=None, help="pin the solver to this core")
    parser.add_argument("--max-instances", type=int, default=0,
                        help="deterministic subsample of the split used for the search")
    options = parser.parse_args()
    space = json.loads(options.space.read_text())
    options.output.mkdir(parents=True, exist_ok=True)
    history_path = options.output / "history.jsonl"
    history = [json.loads(line) for line in history_path.read_text().splitlines()] if history_path.exists() else []
    seen = {entry["configuration_sha256"] for entry in history}
    rng = random.Random(options.seed)
    started = time.monotonic()
    candidates = [dict(entry) for entry in space.get("seeded_candidates", [])]
    while len(history) < options.budget:
        configuration = candidates.pop(0) if candidates else sample(space, rng)
        fingerprint = digest(canonical(configuration))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        label = f"cfg{len(history):03d}_{fingerprint[:8]}"
        begin = time.monotonic()
        try:
            score = evaluate(options.program, space, configuration, options.split,
                             options.output, options.time_limit, label, options.max_instances,
                             options.cpu)
            reason = ""
        except Exception as error:  # a rejected configuration is recorded, not hidden
            score, reason = {"solved": 0, "failures": 10 ** 6, "par2": float("inf"),
                             "seconds": 0.0, "peak_rss_bytes": 0, "instances": 0}, str(error)
        entry = {"label": label, "configuration": configuration,
                 "configuration_sha256": fingerprint, "score": score, "rejected": reason,
                 "tuning_seconds": time.monotonic() - begin}
        history.append(entry)
        with open(history_path, "a") as handle:
            handle.write(json.dumps(entry) + "\n")
        print(f"{label}: solved {score['solved']}/{score['instances']} failures {score['failures']} "
              f"par2 {score['par2']:.1f}s in {entry['tuning_seconds']:.1f}s")
    best = min(history, key=lambda entry: key(entry["score"]))
    summary = {"space": str(options.space.resolve().relative_to(ROOT)), "split": str(options.split.resolve().relative_to(ROOT)),
               "max_instances": options.max_instances, "budget": options.budget, "seed": options.seed, "time_limit": options.time_limit,
               "attempts": len(history), "total_tuning_seconds": time.monotonic() - started,
               "best": best, "ranking": sorted(history, key=lambda e: key(e["score"]))[:8]}
    write_atomic(options.output / "summary.json", json.dumps(summary, indent=1) + "\n")
    print(f"best {best['label']} -> {json.dumps(best['configuration'])}")


if __name__ == "__main__":
    main()
