"""Shared helpers for instance import, generation, campaigns and analysis.

Every canonical instance is written once, named by its content hash, and
referenced by suites and runs through that identifier.  Nothing here writes
outside the project tree.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAT_VERSION = 1


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(payload: dict) -> str:
    """The exact serialisation the solver hashes as ``instance_sha256``."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".incomplete.{os.getpid()}")
    temporary.write_text(text)
    os.replace(temporary, path)


def instance(node_ids, profit, weight, arcs, *, identifier, numeric_type,
             capacity=None, capacities=None, source=None, metadata=None) -> dict:
    payload = {
        "format_version": FORMAT_VERSION,
        "id": identifier,
        "node_ids": list(node_ids),
        "profit": list(profit),
        "weight": list(weight),
        "arcs": [list(a) for a in arcs],
        "numeric_type": numeric_type,
    }
    if capacity is not None:
        payload["capacity"] = capacity
    if capacities is not None:
        payload["capacities"] = list(capacities)
    if source is not None:
        payload["source"] = source
    if metadata is not None:
        payload["metadata"] = metadata
    validate(payload)
    return payload


def validate(payload: dict) -> None:
    n = len(payload["node_ids"])
    assert n and len(payload["profit"]) == n and len(payload["weight"]) == n, "array lengths"
    assert len(set(map(str, payload["node_ids"]))) == n, "duplicate node identifiers"
    for w in payload["weight"]:
        value = float(w)
        assert value > 0 and value == value and abs(value) != float("inf"), f"weight {w}"
    for p in payload["profit"]:
        value = float(p)
        assert value == value and abs(value) != float("inf"), f"profit {p}"
    for tail, head in payload["arcs"]:
        assert 0 <= tail < n and 0 <= head < n, "arc endpoint"
    for key in ("capacity", *(("capacities",) if "capacities" in payload else ())):
        if key in payload:
            values = payload[key] if isinstance(payload[key], list) else [payload[key]]
            for c in values:
                assert float(c) >= 0, "capacity"


def store(payload: dict, directory: Path, name: str) -> dict:
    """Writes the instance and returns its index record.

    The recorded path is relative to the project root, so a caller may pass a
    relative directory; it is resolved first, and a destination outside the
    project is refused rather than silently written.
    """
    directory = Path(directory).resolve()
    try:
        directory.relative_to(ROOT)
    except ValueError:
        raise SystemExit(f"refusing to write outside the project: {directory}")
    text = canonical(payload)
    record = {
        "name": name,
        "path": str((directory / f"{name}.json").relative_to(ROOT)),
        "sha256": digest(text),
        "nodes": len(payload["node_ids"]),
        "arcs": len(payload["arcs"]),
        "capacity": payload.get("capacity"),
        "family": (payload.get("metadata") or {}).get("family", "unknown"),
        "origin": (payload.get("source") or {}).get("origin", "generated"),
    }
    write_atomic(directory / f"{name}.json", text + "\n")
    return record


def load_index(path: Path) -> dict:
    if not path.exists():
        return {"instances": []}
    return json.loads(path.read_text())


def save_index(path: Path, records: list[dict], note: str) -> None:
    by_name = {r["name"]: r for r in records}
    payload = {"note": note, "count": len(by_name),
               "instances": sorted(by_name.values(), key=lambda r: r["name"])}
    write_atomic(path, json.dumps(payload, indent=1) + "\n")
