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

> ## ⚙️ KIEGÉSZÍTVE (2026-08-09) — Nyitás-rotáció (engine v5)
>
> **A rés:** a 2026-08-01-i Authenticity Layer hat természetes nyitó-formát
> **ajánlott** a compose-promptban, a determinisztikus kapu viszont csak a
> *tanácsadói* nyitásokat tiltja (`_STOCK_OPENING_PATTERNS`). A motor **saját
> whitelistjének** ismétlődése ellen semmi nem védett.
>
> **Miért nem kapu a válasz:** ez a hiba a kommentek **között** keletkezik. Két
> komment külön-külön hibátlan, a sorozatuk mégis felismerhető — egy kommenten
> belüli regex tehát *elvileg* sem láthatja. LinkedIn-en pont ez számít: ugyanaz a
> közönség látja a hozzászólásaidat egymás után, és a nyitások egyformasága ott az
> AI-ujjlenyomat. Ezért a javítás a **bemeneten** van, kódbeli rotációként.
>
> **Mechanizmus** (`pick_opening`) — ugyanaz a minta, mint a `strategy_fit` →
> `pick_strategy`: az LLM a szenzor, a kód a bíró (§4/16). A modell **nem** választ
> nyitást; a kód jelöl ki egyet, és azt adja át a COMPOSE feladat-üzenetében (§4/2).
>
> | Követelmény | Hogyan teljesül |
> |---|---|
> | ne ismétlődjön | a legutóbbi 4 forma kizárva (`_recent_openings`) |
> | reprodukálható legyen | a poszt-szöveg **sha256**-hashéből választ |
> | szórjon | a hash egyenletes: 40 poszton mind a 8 forma előjött |
>
> **Miért sha256 és nem `hash()`:** a CPython a string-hasht processzenként
> randomizálja (`PYTHONHASHSEED`), tehát ugyanaz a poszt újraindulás után **más**
> formát kapna — a döntés nem lenne megmagyarázható, a teszt pedig hol átmenne, hol
> nem. Külön teszt méri két processzben, eltérő seeddel (`test_linkedin_opening.py` D).
>
> **Két új forma** a hat mellé: `straight` (nincs keretezés, a állítás maga kezd —
> ez oldja fel, hogy a feladat-üzenet ma is „Begin with the contribution itself"-et
> kér, miközben mind a hat forma elé tesz egy fél mondatot) és `condition` (a
> feltétellel kezd, ami mellett a dolog számítani kezd). Egyik sem ütközik a
> `_STOCK_OPENING_PATTERNS` mintáival — teszt méri (G1).
>
> **Ahol NINCS kijelölés** (`_OPENING_FREE_MODES`): `answer_the_question` és
> `concrete_suggestion`. Ott a nyitást maga a válaszforma döntötte el; elé tenni egy
> tapasztalat-keretezést pontosan a v4 **mért** viselkedését rontaná el.
>
> **Kapcsolat a `temperature`-rel:** alacsonyabb hőmérséklet éppen a
> nyitás-választást lapítja el a leginkább. Ez a rotáció teszi biztonságossá a
> `'default'` → `0.3` váltást, mert a varianciát nem a mintavételre bízza.
>
> **Kill switch:** `linkedin.opening_variety: 'on' | 'off'`. Kikapcsolva a
> compose-prompt **bájtra** a v4-es (`_V4_OPENING_KEYS` a system-prompt katalógusa;
> a két új forma csak a per-hívás kijelölésen keresztül jut be) — tehát ugyanezen a
> kódon A/B-zhető, git-revert nélkül. A bájtra-azonosságot szó szerinti literál
> rögzíti a tesztben (B szekció).
>
> **Perzisztencia:** a gyűrű memóriában él, nem lemezen. Ez **varianciа-állapot,
> nem adat** — elvesztése újraindításkor legfeljebb egy ismétlődő nyitást okoz —,
> így a §Hatókör „nincs perzisztencia/history-tábla" kikötése sértetlen. Több worker
> esetén processzenként külön gyűrű van: ez a szórást csökkenti kissé, helytelen
> viselkedést nem okoz.
>
> **Válasz-szerződés:** a 8 legacy mező változatlan; az új mezők (`opening_shape`,
> `opening_recent`) additívak. DB-séma nem változott.
>
> **Nyitott kérdés:** a rotáció a *gépi* ismétlődést szünteti meg, azt nem méri,
> hogy melyik forma teljesít jobban. Ha az `authenticity_detail` korrelációja a kézi
> pontokkal igazolódik, az `opening_shape` mezővel formánként is bontható.
>
> ### Hívásonkénti hőmérséklet (ugyanaz a kör)
> 2026-08-09-ig **egyetlen** `linkedin.temperature` hajtotta mindkét hívást, holott
> a követelményük ellentétes:
>
> | Hívás | Kimenet | Mit akarunk | Érték |
> |---|---|---|---|
> | REASON | enum + 0-10 pontszám | **stabilitás** — az intent → bias → vétó → stratégia lánc ez alatt van; ingadozó besorolás más kommentet ad | `0.2` |
> | COMPOSE | nyilvános próza | **ne** modális fogalmazás — az alacsony hőmérséklet a leggyakoribb szófordulatok felé húz, vagyis pont az „LLM-hang" felé | `'default'` |
>
> **Miért engedhető meg a magasabb COMPOSE-hőmérséklet:** ott már van precízebb
> kontroll — a determinisztikus kapu fogja a konkrét sértéseket (tiltott fordulat,
> hossz, n-gram-átfedés, executive-szótár, kép-hivatkozás) és egy célzott újraírást
> kér. A temperature ehhez képest tompa eszköz. A költségoldal a válasz `rewrites`
> mezőjében mérhető.
>
> **Miért nem 0.0 a REASON:** a `strategy_fit` hét stratégiát pontoz, és a
> `pick_strategy` holtversenyben a **deklarációs sorrendet** követi — ott pedig a
> `constructive_challenge` áll elöl. Egy ellaposodó pontszám-eloszlás tehát nem
> semleges: csendben a nyilvános kritikát hozná fel gyakori nyertessé olyan
> posztokon is (portfólió, bejelentés), ahol az intent-bias kifejezetten lehúzza.
>
> **Visszafelé-kompatibilitás:** mindkét érték a `linkedin.temperature`-ből
> **öröklődik**, ha nincs megadva (`'inherit'`), tehát egy régi config viselkedése
> bitre változatlan — teszttel rögzítve (`test_linkedin_temperature.py` B/D6).
> Értelmezhetetlen vagy tartományon kívüli érték szintén öröklés: egy elgépelt szám
> nem változtathat csendben viselkedést.
>
> **Válasz-szerződés:** a `temperature` (bázis) mező megmarad; a két tényleges érték
> az additív `reason_temperature` / `compose_temperature` mezőkben.
>
> ### Telemetria — a mérés előfeltétele
> A motor **minden** döntést visszaad a válaszban, de a válasz a HTTP-körrel
> eltűnik. Emiatt négy, már régóta nyitott kérdésre nem lehetett felelni:
>
> | Kérdés | Amiből megválaszolható |
> |---|---|
> | Nyer-e valaha a `constructive_challenge`? A bias-terv szerint vélemény- és debate-poszton nyerhetne. | `strategy`, `strategy_scores`, `strategy_fit`, `conversation_intent` |
> | Korrelál-e az authenticity-rubrika a kézi pontokkal? *(a fenti 2026-08-01-i blokk nyitott kérdése)* | `authenticity_score`, `authenticity_detail` |
> | Hat-e a hőmérséklet-bontás? | `reason_temperature`, `compose_temperature`, `rewrites` |
> | Szór-e a nyitás-rotáció, és nő-e tőle az újraírás? | `opening_shape`, `opening_recent`, `rewrites` |
>
> Mind a négy **ugyanabból az egy sorból** jön, ezért egy fájl, nem négy külön mérés.
>
> **Nem DB-tábla.** A §Hatókör tiltása **állapotra** vonatkozik: approve/reject
> állapotgép, piszkozat-tárolás, UI-ból olvasott előzmény. Ez append-only ténynapló
> — az alkalmazás soha nem olvassa vissza, nincs hozzá felület, nincs migráció.
> JSONL, hogy pandas/jq/Excel közvetlenül olvassa.
>
> **Hol csatlakozik:** a `generate_comment` mostantól vékony wrapper a
> `_generate_comment` körül. Nem záró sor a nagy függvényben, mert az **hat ponton**
> tér vissza korán (üres poszt, nincs API-kulcs, két API-kivétel, érvénytelen
> reasoning, üres komment) — és pont ezek a hibás utak azok, amiket számolni akarsz.
>
> **Join a benchmarkodhoz:** `post_id` (a poszt szövegének sha256-prefixe, stabil).
> Ugyanaz a poszt újragenerálva ugyanazt az id-t kapja.
>
> **Adatvédelem:** a poszt **teljes** szövege nem kerül bele — más tartalma;
> helyette `post_id` + 160 karakteres részlet, ami a párosításhoz elég. A kép soha,
> semmilyen formában (a meglévő szabály szerint). A komment teljes szövege benne
> van: az a saját kimeneted, és pont az, amit pontozol. Csak **explicit listázott**
> mezők kerülnek át, hogy egy jövőbeli válasz-mező ne szivárogjon be észrevétlenül.
>
> **Config:** `linkedin.telemetry: 'on' | 'off'` (kód-default: **off**, hogy egyetlen
> teszt- vagy import-út se írjon csendben lemezre), `linkedin.telemetry_path`.
> A fájl `.gitignore`-ban van: futási adat, nem forrás.
>
> **Következő lépés:** ~20-30 valós komment után a napló összevethető a kézi
> benchmark-pontjaiddal. Az authenticity-rubrika sorsa (marad vagy törölhető) ekkor
> dönthető el először adatból.
>
> **Ténybeli megjegyzés:** a `gemini-2.5-flash` szerver-oldali default hőmérsékletét
> 1.0-ként szokás megadni, de explicit dokumentált sort erre a modellre a jelenlegi
> Gemini-doksiban nem találtunk — a `temperature` fenti kommentjének óvatossága
> („NEM DOKUMENTÁLT") tehát indokolt. A COMPOSE értékét ezért **mérésből** kell
> eldönteni, nem dokumentációból.

> ## ⚙️ KIEGÉSZÍTVE (2026-08-10) — vendor-skip, konkrétság-mérő, szótár-ragozás
>
> **Mind a három EGY mért esetből jön:** a Newforma-benchmark (külső ChatGPT-pontszám
> 88/100, belső authenticity-rubrika **10/10**). Ez volt az első eset, amit a
> telemetria (F1) rögzített, tehát nem következtetés, hanem napló.
>
> ### 1. Vendor-hirdetés → kihagyás
> **Felhasználói döntés:** vendor-hirdetés alatt nem jelenünk meg. Az indok üzleti:
> egy érdemi komment (a) ingyen engagementet ad a hirdetésnek — a LinkedIn
> kommentszám szerint rangsorol —, (b) azzá tesz, aki egy **szomszédos** versenytárs
> (Newforma: koordináció/interop, vagyis a Bridge mellett) marketingje alatt
> ellenvetést fogalmaz meg.
>
> **Miért nem elég a meglévő `product_demonstration` intent:** annak definíciója
> „their own or someone else's" — vagyis egy gyakorló szakember is ide esik, aki a
> saját épített eszközét mutatja. Az PONT olyan poszt, amire válaszolni akarunk. A
> kettőt csak a **regiszter** választja el, ezért kell rá saját séma-mező.
>
> Két új REASON-mező, **új LLM-hívás nélkül**: `vendor_promotion` (BOOLEAN) +
> `promotion_evidence` (a posztból vett szó szerinti idézet). A döntést a kód hozza,
> **három kapuval** — ugyanaz a zero-hallucination minta, mint a `tool_request_quote`-nál:
> kapcsoló → a modell állítása → az idézet **ellenőrizve** a posztban. A modell „ez
> hirdetés" állítását nem fogadjuk el szavára, mert a következmény az, hogy
> egyáltalán nem generálunk.
>
> A kilépés a **COMPOSE ELŐTT** van: egy meg nem született kommentért nem fizetünk.
> Élesben mérve: 2883 ms / 1 hívás a kihagyásnál, 4531 ms / 2 hívás a generálásnál.
> A UI saját kártyát mutat az igazolt bizonyítékkal és egy **„Mégis generálj"**
> gombbal (`force`) — a kihagyás **ajánlás, nem tilalom.**
> Kapcsoló: `linkedin.skip_vendor_promotion`.
>
> ### 2. F2 — konkrétság-diagnosztika (MÉRÉS, nem kapu)
> A benchmarkolt komment **kategóriát** nevezett meg, nem **esetet**: „subtle
> variations in how they classify issues". A REASON-prompt kért konkrétságot, de
> **semmi nem mérte**, és a rubrika minden tengelyen 2/2-t adott — nincs olyan
> tengelye, ami a homályosságot látná.
>
> Három független proxy (`concreteness`), tiszta regex, nulla LLM-költség:
>
> | | benchmarkolt (88/100) | konkrét változat |
> |---|---|---|
> | `anchors_added` (hozott konkrét domain-elem, a poszthoz relativizálva) | **0** | 3 |
> | `abstract_count` | 7 | 1 |
> | `hedges` (darabszám: 3× „often") | 5 | 0 |
>
> **Nincs összpontszám, és nincs belőle kapu** — szándékosan. Az authenticity-rubrika
> tanulsága: egy igazolatlan mérőszámra kapuzni annyi, mint úgy viselkedni, mintha
> tudnánk valamit. A három komponenst **külön** kell rangkorreláltatni a benchmark-
> pontokkal; az megmutatja, melyik jelez egyáltalán. Ha egyik sem, a blokk törölhető.
>
> A REASON `insight` mezője prompt-oldalon is kapott konkrétság-követelményt, a
> határvonal kimondásával: **technikai konkrétság igen, kitalált projekt-specifikum nem.**
>
> ### 3. Szótár-ragozás — mért hiányok
> A kapu-szótárak csak a **szótári alakot** keresték. A benchmarkolt kommentben:
> `standardizing` ≠ `standardi[sz]ation`, `consistent` ≠ `consistency` → a komment a
> teljes framework-szókincset használta, az `ai_fingerprint_terms` mégis **üres** volt.
> Javítva mindkét szótárban (`_AI_FINGERPRINT_PATTERNS`, `_EXEC_ABSTRACTION_PATTERNS`),
> a többes számmal együtt (`frameworks`, `competitive advantages`, `business cases`).
> A `\b`-határok maradnak: az `inconsistent` **nem** egyezik a `consistency`-vel.
>
> **Új, feltétel nélkül mérő lista:** `_MARKETING_CLICHE_PATTERNS`. A mért kommentben
> ott volt a „can truly unlock its full potential" — egyik listán sem. Ez **külön**
> lista, mert az `_AI_FINGERPRINT_PATTERNS` szerzőhöz relativizált és csak
> technikai/emberközpontú beszélgetésben mér, a mért eset viszont `management` síkon
> volt. Egy marketing-klisé **semmilyen** síkon nem jó írás, ezért mindig mér. Szűk
> és védhető: a legitim BIM-zsargon (`architecture`, `pipeline`, `single source of
> truth`) szándékosan kimarad.
>
> ### Telemetria-hiányosság javítva
> `quality_issues_first`: eddig csak a **végső** `quality_issues` került a naplóba
> (üres = átengedve), tehát egy `rewrites: 1`-es sornál nem lehetett megtudni, **mi**
> váltotta ki az újraírást. A 2026-08-10-i napló-elemzés találta meg ezt a hiányt.
>
> ### 4. Framework-reflex kapu → a `management` sík is (user-döntés)
> A ragozás-javítás után a kényszerített generálás `['governance', 'consistency']`-t
> adott — **két** elem, tehát a darabszám-feltétel teljesült —, a kapu mégsem lépett
> be, mert a `discourse_level` `management` volt. Épp az a „foundational governance" +
> „naming conventions" reflex volt, amire a mechanizmus készült.
>
> `_FINGERPRINT_LEVELS = {"technical", "management"}`.
>
> **A `business` szándékosan kimarad:** ha a szerző MÁR üzleti síkra tette a
> beszélgetést, ott folytatni nem drift, hanem a beszélgetés követése — ezt a motor
> saját terve mondja ki (`_LEVEL_STRATEGY_BIAS['business']` meg is emeli a
> `business_impact`-et). Ott kapuzni szembemenne a saját döntésünkkel.
>
> **Miért elég a `>= 2` küszöb management síkon is:** a kapu csak azokat a
> kifejezéseket számolja, amiket a **szerző nem használt** (`ai_fingerprint_terms`
> relativizál). Egy management-poszt szerzője, aki maga beszél governance-ról, eleve
> védett — az ő szavai nem számolódnak. Teszttel rögzítve (H5).
>
> **Visszafordítható:** a hatás a `rewrites` és a `quality_issues_first` mezőkből
> mérhető; ha túl sok hamis pozitívot hoz, a halmaz egy sorban szűkül.
>
> ### 5. Sablonos-nyitás kapu → első két mondat (user-döntés)
> A minták `^`-hoz kötöttek `re.MULTILINE`-nal, ami **sor**kezdet, nem **mondat**kezdet.
> Egy éles generálás így írt: *„The challenge of disconnected tools is a real one. We
> often see that even with integrated platforms…"* — a sablonos fordulat a **második**
> mondat elején volt, ugyanabban a sorban, tehát átment. Ugyanaz a mondat első helyen
> viszont sértés volt.
>
> `_opening_window()`: az első **két** mondat, mondatonként illesztve.
>
> **Miért pontosan kettő, és miért nem „bármely mondatkezdet":** ez a szabály a
> NYITÁSRÓL szól. Egy sablonos fordulat a 8. mondatban nem nyitási hiba — ott a
> sértés címkéje („ismétlődő nyitás") félrevezető lenne, és átfedésbe kerülne az
> `_AI_FINGERPRINT_PATTERNS`-szel, aminek éppen a regiszter a dolga. A kettő megőrzi
> a kódban már dokumentált szándékot is: a kifejezés későbbi, tartalmilag indokolt
> használata nem sérül (teszt: I3 mondat közepén, I4 harmadik mondat).
>
> **Ismert korlát:** a rövidítések („e.g.", „vs.") hamis mondathatárt adnak. A hatás
> legrosszabb esetben egy szűkebb/bővebb ablak, nem hibás sértés.
>
> ### 6. Az Authenticity rubrika TÖRÖLVE (user-döntés, engine v6)
> A 2026-08-01-i bevezetés saját feltételt szabott: *„az egyetlen valódi próba, hogy
> az `authenticity_detail` korrelál-e a kézi benchmark-pontokkal. Ha nem, a rubrika
> törölhető."* **A feltétel teljesült — negatív irányban.**
>
> | # | Poszt | `authenticity` | `no_implementation_drift` | Amit a komment valójában írt |
> |---|---|---|---|---|
> | 1 | Newforma (vendor ad) | **10/10** | 2 | külső pontozó: „consultant mode", 88/100 |
> | 2 | ugyanaz, `force` | **10/10** | 2 | „foundational governance", „naming conventions" |
> | 3 | BIM risk management | **10/10** | 2 | „cultural willingness to embed those capabilities into daily operations" |
>
> Ez **nem gyenge korreláció volt, hanem nulla variancia.** Egy mérőszám, ami mindig a
> maximumot adja, definíció szerint nem tud rangsorolni. A `no_implementation_drift`
> mindháromszor „nulla driftet" állított, miközben mindhárom komment pontosan
> implementációs/szervezeti síkra sodródott.
>
> **Amit vesztünk:** a modell a lezárás előtt öt megnevezett tengely szerint
> újraolvasta a saját szövegét. Három mérés alapján ez az újraolvasás semmit nem
> fogott meg. A törlés utáni negyedik éles futás megerősítette: a komment minősége
> **változatlan** (ugyanaz a hibatípus, `rewrites: 0`) — vagyis a rubrika valóban nem
> tartott semmit.
>
> **Amit nyerünk:** ~10 kimeneti token/hívás, és eltűnik a 10/10 adta hamis
> biztonságérzet. A helyére a determinisztikus kapu és az F2 konkrétság-diagnosztika
> lép — azok **mért** dolgokat mérnek, nem önértékelést kérnek.
>
> Törölve: `_AUTHENTICITY_DIMENSIONS`, `AUTHENTICITY_MAX`, `authenticity_score()`,
> `authenticity_min_score()`, a `_COMPOSE_PROMPT` pontozó blokkja, a `_COMPOSE_SCHEMA`
> öt integer mezője, a `check_quality` `auth_score`/`auth_min` paramétere, a négy
> válasz-mező és a `linkedin.authenticity_min_score` config-kulcs.
> `TELEMETRY_SCHEMA` 1 → 2 (a régi sorok más oszlopkészletűek).
> Visszaszivárgás ellen teszt őrzi (A1–A8, B2.1).
>
> ### 7. Regiszter-szavak és a horgony-lexikon (a negyedik mérésből)
> **`robust` és a puszta `leverage`** bekerült az `_AI_FINGERPRINT_PATTERNS`-be — és
> nem a marketing-listába, mert *lehet* legitim használatuk („a mapping elég robusztus,
> hogy túlélje az újraépítést"). A relativizálás + a legalább-kettő küszöb pontosan ezt
> a határesetet kezeli: ha a szerző használta, nem számol, és egyetlen előfordulás sem
> indít újraírást.
>
> **Önkritikus tétel:** a `robust` szó a külső spec lexikai tiltólistáján szerepelt,
> amit az első értékelésemben „2019-es AI-jelként" intéztem el, és strukturális
> tellekre tereltem a figyelmet. A szó ezután **éles kimenetben** jelent meg („robust
> BIM tools"), és egyetlen kapu sem fogta. A strukturális tellek valósak — de a
> lexikai listát túl könnyen írtam le.
>
> **`full potential`** már `unlock` nélkül is sértés (a mért komment így ment át: „the
> full potential for risk mitigation can remain untapped").
>
> **Horgony-lexikon bővítve** az éles posztok saját szókincséből: `execution plan`,
> `bep`, `4d`/`5d`/`6d`, `takeoff`, `qa/qc`, `scan-to-bim`, `lidar`, `point cloud`,
> `spi`/`cpi`, `power bi`, `drone`. A hiányuk **alulszámolt**, tehát a későbbi
> korrelációt is rontotta volna.
> **Szándékosan kimarad a `naming convention`:** az egyik mért komment éppen
> consultant-nyelvként használta („establishing strict naming conventions"), tehát
> horgonynak venni azt a kommentet **jutalmazta** volna.
>
> ### 8. ÚJ hibatípus (ötödik mérés): szemantikai redundancia
> Teszt-poszt: *„Revit can run an entire multidisciplinary project yet forces you to
> choose between a stair that's intelligent and one that's shaped the way you actually
> designed it."*
>
> **Ez volt eddig a legjobb futás:** `engineering_problem` / `technical` /
> `frustrated` — mindhárom helyes; a `business_impact` **vétózva**; `abstract_count: 1`
> (a korábbi 7 / 5 / 11 / 13 után); a regiszter tiszta; `rewrites: 0`. A kiosztott
> nyitó-forma (`condition`, az egyik 2026-08-09-i új forma) ezúttal **érvényesült** is.
>
> **De:** a komment első három mondata a poszt saját dichotómiáját mondta újra, más
> szavakkal (~75 szó). Az egyetlen új tartalom a záró mondat volt (hibrid → in-place
> modellek → downstream clash és adatintegritás-vesztés).
>
> **És ezt egyetlen kapu sem látja:** a `post_overlap` **0.0**, mert a 4-gram mérő
> **lexikai** visszhangot mér, nem tartalmi redundanciát. Ugyanaz a hibaosztály, mint
> a korábbiaknál: a kapu a betűt méri, nem a mondanivalót.
>
> **Hol keletkezett — és ez most fordítva van.** A negyedik posztnál a REASON jó volt
> és a COMPOSE hígította fel; itt a REASON `insight`-ja **már eleve újramondás** volt,
> és a COMPOSE hűen megírta. A `missing_perspective` `automation`-t választott — vagyis
> a motor **talált** egy kihagyott dimenziót, de a komment nem használta.
>
> **Telemetria bővítve** ezért: `insight`, `core_thesis`, `missing_perspective`. Enélkül
> csak a végterméket látjuk, a gondolatmenetet nem. **Tisztán additív, ezért a
> `TELEMETRY_SCHEMA` NEM emelkedett** — a verzió akkor kell, ha mező eltűnik vagy
> jelentése változik; egy új oszlop nem teremti meg azt a hazárdot, ami ellen véd.
>
> ### 9. A cél-szóhossz a POSZT hosszából (engine v7) — a `MIN_WORDS` felülvizsgálata
> A felülvizsgálat **más eredményt adott, mint a kérdés feltevése.** Nyolc éles
> generálás:
>
> | poszt szó | komment szó | arány |
> |---|---|---|
> | 101 | 82–97 | 0.81–0.96× |
> | 254 | 110–117 | 0.43–0.46× |
> | **53** | **102–116** | **1.92–2.19×** |
>
> **A `MIN_WORDS = 60` nem a probléma volt: soha nem kötött.** Nulla „túl rövid"
> sértés nyolc generálásból, a legrövidebb komment 82 szó. A hosszt a **prompt**
> szabályozta („80-150 words"), nem a kapu — tehát a padló leengedése önmagában
> semmit nem változtatott volna. (Mellékes megfigyelés: a `MAX_WORDS = 175`-nek van
> dokumentált csonkolás-története, a `MIN_WORDS = 60` viszont **kommentár nélküli,
> soha nem indokolt szám** volt a kódban.)
>
> **A valódi hiba:** a motor ~100 szót írt, bármi is volt a bemenet. Egy 53 szavas,
> éles posztra a kétszeresével válaszolni szerkezetileg is része annak, amiért
> tömöttnek érezzük — **a hossz is regiszter**, és a regisztert illeszteni kell,
> ugyanaz az elv, ami a nyelv és a `human_temperature` mögött áll.
>
> **A szabály** (`target_length`, a kód dönt — `pick_opening`/`pick_strategy` minta):
> tükrözd a posztot, és vágd le mindkét végén (`LENGTH_TARGET_FLOOR`=55,
> `LENGTH_TARGET_CEILING`=120, sáv ±25%, ötre kerekítve).
>
> | poszt | sáv |
> |---|---|
> | ≤55 szó | 40–70 |
> | 101 szó | 75–125 |
> | ≥120 szó | 90–150 |
>
> A gyakori (~100 szavas) esetben nagyjából a mai viselkedés marad, és ott változik,
> ahol a mérés hibát mutatott.
>
> **`MIN_WORDS` 60 → 35:** a legkisebb lehetséges sáv (40) **alá**, hogy a kapu ne
> harcoljon a prompttal, de továbbra is kifogja az elfajzott egysorost. Ez a
> **kettő csak együtt hat**. Invariáns, tesztel rögzítve (K7): a sáv minden
> poszt-hosszra a kapun belül van — különben minden komment újraírást kapna.
>
> **ÉLES A/B ugyanazon a poszton** (Revit stair, 53 szó):
>
> | | előtte (fix 80-150) | most (skálázott 40-70) |
> |---|---|---|
> | komment | 102 és 116 szó | **51 szó** |
> | arány | 1.92–2.19× | **0.96×** |
> | `abstract_count` | 1 | **0** |
> | újramondás | első 3 mondat | **nincs** |
> | `rewrites` | 0 | 0 |
>
> A kapott komment: *„When a custom stair form pushes us to generic models or massing,
> the real hit is often downstream. That choice … means that the 'I' in BIM for a
> custom stair geometry often vanishes on IFC export, losing its data for facility
> management or quantity take-off."*
>
> **Ez az első komment a sorozatban, ami vágás nélkül kiposztolható.** Az újramondás
> eltűnt, és a helyére egy olyan következmény lépett, amit a poszt NEM mondott ki
> (IFC-export → FM- és takeoff-adat vesztése) — pontosan az „egy fogalmi lépés a
> poszton túl", amire a motor épült.
>
> **Óvatosság a következtetéssel:** ez n=1 A/B ugyanazon a poszton. A hatás nagy és a
> mechanizmus meggyőző, de a konkrét számok (55/120/±25%) megítélés kérdése, nem
> mérés. Ezért kapcsolóval jött be (`linkedin.length_scaling`), és a `target_length` +
> `reply_words` a naplóban van, tehát mérhető, betartja-e a modell.
>
> ### 10. A `strategy_fit` skála horgonyzása (engine v8) — a stratégia-összeomlás
> **A diagnózis megfordította a feladatot.** A telemetria 10 sora alapján a nyers
> pontszámok gyakorlatilag **állandóak** voltak:
>
> | stratégia | terjedelem | átlag |
> |---|---|---|
> | `missing_perspective` | 8–9 | **8.8** |
> | `practical_lesson` | 7–9 | 8.1 |
> | `field_experience` | 7–8 | 7.6 |
> | `systems_thinking` | 5–7 | 6.2 |
> | `business_impact` | 5–7 | 6.1 |
> | `constructive_challenge` | 4–7 | 5.7 |
> | `future_outlook` | 3–7 | 4.9 |
>
> Az egy stratégián belüli szórás 1–2 pont, a stratégiák közti rés 2–4. **A modell nem
> a posztot pontozta, hanem a stratégia-leírásokat.** Nyers maximum 10-ből **8 esetben
> a dokumentált fallback** (`missing_perspective`).
>
> **A BIAS NEM HIBÁS — ő volt az egyetlen, ami ezt megfordította** (a `-1.5`-es
> fallback-levonás). Ha a bias-számokhoz nyúlnánk, csak azt cserélnénk, melyik
> közel-állandó győztes jön ki; a választ nem tennénk poszt-érzékennyé. `_STRATEGY_BIAS`
> ezért **változatlan** (teszt rögzíti: L6).
>
> **A javítás a skálán van**, projekt-precedenssel: ugyanez a tömörödő pontozás már
> előfordult a classifier severity-jénél, és a megoldás ott is a horgonyzás volt
> (`docs/04-rendszer-audit`: „a severity-prompt mind az öt fokozatát horgonyoztuk",
> `CLASSIFIER_VERSION → v4`). Négy fokozat kimondva (0-2 / 3-5 / 6-8 / 9-10), plusz
> egy **kalibrációs ellenőrzés**, ami megnevezi a konkrét hibát: *„ha négy vagy több
> stratégiának adtál 7-est vagy többet, a stratégiákat értékeled ABSZTRAKTAN, nem EZ
> ellen a poszt ellen — pontozz újra"*, és minimum 5-ös szórás.
>
> ### 11. Csillapítás a hossz-sávban (`LENGTH_DAMPING = 0.5`)
> A tükrözés első változata csak a **rövid** posztok esetét oldotta meg. Mért adat
> három sávszélességen: 53 szó/40-70 → abstract **0**; 108 szó/80-135 → abstract **5**;
> 254 szó/fix → abstract **11-13**. Az irány egyértelmű: **minél több a hely, annyival
> több a töltelék.** A padló feletti rész ezért feleresben számít, így a plafont csak
> ~185 szavas poszt fölött éri el a cél.
>
> **Egy paramétert változtattam, nem hármat** (spread és plafon érintetlen): n=1-2
> mérés sávkonfigurációnként, és végig az volt a tanács, hogy igazolatlan számokra ne
> építsünk. A csillapítás a legvédhetőbb, mert a mért irány (0.96 arány a rövid
> poszton jó volt, 0.86 a hosszabbon már töltelékkel) pont azt mondja, hogy az aránynak
> **csökkennie** kell a poszt hosszával.
>
> ### ÉLES A/B — mindkét változás, ugyanaz a poszt (Copy/Monitor, 108 szó)
> | | előtte | most |
> |---|---|---|
> | `missing_perspective` (fallback) | 9 | **7** |
> | `practical_lesson` | 8 | **9** |
> | nyers max = végső győztes | nem | **igen** |
> | komment | 95 szó | **73 szó** |
> | `abstract_count` | 5 | **2** |
> | `hedges` | 1 | **0** |
>
> A kapott komment **konkrét számot ad** — *„perhaps anything under 10mm"* —, és
> pontosan a szerző saját példájára válaszol (a poszt 300 mm-t említ; a komment szerint
> a *kis* elmozdulások a valódi probléma). Ez általános gyakorlati javaslat, nem
> kitalált projekt-adat, tehát a zero-hallucination elv áll.
>
> **A mechanizmus egészségesebb lett:** a nyers maximum mindkét tesztelt poszton
> egyezik a végső győztessel, tehát a bias nudge-ként működik, nem teherhordóként.
> **Amit ez NEM mond ki:** hogy a győztes diverzifikálódott. Két poszton mindkétszer
> `practical_lesson` nyert. Ehhez több mérés kell.
>
> ### NYITOTT — a konkrétság négy mérés után is romlik
> | | #1 | #2 | #3 | #4 |
> |---|---|---|---|---|
> | `anchors_added` | 0 | 0 | 0 | 0 |
> | `abstract_count` | 7 | 5 | 11 | 13 |
>
> **Négy komment, négyszer nulla hozott konkrét horgony.** A REASON `insight`-ja
> közben használható volt (pl. „a kontroll-százalékok a BIM execution plan
> érettségétől függenek") — a hígítás tehát a COMPOSE lépésben történik, nem a
> gondolatmenetben.
>
> Két további, egyik kapun sem szereplő regiszter-szó a negyedik futásból:
> **„robust"** BIM tools és a puszta **„leverage"** (a `_MARKETING_CLICHE_PATTERNS`
> `leverage the power of`-ot követel). A horgony-lexikon is hiányos: a „BIM execution
> plan", `4D`/`5D`, `quantity takeoff`, `QA/QC`, `scan-to-BIM`, `LiDAR`, `SPI`/`CPI`
> nincs benne, holott valódi, megnevezhető artefaktumok — ez alulszámol, tehát a
> későbbi korrelációt is rontja.
>
> **Válasz-szerződés:** a 8 legacy mező változatlan; új additív mezők: `skipped`,
> `skip_reason`, `vendor_promotion`, `promotion_evidence`, `forced`, `concreteness`,
> `quality_issues_first`. A `skipped: true` válaszban `reply_text` üres — a UI a
> `skipped` flaget vizsgálja először. DB-séma nem változott.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — Nyitás-visszhang kapu (engine v9)
>
> ### A mérés, ami ezt kikényszerítette
> Az első **valódi köteg** (5 poszt, `bench_posts/01..05`, 146–278 szó, mind
> más szerzőtől) — ez volt az első alkalom, hogy a motor egy futásban öt
> **különböző** posztot látott, nem ugyanazt háromszor. Amit azonnal megmutatott:
>
> | # | kijelölt forma | a komment valódi kezdete |
> |---|---|---|
> | 01 | `own_practice` | „**What strikes me** about this is…" |
> | 04 | `strikes` | „**What strikes me** about the discussion…" |
> | 05 | `pattern` | „**What strikes me** is how often…" |
>
> **Három különböző kijelölés, ugyanaz a mondat.** A 2026-08-09-i rotáció tehát a
> *formát* rotálja, de a formakijelölés **utasítás, nem kikényszerített eredmény** —
> és amit a modell valójában ír, azt eddig semmi nem mérte. Ugyanaz a hibaosztály,
> ami ellen a rotáció készült („a hiba a kommentek KÖZÖTT keletkezik"), csak egy
> szinttel beljebb: most a saját mechanizmusunk **kimenetén** jelent meg.
>
> Mellékesen ugyanez a köteg egy második, szintén kapu nélküli tellt is mutatott:
> „the real power / the real advantage / the real difference" záró mondat 4/5-ben.
> Ez **nem** kapott javítást — egy köteg egy mechanizmust, különben nem tudjuk,
> melyik változás mit tett.
>
> ### Miért NEM a tiltólista bővítése
> A kézenfekvő lépés — `_STOCK_OPENING_PATTERNS` + „What strikes me" — **hibás
> lett volna:** a „What strikes me" a *saját katalógusunk* ajánlott formája
> (`OPENING_SHAPES['strikes']`). Tiltólistára tenni annyi, mint a saját whitelistünk
> ellen kapuzni; a G1 teszt épp ezt az önellentmondást őrzi. **A hiba nem a
> kifejezésben van, hanem az ismétlésben** — tehát nem szótárhoz kell mérni, hanem a
> saját előző kimeneteinkhez.
>
> ### A mechanizmus
> `opening_fingerprint(comment)` — az **első mondat első három szava**,
> normalizálva. Gyűrű (`_recent_opening_texts`), és egyezés esetén a determinisztikus
> kapu sértést ad, ami az újraíró körbe megnevezve átmegy.
>
> - **Miért három szó:** a mért eset pontosan ennyiben egyezett; a negyediknél már a
>   tartalom kezdődik (annál hosszabb ujjlenyomat két azonos mozdulatot különbözőnek
>   látna). Kettő viszont összemosná az `own_practice` („I've found") és az
>   `encountered` („I've run into") formát — az két *különböző* ajánlott mozdulat.
> - **Miért csak az első mondat:** a szabály a retorikai mozdulatot méri, azt az első
>   mondat hordozza. A második már tartalom, ott két komment joggal indulhat hasonlóan.
> - **Miért ugyanolyan mély a két gyűrű** (`_OPENING_ECHO_RING_SIZE =
>   _OPENING_RING_SIZE = 4`): különben egymás ellen dolgoznának. A forma-gyűrű 4
>   híváson át kizárja a használt formát; egy **mélyebb** visszhang-gyűrű olyan
>   formát is büntetne, amit a rotáció joggal ad ki újra. Egyetlen számmal a két
>   szabály definíció szerint konzisztens.
> - **Ismert korlát:** a feloldott alak más ujjlenyomat („i have found" ≠ „i ve
>   found"). Fail-open — legfeljebb átengedi az ismétlést, hibás sértést nem ad.
>
> ### ÉLES A/B — ugyanaz az 5 poszt, közvetlenül utána
> | | v8 (előtte) | v9 (most) |
> |---|---|---|
> | különböző nyitás | **3/5** (három komment azonos) | **5/5** |
> | sáv-betartás | 5/5 BENT | 5/5 BENT |
> | `rewrites` | 1/5 | 2/5 (egyet a **visszhang-kapu** váltott ki) |
>
> A kapu élesben is pontosan úgy működött, ahogy kell: az 05-ös poszt első köre
> „I've found…"-dal indult, ami az 01-es komment nyitásával egyezett → újraírás →
> a második kör „One pattern I've noticed…" lett, vagyis **a neki kiosztott
> forma** (`pattern`). Nem elnyomott, hanem visszatérített.
>
> **A költség egy újraíró hívás/ütközés** — ugyanaz a nagyságrend, mint a többi
> kapunál (5/22 sor a teljes naplóban). Kapcsolóval jött be
> (`linkedin.opening_echo_gate`), és mérhető: `opening_fingerprint` +
> `opening_echo_recent` a naplóban, `bench_report.py` §4 mutatja.
>
> ### Amit ez a köteg MÉG mutatott (nyitva marad)
> - **`constructive_challenge`: 0/22.** A 02-es poszt volt rá az ideális eset
>   (vitatható tézis + záró kérdés) — `field_experience` nyert. Ez már nem „nem volt
>   alkalom": vagy explicit trigger kell neki, vagy a stratégia halott.
> - **Nyers max = végső győztes v9-ben 4/5** (v8: 4/7, v5: 0/5). A horgonyzás tartja
>   magát; a bias nudge, nem teherhordó.
> - **`anchors_added` 0 tizenkilencből tizenkétszer** — de a v9 köteg hozta az első
>   **4-es** horgony-számot (03, `business_impact`, `business` sík). Az `abstract_count`
>   lecsökkent (átlag 2.8), a **hedges viszont felment** (átlag 2.1, egy esetben 5) —
>   a hígító átvándorolt, nem eltűnt. Ez a következő gyanúsított.
>
> ### Második köteg (5 poszt) — amit a kapu hozott, és amit kijátszott
> - **`future_outlook` először nyert** (CADENA-poszt, `industry_news`/`technical`,
>   69 szó → 52 szó, abstract 0, hedges 0). Már csak a `constructive_challenge` és a
>   `systems_thinking` nem nyert soha (a `missing_perspective` tervezetten nem).
> - **A visszhang-kapu kétszer elsült** ugyanabban a kötegben: két komment is „What
>   strikes me"-vel indult volna egy harmadik után. Futáson belüli szórás:
>   1. köteg **5/5**, 2. köteg **4/4** különböző nyitás.
> - **MÉRT KIJÁTSZÁS (n=1):** az egyik posztnál az első kör blokkolva → a második
>   kör „We often see"-vel indult → **az is** sértés → a ciklus `range(2)`, tehát a
>   komment **sértéssel jött vissza** (`quality_issues` nem üres — a napló mutatja).
>   A végleges nyitás „What's **compelling** about…" lett: retorikailag ugyanaz a
>   mozdulat, más ujjlenyomat. **Az ujjlenyomat lexikai, a mozdulat szemantikai** —
>   ugyanaz a hibaosztály, amit a `post_overlap`-nál már kimondtunk.
>   Kész, hívásba nem kerülő javítás lenne: a blokkolt ujjlenyomatot a compose-
>   promptba adni tiltásként (prevenció retry helyett). **Szándékosan NEM most:**
>   n=1, és a saját szabályunk szerint háromszor kell visszatérnie.
>
> ### A magyar ág — az első mérés (`--force`, vendor-hirdetés alatt)
> A poszt magyar és vendor-hirdetés volt (igazolt CTA-idézet), tehát a motor
> kihagyta; user-döntésre `--force`-szal lefutott. **Amit jól tett:** a komment
> magyarul jött (a nyelvillesztés kód nélkül is áll), a kiosztott `pattern` forma
> érvényesült, a sáv 65-110 → 76 szó.
>
> **Három mért hiányosság, mind a magyar oldalon:**
> 1. **EKEZET-HIBA az ujjlenyomatban (javítva).** Az első változat `[^a-z0-9]`-t
>    használt, ami az ékezetes betűt szóhatárnak vette: „Egy visszatérő mintát
>    látok" → `'egy visszat r'`, vagyis három szó helyett másfél, és a fragmentumok
>    között sokkal könnyebb a hamis egyezés. Javítás: NFKD-hajtogatás
>    (`_fold_accents`) → `'egy visszatero mintat'`. Melléknyereség: az ékezet nélkül
>    írt változat ugyanazt az ujjlenyomatot adja. Tesztek: I6.1, I6.2.
>    **A naplóban egy sor** (a magyar futás) hordozza a régi, töredékes értéket —
>    azonosítható, ezért `TELEMETRY_SCHEMA` nem emelkedik miatta.
> 2. **A magyar szótár vékonyabb, mint az angol.** A komment második mondata „A
>    gyakorlatban azt tapasztaljuk…" — ez pontosan az `in practice` sablon, ami
>    ANGOLUL sértés (`_STOCK_OPENING_PATTERNS`), magyarul nincs a listán. A HU-oldal
>    két bejegyzést tartalmaz, az EN-oldal tizenhármat: ugyanaz a tanácsadói reflex
>    magyarul átmegy.
> 3. **A komment megdicsérte a hirdetőt:** „a Vantasec által képviselt … valóban
>    sokkal árnyaltabb képet ad". Épp az az ingyen-engagement, ami ellen a
>    vendor-skip készült; a `_FORBIDDEN_PATTERNS` magyar dicséret-mintái ezt a
>    szerkezetet nem fogják. (A komment ezután tett érdemi ellenvetést — az auditor-
>    felkészültség szűk keresztmetszetét —, tehát nem üres egyetértés volt.)
>
> **A `concreteness` a magyar/nem-AEC sorokra NEM informatív:** a horgony- és
> absztrakció-lexikon angol és BIM-specifikus, ezért ott az `anchors_added: 0` nem
> jelez semmit. A későbbi korrelációból ezeket a sorokat ki kell zárni.
>
> **Válasz-szerződés:** a 8 legacy mező változatlan; új additív mezők:
> `opening_fingerprint`, `opening_echo_recent`. `TELEMETRY_SCHEMA` **nem** emelkedik
> (tisztán additív). Új teszt-szekció: `test_linkedin_opening.py` I1–I20 + I6.1-I6.2.
> A `reset_opening_state()` a két gyűrűt egyben nullázza — ez nem kényelmi függvény:
> a visszhang-gyűrű bejövetelekor három meglévő teszt azonnal elbukott, mert csak a
> forma-gyűrűt nullázták.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — Tanácsadó-hang kapu (engine v10)
>
> ### A mérés: a frázis kihátrált az ablakból
> A harmadik köteg után a teljes napló átvizsgálása egyetlen szerkezetet emelt ki
> minden más fölé:
>
> | alak | találat |
> |---|---|
> | „We've often found" | 5 |
> | „We often see" | 4 (ebből **2 a 3. mondatban**) |
> | „We often rebuild" | 1 |
> | **összesen** | **10 / 32 kiadott komment (31%)** |
>
> **Miért nem fogta semmi:** a `_STOCK_OPENING_PATTERNS` szándékosan csak az első
> **két** mondatot méri (2026-08-10-i döntés: „egy sablonos fordulat a 8. mondatban
> nem *nyitási* hiba"), és a v9 két kommentjében a frázis pontosan a **3.** mondatban
> állt. Közben sem az `_AI_FINGERPRINT_PATTERNS`-ben (szerzőhöz relativizált, ≥2
> találat kell), sem a `_MARKETING_CLICHE_PATTERNS`-ben nem volt.
> **Nem az ablak volt szűk — a szótár volt hiányos.**
>
> ### A döntés: külön lista, egész kommentre, feltétel nélkül
> `_CONSULTANT_VOICE_PATTERNS`. Ugyanaz az érv, mint a marketing-kliséé: a tanácsadói
> általánosítás („mi gyakran azt látjuk…") nem szint-függő hiba — semmilyen síkon nem
> jó írás, mert **megnevezetlen tapasztalatra hivatkozik konkrétum helyett.** A
> szerzőhöz relativizálás itt nem kell: ez retorikai állás, nem szakszó, amit a szerző
> „engedélyezhetne".
>
> **Ami SZÁNDÉKOSAN kimaradt** — ez a lista fele:
> - **„One pattern I've noticed" (4 találat):** ez a *saját katalógusunk* `pattern`
>   formája. Tiltani ugyanaz az önellentmondás, amit a G1 teszt őriz; az ismétlést a
>   v9-es visszhang-kapu kezeli. A G1 mostantól az új listát is átvizsgálja.
> - **„the real work / challenge / hit / advantage" (8 találat):** a számok alapján
>   indokolt *lehetne* — de a v7-es A/B-ben éppen egy ilyen mondat volt a sorozat első
>   vágás nélkül kiposztolható kommentjének magja („the real hit is often downstream").
>   Ez **tartalmi szerkezet, nem tic.** A záró mondat ismétlődése cross-komment
>   jelenség, tehát ha kell, a visszhang-kapuhoz hasonló mechanizmus a helyes válasz,
>   nem szótár. Teszt rögzíti, hogy nem sértés (F13).
> - **„in our experience": nulla találat** — mérés nélkül nem veszünk fel semmit.
>
> **Egy dolog mérés NÉLKÜL került be:** az első személyű változat („I've often
> found"). Indok a 2026-08-10-i szótár-ragozás javításának érve: a pronomén-csere a
> legkézenfekvőbb kijátszás **ugyanarra a szerkezetre**, és a `standardizing` ≠
> `standardi[sz]ation` tanulság épp az volt, hogy a hiányos alaklista alulszámol.
> **Nem ütközik** az `own_practice` formával („I've found…"): a minta megköveteli az
> általánosító határozót a két szó között — a tic az „often", nem a tapasztalat-ige.
> Tesztek: F9, F10.
>
> **Magyar:** a `--force`-os magyar futás 2. mondata szó szerint „A gyakorlatban azt
> tapasztaljuk…" volt — ugyanaz a mozdulat. A minta megköveteli a tapasztalat-igét,
> mert a „gyakorlatban" önmagában legitim („a gyakorlatban ez 10 mm"). Teszt: F11, F12.
>
> ### ÉLES — az első futás a kapuval (Conduit-poszt, `--force`)
> Az első kör **hármas sértést** kapott:
> `tanacsadoi hang (We often see/found)` + `ismetlodo nyitas (We often see)` +
> `AI-ujjlenyomat (governance, standardisation, consistency)`. Az újraírás után:
> 112 szó (sáv 90-150), `abstract_count: 1`, `hedges: 1`, `quality_issues: []`.
> A végső kommentben megmaradt a `robust` — **egyetlen** fingerprint-találatként,
> tehát a ≥2 küszöb tervezetten átengedte.
>
> ### A harmadik köteg további mérései
> - **`systems_thinking` először nyert** (magyar LPM-poszt, `engineering_problem` /
>   `technical`). Innentől **csak a `constructive_challenge`** nem nyert soha —
>   33 generálásból egyszer sem, pedig két ideális poszt is volt rá.
> - **ELSŐ SÁV-VÉTÉS: 24/25.** A magyar poszt 277 szó → sáv 90-150 → **85 szó**.
>   Nem modell-hiba: a magyar agglutinál, ugyanaz a tartalom kevesebb szó. **A sáv
>   nyelv-vak** — a tükrözés angol szószámra kalibrált. NYITOTT, n=1, de a mechanizmus
>   egyértelmű; a javítás iránya nyelv-érzékeny szorzó vagy karakter-alapú mérés.
> - **A szemantikai kijátszás másodszor (n=2):** a 12-es komment „What strikes me
>   about this…"-szal indult, a 13-as első mondata pedig „…and **what strikes me** is
>   how much inertia…" — más ujjlenyomat, tehát átment. A mozdulat ismétlődik, a
>   lexikai ujjlenyomat nem fogja. Egy híján a 3× küszöb.
> - A regiszter-kapu dolgozott: egy kommentnél `consistency, robust` → újraírás →
>   `abstract_count: 0`.
>
> **Válasz-szerződés:** változatlan (a lista a meglévő `quality_issues`-ba ír).
> `TELEMETRY_SCHEMA` nem emelkedik. Új tesztek: `test_linkedin_concreteness.py`
> F6–F13; a G1 önvédelem kiterjesztve az új listára.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — Nyitó-keretek és a nyelv-mérés (engine v11)
>
> ### 1. A szemantikai kijátszás: kanonizálás, nem tiltás
> **A mért eset (n=2):** a v9-es kapu blokkolta a „What strikes me"-t, a modell
> második köre pedig „What's **compelling** about Frank's approach…"-szal indult.
> Három szó szerint más ujjlenyomat, retorikailag **ugyanaz a mozdulat**.
>
> `_OPENING_FRAMES` → `frame:notable`. **A megoldás nem tiltás, hanem kanonizálás,**
> és ez a különbség dönti el, miért nem esik a szótár-csapdába: a kifejezés továbbra
> is **használható** (a `strikes` a saját katalógusunk formája), csak az **ismétlése**
> látható. Egy keret-családba eső két egymás utáni nyitás ugyanazt az ujjlenyomatot
> adja, akárhogy variálja a szavakat.
>
> **A két mechanizmus szerződése** (`shape_frame` / `echo_ring_for`): a keret
> megbontotta a gyűrűk szimmetriáját. A forma-gyűrű 4 híváson át kizárja a `strikes`
> formát, de egy **más** formát kapott komment is elhasználhatja a keretet — mérve: a
> 12-es komment `stood_out` kiosztással indult „What strikes me"-vel. Ha ezután a
> rotáció kiadja a `strikes`-ot, a modell a **saját utasítása** miatt kapna sértést.
> Ezért a kiosztott forma saját kerete kimarad a kapunak átadott gyűrűből: **az
> utasítás erősebb, mint a visszhang-tilalom.** Tesztek: J6–J9.
>
> **Szándékos korlát:** csak az első mondat **elején** kanonizálunk. A 13-as komment
> („I've run into similar challenges…, and what strikes me is…") megtartja a saját
> `i ve run` ujjlenyomatát — a *nyitása* valóban más mozdulat volt (J3).
>
> ### 2. A nyelv-mérés — és amit SZÁNDÉKOSAN NEM csináltam
> A nyelv szerinti bontás után a „sáv-vétés" képe megfordult:
>
> | | sávon belül |
> |---|---|
> | angol sorok | **23/23** |
> | nem-angol | 1/2 (a magyar LPM-komment: 85 szó, padló 90) |
>
> **Angol oldalon nincs mit javítani** — a hiba kizárólag a nem-angol kalibrációnál
> jelent meg. **Nyelv-érzékeny szorzót mégsem tettem be**, és ez tudatos döntés: két
> magyar sorunk van (egy BENT, egy 5 szóval a padló alatt), a szorzó száma tehát
> **találgatás lenne** — pontosan az, amit a v7 óta minden blokk tilt („igazolatlan
> számokra ne építsünk"). Ráadásul **a sáv nem kapu**: a 85 szavas komment semmilyen
> újraírást nem váltott ki, a `MIN_WORDS` 35 — vagyis a „vétés" eddig csak a *riport*
> oszlopában létezett, a kimenetben nem.
>
> **Amit helyette csináltam — a mérés hiányzott, nem a mechanizmus:** a napló eddig
> egyáltalán nem tudta, milyen nyelven ment ki a komment, pedig a mérőszámaink fele
> angolra kalibrált. Új additív mezők: `post_language`, `reply_language`
> (a meglévő `looks_english`-ből — determinisztikus, és a kérdés binárisan az, hogy
> „állnak-e erre a sorra az angol kalibrációk"). A `bench_report.py` §2 nyelv szerint
> bont, §3 pedig a **nem-angol sorokat kihagyja**: a horgony-lexikon angol és
> BIM-specifikus, ott az `anchors_added: 0` nem jelez semmit. A v11 előtti sorokra a
> riport a `reply_text`-ből **visszamenőleg** számol nyelvet, tehát a mostani 33 sor
> is azonnal szegmentálható.
>
> **Ez a döntés visszavehető:** ha összejön 8-10 magyar sor és a padló alatti minta
> megismétlődik, a szorzó **mért** számmal jön be, nem becsléssel.
>
> **Válasz-szerződés:** új additív mezők `post_language`, `reply_language`;
> `TELEMETRY_SCHEMA` nem emelkedik. Az `opening_fingerprint` értékkészlete
> **bővült** (`frame:*` alakok) — a jelentése („a nyitás ujjlenyomata") változatlan,
> ezért ez sem séma-emelés. Új tesztek: `test_linkedin_opening.py` J1–J9, K1–K2; az
> I1/I3/I7/I8/I12/I13 várt értéke a v9-es szó szerinti alakról a keretre frissült
> (az állítás ugyanaz maradt).

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — A `constructive_challenge` (engine v12)
>
> ### A diagnózis megfordította a feltevést
> **Két állítás dőlt meg egyszerre.**
>
> **(a) A „bias-terv" nem létezett.** A `config.yaml` és a korábbi blokkok arra
> hivatkoztak, hogy a CC „vélemény- és debate-poszton nyerhetne a bias-terv szerint".
> A kódban ez **nincs így**: a `professional_opinion` és az `industry_debate` intent
> bias-a a CC-re **nulla**, miközben **nyolc** másik intent MÍNUSZT ad neki
> (`reflection` −2, `announcement` −3, `portfolio_showcase` −2 …), és pozitívat
> egyedül a `product_demonstration` (+1). A dokumentáció egy soha meg nem írt tervre
> hivatkozott. Javítva.
>
> **(b) A bias nem is javíthatta volna.** 33 sor aritmetikája:
>
> | | |
> |---|---|
> | CC nyers pontja | min 3, max **7**, átlag 5.45 — **egyszer sem** ment 7 fölé |
> | a győztes pontja | **9 a 33 sorból 32-ben** |
> | szükséges bias-emelés | +2.0 … +9.5 (átlag 4.4) |
> | sor, ahol 1 pont elég lenne | **0** |
>
> Egy ilyen bias már nem nudge, hanem **teherhordó** — amit a v8 döntés kizár. A
> javítás ezért a skálán van, nem a súlyokon.
>
> ### A valódi ok: a `wins_when`-ek nem egyenlő szélességűek
> A győztes-eloszlás **nem a posztokat követte, hanem a győzelmi feltétel
> teljesíthetőségét.** A három legszélesebb vitte a 33 döntésből 31-et:
> `field_experience` („a poszt elméleti, a gyakorlat más" — LinkedIn-en majdnem
> mindig igaz), `practical_lesson` („diagnosztizál, de nem ad teendőt"),
> `business_impact` („technikai marad, az üzleti következmény kimondatlan").
> A CC feltétele volt a legszűkebb: **kimondatlan feltételt** kellett találni, míg a
> többieknek egy felismerhető **állapotot**.
>
> **Két prompt-oldali javítás** (a v8-as horgonyzás mintájára, ami 0/5 → 9/15-öt hozott):
> 1. A CC `wins_when`-je ugyanarra a szintre: „a poszt a központi állítását általánosan
>    mondja ki, és van gyakori eset, amikor nem áll". Ugyanaz a szakmai tartalom,
>    felismerhető állapotként.
> 2. Új horgony a REASON-promptban: *„DISAGREEMENT IS NOT A RISK YOU ARE MANAGING…
>    scoring it 6-7 to stay safe is the known failure of this step."*
>
> ### ÉLES A/B — négy poszt, ugyanaz a szöveg
> | poszt | CC előtte | CC most |
> |---|---|---|
> | Archicad/Forma | 7 | 7 |
> | BIM = building's brain | 7 | **8** ← az első 7 fölötti érték a korpuszban |
> | ISO 19650 | 4 | **6** |
> | BIM-tanácsadó tudás | 7 | 6 |
>
> **A plafon megtört, a döntés nem.** A CC továbbra sem nyert egyszer sem: a győztes
> minden sorban 9, vagyis a modell a 9-est **rangsor-címkeként** használja, nem
> absztolút értékként. Egy stratégia nem tud „felkapaszkodni" 9-re; csak az lehet 9,
> amit a modell elsőnek választ.
>
> ### A döntő mérés: KÉNYSZERÍTETT CC (`bench_linkedin.py --strategy`)
> Ha sosem nyer, jobb lenne-e a komment, ha mégis ő írná? Ezért kapott a **mérési
> script** (nem a motor) egy stratégia-override-ot.
>
> | | természetes győztes | kényszerített CC |
> |---|---|---|
> | Archicad/Forma | `field_experience`, hedges 4 | 118 szó, abstract 3, hedges 3 |
> | BIM brain | `future_outlook`, 91 szó, abstract 4, `rewrites: 2` | **109 szó, anchors 1 (IFC), hedges 0, `rewrites: 0`** |
>
> **Archicad:** a két komment **ugyanazt** az érvet hozza (a fee/incentive-struktúra
> nem jutalmazza a strukturált adatot) — a CC-változat csak becsomagolja egy
> engedmény-majd-ellenvetés keretbe („The post rightly points out…"), ami filler.
> Itt a CC **nem adott többet.**
>
> **BIM brain:** a CC-változat **jobb** — megnevezi a konkrét standardot (IFC), nulla
> hedge, nulla újraírás, és pont azt a kimondatlan feltételt találja meg, amin a
> poszt tézise áll (kétirányú, valós idejű adatcsere). A természetes `future_outlook`
> ezzel szemben a poszt saját vízióját mondta újra + generikus komplexitást.
>
> **Következtetés: a CC NEM redundáns — a probléma a KIVÁLASZTÁS.** A stratégia a
> megfelelő poszton a korpusz legjobb regiszter-értékeit adja, de a pontozó lépés
> nem rangsorolja elsőnek. Törölni tehát hiba lenne (a forced-CC bizonyíték ellene),
> és bias-szal sem fixálható (az aritmetika ellene).
>
> ### NYITOTT — a javaslat: szenzor a pontszám helyett
> A projekt saját mintája (`explicit_tool_request` + igazolt idézet → márkaemlítés):
> **a modell szenzor, a kód bíró.** A CC-hez ugyanez kellene: a REASON adjon vissza
> egy `thesis_quote`-ot (SZÓ SZERINT a posztból, tehát kódból ellenőrizhető) és egy
> `thesis_condition`-t (a gyakori eset, ahol az állítás nem áll). Ha mindkettő megvan
> és az idézet tényleg szerepel a posztban, a **kód** dönt CC mellett — nem a
> pontszám. Ez nem új súly, hanem új tény.
>
> **Két másik nyitott, ami itt jött elő:**
> 1. A compose-ciklus `range(2)`, tehát két elutasítás után a komment **sértéssel megy
>    ki**. Két ilyen sor van (`ismetlodo nyitas (We often see)`, illetve
>    `tanacsadoi hang (We often see/found)` a végső `quality_issues`-ban). Külön döntés
>    kell: harmadik kör, vagy tudatosan vállalt hiba.
> 2. **A v10-es lista első kijátszása (n=1):** az egyik v12-es komment „**We also
>    see** that consistent onboarding…"-gal írta ugyanazt a mozdulatot. Az `also`
>    SZÁNDÉKOSAN nincs a listán: az „often/frequently/…" általánosító határozó, az
>    `also` viszont legitim hozzátétel is lehet („we also see this in the schedules").
>    A 3×-szabály szerint várunk — de a következő ilyen már minta.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — Kihívás-szenzor (engine v13)
>
> ### A megoldás alakja: nem új súly, hanem új tény
> A v12 diagnózisa kizárta a bias-utat (a CC-nek +2..+9,5 kellett volna, ami már
> teherhordó súly) és a törlést is (kényszerített CC-vel a korpusz legjobb
> regiszter-értékét adta). A hiba a **kiválasztásban** volt.
>
> A projekt saját mintája (`explicit_tool_request` + igazolt idézet → márkaemlítés):
> **a modell szenzor, a kód bíró.** Két új REASON-mező:
> - `thesis_condition` — EGY gyakori eset, ahol a poszt tézise nem áll. A prompt
>   kimondja, hogy az **üres válasz érvényes és gyakori** („do not invent a condition
>   to fill this field") — különben a mező kitöltési kényszert teremtene, és a CC
>   az egyik degenerált eloszlásból (soha) a másikba esne (mindig).
> - `thesis_quote` — az állítás **szó szerint** a posztból. A kód megkeresi
>   (`_quote_in_post`), és ha nincs ott, a feltétel érvénytelen.
>
> `challenge_override()` — öt ellenőrizhető feltétel, mindegyik saját indokkal a
> naplóba: vélemény-jellegű intent (`professional_opinion` | `industry_debate`),
> nem üres `thesis_condition`, **igazolt** idézet, a modell maga is
> ≥ `CHALLENGE_FIT_FLOOR` (=7) pontot adott a CC-nek, és a szint nem vetózza.
>
> **Miért 7 a padló:** ez a CC **történelmi maximuma** 33 soron. Így a kód a
> rangsor-artefaktumot javítja, nem a modell ítéletét írja felül — ha a modell maga
> is alacsonyra tette, a szenzor hallgat.
>
> **Az idézet-padló szigorúbb, mint a tool-requestnél** (`THESIS_QUOTE_MIN_WORDS`=6
> a 3 helyett): egy tézis ÁLLÍTÁS, alany és állítmány kell hozzá. Ezt a teszt találta
> meg — a „the concept model" három szóval átment, holott az főnévi szerkezet (K5.1).
>
> ### ÉLES — négy poszt, és a hatás nagyobb, mint a szenzor
> | poszt | `pick_strategy` | végső | CC_fit (előtte → most) |
> |---|---|---|---|
> | Archicad/Forma | `constructive_challenge` | CC | 7 → **9** |
> | BIM brain | `business_impact` | **CC (override)** | 7 → **9** |
> | BIM-tanácsadó | `field_experience` | **CC (override)** | 7 → **8** |
> | MEP-koordináció | `missing_perspective` | változatlan | 6 → 9 |
>
> **A CC plafonja teljesen eltűnt: 9, 9, 8, 9 — a korábbi 33 soros maximum 7 volt.**
> És ez nem a szenzor műve: azért történt, mert a `thesis_condition` kérdés a
> pontozás **ELŐTT** van. Mire a modell pontoz, már megtalálta a kimondatlan
> feltételt — vagyis a tényt, ami a CC-t indokolja. A szenzor csak kettőt fordított
> meg a négyből; a harmadikat a modell magától választotta.
>
> **Ahol NEM sült el, jól nem sült el:** a MEP-poszt `case_study` intentet kapott
> (nem vélemény), a napló indoka szó szerint ezt mondja. A CC ott is 9-es fitet
> kapott, de a `missing_perspective` 10-esből 9,5-öt vitt (a `case_study` intent
> **+1,0**-t ad a fallbacknek, ami a globális −1,5-öt részben ellensúlyozza) — ez a
> fallback első győzelme a korpuszban, és a számítás helyes.
>
> ### ÚJ, MÉRT HIBA — a tartalmi mozdulat összeomlott
> Mindhárom CC-komment **ugyanoda** futott ki: szerződés / incentíva-struktúra.
> „if there isn't a clear contractual ask for structured data" · „the inherent shift
> in contractual frameworks it implies" · „the contractual structure itself plays a
> role here". A stratégia diverzifikálódott, a **tartalmi mozdulat viszont nem** — és
> ez ugyanaz a hibaosztály, mint a nyitás-visszhang: cross-komment ismétlés, amit
> egyetlen kapu sem mér. Egy negyedik, korábbi kötegben is felbukkant („payment
> milestones"), tehát ez már **4 találat**. Ez a következő javítás jelöltje, és a
> nyitás-keret precedens szerint a válasz nem szótár, hanem kanonizált
> **tartalom-ujjlenyomat** a gyűrűben.
>
> **Amit figyelni kell:** a `professional_opinion` a korpusz 27%-a. Ha a szenzor ott
> szinte mindig elsül, a CC 0%-ból ~27%-ba ugrik. A négyes mintában 3/4 lett — ez
> kevés a következtetéshez, de sok ahhoz, hogy ne figyeljük. A fék a hármas kapu
> (intent + igazolt idézet + 7-es padló), és mind a három mérhető a naplóból.
>
> **Válasz-szerződés:** új additív mezők `thesis_condition`, `thesis_quote`,
> `challenge_override`, `challenge_reason`, `strategy_before_override`;
> `TELEMETRY_SCHEMA` nem emelkedik. A REASON-séma két új KÖTELEZŐ mezőt kapott (a
> prompt-tételek 1–24-re számozódtak át, folytonosan — A13 őrzi). Új tesztek:
> `test_linkedin_intent.py` K1–K13.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — Harmadik kör és a tartalmi visszhang (engine v14)
> **Az egyik javítás bevált, a másiknak NEGATÍV eredménye van. Mindkettő itt marad,
> mert a negatív mérés is mérés — ez az authenticity-rubrika tanulsága.**
>
> ### 1. A `range(2)` plafon → harmadik kör, de csak ismétlés-osztályra
> **A mért hiba:** négy komment sértéssel ment ki (28., 38., 49., 50. sor), és a
> mintázat mindig ugyanaz: az 1. kör „We often see"-re bukott, a 2. kör pedig
> **ugyanannak a mozdulatnak más alakját** hozta („I often find"). A modell változatot
> cserélt, nem viselkedést.
>
> Két javítás egyszerre, mert külön nem hat:
> - `MAX_COMPOSE_ATTEMPTS = 3`, de a harmadik kör **csak** akkor jár, ha a maradék
>   sértés kizárólag `_REPHRASABLE_PREFIXES`-be esik (nyitás-ismétlés, tanácsadói
>   nyitás, tanácsadó-hang). Ezek a HOGYAN, nem a MIT — a javítás biztosan lehetséges.
>   A négy mért eset mindegyike ebbe az osztályba esett (teszt: L15).
> - **Akkumulált sértés-lista:** a modell mostantól MINDEN korábbi kör sértését látja,
>   nem csak az utolsóét. Enélkül nem tudja, hogy az előző alak is tilos.
>
> **Élesben működik:** egy komment három kört futott, és a tanácsadó-hang eltűnt a
> végleges szövegből. (Ugyanaz a futás viszont a 3. körben új ismétlésre esett, tehát
> a plafon feljebb került, nem tűnt el.)
>
> ### 2. Tartalmi visszhang-kapu — DETEKTÁL, DE NEM GYÓGYÍT (`content_echo_gate: 'off'`)
> **A mért hiba:** hét CC-kommentből hat ugyanoda futott ki (szerződés/incentíva).
> A nyitás-keret precedensét követve: kanonizált `move:*` ujjlenyomat + gyűrű,
> a `business_impact` stratégia kivételével (ott a kereskedelmi keret az utasítás).
>
> **Öt éles futás ugyanazon a poszt-készleten — a verdikt:**
>
> | | |
> |---|---|
> | a kapu elsült | 3 kommentnél |
> | ebből sértéssel kiment | **2** (tartalmi hibára nem jár harmadik kör) |
> | elhagyta a kereskedelmi keretet | **0** |
> | lexikailag kicsúszott | **2** („design fees aren't always structured" — ugyanaz a mozdulat, más szavakkal, `content_move` üres) |
>
> **A VALÓDI OK FELJEBB VAN, és a napló bizonyítja.** Az öt `thesis_condition`-ből
> **öt** szerződési/incentíva-jellegű:
> - „when project contracts do not explicitly reward or penalize data quality…"
> - „when the contractual frameworks and operational incentives align…"
> - „when the client's procurement process does not explicitly define and compensate…"
> - „when the contractual and liability frameworks for AI-generated design…"
> - „when project contracts and team incentives are aligned to reward early…"
>
> A v13-as kihívás-szenzor kérdésének („nevezz meg egy esetet, ahol az állítás nem
> áll") **hatalmas attraktora van**, és a compose-kapu egy olyan döntés ellen küzd,
> ami a REASON lépésben már megszületett. **Kimeneti kapu nem javít bemeneti
> monokultúrát** — ez a mérés fő tanulsága, és ugyanaz a hibaosztály, mint amikor a
> `post_overlap` a betűt mérte a mondanivaló helyett.
>
> **Ezért a kapu KI van kapcsolva, a MÉRÉS marad.** A `content_move` és a
> `content_echo_recent` kapcsoló nélkül is a naplóba kerül — épp ez mutatta ki a
> monokultúrát. Ami leáll, az a kapuzás: egy extra LLM-hívást fizet, és a sértés
> ugyanúgy kimegy. Ez a projekt saját „removal-friendly" elve: egy kapu, ami nem
> gyógyít, ne kapuzzon.
>
> **A NYITOTT JAVÍTÁS ezért a REASON szintjén van:** a `thesis_condition`-t kell
> elterelni a kereskedelmi alapértelmezésről (a feltétel legyen technikai, helyzeti
> vagy szervezeti, kivéve ha a poszt maga a kereskedelmi feltételekről szól), vagy a
> legutóbbi feltételeket kizárásként átadni a REASON-promptnak.
>
> **Egy harmadik sáv-vétés is jött** (angol, CC-komment: 77 szó a 80-as padló alatt).
> Immár három: magyar (nyelv-kalibráció), listás poszt (szó ≠ tartalom), és ez.
> A sáv továbbra sem kapu — a `MIN_WORDS` 35.
>
> **Válasz-szerződés:** új additív mezők `content_move`, `content_echo_recent`;
> `TELEMETRY_SCHEMA` nem emelkedik. Új tesztek: `test_linkedin_opening.py` L1–L17.
> `reset_opening_state()` mostantól MINDHÁROM gyűrűt nullázza.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — A feltétel-monokultúra (engine v15)
>
> ### A v14 tanulsága volt a kiindulás
> „Kimeneti kapu nem javít bemeneti monokultúrát." A `thesis_condition` öt éles
> futásból ötször szerződési/incentíva-jellegű volt, ezért a javítás oda került,
> ahol a döntés születik. **Két rész, mert külön egyik sem elég:**
>
> **1. PROMPT — a mért attraktor megnevezése.** *„AVOID THE MOST AVAILABLE ANSWER.
> 'When the contracts or the incentives are not aligned' is a real condition, but it
> fits almost every claim in this industry, which is exactly what makes it worth
> little to the author."* Plusz a kívánt irány kimondása: technikai állapot (export-út,
> séma, verzió, koordináta-rendszer), projekt-helyzet (felújítás, később belépő
> szakág, fázishatár) vagy szervezeti tény (kinél van a modell, ki van a helyszínen).
> Ugyanaz a technika, ami a v8-as kalibrációs ellenőrzésnél és a v12-es
> „disagreement is not a risk" horgonynál bevált.
>
> **2. BÍRÓ — a kód nem hisz a jóindulatnak.** Ha a feltétel **családja** megegyezik a
> legutóbbi **elfogadott** feltételekével, a feltétel nem számít ténynek → a szenzor
> nem sül el (`challenge_override` 6. feltétele). Ez a **következő** attraktort is
> kezeli, bármi legyen az. A gyűrű csak elfogadott feltétellel bővül: egy el nem sült
> szenzor feltétele nem befolyásolt kommentet.
>
> **Küszöb-különbség, dokumentálva:** a feltételnél **1** találat elég
> (`_CONDITION_FAMILY_MIN_HITS`), a kommentnél **2** kell — a feltétel egy tagmondat,
> ott az első kereskedelmi terminus már a lényeg; egy 100+ szavas kommentben egy futó
> említés még nem a mozdulat.
>
> **A teszt megint hiányt talált a lexikonban:** a mért feltételek egyike
> „the client's **procurement** process does not explicitly define and **compensate**"
> volt, és a lista egyiket sem tartalmazta; a v14-es lexikai kicsúszás pedig a puszta
> „design **fees**" volt. Mindhárom bekerült — ugyanaz a szótár-hiányosság, mint a
> 2026-08-10-i ragozás-javításnál: a hiány **alulszámol**.
>
> ### ÉLES — ugyanaz az öt poszt, ahol öt/öt szerződési volt
> | | v13/v14 | most (v15) |
> |---|---|---|
> | kereskedelmi `thesis_condition` | **5/5** | **2/5** |
> | kereskedelmi `content_move` a kommentben | 5/5 | **1/5** |
> | a bíró-szabály elsült | – | **2×**, mindkettő ismétlődő feltételre |
>
> **Amit a két új feltétel hozott** (ezek a prompt eredményei, nem a bírói szabályé):
> - BIM-brain: *„semantic interoperability … it's one thing to link a COBie
>   spreadsheet to a maintenance platform, but another to have the model inherently
>   understand the real-time operational state"* — `anchors: 1`, `hedges: 0`.
> - Agentic BIM: *„the real challenge isn't the solver's ability to generate viable
>   geometry, but the formalisation of 'intent' itself … a complex web of conflicting,
>   ambiguous and evolving requirements when you break it down into computable
>   constraints"* — a korpusz legjobb kihívása erre a posztra.
>
> **A bíró kétszer dolgozott, mindkétszer helyesen:** a BIM-tanácsadó posztnál a
> feltétel ismét szerződési volt → a szenzor nem sült el → a stratégia
> `field_experience` maradt, pedig a nyers maximum a CC volt.
>
> ### AMIT EZ NEM OLDOTT MEG (nyitott)
> - **A monokultúra csökkent, nem szűnt meg:** 2/5 feltétel és 1/5 komment továbbra is
>   kereskedelmi. Egy komment (Archicad) a lexikonon átment, de érdemben még mindig
>   költség-érv („general overhead", „project contingency", „internal cost driver") —
>   a mérő itt is a szót fogja, nem a mozdulatot.
> - **A CC aránya magas marad (4/5 vélemény-poszton), és már NEM a szenzor miatt:**
>   ebből a négyből hármat a `pick_strategy` maga választott. A v13-as
>   `thesis_condition`-kérdés melléktermékként megnövelte a CC nyers pontját, és az
>   maradt. Ha ez túl sok, a padló (`CHALLENGE_FIT_FLOOR`) nem segít — a nyers
>   pontozás kalibrációját kell megnézni.
> - **Intent-instabilitás:** ugyanaz a poszt egyik futáson `professional_opinion`,
>   máskor `reflection` (`reason_temperature` 0.2, nem 0). Ez az osztályozás ismert
>   szórása, de a szenzor MŰKÖDÉSÉT eldönti — érdemes mérni, milyen gyakori.
>
> **Válasz-szerződés:** új additív mezők `condition_family`, `condition_echo_recent`;
> `TELEMETRY_SCHEMA` nem emelkedik. Új tesztek: `test_linkedin_intent.py` K14–K23.
> `reset_opening_state()` mostantól NÉGY gyűrűt nulláz.

---

> ## 🔎 DIAGNÓZIS (2026-08-11) — a nyers `strategy_fit` kalibrációja
> **Ez még nem javítás, hanem mérés. A döntés nyitott.**
>
> ### A v8-as horgonyzás két kimondott szabályát a modell nem tartja be
> A v8 blokk két ellenőrzést írt a promptba: *„ha négy vagy több stratégiának adtál
> 7-est vagy többet, pontozz újra"* és *„a szórás legalább 5 legyen"*. 50 soron:
>
> | verzió | n | átlag ≥7 db | (1) sértés | átlag szórás | (2) sértés | max=9 |
> |---|---|---|---|---|---|---|
> | v8 | 7 | 4.3 | 86% | 4.7 | 43% | 100% |
> | v9 | 15 | 4.0 | 73% | 4.9 | 27% | 87% |
> | v12 | 6 | 4.8 | 100% | 4.0 | 83% | 100% |
> | v13 | 11 | 4.9 | 100% | 4.9 | 36% | 82% |
> | v15 | 5 | **5.0** | **100%** | 4.8 | 20% | 60% |
>
> **A hét stratégiából 4-5 mindig 7 fölött van, a szórás soha nem éri el az 5-öt, és
> a nyers maximum 21 v13+ sorból 13-ban HOLTVERSENY** (2-3 stratégia ugyanazon a
> maximumon). Vagyis a pontozás nem rangsor, hanem **egy lapos „elfogadható" sáv** —
> a tényleges döntést a bias-tábla és a szenzor hozza, nem a pontszám. Pontosan az,
> amit a v8 blokk el akart kerülni („a bias nudge legyen, ne teherhordó").
>
> ### A CC-infláció mértéke és oka
> v8-v12 → v13-v15 nyers átlagok: `constructive_challenge` **5.7 → 8.6 (+2.9)**,
> minden más −0.8 … +0.8 között, az összes átlaga +0.4. Az inflació tehát **egyetlen
> stratégiára** vonatkozik, nem általános.
>
> **KONTROLLÁLT KÍSÉRLET** (nem változtatás; a promptot memóriában átrendezve, a
> telemetria kikapcsolva): a `thesis_condition`/`thesis_quote` a `strategy_fit` UTÁN.
>
> | poszt | CC_fit primelve | CC_fit átrendezve |
> |---|---|---|
> | Archicad/Forma | 9 | **7** |
> | BIM brain | 9 | **7** |
> | Agentic BIM | 9 | 9 |
>
> **A priming valós, de csak a felét magyarázza:** átrendezve a CC 7.7 átlagra esik,
> nem az eredeti 5.7-re. A maradék a v12-es horgony és a szélesített `wins_when`.
>
> **És ami NEM változott az átrendezéstől: a laposság.** ≥7 darabszám 5-6, szórás
> 3-5, a maximum továbbra is holtversenyben. **A kalibrációs hiba tehát nem a v13
> következménye — szerkezeti.**
>
> ### Egy mellékes, de konkrét következmény
> A `CHALLENGE_FIT_FLOOR = 7` **már nem szűr semmit**: a CC nyers pontja mostantól
> mindig ≥7. A szenzort valójában három feltétel gátolja (intent, igazolt idézet,
> feltétel-család), a negyedik no-op lett.
>
> ### A DÖNTÉSI FORK (nyitott)
> A prompt-oldali önellenőrzés **háromszor** nem működött (v8-as kalibráció, v12-es
> horgony, és most az átrendezés sem hozta vissza a szórást). Ez ugyanaz a hibaosztály,
> mint az authenticity-rubrika: **a modell önpolicingja nem mérőszám.** A projekt saját
> szabálya erre az volt, hogy törölni kell, nem erősíteni.
>
> Három út, kód-oldali:
> - **(a) Normalizálás:** a nyers pontokat rang-transzformálni a bias előtt, hogy a
>   bias újra nudge legyen egy szétterített skálán. Kicsi változás, de a holtversenyt
>   önkényesen oldja fel.
> - **(b) A fit mint SZŰRŐ, nem rangsor:** jelöltek = akik ≥7 (ezt a modell
>   megbízhatóan mondja meg), és a jelöltek közül a **kód** dönt — intent-bias, vétó,
>   plusz rotációs gyűrű a változatosságért. Ez ugyanaz az elv, ami a nyitásnál és a
>   hossznál már bevált: a varianciát kódban állítjuk elő, nem a mintavételre bízzuk.
>   Ez a `pick_strategy` átírása, tehát a döntési út közepe.
> - **(c) Nem nyúlunk hozzá,** de akkor tudomásul veszjük, hogy a döntést a bias-tábla
>   hozza — és akkor a bias-táblát kell auditálni, nem a pontozást.
>
> **DÖNTÉS: (b).** Megvalósítva alább, v16.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — A fit mint szűrő (engine v16)
>
> ### A mechanizmus
> A `pick_strategy` **változatlan** (a B-blokk regressziós tesztje arra épül, és
> továbbra is ő a kikapcsolt ág meg a fallback). Fölé került egy réteg:
> `strategy_candidates` + `decide_strategy`, három lépésben, mindegyik indokkal a
> naplóba (`strategy_decision_reason`):
> 1. **Jelöltek** — akik elérik a `STRATEGY_CANDIDATE_FLOOR`-t (7) és nincsenek vetózva.
> 2. **Frissesség** — a legutóbbi kettő kiesik. Védőszabály: ha ezzel kiürülne a
>    halmaz, a teljes jelöltlista marad (a rotáció nem kényszeríthet ki nem illeszkedő
>    stratégiát).
> 3. **Választás** — a súlyozott max dönt, és **csak holtversenyben** a poszt-hash.
>    Így a bias ott hat, ahol dolga van (közel-egyenlők között), és nem egy lapos
>    sávon ő a teherhordó.
>
> **A gyűrű sekélyebb (2), mint a nyitás-gyűrű (4):** ott nyolc formából választunk,
> itt a jelölt-halmaz mérve 4-5 elemű — négy kizárása kiürítené, és a mechanizmus
> látszólag működne, valójában folyton a védőszabályra esne vissza.
>
> ### A TESZT EGY SÚLYOS TERVEZÉSI HIBÁT FOGOTT
> Az első változat a **nyers** pontra szűrt. A J6 teszt (a v2 óta dokumentált
> alaphiba őre) azonnal elbukott, és jogosan: a mesterség-poszton a modell a
> `business_impact`-nek ad 10-et, a `field_experience`-nek 6-ot. Nyers padlóra az
> előbbi vetózott, az utóbbi **kiesik** — és az egyetlen jelölt a `systems_thinking`
> (nyers 7) lett volna, **súlyozottan 5.0-tal**, holott a bias a `field_experience`-t
> 9.0-ra emeli. **Egy szűrő, ami a bias ELŐTT vág, kidobja azt a korrekciót, amiért az
> intent layer létezik.** A padló ezért a **súlyozott** pontszámra megy (L18, L18.1,
> L18.2 rögzíti).
>
> ### ÉLES — nyolc poszt egy futásban
> | | |
> |---|---|
> | jelölt-szám | 6, 5, 5, 2, 2, 3, 2, 4 (átlag **3.6**) |
> | a frissesség kizárt | **3×** (2× `constructive_challenge`, 1× `field_experience`) |
> | győztes-eloszlás | CC 3, `field_experience` 3, `practical_lesson` 2 |
> | közvetlen ismétlés | 2 (mindkettő magyarázható, lásd lent) |
>
> A rotáció látható munkát végez: az IFC-poszton a CC volt a nyers maximum, de a gyűrű
> kizárta → `practical_lesson` nyert 11.0-val, ami azon a technikai poszton
> védhetőbb is.
>
> ### KÉT MÉRT LYUK (nyitott, egyik sem javítva — egy változás egyszerre)
> 1. **A kihívás-szenzor legyőzi a rotációt.** A szenzor a `decide_strategy` UTÁN fut,
>    tehát visszahozhatja a CC-t akkor is, ha a gyűrű épp kizárta — mérve: az egyik
>    poszton a döntés `business_impact` volt (a CC kizárva), a szenzor mégis CC-re
>    írta. Ez a „utasítás erősebb a visszhang-tilalomnál" elv következménye, de így két
>    egymás utáni CC lett. Javítás iránya: a szenzor is nézze a gyűrűt.
> 2. **Kis jelölt-halmaznál a rotáció nem tud hatni.** Két posztnál mindössze 2 jelölt
>    volt, mindkettő a gyűrűben → a védőszabály visszaadta a teljes listát → ismétlés.
>    Javítás iránya: adaptív gyűrű-mélység (≤2 jelöltnél 1).
>
> **Amit ez a változás NEM tesz:** nem javítja a modell pontozását. A nyers sáv
> továbbra is lapos (4-5 stratégia ≥7). A változás annyi, hogy a döntés **nem
> támaszkodik többé a rangsorra** — csak arra, amit a modell megbízhatóan tud
> („ez elfogadható lenne"), és a többit a kód dönti el.
>
> **Válasz-szerződés:** új additív mezők `strategy_candidates`, `strategy_recent`,
> `strategy_decision_reason`; `TELEMETRY_SCHEMA` nem emelkedik. Új tesztek:
> `test_linkedin_intent.py` L1–L18.2. `reset_opening_state()` mostantól ÖT gyűrűt nulláz.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — A két mért lyuk befoltozva (engine v17)
>
> ### 1. Adaptív gyűrű-mélység
> **A mért hiba:** nyolc éles posztból kettőnél mindössze **két** jelölt volt, mindkettő
> a kétmélységű gyűrűben → a védőszabály visszaadta a teljes listát → ismétlés.
> A rotáció ott, ahol a legjobban kellett volna, nem tett semmit.
>
> `depth = max(0, min(_STRATEGY_RING_SIZE, len(cands) - 1))`. Legfeljebb annyit zárunk
> ki, hogy **mindig maradjon választható**: 2 jelölt → mélység 1, 1 jelölt → 0.
>
> **Ezzel a védőszabály-ág ELÉRHETETLEN lett** (|used ∩ cands| ≤ len−1), és ezt nem
> érvelés őrzi, hanem teszt: az L19.2 minden jelölt-számra (1..7) és hatféle
> gyűrű-tartalomra végigmegy, és megbukik, ha a védőszabály-üzenet valaha megjelenik,
> vagy ha a győztes nem jelölt. A mélység a naplóba is kiíródik („gyűrű-mélység 2").
>
> ### 2. A kihívás-szenzor tiszteli a rotációt
> **A mért hiba:** a szenzor a `decide_strategy` UTÁN fut, tehát visszahozta a CC-t
> akkor is, amikor a gyűrű épp kizárta — így két egymás utáni CC-komment lett.
>
> Hetedik feltétel: ha a CC a strategia-gyűrűben van, a szenzor nem sül el.
>
> **Miért nem áll itt az „utasítás erősebb a visszhang-tilalomnál" elv** (ami a
> `shape_frame`-nél igen): ott a modell **kapott** egy utasítást, és azt büntetni
> ellentmondás lett volna. A szenzor viszont nem utasítás, hanem **előléptetés** — a
> dolga az, hogy a CC *lehetséges* legyen, nem az, hogy elkerülhetetlen.
>
> **A feltétel-sorrend szándékos:** a rotáció-ellenőrzés az UTOLSÓ, így az indok-string
> megkülönbözteti a „jó volt a tény, csak a rotáció zárta" és a „nem volt tény" esetet —
> a telemetriában ez két különböző jelenség (K24.1, K27).
>
> ### ÉLES — ugyanaz a nyolc poszt
> | | v16 | v17 |
> |---|---|---|
> | közvetlen ismétlés | 2 | **0** |
> | védőszabály-ág | 2× | **0×** |
> | a szenzor felülírta a rotációt | 2× | **0×** |
> | különböző stratégia 7 kommentben | 3 | **5** |
>
> A 17-es poszton a CC volt a nyers maximum, a gyűrű kizárta → `business_impact`
> nyert, és a szenzor **nem** írta vissza. A 19-esnél két jelölt volt, mélység 1 →
> a rotáció mégis hatott.
>
> **Egy átmeneti hiba a kötegben:** az IFC-poszt `503 UNAVAILABLE`-t kapott a compose
> hívásban. A telemetria hiba-ága ezt szabályosan naplózta (`error` mező, `engine`
> nélkül), és az újrafuttatás rendben lefutott (`practical_lesson`, 105 szó, sávon
> belül). Nem regresszió — de jó emlékeztető, hogy a hiba-sorokat a riportok
> `engine`-szűrése kihagyja.
>
> **Válasz-szerződés:** változatlan. Új tesztek: K24–K27, L19–L19.3; az L7 állítása a
> védőszabályról az elérhetetlenségre fordult.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — A v8-as kalibrációs ellenőrzés TÖRÖLVE (engine v18)
>
> ### Amit töröltünk, és mire hivatkozva
> A v8 blokk két szabályt írt a `strategy_fit` tételbe: *„ha négy vagy több
> stratégiának adtál 7-est vagy többet, pontozz újra"* és *„a szórás legyen legalább
> 5"*. A fenti diagnózis-blokk 50 sorral megmérte: a modell **soha nem tartotta be**
> (sértés v8 86%, v9 73%, v13–v15 **100%**), és a v16 óta a döntés amúgy sem
> támaszkodik a rangsorra — a nyers pont **szűrő**, a választást a kód hozza.
>
> Ez tehát **halott szöveg** volt: minden hívásban kimegy, semmit nem kényszerít ki, és
> azt a látszatot adja, hogy a pontozás szórása garantált. Ugyanaz a bánásmód, mint az
> authenticity-rubrikánál: **törlés + visszaszivárgás-teszt**, nem erősítés.
> Az L3–L5 checkek megfordítva őrzik (eddig a jelenlétét állították).
>
> **Ami szándékosan maradt:** a négy horgony (0-2 / 3-5 / 6-8 / 9-10) — a v16-os
> jelölt-padló éppen erre a sáv-szemantikára épül —, és a *„Score on professional value
> ALONE … weighted separately"* mondat, ami most fontosabb, mint valaha: a padló a
> **súlyozott** pontra megy, tehát ha a modell a nyers pontban is beszámítaná az
> intentet, a bias kétszer számolna (L5.1 rögzíti).
>
> ### A/B, nyolc poszt mindkét karban — az abort-kritérium NEM sült el
> | | v17 | v18 |
> |---|---|---|
> | **jelölt-szám átlag** (a döntő metrika) | 3.6 | **3.9** |
> | ≥7 db átlag | 4.1 | 4.6 |
> | szórás átlag | 5.4 | 4.5 |
> | közvetlen ismétlés | 0 | 1 |
>
> Az előre kimondott abort-kritérium a **jelölt-szám ≥5** volt: 3.9-nél nem sült el, a
> döntés bemenete gyakorlatilag változatlan.
>
> **A szórás és a ≥7 mozgása nem a törlés hatása, hanem visszatérés a korpusz
> átlagához.** A több-verziós sor: szórás v8 4.7, v9 4.9, v12 4.0, v13 4.9, v14 4.6,
> v15 4.8 — vagyis **a v17-es 5.4 volt a kiugró érték**, a v18-as 4.5 a sávon belül van.
> Ugyanez a ≥7-re (v13–v15: 4.9–5.0). **Amit ez NEM zár ki:** n=8 karonként, ezen a
> mintán egy gyenge szórás-hatás nem cáfolható. Ha a következő kötegekben a szórás
> tartósan 4 alá menne, ez a törlés újranyitandó.
>
> ### Egy új, mért megfigyelés a rotáció határáról
> Az egyetlen közvetlen ismétlés (`field_experience` → `field_experience`) magyarázott:
> a második posztnál **egyetlen** jelölt volt (`gyűrű-mélység 0`), tehát nem volt mit
> rotálni. A v17-es adaptív mélység így viselkedik szándékosan — de rögzítendő tény:
> **egy-jelöltes soron a rotáció definíció szerint nem tud hatni.**
>
> **Válasz-szerződés:** változatlan, `TELEMETRY_SCHEMA` nem emelkedik. Mellékhaszon:
> ~6 sor ≈ 90 kimeneti token megszűnt hívásonként — de az indok nem ez volt, hanem
> hogy a prompt ne állítson olyat, amit a mérés megcáfolt.

---

> ## ⚙️ KIEGÉSZÍTVE (2026-08-11) — A szenzor padlója: kettő helyett egy (engine v19)
>
> ### A probléma két része
> A v13-as kihívás-szenzornak volt egy „a modell maga is jónak jelölte" feltétele, saját
> konstanssal: `CHALLENGE_FIT_FLOOR = 7`, a **nyers** ponton. Azóta:
>
> 1. **NO-OP lett.** A v13-as `thesis_condition`-kérdés (ami a pontozás ELŐTT áll) a CC
>    nyers pontját 5.7-ről 8.6-ra emelte (v15: 9.0) — a 7-es padló a mért eloszláson
>    **sosem kötött**. Egy feltétel, ami mindig teljesül, úgy olvasódik, mintha védelem
>    lenne, pedig nem az.
> 2. **KETTŐS DEFINÍCIÓ.** A v16 bevezette a `STRATEGY_CANDIDATE_FLOOR`-t ugyanarra a
>    fogalomra, csak a **súlyozott** ponton — és a J6 teszt megmutatta, miért az a
>    helyes (nyers ponton szűrve a bias-korrekció kiesik). Két konstans ugyanarra a
>    fogalomra **drift-hazard**: az egyiket átírja valaki, a másikat elfelejti.
>
> ### A döntés: delegálás, nem törlés
> A szenzor mostantól a `strategy_candidates`-re kérdez rá — **egy** definíció, súlyozott
> ponton, a vétóval együtt. A `CHALLENGE_FIT_FLOOR` konstans megszűnt (a kódban már csak
> kommentben szerepel, történelmi hivatkozásként).
>
> **Miért NEM töröltük magát a feltételt** (szemben a v18-as halott prompt-szöveggel):
> ez **regresszió-védelem**. Ha a CC pontozása valaha visszaesik — például a v12-es
> DISAGREEMENT-horgony kivezetésekor, ami a listán van —, a szenzor ne léptessen elő egy
> rosszul illeszkedő stratégiát. A v18-as prompt-szöveg *félrevezetett*; ez *tartalék*.
> Hogy elsül-e, az a `challenge_reason`-ből megszámolható.
>
> **A vétó-ellenőrzés előbbre került**, mint a padló: a `strategy_candidates` a vetózott
> stratégiákat is kiszűri, tehát utána már nem lehetne megkülönböztetni a „kemény kapu"
> és a „padló alatt" esetet — a telemetriában ez két különböző jelenség.
>
> ### Miért volt szükség verzió-bumpra egy no-op → no-op változáshoz
> A mért eloszláson a viselkedés nem változik. De a feltétel **elérhető**: ha valaha
> bekerül egy CC-re szóló bias (intent- vagy szint-szinten), a súlyozott és a nyers ág
> **eltérő** döntést hoz. A verzió pontosan az ilyen látens ág-váltás miatt kell —
> különben egy későbbi elemzés két különböző döntési utat átlagolna egy címke alatt.
>
> A súlyozott szemantikát teszt bizonyítja, nem érvelés: a K7.2–K7.4 ideiglenesen betesz
> egy `-3.0` CC-biast a `management` szintre (ugyanaz a minta, mint a K9-es vétó-teszt),
> és ellenőrzi, hogy a nyers 8-as pont súlyozva 5-re esik, a szenzor hallgat, az indok a
> **súlyozott** értéket mondja — majd visszaállítás után ugyanaz a bemenet ismét elsül.
>
> **Válasz-szerződés:** változatlan. Tesztek: K6/K6.1 a közös padlóra hivatkozik,
> K7 visszaszivárgás-őr (nincs második padló-konstans), K7.1–K7.4 új.

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
