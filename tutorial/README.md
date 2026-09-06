# Report didattico: ratio-closure simplex

Primo draft in inglese, sulla famiglia generale di LP di `PAPER_LONG`. Il testo sviluppa direttamente il ratio-closure simplex su DAG arbitrari: nessun percorso dedicato ai setup.

- [PDF da leggere](ratio_closure_simplex_tutorial.pdf)
- [Sorgente principale](main.tex)
- [Sezioni](sections/README.md)
- [Risultato dei controlli esatti](../build/tutorial/generated/verification.json)

## Contenuto e stato

Il draft contiene la caratterizzazione delle basi mediante foresta, formule orientate per costi ridotti e direzioni, ratio test, quattro tipi di aggiornamento, regola di Bland, certificati e ricostruzione dell'LP mediante blocco.

Tre elementi sono messi in primo piano: la coppia **foresta–radici** come oggetto combinatorio della base (sezione 3), il **pricing specializzato** e la **colonna pivot calcolata direttamente sulla foresta** (sezione 4). La sezione 8 distingue in una tabella il costo di ogni operazione: pricing completo in `O(n)` e pivot completo in `O(n+m)` nella versione con ricostruzione.

La sezione 4 esplicita i sistemi `B^T pi = g_B` per i moltiplicatori e `B v = A_q` per la colonna pivot, mostrando come le formule combinatorie li risolvono. Tratta separatamente anche la **riga pivot**: i suoi coefficienti fuori base si ricavano dalla foresta senza risolvere `B^T eta = e_r`.

L'esempio a otto vertici include una traccia completa di otto pivot e figure prima/dopo il principale split. Sei pivot sono degeneri. Il testo distingue prove in aritmetica esatta, controlli numerici finiti e ottimizzazioni future.

Il verificatore Python è un supporto didattico con aritmetica razionale e algebra lineare esplicita. **Non è il solver C++ ottimizzato e non produce benchmark di prestazione.**

## Compilazione

Dalla radice `ratio_closure_simplex`:

```bash
python3 tools/build_tutorial.py
```

Il comando verifica gli esempi, rigenera tabelle e figure e compila il PDF. Sono necessari Python 3, `latexmk`, pdfLaTeX, BibTeX e i pacchetti standard TeX Live usati in `main.tex`, fra cui TikZ, `algorithm`, `algpseudocode`, `natbib` e `cleveref`.

Il PDF sta qui, accanto ai sorgenti, in una sola copia: `ratio_closure_simplex_tutorial.pdf`. File intermedi, log e tabelle generate restano in `build/tutorial`; nessun `.aux` o `.log` finisce accanto ai sorgenti.

Per le compilazioni con `latexmk` avviate da questa directory, `.latexmkrc` imposta lo stesso percorso di output e la bibliografia condivisa. Dopo modifiche all'istanza o al verificatore usare sempre il comando Python completo, che aggiorna anche le tabelle e le figure.

## Percorso suggerito per la revisione

1. Sezioni 3–4: foresta, radici, segni e direzioni.
2. Sezione 5: ratio test e aggiornamento della base.
3. Sezione 6: pivot 7 e pivot degenere 8.
4. Sezione 7: supporto ottimo, parità canoniche e recupero della soluzione LP.
5. Sezione 9: limiti della verifica eseguita e lavoro ancora da svolgere.

Le correzioni vanno apportate ai sorgenti in questa directory. Le tabelle numeriche e le figure della traccia derivano dall'unica fixture e dal verificatore; non vanno modificate manualmente in `build/`.
