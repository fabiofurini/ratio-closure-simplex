#!/usr/bin/env python3
"""Generates the synthetic instance families of the experimental plan.

Each family isolates one structural phenomenon.  Profits carry both signs, all
weights are strictly positive and every instance records the generator, its
parameters and its seed so that it can be rebuilt byte for byte.
"""
from __future__ import annotations
import argparse
import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, instance, load_index, save_index, store  # noqa: E402


def profits(rng, n, negative, correlation, weight):
    values = []
    for i in range(n):
        if rng.random() < negative:
            values.append(-rng.randint(1, 40))
        elif correlation:
            values.append(round(weight[i] * rng.uniform(0.5, 2.5), 3))
        else:
            values.append(rng.randint(1, 100))
    return values


def weights(rng, n, spread):
    if spread == "uniform":
        return [rng.randint(1, 10) for _ in range(n)]
    if spread == "dispersed":
        return [rng.randint(1, 1000) for _ in range(n)]
    return [rng.choice([1, 1, 2, 3, 10 ** rng.randint(0, 4)]) for _ in range(n)]


def empty(rng, n, **kw):
    return []


def chain(rng, n, **kw):
    return [(i, i - 1) for i in range(1, n)]


def forest(rng, n, components=8, **kw):
    arcs = []
    roots = sorted(rng.sample(range(n), min(components, n)))
    for i in range(n):
        if i in roots:
            continue
        arcs.append((i, rng.randrange(i) if i else 0))
    return arcs


