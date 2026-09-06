# Campagna ablation

E4: one component switched off at a time with respect to the frozen forest configuration, on the validation split. Sizes are capped at 2000 nodes: the pilot showed that the layered family alone consumes the budget in time-outs, and the ablation needs many configurations rather than large instances.

## Comando

```bash
python3 tools/benchmark/run.py configs/suites/ablation.json --cpu <core>
```

## Stato

- run previsti: 620
- run memorizzati: 620
- verificati da una chiamata `pclp verify` separata: 560
- stati: optimal 560, time_limit 60

## Contenuto

`manifest.json` elenca ogni run con la configurazione risolta, i contatori e l'esito
della verifica. Ogni sottodirectory e un run: `result.json` e `resolved_config.json`.
L'istanza non viene copiata qui: il manifesto la referenzia per nome e hash.

## Configurazioni confrontate

- `forest-tuned`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `no-early-ratio-test`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "restricted", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `no-restricted-ratio-test`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "full", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `close-degeneracy-trigger`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `bland-entering`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "bland", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "full", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `full-pricing`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "full", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `no-local-update`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "full", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `sequential-canonicalization`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "sequential", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `sink-initial-basis`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "sink", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `with-transitive-reduction`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "on"}`

Derivati e tabelle si rigenerano con `python3 tools/report/analyze.py`.
