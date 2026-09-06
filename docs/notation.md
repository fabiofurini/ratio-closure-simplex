# Notazione e dizionario dei simboli

Riferimento unico per testo matematico, LaTeX condiviso e nomi pubblici del
codice. I simboli seguono `PAPER_LONG/paper_v1.tex`; le differenze rispetto alle
note storiche sono segnalate esplicitamente.

| Simbolo | Significato | LaTeX (`latex/common/notation.tex`) | Nome nel codice |
|---|---|---|---|
| `G = (V, A)` | Grafo di precedenza, vertici, archi | `\Gset`, `\Vset`, `\Aset` | `Instance`, `node_ids`, `arcs` |
| `(i,j) in A` | j è prerequisito di i, cioè `x_i <= x_j` | `(i,j)\in\Aset` | `Arc{tail=i, head=j}` |
| `p_i`, `w_i`, `c` | Profitto, peso, capacità | `p_i`, `w_i`, `c` | `profit`, `weight`, `capacity` |
| `C` closure | `i in C` implica `j in C` per ogni `(i,j)` | `C\in\Cset` | supporto verificato in `verify_ratio` |
| `p(S)`, `w(S)` | Aggregati sul sottoinsieme | `p(S)`, `w(S)` | `Macroitem::profit`, `::weight` |
| `rho(S)` | Rapporto `p(S)/w(S)` | `\varrho` | `Macroitem::ratio`, `Engine::rho` |
| `rho*` | Rapporto massimo su closure non vuote | `\rho^*` | valore di ritorno dell'oracolo |
| `M_r` | Prefisso chiuso dopo r blocchi | `\mathcal M_r` | `PathResult::prefix_weight/profit` |
| `K_r` | Blocco canonico r | `\Kset_r` | `PathResult::macroitems[r]` |
| `lambda_r` | Rapporto del blocco r, breakpoint | `\lambda_r` | `Macroitem::ratio` |
| `theta` | Frazione del blocco critico | `\theta` | calcolata in `solve_from_path` |
| `y_i` | Variabile del sottoproblema normalizzato | `y_i` | `Engine::y` |
| `s_ij` | Slack di precedenza `x_j - x_i >= 0` | `s_{ij}` | variabile `n+e` nel pricing |
| `beta` | Valore ottimo del duale normalizzato | `\beta` | `Certificate::beta` |
| `lambda`, `mu_i`, `alpha_ij` | Duali dell'LP: capacità, upper bound, precedenza | `\lambda`, `\mu_i`, `\alpha_{ij}` | `SolveResult::lambda`, `::mu`, `::alpha` |
| `div_i(alpha)` | Flusso uscente meno entrante in i | `\divg_i` | somma in `certificates.cpp::dual` |
| `z(c)` | Valore ottimo dell'LP alla capacità c | `z(c)` | `SolveResult::objective` |
| `u(lambda)` | Valore di maximum closure parametrico | `u(\lambda)` | `ClosureFlow::solve` |
| `F`, `Q` | Foresta di base e insieme delle radici | `\Fset`, `\Qset` | `forest`, radici in `Engine` |
| `A`, `B`, `D` | Matrice in forma standard, base, incidenza trasposta | `\mat{A}`, `\mat{B}`, `\mat{D}` | mai densa: solo nei controlli |
| `p`, `w`, `x`, `y` come vettori | Grassetto per matrici e vettori | `\vect{p}`, `\vect{w}`, ... | — |
| `pi`, `eta`, `alpha` come vettori | Lettere greche in grassetto | `\vecg{\pi}`, `\vecg{\eta}` | — |

## Nomi presi dalla letteratura, non inventati

Ogni termine ha un proprietario e si usa la sua parola. La tabella completa,
con i riferimenti, e nel tutorial (§1, «Names and notation, taken from the
literature»); in breve:

| Oggetto | Nome | Fonte |
|---|---|---|
| sottoinsieme chiuso di `V` | **closure** | Picard (1976), che scrive *maximal closure* dove l'uso corrente scrive *maximum* |
| `max p(C)/w(C)` | **maximum-ratio closure** | Hochbaum (2024) |
| lo stesso insieme, in termini d'ordine | **initial set** `rho`-massimale | Sidney (1975), Lawler (1978) |
| la catena annidata di closure | **Sidney decomposition** | Sidney (1975) |
| le sue differenze successive `K_r` | **blocchi** | terminologia di questo progetto |
| foresta con un vertice distinto per albero | foresta **rooted**, **radici** | Yang (2026) |
| l'albero senza quel vertice | albero **rootless** | Yang (2026) |
| foresta con aggregati per ramo | **normalized tree** | Lerchs-Grossmann (1965) |

