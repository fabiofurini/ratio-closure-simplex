# Documentazione operativa

| Documento | Contenuto |
|---|---|
| [mathematical_contract.md](mathematical_contract.md) | Famiglia di LP, ipotesi, oracolo, decomposizione canonica, certificati, stati di uscita e frontiere non supportate |
| [notation.md](notation.md) | Dizionario dei simboli fra testo, LaTeX condiviso e nomi del codice |
| [algorithm_invariants.md](algorithm_invariants.md) | Invarianti mantenuti e punto in cui ciascuno viene controllato |
| [input_format.md](input_format.md) | Formato delle istanze, CLI e struttura dei risultati |
| [parameters.md](parameters.md) | Parametri realmente esposti, e quelli del piano deliberatamente non implementati |
| [ratio_closure_engine.md](ratio_closure_engine.md) | Strutture dati, costi per operazione, pricing, ratio test e base iniziale |
| [decisions.md](decisions.md) | Registro delle decisioni con la ragione e ciò che resta aperto |
| [claims.md](claims.md) | Matrice delle affermazioni e delle evidenze, con lo stato di ciascuna |
| [reproducibility.md](reproducibility.md) | Comandi per ricostruire ambiente, dati, campagne, tuning, analisi e report |
| [implementation_status.md](implementation_status.md) | Avanzamento rispetto alle fasi del piano, con le prove |

I documenti descrivono il codice esistente e le misure eseguite. Le proposte non
implementate restano in `piano/`, con la ragione in `decisions.md`.
