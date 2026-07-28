# Rendszer-audit — NODU Monitor, 2026-07-28

**Módszer:** négy független, read-only audit-futás (adatfolyam/logika · jelminőség/forrás-hatékonyság · LLM-költség · üzemeltetés), majd a vezető állítások **független újramérése**. A parancs, amivel megismételhető: `/nodu-audit` (`.claude/commands/nodu-audit.md`). Kód, config és DB **nem módosult** az audit alatt.

**Snapshot:** `posts`=1692 · `signals`=1431 · `runs`=786 · `drafts`=23 (22 pending, 1 approved).

---

## 0. Korrekció egy korábbi állításhoz

2026-07-27-én a Slack-munka során ez a mérés került a HANDOFF-ba: *„mind a 90 kiküldött jel severity 4 volt, egy sem 3-as vagy 5-ös → a `digest_min_severity` mint szabályozó nem működik."*

**A mérés hibás volt, a következtetés véletlenül igaz.** A 90 elem a `get_opportunities()` **default `limit=100`** melletti, `severity DESC` szerint rendezett szeletének a `new` státuszú része volt — tehát szükségszerűen a legmagasabb severity-k. A teljes tábla valós eloszlása:

| severity | jel | ebből `is_pain=1` |
|---|---|---|
| 1 | 930 | 0 |
| 2 | 14 | 1 |
| 3 | 305 | 305 |
| 4 | 206 | 206 |
| 5 | 1 | 1 |

A severity tehát **nem konstans**, de a fájdalom-jeleken **de facto kétértékű** (3 vagy 4: 511/513 = 99,6%). A `digest_min_severity: 3` küszöb így 513 jelből **512-t átenged** — a kapu valójában `is_pain=1`, nem a severity. A következtetés áll, az érv más.

---

