# Esperimenti

- `protocol.md`: protocollo di misura e criteri di accettazione.
- `runs/<campagna>/`: un `manifest.json` con i run previsti, eseguiti, falliti e
  verificati, e una directory per run con `result.json` e `resolved_config.json`.
  L'istanza non viene copiata dentro il run: il manifesto la referenzia.
- `tuning/<nome>/`: `history.jsonl` con ogni tentativo, `summary.json` con la
  classifica e il costo totale della ricerca.
- `analysis/`: derivati rigenerabili (CSV per run e aggregati, controllo di
  completezza, provenienza degli artefatti). Non sono fonti primarie.

Un run completato non viene sovrascritto. Una build o una configurazione diverse
producono un identificatore diverso, quindi un nuovo run.
