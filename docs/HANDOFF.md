# HANDOFF — NODU Monitor fejlesztés folytatása

**Dátum:** 2026-07-26 (előző: 2026-07-25) · **Projekt:** `C:\NODU\Sales system\Nodu sales dashboard` · **Cél:** ha ezt egy új Claude Code session-ben olvasod, ez alapján folytasd — ne kelljen újra felfedezni a kontextust.

> **Legutóbb (2026-07-26):** (1) OSArch bekötve (§7/A ✅) — kiderült, hogy **Vanilla Forums, nem Discourse**, ezért új `vanilla_connector.py` lett belőle; `posts` 463 → **534**. (2) A „Nyers leadek" fül két hibája javítva: a pill-szűrő (§7/I ✅) és a 100-as limit (§7/J ✅ — valódi totál + lapozás). (3) **Speckle bekötve** — Discourse, de robots miatt keresés nélkül; **82,9% fájdalom-arány**, a második legjobb forrás. `posts` 463 → **694**. (4) Két elvi döntés beépítve: a Speckle-re **nem készül válasz** (§7/K), és **egyik Discourse-fórumon sem keresünk** többé a robots.txt miatt (§7/L). (5) **support.graphisoft.com bekötve** (§7/M) — Zendesk KB, intelligencia-forrásként, nem leadként. `posts` 463 → **914**, a P3-as lefedetlen források listája elfogyott. **A következő lépés a §7/C: Slack-webhook** — nyitott döntés nincs, ez felhasználói lépés (webhook-URL kell Zoltántól). — ez az egyetlen dolog, ami miatt a kész riasztási lánc még nem ér el senkit (a legutóbbi futásnál is 86 találat maradt `new`-ban, mert nincs hova kiküldeni).
>
> **Előtte (2026-07-24/25):** lead-volumen audit + a P0/P1/P2 javítási kör. A rendszer négy néma hibából állt vissza; `posts` 28 → 402. Részletek: `docs/02-lead-volume-audit-2026-07.md`.

---

## 1. Mi ez a projekt most?

A NODU Monitor **2026-07-19-én pivot-döntést kapott**: hírfigyelőből (Reddit/fórum scraper) **AI-alapú Buying Signal Detection Engine**-né vált. Cél: Archicad↔Revit BIM-interop fájdalmat kifejező bejegyzéseket találni a neten, AI-val kiszűrni a valódi fájdalmat a puszta kulcsszó-egyezéstől, és válasz-javaslatokat generálni, amik a NODU Bridge terméket (vagy tágabban a nodu.build céget) pozicionálják, ahol releváns.

**Alapdokumentum, ha mélyebbre kell menni:** `docs/01-architektura-audit-2026-07.md` — a teljes stratégiai audit, roadmap, adatmodell-tervek.

---

## 2. Architektúra — mi hol van

