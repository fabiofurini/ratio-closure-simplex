# Paper da procurare

Tre voci di [`references.bib`](references.bib) senza PDF in [`papers/`](papers/).
Deve coincidere con l'uscita di [`check.sh`](check.sh).

**Nessuna delle tre blocca più niente.** I bloccanti del posizionamento —
`ChenSaigal1977`, `Caliskan2011`, `CharnesCooper1962` e `MargotEtAl2003` — sono
tutti in `papers/` dal 6 settembre 2026, e con loro i gruppi A, B e C sono
completi. Restano solo tre atti di convegno di storia mineraria.

| Chiave | Riferimento | Come è citato ora | Link |
|---|---|---|---|
| `ZhaoKim1992` | Zhao, Y. and Kim, Y. C. — *A new optimum pit limit design algorithm* — 23rd International APCOM Symposium, 423-434, 1992 | `\citet` in [`sections/06_simplex_forests.tex`](sections/06_simplex_forests.tex): variante di Lerchs-Grossmann, descritta attraverso `HochbaumChen2000` | atti APCOM, nessun DOI né fonte online |
| `GianniniEtAl1991` | Giannini, L. M. and Caccetta, L. and Kelsey, P. and Carras, S. — *PITOPTIM: a new high speed network flow technique for optimum pit design facilitating rapid sensitivity analysis* — AusIMM Proceedings 2 57-62, 1991 | `\citet` in [`sections/06_simplex_forests.tex`](sections/06_simplex_forests.tex): implementazione a flusso che le competeva | [ausimm.com](https://www.ausimm.com/publications/) |
| `Whittle1988` | Whittle, Jeff — *Beyond Optimization in Open Pit Design* — Computer Applications in the Mineral Industry, First Canadian Conference, 331-337, 1988 | **mai citato**: la voce esiste in `references.bib` ma nessun `\cite` la richiama | atti CIM, nessun DOI né fonte online |

## Che cosa farne

`Whittle1988` **si può togliere subito** da `references.bib`: non è citato da
nessun sorgente LaTeX, quindi rimuoverlo non tocca nessun testo e non lascia
buchi.

`ZhaoKim1992` e `GianniniEtAl1991` sono citati per nome nella sezione 6, che
tratta Lerchs-Grossmann come il precedente più vicino (D17). Sono entrambi
descritti attraverso `HochbaumChen2000`, che è in `papers/`. Se non si trovano,
la cosa corretta è **toglierli dalla bibliografia e riformulare la frase
attribuendo la descrizione a Hochbaum e Chen**, non citarli di seconda mano
lasciando credere che siano stati letti.

## Come aggiungerne uno

Metti il PDF in `papers/` col nome della chiave BibTeX, per esempio
`ZhaoKim1992.pdf`. `check.sh` lo riconosce da solo e questa lista si accorcia.

## Nota

`Wuille2025` non compare qui perché non è un articolo: è un post del forum
Delving Bitcoin, citato dall'URL, e non ha un PDF corrispondente.
