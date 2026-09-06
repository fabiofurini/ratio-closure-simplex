# Registro delle decisioni

Decisioni con conseguenze su codice, esperimenti o affermazioni. Ogni voce
riporta la scelta, la ragione e ciò che resta aperto.

## D1 — Il nucleo usa long double, non aritmetica razionale

Il solver lavora in `long double` con scaling binario esatto e controlli
assoluti/relativi. L'aritmetica esatta è usata dagli oracoli di prova (Python
`Fraction`) e dalla ricostruzione algebrica dei pivot nella suite, non dal
nucleo. Conseguenza: l'ottimalità dichiarata è ottimalità entro tolleranze
esplicite, ricontrollata sulle unità originali. Aperto: se una campagna mostrasse
fallimenti numerici sistematici servirebbe una modalità esatta o a precisione
estesa.

## D2 — I backend di confronto sono implementazioni proprie

`dinkelbach` e `parametric` usano un maximum flow Dinic scritto per questo
progetto, con corrente-arco e fasi a livelli. È una implementazione corretta e
ragionevole, **non** un codice di flusso allo stato dell'arte (pseudoflow,
push-relabel con euristiche di gap e relabel globale, o le implementazioni
storiche in `CODICI/DORIT` e `CODICI/GOLBERG`). Qualsiasi confronto con i metodi
di flusso va letto come confronto con questa implementazione. Aperto: adattare
un codice di flusso affermato prima di trarre conclusioni sulla competitività
rispetto allo stato dell'arte.

## D3 — Il backend parametrico è divide et impera, senza riuso del flusso

La decomposizione ricorre sull'insieme differenza e risolve un maximum flow
indipendente per sottoproblema. Non implementa il riuso ammortizzato del flusso
di Gallo, Grigoriadis e Tarjan. È quindi un algoritmo parametrico corretto e
completo, con un costo peggiore di quello ottenibile con il riuso. Aperto: il
riuso del flusso è la prima estensione naturale del backend.

## D4 — `warm_start=residual` non è esposto

Dopo l'estrazione di un blocco la base ereditata resta ammissibile solo se la
componente positiva ereditata è chiusa nel residuo; la rimozione del blocco
elimina proprio quella componente. Una strategia corretta richiederebbe di
scegliere un albero chiuso nel grafo contratto delle componenti, con gestione
dei cicli contratti. Non essendo dimostrata, l'opzione non esiste: il piano
ammette il parametro solo a trasformazione verificata.

## D5 — La riduzione transitiva è esatta o non viene applicata

L'implementazione usa bitset dei discendenti su un ordine topologico inverso,
con un budget di memoria di 64 MiB. Sopra il budget non viene applicata alcuna
riduzione parziale: un filtro euristico renderebbe i confronti dipendenti da
quanto la ricerca è riuscita a esplorare. Il numero di archi rimossi è riportato
nelle statistiche di ogni run.

## D6 — La canonicalizzazione predefinita è `dual`

`sequential` è la procedura di riferimento verificabile: estrae il supporto di
base e aggrega incrementi consecutivi di pari rapporto, quindi richiede più
chiamate all'oracolo in presenza di parità. `dual` recupera direttamente
l'unione massimale per complementarità. Entrambe producono gli stessi blocco
sull'intera suite esatta; `dual` è il default perché evita oracoli ripetuti.

## D7 — Le istanze storiche vengono validate, non adattate

L'importatore PCKP rilegge il modello CPLEX `.lp` accanto al `.dat` e rifiuta
tutto ciò che non è una sola riga di capacità più righe di precedenza semplici
con limiti unitari. Poiché i due file non condividono sempre la numerazione
delle variabili, il confronto ricade su un raffinamento dei colori e dichiara
l'isomorfismo solo quando ogni classe è un singoletto e gli insiemi di archi
coincidono. Le istanze multiperiodo `NN_MM_K.lp` non entrano nel dataset.

## D8 — Le istanze MineLib sono una derivazione dichiarata

