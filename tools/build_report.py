#!/usr/bin/env python3
"""Regenerates the report's artefacts and compiles it; output under build/report."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not shutil.which("latexmk") or not shutil.which("pdflatex"):
        raise SystemExit("Required: latexmk, pdflatex and BibTeX.")
    subprocess.run([sys.executable, str(ROOT / "tools/report/analyze.py")], check=True, cwd=ROOT)
    output = ROOT / "build/report"
    output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["BIBINPUTS"] = str(ROOT / "latex/common") + os.pathsep + environment.get("BIBINPUTS", "")
    # latexmk exits nonzero on mere warnings, so the build is judged by the TeX
    # log rather than by the exit code. It also stops one pass short when a label
    # first appears inside a deferred float: the reference is then resolvable
    # from the .aux but nothing tells latexmk to look again. So the build repeats
    # while the log still reports unresolved references, up to a fixed bound.
    def once(force=False):
        log = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode"]
                             + (["-g"] if force else [])
                             + [f"-auxdir={output}", "-outdir=.",
                              "-jobname=ratio_closure_simplex_report", "main.tex"],
                             cwd=ROOT / "report", env=environment, capture_output=True, text=True)
        (output / "build.log").write_text(log.stdout + log.stderr)
        record = (output / "ratio_closure_simplex_report.log").read_text(errors="ignore").splitlines()
        return record, [line for line in record if "undefined" in line and "Warning" in line]

    record, undefined = once()
    # latexmk considera tutto aggiornato appena il PDF e piu recente dei
    # sorgenti, anche quando le referenze non sono ancora risolte, e nemmeno
    # -g lo convince a rifare la passata. Le passate extra si fanno quindi
    # chiamando pdflatex direttamente: e deterministico e non dipende dal suo
    # tracciamento delle dipendenze.
    for _ in range(3):
        if not undefined:
            break
        subprocess.run(["pdflatex", "-interaction=nonstopmode",
                        f"-output-directory={output}",
                        "-jobname=ratio_closure_simplex_report", "main.tex"],
                       cwd=ROOT / "report", env=environment, capture_output=True, text=True)
        record = (output / "ratio_closure_simplex_report.log").read_text(errors="ignore").splitlines()
        undefined = [line for line in record if "undefined" in line and "Warning" in line]
    if not undefined:
        record, undefined = once(force=True)
    errors = [line for line in record if line.startswith("!")]
    overfull = [line for line in record if line.startswith("Overfull \\hbox")]
    pdf = ROOT / "report/ratio_closure_simplex_report.pdf"
    if errors or not pdf.exists():
        for line in errors[:5]:
            print(line)
        raise SystemExit(f"LaTeX errors; see {output / 'build.log'}")
    print(f"report written to {pdf}")
    print(f"  LaTeX errors {len(errors)}, overfull boxes {len(overfull)}, "
          f"undefined references {len(undefined)}")


if __name__ == "__main__":
    main()
