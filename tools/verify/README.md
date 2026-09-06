# Verifica del draft

`verify_tutorial.py` controlla in aritmetica razionale le formule del ratio-closure simplex contro sistemi di base assemblati separatamente. Verifica inoltre rapporti, blocchi canonici, valore LP e certificati mediante enumerazione delle closure su piccoli DAG.

I confronti comprendono entrambi i sistemi del revised simplex: il sistema trasposto per i moltiplicatori e i costi ridotti e quello diretto per le colonne candidate. Per ogni pivot verifica anche la riga associata alla variabile uscente tramite un sistema trasposto indipendente.

```bash
python3 tools/verify/verify_tutorial.py
```

Il caso principale è letto da `tests/fixtures/paper_example8.json`. Altri quattro casi espliciti e 32 DAG casuali con seed `20260905` controllano parità, profitti negativi, nodi isolati e orientamenti generici.

Genera tabelle, figure TikZ e `verification.json` in `build/tutorial/generated/`. I controlli usano asserzioni Python: eseguire senza `-O`. Il codice è un verificatore didattico, non una libreria di produzione o un backend di benchmark.
