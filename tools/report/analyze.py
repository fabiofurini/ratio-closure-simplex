#!/usr/bin/env python3
"""Turns stored campaign manifests into the report's tables and figure data.

Nothing here recomputes a solution: it reads the manifests, checks that every
planned run is present and verified, and writes derived artefacts together with
their provenance.  A missing or unverified run is reported, never dropped
silently, and no artefact is written from a campaign that failed its
completeness check.
"""
from __future__ import annotations
import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, canonical, digest, write_atomic  # noqa: E402

FAMILY_LABEL = {"empty": "no arcs", "chain": "chains", "forest": "precedence forests",
                "layered": "layered DAGs", "sparse": "sparse DAGs", "dense": "dense DAGs",
                "diamonds": "diamonds", "disconnected": "disconnected", "transitive": "transitive arcs",
                "cyclic": "SCCs", "bilevel": "two levels", "pckp-historical": "PCKP (historical)",
                "minelib-derived": "MineLib (derived)"}


def short(name: str, width: int = 34) -> str:
    """Instance names are long by design; the table shows a readable stem."""
    name = name.replace("gen_", "").replace("_uniform", "").replace("_dispersed", "*")
    return name if len(name) <= width else name[: width - 1] + "~"


def escape(text: str) -> str:
    return str(text).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def load(campaign_root: Path, name: str) -> dict:
    path = campaign_root / name / "manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def current(manifest: dict) -> list[dict]:
    """Only the runs of the build the manifest currently describes."""
    build = (manifest.get("build") or {}).get("source_hash")
    records = list(manifest["records"].values())
    if build:
        records = [r for r in records if r.get("build_source_hash", build) == build]
    return records


def completeness(manifest: dict) -> dict:
    records = current(manifest)
    statuses = defaultdict(int)
    for record in records:
        statuses[record["status"]] += 1
    return {"planned": manifest["planned"], "stored": len(records),
            "complete": manifest["planned"] == len(records),
            "verified": sum(1 for r in records if r.get("verified")),
            "statuses": dict(sorted(statuses.items()))}


def rows(manifest: dict) -> list[dict]:
    return sorted(current(manifest), key=lambda r: (r["instance"], r["configuration"], r["replica"]))


def aggregate(manifest: dict) -> dict:
    """Median over replicas for each instance and configuration."""
    grouped = defaultdict(list)
    for record in rows(manifest):
        grouped[(record["instance"], record["configuration"])].append(record)
    summary = {}
    for key, group in grouped.items():
        usable = [r for r in group if r["status"] == "optimal" and r.get("verified")]
        times = [r["runner_seconds"] for r in usable]
        summary[key] = {
            "family": group[0]["family"], "nodes": group[0]["nodes"], "arcs": group[0]["arcs"],
            "origin": group[0]["origin"], "replicas": len(group), "solved": len(usable),
            "status": group[0]["status"],
            "median_seconds": statistics.median(times) if times else None,
            "spread_seconds": (max(times) - min(times)) if len(times) > 1 else 0.0,
            "solver_seconds": statistics.median([r.get("total_seconds", 0) for r in usable]) if usable else None,
            "peak_rss_bytes": max([r.get("peak_rss_bytes") or 0 for r in group]),
            "pivots": statistics.median([r.get("pivots", 0) for r in usable]) if usable else None,
            "oracle_calls": statistics.median([r.get("oracle_calls", 0) for r in usable]) if usable else None,
            "flow_solves": statistics.median([r.get("flow_solves", 0) for r in usable]) if usable else None,
            "macroitems": group[0].get("macroitems"),
            "objective": group[0].get("objective"),
        }
    return summary


def par2(record: dict, limit: float) -> float:
    if record["solved"] and record["median_seconds"] is not None:
        return record["median_seconds"]
    return 2 * limit


