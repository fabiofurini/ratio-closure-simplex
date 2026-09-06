# Input, CLI e risultati

Formato JSON versione 1: `format_version` (facoltativo per compatibilità con
la fixture storica), `id`, `node_ids`, `profit`, `weight`, `arcs`,
`capacity` o `capacities` facoltative. Gli ID sono interi o stringhe univoche;
gli estremi degli archi sono ID, non posizioni. `[i,j]` significa che i richiede
j, cioè x_i <= x_j. Gli array profit/weight seguono l'ordine di node_ids.

Sono ammessi numeri JSON e stringhe decimali o razionali come `"1/3"`.
Il nucleo usa long double: le stringhe razionali non rendono esatta l'aritmetica
del solver. `numeric_type` può essere integer/rational/floating e documenta
l'origine. `source` e `metadata` sono metadati facoltativi.

Pesi strettamente positivi, capacità nonnegative, numeri finiti. Sono supportati
digrafi con cicli: SCC condensate, duplicati e autoarchi rimossi nel modello
interno. Soluzioni e moltiplicatori sono espansi sulle variabili e sugli archi
originali. Campi sconosciuti, vincoli aggiuntivi, versioni ignote e ID invalidi
sono rifiutati.

Dalla radice `ratio_closure_simplex`:

```bash
cmake --preset release
cmake --build --preset release --parallel 2
ctest --preset release
build/release/pclp solve --instance tests/fixtures/paper_example8.json --output build/example-result.json
build/release/pclp verify --instance tests/fixtures/paper_example8.json --result build/example-result.json
build/release/pclp solve --instance tests/fixtures/paper_example8.json --capacities '[0,2,4,10,100]'
```

Task: inspect, ratio, positive-path, full-path, solve, verify. Ratio restituisce
un supporto ottimo di base; i cammini restituiscono blocco canonici secondo
le tolleranze dichiarate. Full-path include rapporti nulli e negativi;
positive-path è sufficiente per tutte le capacità. La modalità solve costruisce
il cammino positivo completo: non dichiara arresto anticipato. La modalità
multicapacità costruisce il cammino una volta.

Nei risultati, support e macroitems[].nodes contengono **indici a base zero**
nell'array node_ids esportato. I vettori solution/mu/node_bound seguono questo
ordine; alpha segue l'elenco originale degli archi, duplicati compresi. Trace
usa gli indici del modello condensato e scalato esportato in trace_model.

Ogni risultato contiene formato, task, configurazione risolta e SHA-256,
SHA-256 del JSON di input ricodificato canonicamente da nlohmann/json,
fingerprint dei sorgenti della build, compilatore/flag, tempi, contatori e RSS.
Il fingerprint dell'input non è il checksum dei byte originali del file.

Precedenza configurazione: default < --config FILE < CLI. Esempio:
`--basis-update adaptive --pricing partial --entering-rule best-improving`.
Bland richiede pricing completo. Opzioni numeriche, limiti e nomi ammessi sono
definiti in Options; opzioni e backend non implementati sono rifiutati.
I file di configurazione eseguibili si trovano in configs/solver/.

Stati: optimal, iteration_limit, time_limit, numerical_failure, invalid_input,
memory_limit (allocazione fallita). Solo optimal ha un certificato finale.
Alla scadenza di un limite l'oracolo ratio può riportare il supporto ammissibile
corrente, ma non dichiara un bound ottimo. I limiti di pivot e tempo valgono per
l'intera costruzione del cammino, non vengono riavviati per ogni residuo.
Il budget di memoria può essere imposto dal runner/OS; non è simulato dal solver.

--output scrive tramite file temporaneo nella directory di destinazione e
pubblicazione esclusiva: non sovrascrive risultati esistenti. Un'interruzione
può lasciare un file .incomplete.PID, che non è un risultato valido. Nessuna
directory di destinazione viene scelta implicitamente. Uscita 0 per optimal/
valid, 1 per risultato non certificato, 2 per errore di input/I/O.

verify ricalcola ammissibilità, obiettivo, disuguaglianze duali, gap e
complementarità sulle unità originali; non richiama ratio-closure simplex.
Per i cammini verifica anche prefissi, partizione e certificati per blocco.
