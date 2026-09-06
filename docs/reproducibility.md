# Riproduzione

Tutti i comandi partono dalla radice `ratio_closure_simplex`. Nessuno scrive fuori da
questa cartella. Le estrazioni degli archivi storici avvengono in una directory
temporanea e non entrano nel progetto.

## 1. Ambiente

```bash
cmake --preset release
cmake --build --preset release --parallel
ctest --preset release
```

Suite completa con l'oracolo LP indipendente (richiede SciPy/HiGHS):

```bash
python3 -m venv build/venv && build/venv/bin/pip install scipy
cmake --preset release -DPCLP_TEST_HIGHS=ON -DPython3_EXECUTABLE=$PWD/build/venv/bin/python
cmake --build --preset release --parallel && ctest --preset release
```

Build diagnostiche: `cmake --preset sanitize` (ASan/UBSan) e `cmake --preset debug`.
Le misure non vengono mai prese su queste build.

## 2. Dati

Le istanze storiche restano nelle cartelle originali; l'importazione le legge e
non le modifica.

```bash
# PCKP a capacità singola, con rilettura del modello .lp
python3 tools/import/pckp_dat.py ../DATA/INSTANCES/PCKP_BB/instances --cross-check

# MineLib: estrazione temporanea e importazione della derivazione a capacità unica
TMP=$(mktemp -d)
unzip -q ../DATA/MINELIB/INSTANCES.zip -d "$TMP"
python3 tools/import/minelib.py "$TMP/INSTANCES"
rm -rf "$TMP"

# Istanze sintetiche
python3 tools/generate/instances.py

# Manifesti congelati di training/validation/test
python3 tools/benchmark/split.py --index data/generated/index.json --index data/processed/index.json
```

Ogni istanza è scritta una sola volta, con il proprio SHA-256 nell'indice; le
suite e i run la referenziano per nome e hash, non per copia.

## 3. Campagne

```bash
python3 tools/benchmark/run.py configs/suites/pilot.json --cpu 2
python3 tools/benchmark/run.py configs/suites/main.json --cpu 2
python3 tools/benchmark/run.py configs/suites/ablation.json --cpu 2
python3 tools/benchmark/run.py configs/suites/scalability.json --cpu 2
python3 tools/benchmark/run.py configs/suites/capacities.json --cpu 2
```

`--dry-run` mostra quanti run sono già presenti. Un run completato non viene
riscritto: una build o una configurazione diverse producono un identificatore
diverso. Interrompere e rilanciare riprende dallo stato salvato.

## 4. Tuning

```bash
python3 tools/tune/search.py configs/tuning/ratio_closure_space.json \
  --split data/splits/train.json --budget 24 --time-limit 20 \
  --output experiments/tuning/forest-v1
```

La storia completa dei tentativi è in `history.jsonl`, il riassunto e la
classifica in `summary.json`. La configurazione scelta viene copiata in
`configs/frozen/` con data, split e motivazione prima di eseguire il test.

## 5. Analisi e report

```bash
python3 tools/report/analyze.py
latexmk -pdf -cd report/main.tex
```

`analyze.py` verifica prima la completezza di ogni manifesto, poi rigenera
tabelle e file dati in `report/generated/` e i CSV in `experiments/analysis/`,
scrivendo `provenance.json` con gli hash delle campagne usate. Il report non
contiene numeri scritti a mano: ogni tabella e ogni figura provengono da questi
file.

## 6. Riproduzione ridotta

```bash
python3 tools/benchmark/run.py configs/suites/smoke.json --cpu 2
python3 tools/report/analyze.py
```

`smoke.json` ripete un confronto significativo su poche istanze e permette di
controllare in pochi minuti che la catena dati → run → verifica → tabelle
funzioni da una directory di build nuova.

## 7. Ambiente misurato

Le misure riportate nel report sono state prese su una sola macchina, con il
solver vincolato a un core (`taskset`), build `release` senza LTO né
`-march=native`, senza sanitizer e senza trace. Hardware, compilatore, flag e
hash dei sorgenti sono registrati in ogni risultato e riassunti nella tabella
dell'ambiente del report.
