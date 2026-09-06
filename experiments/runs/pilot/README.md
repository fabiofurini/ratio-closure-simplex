# Campagna pilot

Sizing run: a few sizes and families per backend, used only to fix limits, sizes and replicas of the later campaigns.

## Comando

```bash
python3 tools/benchmark/run.py configs/suites/pilot.json --cpu <core>
```

## Stato

- run previsti: 48
- run memorizzati: 48
- verificati da una chiamata `pclp verify` separata: 40
- stati: optimal 40, time_limit 8

## Contenuto

`manifest.json` elenca ogni run con la configurazione risolta, i contatori e l'esito
della verifica. Ogni sottodirectory e un run: `result.json` e `resolved_config.json`.
L'istanza non viene copiata qui: il manifesto la referenzia per nome e hash.

## Configurazioni confrontate

- `forest-reference`: `{"algorithm": "forest", "canonicalization": "sequential", "degeneracy_trigger": 32, "entering_rule": "bland", "forest_update": "full", "initial_basis": "sink", "node_order": "input", "pricing": "full", "ratio_test": "full", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `forest-tuned`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `dinkelbach`: `{"algorithm": "dinkelbach"}`
- `parametric`: `{"algorithm": "parametric"}`

Derivati e tabelle si rigenerano con `python3 tools/report/analyze.py`.
