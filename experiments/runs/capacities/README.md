# Campagna capacities

E6: one capacity against 5, 20 and 100 queries answered from a single positive path; the number of queries is the only difference between the configurations of one backend. Sizes are capped at 2000 nodes so that the query count, not the time limit, is what varies.

## Comando

```bash
python3 tools/benchmark/run.py configs/suites/capacities.json --cpu <core>
```

## Stato

- run previsti: 372
- run memorizzati: 372
- verificati da una chiamata `pclp verify` separata: 372
- stati: optimal 372

## Contenuto

`manifest.json` elenca ogni run con la configurazione risolta, i contatori e l'esito
della verifica. Ogni sottodirectory e un run: `result.json` e `resolved_config.json`.
L'istanza non viene copiata qui: il manifesto la referenzia per nome e hash.

## Configurazioni confrontate

- `forest-q1`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "capacity": "instance", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `forest-q5`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "capacity": {"grid": 5}, "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `forest-q20`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "capacity": {"grid": 20}, "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `forest-q100`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "capacity": {"grid": 100}, "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `parametric-q1`: `{"algorithm": "parametric", "capacity": "instance"}`
- `parametric-q100`: `{"algorithm": "parametric", "capacity": {"grid": 100}}`

Derivati e tabelle si rigenerano con `python3 tools/report/analyze.py`.
