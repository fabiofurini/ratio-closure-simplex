# Stato dell'implementazione rispetto al piano

Aggiornamento del 6 settembre 2026. Questo documento distingue il solver
implementato dalle proposte di tuning e dagli esperimenti del paper.

| Fase/requisito | Implementazione ed evidenza |
|---|---|
| F2: build e contratti | C++20/CMake, preset debug/release/sanitize/profile, JSON versione 1, configurazione file/CLI, stati e output esclusivo |
| F2: grafi generici | CSR, SCC iterative, condensazione con mappa inversa, duplicati/autoarchi, coefficienti firmati e pesi positivi |
| F2: oracoli | Enumerazione Fraction e modello HiGHS indipendente nella suite Python; pivot C++ contro sistemi di base Fraction |
| F3: ratio-closure simplex | Base ammissibile, foresta/radici, pricing, direzioni orientate, ratio test completo, Bland e diagnostica di ogni pivot |
| F3: soluzione completa | ratio, full-path, positive-path, solve, verify; parità, coda negativa, capacità nulle/abbondanti, molte capacità |
| F3: certificazione | Duale ratio, certificato compatto del cammino, duale LP completo lambda/mu/alpha, espansione alle unità e agli archi originali |
| F3: test | 308 istanze esatte, matrice di configurazioni, quattro tipi di pivot, metamorfici, parsing/limiti, 30.000 vertici, ASan/UBSan |
| F4: warm start sul residuo | `warm_start=residual`: ogni oracolo della decomposizione riparte dalla base finale del precedente; albero positivo scelto fra quelli chiusi nel residuo, ricaduta a freddo altrimenti. Pivot ridotti fino a 81x, decomposizione identica, in rotazione nella suite esatta (D20) |
| F4: aggiornamenti | full/local/adaptive integrati nel solver, confronto diagnostico locale/completo, nessuna allocazione nel ciclo senza trace |
| F4: pricing | full/partial/candidate-list, first/best-improving, fallback permanente a Bland in degenerazione |
| F4: canonicalizzazione | sequential come riferimento; dual per massimo supporto, evitando oracoli ripetuti per parità |
| F4: molte capacità | Cammino calcolato una volta; query del valore O(log k), vettore completo e sua verifica O(n+m) |
| F4: misure | Contatori e tempi per fase, fingerprint/configurazione, pilot appaiato con risultati salvati e verificati |

Il solver e le varianti elencate sono implementati; la vecchia DynamicForest
isolata è ora parte effettiva del motore. F3 non dipende più dal solo esempio
didattico. Le caselle del piano sono aggiornate selettivamente per i requisiti
che hanno evidenza concreta.

Restano fuori da questo completamento del nucleo: importazione sistematica
dei dataset storici, backend Dinkelbach/min-cut/parametrici, warm start tra
residui, riduzione transitiva opzionale, tuning con split e campagna finale,
report e articolo. Le alternative avanzate del piano (ad esempio link-cut
tree e aggiornamenti sui soli cammini) restano proposte da valutare con misure.
Non sono esposte come flag fittizi.

## Evidenze salvate

- build/cpp/acceptance.json: accettazione Debug.
- build/cpp-release/acceptance.json: accettazione Release con HiGHS se abilitato.
- build/cpp-sanitize/acceptance.json: accettazione ASan/UBSan.
- build/implementation_pilot/summary.json: 48 run su tre famiglie, configurazioni,
  fingerprint di build e risultati grezzi verificati.

Nel pilot iniziale, su 800 vertici disconnessi, il tempo mediano del percorso
passa da circa 1,06 s (full/sequential) a 0,40 s (local/sequential) e 0,0038 s
(local/dual). I pivot delle prime due varianti sono identici. Su un DAG a
livelli da 250 vertici, full/sequential e local/sequential misurano circa
0,067 s e 0,047 s. Queste sono misure di implementazione, non una dimostrazione
di superiorità generale né la campagna finale prevista dal piano.

## Limiti espliciti

Long double con controlli numerici, non un solver razionale. Non si rivendica
una complessità polinomiale nel numero di pivot. Le tolleranze non sono
parametri da allentare per ottenere tempi migliori. La struttura locale
ricostruisce le componenti coinvolte, non soltanto i cammini modificati.
La base viene reinizializzata sul residuo, mentre il grafo e il workspace
restano condivisi. Nessuna misura corrente sceglie definitivamente il default
per il paper.

## Aggiornamento del 6 settembre 2026

Aggiunti al nucleo, ciascuno come opzione separata e misurabile:

- backend `dinkelbach` (Newton su max closure con taglio minimo) e `parametric`
  (decomposizione divide et impera sull'intervallo dei rapporti), entrambi con
  certificati propri verificati dagli stessi verificatori del ratio-closure simplex;
- `initial_basis` con tre strategie, fra cui `full` che riproduce la base del
  prototipo storico;
- `ratio_test` con scansione ristretta e arresto anticipato sui passi nulli;
- fallback anti-ciclo temporaneo, rilasciato dal primo pivot a passo positivo;
- `transitive_reduction` esatta entro budget di memoria e `node_order` per la
  sensibilita all'ordine della condensazione;
- limite di tempo applicato anche dai backend di flusso.

Effetti misurati sulle istanze applicative, a parita di risultato certificato:
`minelib_newman1` da 7,07 a 0,87 secondi, `pckp_L` da 0,234 a 0,011,
un DAG sparso da 2000 vertici da 59,2 a 1,45. Su un oracolo di `newman1` gli archi
esaminati dal ratio test passano da 1110883 a 184.

Restano fuori: warm start sul residuo, strutture dinamiche avanzate, pricing
incrementale, e l'adozione di un codice di flusso allo stato dell'arte come
termine di confronto.

## Aggiornamento notturno del 6 settembre 2026

Aggiunto il **ratio-closure simplex duale** (`--simplex dual`), oltre il perimetro
del piano, motivato dalla misura sulla degenerazione. Base iniziale ammissibile
duale in O(n), scelta della riga uscente puramente combinatoria, riga di pivot in
O(n + profondità), completamento primale se l'ammissibilità duale viene persa.
Quattro regole di uscita selezionabili con `--dual-leaving`.

Verificato: stessi blocchi del primale sull'intera suite esaustiva e su 1500
istanze casuali con diagnostica a ogni pivot; suite di accettazione passata con
il duale nella rotazione delle configurazioni.

Misurato: degenerazione dal 99 per cento a 0-21, tempo 1,1-2,7 volte migliore.
Le regole di uscita strutturali non aiutano. Numeri completi in
`STATO_NOTTURNO.md` e nel report.

