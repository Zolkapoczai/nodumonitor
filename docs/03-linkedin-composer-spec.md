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

> ## ⚙️ KIEGÉSZÍTVE (2026-07-29) — Conversation Intent Layer (engine v2)
> **Mérés:** 30+ kézzel értékelt LinkedIn-poszt. Vélemény-, dilemma- és
> debate-posztokon a motor 91–95/100. Mesterség-, tutorial-, portfólió- és
> technika-megosztás posztokon viszont **üzleti stratégiává, ROI-vá, szervezeti
> hatássá emelte a témát**, amit a szerző szándékosan technikai szinten tartott:
> a komment technikailag helyes volt, de más kérdésre válaszolt.
>
> **Diagnózis:** nem reasoning-hiba, hanem hiányzó döntési szint. A v1 minden
> stratégiát egyenlően mért, függetlenül attól, milyen beszélgetésbe száll be.
>
> **A változás:** a stratégia-választás ELÉ bekerült két új, a REASON-hívásban
> felvett mező (`conversation_intent`, `discourse_level`) — **nincs új LLM-hívás,
> a hívás-szám változatlanul 2, legfeljebb 3.** A kettőből a kód két külön
> mechanizmussal dolgozik:
>
> | | Mechanizmus | Mit tesz |
> |---|---|---|
> | **Intent-bias** | lágy súlyozás | 13 beszélgetés-típus (`CONVERSATION_INTENTS`) mindegyike fel- vagy lehúzza az egyes stratégiákat. A stratégia-tér nem szűkül, csak átrendeződik. |
> | **Level-vétó** | kemény kapu | Ha a szerző **technical** síkon beszél, a `business_impact` nem jelölhető (`_LEVEL_VETO`). Ez a munkaparancs "Critical Principle"-je. |
>
> **Miért vétó és nem levonás:** ha a modell a `business_impact`-et 10-re
> pontozza és a többit 4-re, egy −2-es bias még mindig átengedi — a mérhető
> következmény pedig pont ez a hiba volt. Az elfogadási kritérium is absztolút
> ("Craftsmanship posts no longer drift toward business value"), nem statisztikai.
>
> **Nincs regresszió a működő eseten:** a `professional_opinion` és az
> `industry_debate` intent-bias-a **üres** — a 91–95/100-as esetben a döntés
> bitre a v1-es. Teszttel rögzítve (`test_linkedin_intent.py` B szekció, v1
> referencia-implementációval összevetve).
>
> **A két szabály interakciója (tudatos döntés):** egy vélemény-poszt, amit a
> szerző technikai síkon tartott, a vétó miatt NEM kap `business_impact`
> stratégiát — holott a munkaparancs a `business_impact`-et a
> `professional_opinion` preferált listáján is felsorolja. A feloldás: az
> intent-lista azt mondja meg, *mi jöhet szóba*, a szint azt, *hol vagyunk*. Ha a
> szerző már üzleti síkra tette a beszélgetést, a vétó nem lép be, és a
> `business_impact` nyerhet (`_LEVEL_STRATEGY_BIAS['business']` még fel is húzza).
>
> **Kapu (stage 9b):** technikai síkon az executive-absztrakció szótár (ROI,
> competitive advantage, profitability, organisational/digital transformation,
> TCO, business case, bottom line — EN+HU) determinisztikus **sértés**, mert
> mérhető. Precízió-orientált lista: a "cost"/"value"/"efficiency" szándékosan
> NINCS benne, mert technikai kommentben ártatlanul is előfordul.
>
> **Kill switch:** `linkedin.intent_layer: 'on' | 'off'`. Kikapcsolva a döntés
> ÉS a compose-prompt is bitre a v1-es (`_LAYER_OFF` az egységelem) — így a
> 30+ posztos mérés ugyanezen a kódon megismételhető A/B-ként, git-revert nélkül.
>
> **Válasz-szerződés:** a dashboard 8 legacy mezője változatlan; az új mezők
> (`conversation_intent`, `discourse_level`, `topic_gravity`, `strategy_scores`,
> `strategy_vetoed`, `intent_layer`) additívak. DB-séma nem változott.

