# Campagna dual

Primal against dual on the same task and the same instances. The dual is a separate campaign because it needs a build that carries it: mixing it into an earlier campaign would change that campaign's build fingerprint.

## Comando

```bash
python3 tools/benchmark/run.py configs/suites/dual.json --cpu <core>
```

## Stato

- run previsti: 248
- run memorizzati: 248
- verificati da una chiamata `pclp verify` separata: 234
- stati: optimal 234, time_limit 14

## Contenuto

`manifest.json` elenca ogni run con la configurazione risolta, i contatori e l'esito
della verifica. Ogni sottodirectory e un run: `result.json` e `resolved_config.json`.
L'istanza non viene copiata qui: il manifesto la referenzia per nome e hash.

## Configurazioni confrontate

- `forest-primal`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `forest-dual`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "simplex": "dual", "transitive_reduction": "off"}`
- `forest-dual-largest-tree`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "dual_leaving": "largest-tree", "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "simplex": "dual", "transitive_reduction": "off"}`
- `parametric`: `{"algorithm": "parametric"}`

Derivati e tabelle si rigenerano con `python3 tools/report/analyze.py`.
