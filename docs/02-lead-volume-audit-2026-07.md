# NODU Monitor — Lead-volumen audit: miért termel kevés találatot a rendszer

**Dátum:** 2026-07-24 · **Tárgy:** funkcionális audit a lead-volumen összeomlásának okaira
**Előzmény:** `docs/01-architektura-audit-2026-07.md` (stratégiai audit, 2026-07-19) — ez a dokumentum arra épül, nem ismétli meg. A 01-es a *célarchitektúráról* szól; ez a *jelenlegi üzemállapotról*.
**Módszer:** kódolvasás + az éles `nodu_monitor.db` (477 `runs`-rekord, 2026-06-16 →) kimérése + élő forrás-próbák (HTTP) + a Playwright-hiba laborreprodukciója. Minden alábbi állítás mért, nem feltételezett; ahol hipotézis, ott ki van írva.

---

## 1. Vezetői összefoglaló

**A rendszer nem azért termel kevés leadet, mert a szűrés túl szigorú vagy mert a Google CSE kikerült. Azért termel keveset, mert a hét begyűjtő közül négy nulla üzemmódban van, egy pedig zajt gyárt — és mindezt a rendszer nem jelzi, mert a „0 új találat" és a „csendben eltört" ugyanúgy néz ki a naplóban.**

A mért forrás-mérleg (a `runs` tábla teljes élettartama, 2026-06-16 → 2026-07-23):

| Connector | Futások | Begyűjtött poszt | Hibás futás | Valódi állapot |
|---|---:|---:|---:|---|
| **playwright** (Graphisoft+Autodesk) | 68 | **157** | 46 | ⛔ **2026-07-21 óta halott** — böngésző nem indul |
| youtube | 39 | 58 | 0 | ⚠️ Termel, de 13 jelből 1 fájdalom — **zajgenerátor** |
| discourse (buildingSMART) | 53 | 38 | 0 | ✅ Működik, de kimerítve (fix query-készlet) |
| github | 51 | 17 | 0 | ✅ **A legjobb jelminőség** (8 jelből 6 fájdalom), alulhasználva |
| **revitforum** | 86 | **0** | **0** | ⛔ **Csendben eltört** — a fórum XenForo-ra migrált |
| **reddit** | 7 | **0** | 6 | ⛔ **Nincs API-kulcs** — óránként kihagyva |
| **stackoverflow** | *nincs napló* | ~0 | ? | ⛔ Hibás tag-szintaxis → 0 találat, **és nem is naplóz** |
| graphisoft/autodesk (HTML) | 155 | 0 | 0 | ⛔ Khoros 403 — 2026-07-22-én kivezetve a configból |
| search (Google CSE) | 4 | **0** | 0 | ⛔ Kivezetve — **soha nem termelt mérhető volument** |

Öt megállapítás, prioritási sorrendben:

1. **A legnagyobb volumenforrás (Playwright, az összes begyűjtött elem ~58%-a) 3 napja halott** — nem szelektor-, hanem **Python-interpreter-hiba**: a szervert a Microsoft Store-os `WindowsApps\python.exe` aliasszal indították, amely alatt a `%LOCALAPPDATA%\ms-playwright` olvasása átirányítódik, így a telepített Chromium „nem létezik". Laborban reprodukálva (§3.1).
2. **A `runs` napló szerint a rendszer 2026-07-23 14:25 óta egyáltalán nem fut** — nincs élő `server.py` processz, csak két beakadt `main.py --github` zombi. Azaz jelenleg **nulla** a begyűjtés.
3. **Az adatbázisból eltűnt a felhalmozott korpusz.** A `HANDOFF.md` (2026-07-21) 249 posztot és 64 osztályozott jelet dokumentál; ma **28 poszt** van benne, `id=1`-től újraindított számlálóval, a legrégebbi `fetched_at` 2026-07-22 13:11. A `runs` tábla nem lett törölve. Nincs backup-fájl. (§3.3)
4. **A riasztási út strukturálisan zárt:** e-mail, Slack és webhook mind `enabled: false`, a napi digest mégis `alerted` státuszra állítja a posztokat — azaz **a találatokat „elküldöttként" fogyasztja el anélkül, hogy bárhová elmenne**. Ráadásul a digest még a *pivot előtti* kulcsszó-score-ral szűr (`min_keyword_matches: 1`), tehát a classifier jelminősége el sem jut az értesítésig. (§3.6)
5. **A kulcsszó-szűrő nem a fő szűk keresztmetszet** — de a YouTube-connector megkerüli, és emiatt a Gemini-kvótát „Parametric Wall Art" típusú videócímekre költi (§3.5). A `search_connector.py` kiesése pedig **lefedettségi**, nem volumen-lyuk: a mérhető történetében 4 futás alatt 0 posztot termelt.

**Egy mondatban:** a lead-volumen helyreállításához nem új forrás kell, hanem a meglévő hét forrás közül a négy nullázott újraélesítése és egy néma-hiba-riasztás — ez a becslésem szerint **1 nap fókuszált munka**, és nagyságrenddel többet hoz, mint bármelyik új connector vagy kereső-API.

---

## 2. Mit mértem és hogyan

Hogy az alábbi állítások visszakövethetők legyenek:

| Bizonyíték | Forrás |
|---|---|
| Forrásonkénti volumen, hibaarány, néma nulla-futások | `runs` tábla aggregálva (477 sor) |
| Jelminőség forrásonként | `signals ⨝ posts` (24 jel) |
| Korpusz-eltűnés | `sqlite_sequence` (posts=28) vs `HANDOFF.md` §3 (249 poszt) |
| Playwright-hiba pontos oka | ugyanaz a szkript két interpreterrel lefuttatva (§3.1) |
| revitforum törés oka | élő HTTP GET: `search.php` → 302 → `/search`, XenForo + Cloudflare |
| Discourse/GitHub fejtér | élő API-hívás: elérhető vs. behozott találatszám |
| Stack Overflow tag-hiba | élő API-hívás `tagged=revit+archicad` (0 találat) vs `revit;archicad` |
| Khoros 403 | élő HTTP GET mindkét fórumra → 403 |

Minden hivatkozott sorszám a repo jelenlegi állapotára érvényes.

---

## 3. Gyökérokok

### 3.1 ⛔ P0 — Playwright: rossz Python-interpreter, nem rossz szelektor
**Hatás a lead-volumenre: MAGAS** (a mért begyűjtés 58%-a) · **Javítási munka: ~15 perc**

A `runs` napló szerint a Playwright 2026-07-20/21-én még **157 posztot** hozott (7–11 poszt/futás), majd 07-21 18:38 óta **minden futás** ugyanezzel a hibával áll le:

```
BrowserType.launch: Executable doesn't exist at
C:\Users\ZoltanPoczai\AppData\Local\ms-playwright\chromium_headless_shell-1228\...\chrome-headless-shell.exe
```

**A fájl viszont létezik** (203 MB, telepítve 2026-07-18, `INSTALLATION_COMPLETE` jelzővel). Ugyanazt a minimál-szkriptet a két gépen elérhető interpreterrel lefuttatva:

| Interpreter | `os.path.exists(...chrome.exe)` | `launch()` |
|---|---|---|
| `...\Python\pythoncore-3.14-64\python.exe` | `True` | ✅ OK (Chromium 149.0.7827.55) |
| `...\Microsoft\WindowsApps\python.exe` | **`False`** | ⛔ pontosan az éles hibaszöveg |

**Ok:** a Microsoft Store-os Python-alias alatt a `%LOCALAPPDATA%` írás/olvasás virtualizált (Store-app redirection), így a `ms-playwright` mappa nem látszik — miközben a hibaszöveg ugyanazt az utat írja ki, ami valójában létezik. Ezért nézett ki „letörölt Chromium"-nak egy interpreter-hiba.

**Ez magyarázza a 07-20/21-i váltakozó OK/HIBA mintát is** (11:30 OK → 12:12 HIBA → 13:19 OK → 13:42 HIBA…): **két párhuzamos szerver-példány futott, két különböző interpreterrel** — pontosan az a hiba, amit a `HANDOFF.md` §4/6 külön kiemel. Jelenleg is két beakadt `main.py --github` processz él, egy-egy interpreterből.

