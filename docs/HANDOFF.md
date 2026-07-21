# HANDOFF — NODU Monitor fejlesztés folytatása

**Dátum:** 2026-07-21 · **Projekt:** `C:\NODU\Sales system\Nodu sales dashboard` · **Cél:** ha ezt egy új Claude Code session-ben olvasod, ez alapján folytasd — ne kelljen újra felfedezni a kontextust.

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

connectors/                — adatgyujtes (mind insert_post()-ba ir)
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

storage/db.py               — SQLite helperek. Tablak: posts, signals, drafts, runs.
                               Kulcs fuggvenyek: get_opportunities, get_post_with_signal,
                               get_pain_posts_without_draft, get_recent_pain_signals.

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
6. **TÖBB PÁRHUZAMOS SZERVER-PÉLDÁNY gyakori hiba volt** — mindig ellenőrizd/öld ki az összeset újraindítás előtt:
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
7. **Gemini API kulcs típusok:** két féle van, NE keverd. (a) AI Studio egyszerű API-kulcs (`aistudio.google.com/apikey`) — ezt használja a `genai.Client(api_key=...)` egyszerű mód, EZ KELL a projekthez. (b) GCP service-account-kötött "Vertex Express" kulcs — ezzel a sima móddal 403-at kapsz. A jelenlegi `config.yaml`-ban lévő kulcs már a jó típusú (AI Studio), élőben tesztelve működik.
8. **Gemini ingyenes szint nagyon szűk volt** (élőben mérve: 5 RPM / 20 RPD egy adott projekten) — **a számlázás be van kapcsolva** a Google Cloud projekten, ez megoldotta.
9. **Playwright-szelektorok fórumonként eltérnek** és törékenyek: Graphisoft NEM a szokásos Khoros DOM-ot használja a keresési nézetben (`.MessageSubject`/`.lia-quilt-column-left-content`), Autodesk viszont igen (`.lia-message-item`), de a `state="visible"` sosem teljesül egyiknél sem — `state="attached"` kell.

---

## 5. Config gyors-referencia (`config.yaml`)

| Szekció | Állapot |
|---|---|
| `reddit` | ❌ **NINCS beállítva** — `client_id: YOUR_REDDIT_CLIENT_ID` placeholder. Felhasználói lépés: reddit.com/prefs/apps → "create another app" → script típus → redirect URI `http://localhost:8080` |
| `discourse`, `github`, `playwright` | ✅ Működnek, kulcs nélkül/API-kulcs nélkül |
| `stackoverflow` | ✅ Működik (API kulcs opcionális) |
| `scoring.gemini_*` | ✅ Beállítva, számlázással, élőben tesztelve |
| `classifier` | ✅ `enabled: true`, `batch_size: 15`, `delay_seconds: 13`, `draft_min_severity: 3` |
| `alerts.email/slack/webhook` | ❌ Nincs beállítva (opcionális) |

---

## 6. main.py CLI-flagek (gyors referencia)

```
python main.py                  # egyszeri futas minden connectorral
python main.py --classify       # Pain Classifier a meg nem osztalyozott posztokra
python main.py --review-signals # kezi kiertekelo riport a signals tablabol
python main.py --generate-drafts # valasz-draftok a pain-jelekbol (severity>=3)
python main.py --review         # interaktiv draft-jovahagyas CLI-ben
python main.py --schedule       # utemezett futas (APScheduler) — ezt inditja a server.py is
```

Szerver indítás (mindig előbb öld ki a régi példányokat, §4/6):
```powershell
Set-Location "C:\NODU\Sales system\Nodu sales dashboard"
& "C:\Users\ZoltanPoczai\AppData\Local\Python\pythoncore-3.14-64\python.exe" server.py
```
Dashboard: `http://localhost:5050/dashboard` · Admin: `http://localhost:5050/admin`

---

## 7. Nyitott / hátralévő munka

| # | Feladat | Állapot |
|---|---|---|
| A | **Reddit API-kulcs beállítása** | Felhasználói lépés (nem automatizálható) — utána a Reddit-connector élesedik |
| B | **2. szakasz: Nyers-lead kereső** — teljes `posts` tábla böngészhetővé/kereshetővé tétele a dashboardon (jelenleg csak az osztályozott/ad-hoc/draft posztok láthatók, a ~185 nyers, még nem osztályozott poszt nem) | **Megbeszélve, megbecsülve (~1-2 óra), MÉG NEM KEZDETT EL.** Terv: `search_posts()` DB-helper (SQL `LIKE` cím/test + forrás-szűrő) → `GET /api/posts` route → új "Nyers leadek" dashboard-fül, az Ad-hoc keresés result-row mintájára |
| C | Kozmetikai: a heti LinkedIn poszt-generátor néha beír egy "Íme két poszt-javaslat..." bevezetőt a szöveg elé — jelezve, de nem javítva (fél mondat a promptba, ha zavaró) |
| D | Korábbról elhalasztva: szerver-keményítés (login, env-secrets, /health, backup), Windows Service + Cloudflare Tunnel — user kérésére parkolva |

---

## 8. Folytatás sorrendje (javasolt)

1. Ha új session-ben vagy: olvasd el ezt a fájlt + `docs/01-architektura-audit-2026-07.md` (ha mélyebb stratégiai kontextus kell).
2. Ellenőrizd a szerver állapotát (§4/6 — lehet, hogy fut egy korábbi példány).
3. Folytasd a **B feladattal** (Nyers-lead kereső) — ez volt a megbeszélt következő lépés.
