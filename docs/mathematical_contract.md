# Contratto matematico del solver

Questo documento fissa che cosa il codice risolve, sotto quali ipotesi e con
quali garanzie. Ogni affermazione qui è verificata dal solver stesso o dalla
suite di accettazione; le proposte non implementate restano in `piano/`.

## 1. Famiglia di LP

Dato un digrafo `G = (I, A)` in cui `(i,j)` significa "i richiede j":

```
max   sum_i p_i x_i
s.t.  sum_i w_i x_i <= c
      x_i - x_j <= 0        per ogni (i,j) in A
      0 <= x_i <= 1         per ogni i
```

Ipotesi della versione implementata:

- `p_i` finiti, di segno arbitrario;
- `w_i` finiti e **strettamente positivi**;
- una sola riga di capacità, `c >= 0` finita;
- coefficienti di precedenza `+1`/`-1` e termine noto nullo;
- limiti superiori unitari comuni.

Input fuori da questa famiglia sono rifiutati con `invalid_input`, senza
modifiche implicite del modello: pesi nulli o negativi, capacità negative,
valori non finiti, ID duplicati, campi sconosciuti, versioni ignote.

I digrafi con cicli sono ammessi: le SCC vengono condensate (all'interno di una
SCC le variabili sono uguali, pesi e profitti si sommano) e la mappa inversa
riporta soluzione e moltiplicatori sulle variabili e sugli archi originali. Ogni
verifica finale avviene nelle unità e sugli archi originali.

## 2. Oracolo di massimo rapporto

Per un prefisso chiuso `M` e residuo `R = I \ M`, l'oracolo cerca `S` non vuoto
in `R` con `M unione S` chiuso che massimizzi `p(S)/w(S)`. Poiché `M` è chiuso,
il problema è una closure nel grafo indotto da `R`.

Il sottoproblema continuo usato dal ratio-closure simplex è

```
max { sum_{i in R} p_i y_i : sum_{i in R} w_i y_i = 1,
      y_i <= y_j per (i,j) in A[R],  y_i >= 0 }
```

senza upper bound. Con pesi positivi il poliedro è limitato e il valore ottimo
coincide con il massimo rapporto di una closure non vuota, **anche quando tale
rapporto è negativo**: è per questo che la normalizzazione è un'uguaglianza.

**Classe di LP.** Vale la pena nominarla, perche il posizionamento dipende da
quale programma si sta specializzando (`literature/sections/03_ratio.tex`,
sezione «The LP class, stated precisely»). Tre letture equivalenti:

- una riga di budget densa a coefficienti positivi sopra un sistema **omogeneo di
  differenze** su un DAG;
- la **base del cono d'ordine** del poset: `{y >= 0, y_i <= y_j}` ha come raggi
  estremi i vettori caratteristici delle closure non vuote, e l'uguaglianza lo
  taglia nel politopo di vertici `chi^C / w(C)`, da cui l'esattezza della
  trasformazione di Charnes-Cooper;
- **incidenza trasposta piu una riga densa**: ogni vincolo di differenza ha un
  `+1` e un `-1` nelle colonne di due variabili di vertice, quindi la matrice e la
  trasposta di un'incidenza, con termine noto nullo sulla parte di rete.

La terza lettura distingue questo LP dalla letteratura del network simplex con
riga laterale, dove le variabili sono archi e le righe sono vertici: qui e il
contrario, e le due formulazioni sono duali l'una dell'altra. Per la stessa
ragione l'LP sta nella famiglia strutturale della regressione isotonica e della
variazione totale su grafo, che sono anch'esse sistemi di differenze su variabili
di vertice.

Duale normalizzato: minimizzare `beta` con `w_i beta + div_i(alpha) >= p_i`,
`alpha >= 0`, `beta` libero. Il certificato restituito è la coppia
(supporto, `alpha`) e viene ricontrollato nelle unità originali.

## 3. Decomposizione canonica

