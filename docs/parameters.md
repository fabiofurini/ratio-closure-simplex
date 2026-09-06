# Parametri, valori e trattamento

Tabella dei parametri **realmente esposti** dal solver. La configurazione segue
`default < file --config < opzioni CLI`; la configurazione risolta completa,
non i soli override, viene salvata in ogni risultato insieme al suo SHA-256.
Le opzioni sconosciute o incompatibili sono rifiutate con `invalid_input`.

## 1. Selezione del problema

| Parametro | Valori | Note |
|---|---|---|
| task (posizionale) | `inspect`, `ratio`, `solve`, `positive-path`, `full-path`, `verify` | `verify` ricontrolla un risultato salvato |
| `--instance` | percorso | obbligatorio |
| `--capacity`, `--capacities` | numero, array JSON | solo con `solve`; in alternativa la capacità dell'istanza |
| `--output` | percorso | scrittura atomica, nessuna sovrascrittura |
| `--config` | percorso | oggetto JSON con le sole chiavi qui elencate |

## 2. Algoritmo

| Parametro | Valori | Trattamento |
|---|---|---|
| `algorithm` | `ratio-closure` (forma breve `closure-simplex`; `forest` accettato come nome storico), `dinkelbach`, `parametric` | il primo è l'oggetto dello studio, gli altri sono riferimenti. Il metodo si chiama **ratio-closure simplex** (D18) e `ratio-closure` è il valore canonico. `forest` resta accettato in lettura perché i config salvati dalle campagne del 6 settembre 2026 lo contengono |
| `pricing` | `full`, `partial`, `candidate-list` | tunabile; ogni forma parziale termina con una scansione globale prima di dichiarare ottimalità |
| `entering_rule` | `bland`, `first-improving`, `best-improving` | `bland` richiede `pricing=full` |
| `pricing_block_size` | intero > 0 (64, 256, 1024, 4096) | solo con `pricing=partial` |
| `candidate_limit` | intero > 0 (16, 64, 256) | solo con `pricing=candidate-list` |
| `basis_update` | `full`, `local`, `adaptive` | tunabile; nome storico `forest_update`, accettato in lettura |
| `warm_start` | `off`, `residual` | solo per la decomposizione canonica: `residual` riavvia ogni oracolo dalla base finale del precedente invece che dalla base vuota. Ricade sul riavvio a freddo quando nessun albero superstite e chiuso nel residuo |
| `rebuild_interval` | intero, `0` disattiva | ricostruzione completa periodica |
| `rebuild_fraction` | in `(0,1]` | solo con `basis_update=adaptive` |
| `canonicalization` | `sequential`, `dual` | `dual` estrae l'unione massimale per complementarità; `sequential` aggrega incrementi di pari rapporto |
| `degeneracy_trigger` | intero > 0 | pivot degeneri consecutivi prima del fallback a Bland; il fallback viene rilasciato dal primo pivot a passo positivo |
| `simplex` | `primal`, `dual` | `primal` e la versione di riferimento verificabile; `dual` parte da una base ammissibile duale e ripara le violazioni di precedenza. Se perde ammissibilita duale per arrotondamento, riparte dal primale e certifica con lo stesso codice |
| `ratio_test` | `full`, `restricted`, `early` | `full` scansiona ogni arco fuori foresta; `restricted` solo quelli che attraversano il sottoalbero entrante o la componente positiva; `early` aggiunge l'arresto al primo bloccante a passo nullo, sospeso quando Bland è attivo |
| `node_order` | `input`, `topological`, `seeded` | numerazione della condensazione; per sensibilità |
| `seed` | intero | ammesso solo con `node_order=seeded` |
| `transitive_reduction` | `off`, `on` | riduzione esatta con budget di memoria; sopra il budget non viene applicata anziché essere approssimata |
| `initial_basis` | `sink`, `closure`, `full` | `sink` avvia la componente positiva da un pozzo del residuo; `closure` dalla closure del seme di miglior rapporto; `full` dall'intera componente non orientata di miglior rapporto, che riproduce la base del prototipo storico. Misure in D11 |
| `initial_seeds` | intero > 0 | semi provati con `initial_basis=closure` |

## 3. Limiti e numerica

| Parametro | Valori | Trattamento |
|---|---|---|
| `time_limit` | secondi, `0` disattiva | orologio monotono; stato `time_limit` |
| `iteration_limit` | intero | stato `iteration_limit`, non implica ottimalità |
| `verify_every` | intero, `0` disattiva | controlli diagnostici interni; la verifica finale è sempre eseguita |
| `feasibility_abs_tol`, `feasibility_rel_tol` | reali >= 0 | tolleranze primali |
| `optimality_abs_tol`, `optimality_rel_tol` | reali >= 0 | tolleranze su costi ridotti e parità |
| `trace` | `off`, `pivots` | fuori dalle misure principali: la trace alloca |

Le tolleranze non fanno parte dello spazio di tuning delle prestazioni. Tutte le
configurazioni confrontate usano le stesse soglie di accettazione; allentarle per
ottenere tempi migliori invaliderebbe il confronto.

## 4. Parametri del piano non implementati

Sono elencati per non lasciarli ambigui. Nessuno di essi è esposto come flag
inerte: chiederli produce `invalid_input`.

| Parametro | Stato | Motivo |
|---|---|---|
| `warm_start=residual` | non implementato | la base trasferita al residuo è ammissibile solo se la componente positiva ereditata è chiusa nel residuo; dopo la rimozione del blocco questa proprietà non è garantita e la trasformazione non è stata dimostrata. Il piano ammette il parametro solo "se la trasformazione è verificata" |
| `memory_limit` | applicato dal runner | il solver riporta il picco RSS; il budget è imposto dall'orchestratore, non dal nucleo |
| `threads` | assente per scelta | il nucleo è seriale; il parallelismo è fra run della campagna |
| `algorithm=lp` | assente | HiGHS è usato come oracolo indipendente nella suite Python, non come backend del binario |
| strutture dinamiche avanzate (link-cut tree) | non implementate | il piano le ammette solo se il profilo mostra che sono il collo di bottiglia |

## 5. Statistiche riportate

Per ogni run: `pivots`, `degenerate_pivots`, `oracle_calls`, `full_rebuilds`,
`local_rebuilds`, `rebuilt_nodes`, `candidates_examined`, `ratio_arcs`,
`bland_fallbacks`, `flow_solves`, `flow_augmentations`, `flow_phases`,
`removed_arcs`, e i tempi separati di preprocessing, pricing, direzione, ratio
test, aggiornamenti, certificazione e totale. Il risultato riporta inoltre
`read_seconds`, `end_to_end_seconds`, `peak_rss_bytes` con il metodo di misura,
gli hash di istanza e configurazione e l'impronta della build.
