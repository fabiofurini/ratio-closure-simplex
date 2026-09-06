# Ricerca dei parametri

`search.py` campiona configurazioni dallo spazio dichiarato, rispettando le
dipendenze condizionali e i vincoli di validità, e le valuta sullo split di
training con criterio lessicografico: correttezza, istanze risolte entro i
limiti, PAR-2, memoria di picco. Ogni tentativo, incluse le configurazioni
rifiutate e il motivo, è aggiunto a `history.jsonl`; rilanciare la ricerca
riprende senza ripetere i tentativi già completati. `summary.json` riporta la
classifica, la configurazione migliore e il tempo complessivo speso nel tuning,
non solo quello della configurazione vincente.