> ## ⚙️ KIEGÉSZÍTVE (2026-07-31) — engine v3/v4: conversation shaping + kép-bemenet
>
> ### v3 — response shaping (a hang és a konkrétság)
> A benchmark maradék hibái nem a stratégia-választásból jöttek, hanem abból, hogy
> a motor mindig ugyanabban a szerepben és formában válaszolt. Három új REASON-mező,
> **új LLM-hívás nélkül** (mind ugyanabban a REASON-válaszban):
> - `expected_responder_role` (7 ág) — milyen szerepet vár el a szerző
> - `response_mode` (5 ág) — milyen formájú válasz szolgálja azt a szerepet
> - `human_temperature` (8 ág) — a megőrzendő emberi regiszter
>
> Új intent: `personal_experience` (a `reflection` mellé), mert egy megélt
> pillanatot a motor process- és governance-nyelvre fordított.
>
> Új determinisztikus kapuk: sablonos nyitás (`We often see`, `In practice`, …),
> sablonos „hatékonyság"-zárás, és egy **kontextushoz kötött** AI-ujjlenyomat-lánc
> (governance / framework / standardisation / …). Az utóbbi csak akkor sért, ha
> **legalább két** olyan kifejezés szerepel, amit a szerző maga NEM használt —
> a szerző saját governance-szavaira válaszolni teljesen jogos.
>
> ### v4 — a párhuzamos válaszforma-skála összevonása
> A v3 `RESPONSE_MODES` és egy időközben bevezetett `CONVERSATION_RESPONSE_STRATEGIES`
> **ugyanazt a döntést** kérte két, egymást átfedő skálán, kódbeli egyeztetés nélkül:
> két LLM-választás mutathatott ellentétes irányba, és semmi nem oldotta fel. Ez
> szembemegy a §4/16-os elvvel (az LLM a szenzor, a kód a bíró). Egy skála maradt,
> 5 ággal, `response_mode` néven — a „strategy" szó ugyanis már foglalt a 7 elemű
> `STRATEGIES`-re, és épp az ilyen névütközés okozta a v2-ben az `intent` változó
> elárnyékolását. Egyik ág sem veszett el.
>
> Ugyanitt megszűnt egy kétszer elkövetett hibaosztály: a REASON-prompt számozott
> listája **számra** mutató kereszthivatkozásokat tartalmazott, amiket minden új
> mező elcsúsztatott. A hivatkozás mostantól mezőnévre mutat, és teszt tiltja a
> `step N` alakot.
>
> ### Kép-bemenet — a poszt képe mint BESOROLÁSI kontextus
> **Miért:** a render-, fotó- és screenshot-alapú posztok (`portfolio_showcase`,
> `craftsmanship`, `technical_tutorial`) jellemzően **főleg képből** állnak — pont az
> a halmaz, amelyik a benchmarkon a legrosszabbul teljesített. A motor eddig csak a
> szöveget látta, tehát egy render-poszton gyakorlatilag a caption alapján sorolt be.
>
> **A kép CSAK a REASON-hívásba megy.** A COMPOSE a reasoning-objektumból ír, ezért
> a „csak kontextus" nagyrészt **szerkezetileg** áll, nem prompt-kérésen. Ez egyben
> a token-takarékosság magja: a kép tokenjeit egyszer fizetjük, és az újraíró kör
> sem fizeti újra. A hívás-szám változatlan: 2, legfeljebb 3.
>
> | Tétel | Token |
> |---|---|
> | kép ≤384 px, a REASON-ben | 258 (fix) |
> | kép-utasítás + `image_role`, **csak ha van kép** | ~65 |
> | COMPOSE / újraírás | 0 |
> | **kép nélkül** | **0** — a prompt és a séma bájtra a korábbi |
>
> **A szivárgási út zárása:** a REASON `insight`/`core_thesis` szabad szöveg, oda
> beszivároghat egy csak-képen-látszó részlet. A kimeneten ezért determinisztikus
> kapu (`_VISUAL_REFERENCE_PATTERNS`, EN+HU) sérésnek jelöli, ha a komment a képre
> hivatkozik — mert az az állítás **kódban nem ellenőrizhető**, ellentétben a
> `tool_request_quote`-tal, amit a posztban megkeresünk (§4/18).
>
> **Átméretezés a böngészőben** (canvas, 384 px): nincs Pillow-függőség, nincs
> szerver-CPU, kisebb feltöltés. A canvas mindig JPEG-et ad, ezért a szerver **csak
> JPEG-et** fogad — magic-byte ellenőrzéssel, tehát a kliens hamis `image/jpeg`
> MIME-fejlece sem segít. 2 MB-os plafon, a dekódolás ELŐTT. A kép **sosem kerül
> lemezre és sosem kerül logba**.
>
> **Config:** `linkedin.image_input: 'on' | 'off'`, `linkedin.image_max_px: 384`.
> Ha az `intent_layer` `off`, a kép **akkor sem megy el**: a besorolás eredményét a
> kikapcsolt layer eldobná, elküldeni tiszta token-veszteség lenne.
>
> **UI:** fájlválasztó + **vágólap-beillesztés** (screenshot → Ctrl+V, csak az aktív
> LinkedIn-szekcióban), előnézeti bélyegkép a valódi mérettel és a token-költséggel.
>
> **Válasz-szerződés:** a 8 legacy mező változatlan; az új mezők
> (`expected_responder_role`, `response_mode`, `human_temperature`,
> `image_attached`, `image_role`, `ai_fingerprint_terms`) additívak. DB-séma nem
> változott.

