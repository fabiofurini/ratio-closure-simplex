#!/usr/bin/env python3
"""Imports the historical single-capacity PCKP instances.

The ``.dat`` files carry ``n m capacity`` followed by one line per node with
identifier, profit, weight, out-degree and the list of its prerequisites, which
is exactly this project's arc convention (tail requires head).  ``--cross-check``
re-reads the companion CPLEX ``.lp`` file and refuses any instance whose rows are
not a single capacity constraint plus simple precedence rows with unit bounds.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, file_digest, instance, load_index, save_index, store  # noqa: E402


def read_dat(path: Path):
    tokens = path.read_text().split()
    at = 0

    def take():
        nonlocal at
        value = tokens[at]
        at += 1
        return value

    n = int(take())
    m = int(take())
    capacity = float(take())
    profit, weight, arcs = [], [], []
    for expected in range(n):
        identifier = int(take())
        if identifier != expected:
            raise ValueError(f"{path.name}: node identifiers must be 0..n-1 in order")
        profit.append(float(take()))
        weight.append(float(take()))
        for _ in range(int(take())):
            arcs.append((expected, int(take())))
    if at != len(tokens):
        raise ValueError(f"{path.name}: trailing data after {n} nodes")
    if len(arcs) != m:
        raise ValueError(f"{path.name}: header declares {m} arcs, found {len(arcs)}")
    return n, capacity, profit, weight, arcs


TERM = re.compile(r"([+-])?\s*(\d+\.?\d*(?:[eE][+-]?\d+)?)?\s*\*?\s*([A-Za-z][A-Za-z0-9_]*)")
LABEL = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*:", re.M)


def read_lp(path: Path):
    """Parses the model and rejects anything outside the supported family."""
    text = "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("\\"))
    objective_sections = re.split(r"^\s*Maximi[sz]e\s*$", text, flags=re.M)
    if len(objective_sections) != 2:
        raise ValueError(f"{path.name}: a single Maximize section is required")
    text = objective_sections[1]
    body = re.split(r"^\s*(?:Subject To|st\.?|s\.t\.)\s*$", text, flags=re.M)
    if len(body) != 2:
        raise ValueError(f"{path.name}: single constraint section required")
    head, rest = body
    head = LABEL.sub("", head, count=1)
    parts = re.split(r"^\s*(?:Bounds)\s*$", rest, flags=re.M)
    if len(parts) != 2:
        raise ValueError(f"{path.name}: explicit Bounds section required")
    rows, tail = parts
    for keyword in ("General", "Semi-Continuous", "SOS"):
        if re.search(rf"^\s*{keyword}", tail, re.M):
            raise ValueError(f"{path.name}: {keyword} section is outside the LP family")
    # A Binaries/Integers section is kept as provenance: the imported instance is
    # the LP relaxation of that integer model, never the integer model itself.
    integral = bool(re.search(r"^\s*(?:Binaries|Integers)\s*$", tail, re.M))
    bounded, declared = re.split(r"^\s*(?:Binaries|Integers)\s*$", tail, flags=re.M)[0], set()

    def terms(chunk):
        found = []
        for sign, number, name in TERM.findall(chunk):
            value = float(number) if number else 1.0
            found.append((-value if sign == "-" else value, name))
        return found

    objective = dict((name, value) for value, name in terms(head))
    capacity_rows, precedence, entries = [], [], re.split(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", rows, flags=re.M)
    for name, chunk in zip(entries[1::2], entries[2::2]):
        chunk = chunk.strip()
        relation = re.search(r"(<=|>=|=<|=>|=)\s*([-+0-9.eE]+)\s*$", chunk)
        if not relation:
            raise ValueError(f"{path.name}: row {name} has no recognised right-hand side")
        operator, rhs = relation.group(1), float(relation.group(2))
        coefficients = terms(chunk[: relation.start()])
        if operator not in ("<=", "=<"):
            raise ValueError(f"{path.name}: row {name} is not a <= row")
        if len(coefficients) == 2 and rhs == 0 and sorted(v for v, _ in coefficients) == [-1.0, 1.0]:
            positive = [name for value, name in coefficients if value > 0][0]
            negative = [name for value, name in coefficients if value < 0][0]
            precedence.append((positive, negative))
        elif all(value > 0 for value, _ in coefficients) and rhs > 0:
            capacity_rows.append((coefficients, rhs))
        else:
            raise ValueError(f"{path.name}: row {name} is neither a capacity nor a precedence row")
    if len(capacity_rows) != 1:
        raise ValueError(f"{path.name}: {len(capacity_rows)} capacity rows; the model is not single-capacity")
    for line in bounded.splitlines():
        line = line.strip()
        if not line or line == "End":
            continue
        bound = re.fullmatch(r"0\s*<=\s*([A-Za-z][A-Za-z0-9_]*)\s*<=\s*1", line)
        if not bound:
            raise ValueError(f"{path.name}: bound '{line}' is not 0 <= x <= 1")
        declared.add(bound.group(1))
    weights, capacity = dict((name, value) for value, name in capacity_rows[0][0]), capacity_rows[0][1]
    # The Bounds section is the variable universe: CPLEX omits zero objective
    # coefficients, while a variable missing from the capacity row has weight
    # zero and is outside the family this project supports.
    if not declared:
        raise ValueError(f"{path.name}: no unit-bounded variables")
    if not set(objective) <= declared or not set(weights) <= declared:
        raise ValueError(f"{path.name}: a row references a variable without unit bounds")
    missing = declared - set(weights)
    if missing:
        raise ValueError(f"{path.name}: {len(missing)} variables have zero capacity coefficient")
    objective = {name: objective.get(name, 0.0) for name in declared}
    return objective, weights, capacity, precedence, integral


def refine(profit, weight, arcs, n):
    """Colour refinement: equal colours means equal local model structure."""
    colour = [hash((round(p, 6), round(w, 6))) for p, w in zip(profit, weight)]
    outgoing, incoming = [[] for _ in range(n)], [[] for _ in range(n)]
    for tail, head in arcs:
        outgoing[tail].append(head)
        incoming[head].append(tail)
    classes = 0
    while True:
        refined = [hash((colour[i], tuple(sorted(colour[j] for j in outgoing[i])),
                         tuple(sorted(colour[j] for j in incoming[i])))) for i in range(n)]
        distinct = len(set(refined))
        colour = refined
        if distinct == classes:
            return colour
        classes = distinct


def cross_check(dat, lp):
    """Verifies that the two files describe the same model.

    The historical ``.dat`` files do not always use the variable numbering of
    the companion ``.lp``.  When the direct mapping fails, the check falls back
    to colour refinement; a bijection is only claimed when every colour class is
    a singleton and the mapped arc sets coincide exactly.
    """
    n, capacity, profit, weight, arcs = dat
    objective, weights, lp_capacity, precedence, _ = lp
    if len(objective) != n or len(weights) != n:
        raise ValueError(f"variable count {len(objective)}/{len(weights)} differs from {n}")
    if abs(lp_capacity - capacity) > 1e-6 * max(1.0, capacity):
        raise ValueError(f"capacity {lp_capacity} differs from {capacity}")
    order = sorted(objective, key=lambda name: int(re.sub(r"\D", "", name)))
    index = {name: k for k, name in enumerate(order)}
    lp_profit = [objective[name] for name in order]
    lp_weight = [weights[name] for name in order]
    lp_arcs = sorted((index[a], index[b]) for a, b in precedence)
    close = lambda a, b: abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))
    if (all(map(close, lp_profit, profit)) and all(map(close, lp_weight, weight))
            and lp_arcs == sorted(arcs)):
        return "identical variable numbering"
    if len(lp_arcs) != len(arcs):
        raise ValueError(f"{len(lp_arcs)} precedence rows against {len(arcs)} arcs")
    left = refine(profit, weight, arcs, n)
    right = refine(lp_profit, lp_weight, lp_arcs, n)
    if sorted(left) != sorted(right):
        raise ValueError("colour refinement separates the two models")
    if len(set(left)) != n:
        return "equal colour-refinement histograms (permutation not pinned down)"
    mapping = {colour: k for k, colour in enumerate(right)}
    permuted = sorted((mapping[left[tail]], mapping[left[head]]) for tail, head in arcs)
    if permuted != lp_arcs:
        raise ValueError("arc sets differ under the unique colour bijection")
    for k, colour in enumerate(left):
        target = mapping[colour]
        if not close(profit[k], lp_profit[target]) or not close(weight[k], lp_weight[target]):
            raise ValueError("profit or weight differs under the unique colour bijection")
    return "isomorphic under a unique colour bijection"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="directory holding the historical .dat files")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--index", type=Path, default=ROOT / "data/processed/index.json")
    parser.add_argument("--cross-check", action="store_true", help="re-read the companion .lp models")
    parser.add_argument("--max-nodes", type=int, default=0)
    arguments = parser.parse_args()
    records = load_index(arguments.index)["instances"]
    imported, skipped = [], []
    for path in sorted(arguments.source.glob("*.dat")):
        try:
            dat = read_dat(path)
        except ValueError as error:
            skipped.append((path.name, str(error)))
            continue
        n, capacity, profit, weight, arcs = dat
        if arguments.max_nodes and n > arguments.max_nodes:
            skipped.append((path.name, f"{n} nodes above --max-nodes"))
            continue
        lp = path.with_suffix("")
        if arguments.cross_check:
            if not lp.exists():
                skipped.append((path.name, "companion .lp model is missing"))
                continue
            try:
                model = read_lp(lp)
                agreement = cross_check(dat, model)
                relaxed = model[4]
            except Exception as error:
                skipped.append((path.name, f"cross-check failed: {error}"))
                continue
        else:
            relaxed, agreement = None, False
        name = "pckp_" + lp.stem.replace(".", "_")
        payload = instance(
            range(n), profit, weight, arcs, identifier=name, numeric_type="floating",
            capacity=capacity,
            capacities=[round(capacity * f, 6) for f in (0.25, 0.5, 1.0, 2.0)],
            source={"origin": "DATA/INSTANCES/PCKP_BB/instances", "file": path.name,
                    "sha256": file_digest(path),
                    "model_cross_checked": agreement and f"{lp.name}: {agreement}",
                    "transformation": "LP relaxation of the historical binary model"
                                      if relaxed else
                                      "none: the .dat file is already a single-capacity PCKP"},
            metadata={"family": "pckp-historical", "nodes": n, "arcs": len(arcs)})
        records.append(store(payload, arguments.output, name))
        imported.append(name)
    save_index(arguments.index, records, "canonical instances referenced by suites and runs")
    print(f"imported {len(imported)} instances into {arguments.output}")
    for name, reason in skipped:
        print(f"  skipped {name}: {reason}")


if __name__ == "__main__":
    main()