CPIT è multiperiodo e multirisorsa. L'istanza importata elimina periodi e
attualizzazione, usa la risorsa 0 come riga di capacità e come capacità il suo
limite sommato sui periodi. La trasformazione è scritta in ogni file importato.
Non va presentata come il modello MineLib originale. Le istanze in cui qualche
blocco non ha coefficiente di risorsa 0 sono rifiutate, perché avrebbero peso
nullo.

## D9 — La separazione dei dati precede il tuning

Training, validation e test sono manifesti congelati, stratificati per origine,
famiglia e decade di taglia, con tutte le repliche di una stessa base generata
sullo stesso lato. Il default viene scelto su training e validation e congelato
prima di eseguire il test. Un default ritoccato dopo aver visto il test
renderebbe il test non indipendente.

## D10 — Nessun risultato non verificato entra nell'analisi

Ogni run è ricontrollato da una chiamata `pclp verify` separata, che non
riottimizza. L'analisi conta solo run `optimal` e verificati; timeout e
fallimenti sono classificati e riportati, mai rimossi silenziosamente. Le
tabelle non vengono generate da una campagna che fallisce il controllo di
completezza.

## D11 — La base iniziale da closure è implementata e misurata negativa

Poiché quasi tutti i pivot hanno passo zero, la prima ipotesi è che il costo sia
il lungo prefisso di fusioni degeneri necessario ad assorbire il residuo
partendo da un singolo pozzo. `initial_basis=closure` avvia la componente
positiva dalla closure del vertice di miglior rapporto fra i primi `initial_seeds`
candidati. È una base ammissibile: su un insieme chiuso i valori sono costanti e
nulli fuori, quindi ogni arco di precedenza non basico è soddisfatto, e la
closure di un singolo seme è connessa, quindi ammette un albero ricoprente.

La correttezza è verificata su 400 istanze casuali con quattro varianti: stessi
blocco e stessi valori. La prestazione **peggiora**: su `minelib_newman1` i
pivot passano da 118\,735 a 216\,768, su un DAG sparso da 2000 vertici restano
invariati. La closure del vertice migliore è spesso un insieme ampio con rapporto
mediocre, che il simplesso deve poi ridurre, di nuovo per passi degeneri.

L'opzione resta implementata e documentata perché il risultato negativo è
un'informazione: sposta il problema dalla scelta del punto di partenza alla
degenerazione stessa del sottoproblema normalizzato. Il default resta `sink`.

`initial_basis=full` riproduce invece la base del prototipo storico, che mette
in base tutti i vertici a `1/w(V)` e rende non basici gli archi di un albero
ricoprente: la componente positiva iniziale e l'intero grafo. La versione
implementata la generalizza ai residui disconnessi scegliendo la componente non
orientata di miglior rapporto. Sul campione preliminare migliora il singolo
oracolo di `pckp_A` (1116 pivot contro 1613) ma peggiora l'aggregato
(505 561 pivot contro 285 932), quindi non diventa default: resta un parametro
misurato dall'ablation.

## D12 - Il fallback anti-ciclo e temporaneo e a soglia lontana

Il fallback permanente a Bland dopo `degeneracy_trigger` pivot degeneri era il
singolo freno piu costoso: con oltre il 99 per cento di pivot a passo zero
scattava immediatamente e restava attivo per tutto l'oracolo, riportando ogni
regola di ingresso a Bland. Sul campione preliminare, passare la soglia da 32 a
32768 riduce i pivot da 850981 a 285932 e il PAR-2 da 170 a 127 secondi.

Il fallback non viene eliminato: viene reso temporaneo. Bland subentra dopo una
sequenza di pivot degeneri e viene rilasciato dal primo pivot a passo positivo.
La terminazione resta garantita: un episodio e una vera esecuzione di Bland su
una soluzione di base fissa, quindi non puo ciclare, e ogni episodio termina con
un aumento stretto del rapporto, quindi gli episodi sono in numero finito.

## D13 - Il ratio test recupera due tecniche dal prototipo storico