```
main.py                    — CLI belepesi pont (lasd §5 a flag-listaert)
server.py                  — Flask + APScheduler egyproceszes szerver (waitress)
config.yaml                — MINDEN config itt (API kulcsok, connector-beallitasok)

env_secrets.py             — titkok env-bol vagy a projekt .env-jebol (BRIDGE_API_KEY,
                             BRAVE_API_KEY). A regi kulcsok maradtak a config.yaml-ben.

crm/salesos_client.py      — SalesOS `POST /api/bridge/ingest` KOZVETLENUL, n8n nelkul.
                             Ceg-adat nelkul a SalesOS 422-t ad (account-centrikus), ezert
                             a cegnevet a dashboard kerdezi meg a felhasznalotol.
                             severity(1-5) x 2 -> SalesOS score(0-10).

connectors/                — adatgyujtes (mind insert_post()-ba ir)
  search_provider.py          — SearchProvider interfesz + Brave implementacio (CSE-potlas)
  web_search_connector.py     — a provider mogotti web-kereses; kulcs nelkul kihagyja magat
  reddit_connector.py         — PRAW, KULCS MEG NINCS BEALLITVA (§7)
  discourse_connector.py      — KET Discourse-forum: buildingSMART + Speckle.
                                Per-forum kapcsolok: use_search (robots!), search_pages,
                                include_latest, latest_pages (a /latest.json is lapoz)
  zendesk_connector.py        — Graphisoft support KB (Zendesk Help Center API).
                                NEM leadforras: staff irja, kommentek tiltva, nincs
                                kit megszolitani. updated_at-et ir created_at-be (§7/M)
  vanilla_connector.py        — OSArch community.osarch.org (Vanilla Forums, NEM Discourse!)
                                /api/v2/discussions (friss temak TELJES torzzsel) +
                                /search.json?Search= (lapoz, komment-szintu talalattal)
  github_connector.py         — IfcOpenShell/speckle-server/xeokit-sdk issue-k
  playwright_connector.py     — Graphisoft+Autodesk Khoros-scraping (headless Chromium)
  html_connector.py           — RevitForum (sima HTTP)
  stackoverflow_connector.py  — Stack Exchange API
  adhoc_search.py             — dashboard "Ad-hoc kereses" fül motorja (reddit+SO)

classifier/
  pain_classifier.py        — A RENDSZER AGYA. Egyetlen strukturalt Gemini-hivas
                               posztonkent: is_pain, severity(1-5), pain_summary,
                               buying_intent, role_hypothesis, stb. -> signals tabla.
                               CLI: python main.py --classify / --review-signals
                               TUDATOSAN NINCS az utemezoben — kezi kapudontes-fazis.

storage/db.py               — SQLite helperek (WAL-mod!). Tablak: posts, signals, drafts, runs.
                               Kulcs fuggvenyek: get_opportunities, get_post_with_signal,
                               get_pain_posts_without_draft, get_recent_pain_signals,
                               get_connector_health (nema hibak felderitese).
                               A `runs.items_seen` a NYERS elemszam — ez valasztja el a
                               "nincs uj tartalom"-ot az "eltort connector"-tol.
storage/backup.py           — napi VACUUM INTO snapshot a backups/-ba, 7 napos rotacio

responder/draft_generator.py — MINDEN AI-valaszgeneralas EZ A FAJL:
  generate_draft_for_post()    — 1 poszthoz valasz (Lehetosegek ful "Valasz generalasa" gomb)
  generate_drafts()             — batch, pain-jelekbol (severity>=3), --generate-drafts
  is_platform_excluded()        — responder.exclude_platforms kapu (ma: speckle, §7/K).
                                   MINDKET generalasi ut ezen megy at
  generate_linkedin_content()   — heti sajat LinkedIn poszt-javaslatok (Slack-re)
  generate_linkedin_reply()     — LinkedIn Valasz ful: beillesztett posztra valasz,
                                   3-agu dontessel (bridge/nodu/none fit_type)
  review_drafts()                — interaktiv CLI jovahagyas

ui/app.py                   — Flask route-ok. Kulcs route-ok:
                               /dashboard, /admin, /linkedin/compose, /lead/<id>/draft
ui/templates/dashboard.html — Sales-nezet: Attekinto, Lehetosegek, Ad-hoc kereses,
                               LinkedIn valasz, Valasztervezetek fulek
ui/templates/admin.html     — Technikai nezet: API kulcsok, connector-inditas gombok
ui/static/nodu.css          — Az EGYETLEN CSS fajl, minden ful ebbol epitkezik
                               (.opp-card/.sev-badge/.sev-hot/.sev-warm/.sev-cool mintak)

docs/
  01-architektura-audit-2026-07.md  — a nagy strategiai dokumentum
  02-opportunities-ui-spec.md       — Lehetosegek ful munkaparancsa (kesz)
  03-linkedin-composer-spec.md      — LinkedIn valasz ful munkaparancsa (kesz)
  HANDOFF.md                        — EZ A FAJL
```

---

## 3. Amit ez a session megepitett és tesztelt (2026-07-19 — 2026-07-21)

- **0. fázis (stabilizálás):** Playwright élesítve (Graphisoft+Autodesk), Google CSE kód teljesen kivezetve (halott API), Discourse + GitHub connector hozzáadva.
- **Pain Classifier:** `signals` tábla, `pain_classifier.py`, CLI (`--classify`, `--review-signals`). Élőben tesztelve: **64 poszt osztályozva, 249 összes poszt** a DB-ben.
- **Lehetőségek fül:** a `signals` tábla böngészhető a dashboardon, severity-jelvényekkel, "Válasz generálása" gombbal (ami a `pain_summary`-ra reflektáló draftot ír).
- **LinkedIn válasz fül:** beilleszthető poszt → 3-ágú döntés (bridge/nodu/none) → válasz + indoklás + másolás-gomb + törlés-gomb.
- **Heti LinkedIn poszt-javaslatok átkötve** a nyers kulcsszó-gyakoriságról a valódi (classifier) fájdalom-jelekre (`get_recent_pain_signals`).
- **Válaszhossz szigorítva:** 150-200 szóról 70-80 szóra (fórum/Lehetőségek draftok), lista-tiltással.

---

## 4. FONTOS — élesben megtanult leckék (ne ismételd meg a hibát)

