# Munkaparancs — Opportunities nézet + signal-vezérelt válaszgenerálás

**Dátum:** 2026-07-20 · **Szerep:** senior tervező → implementáció · **Előzmény:** [01-architektura-audit](01-architektura-audit-2026-07.md) D/1 classifier kész, a `signals` tábla feltöltve, de se UI, se válasz-út nem épült rá.

## Cél (pontosan két dolog, semmi több)
1. **A classifier kimenete láthatóvá válik** a dashboardon egy "Lehetőségek" nézetben — a `signals` tábla böngészhető, fájdalom-fókuszú kártyákként.
2. **A válaszgenerálás a fájdalom-jelre épül**, nem a nyers kulcsszó-score-ra — a Gemini a `pain_summary`/`tech_summary` kontextusból ír választ.

## Hatókör-fegyelem (mit NEM építünk most)
- Nincs `scoring_configs` verziózott súly-tábla (az a Phase 2). A rangsor **prezentációs logika**: severity elsődleges, buying_intent tiebreaker, confidence másodlagos — nem perzisztált pontszám.
- Nincs SalesOS-push, nincs company/person resolver (Phase 2-3).
- Nincs automatikus kiküldés — a human-in-the-loop kapu marad (draft → jóváhagyás → kézi posztolás).

## 1. Adatréteg (`storage/db.py`)
- `get_opportunities(db_path, only_pain=True, min_severity=1, limit=100)` — `signals ⋈ posts`, `is_pain` szűrve, rendezés: `severity DESC, buying_intent DESC, confidence DESC`. A dashboard ezt rendereli szerver-oldalon (a drafts-mintát követve).
- `get_post_with_signal(db_path, post_id)` — poszt + a hozzá tartozó signal-mezők egyben (a válaszgeneráláshoz).
- `get_pain_posts_without_draft(db_path, min_severity, limit)` — `is_pain=1 AND severity>=min AND nincs draft` — a batch-generátor forrása.

## 2. Válaszgenerátor (`responder/draft_generator.py`)
- `generate_draft_for_post` **kiegészül**: lekéri a poszt signal-ját, és ha van, a `pain_summary` + `tech_summary` + `issue_types` bekerül a user-üzenetbe egy "Detektált fájdalom" blokként. Ha nincs signal, a régi viselkedés marad (visszafelé kompatibilis).
- `generate_drafts` batch-szelekció **átáll**: `get_new_posts` + kulcsszó-score helyett `get_pain_posts_without_draft`. Küszöb: `classifier.draft_min_severity` (default 3).

## 3. Route-ok (`ui/app.py`)
- A meglévő `POST /lead/<post_id>/draft` **változatlanul** működik (a signal-enrichment a generátorban történik) — a Lehetőségek kártya "Válasz generálása" gombja ezt hívja.
- A `dashboard()` view átadja az `opportunities` listát a sablonnak.

## 4. UI (`dashboard.html` + `nodu.css`)
- Új nav-elem az "Áttekintő" után: **"Lehetőségek"** badge-dzsel (fájdalom-darabszám).
- Opportunity-kártya: cím (link), platform-pill, **hőfok-badge** (severity 4-5 = forró/piros, 3 = meleg/kék, 1-2 = hűvös/szürke), buying-intent badge, szerep+szerző, **pain_summary** (a fő érték), tech_summary, issue-type chipek, Archicad/Revit valószínűség, gombok: "Válasz generálása" + eredeti megnyitása.
- Áttekintő metrikák bővülnek: "Valódi fájdalom" és "Forró lead (sev 4-5)" kártya.
- CSS: `.sev-badge/.sev-hot/.sev-warm/.sev-cool`, `.intent-badge`, `.issue-chip`, `.opp-card` — a meglévő szín-változókból (`--accent/--blue/--muted/--red`).

## Elfogadási kritériumok
1. `/dashboard` → Lehetőségek fül: a fájdalom-jelek severity-rendezetten, pain_summary-vel láthatók, a nem-fájdalom zaj kiszűrve.
2. Egy opportunity "Válasz generálása" gombja draftot készít, ami a **pain_summary-ra reflektál** (nem generikus), és megjelenik a Választervezetek fülön.
3. `python main.py --generate-drafts` a pain-jelekből válogat (severity>=3), nem a nyers kulcsszó-score-ból.
4. A régi ad-hoc keresés + draft-jóváhagyás + Pipedrive-gomb változatlanul működik (nincs regresszió).
5. A szerver hibamentesen indul, mindkét nézet HTTP 200.
