#!/bin/sh
# Coerenza fra i PDF in papers/ e le voci di references.bib.
# La regola: il nome del file e' esattamente la chiave BibTeX.
cd "$(dirname "$0")" || exit 1

pdfs=$(ls papers/*.pdf 2>/dev/null | xargs -n1 basename | sed 's/\.pdf$//' | sort)
keys=$(grep -o '^@[a-z]*{[^,]*' references.bib | sed 's/^@[a-z]*{//' | sort)

orfani=$(comm -23 <(echo "$pdfs") <(echo "$keys"))
mancanti=$(comm -13 <(echo "$pdfs") <(echo "$keys") | grep -v '^Wuille2025$')

printf 'PDF: %s   voci bib: %s\n' "$(echo "$pdfs" | grep -c .)" "$(echo "$keys" | grep -c .)"

if [ -n "$orfani" ]; then
  printf '\nPDF senza voce bibliografica (da rinominare o da citare):\n'
  echo "$orfani" | sed 's/^/  papers\//;s/$/.pdf/'
fi

if [ -n "$mancanti" ]; then
  printf '\nVoci senza PDF (%s) --- devono coincidere con TO_OBTAIN.md:\n' "$(echo "$mancanti" | grep -c .)"
  echo "$mancanti" | sed 's/^/  /'
fi

if [ -z "$orfani" ] && [ -z "$mancanti" ]; then
  printf '\ntutto allineato\n'
fi

# Esce diverso da zero solo se un PDF non ha voce bibliografica: le voci senza
# PDF sono lavoro noto e tracciato, non un errore.
[ -z "$orfani" ]
