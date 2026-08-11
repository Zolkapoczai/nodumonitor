# Meresi poszt-koteg (LinkedIn)

A `bench_linkedin.py` bemenete. Cel: 20-30 valodi poszt, hogy legyen mit
korrelalni — strategia-eloszlas, hossz-sav betartas, konkretsag-komponensek
(`docs/03-linkedin-composer-spec.md`, v8 zaro blokk).

## Formatum
Egy poszt = egy `.txt`, UTF-8, szo szerinti masolat a LinkedInrol. Opcionalis
elso sor metaadatnak:

```
# author=Jane Doe | role=BIM Manager
```

A `.txt` fajlok **gitignore-oltak** (masok tartalma, futasi adat) — ez a README
marad a repoban.

## Elnevezes
`NN-tema-roviden.txt`, pl. `01-newforma-vendor-ad.txt`. A sorrend igy stabil,
es az osszefoglalo tabla olvashato marad.

## Mit erdemes gyujteni
A meres eddig harom poszton allt (53 / 101 / 254 szo, mind BIM-koordinacio).
A hianyzo esetek:
- **rovid** (< 60 szo) es **hosszu** (> 200 szo) poszt — a hossz-sav vegpontjai
- nem-BIM tema (interop, IFC, projektvezetes, szoftverbeszerzes)
- `technical` es `business` diskurzus-sik (eddig tulnyomoreszt `management`)
- allitas/velemeny-poszt, ami ellen erdemes ervelni — eddig a
  `constructive_challenge` **soha** nem nyert
- kerdes-poszt (`answer_the_question` valaszforma)

## Futtatas
```
python bench_linkedin.py bench_posts/
python bench_linkedin.py bench_posts/01-newforma-vendor-ad.txt --force
```