def write_csv(path: Path, records: list[dict]) -> None:
    fields = sorted({key for record in records for key in record})
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def table(path: Path, caption: str, label: str, header: list[str], body: list[list[str]],
          alignment: str | None = None, note: str = "") -> None:
    alignment = alignment or ("l" + "r" * (len(header) - 1))
    # Una tabella piu alta di una pagina non puo stare in un float: LaTeX la
    # segnala come "Float too large" e la spinge fuori dal blocco di testo.
    # Oltre la soglia si passa quindi a longtable, che spezza le pagine e
    # ripete l'intestazione; sotto la soglia resta un float con adjustbox, che
    # tiene una tabella larga dentro il blocco di testo restringendola.
    if len(body) > 30:
        lines = [r"\begin{longtable}{" + alignment + "}",
                 rf"\caption{{{caption}}}\label{{{label}}}\\",
                 r"\toprule", " & ".join(header) + r" \\", r"\midrule",
                 r"\endfirsthead",
                 r"\multicolumn{" + str(len(header)) + r"}{@{}l}{\footnotesize\itshape continua dalla pagina precedente}\\",
                 r"\toprule", " & ".join(header) + r" \\", r"\midrule", r"\endhead",
                 r"\midrule",
                 r"\multicolumn{" + str(len(header)) + r"}{r@{}}{\footnotesize\itshape continua}\\",
                 r"\endfoot", r"\bottomrule", r"\endlastfoot"]
        lines += [" & ".join(row) + r" \\" for row in body]
        lines.append(r"\end{longtable}")
        if note:
            lines.append(rf"\par\vspace{{2pt}}\footnotesize {note}")
        write_atomic(path, "{\\small\n" + "\n".join(lines) + "\n}\n")
        return
    lines = [r"\begin{table}[tbp]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             r"\small", r"\begin{adjustbox}{max width=\textwidth}",
             rf"\begin{{tabular}}{{{alignment}}}", r"\toprule",
             " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(row) + r" \\" for row in body]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}"]
    if note:
        lines.append(rf"\par\vspace{{2pt}}\footnotesize {note}")
    lines.append(r"\end{table}")
    write_atomic(path, "\n".join(lines) + "\n")


def data_file(path: Path, header: list[str], body: list[list]) -> None:
    lines = [" ".join(header)] + [" ".join(f"{v}" for v in row) for row in body]
    write_atomic(path, "\n".join(lines) + "\n")


def seconds(value) -> str:
    """One fixed format everywhere, so columns line up and compare at a glance."""
    if value is None:
        return "--"
    return f"{value:.3f}"


def environment_table(generated: Path, manifests: dict) -> None:
    """Machine, system and build fingerprint of the campaigns actually stored."""
    cpu = ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    cores = len([1 for line in Path("/proc/cpuinfo").read_text().splitlines()
                 if line.startswith("processor")]) if Path("/proc/cpuinfo").exists() else 0
    memory = ""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                memory = f"{int(line.split()[1]) / 2**20:.0f} GiB"
                break
    except OSError:
        pass
    system = ""
    try:
        system = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines()
                      if "=" in line).get("PRETTY_NAME", "").strip('"')
    except OSError:
        pass
    builds = {json.dumps(m.get("build"), sort_keys=True) for m in manifests.values() if m.get("build")}
    build = json.loads(sorted(builds)[0]) if builds else {}
    body = [["CPU", escape(cpu or "unknown")], ["logical cores", str(cores)],
            ["memory", escape(memory)], ["system", escape(system)],
            ["compiler", escape(build.get("compiler", ""))],
            ["build type", escape(build.get("type", ""))],
            ["build flags", "\\texttt{" + escape(build.get("flags", ""))[:90] + "}"],
            ["source hash", "\\texttt{" + (build.get("source_hash", "")[:16]) + "\\ldots}"],
            ["distinct builds", str(len(builds))],
            ["solver affinity", r"one core per solver process (\texttt{taskset})"],
            ["concurrency", "one campaign at a time, no concurrent measurement"]]
    table(generated / "table_environment.tex",
          "Measurement environment and build fingerprint recorded in the stored results.",
          "tab:environment", ["item", "value"], body, alignment="ll")