> ## Javítási állapot (2026-07-28, az audit napján)
>
> **§1.1 és §1.2 JAVÍTVA és élesben verifikálva** (Zoltán döntése: „csináld meg az 1-est és a 2-est"). Eredmény:
>
> | mérés | audit előtt | javítás után |
> |---|---|---|
> | `posts` | 1692 | **446** |
> | Khoros-poszt (autodesk+graphisoft) | 1309 | **33** (= a valódi szálak száma) |
> | `signals` | 1431 | **317** |
> | Lehetőségek totál | 504 | **129** |
> | fájdalom-jel (`is_pain=1`) | 513 | **128** |
> | ebből sev≥4 | 206 | **71** |
> | egy éles Playwright-kör | 48 elem → **30 „új"** | 48 elem → **0 új** |
>
> **A §2.1–2.7 (P1) IS JAVÍTVA, ugyanazon a napon.** Röviden, tételenként:
>
> | # | Mit | Mérés / bizonyíték |
> |---|---|---|
> | 2.1 | A draft-generálás **nem** állítja `alerted`-re a posztot (két helyen kivéve a `mark_alerted`-et), és a draft-küszöb a digest-küszöböt követi, ha nincs külön megadva | teszt: nincs aktív `mark_alerted` a draft-úton |
> | 2.2 | A heartbeat látja a **hiányzó** futást: új `stale` státusz, `connector_schedule()` mint EGY igazság az ütemezőnek és a health-nek | élesben azonnal kidobta a `backup`+`digest` hiányát, és **Slack-riasztást küldött** |
> | 2.3 | A `backup` és a `digest` `runs`-bejegyzést ír | a 4 napos backup-lyuk innentől 2,5 nap után riaszt (`health.stale_factor`) |
> | 2.4 | A 274 KB-os tudásbázis **kikerült** a fórum-draft promptból; a heti utakon `knowledge_base.prompt_max_chars` (8000) a keret | a system prompt **260 126 → 1 361 karakter** |
> | 2.5 | Az első futás a `runs` utolsó futásából számolódik (+stagger), nem „most" | újraindítás után **0 connector-kör** 45 s-en belül (előtte mind a 11 azonnal) |
> | 2.6 | Titok-maszkoló szűrő a napló mindkét handlerén (`AIza…`, Slack-webhook, `?key=`, Bearer, Brave) | 5 minta-teszt; a **meglévő** logsorokat ez nem javítja — a kulcs visszavonása Zoltán feladata |
> | 2.7 | A jelszókapu **mind a 8** mutáló végponton, plusz egyidejűség-védelem a `/run/<action>`-ben (409) | 11 teszt, mind 401/409 |
>
> Teszt: `test_p1_fixes.py` **38/38**, és a másik négy suite (Slack 37, döntés-napló 30, dedup+digest 20, DB-smoke) változatlanul zöld.
>
> **Két dolog, ami a javítás közben derült ki:** (1) a `reddit` kulcs nélkül nem ír `runs`-sort, tehát `expect_runs: False` kellett neki, különben a `/health` tartós hamis 503-at adna; (2) a `digest` `items_seen`-jébe **1** kerül („a job lefutott"), nem a várakozó jelek száma — különben 5 csendes nap után a heartbeat hamis `blind` riasztást adna.
>
> **A P2-es tételek IS elkészültek** (§3.1–3.9 + §5/#11–12). Tételenként, mérésekkel:
>
> | # | Mit | Mérés |
> |---|---|---|
> | 3.1 | Severity-prompt: **mind az öt fokozat horgonyozva**, az 5-ös feltétele lazítva („elég AZ EGYIK"), `CLASSIFIER_VERSION` → v4. Új `main.py --calibrate N`: **páros** újraértékelés a DB írása nélkül | ld. lentebb a „mit adott a kalibrálás" blokkot — **nem az, amit vártunk** |
> | 3.2 | A `confidence` **kikerült minden rendezésből** (sd=0,037 → zajt rendez), a `buying_intent` a `severity` elé | 4 `ORDER BY` átírva |
> | 3.3 | SalesOS-score: `severity×2` + 1 ha `buying_intent`, −1 ha `solved_internally` | a score-eloszlás **4 → 7 distinct érték**: `{2,6,8,10}` → `{2,5,6,7,8,9,10}`; Qualified (≥7) 113 → **125**/177 |
> | 3.4 | `nodu_mention` **kivezetve a sémából** — a márkaemlítést regex dönti el (`detect_brand_mention`) | a modell 1431 jelből 1-ben jelölte; a regex ugyanazt találja, hallucinálni viszont nem tud |
> | 3.5 | `competitor_name` mellé **kötelező `competitor_quote`**, amit a kód megkeres a posztban; ha nincs meg, a jelölést eldobjuk | **élesben azonnal fogott:** `competitor ELDOBVA (az idezet nincs a posztban): 'similar to the IFC Structure tree in BIM Vision'` |
> | 3.6 | `stackoverflow` → `enabled: false` (kód és config marad, CLI-ból futtatható) | élettartam: 1887 nyers elem → 5 poszt → **0 jel**, 320 s |
> | 3.7 | `revitforum`: nincs mit tenni — a `forums: {}` üres, tehát már nincs ütemezve | utolsó futása 2026-07-23 |
> | 3.8 | Classifier-sor **FIFO** + `posts.classify_attempts` számláló (3 kísérlet után kiesik) | a 4 napja várakozó posztok sorra kerültek; hátralék **104 → 31** |
> | 3.9 | `delay_seconds` **13 → 2**, mért alapon | 13 s → 13,2 s/poszt (4,5 RPM); 5 s → 6,2 s (9,7 RPM); 2 s → 3,3 s (18,1 RPM). Tartós 30-as kör 2 s-nál: 3,9 s/poszt (15,2 RPM), **0 db 429**. 100 poszt: ~3 óra → **~6,5 perc** |
> | §5/11 | `max_output_tokens` 200 → **320** a két draft-úton | a meglévő 23 draft leghosszabbja a régi keret 92%-a volt |
> | §5/12 | `storage/backup.verify_snapshot()`: `integrity_check` + tábla-olvasás minden mentés után, **a rotáció előtt**; sérült/üres snapshot nem szorít ki egy jót. Visszaállítási eljárás dokumentálva (HANDOFF §6) | élesben: `integrity_check=ok, {'posts': 450, 'signals': 390, 'drafts': 17, 'runs': 815}`; teszt sérült fájllal és 0 posztos mentéssel |
>
> Teszt: `test_p2_fixes.py` **42/42**; a teljes suite (Slack 37, döntés-napló 30, dedup+digest 20, P1 38, P2 42, DB-smoke) zöld.
>
> ### Mit adott a severity-kalibrálás — és mit nem
>
> A `--calibrate 25` **páros** mérése (ugyanazok a posztok, régi vs. mai prompt): **7 feljebb, 1 lejjebb, 17 változatlan**; `is_pain` 1 esetben fordult.
>
> | severity | régi (ugyanezen 25 poszton) | v4 |
> |---|---|---|
> | 1 | 0 | 1 |
> | 3 | 9 | 4 |
> | 4 | 16 | 18 |
> | 5 | 0 | 2 |
>
> **Amit elért:** a skála teteje használhatóvá lett (sev5 a fájdalom-jelek 0,07%-áról ~8%-ra), és egy valódi hamis pozitív megszűnt (egy önéletrajz-oldal sev4/pain=1 → sev1/pain=0).
>
> **Amit NEM ért el:** a szórás nem nőtt, a mass **feljebb tolódott** — 25-ből 18 a 4-esen ül. A korábbi sev3 felének a 4-esbe csúszása azt jelenti, hogy a `digest_min_severity: 4` **nem lett jó szűrő**: ma a fájdalom-jelek ~80%-át átengedné (korábban ~54%). **Következtetés: a severity nem prioritási kapcsoló, és nem is lesz az.** A valódi diszkriminátor a `buying_intent` (a jelek ~9%-a), ezért került az a rendezés élére (§3.2) és a SalesOS-score-ba (§3.3). Aki a jövőben szűkíteni akar, `buying_intent`-re szűrjön, ne severityre.
>
> A javítások: `connectors/khoros_url.py` (kanonikus dedup-kulcs, a connector és a migráció **ugyanezt** használja), `migrations/2026_07_28_khoros_dedup.py` (dry-run + `--apply`, saját snapshottal), `_opportunity_where(post_status=…)` + `run_digest` SQL-ben szűr. Teszt: `test_dedup_and_digest.py` **20/20**.
>
> **Amit a javítás közben megtudtunk:** a §1.2-ben talált **32 „strandolt" jel maga is duplikátum volt** — olyan szálak másolatai, amiket a túlélő poszton már kiküldtünk. Tehát valódi lead nem esett ki; a digest-hiba értéke **előretekintő**: ahogy a DB nő, valódi jeleket strandolt volna. A migráció után `count_opportunities(post_status='new')` = **0**.
>
> **A severity-kép is megváltozott** (a duplikátumok nélkül): sev1 186 · sev2 3 · sev3 **57** · sev4 **70** · sev5 1. A fájdalom-jeleken a sev4 mostantól **gyakoribb**, mint a sev3 — az audit §3.1-es javaslata (prompt-kalibrálás) ezért újramérendő, nem a régi számok alapján.

## 1. P0 — a számok, amikre a döntéseket alapozzuk, hamisak

### 1.1 A Playwright-connector dedup nem működik: 1309 poszt = 33 valódi szál

`connectors/playwright_connector.py:129` az `external_id`-nek a **teljes keresési URL-t** adja, ami tartalmazza a futásonként változó `search-action-id` query-paramétert. A `UNIQUE(platform, external_id)` így soha nem fog.

Független mérés (2026-07-28):

| mérés | érték |
|---|---|
| playwright/Khoros poszt (`autodesk` + `graphisoft`) | **1309** |
| ebből `search-action-id`-t tartalmaz | **1309 (100%)** |
| kanonikus szál-azonosító (`/(m-p\|ta-p)/(\d+)`) | **33** |

**Duplikációs faktor: 39,7×.** Következmények, mind mért vagy közvetlenül levezethető:

- A `posts` 77%-a ugyanennek a 33 szálnak a másolata. Minden totál, arány és riport ezt méri.
- A classifier ~1150 fizetős Gemini-hívást költött duplikátumokra.
- A heartbeat **soha nem jelezné**: a `new_posts` magas, tehát „egészséges".
- A 02-es audit „playwright helyreállt, 26–30 új/kör" mérése ezt a hibát mérte sikerként.

### 1.2 A napi digest 100 elemnél elvágja a sort, és a kimaradó jelek soha nem kerülnek sorra

`main.py:251` `limit` nélkül hívja a `get_opportunities()`-t → default **100** (`storage/db.py:273`), és a `status='new'` szűrés **ezután, Pythonban** fut a már levágott listán.

| mérés | érték |
|---|---|
| `sev≥3` fájdalom-jel `status='new'` (SQL, limit nélkül) | **35** |
| amit a digest ebből lát | **3** |
| **strandolt jel** | **32** |

És ez nem időbeli késés, hanem **strukturális kizárás**: a rendezés `severity`/`confidence` szerinti (nem idő szerinti), a már `alerted` sorok pedig sosem esnek ki a halmazból, tehát a 100-as határ monoton lejjebb tolódik. Ezek a jelek `new`-ban maradnak örökre.

**Ez a §7/J és §7/N hibaosztály harmadik előfordulása** — és most nem egy UI-számlálót érint, hanem az értesítési utat.

### 1.3 A Graphisoft-posztok 100%-a megkerüli az 1 éves korlátot

`playwright_connector.py:110-119`: dátum-elem híján a nyers szöveg megy a `created_at`-be; a Khoros `'‎2017-01-26\n\t\t06:54 AM'` formát ad. Az `insert_post` (`storage/db.py:157`) `except Exception: pass` ágon **beszúrja**.

| mérés | érték |
|---|---|
| `platform='graphisoft'` poszt | **405** |
| nem parse-olható `created_at` | **405 (100%)** |
| a szálak évjárata | 2012 (92) · 2017 (46) · 2018 (46) · 2020 (46) · 2021 (86) · 2022 (80) |

Következmény: **14 éves fórumszálakra generálunk 2026-os válaszjavaslatot**, és ezek „friss lehetőségként" jelennek meg a dashboardon.

---

## 2. P1 — csendes veszteség és rejtett költség

| # | Megállapítás | Bizonyíték | Következmény |
|---|---|---|---|
| 2.1 | **A 07:30-as draft-job „elfogyasztja" a jeleket a 08:00-as digest előtt.** A `save_draft` `draft_ready`-re állít, majd a `draft_generator` két sorral később `mark_alerted`-et hív. | `storage/db.py:590` vs `responder/draft_generator.py:226,282`; **0 poszt** van `draft_ready` státuszban 1692-ből; a `draft_min_severity` és a `digest_min_severity` **ugyanaz a szám két helyen** (3), ezért esik egybe a két halmaz | A §3.6-os hibaosztály (kiküldés nélküli elfogyasztás) visszaépült a draft-úton, miután a digestben javították |
| 2.2 | **A `/health` a HIÁNYZÓ futást nem látja, csak a rosszat.** Az `active_within_hours: 24` ablakon kívül eső connector eltűnik a riportból → `problems=[]` → HTTP 200. | `storage/db.py:704-712`; ma **5 connector** (reddit, revitforum, autodesk, graphisoft, search) van ebben az állapotban, nulla riasztás | A §4/6-os hibaosztály visszatért, most a heartbeaten belülről |
| 2.3 | **A napi backup 4 napból 1-szer futott.** A memóriás jobstore + `misfire_grace_time` mellett a kimaradt cron véglegesen elveszik, catch-up és jelzés nincs. | `logs/monitor.log`: 1 db `[backup]` sor; `backups/`: 2 fájl (1 kézi, 1 automata); 82 szerver-újraindítás a logban | A `keep: 7` rotáció soha nem aktiválódott; egy DB-hiba a 07-24-es 28 posztos állapotra vetne vissza |
| 2.4 | **A 274 KB-os tudásbázis továbbra is minden fórum-draft promptjába bekerül** — a §7/O csak a LinkedIn-útról vezette ki. | `draft_generator.py:146` (`_build_system_prompt`), `:435`, `:510`; a felépített prompt **260 126 karakter ≈ 65 000 token**, ebből **99,1% a KB** | 33× költség draftonként, és — súlyosabb — belső anyag (sprint-tervek, licenc-kalkulátor, vezetői összefoglaló) kerül a modell elé, amikor **nyilvános fórumkommentet** ír. Egy meglévő draftban már van hallucinált URL (`drafts.id=4`) |
| 2.5 | **Minden szerver-újraindítás teljes kimenő rajtaütést indít.** 11 interval-job mind `next_run_time=now`-val regisztrál. | `main.py:336…433`; 2026-07-27 19:00–22:00: **71 futás** ütemezés szerinti ~9 helyett. `websearch` napi 1-re konfigurálva → aznap 12 futás × 11 query = **132 Brave-query** | A `poll_interval_minutes` látszólag hat, valójában csak a futások közti minimumot adja; kvóta- és ban-kockázat a forrásoknál |
| 2.6 | **Élő formátumú Google API-kulcs plain textben a logban.** | `logs/monitor.log`, **60 előfordulás** `...key=AIzaSy...` alakban (kivezetett CSE-kulcs, a mai kulcsoktól különbözik) | A `logs/` git-ignorált, de bármely log-másolat vagy hibajelentés viszi. A kulcs a GCP-projekten még érvényes lehet — visszavonandó |
| 2.7 | **A jelszókapu egyetlen HTML-nézetet véd, a mutáló végpontokat nem.** | `_admin_gate` egyetlen hívási helye `ui/app.py:120` (`/admin` GET). Kapun kívül: `/save`, `/run/<action>`, `/draft/*/approve\|reject`, `/lead/*/to-sales-os` | Ha a gép hálózatra nyílik, egy beállított jelszó **hamis biztonságérzetet** ad: az admin oldal kérdez, a `POST /save` és a `POST /run/playwright` nem |

---

## 3. P2 — mérőszámok, amik nem mérnek

| # | Megállapítás | Bizonyíték |
|---|---|---|
| 3.1 | **A severity-skála 5 fokozatából 2 használható.** A prompt csak az 1-est, 3-ast és 5-öst horgonyozza, a 2 és 4 definiálatlan; az 5-ös definíciója kielégíthetetlenül szigorú. | `classifier/pain_classifier.py:68-70`; `sev5 = 1/1431 (0,07%)`, `sev2 = 14` |
| 3.2 | **A `confidence` rangsorolásra használhatatlan**, mégis tiebreaker. | sd=**0,037**, 78%-a pontosan 0,90; `is_pain=0`-nál is 0,896 az átlag. Rendezési kulcs: `db.py:296,381,459` |
| 3.3 | **A SalesOS-score csak 6 vagy 8 lehet.** `score = severity × 2`, a jelek 99,6%-a sev3/4. | `crm/salesos_client.py:39-55`. A 0–10 sávból 8 érték sosem fordul elő; a stage-leképezés bináris |
| 3.4 | **A `nodu_mention` az elsődleges rendezési kulcs — és 1431 sorból 1-ben igaz.** Ráadásul LLM-mel kérdezzük azt, amit a `linkedin_engine._BRAND_PATTERN` regexe már determinisztikusan tud (§4/16 sérül). | `db.py:296`; `nodu_mention=1` → **1 sor** |
| 3.5 | **A `competitor_name` 15%-a igazolatlan** — nincs `competitor_quote`, nincs kódbeli ellenőrzés (§4/18 sérül). | 53 flagelt jelből **8-ban** a megnevezett versenytárs nem szerepel a szövegben; egy esetben maga az „ArchiCAD" van versenytársként megjelölve |
| 3.6 | **A StackOverflow a második buildingSMART.** | Élettartam: 37 futás, **1887 items_seen → 5 poszt → 0 osztályozott jel**, 320 s. Utolsó 48 óra: 26 futás, 1326 elem, **0 új poszt** |
| 3.7 | **A `revitforum` üres configgal is fut**, „sikeres 0"-t naplózva. | `forums: {}`, mégis 86 futás, **2326 s**, 0 elem, 0 hiba |
| 3.8 | **A classifier-sor LIFO, és a bukott poszt örökre visszatér.** | `db.py:215` `ORDER BY fetched_at DESC`; nincs kísérlet-számláló. **257 osztályozatlan** poszt, a legrégebbi **4 napja** vár, miközben 24 óra alatt 725 lett osztályozva |
| 3.9 | **A `delay_seconds: 13` a már kivezetett ingyenes Gemini-szinthez van hangolva.** | 6 éles kör mérve: batch 25 → **352 s**, ebből **312 s puszta várakozás**. 100 poszt átfutása ma **~3 óra**, `delay_seconds: 2`-vel ~6 perc. A számlázás §4/9 szerint be van kapcsolva |

---

## 4. Ami rendben van (lezárva, ne vizsgáljuk újra)

- **`thinking_budget=0` mind a 6 Gemini-hívási helyen ott van** — a §4/1-es csapda le van fedve.
- **Erőforrás nem szűk keresztmetszet:** szerver RSS 173 MB, DB 2,8 MB (~60 MB/év növekedés), log 174 KB/nap 2 MB×6 rotációval. Nincs zombi processz, nincs lógó Chromium.
- **A backup-snapshotok tartalmilag visszaolvashatók** — most először ellenőrizve: `PRAGMA integrity_check` = ok mindkét snapshoton, a táblák és nagyságrendek egyeznek az élő DB-vel. **De visszaállítási eljárás nincs dokumentálva.**
- **A hibakezelés implicit retry-ként működik:** a bukott classifier/draft nem ír rekordot, tehát a következő körben újra sorra kerül. Jelvesztés nincs — próbálkozás-számláló viszont sincs.
- **A GitHub drága, de kifizeti magát:** 9990 s futásidő 82 posztra, viszont **86,3% fájdalom-arány** és 35 db sev≥4 jel. 1 sev≥4 jel ≈ 285 s.
- **A websearch (Brave) fájdalma 88%-ban a reddit.com-ról jön**, és a maradék 60 domain 0 fájdalom-jelet adott → **nincs új bekötendő forrás** az adatban. A Brave értéke ma az, hogy a halott Reddit-connectort pótolja.

---

## 5. Javaslatok priorizálva

A prioritás alapja: mennyi hamis adatot szüntet meg vagy mennyi csendes veszteséget zár le — nem az elegancia.

| # | Teendő | Munka | Mérhető eredmény |
|---|---|---|---|
| **1** | **Playwright `external_id` kanonizálása** (`/(m-p\|ta-p)/(\d+)`, query nélkül) + a ~1276 duplikátum és a rájuk épült `signals`/`drafts` kivezetése migrációval, majd minden jelminőség-szám újramérése | 4 óra | `COUNT(*) == COUNT(DISTINCT canon(url))`; a Lehetőségek totál ~504 → ~115; a valós `new_posts/kör` láthatóvá válik |
| **2** | **`run_digest`: a státusz-szűrés kerüljön a SQL-be** (`_opportunity_where` kapjon `status` paramétert), hogy a lista és a számláló ugyanarra a halmazra vonatkozzon — harmadszorra | 1 óra | Digest után `SELECT COUNT(*) … status='new' AND severity>=3` = **0**; ma 35 |
| **3** | **A Khoros `created_at` normalizálása** (LRM/tab strip + `%Y-%m-%d %I:%M %p`), és az `insert_post` kor-elutasítása legyen **hangos**: a „túl régi" darabszám menjen a `runs`-ba connectoronként | 2 óra | 0 nem parse-olható `created_at`; a 2012-es szálak eltűnnek a Lehetőségek közül |
| **4** | **A draftolt és a kiriasztott állapot szétválasztása:** `mark_alerted` kivétele a `draft_generator`-ból, egy küszöb-konstans kettő helyett | 2 óra | Az adott napon digestbe kerülő jelek száma = aznap sev≥3-ra osztályozott, még nem riasztott jelek száma |
| **5** | **Heartbeat: „elvárt connector" lista** a configból (mikor kellett volna futnia) → `stale` státusz a `problems`-ba; a `backup` és a `digest` is írjon `runs`-bejegyzést | 3-4 óra | Egy connector kikapcsolása → `/health` 503. A 4 napos backup-lyuk azonnal látszott volna |
| **6** | **A 274 KB-os KB kivezetése a fórum-draft útról** (1 sor: `draft_generator.py:146`), a heti riportokhoz kivonat | 1 óra | Prompt 260 126 → ~1 800 karakter; a §7/O n-gram-módszerével a kimenet minősége összevethető |
| **7** | **Titok-szűrő a log-handlerre** (`AIza…`, `hooks.slack.com/services/…`, `[?&]key=`) + a logban lévő CSE-kulcs visszavonása a GCP-n | 1 óra + visszavonás | `grep -cE "AIza\|hooks.slack.com"` = 0 az új sorokra |
| **8** | **Severity-prompt kalibrálása** (a 2-es és 4-es horgonyzása, az 5-ös lazítása) + `CLASSIFIER_VERSION` bump és ~100 poszt újraosztályozása a régi mellé | 1-2 óra | A két kohorsz `classifier_version` szerint összevethető; cél: sev5 aránya > 0,07%, a sev3/4 megoszlás ne 99,6% legyen |
| **9** | **`next_run_time` szórása** (jitter vagy az azonnali indítás elhagyása a 240/720 perces connectoroknál) | 30 perc | Futásszám/3 óra: 71 → ~9 (baseline mérve) |
| **10** | **`_admin_gate` kiterjesztése minden mutáló route-ra** + `_run_in_bg` egyidejűség-ellenőrzés | 1-2 óra | Jelszó nélküli `POST /save` → 401; kétszeri `/run/playwright` → 409 |
| **11** | **StackOverflow és revitforum kivezetése az ütemezőből** (a kód maradhat), `delay_seconds` lemérése lépcsőzetesen (13 → 5 → 2), `max_output_tokens` 200 → 320 | 1 óra összesen | 2646 s futásidő megszűnik 0 jelvesztés mellett; 100 poszt átfutása 3 h → ~6 perc; a draftok nem csonkolnak |
| **12** | **Visszaállítási eljárás a HANDOFF-ba** + `integrity_check` a friss snapshoton, hibára ERROR-log | 1 óra | Az `integrity_check` igen; a procedúra egy valódi próba-visszaállítással (üres másolaton) |

---

## 6. Amit NE tegyünk

- **Ne a jelminőséget hangoljuk először.** Amíg a Playwright-duplikáció (1.1) él, minden arány 39,7×-es zajt tartalmaz a legnagyobb forráson. A 8. javaslat (severity-kalibrálás) **csak az 1. után** mérhető értelmesen.
- **Ne bontsuk fel a LinkedIn-motort 9 hívásra.** Mérve ~3000 input token/komment — a rendszer költségének elhanyagolható része. A 2 hívás indoklása áll (§7/O).
- **Ne töltsük fel a classifier-promptot a Gemini 2048 tokenes implicit-cache küszöbére.** A kitöltés többe kerülne, mint a megtakarítás: a classifier egy poszt teljes útjának ~5%-a.
- **Ne a GitHub-connectort optimalizáljuk futásidőre.** A leglassabb (a gyűjtési idő ~40%-a), de a legjobb jelforrás (86,3% fájdalom). A futásidő itt nem költség, hanem befektetés.
- **Ne állítsunk be admin-jelszót anélkül, hogy a mutáló végpontokra is kiterjesztenénk** (2.7) — a részleges kapu rosszabb, mint a nyilvánvalóan nyitott.