Il nome del metodo e **ratio-closure simplex**, non «Forest Simplex»: la ragione
sta nella decisione D18 di `decisions.md`.

## Convenzioni che differiscono dalle fonti storiche

- In `PAPER/MARCO/SimplexMacro.tex` il simbolo `lambda_ij` indica uno slack di
  precedenza. Qui lo slack è `s_ij`, `alpha_ij` è il moltiplicatore duale
  dell'arco e `lambda` senza indici è il prezzo della capacità.
- Il sottoproblema normalizzato usa `y_i`, distinto dalla `x_i` dell'LP con
  limiti unitari: `y` non ha upper bound e soddisfa `sum w_i y_i = 1`.
- Non esiste una partizione oggetti/classi: la derivazione è su DAG generici e
  nessuna formula assume alternanza bipartita lungo i cammini.

## Nomi che compaiono nell'output JSON

`status`, `objective`, `dual_bound`, `gap`, `solution`, `mu`, `alpha`,
`macroitems`, `prefix_weight`, `prefix_profit`, `node_bound`, `complete`,
`positive_complete`, `stats`, `configuration`, `configuration_sha256`,
`instance_sha256`, `build`. Il significato operativo è in
[input_format.md](input_format.md).

## Corrispondenza con il paper compagno sulle foreste di precedenza

Dose, Furini e Locatelli, *On parametric Maximum Closure Problems over
precedence forests*, trattano lo **stesso oggetto canonico** su un grafo di
precedenza che è una foresta, mentre questo progetto lo tratta su DAG generici.
I due testi devono usare le stesse parole per la stessa cosa. Il vocabolario
autorevole è il loro; la colonna di destra dice come si chiama qui.

| Loro | Qui | Nel codice |
|---|---|---|
| **closure layer** `I_r` | blocco canonico `K_r` | `PathResult::macroitems[r]` |
| **optimal sequence of closure layers** | decomposizione canonica, cammino canonico | `PathResult`, task `full-path` |
| **breakpoint** di `u(lambda)` | `lambda_r`, rapporto del blocco r | `Macroitem::ratio` |
| **threshold** del vertice i | limite per vertice del duale a blocchi | `PathResult::node_bound[i]` |
| **canonicalization rule** che fonde layer consecutivi a soglia uguale | canonicalizzazione | `--canonicalization sequential` o `dual` |
| parametro `lambda` (pesi `p_i - lambda w_i`) | `rho` dentro l'oracolo, `lambda_r` nella sequenza | `Engine::rho` |
| **Maximum Closure Problem**, MCP | problema di chiusura massima | `closure_value` |

Due avvertenze su questa tabella.

- `threshold` e `node_bound` sono la stessa quantità e non un'analogia: dopo
  l'estrazione del blocco `r`, `bound[i]` riceve il rapporto del blocco per ogni
  vertice del blocco (`src/backends.cpp`), che è esattamente la soglia con cui
  loro definiscono il layer di appartenenza di un vertice.
- Il loro `lambda` e il nostro `rho` sono lo stesso scalare, letto in due modi:
  loro parametrizzano i pesi come `p_i - lambda w_i` e cercano tutte le
  soluzioni al variare di `lambda`; qui la stessa espressione è il costo ridotto
  `b_i = p_i - rho w_i` (decisione D17), e l'oracolo cerca il `rho` che la
  annulla sulla chiusura ottima. La riga `lambda_r` della tabella dei simboli
  sopra era già allineata a loro prima di questa verifica.

Sul contenuto i due lavori non si sovrappongono: loro danno algoritmi di
aggregazione specializzati alle foreste, con complessità `O(n log n)`, e qui il
grafo è un DAG qualsiasi e il metodo è il simplesso. La sequenza canonica
prodotta è però la stessa, quindi i risultati sono confrontabili sulle istanze
che sono foreste.
