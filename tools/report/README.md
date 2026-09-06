# Analisi e artefatti del report

`analyze.py` legge i manifesti delle campagne, verifica che ogni run previsto sia
presente per la build corrente, e solo allora genera tabelle LaTeX e file dati
per pgfplots in `report/generated/`, insieme ai CSV per run e aggregati in
`experiments/analysis/`. Scrive `provenance.json` con build, conteggi, istogramma
degli stati e hash dei record di ogni campagna usata.

Il report non contiene numeri scritti a mano: ogni tabella e ogni figura
provengono da questi file.