La direzione vale `sign` sul sottoalbero entrante, `-kappa` sulla componente
positiva e zero altrove: un arco puo bloccare solo se attraversa il bordo di uno
dei due insiemi. `ratio_test=restricted` scansiona soltanto quegli archi. Poiche
la componente positiva e chiusa, un arco che la attraversa ha la coda fuori, e
la seconda passata copre esattamente le code fuori dal sottoalbero.

`ratio_test=early` aggiunge la scorciatoia del prototipo dell'11 maggio: un
passo nullo e il minimo possibile, quindi la scansione puo fermarsi al primo
bloccante che lo raggiunge. La scorciatoia e sospesa quando Bland e attivo,
perche quella regola richiede l'indice minimo fra i pari merito.

Su un oracolo di `minelib_newman1` gli archi esaminati passano da 1110883 a
215669 con `restricted` e a 184 con `early`, con lo stesso numero di pivot; il
ratio test scende dal 43 per cento al 5 per cento del tempo. Entrambe le
varianti restano opzioni separate, cosi l'ablation misura i due effetti
distintamente e la versione esaustiva resta la referenza verificabile.

## D14 - Il ratio-closure simplex duale

La degenerazione primale e per pivot, quella duale e per blocco. Misurato sulle
istanze generate da 2000 vertici: oltre il 99 per cento dei pivot primali ha passo
zero, mentre le parita fra rapporti - unica sorgente di degenerazione duale -
riguardano 123 blocchi su 267. L'asimmetria e di tre ordini di grandezza e
indica il duale.

Due fatti strutturali rendono il duale particolarmente semplice su questo
problema:

1. **Le variabili di vertice non sono mai primalmente inammissibili.** Il loro
   valore e `1/w(P)` sulla componente positiva e zero altrove, quindi ogni
   inammissibilita primale e uno slack di precedenza `y_head - y_tail < 0`,
   cioe un arco che **esce** da `P`. La scelta della variabile uscente e una
   ricerca combinatoria di un prerequisito non soddisfatto, senza scansioni
   numeriche.
2. **La base e primalmente ammissibile esattamente quando `P` e chiusa**, che e
   quindi la condizione di arresto.

La base iniziale e ammissibile duale per costruzione: ogni vertice e un albero
singolo e `P` e il vertice di rapporto massimo, quindi il costo ridotto di ogni
altro vertice vale `w_k (p_k/w_k - rho) <= 0` e non ci sono archi in foresta.
Costa O(n).

La riga di pivot dello slack uscente si calcola in O(n + profondita): entrando
una variabile non basica `q` di una unita, ogni vertice si muove di
`sigma_q [u in S_q] - kappa_q [u in P]`, quindi la riga dello slack dell'arco
`(t,h)` e non nulla solo per l'ancora dell'albero di ciascun estremo, per gli
archi di foresta sui due cammini verso le radici, e attraverso il termine di
rango uno `kappa_q` quando esattamente un estremo sta in `P`.

Il test del rapporto duale sceglie l'indice minimo fra le colonne che
raggiungono il rapporto minimo, e l'arco uscente e scelto per indice minimo:
insieme sono la regola di Bland duale, quindi non serve - ne e ammesso - un
fallback separato che scelga la prima colonna ammissibile, che distruggerebbe
l'ammissibilita duale.

Due difetti trovati in fase di sviluppo e corretti, entrambi degni di nota
perche non erano dell'idea ma dell'implementazione: la tolleranza di
ammissibilita duale era relativa al costo ridotto stesso, quindi praticamente
nulla, e faceva scattare un abbandono a ogni arrotondamento; ed esisteva un ramo
di Bland che sceglieva la prima colonna invece della minima.

Se l'ammissibilita duale viene comunque persa, il solver **riparte dal primale**
con la sua inizializzazione ammissibile. Non eredita la base duale: il ciclo
primale presuppone ammissibilita primale, che durante la fase duale non vale.
Il certificato finale e prodotto dallo stesso codice verificato nei due casi.

## D15 - Lista incrementale delle violazioni nel duale

