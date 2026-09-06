# Protocollo di misura

## Ambiente

Build `release` senza LTO e senza `-march=native`, nessun sanitizer, nessuna
trace per pivot. Ogni processo solver è vincolato a un core con `taskset`.

**Le campagne di misura vengono eseguite una alla volta.** Durante
l'esplorazione preliminare la stessa configurazione sulla stessa istanza è stata
misurata a circa 40 s con un solo processo attivo e oltre 60 s con tre processi
su core distinti della stessa macchina. La pinning su core separati non elimina
la contesa su cache condivisa e banda di memoria, quindi campagne concorrenti
non sono ammesse: il costo in tempo di parete è preferibile a misure non
confrontabili. Le esplorazioni esplicitamente etichettate come preliminari
possono essere concorrenti, ma i loro numeri non entrano nel report come misure.

CPU, memoria, sistema, compilatore, flag e hash dei sorgenti sono registrati in
ogni risultato e riassunti nella tabella dell'ambiente del report.

## Tempo e memoria

Il runner misura il wall time con un orologio monotono attorno al processo
completo, comprensivo di lettura dell'istanza e scrittura del risultato. Il
solver misura separatamente lettura, preprocessing, pricing, direzione, ratio
test, aggiornamenti, certificazione e totale. Il picco di memoria è il
`ru_maxrss` del processo solver, distinto dalla memoria del runner. Le due misure
sono riportate entrambe: il tempo del nucleo non nasconde il costo delle fasi
preparatorie.

## Repliche e dispersione

Una replica di riscaldamento non viene registrata separatamente: la prima
replica di ogni combinazione paga la cache fredda e resta nel campione, e le
tabelle riportano la mediana delle repliche e la loro escursione. La proposta
iniziale di cinque repliche è stata ridotta dopo il pilot: con un limite di
trenta secondi e configurazioni che vanno in timeout su una parte delle istanze,
tre repliche per la campagna principale e due per le campagne secondarie
mantengono il costo entro il budget di macchina senza cambiare l'ordinamento
osservato. La riduzione è una decisione dichiarata, non un adattamento dopo aver
visto i risultati.

## Repliche di run che non terminano

Una replica serve a misurare la dispersione di un tempo. Un run che non termina
non ha un tempo da disperdere, e ripeterlo è deterministico: stessa build,
stessa istanza, stessa configurazione e stesso limite danno lo stesso esito.

La prima replica di ogni coppia (istanza, configurazione) viene quindi misurata
sempre; se non produce un risultato ottimo e verificato, le repliche successive
ereditano il suo esito senza essere eseguite e sono marcate
`repeat_of_replica_0`. Il manifesto resta completo, i conteggi di successi e
timeout non cambiano, il PAR-2 non cambia, e il budget di macchina si spende
dove misura qualcosa. Sulla campagna principale questo evitava di rieseguire
138 timeout su 672 run.

## Limiti e stati

Limite di tempo trenta secondi per run nelle campagne principali, applicato da
tutti i backend attraverso l'orologio monotono del solver; il runner impone un
limite di parete più largo come sola rete di sicurezza. Gli stati possibili sono
`optimal`, `time_limit`, `iteration_limit`, `memory_limit`,
`numerical_failure`, `invalid_input`. Un timeout è classificato, non rimosso.
Nessun risultato dichiara un gap non certificato.

## Accettazione di un risultato

Un run entra nell'analisi solo se lo stato è `optimal` **e** una chiamata
separata `pclp verify` ha ricontrollato il certificato senza riottimizzare. Le
soglie di accettazione sono identiche per tutte le configurazioni confrontate e
non fanno parte dello spazio di tuning.

## Aggregazione

Mediana delle repliche per singola istanza e configurazione; confronti appaiati
sulle sole istanze che entrambe le configurazioni hanno risolto e verificato;
PAR-2 con penalità pari al doppio del limite per ogni run non risolto, riportato
insieme al tasso di successo e ai tempi non aggregati. I performance profile
dichiarano l'insieme confrontato e il trattamento dei fallimenti.

## Separazione dei dati

Il tuning esplora su `data/splits/train.json`, la scelta finale si confronta su
`data/splits/validation.json`, e la configurazione viene congelata in
`configs/frozen/` prima di eseguire la campagna sul test. Il test non viene usato
per ritoccare i default.

## Incidente registrato: campagna `main` da rieseguire

Durante la campagna `main` un processo orfano del confronto col prototipo 2023
è rimasto attivo per circa 47 minuti, non vincolato a un core. Il protocollo
richiede che le campagne di misura girino da sole, quindi una parte dei tempi di
`main` è stata raccolta in condizioni non conformi.

La correttezza dei risultati non è in discussione: ogni run resta verificato dal
suo certificato. Sono i tempi a non essere confrontabili con il resto.

**Azione:** al termine delle altre campagne, cancellare
`experiments/runs/main/` e rieseguire la suite a macchina scarica. Un run
completato non viene sovrascritto, quindi la cancellazione esplicita del
manifesto è il modo previsto per ripetere una campagna.

L'episodio è la ragione per cui il protocollo vieta le misure concorrenti: la
contesa non era prevista, è stata scoperta guardando la lista dei processi, e
senza quel controllo sarebbe finita nei numeri senza lasciare traccia.

