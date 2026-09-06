# Validation

Three independent routes must agree before an answer is reported.

## An exhaustive rational oracle

Small instances are solved by enumerating their closures with
`fractions.Fraction`, in exact arithmetic, and the solver is compared against
that value on 308 instances: hand-built corner cases and random DAGs across the
structural families, including negative profits, ties, degenerate ratios,
disconnected residuals and digraphs with cycles.

The comparison runs in every configuration of a rotation — full, local and
adaptive basis updates, partial and candidate-list pricing, each entering rule,
each ratio test, the dual simplex, and the residual warm restart — with
`--verify-every 1`, so the basis invariants and primal feasibility are checked
at *every* pivot rather than at the end.

The suite also reconstructs individual pivots against rational basis systems,
covering all four kinds of pivot (vertex or slack entering, vertex or slack
leaving).

## Two cross-check backends

Two maximum-flow backends answer the same questions through their own
certificates rather than through the simplex code, selectable with
`--algorithm`: a Newton iteration on the parametrised objective, and a
divide-and-conquer decomposition over the interval of ratios. They exist to
disagree with the simplex when the simplex is wrong.

## A separate verifier

Every optimal answer carries a primal-dual certificate: the ratio, the arc
multipliers and the per-vertex residuals. A verifier that shares no code with
the pivot loop re-checks it in the original units and on the original arcs,
after the condensation and the scaling have been undone. An answer whose
certificate does not re-check is reported as a numerical failure, not as a
solution.

```bash
build/pclp verify --instance <file> --result result.json
```

## Sanitizers and continuous integration

The `sanitize` preset builds with AddressSanitizer and UndefinedBehaviorSanitizer
and runs the same tests. A dedicated test intercepts `operator new` and requires
zero allocations inside the pivot loop, and the iterative graph walks are
exercised on a strongly connected component of thirty thousand vertices.

Continuous integration builds in Release, runs the five tests, and then runs a
small campaign end to end, asserting that every recorded run re-verified.
