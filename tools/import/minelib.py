#!/usr/bin/env python3
"""Imports MineLib open-pit instances as single-capacity precedence knapsacks.

MineLib CPIT is a multi-period, multi-resource model.  The instance written here
is an explicit derivation, not the original model: period indices and discounting
are dropped, the objective keeps the undiscounted block values, the knapsack row
is resource 0 of the CPIT file and the capacity is that resource's limit summed
over the periods it was granted.  The derivation is recorded in every instance.
Blocks whose resource-0 coefficient is not strictly positive fall outside the
supported family, and such an instance is refused rather than repaired.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, file_digest, instance, load_index, save_index, store  # noqa: E402


def sections(path: Path):
    """Splits a MineLib file into its header fields and its labelled blocks."""
    header, blocks, current = {}, {}, None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith(":"):
            current = line[:-1]
            blocks[current] = []
        elif ":" in line and current is None:
            key, value = line.split(":", 1)
            header[key.strip()] = value.strip()
        elif line == "EOF":
            current = None
        elif current is not None:
            blocks[current].append(line.split())
        else:
            raise ValueError(f"{path.name}: unexpected line '{line}'")
    return header, blocks


def read_precedences(path: Path, n: int):
    arcs = []
    seen = set()
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        node, count = int(fields[0]), int(fields[1])
        if len(fields) != 2 + count:
            raise ValueError(f"{path.name}: node {node} declares {count} predecessors")
        if node in seen:
            raise ValueError(f"{path.name}: node {node} appears twice")
        seen.add(node)
        for text in fields[2:]:
            head = int(text)
            if not 0 <= head < n or head == node:
                raise ValueError(f"{path.name}: invalid predecessor {head} of {node}")
            arcs.append((node, head))
    if len(seen) != n:
        raise ValueError(f"{path.name}: {len(seen)} precedence lines for {n} blocks")
    return arcs


def read_model(stem: Path):
    header, blocks = sections(stem.with_suffix(".cpit"))
    n = int(header["NBLOCKS"])
    profit = [None] * n
    for fields in blocks["OBJECTIVE_FUNCTION"]:
        profit[int(fields[0])] = float(fields[1])
    if any(value is None for value in profit):
        raise ValueError("objective does not cover every block")
    weight = [None] * n
    for fields in blocks["RESOURCE_CONSTRAINT_COEFFICIENTS"]:
        if int(fields[1]) == 0:
            weight[int(fields[0])] = float(fields[2])
    missing = [k for k, value in enumerate(weight) if value is None]
    if missing:
        raise ValueError(f"{len(missing)} blocks have no resource-0 coefficient")
    if any(value <= 0 for value in weight):
        raise ValueError("resource-0 coefficients are not strictly positive")
    limits = [fields for fields in blocks["RESOURCE_CONSTRAINT_LIMITS"] if int(fields[0]) == 0]
    if not limits or any(fields[2] != "L" for fields in limits):
        raise ValueError("resource 0 has no purely upper-bounded limits")
    capacity = sum(float(fields[3]) for fields in limits)
    return header, n, profit, weight, capacity, len(limits)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="directory with the extracted MineLib files")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--index", type=Path, default=ROOT / "data/processed/index.json")
    parser.add_argument("--max-nodes", type=int, default=120000)
    arguments = parser.parse_args()
    records = load_index(arguments.index)["instances"]
    imported, skipped = [], []
    for path in sorted(arguments.source.glob("*.cpit")):
        stem = path.with_suffix("")
        try:
            header, n, profit, weight, capacity, periods = read_model(stem)
            if n > arguments.max_nodes:
                raise ValueError(f"{n} blocks above --max-nodes")
            arcs = read_precedences(stem.with_suffix(".prec"), n)
        except (ValueError, KeyError, FileNotFoundError) as error:
            skipped.append((stem.name, str(error)))
            continue
        name = "minelib_" + stem.name
        payload = instance(
            range(n), profit, weight, arcs, identifier=name, numeric_type="floating",
            capacity=capacity,
            capacities=[round(capacity * f, 6) for f in (0.1, 0.25, 0.5, 1.0)],
            source={"origin": "DATA/MINELIB/INSTANCES.zip", "file": path.name,
                    "sha256": file_digest(path),
                    "precedence_sha256": file_digest(stem.with_suffix(".prec")),
                    "transformation": "single-period relaxation of CPIT: periods and discounting "
                                      f"dropped, knapsack row = resource 0, capacity = its limit "
                                      f"summed over {periods} periods"},
            metadata={"family": "minelib-derived", "nodes": n, "arcs": len(arcs),
                      "minelib_name": header.get("NAME", stem.name),
                      "minelib_type": header.get("TYPE", "CPIT")})
        records.append(store(payload, arguments.output, name))
        imported.append(name)
    save_index(arguments.index, records, "canonical instances referenced by suites and runs")
    print(f"imported {len(imported)} instances into {arguments.output}")
    for name, reason in skipped:
        print(f"  skipped {name}: {reason}")


if __name__ == "__main__":
    main()
