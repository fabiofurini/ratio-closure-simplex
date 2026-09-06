#!/usr/bin/env python3
"""Exact checks for the tutorial, not the optimized experimental solver.

Forest directions are checked against separately assembled basis matrices.
Closure enumeration independently checks ratios and canonical decompositions.
Only Python's standard library is needed. All generated files stay in build/.
"""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "tutorial" / "generated"


def solve(a, b):
    n = len(b)
    mat = [[F(x) for x in row] + [F(rhs)] for row, rhs in zip(a, b)]
    for k in range(n):
        pivot = next(i for i in range(k, n) if mat[i][k])
        mat[k], mat[pivot] = mat[pivot], mat[k]
        d = mat[k][k]
        mat[k] = [v / d for v in mat[k]]
        for i in range(n):
            if i != k:
                d = mat[i][k]
                mat[i] = [x - d*y for x, y in zip(mat[i], mat[k])]
    return [row[-1] for row in mat]


def matrix(p, w, arcs):
    n, m = len(p), len(arcs)
    a = [list(w) + [0]*m]
    for e, (i, j) in enumerate(arcs):
        row = [0]*(n+m)
        row[i], row[j], row[n+e] = 1, -1, 1
        a.append(row)
    return a


def forest_state(p, w, arcs, nb):
    n, m = len(p), len(arcs)
    edges = {v-n for v in nb if v >= n}
    anchors = {v for v in nb if v < n}
    adj = [[] for _ in p]
    for e in edges:
        i, j = arcs[e]
        adj[i].append((j, e))
        adj[j].append((i, e))
    unseen, trees = set(range(n)), []
    while unseen:
        stack, tree = [min(unseen)], set()
        while stack:
            u = stack.pop()
            if u in tree:
                continue
            tree.add(u)
            stack.extend(v for v, _ in adj[u] if v not in tree)
        unseen -= tree
        trees.append(tree)
    assert len(edges) == n-len(trees)
    assert all(len(t & anchors) <= 1 for t in trees)
    free = [t for t in trees if not t & anchors]
    assert len(free) == 1
    main = free[0]
    W = sum(w[i] for i in main)
    rho = F(sum(p[i] for i in main), W)
    y = [F(int(i in main), W) for i in range(n)]
    values = y + [y[j]-y[i] for i, j in arcs]
    assert min(values) >= 0
    assert all(values[j] == 0 for j in nb)
    descendants, signs = {}, {}
    for tree in trees:
        root = next(iter(tree & anchors)) if tree & anchors else min(tree)
        parent, order = {root: None}, [root]
        for u in order:
            for v, e in adj[u]:
                if v == parent[u]:
                    continue
                assert v not in parent
                parent[v] = u
                order.append(v)
        sub = {i: {i} for i in tree}
        for v in reversed(order[1:]):
            u = parent[v]
            e = next(e for node, e in adj[v] if node == u)
            descendants[e] = set(sub[v])
            signs[e] = 1 if arcs[e] == (u, v) else -1
            sub[u] |= sub[v]
    directions, reduced = {}, {}
    for q in sorted(nb):
        if q < n:
            support = next(t for t in trees if q in t)
            sign = 1
        else:
            support, sign = descendants[q-n], signs[q-n]
        h = [F(sign*int(i in support)) for i in range(n)]
        kappa = sum(w[i]*h[i] for i in range(n)) / W
        dy = [h[i]-kappa*int(i in main) for i in range(n)]
        directions[q] = dy + [dy[j]-dy[i] for i, j in arcs]
        reduced[q] = sum(p[i]*dy[i] for i in range(n))
        assert directions[q][q] == 1
        assert all(directions[q][z] == 0 for z in nb if z != q)
    return values, rho, directions, reduced, main, edges, anchors


