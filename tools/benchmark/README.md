# Esecuzione delle campagne

- `run.py`: esegue una suite. Identifica ogni run da istanza, task, capacità,
  configurazione risolta, build e replica; non ricalcola e non sovrascrive un run
  già presente; riprende una campagna interrotta dallo stato salvato; ricontrolla
  ogni risultato con una chiamata `pclp verify` separata. `--cpu` vincola il
  solver a un core, `--dry-run` mostra quanto resta da eseguire.
- `split.py`: scrive i manifesti congelati di training, validation e test,
  stratificati per origine, famiglia e decade di taglia, tenendo tutte le
  repliche di una stessa base generata dallo stesso lato.
