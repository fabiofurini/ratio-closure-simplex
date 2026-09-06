# Matrice delle affermazioni e delle evidenze

Tabella viva: una riga per ogni affermazione che il progetto potrebbe sostenere,
con l'evidenza che la giustifica e il suo stato. Serve a impedire che
un'affermazione entri in un testo prima della sua prova.

**Ambito attuale.** Il lavoro è fermo, per decisione esplicita, alla fine della
fase sperimentale e del report. La stesura dell'articolo non è iniziata.
L'audit di novità rispetto alla letteratura, invece, **è stato eseguito**: sta in
`literature/`, e il suo esito è restrittivo. Le righe di novità qui sotto
riportano quell'esito e non sono più `da verificare`.

**Misure rifatte.** Le campagne sono state rieseguite il 6 settembre 2026 sulla
libreria rigenerata in modo deterministico (`decisions.md` D16), su una macchina
altrimenti scarica: sette campagne, 2158 run, tutte complete. Le righe qui sotto
riportano quei numeri e non i precedenti; il report e stato riallineato nella
stessa passata.

Stati: `dimostrato` (prova matematica scritta), `verificato` (controllato dal
codice o dalle suite), `osservato` (misura sperimentale, dominio limitato),
`da verificare`, `non supportato`.

| Affermazione | Evidenza | Dove | Stato |
|---|---|---|---|
| Il solver tratta DAG generici, profitti di segno qualsiasi, pesi positivi, una capacità | derivazione orientata senza ipotesi bipartite; suite esatta su 308 istanze; famiglie multilivello e disconnesse | `docs/mathematical_contract.md`, `tests/solver_suite.py` | verificato |
| I digrafi ciclici sono trattati per condensazione equivalente | confronto istanza ciclica / condensata; espansione di soluzione e duali | `src/graph.cpp`, suite metamorfica | verificato |
| Ogni pivot coincide con un pivot ammissibile del simplesso | ricostruzione razionale esatta della base, direzione, costo ridotto, passo e variabile uscente per i pivot tracciati; quattro tipi di pivot coperti | `tests/solver_suite.py::algebra` | verificato |
| Gli invarianti della foresta valgono a ogni pivot | controlli `verify_every` su conteggi, radici, aggregati, normalizzazione e chiusura | `src/engine.cpp::check` | verificato |
| `local` e `adaptive` producono lo stesso stato matematico di `full` | confronto diagnostico con ricostruzione completa indipendente; uguaglianza dei blocchi su tutta la suite | `src/engine.cpp`, `tests/solver_suite.py` | verificato |
| Il metodo termina | regola di Bland sul sottoproblema normalizzato, fallback permanente in degenerazione | `src/engine.cpp` | da verificare (nessuna prova scritta nel progetto) |
| La sequenza prodotta è canonica | unione massimale per complementarità; confronto con l'oracolo esaustivo su tutte le istanze esatte | `Engine::support`, `exact_blocks` | verificato |
| La soluzione LP e il suo duale sono certificati | verifica primale-duale nelle unità originali su ogni run; `verify` indipendente su risultato salvato | `src/certificates.cpp`, runner | verificato |
| Tre backend indipendenti concordano | stessi blocchi e stessi valori LP per `forest`, `dinkelbach`, `parametric` sull'intera suite esatta; confronto con HiGHS su 60 istanze | `tests/solver_suite.py` | verificato |
| La memoria strutturale è lineare in n+m | analisi delle strutture, nessun tableau denso, nessuna allocazione nel ciclo dei pivot | `docs/ratio_closure_engine.md`, `tests/unit/engine.cpp` | verificato (analisi + misura di picco RSS) |
| Gli aggiornamenti locali riducono il costo per pivot | contatore `rebuilt_nodes` e tempi appaiati; ablation | campagne `main`, `ablation` | osservato |
| Il numero di pivot ha un limite polinomiale | — | — | non supportato |
| Il ratio-closure simplex è competitivo con Dinkelbach + min-cut | test congelato, 46 istanze | campagna `main` | **non supportato**: forest-tuned risolve 36/46 contro 40/46; sulle PCKP storiche entrambi risolvono tutto ma la mediana è 0,655 s contro 0,087 s |
| Il ratio-closure simplex è veloce dove riesce a terminare | mediana sui run risolti, per famiglia | campagna `main` | **non supportato**: mediana 0,142 s contro 0,057 s del parametrico, e calcolata sul sottoinsieme più piccolo che riesce a risolvere |
| Il simplesso duale migliora il primale | campagna dedicata sullo split di validation, 31 istanze in due repliche | campagna `dual` | **non supportato**: la degenerazione crolla dal 99,3% mediano allo 0,0%, ma il duale fa più pivot (7813 contro 3253 mediani), è più lento (speedup appaiato mediano 0,90) e risolve meno (56/62 contro 62/62), perdendo un DAG denso che il primale chiude in undici secondi |
| Le due leve sulla degenerazione valgono un fattore, non una percentuale | ablation a parità di tutto il resto, speedup appaiati | campagna `ablation` | osservato: la configurazione congelata è 2,83× più veloce di quella che forza Bland (fino a 18,8× su singole istanze); riportare la soglia al valore vecchio scende a 1,25× |
| La configurazione congelata è la migliore nello spazio cercato | ablation | campagna `ablation` | **non supportato**: due impostazioni scartate dalla ricerca sono più veloci di quella congelata, base iniziale `sink` 3,33× e riduzione transitiva attiva 3,46× contro 2,83× |
| Il ratio-closure simplex è competitivo con il backend parametrico | idem | campagna `main` | osservato e **sfavorevole**: il parametrico resta più veloce di un ordine di grandezza sulle istanze medie |
| Il fallback anti-ciclo permanente costava più di quanto proteggesse | ablation con soglia vicina e lontana, a parità di tutto il resto | campagna `ablation`, decisione D12 | osservato |
| La restrizione del ratio test è corretta | argomento sul supporto della direzione e chiusura della componente positiva; confronto con la versione esaustiva su tutte le istanze esatte | `docs/algorithm_invariants.md`, suite | dimostrato e verificato |
| Il tuning produce un default robusto | ricerca su training, scelta su validation, congelamento, test indipendente | `experiments/tuning`, `configs/frozen` | osservato |
| Il metodo conviene per molte capacità | campagna dedicata con punto di pareggio, costo del cammino e della ricostruzione inclusi | campagna `capacities` | osservato |
| La rappresentazione a foresta è nuova rispetto alla letteratura | audit eseguito | `literature/sections/06_simplex_forests.tex`, ritrattazione R4 | **non supportato**: l'algoritmo di Lerchs-Grossmann (1965) mantiene una foresta con aggregati per ramo e classifica un arco dal segno della massa che sostiene; ponendo `b_i = p_i - rho*w_i` quel test è il segno del nostro costo ridotto. La stessa struttura ricompare in Wuille (2025) sullo stesso LP normalizzato e in Yang (2026) su un LP diverso |
| Gli effetti merge/split dei pivot sono nuovi | audit eseguito | `literature/sections/07_positioning.tex`, R2 e R4 | **non supportato**: il *merger* di Lerchs-Grossmann aggiunge un arco e rimuove l'arco di radice del ramo; merge e split sono espliciti anche in Wuille (2025) e in Yang (2026) |
| Risolvere la versione di rapporto camminando su uno stato a foresta è nuovo | audit eseguito | `literature/sections/07_positioning.tex`, R7 | **non supportato**: Hochbaum (2001) dà una Lerchs-Grossmann parametrica con il costo di una singola esecuzione; Picard e Smith (2004) calcolano contorni massimizzando un rapporto benefit-cost con flusso parametrico |
| La specializzazione esatta del simplesso primale a questo LP è nuova | audit eseguito, con condizioni non ancora saldate | `literature/sections/07_positioning.tex` C1-C4, `08_open.tex` Q1-Q5 | da verificare: è l'unica affermazione di novità superstite, e resta subordinata al confronto formula per formula con Yang (2026) e alla separazione formale dal *normalized tree* di Lerchs-Grossmann |
| Il riuso sul residuo o la certificazione sono nuovi | audit eseguito | `literature/sections/06_simplex_forests.tex` | **non supportato** per la certificazione: Hochbaum (2001) ricava un flusso ammissibile dal *normalized tree* in tempo lineare, quindi la corrispondenza primale-duale fra stato a foresta e certificato di flusso è nota. Il riuso sul residuo non è stato misurato contro il warm start di pseudoflow (`08_open.tex` E3) |
| Il confronto con i metodi di flusso riflette lo stato dell'arte | il backend di flusso è un Dinic scritto per il progetto, non un codice affermato | `docs/decisions.md` D2 | non supportato |
