# Campagna canonical_path

E2: decomposizione canonica completa, tutti i blocchi. Confronta il riavvio a freddo di ogni oracolo con il riavvio a caldo dalla base finale del precedente.

## Comando

```bash
python3 tools/benchmark/run.py configs/suites/canonical_path.json --cpu <core>
```

## Stato

- run previsti: 144
- run memorizzati: 144
- verificati da una chiamata `pclp verify` separata: 130
- stati: optimal 130, time_limit 14

## Contenuto

`manifest.json` elenca ogni run con la configurazione risolta, i contatori e l'esito
della verifica. Ogni sottodirectory e un run: `result.json` e `resolved_config.json`.
L'istanza non viene copiata qui: il manifesto la referenzia per nome e hash.

## Configurazioni confrontate

- `ratio-closure-tuned`: `{"algorithm": "ratio-closure", "basis_update": "local", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off"}`
- `ratio-closure-warm`: `{"algorithm": "ratio-closure", "basis_update": "local", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "transitive_reduction": "off", "warm_start": "residual"}`
- `ratio-closure-dual`: `{"algorithm": "ratio-closure", "basis_update": "local", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "simplex": "dual", "transitive_reduction": "off"}`
- `ratio-closure-warm-dual`: `{"algorithm": "ratio-closure", "basis_update": "local", "candidate_limit": 64, "canonicalization": "dual", "degeneracy_trigger": 32768, "entering_rule": "best-improving", "initial_basis": "full", "node_order": "input", "pricing": "candidate-list", "ratio_test": "early", "rebuild_interval": 256, "simplex": "dual", "transitive_reduction": "off", "warm_start": "residual"}`
- `dinkelbach`: `{"algorithm": "dinkelbach"}`
- `parametric`: `{"algorithm": "parametric"}`

Derivati e tabelle si rigenerano con `python3 tools/report/analyze.py`.