def ratio_closure_ratio(p, w, arcs, counters):
    n, m = len(p), len(arcs)
    sinks = [i for i in range(n) if not any(u == i for u, _ in arcs)]
    assert sinks, "This pedagogical checker expects a DAG."
    nb = set(range(n)) - {min(sinks)}
    a, b = matrix(p, w, arcs), [1]+[0]*m
    costs = list(p)+[0]*m
    seen, trace = set(), []
    for iteration in range(1000):
        key = tuple(sorted(nb))
        assert key not in seen, "Repeated basis under Bland's rule"
        seen.add(key)
        basic = sorted(set(range(n+m))-nb)
        B = [[row[j] for j in basic] for row in a]
        values, rho, directions, reduced, main, edges, anchors = forest_state(p, w, arcs, nb)
        linear_values = solve(B, b)
        assert linear_values == [values[j] for j in basic]
        transposed = [list(column) for column in zip(*B)]
        alpha = [-reduced[n+e] if e in edges else F(0) for e in range(m)]
        multipliers = solve(transposed, [costs[j] for j in basic])
        assert multipliers == [rho] + alpha
        counters['checked_multiplier_systems'] += 1
        for q in sorted(nb):
            direct = solve(B, [-row[q] for row in a])
            assert direct == [directions[q][j] for j in basic]
            direct_rc = costs[q] + sum(costs[j]*d for j, d in zip(basic, direct))
            assert direct_rc == reduced[q]
            assert costs[q] - sum(row[q]*pi for row,pi in zip(a,multipliers)) == reduced[q]
            counters['checked_directions'] += 1
        counters['checked_bases'] += 1
        improving = [q for q in sorted(nb) if reduced[q] > 0]
        if not improving:
            alpha = [F(0)]*m
            for e in edges:
                alpha[e] = -reduced[n+e]
            residual = [w[i]*rho-p[i] for i in range(n)]
            for e, (i, j) in enumerate(arcs):
                residual[i] += alpha[e]
                residual[j] -= alpha[e]
            assert min(alpha, default=0) >= 0
            assert min(residual) >= 0
            assert all(residual[i] == 0 for i in set(range(n))-anchors)
            assert all(residual[i] == -reduced[i] for i in anchors)
            return rho, main, trace
        q = improving[0]
        choices = [(values[j]/(-directions[q][j]), j)
                   for j in basic if directions[q][j] < 0]
        step, leaving = min(choices)
        unit_row = [F(int(j == leaving)) for j in basic]
        row_multiplier = solve(transposed, unit_row)
        for candidate in sorted(nb):
            row_entry = sum(pi*row[candidate] for pi,row in zip(row_multiplier,a))
            assert row_entry == -directions[candidate][leaving]
        counters['checked_pivot_rows'] += 1
        next_values = [v+step*d for v, d in zip(values, directions[q])]
        assert min(next_values) >= 0
        new_nb = (nb-{q}) | {leaving}
        rebuilt = forest_state(p, w, arcs, new_nb)[0]
        assert rebuilt == next_values
        trace.append(dict(iteration=iteration+1, entering=q, leaving=leaving,
                          reduced=reduced[q], step=step, rho_before=rho,
                          rho_after=rho+step*reduced[q], main=sorted(main),
                          forest=sorted(edges), anchors=sorted(anchors),
                          values=values, direction=directions[q]))
        nb = new_nb
    raise AssertionError('Pedagogical iteration guard exceeded')


def closures(n, arcs):
    return [s for s in range(1 << n)
            if all(not(s >> i & 1) or (s >> j & 1) for i, j in arcs)]


def total(mask, a):
    return sum(v for i, v in enumerate(a) if mask >> i & 1)


def exact_blocks(p, w, arcs):
    cs, prefix, result = closures(len(p), arcs), 0, []
    while prefix != (1 << len(p))-1:
        residuals = [s ^ prefix for s in cs if s != prefix and s & prefix == prefix]
        rho = max(F(total(s, p), total(s, w)) for s in residuals)
        tied = [s for s in residuals if F(total(s, p), total(s, w)) == rho]
        block = 0
        for s in tied:
            block |= s
        assert block in tied
        result.append((block, rho))
        prefix |= block
    return result


def ratio_closure_blocks(p, w, arcs, counters):
    active, blocks, full_trace = list(range(len(p))), [], []
    while active:
        inv = {i: k for k, i in enumerate(active)}
        pp, ww = [p[i] for i in active], [w[i] for i in active]
        aa = [(inv[i], inv[j]) for i, j in arcs if i in inv and j in inv]
        rho, support, trace = ratio_closure_ratio(pp, ww, aa, counters)
        cs = closures(len(active), aa)
        assert rho == max(F(total(s, pp), total(s, ww)) for s in cs if s)
        mask = sum(1 << active[i] for i in support)
        if blocks and blocks[-1][1] == rho:
            blocks[-1] = (blocks[-1][0] | mask, rho)
        else:
            assert not blocks or blocks[-1][1] > rho
            blocks.append((mask, rho))
        full_trace.append(trace)
        active = [v for k, v in enumerate(active) if k not in support]
    assert blocks == exact_blocks(p, w, arcs)
    return blocks, full_trace


