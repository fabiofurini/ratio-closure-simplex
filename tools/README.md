# Strumenti

| Directory | Contenuto |
|---|---|
| [import/](import/README.md) | Importazione validata delle istanze storiche PCKP e MineLib |
| [generate/](generate/README.md) | Generatore delle famiglie sintetiche del piano sperimentale |
| [benchmark/](benchmark/README.md) | Runner delle campagne, split congelati e baseline del prototipo 2023 |
| [tune/](tune/README.md) | Ricerca riproducibile dei parametri con storia e ripresa |
| [report/](report/README.md) | Analisi dei manifesti e generazione di tabelle e dati per le figure |
| [verify/](verify/README.md) | Verificatore esatto degli esempi e delle formule del tutorial |

Script di primo livello:

- `build_tutorial.py`: verifica esatta, figure, tabelle e PDF del draft didattico.
- `build_report.py`: rigenera gli artefatti e compila il report sperimentale,
  giudicando l'esito dal log TeX invece che dal codice di uscita di latexmk.
- `benchmark_solver.py`: misura rapida di una singola istanza, fuori campagna.
- `common.py`: istanze canoniche, hash, scrittura atomica e indici condivisi.

Tutti gli script si eseguono dalla radice del progetto e scrivono soltanto
dentro di essa.
