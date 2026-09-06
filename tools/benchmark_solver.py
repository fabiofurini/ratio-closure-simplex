#!/usr/bin/env python3
"""Paired implementation pilot; generated inputs and raw verified runs are retained."""
import argparse
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess

def main():
    parser=argparse.ArgumentParser();parser.add_argument("program");parser.add_argument("--output",required=True)
    args=parser.parse_args();program=str(Path(args.program).resolve());dest=Path(args.output)
    if dest.exists():raise SystemExit("Choose a new output directory; pilot runs are immutable.")
    dest.mkdir(parents=True);rng=random.Random(20260905)
    families=[]
    n=800
    families.append(("disconnected",dict(profit=[3 if i%2==0 else -1 for i in range(n)],weight=[1]*n,arcs=[[i,i+1] for i in range(0,n,2)])))
    families.append(("ties",dict(profit=[1]*n,weight=[1]*n,arcs=[])))
    n=250
    families.append(("layered",dict(profit=[rng.randint(-20,40) for _ in range(n)],weight=[rng.randint(1,15) for _ in range(n)],
        arcs=[[i,j] for i in range(n) for j in range(i) if rng.random()<.025])))
    configs={
        "full":["--basis-update","full","--canonicalization","sequential"],
        "local":["--basis-update","local","--canonicalization","sequential"],
        "dual":["--basis-update","local","--canonicalization","dual"],
        "candidate":["--basis-update","local","--canonicalization","dual","--pricing","candidate-list","--entering-rule","best-improving"],
    }
    rows=[]
    for family,g in families:
        g.update(format_version=1,id=family,node_ids=list(range(len(g["profit"]))),capacity=sum(g["weight"])/3)
        instance=dest/(family+".json");instance.write_text(json.dumps(g))
        jobs=[(name,rep) for name in configs for rep in range(4)];rng.shuffle(jobs)
        for name,rep in jobs:
            output=dest/(family+"-"+name+"-"+str(rep)+".json")
            subprocess.run([program,"solve","--instance",str(instance),"--output",str(output),*configs[name]],check=True,capture_output=True)
            subprocess.run([program,"verify","--instance",str(instance),"--result",str(output)],check=True,capture_output=True)
            r=json.loads(output.read_text())
            assert r["build"]["type"] in ("Release","RelWithDebInfo"),r["build"]
            rows.append(dict(family=family,configuration=name,replica=rep,warmup=rep==0,
                seconds=r["path"]["stats"]["total_seconds"],objective=r["objective"],stats=r["path"]["stats"],run=output.name,
                configuration_sha256=r["configuration_sha256"],source_sha256=r["build"]["source_sha256"]))
    summaries=[]
    for family,_ in families:
        for config in configs:
            runs=[r for r in rows if r["family"]==family and r["configuration"]==config and not r["warmup"]]
            summaries.append(dict(family=family,configuration=config,median_seconds=statistics.median(r["seconds"] for r in runs),
                rebuilt_nodes=runs[0]["stats"]["rebuilt_nodes"],pivots=runs[0]["stats"]["pivots"],oracle_calls=runs[0]["stats"]["oracle_calls"]))
    (dest/"summary.json").write_text(json.dumps(dict(seed=20260905,machine=platform.platform(),raw=rows,summary=summaries),indent=2)+"\n")
    (dest/"README.md").write_text("# Pilot di implementazione\n\nTre famiglie sintetiche, confronto appaiato full/local/dual/candidate. Tutti i risultati sono verificati con il comando verify. Replica 0 esclusa dalle mediane. Queste misure non costituiscono il test finale del paper. Dati grezzi e configurazioni risolte sono nei singoli JSON.\n")
    print(json.dumps(summaries,indent=2))
if __name__=="__main__":main()