def exact_lp(p, w, arcs, capacity):
    points = [(total(s, w), total(s, p)) for s in closures(len(p), arcs)]
    best = max(F(v) for weight, v in points if weight <= capacity)
    for wl, pl in points:
        for wh, ph in points:
            if wl < capacity < wh:
                best = max(best, ((wh-capacity)*pl+(capacity-wl)*ph)/(wh-wl))
    return best


def interpolated(p, w, blocks, capacity):
    value, remaining = F(0), F(capacity)
    for mask, rho in blocks:
        if rho <= 0 or remaining <= 0:
            break
        used = min(remaining, total(mask, w))
        value += used*rho
        remaining -= used
    return value


def texfrac(x):
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else rf'\frac{{{x.numerator}}}{{{x.denominator}}}'


def varname(j, n, arcs):
    if j < n:
        return f'y_{{{j+1}}}'
    i, k = arcs[j-n]
    return f's_{{{i+1},{k+1}}}'


def emit_tex(example, arcs, blocks, trace):
    OUT.mkdir(parents=True, exist_ok=True)
    p, w, n = example['profit'], example['weight'], len(example['profit'])
    rows = [r'\begin{tabular}{c'+'r'*n+'}', r'\toprule',
            '$i$ & '+' & '.join(str(i+1) for i in range(n))+r' \\',
            r'\midrule', '$p_i$ & '+' & '.join(map(str, p))+r' \\',
            '$w_i$ & '+' & '.join(map(str, w))+r' \\', r'\bottomrule', r'\end{tabular}']
    (OUT/'instance_table.tex').write_text('\n'.join(rows)+'\n')
    rows = [r'\begin{tabular}{clrrc}', r'\toprule',
            r'$r$ & $\mathcal I_r$ & $p(\mathcal I_r)$ & $w(\mathcal I_r)$ & $\lambda_r$ \\', r'\midrule']
    for r, (s, rho) in enumerate(blocks, 1):
        nodes = ','.join(str(i+1) for i in range(n) if s >> i & 1)
        rows.append(f'{r} & $\\{{{nodes}\\}}$ & {total(s,p)} & {total(s,w)} & ${texfrac(rho)}$'+r' \\')
    rows += [r'\bottomrule', r'\end{tabular}']
    (OUT/'blocks_table.tex').write_text('\n'.join(rows)+'\n')
    rows = [r'\begin{tabular}{rcccccc}', r'\toprule',
            r'Pivot & Enter & Leave & $\bar c_q$ & $t^\star$ & $\rho$ before & $\rho$ after \\', r'\midrule']
    for row in trace:
        vals = [str(row['iteration']), varname(row['entering'],n,arcs), varname(row['leaving'],n,arcs),
                *[texfrac(row[k]) for k in ('reduced','step','rho_before','rho_after')]]
        rows.append(' & '.join('$'+v+'$' for v in vals)+r' \\')
    rows += [r'\bottomrule', r'\end{tabular}']
    (OUT/'trace_table.tex').write_text('\n'.join(rows)+'\n')
    coords = [(-3.6,2.4),(-1.2,2.4),(1.2,2.4),(3.6,2.4),(-2.4,0),(0,0),(2.4,0),(0,-2.4)]
    for name, pivot in [('graph',None),('forest_before',6),('forest_after',7)]:
        state = trace[pivot] if pivot is not None else None
        lines = [r'\begin{tikzpicture}[>=Stealth, every node/.style={font=\small}, scale=.9]']
        for i, (x,y) in enumerate(coords):
            fill = 'blue!12' if state is None or i in state['main'] else 'gray!10'
            border = ',double,double distance=1.2pt' if state and i in state['anchors'] else ''
            lines.append(rf'\node[circle,draw,fill={fill},minimum size=9mm{border}] (v{i}) at ({x},{y}) {{{i+1}}};')
            if state is None:
                position = 'above' if i < 4 or i == 5 else 'below'
                lines.append(rf'\node[font=\scriptsize,{position}=2mm of v{i}] {{$({p[i]},{w[i]})$}};')
        for e, (i,j) in enumerate(arcs):
            style = '->,thick' if state is None else ('->,very thick,blue!70!black' if e in state['forest'] else '->,dashed,gray!70')
            bend = ',bend right=15' if (i,j)==(7,5) else ''
            lines.append(rf'\draw[{style}{bend}] (v{i}) to (v{j});')
        lines.append(r'\end{tikzpicture}')
        (OUT/f'{name}.tex').write_text('\n'.join(lines)+'\n')


