#!/usr/bin/env python3
"""Verify and build the tutorial; all output is isolated under build/tutorial."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not shutil.which('latexmk') or not shutil.which('pdflatex'):
        raise SystemExit('Required: latexmk, pdflatex, BibTeX and the packages listed in tutorial/README.md.')
    subprocess.run([sys.executable, str(ROOT/'tools/verify/verify_tutorial.py')], check=True, cwd=ROOT)
    output = ROOT/'build/tutorial'
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['BIBINPUTS'] = str(ROOT/'latex/common') + os.pathsep + env.get('BIBINPUTS', '')
    cmd = ['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error',
           '-file-line-error', '-jobname=ratio_closure_simplex_tutorial',
           '-auxdir='+str(output), '-outdir=.', 'main.tex']
    with (output/'build.log').open('w') as log:
        result = subprocess.run(cmd, cwd=ROOT/'tutorial', env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((output/'build.log').read_text()[-14000:], file=sys.stderr)
        raise SystemExit(result.returncode)
    tex_log = (output/'ratio_closure_simplex_tutorial.log').read_text()
    if ('There were undefined references' in tex_log or
            re.search(r'(?:LaTeX|Package natbib) Warning: (?:Reference|Citation)[^\n]*undefined', tex_log)):
        raise SystemExit('Unresolved LaTeX references or citations: inspect '+str(output/'build.log'))
    # A copy where a reader will actually look for it; build/ keeps the
    # authoritative output together with the compilation log.
    print('PDF:', ROOT/'tutorial/ratio_closure_simplex_tutorial.pdf')
    print('Build log:', output/'build.log')


if __name__ == '__main__':
    main()