> ## ⚙️ KIEGÉSZÍTVE (2026-08-01) — Authenticity Layer
>
> Külső munkaparancs („AUTHENTICITY LAYER v1"). A spec kétharmada már élt
> (intent-besorolás, discourse-szint + vétó, One-Step Rule, kérdés-megválaszolás,
> nyitás- és zárás-kapuk), ezért csak a valóban új rész került be.
>
> ### Bekerült
> - **Természetes nyitások whitelistje** a compose-promptban. Eddig a kapu csak
>   *tiltott*, de nem ajánlott helyettesítést — ez volt a legnagyobb kihasználatlan
>   tartalék a specben.
> - **Bővített tanácsadói tiltólista** a determinisztikus kapuban (`We frequently
>   observe`, `One approach`, `Best practice`, `Organizations should`,
>   `Implementation requires`, `Establishing`, `Ensuring`, `It is critical to`,
>   plusz két magyar megfelelő). Mind **mondat-eleji** egyezés, tehát a kifejezés
>   későbbi, tartalmilag indokolt használata nem sérül.
> - **Megnevezett anti-szerepek:** consultant, standards committee, solution
>   architect, whitepaper, conference speaker.
> - **`linkedin.temperature: 0.3`** — a kódbázis eddig **soha** nem állította a
>   temperature-t, tehát mindkét hívás API-defaulton (1.0) futott. A hullámzás
>   részben egyszerűen ez volt. `'default'` visszaadja a korábbi viselkedést, így
>   A/B-zhető.
> - **Gondolatjel-kapu, CSAK angol kommentben.** LinkedIn-en ismert AI-jel, de a
>   magyar tipográfiában legitim írásjel — ugyanaz az elv, amiért az „architecture"
>   sem került kemény tiltólistára.
>
> ### Authenticity Score — MEGFORDÍTVA
> A spec belső self-checket és önértékelés-alapú újraírást kért. Az így nem tud
> működni: a COMPOSE strukturált kimenetet ad `thinking_budget=0`-val, tehát nincs
> hol egy belső kört futtatni, és az LLM a saját szövegét gyakorlatilag mindig
> elfogadja.
>
> Ezért a rubrika **séma-mező**: a modell öt megnevezett tengelyen pontoz (0-2),
> a küszöböt (`linkedin.authenticity_min_score`, default 8) és az újraírást a **kód**
> végzi, a már létező egy-körös újraíró gépezetben. A modell szenzor, a kód bíró
> (§4/16). Költség: ~10 kimeneti token.
>
> A `no_implementation_drift` tagadva van megfogalmazva, mert a spec
> „Implementation Drift"-je fordított irányú lett volna, és az összeg értelmetlen.
> Minden tengelyen a nagyobb a jobb.
>
> **Kétféle hiányzó pontszám, kétféle válasz** (mért döntés): *részben* hiányzó
> pontszám -> a hiányzó tengely 0, a kapu mér (a modell nem kerülheti meg a kaput a
> rossz tengely kihagyásával). *Teljesen* hiányzó -> `None`, és a kapu **kihagyja** a
> rubrikát, mert az séma-hiba, nem minőségi jel: 0-nak venni azt jelentené, hogy
> minden hívás újraírást kap, a második kör ugyanúgy nem pontozna, tehát a plusz kör
> semmit nem javítana, csak csendben megduplázná a compose-költséget.
>
> ### Szándékosan KIMARADT
> | Amit a spec kért | Miért nem |
> |---|---|
> | Claude Opus 5 Max, „reasoning: high" | Ez a motor `gemini-2.5-flash`-en fut, `thinking_budget=0`-val. A beállítás nem létezik ebben a rendszerben. |
> | 220-250 token kimeneti plafon | A COMPOSE ma 700, a kapu 175 szóig engedi a kommentet. A projektben **kétszer** volt csonkolás-hiba, és a fórum-úton pont ezért emelték 200-ról 320-ra: egy ugyanolyan szóhosszú magyar/német válasz a régi kereten már túlfutott (§4/3). A fel nem használt keret nem kerül semmibe. |
> | `architecture`, `protocol`, `pipeline`, `repository` kemény tiltólistára | Egy AEC-eszközben az „architecture" az iparág neve; a többi legitim technikai szó BIM-beszélgetésben. Ezek helye a már meglévő, szerzőhöz relativizált, legalább-kettő mechanizmus (`_AI_FINGERPRINT_PATTERNS`). |
>
> ### Nyitott kérdés
> A rubrika értéke **nem igazolt**: egy önértékelés önértékelés marad. Az egyetlen
> valódi próba, hogy az `authenticity_detail` korrelál-e a kézi benchmark-pontokkal.
> Ha nem, a rubrika törölhető. A spec 80-85 -> 90-93 pontos becslése a szerző
> projekciója, nem mérés.

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