Il profilo del duale mostrava che la ricerca delle violazioni costava il 27,5 per
cento del tempo: 1.442.851.488 archi esaminati su un cammino di
`layered n=2000`, perche si riesaminava tutta la componente positiva a ogni
pivot. Con `--dual-leaving incremental` la lista degli archi che escono da `P`
viene mantenuta e aggiornata solo per i vertici la cui appartenenza cambia, con
scarto pigro delle voci obsolete: su `sparse n=2000` le scansioni passano da
17.057.071 a 261.976.

E stata provata anche una variante che mantiene la lista **e** sceglie l'indice
minimo, per avere insieme risparmio e determinismo. Riproduce esattamente la
sequenza di pivot della regola `first` ma costa una passata sulla lista a ogni
pivot, ed e risultata due volte piu lenta. Si e tenuto l'ordine LIFO, lasciando
`first` come regola deterministica di riferimento.

Sulle istanze difficili il duale incrementale arriva a 5,1 volte il primale, ma
la campagna dedicata sullo split di validation non conferma il vantaggio: e la
ragione per cui la separazione dei dati esiste. Vedi il report.

## D16 - Il generatore non era riproducibile, e le istanze correnti lo precedono

Un controllo di riproducibilita ha mostrato che rieseguire
`tools/generate/instances.py` produceva **171 istanze diverse su 171**. La causa:
il seme di ogni istanza derivava da `hash()` di Python su una tupla di stringhe,
e Python randomizza quell'hash a ogni processo. Il difetto era invisibile finche
non si confrontavano due esecuzioni: ogni istanza registrava correttamente il
proprio seme, quindi era autoconsistente, ma il **comando** non ricostruiva
l'insieme.

Corretto: il seme deriva ora da uno SHA-256 degli stessi campi. Due esecuzioni
indipendenti producono 171 istanze identiche byte per byte.

**Conseguenza da tenere presente.** Le istanze in `data/generated/` sono state
prodotte *prima* della correzione, quindi il generatore corretto non le
ricostruisce: ne costruisce un altro insieme, quello che d'ora in poi resta
stabile. Le campagne gia eseguite restano valide e verificabili, perche
referenziano le istanze per nome e SHA-256 e i file sono conservati con i loro
checksum; ma sono riproducibili **conservando i file**, non rigenerandoli.

Rigenerare l'insieme cambia gli hash delle istanze, quindi gli identificatori dei
run: va fatto insieme a una riesecuzione delle campagne, non da solo.


## D17 — L'algoritmo di Lerchs-Grossmann è il precedente più vicino, e va trattato come tale

L'audit della letteratura (`literature/`) ha trovato, dopo la prima stesura, che
l'algoritmo di progettazione di miniere a cielo aperto di Lerchs e Grossmann
(1965) mantiene esattamente il tipo di stato che questo progetto chiamava nuovo.
Nell'esposizione di Hochbaum (2001), che è in `literature/papers/Hochbaum2001.pdf`:
il *normalized tree* è un albero radicato in un vertice aggiunto, ogni ramo porta la
propria massa `b(T_q)`, un arco discendente è *strong* se la massa che sostiene è
positiva, l'albero è normalizzato quando gli unici archi strong sono adiacenti
alla radice, e togliendo gli archi di radice Hochbaum chiama *foresta* la
struttura risultante. Un'iterazione è un *merger*: si aggiunge un arco da un ramo
strong a un ramo weak e si rimuove l'arco che collega la radice del ramo strong
alla radice, aggiornando le masse sostenute.

**Corrispondenza.** Ponendo `b_i = p_i - rho*w_i`, il test strong/weak di
Lerchs-Grossmann è il segno del costo ridotto `p(T) - rho*w(T)` del Forest
Simplex; l'unione dei rami strong è il supporto della soluzione di base; il
merger è un arco entrante con l'arco di radice come uscente.

