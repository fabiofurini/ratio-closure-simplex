# Validazione del solver

CTest esegue cinque suite: esempio8, 36 DAG iniziali, liste intrusive, invarianti
del motore e accettazione estesa. Tutti gli assert critici C++ restano attivi
anche in Release (controlli espliciti con eccezioni).

La suite estesa usa 308 istanze con enumerazione razionale e verifica:
rapporti, macroitem massimi, LP tramite coppie di closure, cinque configurazioni,
tutti i quattro tipi di pivot, certificati originali, trasformazioni metamorfiche,
scaling, parsing, limiti, output esclusivo e certificati alterati.
I pivot C++ tracciati sono confrontati con sistemi di base indipendenti.
engine_invariants verifica zero allocazioni nel ciclo senza trace, riduzione
delle visite full/local e SCC/catene di 30.000 nodi.

```bash
cmake --preset debug
cmake --build --preset debug --parallel 2
ctest --preset debug
cmake --preset sanitize
cmake --build --preset sanitize --parallel 2
ctest --preset sanitize
```

Nel runner tracciato di questa sessione LeakSanitizer non può funzionare:
configurare esplicitamente con -DPCLP_DISABLE_LEAK_CHECK=ON. ASan e UBSan
rimangono attivi. LSan resta abilitato per default nelle esecuzioni ordinarie.

Per richiedere anche HiGHS installare SciPy nell'interprete scelto e usare
-DPCLP_TEST_HIGHS=ON -DPython3_EXECUTABLE=/percorso/python. Il test aggiunge
60 istanze medie, confrontando tre configurazioni Forest con il modello LP
assemblato da zero e scipy.optimize.linprog(method="highs").
Nella sessione è stato usato SciPy 1.18.1 già presente in build/venv;
nessuna dipendenza LP entra nel binario C++.

Ogni build salva acceptance.json nella propria directory; un fallimento del
runner salva failure.json con seed, istanza, flag, stdout e stderr.
I vecchi failure.json possono restare come evidenza storica: lo stato corrente
è quello dell'ultimo CTest e di acceptance.json.

Il verificatore didattico resta disponibile in tools/verify/verify_tutorial.py.
I benchmark non sono test temporali: tools/benchmark_solver.py salva dati grezzi
e risultati certificati in una nuova directory indicata con --output.
