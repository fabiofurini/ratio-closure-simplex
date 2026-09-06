#!/usr/bin/env python3
"""Compare the C++ reference solver with exhaustive closure enumeration."""

from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile


def closures(n, arcs):
    result = []
    for mask in range(1 << n):
        if all(not (mask >> tail & 1) or (mask >> head & 1) for tail, head in arcs):
            result.append(mask)
    return result


def total(mask, values):
    return sum(value for index, value in enumerate(values) if mask >> index & 1)


def exact_ratio(profit, weight, arcs):
    return max(Fraction(total(mask, profit), total(mask, weight))
               for mask in closures(len(profit), arcs) if mask)


def exact_lp(profit, weight, arcs, capacity):
    points = [(total(mask, weight), total(mask, profit)) for mask in closures(len(profit), arcs)]
    answer = max(Fraction(value) for used, value in points if used <= capacity)
    for low_weight, low_value in points:
        for high_weight, high_value in points:
            if low_weight < capacity < high_weight:
                answer = max(answer, Fraction((high_weight-capacity)*low_value +
                                              (capacity-low_weight)*high_value,
                                              high_weight-low_weight))
    return answer


def run(program, instance, task):
    with tempfile.TemporaryDirectory() as directory:
        filename = Path(directory) / "instance.json"
        filename.write_text(json.dumps(instance))
        completed = subprocess.run([program, task, "--instance", str(filename)],
                                   check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def check(program, profit, weight, arcs):
    instance = {"id": "differential", "node_ids": list(range(1, len(profit)+1)),
                "profit": profit, "weight": weight,
                "arcs": [[tail+1, head+1] for tail, head in arcs]}
    ratio = run(program, instance, "ratio")
    assert ratio["status"] == "optimal", ratio
    assert abs(float(exact_ratio(profit, weight, arcs)) - ratio["ratio"]) < 1e-10, ratio
    for capacity in (0, sum(weight)//3, sum(weight), sum(weight)+1):
        instance["capacity"] = capacity
        solved = run(program, instance, "solve")
        assert solved["status"] == "optimal", solved
        assert abs(float(exact_lp(profit, weight, arcs, capacity)) - solved["objective"]) < 1e-10, solved


def main():
    program = sys.argv[1]
    fixtures = [([1, 1], [1, 1], []), ([-3, -1], [1, 2], [(0, 1)]),
                ([0, 0], [1, 2], []), ([3], [2], [])]
    rng = random.Random(20260905)
    for _ in range(32):
        n = rng.randint(2, 6)
        order = list(range(n))
        rng.shuffle(order)
        arcs = [(order[i], order[j]) for i in range(n) for j in range(i+1, n)
                if rng.random() < 0.4]
        fixtures.append(([rng.randint(-5, 8) for _ in range(n)],
                         [rng.randint(1, 5) for _ in range(n)], arcs))
    for profit, weight, arcs in fixtures:
        check(program, profit, weight, arcs)
    print(f"checked {len(fixtures)} small DAGs against exhaustive enumeration")


if __name__ == "__main__":
    main()