**Conseguenze.** Tre affermazioni di `docs/claims.md` passano a *non supportato*
(foresta, merge/split, risoluzione della versione di rapporto camminando su uno
stato a foresta). Hochbaum (2001) dà anche una Lerchs-Grossmann parametrica con
la complessità di una singola esecuzione, quindi è un **concorrente** sul compito
che il progetto risolve, non solo un antenato; Picard e Smith (2004) usano già un
obiettivo di rapporto su chiusure. Il tutorial attribuisce ora la foresta nella
sezione che la introduce (`tutorial/sections/03_forest.tex`, Remark) e nel
contesto di flusso.

**Cosa resta aperto.** La domanda Q5 di `literature/sections/08_open.tex`: scrivere
dove la corrispondenza col normalized tree si rompe. L'aspettativa è che un
normalized tree non sia una base dell'LP di rapporto, non porti ratio test né
moltiplicatore duale come oggetti dell'LP, e che la versione parametrica cammini
sui breakpoint invece di pivotare sul programma normalizzato. Se la
corrispondenza fosse invece esatta, il metodo è una rilettura di un algoritmo del
1965 e il lavoro cambia natura.

## D18 — Il nome «ratio-closure simplex» va cambiato in «closure simplex»

Approvato e **applicato a documenti e codice** il 6 settembre 2026; il dettaglio
di che cosa e stato rinominato e che cosa no e in fondo alla decisione.

Tre ragioni, tutte emerse dall'audit:

1. *Nomina la parte ritrattata.* Foresta, struttura delle soluzioni di base e
   pivot merge/split non sono rivendicabili (D17, R2-R4 del posizionamento).
   Il nome coincide con ciò che non è nuovo.
2. *Collide col vocabolario dei vicini.* Mollakhani, Wuille e Guo (2026) si
   chiamano *Spanning Forest Linearization*; Yang (2026) caratterizza le basi con
   *rooted spanning forests*; Lerchs-Grossmann è la foresta nel mining.
3. *Collide con Forrest-Tomlin.* Forrest e Tomlin, *Math. Prog.* 2:263-278,
   1972, è l'aggiornamento dei fattori triangolari della base: differisce per una
   lettera e in un seminario parlato è indistinguibile.

**Scelta.** `closure simplex`, minuscolo, sul modello di *network simplex*, che
prende il nome dal problema a cui è specializzato e non dalla struttura della
base. Forma precisa quando serve: `ratio-closure simplex`. Il lessico della
foresta resta come descrizione dello stato, con attribuzione.

**Verifica del nome.** Una sola ricerca web non ha trovato «closure simplex»
occupato. È evidenza debole: va rifatta su Google Scholar prima di fissarlo.

**Il nome non menziona la capacità, e non deve.** Il sottoproblema che il
simplesso risolve è `max sum p_i y_i` con `sum w_i y_i = 1`, `y_i <= y_j`,
`y >= 0`: la riga di capacità è stata sostituita dalla normalizzazione a 1 e `c`
non appare. La capacità entra solo nel ciclo esterno, dove decide fin dove si
cammina sulla sequenza di blocchi e quale frazione `theta` del blocco critico
si prende. Un nome tipo «knapsack simplex» prometterebbe che il simplesso
gestisce la capacità, cosa che fa la decomposizione canonica — classica, e che
non deve prendere un nome nuovo. Vale la stessa ragione per cui *network simplex*
non nomina le capacità sugli archi.

Tre livelli distinti, da non confondere:

| Livello | Formulazione |
|---|---|
| Nome dell'algoritmo | `ratio-closure simplex` (breve: `closure simplex`) |
| Titolo | *A ratio-closure simplex for maximum-ratio closure and its canonical decomposition* |
| Prima frase dell'abstract | il knapsack LP come bersaglio; poi l'oracolo di rapporto come l'LP a cui il simplesso è specializzato |

Il knapsack con precedenze **non** va presentato come «possibile applicazione»:
è l'origine dell'LP ed è dove il metodo viene misurato. Sta nel titolo e
nell'abstract; sta fuori solo dal nome dell'algoritmo.

