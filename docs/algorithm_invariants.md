# Invarianti e loro verifica

Elenco degli invarianti che il codice mantiene, con il punto in cui ciascuno
viene controllato. Un invariante senza controllo eseguibile è segnalato come
tale.

## 1. Base a foresta (`Engine::check`, attiva con `verify_every`)

| Invariante | Controllo |
|---|---|
| Gli archi della foresta esistono nel grafo condensato e non formano cicli non orientati | radicazione in `rebuild`, eccezione `cycle in forest basis` |
| Ogni albero ha al più una radice; esattamente una componente è senza radice | `two anchors in one forest tree`, conteggio `unanchored != 1` |
| Padre, arco padre, figli e radice sono mutuamente coerenti | `invalid parent edge` |
| Il numero di variabili non basiche è `n_attivi - 1`, senza ripetizioni | `invalid forest basis count` |
| Gli aggregati di sottoalbero coincidono con la somma diretta dei figli | `subtree aggregate mismatch` |
| I valori non basici sono nulli e i basici ammissibili entro tolleranza | `y` ricostruito e confrontato |
| La normalizzazione di peso `sum w_i y_i = 1` è rispettata | `close(weight,1)` |
| Il supporto primale è chiuso nel residuo | `primal forest support is not closed` |

## 2. Pivot (build diagnostiche, `verify_every=k`)

- La direzione sta nel nullo delle righe da mantenere: `sum w_i d_i = 0`.
- Il costo ridotto coincide con `sum p_i d_i`.
- La direzione vale `1` sulla variabile entrante e `0` sulle altre non basiche.
- Il passo è il massimo ammissibile e la variabile uscente è quella che blocca:
  il ratio test esamina tutte le variabili basiche che possono diventare
  negative, vertici senza radice e slack fuori foresta compresi.
- Dopo il pivot i valori ricostruiti coincidono con `y + step*d`, e il rapporto
  con `rho + step*costo_ridotto`.
- Una ricostruzione completa indipendente riproduce aggregati e rapporto della
  ricostruzione locale: `local` e `full` devono coincidere come stato
  matematico, non come ordine delle liste.
- Selezione deterministica in caso di parità (indice minimo) quando il ratio
  test è esaustivo. Con `bland` la regola è attiva dall'inizio; con le altre
  regole il fallback a Bland scatta dopo `degeneracy_trigger` pivot a passo zero
  consecutivi e viene rilasciato dal primo pivot a passo positivo.
- Con `ratio_test=early` la scansione si ferma al primo bloccante a passo nullo,
  che è il minimo possibile: il passo resta ottimo, ma la variabile uscente non
  è più necessariamente quella di indice minimo. Per questo la scorciatoia è
  sospesa quando Bland è attivo.
- Con `ratio_test=restricted` la scansione copre gli archi incidenti al
  sottoalbero entrante e gli archi uscenti dai vertici fuori dalla componente
  positiva. È completa perché la direzione è nulla su ogni arco con entrambi gli
  estremi fuori dai due insiemi, e perché la componente positiva è chiusa,
  quindi ogni arco che la attraversa ha la coda fuori.

La suite di accettazione ricostruisce, con aritmetica razionale esatta, la
matrice di base di ogni pivot tracciato e ricalcola valori, direzione, costo
ridotto, passo, variabile uscente e coefficiente di pivot. I quattro tipi di
pivot (vertice/arco entrante contro vertice/arco uscente) sono richiesti esplicitamente
dalla suite.

## 2bis. Fase duale

Durante la fase duale la base attraversa deliberatamente punti primalmente
inammissibili, quindi i controlli si dividono in due gruppi.

| Invariante | Vale durante il duale? |
|---|---|
| Conteggio delle non basiche, radici, radici, aggregati, normalizzazione | sì, verificati a ogni pivot con `verify_every` |
| Chiusura del supporto primale (`y_tail <= y_head`) | **no**: è esattamente ciò che il duale sta riparando, ed è la condizione di arresto |
| Costi ridotti non positivi (ammissibilità duale) | sì, ed è ciò che il test del rapporto duale preserva |

`check(feasible)` prende un parametro proprio per questo: la fase duale lo
chiama con `false`, e la verifica finale con `true`, quando `P` è chiusa.

L'unica inammissibilità primale possibile è uno slack di precedenza negativo,
cioè un arco che esce dalla componente positiva: le variabili di vertice valgono
`1/w(P)` oppure zero e non sono mai negative.

## 3. Oracolo di rapporto (`verify_ratio`)

- Il supporto è non vuoto, senza ripetizioni e chiuso rispetto agli **archi
  originali**.
- Il rapporto dichiarato è esattamente `p(supporto)/w(supporto)`.
- `beta` coincide con il rapporto.
- `alpha >= 0` e `w_i beta + div_i(alpha) >= p_i` per **ogni** vertice originale.

## 4. Percorso canonico (`verify_path`)

- Prefissi coerenti: `prefix_weight[0] = prefix_profit[0] = 0` e incrementi pari
  agli aggregati del blocco.
- Blocchi non vuoti, disgiunti, a rapporti strettamente decrescenti.
- `node_bound[i]` uguale al rapporto del blocco di `i`, con uguaglianza esatta
  della riga duale su ogni vertice di un blocco.
- Nessun arco va da un blocco precedente a uno successivo: `block[tail] >=
  block[head]`.
- Nessun moltiplicatore attraversa blocchi distinti.
- I vertici non assegnati esistono solo in un percorso positivo e hanno
  `node_bound <= 0`.

## 5. Soluzione LP (`verify_solution`)

`0 <= x <= 1`; `x_i <= x_j` su ogni arco originale; `sum w_i x_i <= c`;
`lambda, mu, alpha >= 0`; `w_i lambda + mu_i + div_i(alpha) >= p_i`;
complementarità su `mu`, su `alpha` e sulla riga di capacità; uguaglianza fra
obiettivo primale e bound duale. Tutte le disuguaglianze usano una soglia
assoluta più una relativa alla scala della riga.

## 6. Preprocessing

- La condensazione SCC preserva il valore ottimo: le suite confrontano istanza
  ciclica e istanza condensata equivalente.
- La riduzione transitiva rimuove solo archi implicati da un cammino: il duale
  degli archi rimossi vale zero e resta ammissibile, mentre la chiusura del
  supporto è comunque verificata sugli archi originali.
- L'ordine dei vertici (`input`, `topological`, `seeded`) non cambia la
  decomposizione canonica: la suite lo verifica su ogni istanza esatta.

## 7. Invarianti non verificati automaticamente

- La terminazione in un numero finito di pivot si appoggia alla regola di Bland
  sul sottoproblema normalizzato. Con il fallback temporaneo l'argomento è: un
  episodio sotto Bland avviene a soluzione di base fissa e non può ciclare, e
  ogni episodio termina con un aumento stretto del rapporto, quindi gli episodi
  sono finiti. L'argomento è scritto, non verificato da un test: esistono solo
  fixture degeneri che devono terminare.
- Il numero di pivot non ha un limite polinomiale dimostrato, e nessun risultato
  del progetto lo rivendica.