L'estrazione residua ripetuta produce blocchi `K_1, K_2, ...` con rapporti
`lambda_1 > lambda_2 > ...`. Fra le continuazioni di massimo rapporto si sceglie
l'**unione** di tutte le continuazioni ottime: con pesi positivi questa è essa
stessa una continuazione ottima ed è il blocco canonico. Il codice distingue
due nozioni:

- `optimal_support`: il supporto di una singola soluzione di base, che può essere
  strettamente contenuto nel blocco canonico;
- `canonical_macroitem`: l'unione massimale, ottenuta con
  `canonicalization=dual` per complementarità oppure, con
  `canonicalization=sequential`, aggregando incrementi consecutivi di pari
  rapporto.

Ogni prefisso `M_r` è chiuso sul grafo originale; i blocchi sono disgiunti; dopo
la fusione delle parità i rapporti sono strettamente decrescenti. `verify_path`
controlla tutte queste proprietà.

Un percorso può essere **completo** (`complete`) oppure limitato ai rapporti
positivi (`positive_complete`). Il secondo è sufficiente per l'LP a qualunque
capacità e viene dichiarato come tale: non è la sequenza canonica completa.

## 4. Ricostruzione e certificazione dell'LP

Per la capacità `c`, sia `h` il primo indice con `w(M_h) >= c` fra i blocchi di
rapporto positivo. Allora

```
theta = (c - w(M_{h-1})) / w(I_h)
x = (1 - theta) * chi(M_{h-1}) + theta * chi(M_h)
```

Casi trattati esplicitamente: `c = 0`; `c` coincidente con un prefisso
(`theta` degenere senza divisione problematica); `c` oltre il peso del prefisso
positivo, dove la capacità **non** viene saturata perché restano solo rapporti
non positivi; blocco di rapporto nullo, che non migliora il valore.

Il duale completo esportato è `lambda` (prezzo della capacità), `mu_i >= 0`
(upper bound) e `alpha_ij >= 0` (precedenze), con

```
w_i lambda + mu_i + div_i(alpha) >= p_i
```

`verify_solution` ricontrolla, nelle unità originali: ammissibilità primale
(`0 <= x <= 1`, archi, capacità), segni duali, la disuguaglianza qui sopra,
complementarità su `mu`, su `alpha` e sulla riga di capacità, e l'uguaglianza fra
obiettivo primale e bound duale. Un risultato che non supera questi controlli
diventa `numerical_failure`, non viene restituito come ottimo.

## 5. Backend e loro equivalenza

Tre backend producono le stesse strutture certificate e passano gli stessi
verificatori:

- `forest`: ratio-closure simplex sul sottoproblema normalizzato, oracolo per blocco;
- `dinkelbach`: iterazione di Newton dal basso su `max { p(S) - lambda w(S) }`
  risolta come maximum closure con taglio minimo; l'inizializzazione parte da un
  limite inferiore stretto (`min_i p_i/w_i - 1`), quindi tratta anche i rapporti
  negativi senza casi particolari;
- `parametric`: decomposizione divide et impera sull'intervallo dei rapporti; il
  rapporto medio di un intervallo o è un breakpoint o lo separa in due.

Per il taglio minimo si usano due convenzioni distinte: il **lato sorgente
minimo** è l'insieme raggiungibile dalla sorgente nella rete residua; il **lato
sorgente massimo** è il complemento dei vertici che raggiungono il pozzo. Il
blocco canonico è il lato sorgente massimo al rapporto ottimo.

## 6. Stati di uscita

`optimal`, `time_limit`, `iteration_limit`, `memory_limit`,
`numerical_failure`, `invalid_input`. A un limite il solver non dichiara un gap
non certificato. `verify` ricontrolla un risultato salvato senza riottimizzare e
restituisce `valid` o `invalid_certificate`.

## 7. Frontiere non supportate

Pesi nulli o negativi, più capacità indipendenti, upper bound eterogenei,
vincoli `x_i <= gamma_ij x_j`, prerequisiti OR, conflitti, cardinalità e tagli
aggiuntivi restano fuori dal dominio: il solver li rifiuta invece di risolverli
approssimativamente. Il problema intero è un problema distinto e non viene
risolto qui.
