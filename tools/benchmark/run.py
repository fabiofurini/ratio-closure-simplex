#!/usr/bin/env python3
"""Runs a measurement campaign described by a suite file.

Every run has an identifier derived from instance, task, capacity, resolved
configuration, build and replica index, so a finished run is never recomputed
and never overwritten: a new build or configuration simply produces a new
identifier.  Each result is re-checked by an independent ``pclp verify`` call
before it is counted as usable.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, canonical, digest, load_index, write_atomic  # noqa: E402

TERMINAL = {"optimal", "time_limit", "iteration_limit", "memory_limit",
            "numerical_failure", "invalid_input", "unsupported_model", "internal_error"}


def build_fingerprint(program: Path) -> dict:
    probe = subprocess.run([str(program), "inspect", "--instance", str(ROOT / "tests/fixtures/paper_example8.json")],
                           capture_output=True, text=True, check=True)
    return json.loads(probe.stdout)["build"]


def select(suite: dict) -> list[dict]:
    chosen, seen = [], set()
    for path in suite["instances"]["index"]:
        for record in load_index(ROOT / path)["instances"]:
            if record["name"] in seen:
                continue
            selection = suite["instances"]
            if selection.get("names") and record["name"] not in selection["names"]:
                continue
            if selection.get("families") and record["family"] not in selection["families"]:
                continue
            if selection.get("origins") and record["origin"] not in selection["origins"]:
                continue
            if selection.get("max_nodes") and record["nodes"] > selection["max_nodes"]:
                continue
            if selection.get("min_nodes") and record["nodes"] < selection["min_nodes"]:
                continue
            seen.add(record["name"])
            chosen.append(record)
    return sorted(chosen, key=lambda r: (r["nodes"], r["name"]))


def plan(suite: dict, fingerprint: dict) -> list[dict]:
    runs = []
    for record in select(suite):
        for label, configuration in suite["configurations"].items():
            for replica in range(suite.get("replicas", 1)):
                key = canonical({"instance": record["sha256"], "task": suite["task"],
                                 "capacity": suite.get("capacity", "instance"),
                                 "configuration": configuration, "build": fingerprint["source_hash"],
                                 "type": fingerprint["type"], "replica": replica})
                runs.append({"run_id": digest(key)[:16], "instance": record["name"],
                             "instance_path": record["path"], "instance_sha256": record["sha256"],
                             "nodes": record["nodes"], "arcs": record["arcs"], "family": record["family"],
                             "origin": record["origin"], "configuration": label, "replica": replica})
    return runs


def capacities_of(record_path: Path, mode) -> list[str]:
    """Capacity flags of one run: the instance's own value, its saved list, a
    fixed value, or a grid of `k` queries spanning the total weight."""
    if mode == "instance":
        return []
    instance = json.loads(record_path.read_text())
    if mode == "list":
        return ["--capacities", json.dumps(instance["capacities"])]
    if isinstance(mode, dict) and "grid" in mode:
        total = sum(float(w) for w in instance["weight"])
        count = int(mode["grid"])
        grid = [round(total * (k + 1) / (count + 1), 6) for k in range(count)]
        return ["--capacities", json.dumps(grid)]
    return ["--capacity", str(mode)]


def arguments_for(suite: dict, record_path: Path, configuration: dict, output: Path,
                  config_file: Path, mode) -> list[str]:
    flags = ["--instance", str(record_path), "--config", str(config_file), "--output", str(output)]
    if suite["task"] == "solve":
        flags += capacities_of(record_path, mode)
    return flags


def execute(program: Path, suite: dict, run: dict, directory: Path, cpu: int | None,
            build: str = "") -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    configuration = dict(suite["configurations"][run["configuration"]])
    mode = configuration.pop("capacity", suite.get("capacity", "instance"))
    configuration.setdefault("time_limit", suite.get("time_limit", 0))
    config_file = directory / "resolved_config.json"
    write_atomic(config_file, json.dumps(configuration, indent=1, sort_keys=True) + "\n")
    output = directory / "result.json"
    if output.exists():
        output.unlink()
    command = [str(program), suite["task"]] + arguments_for(
        suite, ROOT / run["instance_path"], configuration, output, config_file, mode)
    if cpu is not None and shutil.which("taskset"):
        command = ["taskset", "-c", str(cpu)] + command
    started = time.monotonic()
    completed = subprocess.run(command, capture_output=True, text=True,
                               timeout=suite.get("wall_limit", 3600))
    elapsed = time.monotonic() - started
    record = dict(run)
    record["build_source_hash"] = build
    record["capacity_mode"] = json.dumps(mode)
    record["runner_seconds"] = elapsed
    record["command"] = command[len(command) - len(command):]
    if not output.exists():
        record["status"] = "runner_failure"
        record["message"] = (completed.stderr or completed.stdout)[-400:]
        return record
    result = json.loads(output.read_text())
    record["status"] = result.get("status", "internal_error")
    record["objective"] = result.get("objective")
    record["end_to_end_seconds"] = result.get("end_to_end_seconds")
    record["peak_rss_bytes"] = result.get("peak_rss_bytes")
    statistics = result.get("stats") or (result.get("path") or {}).get("stats") or {}
    for key in ("pivots", "degenerate_pivots", "oracle_calls", "flow_solves", "flow_augmentations",
                "full_rebuilds", "local_rebuilds", "rebuilt_nodes", "candidates_examined",
                "removed_arcs", "preprocessing_seconds", "pricing_seconds", "direction_seconds",
                "ratio_test_seconds", "update_seconds", "certification_seconds", "total_seconds"):
        if key in statistics:
            record[key] = statistics[key]
    path = result.get("path") or (result if suite["task"].endswith("path") else {})
    if path.get("macroitems") is not None:
        record["macroitems"] = len(path["macroitems"])
        record["complete_sequence"] = bool(path.get("complete"))
    if isinstance(result.get("solutions"), list):
        record["queries"] = len(result["solutions"])
        record["objective"] = result["solutions"][-1].get("objective") if result["solutions"] else None
    if record["status"] == "optimal":
        check = subprocess.run([str(program), "verify", "--instance", str(ROOT / run["instance_path"]),
                                "--result", str(output)], capture_output=True, text=True)
        record["verified"] = check.returncode == 0
        if not record["verified"]:
            record["message"] = (check.stderr or check.stdout)[-400:]
    else:
        record["verified"] = False
        record["message"] = result.get("message", "")
    return record


def write_readme(campaign: Path, suite: dict, suite_path: Path, manifest: dict) -> None:
    """Every campaign directory documents its own purpose, command and state."""
    report = {"optimal": 0}
    for record in manifest["records"].values():
        report[record["status"]] = report.get(record["status"], 0) + 1
    verified = sum(1 for r in manifest["records"].values() if r.get("verified"))
    lines = [f"# Campagna {suite['campaign']}", "",
             suite.get("note", ""), "",
             "## Comando", "", "```bash",
             f"python3 tools/benchmark/run.py {suite_path} --cpu <core>", "```", "",
             "## Stato", "",
             f"- run previsti: {manifest['planned']}",
             f"- run memorizzati: {len(manifest['records'])}",
             f"- verificati da una chiamata `pclp verify` separata: {verified}",
             "- stati: " + ", ".join(f"{k} {v}" for k, v in sorted(report.items()) if v), "",
             "## Contenuto", "",
             "`manifest.json` elenca ogni run con la configurazione risolta, i contatori e l'esito",
             "della verifica. Ogni sottodirectory e un run: `result.json` e `resolved_config.json`.",
             "L'istanza non viene copiata qui: il manifesto la referenzia per nome e hash.", "",
             "## Configurazioni confrontate", ""]
    lines += [f"- `{label}`: `{json.dumps(configuration, sort_keys=True)}`"
              for label, configuration in suite["configurations"].items()]
    lines += ["", "Derivati e tabelle si rigenerano con `python3 tools/report/analyze.py`."]
    write_atomic(campaign / "README.md", "\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", type=Path)
    parser.add_argument("--program", type=Path, default=ROOT / "build/release/pclp")
    parser.add_argument("--root", type=Path, default=ROOT / "experiments/runs")
    parser.add_argument("--cpu", type=int, default=None, help="pin the solver to this core")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many new runs")
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args()
    suite = json.loads(options.suite.read_text())
    suite.setdefault("time_limit", 0)
    fingerprint = build_fingerprint(options.program)
    fingerprint = {"source_hash": fingerprint["source_sha256"], "type": fingerprint["type"],
                   "compiler": fingerprint["compiler"], "flags": fingerprint["flags"],
                   "machine": fingerprint["machine"]}
    campaign = options.root / suite["campaign"]
    runs = plan(suite, fingerprint)
    manifest_path = campaign / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"records": {}}
    done = manifest["records"]
    pending = [run for run in runs if run["run_id"] not in done]
    print(f"{suite['campaign']}: {len(runs)} planned, {len(runs) - len(pending)} already stored, "
          f"{len(pending)} to run")
    if options.dry_run:
        return
    started = time.monotonic()
    # Replicas measure the dispersion of a time; a run that does not finish has
    # no time to disperse, and repeating it is deterministic.  The first replica
    # of a pair (instance, configuration) is measured; if it did not reach an
    # optimal, verified result the remaining replicas inherit its outcome
    # without being executed, so the manifest stays complete and the budget is
    # spent where it measures something.
    outcome: dict[tuple[str, str], dict] = {}
    for index, run in enumerate(pending):
        if options.limit and index >= options.limit:
            break
        key = (run["instance"], run["configuration"])
        first = outcome.get(key)
        if run["replica"] and first is not None and not first.get("verified"):
            record = dict(run)
            record.update({k: first[k] for k in ("status", "message", "build_source_hash",
                                                 "capacity_mode") if k in first})
            record["verified"] = False
            record["repeat_of_replica_0"] = True
            record["runner_seconds"] = first.get("runner_seconds")
        else:
            record = execute(options.program, suite, run, campaign / run["run_id"], options.cpu,
                             fingerprint["source_hash"])
            if not run["replica"]:
                outcome[key] = record
        done[run["run_id"]] = record
        manifest.update({"campaign": suite["campaign"], "suite": str(options.suite.resolve().relative_to(ROOT)),
                         "note": suite.get("note", ""), "task": suite["task"],
                         "capacity": suite.get("capacity", "instance"),
                         "configurations": suite["configurations"], "build": fingerprint,
                         "planned": len(runs), "records": done})
        write_atomic(manifest_path, json.dumps(manifest, indent=1) + "\n")
        write_readme(campaign, suite, options.suite.resolve().relative_to(ROOT), manifest)
        flag = "ok" if record.get("verified") else record["status"]
        if record.get("repeat_of_replica_0"):
            flag += " (ripetizione non eseguita)"
        print(f"  [{index + 1}/{len(pending)}] {run['instance']:34s} {run['configuration']:22s} "
              f"{record['runner_seconds'] or 0:8.3f}s {flag}")
    print(f"campaign wall time {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()
