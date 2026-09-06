# Generatore di istanze sintetiche

`instances.py` produce le famiglie del piano sperimentale: nessun arco, catene,
foreste di precedenza, DAG a livelli con e senza salti, DAG sparsi e densi,
diamanti, grafi disconnessi, archi transitivamente ridondanti, SCC artificiali e
grafi a due livelli. Ogni famiglia varia taglia, dispersione dei pesi, quota di
profitti negativi, correlazione profitto/peso e quota di parità esatte.

Ogni istanza salva generatore, parametri e seed, e il seme deriva da uno SHA-256
dei parametri: due esecuzioni indipendenti producono lo stesso insieme byte per
byte. Attenzione: le istanze attualmente in `data/generated/` precedono la
correzione di questo comportamento (`docs/decisions.md` D16) e non vengono
ricostruite da questo comando; sono conservate con i loro checksum.
