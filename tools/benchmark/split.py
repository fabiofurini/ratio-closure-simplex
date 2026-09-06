#!/usr/bin/env python3
"""Freezes the training, validation and test manifests.

Instances are grouped so that every replica, capacity and transformation of the
same generated base stays on one side of the split, then the groups are
stratified by origin, family and size decade and dealt out deterministically.
The manifests are written once; regenerating them with the same inputs and seed
reproduces the same assignment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, load_index, write_atomic  # noqa: E402


def group_of(record: dict) -> str:
    """All replicas of one generated configuration share a group."""
    return re.sub(r"_r\d+$", "", record["name"])


def bucket(nodes: int) -> str:
    return "small" if nodes < 1000 else "medium" if nodes < 20000 else "large"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/splits")
    parser.add_argument("--shares", default="50,25,25")
    parser.add_argument("--seed", type=int, default=20260906)
    options = parser.parse_args()
    records = []
    for path in options.index:
        records.extend(load_index(path)["instances"])
    groups: dict[str, list[dict]] = {}
    for record in records:
        groups.setdefault(group_of(record), []).append(record)
    strata: dict[tuple, list[str]] = {}
    for name, members in groups.items():
        key = (members[0]["origin"], members[0]["family"], bucket(members[0]["nodes"]))
        strata.setdefault(key, []).append(name)
    shares = [int(x) for x in options.shares.split(",")]
    names = ["train", "validation", "test"]
    assignment: dict[str, list[dict]] = {name: [] for name in names}
    quota = []
    for name, share in zip(names, shares):
        quota += [name] * share
    for key in sorted(strata):
        members = sorted(strata[key])
        for position, group in enumerate(members):
            # A rotating offset per stratum keeps small strata from all landing
            # in the training split.
            # Python randomises hash() of strings per process; a content hash of
            # the stratum keeps the assignment stable across runs and machines.
            offset = int(hashlib.sha256(repr(key).encode()).hexdigest()[:8], 16)
            target = quota[(position * len(quota) // max(1, len(members)) + options.seed + offset) % len(quota)]
            assignment[target].extend(groups[group])
    for name in names:
        chosen = sorted(assignment[name], key=lambda r: r["name"])
        payload = {"split": name, "seed": options.seed, "shares": options.shares,
                   "count": len(chosen), "instances": chosen}
        write_atomic(options.output / f"{name}.json", json.dumps(payload, indent=1) + "\n")
        families = sorted({r["family"] for r in chosen})
        print(f"{name:11s} {len(chosen):4d} instances, {len(families)} families")


if __name__ == "__main__":
    main()