1. **Gemini "thinking" token-csapda:** a `gemini-2.5-flash` alapból a `max_output_tokens` keretből "gondolkodásra" költ, és csonka JSON/választ ad. **MINDIG** állítsd: `thinking_config=types.ThinkingConfig(thinking_budget=0)`. Ezt már 2x kellett újrafelfedezni (classifier, majd draft_generator) — ha új Gemini-hívást írsz, EZT AZONNAL tedd bele.
2. **A rendszerprompt-beli szabályokat a modell nem mindig tartja be**, ha csak egy lista-elemként szerepelnek. Kétszer bizonyult be: (a) nyelv-utasítás (angol poszt → magyar válasz lett, amíg a user-message-ben is meg nem ismételtük), (b) hossz-utasítás (70-80 szó helyett 140-et írt, amíg user-message-ben nem ismételtük + `max_output_tokens`-t is szigorítottuk). **Szabály:** kritikus megkötést mindig ismételd meg a user-message végén is, NE csak a system promptban.
3. **max_output_tokens finomhangolás:** ha a válasz linket is tartalmaz (UTM URL), a token-keret vágja le csonkán, ha túl szoros. A szó-limit a prózára vonatkozzon, a linknek külön hely kell a promptban jelezve.
4. **Windows konzol encoding:** `main.py` tetején van egy `sys.stdout.reconfigure(errors="replace")` — ez véd a `UnicodeEncodeError` crash ellen (pl. "²" karakter egy StackOverflow címben leállította a teljes classifier-batchet). Ha új CLI-scriptet írsz ami sok posztcímet printel, ezt vedd figyelembe.
5. **Flask nem veszi észre a sablon/kód-változást automatikusan** (nincs `TEMPLATES_AUTO_RELOAD` beállítva). **Minden `.py` vagy `.html` módosítás után újra kell indítani a szervert.**
6. **A GÉPEN KÉT PYTHON VAN, ÉS EZ MEGÖLTE A PLAYWRIGHT-CONNECTORT.** A Microsoft Store-os `AppData\Local\Microsoft\WindowsApps\python.exe` alias alatt a `%LOCALAPPDATA%\ms-playwright` olvasása virtualizált, ezért a *telepített* Chromium „nem létezik", és a connector `BrowserType.launch: Executable doesn't exist` hibával áll le. Ugyanaz a kód `AppData\Local\Python\pythoncore-3.14-64\python.exe`-vel hibátlanul fut. **MINDIG absolute interpreter-úttal indíts** (`start-monitor.bat` és `.claude/launch.json` már így van beállítva). 2026-07-21 → 07-24 között ez 46 néma hibás futást és a lead-volumen 58%-ának kiesését okozta — ld. `docs/02-lead-volume-audit-2026-07.md` §3.1. A `server.py → preflight()` mostantól ERROR-t naplóz indulásnál, ha rossz interpreter fut vagy nincs böngésző.
7. **TÖBB PÁRHUZAMOS SZERVER-PÉLDÁNY gyakori hiba volt** — és ha a kettő *különböző* interpreterrel indul, váltakozó OK/HIBA mintát látsz a `runs` táblában (pontosan ez történt 07-20/21-én). Mindig ellenőrizd/öld ki az összeset újraindítás előtt:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
8. **Gemini API kulcs típusok:** két féle van, NE keverd. (a) AI Studio egyszerű API-kulcs (`aistudio.google.com/apikey`) — ezt használja a `genai.Client(api_key=...)` egyszerű mód, EZ KELL a projekthez. (b) GCP service-account-kötött "Vertex Express" kulcs — ezzel a sima móddal 403-at kapsz. A jelenlegi `config.yaml`-ban lévő kulcs már a jó típusú (AI Studio), élőben tesztelve működik.
9. **Gemini ingyenes szint nagyon szűk volt** (élőben mérve: 5 RPM / 20 RPD egy adott projekten) — **a számlázás be van kapcsolva** a Google Cloud projekten, ez megoldotta.
10. **A `keyword_filter` regexei kényesek a hosszú szövegre.** A többszavas kulcsszavak korábban láncolt, horgony nélküli `(?=.*\bszó)` lookahead-ekké fordultak `re.DOTALL`-lal — ez négyzetes futási időt adott (10 KB szöveg = 57,8 s!), és beakasztotta a GitHub-connectort (373 s CPU/kör, két zombi processz). Javítva: szavanként külön minta, mind egyezik. **Ha új mintát írsz ide, mérd le hosszú (30 KB+) szövegen**, és soha ne tegyél horgony nélküli `.*`-ot lookahead-be. Ld. `docs/02-lead-volume-audit-2026-07.md` §3.13.
11. **A DB WAL-módban van** (`PRAGMA journal_mode=WAL`, `timeout=30`), mert a `server.py` és egy párhuzamos CLI-futás `database is locked`-kal ütötte ki egymást. Ha új helyen nyitsz kapcsolatot, használd a `storage.db.get_connection()`-t, ne közvetlen `sqlite3.connect()`-et (§3.14).
12. **Playwright-szelektorok fórumonként eltérnek** és törékenyek: Graphisoft NEM a szokásos Khoros DOM-ot használja a keresési nézetben (`.MessageSubject`/`.lia-quilt-column-left-content`), Autodesk viszont igen (`.lia-message-item`), de a `state="visible"` sosem teljesül egyiknél sem — `state="attached"` kell.
13. **Ne hidd el egy fórumról a motorját ránézésre.** A korábbi §7/A azt állította, hogy az OSArch Discourse-alapú, tehát a `discourse_connector` egy config-blokkal lefedi. **Nem az:** élesben mérve (2026-07-26) a `community.osarch.org/latest.json` és `/about.json` **404**, a `/search.json` viszont **200** — de **Vanilla Forums**-sémával (`SearchResults`/`ThemeOptions`/`heroImageUrl`), nem Discourse-éval (`posts[]`/`topics[]`). Így egy „30 perces config-blokk"-ból külön connector lett. **Szabály:** új forrásnál a VÁLASZ SÉMÁJÁT nézd, ne a HTTP-státuszt — a 200 önmagában semmit nem bizonyít, itt épp egy teljesen más fórummotor adta.
15. **A robots.txt-t is forrásonként olvasd el, és a záró perjel SZÁMÍT.** Mérés (2026-07-26): a `speckle.community` és a `forums.buildingsmart.org` robots.txt-jében `Disallow: /search` szerepel — ez prefix-egyezés, tehát a **`/search.json`-ra is illik**. Az OSArch-on viszont `Disallow: /search/` van (záró perjellel), ami a `/search.json`-ra **nem** illik. Ezért van a Discourse-connectorban per-fórum `use_search` kapcsoló. **Mai állapot: MINDKÉT Discourse-fórumon ki van kapcsolva a keresés** (§7/L) — a `_search()` kód megmarad, de dormant; csak a lapozott `/latest.json` fut. Az OSArch-on (Vanilla) a keresés mehet, ott a robots megengedi. Ha a `latest.json` kevés, a robots-barát mélység a `/c/<kategoria>/l/latest.json` (a robots csak a `/c/*.rss`-t tiltja).
14. **A rate limit forrásonként külön mérendő.** A buildingSMART Discourse 429-et adott ~8 gyors kérésnél (ezért 3 s szünet + `search_pages: 1`), az OSArch viszont **8 gyors kérésre mind 200-at** (0,5–0,8 s). Ne másold át vakon a szünet-értéket connectorok között: OSArch-nál 1,5 s elég és 2 lap/query is belefér.