def main():
    example_path = ROOT/'tests/fixtures/paper_example8.json'
    example = json.loads(example_path.read_text())
    p, w = example['profit'], example['weight']
    arcs = [(i-1,j-1) for i,j in example['arcs']]
    counters = dict(checked_bases=0, checked_directions=0,
                    checked_multiplier_systems=0, checked_pivot_rows=0)
    blocks, traces = ratio_closure_blocks(p, w, arcs, counters)
    assert [(s,r) for s,r in blocks] == [(36,F(2)),(19,F(3,2)),(200,F(1))]
    assert exact_lp(p,w,arcs,F(4)) == 7
    assert max(total(s,p) for s in closures(8,arcs) if total(s,w) <= 4) == 5
    assert interpolated(p,w,blocks,F(4)) == 7
    trace = traces[0]
    assert len(trace) == 8 and trace[6]['entering'] == 10 and trace[6]['step'] == F(1,2)
    assert sum(t['step'] == 0 for t in trace) == 6
    last = trace[-1]
    terminal_nb = ((set(last['anchors']) | {8+e for e in last['forest']})
                   - {last['entering']}) | {last['leaving']}
    terminal = forest_state(p,w,arcs,terminal_nb)
    terminal_alpha = [-terminal[3][8+e] if e in terminal[5] else F(0) for e in range(9)]
    assert terminal_alpha == [0,2,0,3,0,1,0,0,1]
    x = [F(1,2),F(1,2),F(1),F(0),F(1,2),F(1),F(0),F(0)]
    lam, mu = F(3,2), [F(0)]*8
    mu[5] = F(1)
    alpha = [F(1,2),F(5,2),0,F(5,2),0,F(2),0,0,F(3,2)]
    residual = [w[i]*lam+mu[i]-p[i] for i in range(8)]
    for e,(i,j) in enumerate(arcs):
        residual[i] += alpha[e]; residual[j] -= alpha[e]
        assert alpha[e]*(x[j]-x[i]) == 0
    assert min(residual) >= 0
    assert all(x[i]*residual[i] == 0 and mu[i]*(1-x[i]) == 0 for i in range(8))
    assert sum(wi*xi for wi,xi in zip(w,x)) == 4
    assert sum(pi*xi for pi,xi in zip(p,x)) == 4*lam+sum(mu) == 7
    fixtures = [([1,1],[1,1],[]), ([-3,-1],[1,2],[(0,1)]),
                ([0,0],[1,2],[]), ([3],[2],[])]
    rng = random.Random(20260905)
    for _ in range(32):
        n = rng.randint(2,6)
        order = list(range(n)); rng.shuffle(order)
        aa = [(order[i],order[j]) for i in range(n) for j in range(i+1,n) if rng.random()<.4]
        fixtures.append(([rng.randint(-5,8) for _ in range(n)],
                         [rng.randint(1,5) for _ in range(n)], aa))
    for pp,ww,aa in fixtures:
        bb,_ = ratio_closure_blocks(pp,ww,aa,counters)
        for capacity in [F(0),F(sum(ww),3),F(sum(ww)),F(sum(ww)+1)]:
            assert interpolated(pp,ww,bb,capacity) == exact_lp(pp,ww,aa,capacity)
    emit_tex(example,arcs,blocks,trace)
    result = dict(status='passed', seed=20260905, instances=len(fixtures)+1,
                  **counters, example_closures=len(closures(8,arcs)),
                  example_lp='7', example_pivots=len(trace), example_degenerate_pivots=6,
                  fixture_sha256=hashlib.sha256(example_path.read_bytes()).hexdigest(),
                  verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  trace=trace)
    (OUT/'verification.json').write_text(json.dumps(result,default=str,indent=2)+'\n')
    (OUT/'verification_stats.tex').write_text(
        '\n'.join('\\newcommand{\\'+name+'}{'+str(result[key])+'}' for name,key in
                  [('VerifiedInstances','instances'),('VerifiedBases','checked_bases'),
                   ('VerifiedDirections','checked_directions'),
                   ('VerifiedMultipliers','checked_multiplier_systems'),
                   ('VerifiedPivotRows','checked_pivot_rows')])+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='trace'},indent=2))


if __name__ == '__main__':
    main()
