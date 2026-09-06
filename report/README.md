# Report sperimentale

`main.tex` con le sezioni in `sections/` e gli artefatti generati in
`generated/`. Notazione e bibliografia sono condivise con il tutorial in
`latex/common/`.

```bash
python3 tools/build_report.py
```

Il PDF sta qui, accanto ai sorgenti, in una sola copia:
`ratio_closure_simplex_report.pdf`. I file intermedi di LaTeX e il log di compilazione
restano in `build/report/`.

`generated/` è interamente rigenerato da `analyze.py`: non va modificato a mano.
