# Importazione delle istanze storiche

- `pckp_dat.py`: legge i file `.dat` delle istanze PCKP a capacità singola e, con
  `--cross-check`, rilegge il modello CPLEX `.lp` accanto. Rifiuta tutto ciò che
  non è una sola riga di capacità più righe di precedenza semplici con limiti
  unitari; le istanze multiperiodo non entrano. Poiché i due file non condividono
  sempre la numerazione delle variabili, il confronto ricade su un raffinamento
  dei colori e dichiara l'isomorfismo solo se ogni classe è un singoletto e gli
  archi coincidono.
- `minelib.py`: costruisce la derivazione a capacità unica delle istanze
  open-pit. La trasformazione (eliminazione di periodi e attualizzazione,
  risorsa 0 come riga di capacità, limite sommato sui periodi) è scritta dentro
  ogni istanza importata. Le istanze con blocchi privi di coefficiente di
  risorsa 0 sono rifiutate perché avrebbero peso nullo.

Le fonti originali non vengono modificate né copiate: si registrano percorso,
checksum ed esito della validazione.