**Applicato il 6 settembre 2026.** La prosa e passata al nome nuovo in
`tutorial/`, `report/`, `literature/`, `docs/`, `piano/` e nei README; la macro
condivisa `\FS` produce «ratio-closure simplex», con `\FSC` a inizio frase; i
PDF si chiamano `ratio_closure_simplex_tutorial.pdf` e
`ratio_closure_simplex_literature.pdf`.

**Applicato al codice il 6 settembre 2026, nella stessa giornata.** La prima
passata aveva lasciato gli identificatori invariati e aggiunto due sinonimi CLI;
questa li allinea. La ragione tecnica per rimandare era che cambiare il contenuto
delle configurazioni avrebbe invalidato l'identita dei run gia misurati, ma quel
costo era gia stato pagato: l'aggiunta dei sinonimi aveva cambiato l'hash dei
sorgenti, e tutte e sette le suite ripartivano gia da zero. Rinominare non ha
distrutto nulla che non fosse gia perduto.

| Livello | Prima | Ora |
|---|---|---|
| Valore di `--algorithm` | `forest` | `ratio-closure` (breve `closure-simplex`; `forest` accettato in lettura) |
| Opzione di aggiornamento | `forest_update`, `--forest-update` | `basis_update`, `--basis-update` (nome storico accettato in lettura) |
| API dell'oracolo | `forest_ratio`, `uses_forest` | `ratio_closure_ratio`, `uses_ratio_closure` |
| Header dell'API | `pclp/forest_simplex.hpp` | `pclp/core.hpp` |
| Sorgente del metodo | `src/forest_simplex.cpp` | `src/ratio_closure.cpp` |
| Struttura della base | `DynamicForest`, `dynamic_forest.*` | `BasisForest`, `basis_forest.*` |
| Etichette delle suite | `forest-tuned`, `forest-reference`, `forest-q*`, `forest-primal`, `forest-dual*` | le stesse con prefisso `ratio-closure-` |
| File di configurazione | `configs/{frozen/forest-tuned,solver/forest-reference,tuning/forest_space}.json` | `ratio-closure-tuned`, `ratio-closure-reference`, `ratio_closure_space` |
| Documento del motore | `docs/forest_engine.md` | `docs/ratio_closure_engine.md` |

**Che cosa non e stato rinominato, e perche.** Tre cose conservano la parola
`forest` perche in quei punti non nomina il metodo:

1. *La foresta dentro il motore.* `Engine::forest`, e la prosa su spanning
   forest, forest basis e forest edges in `engine.cpp`, descrivono una foresta
   che e ancora una foresta. Il tipo si chiama ora `BasisForest` perche dice
   **quale** foresta, non perche la parola fosse sbagliata. L'attribuzione
   resta quella di D17.
2. *La famiglia di istanze `forest`.* I diciotto file
   `gen_forest_components8_*` e la famiglia `forest` nell'indice e negli split
   sono identita di dati, con SHA256 in `data/MANIFEST.sha256`. Sono DAG che
   **sono** foreste e non hanno rapporto col nome dell'algoritmo. Rinominarli
   invaliderebbe il manifest dei checksum e gli split congelati.
3. *I record delle campagne.* I manifest, i `resolved_config.json` e il nome
   della campagna di tuning `forest-v2` registrano cosa e stato eseguito, con le
   etichette `forest-*` di allora. Non vengono riscritti. Per questo il solver
   accetta ancora in lettura `algorithm: forest` e la chiave `forest_update`, e
   `tools/report/analyze.py` riconosce sia le etichette storiche sia quelle
   nuove: i dati salvati devono restare leggibili e analizzabili.

**Conseguenza da tenere presente.** Le 2468 misure salvate portano le etichette
`forest-*` e il report le descrive con quel nome, mentre le suite attuali
producono `ratio-closure-*`. La divergenza e voluta: allinearla richiederebbe di
rieseguire le campagne, oppure di riscrivere i record, e la seconda cosa non si
fa. Sparira alla prima campagna misurata con le suite nuove.

