# Motore ratio-closure simplex

## Rappresentazione e costo

Il grafo condensato è immutabile; CSR entrante/uscente e indici stabili.
La foresta usa due slot intrusivi per arco originale del grafo condensato.
Inserimento e cancellazione degli slot costano O(1); **l'intero aggiornamento
del pivot non ha costo O(1)**.

Per vertice si mantengono radice, padre, arco padre, primo figlio/fratello,
successore nella lista dei membri e somme di profitto/peso del sottoalbero.
Le liste dei membri permettono di raccogliere esattamente le vecchie componenti
toccate dalle variabili entrante e uscente. Si applicano cut/link e cambi
d'ancora, poi si radicano e ricalcolano soltanto quelle componenti. Le componenti
estranee al pivot conservano metadati e aggregati. Tutte le visite sono iterative.

La variante full ricostruisce tutte le componenti; local quelle toccate;
adaptive passa a full oltre rebuild_fraction. rebuild_interval permette
ricostruzioni periodiche. Il costo locale è lineare nel numero di vertici delle
componenti toccate, non solo nel sottoalbero spostato. Gli indici sono size_t
(64 bit nella build verificata): nessuna riduzione silenziosa a 32 bit.

La lista ordinata delle variabili non basiche ha n_attivi-1 elementi.
Il pricing completo costa O(n_attivi), indipendentemente da m. Le direzioni
usano sottoalberi e correzione sulla componente positiva.

Il ratio test ha tre modalita. `full` esamina tutti gli slack basici del
residuo ed e la referenza verificabile. `restricted` usa il fatto che la
direzione vale sign sul sottoalbero entrante, -kappa sulla componente positiva e
zero altrove: un arco puo bloccare solo se attraversa il bordo di uno dei due
insiemi, quindi si scandiscono gli archi incidenti al sottoalbero piu quelli
uscenti dai vertici fuori dalla componente positiva. Poiche la componente positiva
e chiusa, ogni arco che la attraversa ha la coda fuori, e le due passate insieme
sono complete. `early` aggiunge l'arresto al primo bloccante a passo nullo, che
e il minimo possibile; e sospeso quando la regola di Bland e attiva, perche
quella regola richiede l'indice minimo fra i pari merito.

Memoria O(n+m), nessun tableau denso. Stack, liste di visita, direzioni e
metadati sono preallocati e riutilizzati. Il test engine_invariants intercetta
operator new nel ciclo senza trace e richiede zero allocazioni. La trace è
volutamente separata e alloca i dati diagnostici. Il residuo usa maschere e
liste di indici sul medesimo grafo; la base è inizializzata nuovamente ad ogni
oracolo. Non vengono copiati profitto/peso/archi per ogni blocco.

La base iniziale ha tre modalita. `sink` mette ogni vertice in un albero singolo e
radica la componente positiva su un pozzo del residuo. `closure` la avvia dalla
closure del vertice di miglior rapporto fra i primi `initial_seeds` candidati.
`full` la avvia dall'intera componente non orientata di miglior rapporto, che e
la base del prototipo storico generalizzata ai residui disconnessi. Tutte e tre
sono ammissibili perche su un insieme chiuso i valori sono costanti e nulli
fuori, quindi nessun arco di precedenza non basico e violato.

## Pricing e degenerazione

full, partial a blocchi e candidate-list sono selezionabili; i candidati in
cache vengono rivalutati sulla base corrente. Prima di dichiarare ottimalità
si esaurisce una scansione completa. Le regole first/best-improving passano
permanentemente a Bland dopo degeneracy_trigger pivot consecutivi di passo
zero. Il riferimento Bland applica l'ordine totale a variabili entranti e
uscenti. La finitezza matematica di Bland riguarda l'aritmetica esatta;
il solver numerico conserva limiti espliciti e controlli finali.

## Massimo blocco dal duale

Alla fine dell'oracolo: beta=rho, alpha_e=-reduced_cost_e sugli archi forestali,
zero sugli altri; r_i=beta*w_i+div(alpha)_i-p_i >= 0.

Un supporto ottimo deve escludere i vertici con r_i>0. Inoltre deve essere chiuso
sugli archi originali e avere estremi ugualmente selezionati su alpha_e>0.
Propaghiamo quindi esclusioni all'indietro sulle precedenze e in avanti sugli
archi con moltiplicatore positivo. Il complemento è chiuso, soddisfa la
complementarità e contiene qualsiasi altro supporto ottimo: è il massimo
blocco, anche se disconnesso. Il costo è O(n+m) per oracolo concluso.

canonicalization=sequential conserva la procedura originale di estrazione
residua e fusione delle parità, usata nei confronti differenziali. dual evita
le chiamate ripetute per componenti a pari rapporto.

## Certificati e SCC

Le SCC vengono calcolate con due visite iterative e condensate, sommando
profitti/pesi e registrando membri e rappresentanti degli archi. Per riportare
il duale sulle variabili originali si usa un albero orientato verso una radice
e uno dalla radice dentro ogni SCC. Le eccedenze di divergenza vengono instradate
alla radice e da questa ai vertici con deficit; i moltiplicatori restano nonnegativi.
La verifica finale usa tutti gli archi originali.

Per ciascun blocco si conserva il duale interno e il rapporto b_i comune.
Si ottiene w_i*b_i+div(alpha)_i >= p_i; uguaglianza sui blocchi estratti.
Per una capacità si sceglie lambda >= 0 al breakpoint critico e
mu_i=max(0,w_i*(b_i-lambda)). Questo fornisce un duale completo dell'LP.
Le somme non richiedono di conservare un certificato denso per ogni residuo:
il certificato complessivo occupa O(n+m).

## Numerica e diagnostica

Profitti e pesi sono scalati separatamente per potenze di due, operazione
esatta in binario salvo i limiti rappresentabili. Il rapporto, i moltiplicatori
e le soluzioni sono restituiti nelle unità originali. Niente fast-math.
Il segno delle direzioni bloccanti usa il confronto stretto d<0: una soglia
assoluta potrebbe nascondere un vincolo. Non si azzerano residui negativi
per far passare un certificato.

Il pricing usa tolleranze assolute/relative sulla scala interna; il controllo
finale usa quelle primali sulle unità originali. I blocco numerici possono
fondere quasi-parità entro la tolleranza documentata; i test razionali
controllano le parità esatte e un caso di rapporti distinti vicini.

verify_every=1 verifica normalizzazione, radici, orientamenti, aggregati,
direzione, corrispondenza del nuovo punto e ricostruzione completa dopo ogni
pivot. La suite Python assembla separatamente B, risolve sistemi con Fraction
e confronta valori, moltiplicatori, colonne, righe e ratio test dei pivot C++.

## Scelte successive alla profilazione

La configurazione locale con estrazione duale è il default implementativo
provvisorio, non un default scelto con tuning/test separati. Warm start tra
residui, aggiornamenti sui soli cammini e riduzione transitiva non sono
attivati: servono varianti e confronti dedicati prima di adottarli.
LEMON/Boost non sono dipendenze del nucleo attuale; non è stata misurata una
superiorità generale rispetto alle loro strutture. HiGHS via SciPy è il
riferimento indipendente LP.
