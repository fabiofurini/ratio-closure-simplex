#!/usr/bin/env python3
"""Independent acceptance suite: enumeration, certificates, basis algebra, HiGHS.

Every generated failure persists its instance, arguments and result in --report's
directory. Tests make no assertions about elapsed time.
"""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260905

def near(a, b, tol=2e-8):
    assert math.isfinite(float(a)) and math.isfinite(float(b))
    assert abs(float(a)-float(b)) <= tol*max(1, abs(float(a)), abs(float(b))), (a,b)

def fixture(p,w,arcs):
    return dict(format_version=1,id="generated",node_ids=list(range(len(p))),profit=p,weight=w,arcs=arcs,capacity=sum(w)/3)

def closures(g):
    return [s for s in range(1<<len(g["profit"])) if all(not(s>>u&1) or s>>v&1 for u,v in g["arcs"])]

def total(g,s,key):
    return sum((F(str(v)) for i,v in enumerate(g[key]) if s>>i&1), F(0))

def exact_blocks(g):
    cs=closures(g);prefix=0;answer=[]
    while prefix != (1<<len(g["profit"]))-1:
        candidates=[s^prefix for s in cs if s&prefix==prefix and s!=prefix]
        rho=max(total(g,s,"profit")/total(g,s,"weight") for s in candidates)
        block=0
        for s in candidates:
            if total(g,s,"profit")/total(g,s,"weight")==rho:block|=s
        answer.append((block,rho));prefix|=block
    return answer

def exact_lp(g,c):
    c=F(str(c));points=[(total(g,s,"weight"),total(g,s,"profit")) for s in closures(g)]
    best=max(p for w,p in points if w<=c)
    for w,p in points:
        for v,q in points:
            if w<c<v:best=max(best,((v-c)*p+(c-w)*q)/(v-w))
    return best

def check_ratio(g,r):
    p=list(map(float,g["profit"]));w=list(map(float,g["weight"]))
    chosen=set(r["support"]);assert chosen and len(chosen)==len(r["support"])
    assert all(u not in chosen or v in chosen for u,v in g["arcs"])
    near(sum(p[i] for i in chosen)/sum(w[i] for i in chosen),r["ratio"])
    alpha=r["certificate"]["alpha"];assert len(alpha)==len(g["arcs"])
    lhs=[r["ratio"]*wi for wi in w]
    for (u,v),a in zip(g["arcs"],alpha):
        assert math.isfinite(a) and a>=-1e-9
        lhs[u]+=a;lhs[v]-=a
    for left,right in zip(lhs,p):assert left>=right-1e-8*max(1,abs(left),abs(right)),(left,right)

def check_solve(g,r):
    p=list(map(float,g["profit"]));w=list(map(float,g["weight"]));x=r["solution"]
    assert len(x)==len(p) and all(math.isfinite(v) and -1e-10<=v<=1+1e-10 for v in x)
    assert all(x[u]<=x[v]+1e-10 for u,v in g["arcs"])
    used=sum(a*b for a,b in zip(w,x));obj=sum(a*b for a,b in zip(p,x))
    assert used<=r["capacity"]+1e-8*max(1,r["capacity"]);near(used,r["used_weight"]);near(obj,r["objective"])
    lam=r["lambda"];mu=r["mu"];alpha=r["alpha"]
    assert math.isfinite(lam) and lam>=0 and len(mu)==len(p) and len(alpha)==len(g["arcs"])
    assert all(math.isfinite(a) and a>=-1e-9 for a in mu+alpha)
    lhs=[wi*lam+a for wi,a in zip(w,mu)]
    for (u,v),a in zip(g["arcs"],alpha):lhs[u]+=a;lhs[v]-=a
    for left,right in zip(lhs,p):assert left>=right-1e-8*max(1,abs(left),abs(right))
    near(lam*r["capacity"]+sum(mu),obj)

class Runner:
    def __init__(self,program,report):
        self.program=str(Path(program).resolve());self.report=Path(report);self.calls=0
    def run(self,g,task="solve",flags=(),expect="optimal"):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"instance.json";path.write_text(json.dumps(g))
            cmd=[self.program,task,"--instance",str(path),*map(str,flags)]
            completed=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        self.calls+=1
        try:
            result=json.loads(completed.stdout)
            assert result["status"]==expect,(completed.returncode,result,completed.stderr)
            if expect=="optimal":assert completed.returncode==0
            canonical=json.dumps(g,sort_keys=True,separators=(",",":"),ensure_ascii=False)
            if g["id"]=="generated" and expect!="invalid_input":assert result["instance_sha256"]==hashlib.sha256(canonical.encode()).hexdigest()
            return result
        except Exception:
            self.report.parent.mkdir(parents=True,exist_ok=True)
            (self.report.parent/"failure.json").write_text(json.dumps(dict(seed=SEED,instance=g,task=task,flags=list(flags),stdout=completed.stdout,stderr=completed.stderr),indent=2))
            raise