**La cartella del progetto** e stata rinominata da `PRECEDENCE_LP` a
`ratio_closure_simplex` nella stessa passata. Gli strumenti Python derivano la
radice da `__file__` e i documenti LaTeX usano percorsi relativi, quindi non
serviva altro che riconfigurare `build/release`. I manifest delle campagne
contengono i percorsi assoluti dei comandi eseguiti e citano ancora il nome
vecchio: sono un registro di cosa e stato eseguito e non vanno riscritti, perche
riscriverli farebbe dire al registro una cosa che non e avvenuta.

La ragione tecnica per non toccare il valore canonico e in `tools/benchmark/run.py`:
l'identificativo di un run e derivato da istanza, task, capacita, **contenuto**
della configurazione e hash dei sorgenti. Cambiare il contenuto della
configurazione avrebbe invalidato l'identita di tutte le campagne. L'aggiunta dei
sinonimi cambia l'hash dei sorgenti, quindi le campagne future avranno
identificativi nuovi e non potranno riprendere in modo incrementale da quelle di
oggi; i record e il report gia scritti restano validi, perche ciascun manifest
porta con se l'hash con cui e stato misurato.

## D19 — Il titolo nomina il metodo e la decomposizione, non l'applicazione

Supera la riga «Titolo» e il paragrafo sul knapsack di D18, che restano scritti
sopra perché una decisione ribaltata in silenzio tende a riapparire.

**Titolo:** *A ratio-closure simplex for maximum-ratio closure and its canonical
decomposition*.

Tre ragioni, tutte emerse discutendo che cosa il metodo effettivamente produce.

1. *Il metodo non si ferma al primo blocco.* Estrae l'intera sequenza canonica:
   un oracolo di rapporto per macroitem, con i duali ricalcolati dentro ogni
   blocco perché nessun moltiplicatore attraversi i blocchi
   (`src/backends.cpp`). Un titolo che nomina la sola chiusura di rapporto
   massimo descrive il primo blocco e tace sul resto.
2. *Il knapsack con precedenze è un'applicazione, e va fra le applicazioni.*
   D18 sosteneva il contrario: che essendo l'origine dell'LP e il luogo della
   misura, dovesse stare nel titolo. La ragione per cui ora sta fuori è la
   stessa per cui sta fuori dal nome: la riga di capacità non compare
   nell'LP che il simplesso risolve, entra solo nel ciclo esterno, e prometterla
   nel titolo prometterebbe che il simplesso la gestisce.
3. *Il metodo è primale e duale.* Il simplesso duale a foresta è implementato
   (D14, `--simplex dual`) e misurato dalla campagna `dual`. Il titolo non lo
   nomina, ma il contributo dichiarato sì.

**Che cosa non è il contributo.** Che un metodo del simplesso sia esatto non è
una rivendicazione e non va offerto come tale. Quello che è in gioco è che cosa
il simplesso *diventa* su questo programma: forme chiuse specifiche della
chiusura, pricing in `O(n)` indipendente dal numero di archi, ratio test
completo, e la sequenza canonica intera invece del solo primo blocco.

**Dove si pensava potesse esserci un caso computazionale, e cosa dice la
misura.** L'ipotesi era la decomposizione: una base è un oggetto naturale da
riusare fra un residuo e il successivo, uno stato di max-flow lo è meno. La
sequenza canonica completa è stata misurata il 6 settembre 2026 con la suite
`configs/suites/canonical_path.json` (task `full-path`, undici istanze, due
repliche, primale sintonizzato, duale, Dinkelbach, parametrico). **L'ipotesi non
regge come formulata:** il parametrico vince su dieci istanze su undici, il
duale solo sul grafo senza archi, e i rapporti sono di uno o due ordini di
grandezza.

La diagnosi conta più della classifica. Il numero di oracoli è esattamente
quello previsto — uno per closure layer, lo stesso che paga Dinkelbach — e il
parametrico usa circa due calcoli di flusso per layer. La differenza sta tutta
**dentro** l'oracolo: da decine a centinaia di migliaia di pivot, di cui fra il
98% e il 100% degeneri. Sull'istanza a livelli con `n = 2000`, 99 oracoli
costano 768.639 pivot, tutti a passo nullo.

