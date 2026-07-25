# HANDOFF — NODU Monitor fejlesztés folytatása

**Dátum:** 2026-07-25 (előző: 2026-07-21) · **Projekt:** `C:\NODU\Sales system\Nodu sales dashboard` · **Cél:** ha ezt egy új Claude Code session-ben olvasod, ez alapján folytasd — ne kelljen újra felfedezni a kontextust.

> **Legutóbb (2026-07-24/25):** lead-volumen audit + a P0/P1/P2 javítási kör. A rendszer négy néma hibából állt vissza; `posts` 28 → 402. **A következő lépés a §7/A: OSArch bekötése.** Részletek: `docs/02-lead-volume-audit-2026-07.md`.

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
  discourse_connector.py      — buildingSMART forums.buildingsmart.org, nyilt API
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

---

## 5. Config gyors-referencia (`config.yaml`)

| Szekció | Állapot |
|---|---|
| `reddit` | ❌ **NINCS beállítva** — `client_id: YOUR_REDDIT_CLIENT_ID` placeholder. Felhasználói lépés: reddit.com/prefs/apps → "create another app" → script típus → redirect URI `http://localhost:8080` |
| `discourse`, `github`, `playwright` | ✅ Működnek, kulcs nélkül/API-kulcs nélkül |
| `stackoverflow` | ✅ Működik (API kulcs opcionális). **A tag-szeparátor `;`, NEM `+`** — a `+` nem létező tagre keres és örökre 0-t ad |
| `forums` | ⛔ **Üres (`{}`)** — a revitforum kivezetve, mert XenForo-ra migrált Cloudflare mögé; a phpBB-szelektorok halottak |
| `scoring.gemini_*` | ✅ Működik, számlázással. **A kulcs 2026-07-25 óta a `.env`-ben** (`GEMINI_API_KEY`), a `config.yaml`-ben `''` — a GitHub push-protection (joggal) elutasította azt a commitot, amiben éles kulcs volt a config.yaml-ben. **Az admin UI SEM írja vissza többé** a Gemini/YouTube kulcsot: a mező csak megjelenít, új kulcsot a `.env`-be kell tenni |
| `.env` (git-ignorált) | Itt élnek a titkok: `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `BRIDGE_API_KEY`, `BRAVE_API_KEY` beállítva; `REDDIT_CLIENT_ID`/`_SECRET` üres. Olvasó: `env_secrets.py` (env → .env → config.yaml fallback) |
| `classifier` | ✅ `enabled: true`, `batch_size: 25`, `delay_seconds: 13`, `draft_min_severity: 3` |
| `health` | ✅ Connector-heartbeat, 6 óránként. `main.py --health` kézzel is |
| `backup` | ✅ Napi 03:30 `VACUUM INTO` snapshot a `backups/`-ba, 7 napos rotáció. `main.py --backup` kézzel is |
| `responder.auto_generate` | ✅ Napi 07:30 draft-generálás a fájdalom-jelekből |
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
| **A** | **KÖVETKEZŐ LÉPÉS: OSArch bekötése a Discourse-connectorba** | A Brave-kereső felhozta a `community.osarch.org`-ot (openBIM/IfcOpenShell-közösség), ami **Discourse-alapú**, tehát a meglévő `discourse_connector` egy config-blokkal lefedi. Ugyanaz a `latest.json` + kereső logika futna rá, mint a buildingSMART-on. ~30 perc. Ld. `02-...md` §5a |
| B | **Reddit API-kulcs** | ⏸️ **Elakadt, nem a mi hibánk.** A `prefs/apps` form működik (a gomb: *„are you a developer? create an app…"*, a form az oldal alján nyílik), de CAPTCHA + a 2025 novemberi „Responsible Builder Policy" jóváhagyása kell hozzá. **Áthidalva:** a Reddit-tartalom a Brave-keresőn jön (`site:reddit.com`, első futásra 35 poszt) — cím + kivonat, kommentek nélkül. Kulcs birtokában a `.env` `REDDIT_CLIENT_ID`/`_SECRET` sorába kell tenni, és a 8 subredditre bővítés azonnal élesedik |
| C | **Slack-webhook** (`alerts.slack`) | ❌ **Felhasználói lépés, még nincs.** Enélkül SEM a napi digest, SEM a connector-heartbeat riasztása nem jut el sehova — a találatok a DB-ben gyűlnek `new` státuszban, csak a dashboardon látszanak |
| D | `BRIDGE_API_KEY` a `.env`-be | ✅ **Kész** (2026-07-24), élesben verifikálva: valódi kulcs → 422 (validáció), hamis → 401 |
| E | `BRAVE_API_KEY` a `.env`-be | ✅ **Kész** (2026-07-25), élesben fut. `freshness: py` kell (a `pm` mozi-szálakat adott), query-k problémára hangolva |
| F | **Windows Service** | ⏸️ Szándékosan NEM regisztrálva (rendszerbeállítás + korábban parkoltattad). Ma a monitor manuálisan indított konzolos processz; gépújraindításnál megszűnik. A `/health` már kész egy külső watchdoghoz |
| G | Kozmetikai: a heti LinkedIn poszt-generátor néha beír egy „Íme két poszt-javaslat…" bevezetőt | Jelezve, nem javítva (fél mondat a promptba, ha zavaró) |
| H | Playwright: a Graphisoft/Autodesk szelektorok törékenyek | Ma működnek. Ha elhallgatnak, a heartbeat 6 órán belül jelez (`items_seen=0` → „blind") |

> **A SalesOS-ben DEMO-rekordok vannak (2026-07-24, Zoltán döntése: maradjanak).** 5 `Company` / 5 `Activity` / 5 `BridgeIngest` / 3 `Deal`, a `NODU MONITOR DEMO — A..D` cégeken (+ egy `iroda.hu` nevű, egy elrontott tesztből). **Ezek NEM valódi leadek** — a poszt, a forrás-URL és a fájdalom-összefoglaló valódi, de a cég kitalált (`.invalid` domain). Kiszűrés: `name LIKE 'NODU MONITOR DEMO%'`, ill. `externalId LIKE 'nodu-monitor-post-demo-%'`. A 3 Deal (1 Qualified, 2 Lead) **beleszámít a pipeline-riportokba** — egy éles pipeline-review előtt vedd ki őket a szűrésből. Ezekkel lett élesben igazolva a stage-leképezés (score ≥7 → Qualified, 5–6 → Lead, <5 → nincs Deal).

> **Lefedetlen források, amiket a Brave-kereső felhozott** (P3-jelöltek): `community.osarch.org` (→ A pont), `speckle.community` (versenytárs fóruma), `support.graphisoft.com` (support-cikkek — a Playwright csak a fórumot látja).

---

## 8. Folytatás sorrendje (javasolt)

1. Olvasd el ezt a fájlt. Ha mélyebb kontextus kell: `docs/02-lead-volume-audit-2026-07.md` (üzemállapot, mérések, döntések), majd `docs/01-architektura-audit-2026-07.md` (stratégia).
2. **Ellenőrizd a rendszer állapotát:** `python main.py --health` vagy `GET localhost:5050/health`. Ha nem fut a szerver, indítsd (§6) — **absolute interpreter-úttal** (§4/6!).
3. **Kezdd az A ponttal: OSArch bekötése** a `discourse.forums` alá.
4. Utána: a C pont (Slack-webhook) az egyetlen dolog, ami miatt a kész riasztási lánc még nem ér el senkit.
