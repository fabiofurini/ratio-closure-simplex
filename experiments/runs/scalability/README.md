# Campagna scalability

E3: generated families whose size varies while structure is held fixed; three backends, two replicas.

## Comando

```bash
python3 tools/benchmark/run.py configs/suites/scalability.json --cpu <core>
```

## Stato

- run previsti: 612
- run memorizzati: 612
- verificati da una chiamata `pclp verify` separata: 518
- stati: optimal 518, time_limit 94

## Contenuto

`manifest.json` elenca ogni run con la configurazione risolta, i contatori e l'esito
della verifica. Ogni sottodirectory e un run: `result.json` e `resolved_config.json`.
L'istanza non viene copiata qui: il manifesto la referenzia per nome e hash.

## Configurazioni confrontate

- `forest-tuned`: `{"algorithm": "forest", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "forest_update": "local", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `dinkelbach`: `{"algorithm": "dinkelbach"}`
- `parametric`: `{"algorithm": "parametric"}`

Derivati e tabelle si rigenerano con `python3 tools/report/analyze.py`.
