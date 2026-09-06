# References and related work

## Attribution

The maximum-closure problem and the classical machinery around it have a long
history. The work this implementation stands on, and the sources of the two
cross-check backends, are credited here.

| Idea | Source |
|---|---|
| maximum closure as a minimum cut | Picard (1976) |
| the pseudoflow algorithm | Hochbaum (2008) |
| the equality normalisation of a linear fractional program | Charnes and Cooper (1962) |
| the parametric treatment of a ratio objective | Dinkelbach (1967) |
| parametric maximum flow and the nested cut sequence | Gallo, Grigoriadis and Tarjan (1989) |
| divide and conquer over the interval of parameters | Eisner and Severance (1976) |
| the residual decomposition | Sidney (1975), developed by Lawler (1978) |
| the version closest to the ratio reading | Margot, Queyranne and Wang (2003) |
| a forest on the closure graph, carrying branch masses and classifying arcs by the sign of the mass they support | Lerchs and Grossmann (1965) |
| its parametric version | Hochbaum (2001) |
| the simplex on an incidence matrix with `k` side rows | Chen and Saigal (1977) |
| the same with a single budget row, on maximum flow | Caliskan (2011) |
| the same on minimum cost flow | Holzhauser, Krumke and Thielen (2017) |

## Companion work

The same canonical sequence, restricted to precedence graphs that are directed
forests, is the subject of a companion paper and repository, whose aggregation
algorithms reach `O(n log n)`:

> **"On parametric Maximum Closure Problems over precedence forests"**
> Valerio Dose, Fabio Furini, Marco Locatelli
> <https://github.com/fabiofurini/parametric-closure-forests>

The vocabulary is shared. A *closure layer* there is a block here, an *optimal
sequence of closure layers* is the canonical decomposition, the *threshold* of a
vertex is the per-vertex bound, and their parameter `lambda` is the ratio `rho`
of the oracle. Those algorithms are specialised to forests; this repository
handles arbitrary DAGs.

## Citing

See [`CITATION.cff`](../CITATION.cff). A manuscript is in preparation.