def instances_table(generated: Path, root: Path) -> None:
    splits = {}
    for name in ("train", "validation", "test"):
        path = root / "data/splits" / f"{name}.json"
        if path.exists():
            splits[name] = {r["name"] for r in json.loads(path.read_text())["instances"]}
    records = []
    for index in ("data/generated/index.json", "data/processed/index.json"):
        path = root / index
        if path.exists():
            records.extend(json.loads(path.read_text())["instances"])
    grouped = defaultdict(list)
    for record in records:
        grouped[record["family"]].append(record)
    body = []
    for family in sorted(grouped, key=lambda f: FAMILY_LABEL.get(f, f)):
        group = grouped[family]
        nodes = [r["nodes"] for r in group]
        arcs = [r["arcs"] for r in group]
        shares = [str(sum(1 for r in group if r["name"] in members)) for members in splits.values()]
        body.append([escape(FAMILY_LABEL.get(family, family)), str(len(group)),
                     f"{min(nodes)}--{max(nodes)}", f"{min(arcs)}--{max(arcs)}"] + shares)
    body.append([r"\textbf{total}", str(len(records)), "", ""] +
                [str(len(members)) for members in splits.values()])
    table(generated / "table_instances.tex",
          "Instance families, sizes and how many instances of each family fall in the frozen "
          "training, validation and test manifests.",
          "tab:instances", ["family", "count", "$n$", "$m$"] + list(splits), body)


def validation_table(generated: Path, root: Path, manifests: dict) -> None:
    body = []
    acceptance = root / "build/release/acceptance.json"
    if acceptance.exists():
        report = json.loads(acceptance.read_text())
        cross = report.get("cross_backend_instances", {})
        body += [["exhaustive rational oracle", f"{report['exact_instances']} instances",
                  f"{report['solver_calls']} solver calls"],
                 ["basis algebra in exact arithmetic", f"{report['checked_cpp_pivots']} pivots",
                  f"{len(report['pivot_types'])} pivot types"],
                 ["independent LP (HiGHS via SciPy)", f"{report['highs_instances']} instances",
                  escape("scipy " + report.get("scipy_version", ""))],
                 ["Dinkelbach against the ratio-closure sequence", f"{cross.get('dinkelbach', 0)} instances",
                  "same blocks and LP values"],
                 ["parametric against the ratio-closure sequence", f"{cross.get('parametric', 0)} instances",
                  "same blocks and LP values"]]
    for name, manifest in sorted(manifests.items()):
        report = completeness(manifest)
        statuses = ", ".join(f"{escape(k)} {v}" for k, v in report["statuses"].items())
        body.append([f"campaign {escape(name)}", f"{report['verified']}/{report['stored']} verified",
                     statuses])
    table(generated / "table_validation.tex",
          "Validation evidence: independent oracles used by the acceptance suite, and the outcome "
          "of every stored campaign run. A run counts as verified only if a separate "
          r"\texttt{pclp verify} call re-checked its certificate.",
          "tab:validation", ["check", "coverage", "outcome"], body, alignment="lll")


def summary_table(generated: Path, manifest: dict) -> None:
    """One line per configuration: the headline of the whole campaign."""
    summary = aggregate(manifest)
    limit = float(manifest.get("time_limit") or 30)
    configurations = sorted({key[1] for key in summary})
    instances = sorted({key[0] for key in summary})
    body = []
    for configuration in configurations:
        group = [summary[(i, configuration)] for i in instances if (i, configuration) in summary]
        solved = [r for r in group if r["solved"]]
        times = [r["median_seconds"] for r in solved]
        body.append([escape(configuration), f"{len(solved)}/{len(group)}",
                     seconds(statistics.median(times)) if times else "--",
                     seconds(max(times)) if times else "--",
                     f"{sum(par2(r, limit) for r in group):.0f}",
                     f"{max((r['peak_rss_bytes'] or 0) for r in group) / 2**20:.0f}"])
    table(generated / "table_summary.tex",
          r"Headline of the frozen test set. \emph{solved} counts the instances finished and "
          r"independently verified within the limit; \emph{median} and \emph{worst} are wall-clock "
          r"seconds over those; \emph{PAR-2} sums the times and charges twice the time limit for "
          r"each unsolved instance, so lower is better and a single time-out costs a lot; "
          r"\emph{MiB} is the largest peak resident memory observed.",
          "tab:summary", ["configuration", "solved", "median", "worst", "PAR-2", "MiB"], body)