> **Fontos következtetés:** a brief hipotézise, hogy a Playwright-szelektorok csendben eltörtek, **nem igazolódott.** A szelektorok (`.lia-quilt-column-left-content` / `.MessageSubject a` Graphisoftnál, `.lia-message-item` Autodesknál) 07-21-én még dolgoztak. A törékenységük valós kockázat, de nem ez a mostani hiba.

> **Utólagos megerősítés (2026-07-24, a P0-javítás után):** a helyes interpreterrel indított szerver első Graphisoft-körében **6 új bejegyzés** érkezett — a szelektorok tehát épek. **Egy új, kisebb törékenység viszont láthatóvá lett:** a `page.goto(..., wait_until="networkidle")` a Khoros-SPA-n időnként belefut a 15 s-os limitbe (a folyamatos telemetria-kérések miatt a hálózat sosem lesz „idle"), és olyankor az adott keresési URL **kimarad** — az egyik két Graphisoft-URL közül pontosan ez történt. Javasolt (P2, ~30 perc): `wait_until="domcontentloaded"` + a már meglévő explicit `wait_for_selector(..., state="attached")` — a tartalomra várunk, nem a hálózati csendre.

**Javítás:** a `start-monitor.bat`-ban és minden indítási útvonalon **absolute interpreter-út** (`...pythoncore-3.14-64\python.exe`), plusz indulási self-check, amely `p.chromium.executable_path` létezését ellenőrzi és `ERROR` szinten naplóz, ha nincs böngésző.

---

### 3.2 ⛔ P0 — A rendszer jelenleg egyáltalán nem fut
**Hatás: MAGAS** · **Javítási munka: 5 perc (indítás) + ~2 óra (Windows Service)**

Utolsó napló-bejegyzés: `2026-07-23 14:25:45`. Nincs futó `server.py`. Két zombi `python main.py --github` processz él, amelyek soha nem fejeződtek be (a GitHub-connectornak van `timeout=15`, tehát valószínűleg a `time.sleep(6)`-os ciklusban vagy a szülő-shellben akadtak be — ez önmagában is vizsgálandó).

A `HANDOFF.md` §7/D szerint a Windows Service + tunnel szándékosan parkolva van. **Ez a parkolás a lead-volumen szempontjából ma a második legdrágább döntés:** egy manuálisan indított konzolos processz minden gépújraindításnál, minden véletlen ablakbezárásnál csendben megszűnik, és semmi nem jelzi.

---

### 3.3 ⛔ P0 — A felhalmozott korpusz eltűnt, és nincs backup
**Hatás: MAGAS (érzékelt lead-volumen)** · **Javítási munka: ~1 óra (backup-job); az adat maga nem visszaállítható**

| Metrika | `HANDOFF.md` (2026-07-21) | Ma mérve |
|---|---:|---:|
| `posts` | 249 | **28** |
| osztályozott `signals` | 64 | 24 |
| `posts` AUTOINCREMENT számláló | — | **28** (azaz újraindítva) |
| legrégebbi `fetched_at` | — | 2026-07-22 13:11 |
| `runs` | — | 477 (érintetlen, 06-16-tól) |

A `posts`/`signals`/`drafts` táblák tartalma **és** a hozzájuk tartozó `sqlite_sequence`-sor is nullázódott, míg a `runs` megmaradt. A DB-fájl maga nem lett kicserélve (létrehozás: 2026-06-16). Ez `DROP TABLE` + `init_db()` újrafutás vagy célzott `DELETE`+`sqlite_sequence`-reset lenyomata. **A kódban nincs ilyen funkció** (végigkeresve: nincs `DELETE FROM posts` / `DROP TABLE` sehol az `ui/`, `main.py`, `storage/` alatt) — tehát kézi beavatkozás történt.

Backup nincs: a repóban egyetlen `.db` fájl van, semmilyen `.bak`/`.db-wal` snapshot.

> **Ez a legvalószínűbb magyarázata annak, hogy „a dashboard üres".** Nem a detektálás állt le először — a már meglévő 249 elem is eltűnt, és mivel a Playwright ezzel egy időben halt meg, nem is töltődött vissza.
>
> **Nyitott kérdés (K1):** szándékos volt-e ez a törlés (tiszta lap a v3 classifier miatt)? Ha igen, ez a §1/3 pont nem hiba, csak elvesztett előzmény — de a backup-hiány akkor is P0.

---

### 3.4 ⛔ P1 — revitforum.org: csendben eltört, mert a fórum platformot váltott
**Hatás: KÖZEPES** · **Javítási munka: ~10 perc (kivezetés) VAGY 3–4 óra (XenForo-újraírás, Cloudflare-kockázattal)**

86 futás, **0 begyűjtött poszt, 0 hibajelzés**. A napló pontosan megmondja, hol veszik el:

```
[revitforum] search .../search.php?keywords=archicad+ifc...: 0 elem
[revitforum] board .../revit-general-discussion: 0 elem
```

Nem a kulcsszó-szűrő dobja ki őket — **a parser nulla elemet talál**. Élő próbával kiderült, miért:

- `https://www.revitforum.org/search.php?...` → HTTP 200, de **302-vel átirányít** `/search?...`-ra, és a válasz **XenForo**-markup, Cloudflare mögött, login-fallal.
- A `html_connector._parse_phpbb_search()` **phpBB-szelektorokat** használ (`li.bg1`, `li.bg2`, `dl.row`, `a.topictitle`) — ezek XenForo-ban nem léteznek, tehát **soha, semmilyen körülmények között nem fognak illeszkedni**.
- A board-URL-t a szerver kétszer is **read timeout**-ra futtatta (Cloudflare-lassítás/throttling).

Ez a brief „csendben eltörhettek-e a szelektorok" hipotézisének **valódi találata** — csak nem a Playwright-, hanem a HTML-connectoron.

**Miért volt láthatatlan:** a `HTMLConnector.run()` csak akkor ír `error`-t a `runs`-ba, ha *kivétel* dobódik. HTTP 200 + 0 parsolt elem = tökéletesen sikeres futás a napló szerint. Ugyanez az anti-minta felelős a graphisoft/autodesk HTML-connector 155 néma nulla-futásáért is (403-at kaptak, `_safe_get` kiírta a konzolra, de a `runs`-ba nem került).

**Javaslat:** a phpBB-parsert **ne** javítsuk. A revitforum ma Cloudflare + XenForo + login — ugyanaz a kategória, mint a Khoros-fórumok, tehát ha kell, akkor Playwright-tal, `playwright.forums` alá új bejegyzésként. Első körben inkább **vezessük ki a `forums:` szekcióból**, hogy ne fusson 86-szor a semmiért, és ne generáljon hamis „minden rendben" jelet.

---

### 3.5 ⚠️ P1 — YouTube: videónként EGY komment mentődik, és nincs kulcsszó-kapu
**Hatás: KÖZEPES (rontja a jel/zaj arányt és felzabálja a Gemini-kvótát)** · **Javítási munka: ~45 perc**

Két külön hiba egy connectorban:

**(a) Hamis duplikátum-jelölés — ez a brief „storage/ tévesen már látottnak jelöl" hipotézisének igazolása.**
`connectors/youtube_connector.py:76` minden kommenthez ugyanazt az azonosítót adja:

```python
"external_id": f"yt_{video_id}",     # ← videó-ID, nem komment-ID!
```

A `posts` tábla megkötése `UNIQUE(platform, external_id)`, tehát **egy videóból pontosan egy komment kerül be, a többi 19 csendben eldobódik** (`insert_post` `IntegrityError`-t kap → `False`). A `comment_id` változó ki van olvasva (`:68`), de sehol nem használódik.

Adattal igazolva: a 3 query × 5 videó = max 15 videóból **13 poszt** van a DB-ben, mindegyik **más videó** — azaz videónként pontosan egy. Elméleti maximum 15 × 20 = 300 komment/futás helyett 15. **Kiesés: ~95% a YouTube-csatornán.** És mivel a videó-ID a második futástól már létezik, minden ismételt futás 0 újat ad (39 futásból 29 volt nulla).

**(b) Nincs kulcsszó-kapu**, ellentétben az összes többi connectorral (`:83-84`):

```python
"keywords": ", ".join(keywords) if keywords else "youtube",
"score": max(score, 1),
```

Tehát minden komment bekerül, `score ≥ 1`-gyel — és mivel `alerts.min_keyword_matches: 1`, mindegyik „relevánsnak" is számít. A mért következmény a `signals` táblában:

| Platform | Osztályozott jel | Ebből fájdalom | Átlagos severity |
|---|---:|---:|---:|
| IfcOpenShell (GitHub) | 8 | **6** | **3,00** |
| buildingsmart | 3 | 1 | 2,00 |
| **youtube** | **13** | **1** | **1,15** |

A jelenlegi DB-ben ez konkrétan azt jelenti, hogy a Gemini a következőkre költött hívást: *„Parametric Equations"*, *„Parametric Wall Art"*, *„Baixar Enscape 4.18"*, *„Introduction to Parametric Equations — Graphing"*. Ezek a `parametric conversion` kulcsszó „parametric" felére csúsztak be — de valójában a kulcsszó-kapu megkerülése engedte be őket.

**Javítás:** `external_id = f"yt_{comment_id}"` (+ egyszeri visszatöltés), és a kulcsszó-kapu behúzása a többi connectorral egyezően. Ezzel a YouTube volumene ~15×-re nő, a zaj viszont lecsökken.

---

### 3.6 ⛔ P0 — Az alerts-pipeline: a találat „elküldöttként" fogy el, de nem megy sehová
**Hatás: MAGAS (érzékelt lead = 0)** · **Javítási munka: ~20 perc (Slack bekapcsolás) + ~30 perc (kódjavítás)**

A brief kérdése: „minden detektált találat ténylegesen eljut emailig/Slackig?" **Nem, egyetlen sem.** Három egymásra rakódó ok:

**(a) Mindhárom kimeneti csatorna ki van kapcsolva** (`config.yaml`):
```yaml
alerts:
  email:   {enabled: false, ...}
  slack:   {enabled: false, webhook_url: YOUR_SLACK_WEBHOOK_URL}
  webhook: {enabled: false, url: YOUR_N8N_WEBHOOK_URL}
```
`send_alerts()` (`alerts/notifier.py:214`) így minden ágat átlép, és **csendben visszatér**.

**(b) A digest mégis elfogyasztja a posztokat.** `main.py:159-162`:
```python
send_alerts(relevant, config.get("alerts", {}))   # no-op, ha minden ki van kapcsolva
if relevant:
    mark_alerted(db_path, [p["id"] for p in relevant])   # ← státusz 'new' → 'alerted' MINDENKÉPPEN
```
Tehát a napi 8:00-as digest a teljes friss készletet `alerted`-re állítja, miközben nulla értesítés ment ki. A poszt a `status='new'` szűrőkből (`get_new_posts`, ad-hoc nézet) kiesik. **Ez pontosan az „elvész útközben" eset.**

**(c) Ha be lenne kapcsolva, sem a jó dolog mennénk ki.** A digest a **pivot előtti kulcsszó-score-ral** szűr (`min_keyword_matches: 1`), nem a `signals` tábla `is_pain`/`severity` mezőivel — a `classifier` teljesen ki van hagyva az értesítési útból. `min_score: 1`-nél gyakorlatilag **minden begyűjtött elem** bekerülne a levélbe, beleértve a „Parametric Wall Art" kommentet. A dashboard „Lehetőségek" fül (`get_opportunities`) *már* a jelekre épül — az e-mail/Slack út nem követte.

**Javítás:** (1) Slack webhook bekapcsolása (felhasználói lépés), (2) `mark_alerted` csak tényleges sikeres kiküldés után, (3) a digest forrása `get_opportunities(min_severity=3)` legyen a kulcsszó-score helyett.

---

### 3.7 ⛔ P1 — Reddit: nincs kulcs; a lefedettség viszont nem rate-limit-kérdés
**Hatás: MAGAS (a brief szerint ez az elsődleges forrás — és jelenleg 0)** · **Javítási munka: 10 perc felhasználói lépés**

`config.yaml`: `client_id: YOUR_REDDIT_CLIENT_ID`. Emiatt `main.run_reddit()` (`main.py:55-57`) minden órában kilép, mielőtt bármit tenne — a naplóban óránként ott van: `[reddit] Nincs beállítva API kulcs. Kihagy.` Ezért a `runs` táblában is csak 7 reddit-sor van (6 közülük `received 401 HTTP response`, egy korábbi, érvénytelen kulccsal).

**A brief hipotézise a rate limitről / kvótáról: nem igazolódott.** Egy teljes ciklus a jelenlegi configgal 3 subreddit × (25 új poszt + 10 poszt kommentjei + 6 keresés × 25 találat) ≈ 3 × 285 ≈ **855 elem/futás**, óránként. A PRAW OAuth-limit 100 kérés/perc csúszó ablakban, a lekérések listánként 100 elemet hoznak — ez **bőven a limit alatt van**, a `poll_interval_minutes: 60` mellett még inkább.

**A valódi korlát a lefedettség, nem a kvóta:**
- 3 subreddit (`Revit`, `ArchiCAD`, `BIM`) — hiányzik pl. `r/bimlevel`, `r/AutodeskRevit`, `r/architecture`, `r/BlenderBIM`, `r/openBIM`, és a nem angol nyelvű BIM-közösségek (a 01-es audit §11/4 pontja is előre veszi a nyelvi bővítést).
- A keresési ág `time_filter="year"` + `sort="new"` + `limit=25` — az első futás egy évet töltene vissza, utána a dedup miatt szinte mindig 0. Ez rendben van, de azt jelenti, hogy **a Reddit steady-state hozama napi néhány elem**, nem tucatok. Ne várjunk tőle csodát: a jelminősége viszont a GitHub után a legjobb lesz, mert ott valódi emberek kérdeznek.

Amíg nincs kulcs, a **dashboard „Ad-hoc keresés" funkciója is féllábú**: az `adhoc_search.py` `reddit` csatornája minden hívásnál kivételre fut.

---

### 3.8 ⛔ P1 — Stack Overflow: hibás tag-szintaxis és teljes napló-vakság
**Hatás: ALACSONY-KÖZEPES** · **Javítási munka: ~30 perc**

Két hiba:

**(a) A `tagged_queries` szintaxisa érvénytelen.** A config `revit+archicad`-ot ad meg; a Stack Exchange API tag-szeparátora a `;`, a `+` pedig URL-kódolva `%2B` lesz, tehát a kérés egy `revit+archicad` **nevű, nem létező tagre** keres. Élő mérés:

| `tagged` érték | Találat |
|---|---:|
| `revit+archicad` (jelenlegi config) | **0** |
| `revit;archicad` | 1 |
| `revit-api` (a valódi SO-tag) | 25 |
| `revit` | 25 |

Azaz a három konfigurált tag-query közül **mindhárom strukturálisan nulla találatot ad**, örökre. A `text_queries` ág működik, de a `tagged` ág halott.

**(b) A connector nem naplóz futást.** A `stackoverflow_connector.py` — egyedül az összes közül — **nem importálja és nem hívja a `log_run()`-t**. Ezért a `runs` táblában **egyetlen `stackoverflow` sor sincs**, holott az ütemező 180 percenként meghívja (`main.py:241-248`), és a napló szerint ma is futott (`[stackoverflow] 0 uj bejegyzes mentve`). A forrás állapota a DB-ből **nem megállapítható** — ez pontosan az a néma-hiba-osztály, ami az egész auditot indokolta.

Megjegyzés: a `sites` listában szereplő `softwareengineering.stackexchange` BIM-témában gyakorlatilag üres — érdemesebb a `revit-api` tagre és a `text_queries`-re szűkíteni.

---

### 3.9 ⚠️ P2 — Discourse és GitHub: működik, de a fejtér nagy része kihasználatlan
**Hatás: KÖZEPES (növelhető volumen)** · **Javítási munka: ~2-3 óra**

Ez a két connector nem hibás — csak alul van hangolva. Élő mérés a jelenlegi query-készlettel:

**buildingSMART (Discourse):**

| Query | Visszaadott poszt |
|---|---:|
| `revit archicad` | 45 |
| `archicad revit` | 45 |
| `ifc export revit` | 50 |
| `archicad ifc` | 50 |
| `latest.json` (friss témák) | **30 — jelenleg NEM használt** |

Azaz ~190 elem érkezik be minden futásnál (4 óránként), amiből 53 futás alatt 38 új keletkezett — a `/search.json` **relevancia szerint rendez**, tehát nagyjából ugyanazt a statikus top-50-et adja mindig. Nincs `order:latest`, nincs `page=` lapozás, és a `latest.json` (friss témák) végpont, amit a 01-es audit §10 külön kiemelt, nincs bekötve. **Következmény:** egy új, releváns téma csak akkor jelenik meg, ha berobban a relevancia-rangsor tetejére.

**GitHub Issues** — itt a legnagyobb a kihasználatlan fejtér, és egyben ez a legjobb jelminőségű forrás (8 jelből 6 fájdalom, átlag severity 3,0):

| Query (3 repo szűkítéssel) | `total_count` | Behozott |
|---|---:|---:|
| `archicad revit` (jelenlegi) | 30 | 20 |
| `revit archicad` (jelenlegi) | 30 | 20 |
| `archicad ifc export` (jelenlegi) | 26 | 20 |
| **`archicad`** | **103** | — |
| **`revit`** | **303** | — |

Egyetlen query-szélesítéssel ugyanabból a három repóból **~10× több issue** érhető el — és a kulcsszó-szűrő utána amúgy is szűr. Ráadásul a repo-lista mindössze 3 elemű; a 01-es audit §10 „alulértékelt aranybánya"-minősítése alapján ide tartozik még pl. `IfcOpenShell/IfcOpenShell` discussions, `buildingSMART/IFC4.x-IF`, `Autodesk-Forge`/Revit-API-repók, `blenderbim`-környék.

---

### 3.10 ✅ Kulcsszó-szűrő és classifier: NEM ez a szűk keresztmetszet
**Hatás: ALACSONY-KÖZEPES** · **Javítási munka: ~1 óra (kulcsszó-lista) ha egyáltalán akarjuk**

A brief hipotézise, hogy „a kulcsszavak/klasszifikáció túl szigorú, kidob valós releváns posztokat" — **részben igaz, de nem ez a fő ok.** A mért számok:

- A `classifier` 24 jelet állított elő, ebből **8 fájdalom (33%)** — ez a 01-es audit 1. fázisának („bizonyítsuk, hogy a jelminőség valós") **teljesülő** eredménye. A classifier helyesen szűrte ki a videótutorial-zajt (16 nem-fájdalom), és helyesen emelte ki az IfcOpenShell-issue-kat (severity 4, confidence 0,95).
- **Osztályozatlan poszt: 0.** Azaz nincs classifier-torlódás, nincs kvótafal. A `logs/monitor.log` óránként `[classifier] Nincs osztalyozatlan poszt.`-ot ír — nem azért, mert szigorú, hanem mert **nincs mit osztályozni**.
- A `classifier.enabled: true`, `delay_seconds: 13`, `batch_size: 15` beállítás óránként max 15 posztot dolgoz fel. Ha a §3.1/3.5/3.7 javítások után napi 30–80 elem érkezik, ez **elég** (napi 24×15=360 kapacitás), de a `delay_seconds: 13` × 15 = 3,25 perc/batch mellett érdemes lesz a batch_size-t 25-re emelni.

Ahol a szűrő **valóban veszít** — érdemes tudni, de ne ez legyen az első javítás:

A `filters/keyword_filter.py` többszavas kulcsszavakat AND-lookahead-dé fordít (`(?=.*\bархicad)(?=.*\brevit)`), tehát **minden találathoz legalább két konkrét token kell**. A `primary` listában a `nodu`-n kívül **nincs egyetlen egyszavas bejegyzés sem**. Következmény: egy ilyen valódi fájdalom-poszt **kiesik**:

> *„Losing element properties when importing to Revit"* → nincs benne `ifc` és nincs benne `archicad`, tehát egyetlen `primary` sem illeszkedik; a `pain_points` közül a `lost parameters` sem (a „Losing" nem `\blost`), így **0 kulcsszó → eldobva.**

Ez a Reddit- és fórum-oldalon számít a legtöbbet, ahol az emberek nem a formátumot, hanem a *tünetet* írják le („my walls break", „properties vanish", „geometry is garbage"). **De:** amíg a Reddit és a Playwright nulla üzemben van, ennek a javításának **nincs mérhető hozama** — ezért P2.

Egy apró, most is aktív probléma: az egyszavas kulcsszavak szóhatár nélküli substring-egyezést kapnak (`re.escape(kw)`), tehát a `nodu` illeszkedne pl. a „nodule" szóra is. A `parametric conversion`-nál a „parametric" fele volt az, ami a „Parametric Wall Art"-ot beengedte — de ott a valódi bűnös a YouTube-connector hiányzó kulcsszó-kapuja (§3.5).

---

### 3.11 ✅ `--schedule` és a néma hibák: az ütemező jó, a hibakezelés a probléma
**Hatás: MAGAS (közvetetten — ez tette láthatatlanná az összes fentit)** · **Javítási munka: ~3 óra**

A brief kérdése: „a `--schedule` mód megbízhatóan fut-e éles környezetben, van-e logging/error handling néma connector-hibára?"

**Ami jó** (és a 01-es audit is így értékelte): `JOB_DEFAULTS = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 300}` — helyes, nem lehet átfedő futás. A `server.py` `RotatingFileHandler` + `print()`-átirányítás jó minta, a `runs` tábla auditálható. Az ütemezés maga megbízhatóan lefut, ezt a napló igazolja.

**Ami rossz — négy egymást erősítő anti-minta:**

1. **A `main.py` wrapperek minden kivételt lenyelnek és 0-t adnak vissza**: `run_reddit`, `run_playwright`, `run_stackoverflow`, `run_discourse`, `run_github`, `run_youtube` — mind `except Exception as e: print(...); return 0`. A hívónak (ütemező) így a hiba és a „nincs új találat" azonos.
2. **A `runs.error` csak kivételt rögzít, üzleti nullát nem.** 86 revitforum-futás 0 elemmel, 0 hibával — a napló szerint minden rendben. **Nincs olyan fogalom, hogy „ez a connector N futás óta nem hozott semmit".**
3. **Egy connector (`stackoverflow`) egyáltalán nem naplóz** (§3.8b).
4. **Semmi nem riaszt.** Nincs `/health`, nincs heartbeat, nincs „connector elhallgatott" értesítés — pedig a Playwright 46 egymást követő hibás futása után is csak akkor derült ki, hogy baj van, amikor most kézzel megnéztük a `runs` táblát.

**Ez a rendszer legdrágább hibája,** mert megsokszorozza az összes többit: a Playwright 3 napig, a revitforum 5+ hétig, a Stack Overflow a kezdetektől halott volt anélkül, hogy bármi jelezte volna.

**Javaslat (a legjobb megtérülésű egyetlen fejlesztés):** connector-heartbeat. Egyszerű szabály a `runs` táblán: minden connectorhoz `expected_min_per_day` és „ha N egymást követő futás 0 új elem VAGY hibás → Slack-riasztás". Plusz a `_safe_get`/parser-nulla eset naplózása `runs.error`-ba (`"HTTP 200 de 0 parsolt elem"`).

---

### 3.12 ⚠️ P2 — A signal → outreach lánc kézi kapun ül
**Hatás: KÖZEPES (érzékelt lead-volumen)** · **Javítási munka: ~30 perc**

A `register_jobs()` (`main.py:208-315`) 11 jobot regisztrál: reddit, forums, playwright, stackoverflow, discourse, github, youtube, classifier, digest, weekly_report, linkedin_content. **A `generate_drafts` nincs köztük.**

Tehát: a classifier előállítja a 8 fájdalom-jelet → a `draft_min_severity: 3` küszöböt 8 jel közül 8 átlépi → és **egyetlen draft sem készül**, amíg valaki nem kattint a dashboardon vagy nem futtatja a `--generate-drafts`-ot. A DB-ben ma **1 draft** van összesen (state: `approved`), a `drafts` AUTOINCREMENT számláló is 1-en áll.

A 01-es audit szerint a human-in-the-loop kapu **szándékos és helyes** — de a kapu az *jóváhagyásnál* legyen, ne a *generálásnál*. Ha a draftok automatikusan elkészülnek és „pending"-ben várnak, a dashboard tele lesz döntésre kész elemekkel; ma viszont üresnek látszik.

Kapcsolódó megjegyzés: a `pain_classifier.py` docstringje azt írja, hogy a classifier **„TUDATOSAN NINCS az ütemezőben"** (és a `HANDOFF.md` §2 is ezt ismétli) — ez **elavult**: a `main.py:277-284` óta be van kötve, óránként fut. Érdemes javítani, hogy a dokumentáció ne vezesse félre a következő session-t.

---

### 3.13 ⛔ A kulcsszó-szűrő négyzetes futási idejű — ez akasztotta be a GitHub-connectort
**Hatás a lead-volumenre: MAGAS** · **Javítási munka: kész (2026-07-24)**

Ez a hiba a P1-javítások közben, mérés útján derült ki, és utólag megmagyaráz több korábbi tünetet.

A `filters/keyword_filter.py` a többszavas kulcsszavakat **egyetlen regexbe** fordította, láncolt lookahead-ekkel és `re.DOTALL`-lal, **horgony nélkül**:

```python
lookaheads = "".join(rf"(?=.*\b{re.escape(w)})" for w in words)
pattern = re.compile(lookaheads, re.IGNORECASE | re.DOTALL)
```

Horgony nélkül a `re.search` **minden kezdőpozíciótól** újrapróbálja a `.*`-os lookahead-eket → négyzetes idő. Mért értékek az éles kulcsszókészleten (59 kulcsszó, ebből 54 többszavas):

| Szöveg hossza | Régi | Új | Gyorsulás |
|---|---:|---:|---:|
| 2 KB | **2,53 s** | 2,0 ms | ~1 240× |
| 10 KB | **57,8 s** | 11,2 ms | ~5 160× |
| 30 KB | (~10 perc) | 19,7 ms | — |
| 200 KB | (gyakorlatilag végtelen) | 23,1 ms | — |

A GitHub-connector a **teljes** issue-törzsre hívta a szűrőt (a 2000 karakteres csonkolás csak a mentésnél történik), és a GitHub-issue-k logokat/stacktrace-eket tartalmaznak. Egyetlen körben mért CPU-idő: **373 másodperc**, majd beakadás.

**Amit ez megmagyaráz:** a session elején talált **két beakadt `main.py --github` processz** (mindkettő órákig élt), és az, hogy a GitHub-connector — a legjobb jelminőségű forrás — miért futott olyan lassan, hogy a körei gyakran nem is fejeződtek be.

**Javítás:** a többszavas kulcsszó szavanként külön, egyszerű `\bszó` mintát kap, és mindnek egyeznie kell. **A szemantika bitre azonos** („minden szó szerepel valahol, sorrendtől függetlenül") — 7 esetre + sorrend-függetlenségre teszttel igazolva. Plusz `MAX_TEXT_CHARS = 20 000` védvonal (a `posts.body` amúgy is 2000 karakteren csonkolódik).

---

### 3.14 ⚠️ SQLite rollback-journal: `database is locked` két processz mellett
**Hatás: KÖZEPES** · **Javítási munka: kész (2026-07-24)**

A §3.13 javítása után a GitHub-kör 6 perc helyett 21 másodperc lett — és azonnal előjött egy addig rejtett hiba: a párhuzamosan futó `server.py` (ütemező + Flask-szálak) és a CLI-futás `sqlite3.OperationalError: database is locked`-kal szakadt meg. Korábban a lassú kulcsszó-szűrő **véletlenül sorosította** a két processzt, ezért ez nem jelentkezett.

Ok: a DB rollback-journal módban volt (alapértelmezés), ahol **egy írás minden olvasót blokkol**, és a `sqlite3.connect()` alap 5 másodperces várakozása kevés.

**Javítás:** `PRAGMA journal_mode=WAL` (egy író + sok olvasó párhuzamosan; a beállítás a DB-fájlon perzisztens) + `timeout=30.0` minden kapcsolaton. Verifikálva: `journal_mode = wal`, `busy_timeout = 30000`, és a párhuzamos szerver+CLI futás hibátlanul végigment.

> Megjegyzés a 01-es audit §12-höz: a Postgres-váltás triggere ott „több párhuzamos író" volt. A WAL ezt a pontot **kitolja** — a váltás továbbra sem indokolt, de a lock-hibák miatt már nem is fog hamis riasztást adni.

---

## 4. A brief kilenc hipotézise — pontonkénti verdikt

| # | Hipotézis | Verdikt | Hatás a volumenre |
|---|---|---|---|
| 1 | A `search_connector.py` (Google CSE) volt a fő volumenforrás; pótlás nélkül lyuk maradt | **Részben.** Fő volumenforrás **nem** volt: a `runs` szerint 4 futás alatt **0 posztot** termelt (már 403-cal). A teljes 249-es korpuszt a playwright+youtube+discourse+github összege (270) magyarázza. Pótlás **valóban nincs** beépítve — a `SearchProvider` adapter üres hely | **ALACSONY** volumenre, **KÖZEPES** lefedettségre |
| 2 | Discord nincs implementálva, LinkedIn scraping tiltott — mekkora a kiesés? | **Igaz, de most irreleváns.** Egyik sem kérdés-orientált forrás (a LinkedIn engagement-, nem support-csatorna), és mindkettő ToS/GDPR-terhelt (01-es audit §10/§11). Amíg **négy meglévő** forrás nullán van, egy új csatorna hozzáadása a rossz optimalizálás | **ALACSONY** |
| 3 | A Playwright-szelektorok csendben eltörhettek (0 találat) | **NEM igazolódott a Playwrighton** — a szelektorok 07-21-én működtek (157 poszt); a hiba interpreter-eredetű (§3.1). **DE igazolódott a HTML-connectoron:** a revitforum phpBB-szelektorai a XenForo-migráció óta halottak, 86 futás 0 elemmel, 0 hibával (§3.4) | **MAGAS** (Playwright) + **KÖZEPES** (revitforum) |
| 4 | Reddit: csak 3 subreddit; van-e rate limit / kvótakorlát? | **Rate limit NEM.** ~855 elem/futás óránként, jóval a PRAW 100 kérés/perc alatt. A valódi probléma: **nincs API-kulcs**, tehát 0 elem; másodsorban a 3-subreddites lefedettség (§3.7) | **MAGAS** (kulcs) / **KÖZEPES** (lefedettség) |
| 5 | A kulcsszavak/klasszifikáció túl szigorú, kidob valós posztokat | **Részben.** A classifier **jól működik** (33% fájdalom-arány, 0 torlódás). A kulcsszó-előszűrő viszont minden találathoz **két konkrét tokent** kér, így a tünet-leíró posztok („losing element properties when importing to Revit") kiesnek. **De ma nincs mit kidobni** — nincs bejövő anyag (§3.10) | **KÖZEPES**, de csak a többi javítás UTÁN mérhető |
| 6 | `--schedule` megbízhatóan fut-e; van-e logging néma connector-hibára? | **Az ütemező jó, a hibakezelés nem.** A `runs.error` csak kivételt lát, az „üzleti nulla" láthatatlan; egy connector (`stackoverflow`) egyáltalán nem naplóz; nincs heartbeat/riasztás. **Ez tette 3 nap–5 hét hosszúságúvá az összes kiesést** (§3.11). Ráadásul **jelenleg egyáltalán nem fut** semmi (§3.2) | **MAGAS (közvetett)** |
| 7 | A dedup tévesen „már látott"-nak jelöl új posztokat | **IGAZOLÓDOTT, a YouTube-connectoron.** `external_id = f"yt_{video_id}"` minden kommenthez → videónként 1 komment mentődik, ~19 csendben eldobódik. A `storage/db.py` dedup-logikája maga **helyes** (§3.5a). Másodlagos: az `insert_post` 365 napnál régebbi posztot is csendben `False`-szal dob el, megkülönböztethetetlenül a duplikátumtól | **KÖZEPES** |
| 8 | Az alerts-pipeline: minden találat eljut e-mailig/Slackig? | **NEM, egyetlen sem.** Mindhárom csatorna `enabled: false`, `send_alerts()` no-op — a digest mégis `alerted`-re állítja a posztokat, azaz **elfogyasztja őket kiküldés nélkül**. Ha be lenne kapcsolva, akkor is a pivot előtti kulcsszó-score-t (`min_score: 1`) küldené, nem a `signals` fájdalom-jeleit (§3.6) | **MAGAS** |
| 9 | Az `N8N_SETUP.md` szerinti n8n-integráció működik-e még? | **Nem működik, és szándékosan.** A dokumentum saját fejlécében `⚠️ ELAVULT (2026-07-20)`, a Pipedrive kikerült. **Törés viszont van a helyén:** a 01-es auditban eldöntött pótlás (**közvetlen `POST /api/bridge/ingest`** a SalesOS-be) **nincs implementálva** — az `ui/app.py:331` „to-sales-os" gomb valójában az **n8n webhookot** hívja (`alerts.webhook`), ami `enabled: false`, tehát a gomb minden kattintásra hibát ad. A repóban nincs `BRIDGE_API_KEY`, nincs `ingest` hívás | **KÖZEPES** (a CRM-átadás, nem a detektálás) |

**Kiegészítés a briefben nem szerepelt, de a mérés kidobta:** a felhalmozott korpusz (249 → 28 poszt) elvesztése backup nélkül (§3.3), és a `generate_drafts` kimaradása az ütemezőből (§3.12).

---

## 5. A Google CSE pótlása — melyik éri meg most

Először a fontos keretezés: **ez nem P0.** A CSE mérhetően 0 posztot termelt, míg a Playwright 157-et; egy új kereső-API bekötése ~4 óra, ugyanannyi, mint a §3.1–3.8 összes javítása együtt, viszont **nagyságrenddel kevesebb elemet** hoz. A kereső-adapter értéke nem a volumen, hanem a **lefedettség**: azok a fórumok/blogok/Q&A-oldalak, amikre nincs saját connector (Reddit-tükrök, német/holland BIM-fórumok, LinkedIn *publikus* posztok, Graphisoft-blogkommentek).

| Opció | Index | Ár (nagyságrend) | Előny | Hátrány |
|---|---|---|---|---|
| **Brave Search API** | saját, független | **$5 / 1 000 kérés, havi $5 ingyenes kredittel → ~1 000 kérés/hó ingyen**, 50 QPS *(2026-07-24-én az oldalról ellenőrizve; a korábbi „~2 000 query/hó ingyenes szint" ebben a dokumentumban téves volt)* | **Self-serve, ma is nyitva**; nincs ToS-szürkezóna; független a Google-től; a napi 11 query-s valós igény (~330/hó) az ingyenes keret harmada | Kisebb index, mint a Google — niche fórumoknál gyengébb recall. A regisztráció CAPTCHA-t tartalmaz |
| Serper.dev | Google SERP proxy | ~1 USD/1 000 query, pár ezer ingyenes kredit | **Legjobb recall** (Google indexe), legalacsonyabb egységár | Scraping-proxy → ToS-szürke, egyetlen szolgáltatóra épülő függőség, jogi/üzletmenet-kockázat |
| Bing Search API | Microsoft | — | — | **Nem opció:** a self-serve Bing Search / Custom Search API-kat a Microsoft 2025 augusztusában kivezette (helyette Azure AI „Grounding with Bing"). *Döntés előtt 5 perc ellenőrzést érdemel* |
| Exa | neurális/szemantikus | ~5 USD/1 000 (neural) | Fájdalom-szemantikára keres, nem kulcsszóra — „találj hasonló panaszt" | Drágább; monitoringra túlzás, felderítésre viszont erős |

**Javaslat: Brave Search API, `SearchProvider` adapter mögött (a 01-es audit §5 szerinti interfésszel), P2 prioritással.**

Indoklás: (a) ma önállóan regisztrálható, nincs várólista, nincs „új ügyfeleknek zárva" kockázat — pontosan az a hiba ölte meg a CSE-t; (b) a rendszer valós query-igénye (10–20/nap) elfér a legalacsonyabb szinten, tehát ~0 Ft; (c) nem scraping-proxy, tehát nem ismétli meg a Khoros-403 típusú jogi/technikai törékenységet; (d) az adapter mögött a Serper 30 perc alatt betehető **második** providerként, ha a recall kevés — és pont ez volt az adapter-interfész értelme.

### 5a. Reddit a kereső-adapteren keresztül (2026-07-24, a Reddit-kulcs elakadása után)

Felmerült egy kézenfekvő terv: *Google CSE → `site:reddit.com` → Reddit `.json` végpont → poszt + kommentek letöltése → AI-elemzés → scoring → CRM*. A lánc két eleme nem működik, kettő viszont jó:

| Lépés | Verdikt |
|---|---|
| Google CSE | ⛔ **Halott** — a Google lezárta új ügyfelek elől, ebben a projektben 403-mal verifikálva (§4/1). Helyette Brave, az adapter már kész |
| `site:reddit.com` kereséssel | ✅ **Legális és hasznos** — a kereső *indexét* fogyasztjuk (cím + URL + kivonat), nem a Redditet crawlerezzük |
| Reddit `.json` végpont letöltése | ⛔ **Nem működik és tiltott.** A `reddit.com/robots.txt` élőben ellenőrizve: `User-agent: * / Disallow: /`. Az unauthenticated `.json` 2026 májusa óta 403 (TLS-fingerprint + IP-reputáció-ellenőrzés) — tehát nem is "kockázatos", hanem egyszerűen elérhetetlen. Ez ugyanaz a ToS-szürke kategória, amit a 01-es audit §10 a LinkedIn-nél elvetett |
| AI-elemzés → scoring → CRM | ✅ **Már kész** — classifier, severity→score leképezés, SalesOS ingest (élesben verifikálva) |

**Amit ebből megvalósítottunk:** 4 `site:reddit.com` query a `web_search.queries`-be. A classifier a Reddit-poszt **címéből + kivonatából** dolgozik — ez kevesebb, mint a teljes szál, de a fájdalom-döntéshez gyakran elég („IFC export loses all parameters" önmagában is beszédes). A szálat **ember nyitja meg** a linkről; automatikus letöltés nincs.

**Amit ez nem ad:** a kommentek szövegét. Ez valós veszteség — a Redditen sokszor a kommentekben van a fájdalom részlete. A teljes szál csak jóváhagyott API-kulccsal jön (PRAW, 60–100 kérés/perc), ezért a jóváhagyási folyamat végigvitele továbbra is a helyes hosszú távú út; a kereső-út a híd addig.

**Eredmény az első éles futásból (2026-07-24):** 94 új poszt, ebből **35 reddit.com** — a Reddit-tartalom tehát API-kulcs nélkül is elindult. Ráadásul a kereső **két olyan forrást is felhozott, ami eddig egyetlen connectorban sem szerepelt**, és a 01-es audit forráslistáján sem volt:

| Forrás | Miért érdekes |
|---|---|
| `community.osarch.org` | openBIM/IfcOpenShell-közösség, Discourse-alapú → **saját connectorral is lefedhető** (a meglévő `discourse_connector` egy config-sorral) |
| `speckle.community` | Egy **versenytárs** (Speckle) saját fóruma — ott a felhasználók pont az interop-fájdalmukról beszélnek |
| `support.graphisoft.com` | Graphisoft *support*-cikkek (pl. „Unable to import a Revit file into Archicad") — a Playwright-connector csak a fórumot látja, ezt nem |

Ez a kereső-adapter fő haszna: nem a volumen, hanem hogy **megmutatja, hol vannak a lefedetlen források**. Az OSArch bekötése a következő kézenfekvő lépés (P3).

---

**Amit ne tegyünk:** ne kötsünk egyszerre két providert, és ne a keresővel kezdjük. Egy `SearchProvider` interfész + Brave implementáció + 2-3 mentett query (`"archicad revit" ifc site:forum`-típusú), heti ütemezéssel — ennyi elég, hogy a lefedettségi lyuk be legyen tömve.

---

## 6. Priorizált akcióterv

### P0 — Ma (összesen ~2 óra, ebből 25 perc felhasználói lépés)

**Állapot: 2026-07-24-én elvégezve, a 3. és 4. pont kivételével (azok felhasználói lépések).**

| # | Teendő | Hatás | Munka | Állapot |
|---|---|---|---|---|
| 1 | **Interpreter-fix:** minden indítási útvonal (`start-monitor.bat`, `.claude/launch.json`, HANDOFF) absolute `pythoncore-3.14-64\python.exe`-t használjon; a WindowsApps-alias tiltása. Az összes zombi processz kiölése indítás előtt (HANDOFF §4/6) | Visszahozza a volumen 58%-át | 15 perc | ✅ **kész** — `.claude/launch.json` absolute útra állítva (a `start-monitor.bat` már helyes volt); 2 zombi processz kilőve; `server.preflight()` mostantól ERROR-t naplóz, ha WindowsApps-alias fut vagy nincs Chromium |
| 2 | **Szerver újraindítása** + annak ellenőrzése, hogy a Playwright-futás nem hibás a `runs`-ban | A begyűjtés újraindul | 5 perc | ✅ **kész** — `preflight: Playwright chromium OK`, a Graphisoft/Autodesk scraping újra fut |
| 3 | **Reddit API-kulcs** beállítása (reddit.com/prefs/apps → script → `http://localhost:8080`) | A brief szerinti elsődleges forrás élesedik | 10 perc (user) | ⏳ **felhasználói lépés** |
| 4 | **Slack webhook** bekapcsolása (`alerts.slack`) | A találat végre elér valakit | 15 perc (user) | ⏳ **felhasználói lépés** |
| 5 | **`mark_alerted` csak sikeres kiküldés után** (`main.py:159-162`) | Megszűnik a „csendben elfogyasztott lead" | 20 perc | ✅ **kész** — `send_alerts()` mostantól a tényleg kiszolgált csatornák listáját adja vissza; a digest csak akkor lép státuszt, ha volt kiküldés, egyébként figyelmeztetést naplóz. Élesben tesztelve: 27 találat `new`-ban maradt |
| 6 | **DB-backup job:** napi `VACUUM INTO` snapshot 7 napos rotációval | Nincs több 249→28 esemény | 45 perc | ✅ **kész** — `storage/backup.py`, napi 03:30-as ütemezett job, `config.yaml → backup`, `main.py --backup` CLI. Első snapshot elkészült; a rotáció külön tesztelve |

### P1 — Ezen a héten (összesen ~1 nap)

**Állapot: 2026-07-24-én elvégezve, plusz két menet közben felderített hiba (§3.13, §3.14).**

| # | Teendő | Hatás | Munka | Állapot |
|---|---|---|---|---|
| 7 | **Connector-heartbeat:** N egymást követő 0-új/hibás futás → Slack-riasztás; a parser-nulla (`HTTP 200, 0 elem`) írása `runs.error`-ba; `log_run()` bekötése a `stackoverflow_connector`-ba | **A legjobb megtérülés** — ez fedte volna fel az összes fenti hibát napokkal korábban | 3 óra | ✅ **kész** — új `runs.items_seen` oszlop (migrációval): ez választja el a „nincs új tartalom"-ot a „nem lát semmit"-től. Mind a 7 connector jelenti. `get_connector_health()` + `send_health_alert()` + 6 óránkénti job + `main.py --health`. A detektálás szintetikus adaton tesztelve: a 0-új-posztos egészséges connectort **nem** jelzi, a vak/hibás kettőt igen |
| 8 | **YouTube `external_id` javítás** (`yt_{comment_id}`) + kulcsszó-kapu behúzása a többi connectorral egyezően | ~15× több komment, kevesebb Gemini-zaj | 45 perc | ✅ **kész** — mérve: 15 → **117 komment/kör** átvizsgálva, és a kör 11 új posztot mentett. A kapu a *komment* szövegére szűr, nem a videócímre (különben egy releváns videó összes kommentje bejönne) |
| 9 | **revitforum kivezetése** a `forums:` szekcióból (a phpBB-parser halott; ha kell, később Playwright-tal) | Megszűnik 86 hamis „minden rendben" futás | 10 perc | ✅ **kész** — `forums: {}`, plusz a `html_connector` mostantól `runs.error`-t ír, ha HTTP 200 mellett 0 elemet parsol |
| 10 | **Stack Overflow tag-fix:** `tagged: revit-api` (`;`-szeparátor), `softwareengineering` elhagyása | 0 → ~25 elem/futás | 30 perc | ✅ **kész** — mérve: 0 → **51 elem/kör**, és az első körben **5 új poszt** (a connector eddig egyetlen posztot sem termelt) |
| 11 | **Digest átkötése a `signals`-ra:** `get_opportunities(min_severity=3)` a kulcsszó-score helyett; `min_keyword_matches` elhagyása döntési szerepből | Az értesítés végre jelet küld, nem zajt | 1 óra | ✅ **kész** — a digest most severity + `pain_summary` + buying-intent szerint listáz (`alerts.digest_min_severity: 3`), és csak a még ki nem riasztott posztokat. A Slack/e-mail formázó is megkapta a fájdalom-mezőket |
| 12 | **`generate_drafts` bekötése az ütemezőbe** (napi 1×, `draft_min_severity: 3`) | A dashboard döntésre kész elemekkel töltődik | 30 perc | ✅ **kész** — napi 07:30, `responder.auto_generate` kapcsolóval |
| 13 | **GitHub query-szélesítés:** `archicad`, `revit`, `ifc` önálló query-ként + 2-3 új repó | ~10× több issue a legjobb jelminőségű forrásból | 45 perc | ✅ **kész** — 3 → 6 query, mérve **100 issue/kör** (volt ~60) és **33 új poszt** az első körben. A repo-lista bővítése P2-ben marad (token nélkül 10 kérés/perc a plafon) |
| +14 | **Kulcsszó-szűrő négyzetes futási ideje** (§3.13) — menet közben felderítve | Ez akasztotta be a GitHub-connectort, 373 s CPU/kör | 1 óra | ✅ **kész** — 10 KB-on 57,8 s → 11,2 ms, szemantika bitre azonos (teszttel igazolva) |
| +15 | **SQLite WAL-mód** (§3.14) — a gyorsítás után előjött `database is locked` | Két processz (szerver + CLI) egyszerre már nem üti ki egymást | 20 perc | ✅ **kész** — `journal_mode=WAL` + `timeout=30` |
| +16 | **Classifier `batch_size` 15 → 25** | 93 poszt/este mellett a 15-ös batch nem gyűrte le a beérkezőt | 5 perc | ✅ **kész** |

### P2 — Utána (a mérés fényében újraértékelve)

**Állapot: 2026-07-24-én elvégezve, a Windows Service kivételével (ld. lent).**

| # | Teendő | Hatás | Munka | Állapot |
|---|---|---|---|---|
| 14 | **Discourse `latest.json` + `order:latest` + lapozás** | Friss témák eddig láthatatlanok voltak | 2 óra | ✅ **kész** — minden query lefut relevancia- **és** friss-rendezéssel, plusz a `/latest.json` 30 friss témája. Mérve: **190 → 514 elem/kör**, és 5 új poszt egy addig kimerült forrásból. Menet közben kiderült, hogy a fórum szigorúan rate-limitel (429), ezért 3 s késleltetés + 1 lap/query, és a 429 mostantól bekerül a `runs.error`-ba |
| 15 | **Reddit lefedettség:** +3-5 subreddit; a keresési query-készlet a `pain_points` listából generálva | Több jó jel | 1 óra | ✅ **kész** — 3 → **8 subreddit**; a kódba égetett 6 fix query helyett a `keywords.primary` + `pain_points` többszavas kifejezéseiből épül (max 12), tehát egy új kulcsszó az Adminban automatikusan új keresés is lesz. **Élesben csak a Reddit-kulcs beállítása után mérhető** |
| 16 | **Kulcsszó-előszűrő lazítása** | A tünet-leíró posztok bekerülnek — a classifier amúgy is kiszűri a zajt | 1-2 óra | ✅ **kész** — szóhatár + toldalék-tolerancia (3+ karakteres tokenre), és **29 új tünet-kulcsszó**. Az audit §3.10 példája (*„Losing element properties when importing to Revit"*) mostantól átjut; 12 esetes teszt, benne két guard: `to`→`tool` és `nodu`→`anodus` **nem** egyezhet |
| 17 | **`SearchProvider` adapter + Brave Search** (§5) | Lefedettségi lyuk betömése | 4 óra | ✅ **kész és élesben fut** (kulcs 2026-07-24-én beállítva). A parser mezőnév-feltételezései (`title`/`url`/`description`/`page_age`/`age`) mind igazolva. Első futás: **199 találat → 94 új poszt**. Egy hangolás kellett: `freshness` **`pm` → `py`** — a szűk időkeret miatt a Brave részleges egyezésekre esett vissza (az „IFC" a filmes Independent Film Channel is: 4 találat, mind mozi-szál). `py`-vel 10/10 átmegy a kulcsszó-szűrőn, és mind 1 éven belüli. A query-k is problémára hangolva („export", „import problem", „parameters lost"), mert a puszta „archicad revit" összehasonlító threadeket hoz |
| 18 | **SalesOS `POST /api/bridge/ingest` közvetlen hívás** | A lead eljut a CRM-be | 3 óra | ✅ **kód kész** — `crm/salesos_client.py`, a dashboard „to-sales-os" gombja átkötve az n8n-webhookról. A SalesOS **account-centrikus: cég-adat nélkül 422**, ezért a cégnevet a felhasználó adja meg (ez a 01-es audit §6 szerinti tervezett emberi kapu, nem hiány). `severity × 2` → 0–10 score-leképezés. **Élő POST-ot nem futtattam** — az CRM-rekordot hozna létre |
| 19a | **`/health` endpoint** | Külső felügyelet észreveszi a néma hibákat | 1 óra | ✅ **kész** — `GET /health`, HTTP **503** ha bármely aktív connector hibás/vak, 200 ha rendben |
| 19b | **Windows Service** | Nincs több „valaki bezárta az ablakot" | 2 óra | ⏸️ **NEM csináltam meg** — rendszerszintű beállítást módosítana, és a HANDOFF §7/D szerint ezt korábban kifejezetten parkoltattad. Döntésre vár (ld. K6) |

### Amit NE tegyünk most
Discord-bot, LinkedIn-scraper, új nyelvi források, szemantikus dedup, Postgres-migráció, vektor-DB. Mindegyiket a 01-es audit is későbbre teszi, és mind **új** kapacitást épít egy olyan rendszerre, amelynek a **meglévő** kapacitása négyötödében nem üzemel.

---

## 7. Mit várhatunk a javítások után

Nem szeretném felülígérni — a 01-es audit §11/4 pontja („lehet, hogy heti 2-3 valódi opportunity van összesen") szerintem továbbra is helyes, és a mostani mérés is ezt támogatja. A reális becslés a P0+P1 után:

| Metrika | Audit előtt | Becslés P0+P1-re | **Mérve 2026-07-24 este (P0+P1+P2 után)** |
|---|---:|---:|---:|
| Aktív begyűjtő | 2 (github, discourse) | 6 | **5** (reddit kulcsra, websearch Brave-kulcsra vár) |
| `posts` a DB-ben | 28 | — | **214** |
| Nyers elem / kör (összes forrás) | ~0 | — | **~880** (discourse 410, youtube 129, github 120, SO 51, playwright 47) |
| Osztályozott jel / fájdalom | 24 / 8 | — | **72 / 27** |
| Néma hiba észlelési ideje | ∞ | < 1 nap | **< 6 óra** (heartbeat-job + `/health`) |
| Megkeresésre érdemes opportunity / hét | 0 | **2–5** | *még korai — 1-2 hét adat kell* |

Forrásonkénti mérés az új kóddal (`runs.items_seen` alapján):

| Connector | Nyers elem/kör | Új poszt/kör | Előtte | Jelminőség (fájdalom/jel) |
|---|---:|---:|---|---|
| playwright (Graphisoft+Autodesk) | 47 | **26–30** | 0 (halott böngésző) | autodesk 11/31, graphisoft 1/6 |
| discourse | **410** (volt 190) | 5 az első bővített körben | kimerült query-készlet | 3/8 |
| github | **120** (volt ~60) | **33** az első körben | gyakran beakadt kör | **11/14, átlag sev 3,21** |
| youtube | **129** (volt ~15) | 11 | max 1 komment/videó | 1/13 → ld. K3 |
| stackoverflow | **51** (volt 0) | 5 | 0, és nem is naplózott | még kevés adat |
| revitforum | — | — | kivezetve | — |
| websearch (Brave) | — | — | új | kulcsra vár (K7) |

A jelminőség-oszlop megerősíti a 01-es audit §10 „alulértékelt aranybánya" minősítését a GitHubra: 14 jelből 11 valódi fájdalom, 3,21-es átlagos súlyossággal — messze a legjobb arány. Az Autodesk-fórum nagy volument ad (89 poszt) de gyengébb arányt (11/31, átlag 1,77).

Az utolsó sor a termék valódi KPI-ja (01-es audit §4/2: „napi 3 jó opportunity többet ér, mint 300 link"), és szándékosan nincs kitalált szám mögé írva: ehhez 1-2 hét éles adat kell. A **néma hiba észlelési ideje** viszont az, ami eldönti, hogy a KPI tartható-e — ezért volt a heartbeat a P1 élén.

---

## 8. Nyitott kérdések (döntés kell, nem tippelek)

| # | Kérdés | Miért fontos |
|---|---|---|
| **K1** | A `posts`/`signals`/`drafts` táblák 2026-07-22-i kiürítése (249 → 28) **szándékos** volt-e (pl. tiszta lap a `gemini-2.5-flash-v3` classifier-verzióhoz)? | Ha szándékos, akkor nem hiba, csak elvesztett előzmény — de a backup-hiány akkor is P0. Ha nem, érdemes megérteni, mi tette |
| **K2** | A **revitforum.org**-ot vezessük ki véglegesen, vagy építsük újra Playwright-tal (Cloudflare + login mögött van)? | 10 perc vs. 3–4 óra + folyamatos törékenység. A jelsűrűsége mérhetetlen, mert soha nem termelt adatot |
| **K3** | A **YouTube-csatornát** egyáltalán akarjuk-e? A javítás után 117 komment/kör jön be, ebből a kulcsszó-kapu 11-et engedett át — de a korábbi mért fájdalom-arány 13-ból 1 (~8%). A digest `severity ≥ 3` küszöbe már kivédi a zajt, a Gemini-hívást viszont nem | Ha az első 1-2 hét után a YouTube-jelek fájdalom-aránya továbbra is ~10% alatt van, érdemes kivezetni a GitHub/Reddit javára — a döntéshez most már van mérőszám |
| **K4** | A **Slack** vagy az **e-mail** legyen az elsődleges riasztási csatorna? | A `notifier.py` mindkettőt tudja; a Slack Block Kit-es út a kidolgozottabb, de az e-mail nem igényel workspace-t |
| **K5** | ~~A **SalesOS ingest** átkötése (P2/18) mehet-e a P1-be?~~ **Megválaszolva: elkészült.** A „Sales OS" gomb most `prompt()`-tal kéri a cégnevet (+ opcionális domaint), és közvetlenül POST-ol az ingestre | A `prompt()` szándékosan minimális: nem akartam UI-elhelyezési döntést hozni helyetted. Ha a Lehetőségek fülön inline mezőt szeretnél a kártyán, az ~30 perc — szólj |
| **K6** | **Windows Service** (P2/19b): regisztráljuk? Ez rendszerszintű beállítást módosít, és korábban kifejezetten parkoltattad (HANDOFF §7/D) | Ma a monitor egy manuálisan indított konzolos processz: minden gépújraindításnál és véletlen ablakbezárásnál csendben megszűnik. A `/health` végpont már kész, tehát egy külső watchdog azonnal használhatja. Alternatíva service helyett: Feladatütemező „bejelentkezéskor indul" bejegyzés — kevésbé invazív |
| **K7** | Kérsz-e **Brave-kulcsot** (`BRAVE_API_KEY` a `.env`-be)? A web-kereső kód kész, de kulcs nélkül minden körben kihagyja magát | Ez az egyetlen lefedettségi forrás a saját connectorok által nem fedett területekre (DE/NL/skandináv fórumok, publikus LinkedIn). Ingyenes szint elég. **Az első éles futásnál a Brave válasz-mezőneveit verifikálni kell** — kulcs nélkül ezt nem tudtam megtenni |

---

*— Lead-volumen audit vége. Kódmódosítás ebben a körben nem történt.*