def algebra(r):
    spec=importlib.util.spec_from_file_location("tutorial_verifier",ROOT/"tools/verify/verify_tutorial.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    model=r["trace_model"];n=len(model["profit"]);arcs=model["arcs"]
    counts=0;types=set()
    for t in r["trace"]:
        active=t["active"];active_set=set(active);es=[e for e,(u,v) in enumerate(arcs) if u in active_set and v in active_set]
        variables=active+[n+e for e in es];nb=set(t["nonbasic"]);basic=[q for q in variables if q not in nb]
        rows=[[F(str(model["weight"][i])) if i<n else F(0) for i in variables]]
        for e in es:
            u,v=arcs[e];rows.append([F(int(q==u)-int(q==v) if q<n else int(q==n+e)) for q in variables])
        inv={q:k for k,q in enumerate(variables)}
        B=[[row[inv[q]] for q in basic] for row in rows]
        values=module.solve(B,[1]+[0]*len(es))
        direction=module.solve(B,[-row[inv[t["entering"]]] for row in rows])
        costs=[F(str(model["profit"][q])) if q<n else F(0) for q in basic]
        pi=module.solve(list(map(list,zip(*B))),costs)
        rc=(F(str(model["profit"][t["entering"]])) if t["entering"]<n else F(0))-sum(row[inv[t["entering"]]]*v for row,v in zip(rows,pi))
        for q,v,d in zip(basic,values,direction):near(v,t["values"][q]);near(d,t["direction"][q])
        near(rc,t["reduced"]);assert rc>0
        ratios=[(v/-d,q) for q,v,d in zip(basic,values,direction) if d<0]
        step=min(v for v,q in ratios);near(step,t["step"])
        assert any(q==t["leaving"] and abs(float(v-step))<1e-8 for v,q in ratios)
        pivot_row=module.solve(list(map(list,zip(*B))),[int(q==t["leaving"]) for q in basic])
        coefficient=sum(v*row[inv[t["entering"]]] for v,row in zip(pivot_row,rows))
        near(coefficient,-t["direction"][t["leaving"]])
        types.add(("node" if t["entering"]<n else "slack","node" if t["leaving"]<n else "slack"));counts+=1
    return counts,types

def main():
    parser=argparse.ArgumentParser();parser.add_argument("program");parser.add_argument("--report",required=True);parser.add_argument("--highs",action="store_true")
    args=parser.parse_args();runner=Runner(args.program,args.report);rng=random.Random(SEED)
    primal_configurations=[
        ["--basis-update","full","--canonicalization","sequential","--verify-every","1"],
        ["--basis-update","local","--verify-every","1"],
        ["--basis-update","adaptive","--entering-rule","best-improving","--verify-every","1"],
        ["--basis-update","local","--pricing","partial","--entering-rule","first-improving","--pricing-block-size","2","--verify-every","1"],
        ["--basis-update","local","--pricing","candidate-list","--entering-rule","best-improving","--candidate-limit","2","--degeneracy-trigger","1","--verify-every","1"],
    ]
    # The exact basis-algebra check reconstructs a primal pivot, so the traced
    # instances cycle the primal configurations only; the dual joins the
    # rotation on the untraced ones and is compared against the same oracle.
    # Il riavvio a caldo sul residuo riusa la base finale dell'oracolo
    # precedente: entra nella rotazione con la verifica degli invarianti a ogni
    # pivot, cosi un albero positivo non chiuso verrebbe intercettato subito.
    configurations=primal_configurations+[["--simplex","dual","--verify-every","1"],
                                          ["--simplex","dual","--dual-leaving","largest-tree"],
                                          ["--warm-start","residual","--verify-every","1"],
                                          ["--warm-start","residual","--basis-update","full",
                                           "--canonicalization","sequential","--verify-every","1"]]
    cases=[fixture([3],[2],[]),fixture([-3],[2],[]),fixture([1,1],[1,1],[]),fixture([0,0],[1,2],[]),
           fixture([5,-6],[1,1],[[0,1]]),fixture([4,-1,7,-3],[1,2,1,1],[[0,1],[0,2],[1,3],[2,3]]),
           fixture([5,-3,2],[1,2,1],[[0,1],[1,0],[2,1],[1,1],[0,1]]),fixture([1,2],[1,1],[])]
    for _ in range(300):
        n=rng.randint(2,8);order=list(range(n));rng.shuffle(order)
        arcs=[[order[i],order[j]] for i in range(n) for j in range(i+1,n) if rng.random()<.3]
        if rng.random()<.25:arcs.extend([[order[0],order[-1]],[order[-1],order[0]]])
        cases.append(fixture([rng.randint(-8,12) for _ in range(n)],[rng.randint(1,9) for _ in range(n)],arcs))
    pivot_count=0;pivot_types=set();backend_calls={"dinkelbach":0,"parametric":0}
    for index,g in enumerate(cases):
        expected=exact_blocks(g);capacities=[0,sum(g["weight"])/3,sum(g["weight"]),sum(g["weight"])+1]
        expected_values=[exact_lp(g,c) for c in capacities]
        traced=index<45
        flags=(primal_configurations[index%len(primal_configurations)] if traced
               else configurations[index%len(configurations)])
        ratio=runner.run(g,"ratio",flags+(["--trace","pivots"] if traced else []))
        near(ratio["ratio"],expected[0][1]);check_ratio(g,ratio)
        if traced:
            count,types=algebra(ratio);pivot_count+=count;pivot_types|=types
        path=runner.run(g,"full-path",flags)
        assert len(path["macroitems"])==len(expected),(g,path,expected)
        for block,(mask,rho) in zip(path["macroitems"],expected):
            assert sum(1<<i for i in block["nodes"])==mask,(g,path,expected);near(block["ratio"],rho)
        solved=runner.run(g,"solve",flags+["--capacities",json.dumps(capacities)])
        for r,v in zip(solved["solutions"],expected_values):check_solve(g,r);near(r["objective"],v)
        if index<30:
            for alternative in configurations:
                p=runner.run(g,"full-path",alternative)
                assert [set(b["nodes"]) for b in p["macroitems"]]==[set(b["nodes"]) for b in path["macroitems"]]
        # Independent backends must reproduce the same canonical sequence and LP
        # values through their own certificates, not through the ratio-closure code.
        if index<80:
            for backend in ("dinkelbach","parametric"):
                p=runner.run(g,"full-path",["--algorithm",backend])
                assert [set(b["nodes"]) for b in p["macroitems"]]==[set(b["nodes"]) for b in path["macroitems"]],(g,backend,p)
                for block,(mask,rho) in zip(p["macroitems"],expected):near(block["ratio"],rho)
                r=runner.run(g,"ratio",["--algorithm",backend]);near(r["ratio"],expected[0][1]);check_ratio(g,r)
                s=runner.run(g,"solve",["--algorithm",backend,"--capacities",json.dumps(capacities)])
                for entry,v in zip(s["solutions"],expected_values):check_solve(g,entry);near(entry["objective"],v)
                backend_calls[backend]+=1
        # Optional preprocessing must not change the canonical decomposition.
        for extra in (["--transitive-reduction","on"],["--node-order","topological"],
                      ["--node-order","seeded","--seed","17"],["--initial-basis","closure"],
                      ["--initial-basis","closure","--initial-seeds","1"],
                      ["--simplex","dual"],["--simplex","dual","--verify-every","1"],
                      ["--simplex","dual","--dual-leaving","largest-tree"],
                      ["--simplex","dual","--ratio-test","full"]):
            p=runner.run(g,"full-path",extra)
            assert [set(b["nodes"]) for b in p["macroitems"]]==[set(b["nodes"]) for b in path["macroitems"]],(g,extra,p)
    # Metamorphic tests preserve node identities while changing storage/arc order.
    for g in cases[7:27]:
        base=runner.run(g);n=len(g["profit"]);order=list(range(n));rng.shuffle(order)
        ids=g["node_ids"];permuted={**g,"node_ids":[ids[i] for i in order],"profit":[g["profit"][i] for i in order],"weight":[g["weight"][i] for i in order],"arcs":list(reversed(g["arcs"]))}
        near(runner.run(permuted)["objective"],base["objective"])
        duplicate={**g,"arcs":g["arcs"]+g["arcs"]+[[0,0]]}
        near(runner.run(duplicate)["objective"],base["objective"])
        for scale in (1e-12,1e12):
            transformed={**g,"weight":[str(F(str(w))*F(str(scale))) for w in g["weight"]],"capacity":str(F(str(g["capacity"]))*F(str(scale)))}
            near(runner.run(transformed)["objective"],base["objective"])
            transformed={**g,"profit":[p*scale for p in g["profit"]],"id":"scaled"}
            near(runner.run(transformed)["objective"]/scale,base["objective"])
        extra={**g,"node_ids":ids+[n],"profit":g["profit"]+[-100],"weight":g["weight"]+[1]}
        near(runner.run(extra)["objective"],base["objective"])
    # Input rejection, limits, scaling and exact/near ties.
    guide=json.loads((ROOT/"tests/fixtures/paper_example8.json").read_text());guide["id"]="guide"
    limited=runner.run(guide,"ratio",["--iteration-limit","0"],"iteration_limit");assert limited["pivots"]==0
    runner.run(guide,"ratio",["--time-limit","1e-30"],"time_limit")
    for bad in [dict(cases[0],weight=[0]),dict(cases[0],capacity=-1),dict(cases[0],format_version=99),dict(cases[0],extra_constraint=True),dict(cases[0],profit=["NaN"])]:
        runner.run(bad,expect="invalid_input")
    runner.run(guide,flags=["--pricing","partial"],expect="invalid_input")
    runner.run(guide,flags=["--algorithm","missing"],expect="invalid_input")
    runner.run(guide,flags=["--seed","3"],expect="invalid_input")
    runner.run(guide,flags=["--initial-seeds","0"],expect="invalid_input")
    runner.run(guide,flags=["--transitive-reduction","maybe"],expect="invalid_input")
    runner.run(guide,flags=["--simplex","primaldual"],expect="invalid_input")
    runner.run(guide,flags=["--dual-leaving","random"],expect="invalid_input")
    zero_regression=json.loads((ROOT/"tests/fixtures/scaled_zero_profit.json").read_text())
    near(runner.run(zero_regression,"ratio")["ratio"],0)
    near(runner.run(zero_regression)["objective"],0)
    redundant=fixture([3,-1,5],[1,2,1],[[0,1],[1,2]])
    before=runner.run(redundant)
    redundant["arcs"].append([0,2]);near(runner.run(redundant)["objective"],before["objective"])
    near_ties=fixture([1,1.00000001],[1,1],[])
    assert len(runner.run(near_ties,"full-path")["macroitems"])==2
    rational=fixture(["1/3","2/3"],[1,1],[])
    near(runner.run(rational,"ratio")["ratio"],2/3)
    strings={**cases[0],"node_ids":["node-A"]}
    near(runner.run(strings)["objective"],runner.run(cases[0])["objective"])
    # Saved certificate must pass, tampering and output overwrite must fail.
    with tempfile.TemporaryDirectory() as directory:
        inp=Path(directory)/"g.json";out=Path(directory)/"result.json";inp.write_text(json.dumps(guide))
        command=[runner.program,"solve","--instance",str(inp),"--output",str(out)]
        subprocess.run(command,check=True,capture_output=True)
        saved=out.read_bytes()
        assert subprocess.run(command,capture_output=True).returncode!=0 and out.read_bytes()==saved
        verify=[runner.program,"verify","--instance",str(inp),"--result",str(out)]
        subprocess.run(verify,check=True,capture_output=True)
        config=Path(directory)/"config.json";config.write_text(json.dumps({"basis_update":"full","verify_every":1}))
        override=subprocess.run([runner.program,"solve","--instance",str(inp),"--config",str(config),"--basis-update","local"],check=True,capture_output=True,text=True)
        assert json.loads(override.stdout)["configuration"]["basis_update"]=="local"
        broken=json.loads(saved);broken["solution"][0]=1;out.write_text(json.dumps(broken))
        assert subprocess.run(verify,capture_output=True).returncode!=0
        inp.write_text('{"id":');assert subprocess.run(command,capture_output=True).returncode!=0
    highs_cases=0
    if args.highs:
        import scipy
        import numpy as np
        from scipy.optimize import linprog
        from scipy.sparse import coo_matrix, vstack
        for _ in range(60):
            n=rng.randint(20,180);order=list(range(n));rng.shuffle(order)
            arcs=[[order[i],order[j]] for i in range(n) for j in range(i+1,n) if rng.random()<.025]
            if rng.random()<.3:arcs.extend([[0,1],[1,0]])
            g=fixture([rng.randint(-30,50) for _ in range(n)],[rng.randint(1,30) for _ in range(n)],arcs)
            row=[];col=[];data=[]
            for e,(u,v) in enumerate(arcs):row.extend([e,e]);col.extend([u,v]);data.extend([1,-1])
            A=coo_matrix((data,(row,col)),shape=(len(arcs),n)).tocsr()
            for conf in configurations[:3]+[["--algorithm","dinkelbach"],["--algorithm","parametric"]]:
                r=runner.run(g,flags=conf);check_solve(g,r)
                lp=linprog(-np.array(g["profit"],dtype=float),A_ub=vstack([np.array(g["weight"]),A]),b_ub=[g["capacity"]]+[0]*len(arcs),bounds=(0,1),method="highs")
                assert lp.success;near(-lp.fun,r["objective"])
            highs_cases+=1
    assert ("node","slack") in pivot_types and ("slack","node") in pivot_types and ("slack","slack") in pivot_types,pivot_types
    result=dict(status="passed",seed=SEED,exact_instances=len(cases),solver_calls=runner.calls,checked_cpp_pivots=pivot_count,pivot_types=sorted(pivot_types),cross_backend_instances=backend_calls,highs_instances=highs_cases)
    if args.highs:result["scipy_version"]=scipy.__version__
    path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
if __name__=="__main__":main()