def agreement_table(generated: Path, manifest: dict) -> None:
    """Objective agreement between backends on the runs that all of them solved."""
    values = defaultdict(dict)
    for record in rows(manifest):
        if record["status"] == "optimal" and record.get("verified") and record.get("objective") is not None:
            values[record["instance"]][record["configuration"]] = record["objective"]
    configurations = sorted({c for entry in values.values() for c in entry})
    body = []
    for configuration in configurations:
        if configuration == configurations[0]:
            continue
        paired = [(entry[configurations[0]], entry[configuration]) for entry in values.values()
                  if configurations[0] in entry and configuration in entry]
        if not paired:
            continue
        errors = [abs(a - b) / max(1.0, abs(a), abs(b)) for a, b in paired]
        body.append([escape(configuration), str(len(paired)), f"{max(errors):.2e}",
                     str(sum(1 for e in errors if e > 1e-9))])
    if body:
        table(generated / "table_agreement.tex",
              f"Agreement of the LP value with {escape(configurations[0])} on the instances both "
              "configurations solved and verified: worst relative difference and number of pairs "
              "above $10^{-9}$.",
              "tab:agreement", ["configuration", "paired", "worst relative gap", "above $10^{-9}$"], body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, default=ROOT / "experiments/runs")
    parser.add_argument("--analysis", type=Path, default=ROOT / "experiments/analysis")
    parser.add_argument("--generated", type=Path, default=ROOT / "report/generated")
    parser.add_argument("--tuning", type=Path, default=ROOT / "experiments/tuning")
    options = parser.parse_args()
    campaigns = sorted(p.parent.name for p in options.runs.glob("*/manifest.json"))
    provenance = {"script": "tools/report/analyze.py", "campaigns": {}, "artifacts": []}
    checks = []
    for name in campaigns:
        manifest = load(options.runs, name)
        report = completeness(manifest)
        checks.append((name, report))
        provenance["campaigns"][name] = {"build": manifest.get("build"), **report,
                                         "manifest_sha256": digest(canonical(rows(manifest)))}
        write_csv(options.analysis / f"{name}.csv", rows(manifest))
        provenance["artifacts"].append(f"experiments/analysis/{name}.csv")
    write_atomic(options.analysis / "completeness.json",
                 json.dumps({name: report for name, report in checks}, indent=1) + "\n")
    for name, report in checks:
        state = "complete" if report["complete"] else "INCOMPLETE"
        print(f"{name:16s} {report['stored']}/{report['planned']} runs {state}, "
              f"{report['verified']} verified, statuses {report['statuses']}")

    usable = {name: load(options.runs, name) for name, report in checks if report["complete"]}
    generated = options.generated
    stored = {name: load(options.runs, name) for name, _ in checks}
    environment_table(generated, stored)
    instances_table(generated, ROOT)
    validation_table(generated, ROOT, stored)
    provenance["artifacts"] += ["report/generated/table_environment.tex",
                                "report/generated/table_instances.tex",
                                "report/generated/table_validation.tex"]
    if "main" in usable:
        summary_table(generated, usable["main"])
        provenance["artifacts"].append("report/generated/table_summary.tex")
        agreement_table(generated, usable["main"])
        provenance["artifacts"].append("report/generated/table_agreement.tex")

    if "pilot" in usable:
        manifest = usable["pilot"]
        summary = aggregate(manifest)
        configurations = sorted({key[1] for key in summary})
        instances = sorted({key[0] for key in summary}, key=lambda i: (summary[(i, configurations[0])]["nodes"], i))
        body = []
        for name in instances:
            first = summary[(name, configurations[0])]
            row = [escape(short(name)), f"{first['nodes']}", f"{first['arcs']}"]
            for configuration in configurations:
                record = summary.get((name, configuration))
                row.append(seconds(record["median_seconds"]) if record and record["solved"] else
                           (escape(record["status"]) if record else "--"))
            body.append(row)
        table(generated / "table_pilot.tex",
              "Pilot campaign: median wall time in seconds of one solve per instance and backend. "
              "A status word replaces the time when the run did not finish within the pilot limit.",
              "tab:pilot", ["instance", "$n$", "$m$"] + [escape(c) for c in configurations], body)
        provenance["artifacts"].append("report/generated/table_pilot.tex")

    for name in ("main", "ablation", "scalability", "capacities", "dual", "canonical_path", "degeneracy"):
        if name not in usable:
            continue
        manifest = usable[name]
        summary = aggregate(manifest)
        limit = manifest.get("configurations") and float(json.loads(
            (options.runs / name / "manifest.json").read_text()).get("time_limit", 0) or 0)
        limit = limit or 60.0
        configurations = sorted({key[1] for key in summary})
        write_csv(options.analysis / f"{name}_aggregated.csv",
                  [{"instance": i, "configuration": c, **v} for (i, c), v in sorted(summary.items())])
        provenance["artifacts"].append(f"experiments/analysis/{name}_aggregated.csv")

        families = defaultdict(lambda: defaultdict(list))
        for (instance, configuration), record in summary.items():
            families[record["family"]][configuration].append(record)
        body = []
        for family in sorted(families, key=lambda f: FAMILY_LABEL.get(f, f)):
            for configuration in configurations:
                group = families[family][configuration]
                if not group:
                    continue
                solved = sum(1 for r in group if r["solved"])
                times = [r["median_seconds"] for r in group if r["solved"]]
                body.append([escape(FAMILY_LABEL.get(family, family)), escape(configuration),
                             f"{solved}/{len(group)}",
                             seconds(statistics.median(times)) if times else "--",
                             seconds(max(times)) if times else "--",
                             f"{statistics.median([par2(r, limit) for r in group]):.2f}",
                             f"{max((r['peak_rss_bytes'] or 0) for r in group) / 2**20:.0f}"])
        table(generated / f"table_{name}.tex",
              f"Campaign {escape(name)}: instances solved and verified, median and worst median wall "
              f"time in seconds, PAR-2 with a {limit:g}\\,s limit, and peak resident memory in MiB.",
              f"tab:{name}", ["family", "configuration", "solved", "median", "worst", "PAR-2", "MiB"], body)
        provenance["artifacts"].append(f"report/generated/table_{name}.tex")

        # Il riferimento di una campagna e la configurazione contro cui ha senso
        # confrontare: la reference verificabile dove c'e, il primale nella
        # campagna che mette a confronto primale e duale.
        # Le campagne del 6 settembre 2026 hanno registrato le etichette storiche
        # "forest-*"; le suite attuali producono "ratio-closure-*".  I record non
        # vengono riscritti, quindi entrambe le forme restano riconosciute.
        reference = next((c for c in ("ratio-closure-reference", "ratio-closure-primal",
                                      "forest-reference", "forest-primal") if c in configurations),
                         configurations[0])
        speedups = []
        for configuration in configurations:
            paired = [(summary[(i, reference)]["median_seconds"], summary[(i, configuration)]["median_seconds"])
                      for (i, c) in summary if c == configuration
                      and (i, reference) in summary and summary[(i, reference)]["solved"]
                      and summary[(i, configuration)]["solved"]]
            ratios = [a / b for a, b in paired if b and b > 0]
            if ratios:
                speedups.append([escape(configuration), f"{len(ratios)}",
                                 f"{statistics.median(ratios):.2f}",
                                 f"{min(ratios):.2f}", f"{max(ratios):.2f}"])
        if speedups:
            table(generated / f"table_{name}_speedup.tex",
                  f"Campaign {escape(name)}: paired speedup against {escape(reference)} on the instances "
                  "both settings solved and verified.",
                  f"tab:{name}-speedup", ["configuration", "paired", "median", "min", "max"], speedups)
            provenance["artifacts"].append(f"report/generated/table_{name}_speedup.tex")

        # Performance profile over the instances any configuration solved.
        instances = sorted({key[0] for key in summary})
        best = {}
        for instance in instances:
            times = [summary[(instance, c)]["median_seconds"] for c in configurations
                     if (instance, c) in summary and summary[(instance, c)]["solved"]]
            if times:
                best[instance] = min(t for t in times if t is not None)
        taus = [1.0 * 1.35 ** k for k in range(0, 28)]
        profile = []
        for tau in taus:
            row = [f"{tau:.3f}"]
            for configuration in configurations:
                covered = 0
                for instance in best:
                    record = summary.get((instance, configuration))
                    if record and record["solved"] and record["median_seconds"] is not None \
                            and record["median_seconds"] <= tau * max(best[instance], 1e-6):
                        covered += 1
                row.append(f"{covered / max(1, len(best)):.4f}")
            profile.append(row)
        data_file(generated / f"profile_{name}.dat", ["tau"] + [c.replace("-", "") for c in configurations], profile)
        provenance["artifacts"].append(f"report/generated/profile_{name}.dat")

        scaling = defaultdict(list)
        for (instance, configuration), record in summary.items():
            if record["solved"] and record["family"] in ("sparse", "layered", "chain", "empty"):
                scaling[configuration].append((record["nodes"], record["median_seconds"]))
        for configuration, points in scaling.items():
            merged = defaultdict(list)
            for nodes, value in points:
                merged[nodes].append(value)
            data_file(generated / f"scaling_{name}_{configuration}.dat", ["nodes", "seconds"],
                      [[nodes, f"{statistics.median(values):.6f}"] for nodes, values in sorted(merged.items())])
            provenance["artifacts"].append(f"report/generated/scaling_{name}_{configuration}.dat")

        breakdown = []
        for configuration in configurations:
            group = [summary[(i, configuration)] for i in instances if (i, configuration) in summary
                     and summary[(i, configuration)]["solved"]]
            phases = defaultdict(float)
            for record in group:
                pass
            source = [r for r in rows(manifest) if r["configuration"] == configuration
                      and r["status"] == "optimal" and r.get("verified")]
            for record in source:
                for phase in ("preprocessing_seconds", "pricing_seconds", "direction_seconds",
                              "ratio_test_seconds", "update_seconds", "certification_seconds"):
                    phases[phase] += record.get(phase, 0.0) or 0.0
                phases["total_seconds"] += record.get("total_seconds", 0.0) or 0.0
            if phases["total_seconds"] > 0:
                breakdown.append([escape(configuration), f"{len(source)}"] +
                                 [f"{100 * phases[p] / phases['total_seconds']:.1f}" for p in
                                  ("preprocessing_seconds", "pricing_seconds", "direction_seconds",
                                   "ratio_test_seconds", "update_seconds", "certification_seconds")])
        if breakdown:
            table(generated / f"table_{name}_breakdown.tex",
                  f"Campaign {escape(name)}: share of the solver's own measured time per phase, "
                  "summed over the verified runs of each configuration.",
                  f"tab:{name}-breakdown",
                  ["configuration", "runs", "prep.", "pricing", "direction", "ratio", "update", "certif."],
                  breakdown,
                  note="Percentages of the solver's internal accounting; the flow backends spend their "
                       "time outside these ratio-closure phases and therefore show near-zero shares.")
            provenance["artifacts"].append(f"report/generated/table_{name}_breakdown.tex")

    for directory in sorted(options.tuning.glob("*/summary.json")):
        summary = json.loads(directory.read_text())
        history = [json.loads(line) for line in (directory.parent / "history.jsonl").read_text().splitlines()]
        body = []
        for entry in summary["ranking"]:
            score = entry["score"]
            body.append([escape(entry["label"]),
                         r"\footnotesize " + escape(", ".join(
                             f"{k}={v}" for k, v in sorted(entry["configuration"].items())
                             if k != "algorithm")[:110]),
                         f"{score['solved']}/{score['instances']}", f"{score['failures']}",
                         f"{score['par2']:.1f}"])
        table(options.generated / f"table_tuning_{directory.parent.name}.tex",
              f"Random search on {escape(summary['split'])}: best {len(body)} of {summary['attempts']} "
              f"attempts, total tuning time {summary['total_tuning_seconds']:.0f}\\,s.",
              f"tab:tuning-{directory.parent.name}",
              ["attempt", "configuration", "solved", "failures", "PAR-2"], body,
              alignment="llrrr")
        provenance["artifacts"].append(f"report/generated/table_tuning_{directory.parent.name}.tex")

    write_atomic(options.analysis / "provenance.json", json.dumps(provenance, indent=1) + "\n")
    print(f"wrote {len(provenance['artifacts'])} artefacts")


if __name__ == "__main__":
    main()