---

## 5. Config gyors-referencia (`config.yaml`)

| Szekció | Állapot |
|---|---|
| `reddit` | ❌ **NINCS beállítva** — `client_id: YOUR_REDDIT_CLIENT_ID` placeholder. Felhasználói lépés: reddit.com/prefs/apps → "create another app" → script típus → redirect URI `http://localhost:8080` |
| `discourse`, `github`, `playwright` | ✅ Működnek, kulcs nélkül/API-kulcs nélkül. **A discourse-nál 2026-07-26 óta MINDKÉT fórumon `use_search: false`** (robots, §7/L) — csak lapozott `/latest.json` fut |
| `discourse.forums.speckle` | ✅ **Új, 2026-07-26.** `use_search: false` (robots, §4/15), `latest_pages: 5` üzemi szinten. Backfill (20 lap, 600 téma) → **35 poszt**, classifier: **29 fájdalom (82,9%)**, 16 db sev≥4 mind `buying_intent=1`. **A második legjobb jelminőség** a GitHub (86,2%) után |
| `vanilla` (OSArch) | ✅ **Új, 2026-07-26.** Kulcs nélkül működik. `search_pages: 2`, `recent_limit: 50`, 240 perc. Első éles kör: **212 elem látva → 71 új poszt**, ebből az első 25-ös classifier-batch **7 fájdalom-jelet** adott (28%, sev 3–4) |
| `stackoverflow` | ✅ Működik (API kulcs opcionális). **A tag-szeparátor `;`, NEM `+`** — a `+` nem létező tagre keres és örökre 0-t ad |
| `forums` | ⛔ **Üres (`{}`)** — a revitforum kivezetve, mert XenForo-ra migrált Cloudflare mögé; a phpBB-szelektorok halottak |
| `scoring.gemini_*` | ✅ Működik, számlázással. **A kulcs 2026-07-25 óta a `.env`-ben** (`GEMINI_API_KEY`), a `config.yaml`-ben `''` — a GitHub push-protection (joggal) elutasította azt a commitot, amiben éles kulcs volt a config.yaml-ben. **Az admin UI SEM írja vissza többé** a Gemini/YouTube kulcsot: a mező csak megjelenít, új kulcsot a `.env`-be kell tenni |
| `.env` (git-ignorált) | Itt élnek a titkok: `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `BRIDGE_API_KEY`, `BRAVE_API_KEY` beállítva; `REDDIT_CLIENT_ID`/`_SECRET` üres. Olvasó: `env_secrets.py` (env → .env → config.yaml fallback) |
| `classifier` | ✅ `enabled: true`, `batch_size: 25`, `delay_seconds: 13`, `draft_min_severity: 3` |
| `health` | ✅ Connector-heartbeat, 6 óránként. `main.py --health` kézzel is |
| `backup` | ✅ Napi 03:30 `VACUUM INTO` snapshot a `backups/`-ba, 7 napos rotáció. `main.py --backup` kézzel is |
| `responder.auto_generate` | ✅ Napi 07:30 draft-generálás a fájdalom-jelekből |
| `responder.exclude_platforms` | ✅ **Új, 2026-07-26.** `[speckle, graphisoft-support]` — ezekre NEM készül válasz (se batch, se kézi gomb). A poszt bejön és jelként látszik. Okok: `speckle` = versenytárs fóruma (döntés, §7/K), `graphisoft-support` = nincs kinek válaszolni (tényállítás, §7/M) |
| `zendesk` | ✅ **Új, 2026-07-26.** `enabled: true`, 720 perc. Két szekció a `support.graphisoft.com`-ról. Egy kör: 960 cikk → 91 a cél-szekciókban → **32 poszt**, ~26 s. Rate limit nincs |
| `alerts.email/slack/webhook` | ❌ **Nincs beállítva** — emiatt SEMMILYEN riasztás nem megy ki. A digest mostantól nem is „fogyasztja el" a posztokat (maradnak `new`-ban), de látni csak a dashboardon lehet őket |
| `alerts.digest_min_severity` | ✅ `3` — a napi digest a `signals` fájdalom-jeleire épül, nem a nyers kulcsszó-score-ra |

---

## 6. main.py CLI-flagek (gyors referencia)

```
python main.py                  # egyszeri futas minden connectorral
python main.py --classify       # Pain Classifier a meg nem osztalyozott posztokra
python main.py --review-signals # kezi kiertekelo riport a signals tablabol
python main.py --generate-drafts # valasz-draftok a pain-jelekbol (severity>=3)
python main.py --review         # interaktiv draft-jovahagyas CLI-ben
python main.py --vanilla        # OSArch community (Vanilla Forums API)
python main.py --zendesk        # Graphisoft support KB (Zendesk Help Center API)
python main.py --health         # connector-egeszseg riport (nema hibak felderitese)
python main.py --backup         # DB-snapshot most (backups/, 7 napos rotacio)
python main.py --websearch      # web-kereses (Brave; BRAVE_API_KEY nelkul kihagyja magat)
python main.py --schedule       # utemezett futas (APScheduler) — ezt inditja a server.py is
```

Allapot-vegpont: `GET http://localhost:5050/health` — **HTTP 503**, ha barmely aktiv
connector hibas vagy "vak" (0 nyers elemet lat), 200 ha rendben. Kulso watchdoghoz.

