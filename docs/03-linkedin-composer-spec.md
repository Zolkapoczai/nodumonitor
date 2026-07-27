# Munkaparancs — LinkedIn válaszgeneráló (Monitor dashboard)

**Dátum:** 2026-07-20 · **Előzmény:** felhasználói terv-jóváhagyás (chat), a 02-opportunities-ui-spec mintáját követi.

> ## ⚠️ FELÜLÍRVA (2026-07-27) — Thought Leadership Engine
> A v1 „egyetlen Gemini-hívás dönt és ír egyben" architektúráját felváltotta a
> **döntés-vezérelt motor**: `responder/linkedin_engine.py`. Indok: a v1 a tipikus
> LLM-viselkedést adta (összefoglalta a posztot, egyetértett, dicsért), mert
> ugyanabban a hívásban kérte a gondolatmenetet és a szövegezést.
>
> **Ami ebből a dokumentumból ÉRVÉNYES marad:** a hatókör-fegyelem (§Hatókör),
> a route-szerződés (§2) és az UI (§3) — mindhárom változatlan.
>
> **Ami MEGVÁLTOZOTT:** a §14 három-ágú márkadöntés (`bridge`/`nodu`/`none`) már
> **nem globális beállítás, hanem a POSZT tulajdonsága.** A 2026-07-27-i
> munkaparancs követelménye („Never mention NODU unless explicitly instructed")
> úgy teljesül, hogy a megnevezés ahhoz kötött, hogy a poszt **kifejezetten
> eszközt kér-e**. `linkedin.brand_positioning`:
> - `'on_request'` (**default**) — csak igazolt eszköz-kérdésre, Bridge-relevans
>   témában. Három kapu: `explicit_tool_request` → az idézet **ellenőrizve** a
>   posztban (zero-hallucination) → téma ∈ {archicad, revit, interoperability, ifc}.
> - `'off'` — soha, kifejezett kérdésre sem.
> - `'auto'` — a lenti §14 viselkedés, a poszt kérdésétől függetlenül.
>
> A `brand_mode` mező megmarad az API-ban (`bridge`/`nodu`/`none`), és minden
> válasz tartalmazza a döntés indokát (`brand_gate_reason`) — utólag is
> megmagyarázható, miért említette vagy nem említette.
>
> Az architektúra leírása és a döntések indoklása a
> `responder/linkedin_engine.py` modul-docstringjében van, a kód mellett.

## Cél
Egy dashboard-fül, ahova egy LinkedIn-poszt szövege bemásolható, és a rendszer egyetlen Gemini-hívással eldönti, melyik válasz-mód illik rá, majd megírja a választ.

## Hatókör-fegyelem
- **Csak ezt** — a Monitor más része (Lehetőségek, Ad-hoc keresés, Választervezetek, Admin) változatlan marad.
- **Egy válasz-variáns** v1-ben (nem kettő: nyilvános komment + DM — az v1.1).
- **Nincs perzisztencia/history-tábla** — egyszeri, szinkron "beillesztek → kapok → másolok" művelet, nincs approve/reject állapotgép.
- **Nincs automata posztolás, nincs scraping, nincs SalesOS-push.**

## Három ágú döntés (a rendszerprompt lényege)
| Ág | Kritérium | Válasz |
|---|---|---|
| `bridge` | konkrét Archicad↔Revit / parametrikus adatcsere fájdalom | finoman megemlíti a NODU Bridge-et |
| `nodu` | tágabb BIM/IFC/koordinációs szakmai téma, Bridge nem oldaná meg | szakmai hozzászólás, nodu.build jelenléttel, pitch nélkül |
| `none` | egyik sem illik | semleges, hasznos válasz, márkaemlítés nélkül |

Forrás a nodu.build pozicionáláshoz: `SalesOS/docs/00-vision-prd.md` §1 ("BIM/IFC tanácsadás UK facade cégeknek").

## 1. Backend — `responder/draft_generator.py`
Új, önálló függvény (a meglévő Bridge-specifikus `_SYSTEM_PROMPT`-ot NEM módosítjuk):
- `_LINKEDIN_SYSTEM_PROMPT` — a három ágú döntési szabály + LinkedIn-hangnem (rövid, publikus komment, nincs emoji/marketingzsargon — a meglévő elvek szerint).
- `_LINKEDIN_SCHEMA` — strukturált JSON (`fit_type`: bridge|nodu|none, `reply_text`, `rationale`), a Pain Classifier bevált mintája szerint (`response_mime_type=application/json`, `response_schema`, `thinking_config=ThinkingConfig(thinking_budget=0)` — a csonka-válasz hiba elkerülésére, amit már kétszer megtaláltunk).
- `generate_linkedin_reply(config, post_text, author_name="", author_role="") -> dict | None` — egy hívás, visszaadja a strukturált eredményt vagy None hiba esetén.

## 2. Route — `ui/app.py`
- `POST /linkedin/compose` — JSON body `{post_text, author_name, author_role}` → `generate_linkedin_reply` hívása → `{ok, fit_type, reply_text, rationale}` vagy `{ok: false, error}`.
- **Szinkron** (nem `_run_in_bg`), mert egyetlen gyors hívás, azonnali válasz kell a felhasználói élményhez.

## 3. UI — `dashboard.html` + `nodu.css`
- Új nav-item "LinkedIn válasz" az "Ad-hoc keresés" után.
- Szekció: textarea (poszt szövege) + két opcionális input (szerző neve, szerepe/cége) + "Válasz generálása" gomb.
- Eredmény-kártya: fit_type-jelvény (bridge/nodu/none — színkóddal az opportunity severity-jelvények mintájára), a válasz-szöveg, az indoklás, "Másolás a vágólapra" gomb (a meglévő `doCopy`-logika újrafelhasználásával).
- CSS: minimális kiegészítés a meglévő `.opp-card`/`.sev-badge` mintára, nem új rendszer.

## Elfogadási kritériumok
1. Új fül megjelenik, textarea + gomb működik.
2. Bridge-fit teszt-poszt (Archicad→Revit IFC probléma) → `fit_type=bridge`, a válasz megemlíti a Bridge-et.
3. Nodu-fit teszt-poszt (általános BIM-koordinációs téma) → `fit_type=nodu`, válasz Bridge-pitch NÉLKÜL.
4. Semleges teszt-poszt → `fit_type=none`, márkaemlítés nélkül.
5. A válasz teljes (nem csonka — thinking_budget=0 él).
6. A régi funkciók (Lehetőségek, Választervezetek, Ad-hoc, Admin) hibamentesen működnek — nincs regresszió.