def layered(rng, n, levels=8, density=0.02, skip=0.0, **kw):
    per = max(1, n // levels)
    layer = [min(levels - 1, i // per) for i in range(n)]
    buckets = [[i for i in range(n) if layer[i] == k] for k in range(levels)]
    arcs = []
    for k in range(1, levels):
        for i in buckets[k]:
            for j in buckets[k - 1]:
                if rng.random() < density:
                    arcs.append((i, j))
            if skip and k >= 2:
                for j in buckets[k - 2]:
                    if rng.random() < skip:
                        arcs.append((i, j))
        if not any(tail == i for tail, _ in arcs[-len(buckets[k]):]) and buckets[k - 1]:
            for i in buckets[k]:
                arcs.append((i, rng.choice(buckets[k - 1])))
    return arcs


def sparse(rng, n, degree=3, **kw):
    arcs = []
    for i in range(1, n):
        for _ in range(min(degree, i)):
            arcs.append((i, rng.randrange(i)))
    return sorted(set(arcs))


def dense(rng, n, density=0.2, **kw):
    return [(i, j) for i in range(n) for j in range(i) if rng.random() < density]


def diamonds(rng, n, module=4, **kw):
    arcs = []
    for base in range(0, n - module, module):
        top, left, right, bottom = (base + k for k in range(4))
        arcs += [(top, left), (top, right), (left, bottom), (right, bottom)]
        if base:
            arcs.append((bottom - module, top))
    return [(a, b) for a, b in arcs if a < n and b < n]


def disconnected(rng, n, components=6, **kw):
    size = max(1, n // components)
    arcs = []
    for start in range(0, n, size):
        stop = min(n, start + size)
        for i in range(start + 1, stop):
            arcs.append((i, rng.randrange(start, i)))
    return arcs


def transitive(rng, n, degree=2, extra=3.0, **kw):
    """Adds arcs implied by paths of length two and three, never new relations."""
    base = sparse(rng, n, degree)
    successors = {}
    for tail, head in base:
        successors.setdefault(tail, []).append(head)
    redundant = set()
    for tail, head in base:
        for middle in successors.get(head, ()):
            redundant.add((tail, middle))
            for far in successors.get(middle, ()):
                redundant.add((tail, far))
    redundant -= set(base)
    extra_arcs = sorted(redundant)
    rng.shuffle(extra_arcs)
    return sorted(set(base) | set(extra_arcs[: int(extra * len(base))]))


def cyclic(rng, n, components=10, **kw):
    size = max(2, n // components)
    arcs = []
    for start in range(0, n, size):
        stop = min(n, start + size)
        for i in range(start, stop):
            arcs.append((i, start + (i - start + 1) % (stop - start)))
        if start:
            arcs.append((start, start - 1))
    return arcs


def bilevel(rng, n, density=0.05, **kw):
    top = n // 2
    return [(i, j) for i in range(top) for j in range(top, n) if rng.random() < density]


FAMILIES = {"empty": empty, "chain": chain, "forest": forest, "layered": layered,
            "sparse": sparse, "dense": dense, "diamonds": diamonds,
            "disconnected": disconnected, "transitive": transitive, "cyclic": cyclic,
            "bilevel": bilevel}

# Nodes, family parameters and numeric profile of the campaign's generated set.
PLAN = [
    ("empty", {}, [200, 2000, 20000], ["uniform"], [0.0, 0.3]),
    ("chain", {}, [200, 2000, 20000], ["uniform"], [0.0, 0.3]),
    ("forest", {"components": 8}, [200, 2000, 20000], ["uniform", "heterogeneous"], [0.3]),
    ("layered", {"levels": 8, "density": 0.05}, [200, 2000, 8000], ["uniform"], [0.0, 0.3, 0.6]),
    ("layered", {"levels": 20, "density": 0.02, "skip": 0.005}, [2000, 8000], ["dispersed"], [0.3]),
    ("sparse", {"degree": 3}, [200, 2000, 20000], ["uniform", "dispersed"], [0.3]),
    ("sparse", {"degree": 8}, [2000, 8000], ["uniform"], [0.3]),
    ("dense", {"density": 0.1}, [200, 800, 2000], ["uniform"], [0.3]),
    ("diamonds", {"module": 4}, [200, 2000, 20000], ["uniform"], [0.3]),
    ("disconnected", {"components": 6}, [200, 2000, 20000], ["uniform"], [0.3]),
    ("disconnected", {"components": 64}, [2000, 20000], ["uniform"], [0.3]),
    ("transitive", {"degree": 2, "extra": 3.0}, [200, 2000, 8000], ["uniform"], [0.3]),
    ("cyclic", {"components": 10}, [200, 2000, 20000], ["uniform"], [0.3]),
    ("bilevel", {"density": 0.02}, [200, 2000, 8000], ["uniform"], [0.3]),
]


def build(family, parameters, n, spread, negative, correlation, ties, seed):
    rng = random.Random(seed)
    weight = weights(rng, n, spread)
    profit = profits(rng, n, negative, correlation, weight)
    if ties:
        # Exact ties: repeat one ratio on a random share of the nodes.
        for i in range(n):
            if rng.random() < ties:
                weight[i], profit[i] = 4, 8 if profit[i] >= 0 else -8
    arcs = FAMILIES[family](rng, n, **parameters)
    arcs = sorted({(a, b) for a, b in arcs if a != b})
    total = sum(weight)
    return weight, profit, arcs, total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data/generated")
    parser.add_argument("--index", type=Path, default=ROOT / "data/generated/index.json")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--base-seed", type=int, default=20260906)
    parser.add_argument("--scale", type=float, default=1.0, help="node-count multiplier")
    arguments = parser.parse_args()
    records = []
    for family, parameters, sizes, spreads, negatives in PLAN:
        for n in sizes:
            n = max(2, int(n * arguments.scale))
            for spread in spreads:
                for negative in negatives:
                    for replica in range(arguments.seeds):
                        ties = 0.4 if replica == 2 else 0.0
                        correlation = replica == 1
                        # Python randomises hash() of strings per process, so a
                        # seed derived from it is not reproducible across runs.
                        # A content hash of the same fields is.
                        key = repr((family, n, spread, negative, replica)).encode()
                        seed = arguments.base_seed + int(hashlib.sha256(key).hexdigest()[:8], 16) % 10 ** 6
                        weight, profit, arcs, total = build(
                            family, parameters, n, spread, negative, correlation, ties, seed)
                        tag = "-".join(f"{k}{v}" for k, v in parameters.items()) or "plain"
                        name = (f"gen_{family}_{tag}_n{n}_{spread}_neg{int(negative * 100)}"
                                f"_r{replica}")
                        payload = instance(
                            range(n), profit, weight, arcs, identifier=name, numeric_type="integer",
                            capacity=round(total * 0.25, 6),
                            capacities=[round(total * f, 6) for f in (0.0, 0.05, 0.25, 0.5, 1.0)],
                            metadata={"family": family, "generator_parameters": parameters,
                                      "nodes": n, "arcs": len(arcs), "seed": seed,
                                      "weight_spread": spread, "negative_share": negative,
                                      "correlated": correlation, "tie_share": ties,
                                      "total_weight": total})
                        records.append(store(payload, arguments.output, name))
    save_index(arguments.index, records, "synthetic instances rebuilt by tools/generate/instances.py")
    print(f"generated {len(records)} instances into {arguments.output}")


if __name__ == "__main__":
    main()