Szerver indítás (mindig előbb öld ki a régi példányokat, §4/6):
```powershell
Set-Location "C:\NODU\Sales system\Nodu sales dashboard"
& "C:\Users\ZoltanPoczai\AppData\Local\Python\pythoncore-3.14-64\python.exe" server.py
```
Dashboard: `http://localhost:5050/dashboard` · Admin: `http://localhost:5050/admin`

---

## 7. Nyitott / hátralévő munka

> **2026-07-24/25 — lead-volumen audit + P0/P1/P2 javítási kör kész.** Alapdokumentum: `docs/02-lead-volume-audit-2026-07.md`. Eredmény: `posts` **28 → 402**, jelek **24 → 187**, valódi fájdalom **8 → 69**; 6 begyűjtő aktív. A hét connector közül négy nulla üzemben volt, és semmi nem jelezte — ezért van most connector-heartbeat, `/health` és DB-backup.

| # | Feladat | Állapot |
|---|---|---|
| **A** | **OSArch bekötése** | ✅ **Kész (2026-07-26), élesben verifikálva.** A feladat premisszája HIBÁS volt: az OSArch **nem Discourse, hanem Vanilla Forums** (ld. §4/13), ezért nem config-blokk lett belőle, hanem új `connectors/vanilla_connector.py`. Éles első kör: **212 elem → 71 új poszt**, classifier 25-ös batch → **7 fájdalom-jel (28%, sev 3–4)**, ami a rendszerátlag (36%) sávjában van, a `discourse` (37,5%) és `playwright` (31,7%) mellett. **Megfigyelés a tartalomról:** az OSArch fájdalma túlnyomórészt *Bonsai/FreeCAD/IfcOpenShell* eszköz-fájdalom, nem közvetlen Archicad↔Revit interop (7-ből 2 említ Revitet/Archicadet). Nyitott kérdés Zoltánnak: ez a NODU Bridge-nek releváns célközönség-e, vagy inkább a tágabb nodu.build-pozicionálásnak |
| B | **Reddit API-kulcs** | ⏸️ **Elakadt, nem a mi hibánk.** A `prefs/apps` form működik (a gomb: *„are you a developer? create an app…"*, a form az oldal alján nyílik), de CAPTCHA + a 2025 novemberi „Responsible Builder Policy" jóváhagyása kell hozzá. **Áthidalva:** a Reddit-tartalom a Brave-keresőn jön (`site:reddit.com`, első futásra 35 poszt) — cím + kivonat, kommentek nélkül. Kulcs birtokában a `.env` `REDDIT_CLIENT_ID`/`_SECRET` sorába kell tenni, és a 8 subredditre bővítés azonnal élesedik |
| C | **Slack-webhook** (`alerts.slack`) | ❌ **Felhasználói lépés, még nincs.** Enélkül SEM a napi digest, SEM a connector-heartbeat riasztása nem jut el sehova — a találatok a DB-ben gyűlnek `new` státuszban, csak a dashboardon látszanak |
| D | `BRIDGE_API_KEY` a `.env`-be | ✅ **Kész** (2026-07-24), élesben verifikálva: valódi kulcs → 422 (validáció), hamis → 401 |
| E | `BRAVE_API_KEY` a `.env`-be | ✅ **Kész** (2026-07-25), élesben fut. `freshness: py` kell (a `pm` mozi-szálakat adott), query-k problémára hangolva |
| F | **Windows Service** | ⏸️ Szándékosan NEM regisztrálva (rendszerbeállítás + korábban parkoltattad). Ma a monitor manuálisan indított konzolos processz; gépújraindításnál megszűnik. A `/health` már kész egy külső watchdoghoz |
| G | Kozmetikai: a heti LinkedIn poszt-generátor néha beír egy „Íme két poszt-javaslat…" bevezetőt | Jelezve, nem javítva (fél mondat a promptba, ha zavaró) |
| H | Playwright: a Graphisoft/Autodesk szelektorok törékenyek | Ma működnek. Ha elhallgatnak, a heartbeat 6 órán belül jelez (`items_seen=0` → „blind") |

> **A SalesOS-ben DEMO-rekordok vannak (2026-07-24, Zoltán döntése: maradjanak).** 5 `Company` / 5 `Activity` / 5 `BridgeIngest` / 3 `Deal`, a `NODU MONITOR DEMO — A..D` cégeken (+ egy `iroda.hu` nevű, egy elrontott tesztből). **Ezek NEM valódi leadek** — a poszt, a forrás-URL és a fájdalom-összefoglaló valódi, de a cég kitalált (`.invalid` domain). Kiszűrés: `name LIKE 'NODU MONITOR DEMO%'`, ill. `externalId LIKE 'nodu-monitor-post-demo-%'`. A 3 Deal (1 Qualified, 2 Lead) **beleszámít a pipeline-riportokba** — egy éles pipeline-review előtt vedd ki őket a szűrésből. Ezekkel lett élesben igazolva a stage-leképezés (score ≥7 → Qualified, 5–6 → Lead, <5 → nincs Deal).

| I | **Dashboard „Csatornák" pill-szűrő félrelőtt** | ✅ **Javítva (2026-07-26), élesben verifikálva.** Ok: a `search_posts()` szigorúan `platform IN (...)`-ra szűrt, a pill-ek viszont vegyesen küldenek *platform*- és *source*-nevet (a connectorok nem egységesen töltik a két mezőt — a leképezési tábla ott van a függvény docstringjében). **Három javítás:** (1) `search_posts` most `(platform IN (...) OR source IN (...))`; (2) az „Összes" nem fix listát küld, hanem **szűrő nélkül** kér, így a jövőbeli connectorok automatikusan látszanak; (3) új **Web-keresés** pill — a `websearch` 113 posztjának eddig egyáltalán nem volt pill-je. **Mérés előtte → utána:** `github` 0 → 70, `discourse` 0 → 8, `stackoverflow` 0 → 5, elérhető összesen 395/591 → **591/591**. A `reddit` és `revitforum` pill 0-t ad, de az helyes (nincs ilyen poszt) |
| J | `/api/posts` `limit=100` — a „Nyers leadek" fül tetőzött | ✅ **Javítva (2026-07-26), élesben verifikálva.** Új `count_posts()` adja a szűrés VALÓDI darabszámát, a `/api/posts` visszaad `total`/`offset`/`limit`-et, a fülön pedig „100 / 655 találat" + **„Továbbiak betöltése (555 hátra)"** gomb (hozzáfűz, nem cserél). A `_posts_where()` helperbe kiemelt közös WHERE garantálja, hogy a számláló és a lista **ugyanarra a halmazra** vonatkozzon — ez volt a fő hibalehetőség. **Ellenőrzés:** 7 lap, 655 elem, **átfedés és hiány nélkül** (egyedi id-k), `total` minden pill-en egyezik a DB-vel, szűrő+query kombinációra is (`ifc` → 547). A státuszsor „X / Y"-t csak akkor ír, ha van mit lapozni |

| K | **Válaszolunk-e a Speckle fórumán?** | ✅ **Eldöntve (Zoltán, 2026-07-26): NEM.** A Speckle tiszta *intelligence*-forrás — a poszt bejön, jelként látszik, számít a riportokban, de **válasz nem készül rá**. Megvalósítás: `responder.exclude_platforms: [speckle]`, és a kapu **két helyen** zár: (1) a batch-szelekció SQL-jében (`get_pain_posts_without_draft`, `exclude_platforms` paraméter), (2) az egyedi „Válasz generálása" gombnál (`is_platform_excluded`) — különben a dashboardról kézzel mégis lehetne. **Mérés:** szűrés nélkül a következő 20-as batch-ből **7 volt Speckle**, szűréssel **0**, és a batch **továbbra is teljes 20 posztot ad** (a limit nem kopik el a kizártakon). A gomb konkrét indoklást ad, nem néma hibát. Feloldás: vedd ki a `speckle`-t a listából |
| L | **buildingSMART `/search.json` vs robots.txt** | ✅ **Eldöntve (Zoltán, 2026-07-26): a keresés KIKAPCSOLVA.** Innentől **egyik Discourse-fórumon sem** használunk `/search.json`-t — mindkettő robots.txt-je tiltja (§4/15). buildingSMART: `use_search: false`, `latest_pages: 3`. **Mért hatás:** `items_seen` 410 → 90/kör, a teljes discourse-futás 51 → **31 s**. A poszt-szám nem csökkent, sőt 8 → **10**: a `latest.json` 1–2. lapja hozott két témát, amit a keresés sosem talált meg. ⚠️ **De legyen tiszta: a buildingSMART innentől közel null forrás** — ld. lentebb |

> **A buildingSMART reális hozama a keresés nélkül (mérés, 2026-07-26).** 12 lap `/latest.json` = 360 téma, ebből **összesen 3 menthető**. A szűrőn 37 megy át, de **34 régebbi 1 évnél** (az `insert_post` eldobja), és a 2. laptól nulla az új hozam. Ráadásul csak **2/30 témának van excerpt-je**, tehát a `keyword_filter` itt gyakorlatilag csak a CÍMET látja — ezért a mélyebb lapozásnak sincs értelme. A fórum összes posztja 10, ebből 3 fájdalom-jel. Ez most már egy „hátha" forrás, nem lead-motor; a volument a playwright, a websearch, a GitHub és a Speckle adja. Ha egyszer mégis kell a mélység, a robots-barát út a `/c/<kategoria>/l/latest.json` (a robots csak a `/c/*.rss`-t tiltja) — ez a Speckle-nél mérve működött.

| N | **„Lehetőségek" fül: csatorna-szűrő + valódi totál** | ✅ **Kész (2026-07-27), élesben verifikálva.** A kérés csak a szűrő volt, de a mérés egy nagyobb hibát is kidobott: a `dashboard()` route `limit=100`-cal kérte a lehetőségeket, **305-ből** — és a nav-badge meg a metrika-kártya a *lista hosszát* írta ki totalként, tehát „100"-at. Ugyanaz a hiba, mint §7/J-ben. **Ha csak kliens-oldalon szűrtem volna, az OSArch 14 helyett 2-t mutatott volna.** Három javítás: (1) új `count_opportunities()` + `get_opportunity_platform_counts()` a `_opportunity_where()` közös WHERE-re épülve (mint `_posts_where()` a §7/J-nél) — így a számláló és a lista **ugyanarra a halmazra** vonatkozik; (2) a badge/metrika a **valódi** totált mutatja, a render-keret `ui.opportunities_limit` (default 400), és ha mégis csonkol, a status-sor **kiírja**; (3) pill-sor a szekcióban, **a platform-listát az adatból építve** (nem beégetve, így új forrás automatikusan megjelenik), a darabszámok SQL-ből. **Mérés:** 305 kártya renderelve, `osarch` → 14, `IfcOpenShell/IfcOpenShell` → 37 (a `/` miatt `CSS.escape` kell a szelektorban), „Összes" → 305. Két szomszédos hibát is javítottam: a `selectChannelFilter` globális `.filter-pills-row .filter-pill` szelektora **a másik két fül aktív pilljét is levette** (most `#s-raw`-ra szűkítve), és a Discourse-pill `<button>`-je `</label>`-lel volt zárva |
| M | **support.graphisoft.com bekötve — de NEM leadforrás** | ✅ **Kész (2026-07-26), élesben verifikálva.** Zendesk Help Center, nyílt API. **32 poszt** a két interop-szekcióból. **De tudni kell, mi ez:** a cikkeket a Graphisoft supportja írja, `comments_disabled: true`, a szerző staff — **nincs kit megszólítani**, ezért a `graphisoft-support` rajta van a `responder.exclude_platforms` listán. A classifier ezt magától is felismerte: **6,2% fájdalom-arány** (32-ből 2), a leggyengébb az összes forrás közül — ez itt NEM hiba, hanem a helyes viselkedés. Amit ad: piaci intelligencia arról, melyik interop-probléma fordul elő elégszer ahhoz, hogy KB-cikk szülessen róla |

> **Két mérésből jött döntés a Zendesk-connectorban — ne „javítsd" vissza.** (1) A poszt `created_at` mezőjébe az **`updated_at`** kerül: a 234 kulcsszó-találatból `created_at` szerint csak **45** esne 1 éven belülre, és pont a jók esnének ki („Unable to import a Revit file into Archicad", score 25, 2024-es cikk 2026-os frissítéssel; „IFC import, how to translate Revit stories", 23). `updated_at` szerint mind a 234 bejön, és 0 esett ki kor miatt. Egy KB-cikknél a frissítés dátuma a releváns, nem a születésé. (2) Csak **két szekcióból** gyűjtünk („Collaboration with Other Software", „Project Data & BIM"): a maradék ~200 találat licencelési/BIMcloud/BIMx/renderelési zaj, a magas score-ú interop-cikkek mind ebben a kettőben vannak. A szekciókat **név szerint** konfiguráljuk, futásidőben oldódnak fel id-re — a site-on 5 db azonos nevű („General") szekció is van.

> **A Zendesk community HALOTT** — 5 poszt, mind 2020-12-03, és azok a Zendesk **gyári demo-bejegyzései** („What is the community?", „Feature a post"), amiket sosem töröltek. A connector ezért a community-végpontot meg sem hívja. Ha valaki később mégis rákeresne: nem elfelejtettük, hanem nincs ott semmi.

> **Lefedetlen források, amiket a Brave-kereső felhozott** (P3-jelöltek): ~~`community.osarch.org`~~ (✅ A pont), ~~`speckle.community`~~ (✅ 2026-07-26), ~~`support.graphisoft.com`~~ (✅ 2026-07-26, M pont). **A lista elfogyott.** Új forrásnál ELŐBB mérd meg a motort (§4/13), a rate limitet (§4/14) ÉS a robots.txt-t (§4/15) — és kérdezd meg magadtól, hogy van-e ott EMBER, akinek válaszolni lehet (§7/M tanulsága).

---

## 8. Folytatás sorrendje (javasolt)

1. Olvasd el ezt a fájlt. Ha mélyebb kontextus kell: `docs/02-lead-volume-audit-2026-07.md` (üzemállapot, mérések, döntések), majd `docs/01-architektura-audit-2026-07.md` (stratégia).
2. **Ellenőrizd a rendszer állapotát:** `python main.py --health` vagy `GET localhost:5050/health`. Ha nem fut a szerver, indítsd (§6) — **absolute interpreter-úttal** (§4/6!).
3. **Kezdd a C ponttal: Slack-webhook** — ez az egyetlen dolog, ami miatt a kész riasztási lánc még nem ér el senkit. Felhasználói lépés (webhook-URL kell Zoltántól), utána `alerts.slack` a configba.
4. Utána szabadon: I pont (pill-szűrő javítása, kis meló, mérhető haszon a dashboardon), vagy a következő lefedetlen forrás (`speckle.community`).