Questo **restringe** l'ipotesi del warm start invece di sostenerla. Ereditare
una base cambierebbe da dove ogni oracolo *parte*, non toglierebbe la
degenerazione che consuma il tempo una volta partito. L'ostacolo
implementativo resta quello di D4 — la base ereditata resta ammissibile solo se
la componente positiva ereditata è chiusa nel residuo, e l'estrazione toglie
esattamente quella componente — ma l'onere è cresciuto: una narrazione sulla
riottimizzazione deve ora mostrare che ereditare una base riduce il **numero di
pivot degeneri**, non solo il numero di oracoli.

## D20 — Il riavvio a caldo sul residuo esiste, ed è l'ottimizzazione della decomposizione

Supera D4, che non esponeva `warm_start=residual` perché la trasformazione non
era dimostrata. La condizione mancante era una sola e si verifica in `O(m)`.

**Il fatto strutturale.** Il blocco estratto *è* la componente positiva, cioè un
albero della foresta di base. Gli altri alberi sopravvivono intatti e restano
ancorati a zero: si stacca un albero alla volta. Riusare quella foresta invece
di ripartire dalla base vuota è quindi naturale.

**La condizione.** I valori valgono `1/w(T)` sull'albero positivo `T` e zero
altrove, quindi un arco attivo che esce da `T` violerebbe `y_tail <= y_head`.
L'albero positivo deve essere **chiuso nel residuo**. Si sceglie il migliore per
rapporto fra gli alberi chiusi; se nessuno lo è, `warm_restart()` fallisce e il
chiamante riparte a freddo. La correttezza non dipende quindi da un teorema
sulla struttura del residuo, ma da un controllo eseguito a ogni oracolo.

**Perché non bastava evitare la ricostruzione.** Misurato prima di scrivere il
codice: il lavoro dei pivot supera quello di ricostruzione da 33 a 654 volte.
Un warm start che risparmiasse solo il rebuild varrebbe circa l'1%. Il guadagno
doveva venire dal **numero di pivot**, e viene da lì.

**Misure**, `full-path` con la configurazione congelata, decomposizione identica
blocco per blocco fra freddo e caldo:

| istanza | pivot a freddo | a caldo | riduzione |
|---|---:|---:|---:|
| `gen_disconnected_components6_n2000` | 251.780 | 3.080 | 81,7x |
| `gen_sparse_degree3_n2000` | 89.468 | 6.108 | 14,6x |
| `gen_transitive_degree2-extra3.0_n2000` | 166.730 | 13.225 | 12,6x |
| `pckp_A_972_1661` | 8.503 | 1.056 | 8,1x |
| `minelib_newman1` | 48.974 | 6.915 | 7,1x |

**Tempi**, campagna `canonical_path` a 144 run, dieci istanze risolte da tutte
le configurazioni: il primale a caldo e **3,14x** piu veloce di quello a freddo,
supera Dinkelbach (che il freddo non superava) e vince tre istanze su dieci --
catena, disconnesso e ciclico, cioe le famiglie con la sequenza piu lunga --
contro una su dodici prima. Il parametrico resta avanti sulle altre sette e di
3,4x nel totale: il divario passa da uno-due ordini di grandezza a un fattore
tre, e si chiude del tutto dove i blocchi sono tanti.

**Verifica.** La configurazione entra nella rotazione di `tests/solver_suite.py`
con `--verify-every 1`, quindi un albero positivo non chiuso verrebbe
intercettato al primo pivot dalle 308 istanze esatte confrontate con l'oracolo
di enumerazione.

**Un errore da non ripetere.** La prima stesura usava `inset`, che è
`vector<char>`, come indice di componente. Con più di 127 alberi l'indice va in
overflow silenzioso e si scrive fuori dai limiti: su `minelib_newman1` il
processo moriva con `free(): invalid size`. L'indice di componente ora sta in
`parent`, che è di tipo `Index` e viene comunque ricostruito subito dopo.
