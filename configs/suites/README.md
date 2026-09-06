# Suite di campagna

Una suite descrive un esperimento completo: istanze selezionate per indice,
famiglia, origine e taglia; task e modo di capacità; configurazioni confrontate;
repliche; limite di tempo. Il runner ne deriva gli identificatori dei run.

| Suite | Esperimento |
|---|---|
| `pilot.json` | dimensionamento: poche istanze per famiglia, un run per configurazione |
| `main.json` | E2: test congelato, quattro configurazioni, tre repliche |
| `ablation.json` | E4: una componente disattivata per volta rispetto alla configurazione congelata |
| `scalability.json` | E3: famiglie generate a taglia crescente |
| `capacities.json` | E6: una capacità contro 5, 20 e 100 query dallo stesso cammino |
| `smoke.json` | riproduzione ridotta, pochi minuti |

Il modo di capacità può essere fissato per suite oppure per configurazione con
la chiave `capacity`: `instance`, `list`, un numero, oppure `{"grid": k}` per k
query equispaziate sul peso totale.
