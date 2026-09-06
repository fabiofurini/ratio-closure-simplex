# Libreria di istanze

Una sola istanza canonica per contenuto, scritta una volta e referenziata da
suite e run tramite nome e SHA-256. Nessun file qui va modificato a mano.

## Contenuto

| Cartella | Istanze | Contenuto |
|---|---|---|
| `processed/` | 31 | importate dalle fonti storiche: 23 PCKP a capacità singola, 8 open-pit derivate da MineLib |
| `generated/` | 171 | sintetiche, 13 famiglie strutturali, da 200 a 20000 nodi |
| `splits/` | — | manifesti congelati di training (103), validation (53) e test (46) |

Taglie: fino a 99014 nodi e 1271207 archi (MineLib), fino a 350302 archi fra i
DAG a livelli densi. `index.json` in ciascuna cartella elenca nome, percorso,
hash, nodi, archi, capacità, famiglia e origine.

## Verificare la libreria

```bash
python3 - <<'EOF'
import json, hashlib, pathlib
bad = 0
for line in pathlib.Path('data/MANIFEST.sha256').read_text().splitlines():
    digest, path = line.split('  ', 1)
    data = pathlib.Path(path).read_bytes()
    if path.endswith('.json') and '/splits/' not in path:
        data = data.rstrip(b'\n')          # l'hash è quello del testo canonico
    if hashlib.sha256(data).hexdigest() != digest:
        bad += 1; print('MISMATCH', path)
print('manifest verificato' if not bad else f'{bad} discrepanze')
EOF
```

## Ricostruire

Le istanze sintetiche e gli split sono **riproducibili byte per byte**: due
esecuzioni indipendenti, su macchine diverse, producono gli stessi file.

```bash
python3 tools/generate/instances.py
python3 tools/benchmark/split.py --index data/generated/index.json --index data/processed/index.json
```

Le istanze importate dipendono dagli archivi storici e si ricostruiscono con
`tools/import/`; i comandi sono in `docs/reproducibility.md`.

## Formato

Ogni istanza è un JSON autoconsistente: `node_ids`, `profit`, `weight`, `arcs`
con la convenzione `[i,j]` = «i richiede j», capacità singola o lista di
capacità, e `numeric_type` che dichiara se l'origine è intera, razionale o in
virgola mobile. Le importate portano `source` con file originale, checksum,
esito della validazione del modello e la trasformazione applicata; le generate
portano `metadata` con generatore, parametri e seme. Dettagli in
`docs/input_format.md`.
