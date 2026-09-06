# How the method works

## The basis is a forest

A basic feasible solution of

```
max  sum_i p_i y_i     s.t.   y_i <= y_j  for every arc (i,j),
                              sum_i w_i y_i = 1,   y >= 0
```

has a shape. The tight precedence arcs form a **forest** on the vertices: one
tree carries the positive values, every other tree is anchored at zero. So the
basis is not stored as a matrix but as a forest plus a root, and the algebra
collapses accordingly.

Write `b_i = p_i - rho*w_i` for the current ratio. The reduced cost of a
nonbasic vertex variable is the aggregate of `b` over its tree, and the reduced
cost of a nonbasic precedence slack is the signed aggregate over the subtree
hanging below its arc:

```
c(y_T) = p(T) - rho*w(T)          c(s_e) = +/- [ p(D_e) - rho*w(D_e) ]
```

Every one of those aggregates comes out of a single postorder walk, and there
are exactly `n-1` candidates to price. **Complete pricing therefore costs `O(n)`
arithmetic, whatever the number of precedence arcs**, and no non-forest arc is
ever priced.

## A pivot merges or splits a tree

A pivot links one arc and cuts another. Two trees **merge**, or one tree
**splits**. The direction is `+1` on the entering subtree, `-kappa` on the
positive component and zero elsewhere, so only an arc crossing the boundary of
one of those two sets can block. That is what `--ratio-test restricted` scans;
`--ratio-test early` additionally stops at the first blocker that already
achieves a zero step, since no step can be smaller.

After the pivot only the components the pivot touched need their aggregates
recomputed, which is what `--basis-update local` does; `adaptive` falls back to
a full rebuild when the affected part is large enough to make it cheaper.

## Degeneracy

Most pivots on this program take a zero step. The solver runs a chosen entering
rule until a number of consecutive degenerate pivots is reached, then falls back
to Bland's rule, which is finite, and releases the fallback at the first pivot
with a positive step. The threshold is `--degeneracy-trigger`. A permanent
fallback to Bland is correct but markedly slower, which is why it is a safety
net at a distant threshold rather than the default rule.

## The canonical path, and the warm restart

Extract a block, delete it, ask again on the residual, until nothing is left.
The result is the canonical decomposition: blocks of strictly decreasing ratio,
the threshold of every vertex, and the breakpoints of the parametric closure
value. Which set is extracted at a tie is fixed by `--canonicalization`: `dual`
takes the maximal set by complementarity, `sequential` aggregates increments of
equal ratio.

The extracted block *is* the positive tree, so the other trees survive untouched
and stay anchored: one tree detaches at a time. `--warm-start residual` reuses
that forest for the next oracle instead of rebuilding from the empty basis.

It is admissible under one condition. The values are `1/w(T)` on the positive
tree `T` and zero elsewhere, so an active arc leaving `T` would violate
`y_i <= y_j`. The tree chosen to carry the positive values must therefore be
**closed in the residual**. The solver checks that in `O(m)` per oracle rather
than assuming it, picks the best closed surviving tree by ratio, and restarts
cold when no surviving tree is closed. The sequence produced is identical block
by block to the one obtained without the warm restart.

## Certificates

Every optimal answer carries a primal-dual certificate: the ratio, the arc
multipliers and the per-vertex residuals. A separate verifier re-checks it in
the original units and on the original arcs, after the condensation and the
scaling have been undone, and `pclp verify` runs that verifier alone on a saved
result without re-optimising. An answer whose certificate does not re-check is
reported as a numerical failure rather than as a solution.

## Cross-checks

Two maximum-flow backends answer the same questions through their own
certificates, selectable with `--algorithm`: a Newton iteration on the
parametrised objective, and a divide-and-conquer decomposition over the interval
of ratios. They exist to disagree with the simplex when the simplex is wrong.
