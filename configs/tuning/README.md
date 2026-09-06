# Spazio di ricerca

`ratio_closure_space.json` elenca i soli parametri implementati dal solver, con le
dipendenze condizionali: `pricing_block_size` esiste solo con pricing parziale,
`candidate_limit` solo con candidate list, `rebuild_fraction` solo con
aggiornamento adattivo. Il vincolo `bland -> pricing full` riflette la
validazione del solver. `seeded_candidates` contiene configurazioni valutate per
prime perché rappresentano scelte plausibili a priori.

Le tolleranze numeriche non fanno parte dello spazio: allentarle per ottenere
tempi migliori invaliderebbe il confronto.
