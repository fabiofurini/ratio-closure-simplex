# Configurazioni del solver

- `ratio-closure-reference.json`: versione verificabile di riferimento. Pricing
  completo, regola di Bland, ricostruzione completa della foresta,
  canonicalizzazione sequenziale, ratio test esaustivo, controlli diagnostici a
  ogni pivot. Non e una configurazione pensata per essere veloce.
- `dinkelbach.json`, `parametric.json`: backend combinatori di riferimento.

La configurazione scelta dalla ricerca dei parametri sta in `configs/frozen/`,
con data, split e motivazione. Nessuna configurazione qui e un default validato
sul test finale.
