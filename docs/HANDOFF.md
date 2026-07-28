# HANDOFF — NODU Monitor fejlesztés folytatása

**Dátum:** 2026-07-27 (előző: 2026-07-26) · **Projekt:** `C:\NODU\Sales system\Nodu sales dashboard` · **Cél:** ha ezt egy új Claude Code session-ben olvasod, ez alapján folytasd — ne kelljen újra felfedezni a kontextust.

> ✅ **2026-07-28 — §4/19 MEGOLDVA: az admin „Mentés" mostantól NEM törli a config.yaml kommentjeit.** A régi `ui/app.py → save_config()` (`yaml.dump`) helyett új `storage/config_writer.py`: célzott, 15 útra (11 skalár + 4 blokk-lista) whitelistelt szöveg-patcher, ami a fájl MEGLÉVŐ szövegében cseréli a birtokolt kulcs sorát, minden mást bájtra érintetlenül hagyva (`newline=""`, saját sor-hasítás, nincs `ruamel.yaml`). Élesben verifikálva: egy `weekly_report.language`-et módosító mentés után `git diff` **pontosan 1 sort** mutat, a 206 komment-only sor és a 8 inline komment megmarad (nem 318-ra/~7 KB-ra esik), ismételt mentés azonos értékkel bájtra no-op (sha256 egyezik), `curl` részleges POST-tal nem lehet átfordítani a `gemini_enabled`/`slack.enabled` boolt. Ugyanebben a körben javítva a szomszédos adatvesztési hibák is: üres/hiányzó mező = változatlan marad (nem placeholder-felülírás — ez okozta a `d42c3c8` regressziót), a három kulcsszó-textarea egymástól független feltétel, hiányzó szekció → HTTP 400 látható hibasávval, nem 500. `test_config_writer.py` **75/75**, a teljes suite (242 teszt) zöld. **Két pontosítás, amit a felderítés hozott a régi §4/19-szöveghez képest** (részletek lent az újraírt 19. pontban): a Zendesk `updated_at`-szabály nem config.yaml-kommentben él, és a §4/17-es `off`-csapda csak kézi szerkesztésre igaz. **Egy harmadik, most mért tény:** a `keywords.pain_points` listában 11 sornyi beágyazott komment van, ami elveszne, ha ezt a mezőt valaha szerkesztik az Adminban (a másik 3 lista tiszta) — ez cáfolja a régi szöveg „0 veszteség" állítását.
>
> ✅ **2026-07-28 — az audit P2-es tételei is JAVÍTVA (§7/V).** A legfontosabb tanulság **negatív, és számít:** a severity-prompt kalibrálása után a **páros** mérés (`--calibrate 25`) azt mutatja, hogy a skála teteje használhatóvá lett (sev5 0,07% → ~8%), de a szórás NEM nőtt — 25-ből 18 a 4-esen ül. **A severity tehát nem prioritási kapcsoló, és nem is lesz az:** a `digest_min_severity: 4` ma a fájdalom-jelek ~80%-át átengedné. A valódi diszkriminátor a `buying_intent` — ezért került a rendezés élére és a SalesOS-score-ba (a score-eloszlás 4 → 7 distinct értékre nyílt). Emellett: a márkaemlítés regexre cserélve, a versenytárs-név idézettel igazolva (**élesben azonnal fogott egy hallucinációt**), classifier FIFO + kísérlet-számláló (hátralék 104 → 31), `delay_seconds` 13 → 2 mért alapon (100 poszt: ~3 óra → ~6,5 perc, 0 db 429), stackoverflow kivezetve, snapshot-ellenőrzés + **dokumentált visszaállítási eljárás** (§6). `test_p2_fixes.py` **42/42**; a teljes suite 167 teszt, mind zöld.
>
> ✅ **2026-07-28 — az audit HÉT P1-ese is JAVÍTVA (§7/U).** A legfontosabbak: a draft-job nem veszi el a jeleket a digest elől; a heartbeat **látja a hiányzó futást** (`stale` státusz, `connector_schedule()` mint egy igazság) és élesben azonnal jelezte a backup+digest kimaradását; a 274 KB-os tudásbázis kikerült a fórum-draft promptból (260 126 → 1 361 karakter); az újraindítás nem lő ki mindent (**0 kör 45 s-en belül**, előtte 11); titok-maszkolás a naplóban; a jelszókapu mind a 8 mutáló végponton. `test_p1_fixes.py` **38/38**. ⚠️ **Egy felhasználói lépés maradt: a `logs/monitor.log`-ban lévő régi Google CSE-kulcsot vissza kell vonni a GCP-n** — a szűrő csak az ÚJ sorokat védi.
>
> ✅ **2026-07-28 — az audit két P0-ja JAVÍTVA (§7/T).** A Khoros-dedup kanonizálva + 1276 duplikátum kivezetve migrációval (`posts` 1692 → **446**, Khoros 1309 → **33**, Lehetőségek 504 → **129**), és a napi digest mostantól SQL-ben szűr statuszra, tehát a `limit` nem vághatja le a várakozó jeleket. Élesben verifikálva: egy Playwright-kör 48 elemből **0 újat** szúr be (előtte 30-at). **A rendszerről alkotott számok most először igazak — a régi arányokra ne hivatkozz.** A maradék javaslatok (P1: draft-job elfogyasztás, heartbeat hiányzó futás, backup-lyuk, 274 KB-os KB a promptban, log-beli kulcs; P2: severity-kalibrálás, `confidence`, restart-amplifikáció) a `docs/04-rendszer-audit-2026-07-28.md` §5-ben, priorizálva.
>
> ⚠️ **2026-07-28 — RENDSZER-AUDIT: a mai számok nem azt mutatják, amit hiszünk róluk.** Három P0-s hiba, mind független újraméréssel igazolva: (1) a **Playwright-dedup nem működik** — 1309 poszt = **33 valódi szál** (minden `external_id` tartalmazza a változó `search-action-id`-t), tehát a `posts` 77%-a duplikátum, és ~1150 fizetős Gemini-hívás duplikátumokra ment; (2) a **napi digest 100 elemnél elvágja a sort** (`main.py:251` nem ad `limit`-et) — 35 várakozó jelből **3-at lát, 32 strandol örökre**, mert a rendezés severity szerinti, nem idő szerinti (ez a §7/J–§7/N hibaosztály **harmadik** előfordulása, most az értesítési útban); (3) a **`graphisoft` posztok 405/405-ének `created_at`-je nem parse-olható**, ezért mind megkerüli az 1 éves korlátot — 2012-es szálakra generálunk 2026-os választ. **Teljes lista, bizonyítékokkal és 12 priorizált javaslattal: `docs/04-rendszer-audit-2026-07-28.md`.** Megismételhető: `/nodu-audit`. **Az audit egy korábbi állítást is korrigált:** a „mind a 90 jel severity 4" mérés a limit=100-as csonkolás artefaktuma volt — a valós eloszlás 305× sev3, 206× sev4, 1× sev5 (a következtetés viszont áll: a 3-as küszöb 513-ból 512-t átenged).
>
> **Előtte (2026-07-27, második kör): a Slack-riasztási lánc ÉL és MÁR KÜLDÖTT (§7/C ✅, §7/Q ✅).** A 90 felgyűlt fájdalom-jel kiment 5 Slack-üzenetben, mind a 90 részletezve — a digest mostantól nem összesíti láthatatlanná a többséget (§7/Q). A webhook-URL a `.env`-ben (`SLACK_WEBHOOK_URL`), a csatorna `enabled: true`, `--test-slack` → **HTTP 200**. 24/24 lánc-teszt zöld; élesben mérve, hogy URL nélkül a 90 fájdalom-jel `new`-ban MARAD, tehát semmi nem tűnt el a beállítás előtt. **A rendszer első riasztási képessége ezzel megvan: a napi digest és a connector-heartbeat innentől eljut valakihez.** Két új lecke: **§4/20** — a `.env` `=` nélküli sora néma hiba volt (a webhook-URL „ott volt, mégsem"), most kiírja; **§4/19** — az admin „Mentés" letörli a config.yaml kommentjeit.
>
> **Előtte (2026-07-27):** a „Lehetőségek" fül csatorna-szűrője + valódi totálok (§7/N), majd a **LinkedIn kommentgenerálás teljes újratervezése** Thought Leadership Engine-né (§7/O) és a márkaemlítés poszt-vezéreltté tétele (§7/P).

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

responder/
  linkedin_engine.py        — LinkedIn Thought Leadership Engine (2026-07-27).
                               A "LinkedIn valasz" ful kommentgeneralasa.
                               REASON (1 strukturalt hivas: intent, core thesis,
                               missing perspective, strategia-PONTOZAS, egy insight)
                               -> COMPOSE (1 hivas) -> DETERMINISZTIKUS kapu kodban.
                               A strategiat a KOD valasztja (pick_strategy), a
                               markaemlitest a POSZT donti el (brand_mention_allowed).
                               A modul-docstring reszletezi, miert 2 hivas es nem 9.
  draft_generator.py        — MINDEN MAS AI-valaszgeneralas (forum-draftok, heti
                               LinkedIn poszt-otletek, trendelemzes). A
                               `generate_linkedin_reply` itt mar csak VEKONY
                               DELEGALO a linkedin_engine fele — a route-ot nem
                               kellett atirni. A `_LEGACY_LINKEDIN_REPLY_*`
                               konstansok kivezetettek, de az enumjaik meg elnek a
                               visszafele-kompatibilis lekepezesben.
    generate_draft_for_post()   — 1 poszthoz valasz (Lehetosegek "Valasz generalasa")
    generate_drafts()           — batch a pain-jelekbol (severity>=3)
    generate_content_pipeline() — heti blog+LinkedIn poszt-otletek (Slack-re)
    generate_trend_analysis()   — heti narrativ trendelemzes (Slack-re)
    review_drafts()             — interaktiv CLI jovahagyas
    is_platform_excluded()      — responder.exclude_platforms kapu

classifier/
  pain_classifier.py        — A RENDSZER AGYA. Egyetlen strukturalt Gemini-hivas
                               posztonkent: is_pain, severity(1-5), pain_summary,
                               buying_intent, role_hypothesis, stb. -> signals tabla.
                               CLI: python main.py --classify / --review-signals
                               TUDATOSAN NINCS az utemezoben — kezi kapudontes-fazis.

test_draft_decisions.py     — 30 teszt a draft-dontes naplozasahoz (§7/S): migracio
                              regi sematu DB-n, idempotencia, mark_draft nevvel/nev
                              nelkul, /draft/<id>/approve|reject route, basic-auth
                              fallback, /api/decisions. Temp DB-t hasznal.
test_db.py                  — DB-smoke teszt. 2026-07-27 ota TEMP DB-re ir: elotte az
                              ELES nodu_monitor.db-be szurt egy hamis reddit-posztot
                              ('test_abc123'), ami beleszamitott a poszt-totalokba.
                              A bekerult sort (id=1563) kitoroltuk.

storage/db.py               — SQLite helperek (WAL-mod!). Tablak: posts, signals, drafts, runs.
                               Kulcs fuggvenyek: get_opportunities, get_post_with_signal,
                               get_pain_posts_without_draft, get_recent_pain_signals,
                               get_connector_health (nema hibak felderitese).
                               A `runs.items_seen` a NYERS elemszam — ez valasztja el a
                               "nincs uj tartalom"-ot az "eltort connector"-tol.
storage/backup.py           — napi VACUUM INTO snapshot a backups/-ba, 7 napos rotacio
storage/config_writer.py   — celzott config.yaml-iro (§4/19): 15 whitelistelt utat
                              (PATCHABLE) patchel a fajl MEGLEVO szovegeben, yaml.dump
                              helyett — a 206+8 kommentsor megmarad. Hivo: ui/app.py /save.
test_config_writer.py       — 75 teszt (A-F: megorzes/celzas/tipizalas/listak/rollback/
                              route). Az elo config.yaml egy MASOLATat is regresszios
                              tesztkent hasznalja (206/8 komment megmaradasa).

alerts/notifier.py          — MINDEN riasztas (Slack/email/n8n-webhook).
                              slack_webhook_url()  — env -> .env -> config fallback,
                                                     hooks.slack.com prefix-ellenorzes
                              slack_status()       — (kesz-e, indoklas) az admin UI-hoz
                              send_slack()         — BOOL-t ad vissza: csak valodi
                                                     kikuldes szamit 'delivered'-nek
                              send_slack_test()    — `main.py --test-slack`
test_slack_alerts.py        — 37 lanc-teszt a Slack-uthoz (halozat monkeypatchelve):
                              URL nelkul / rossz host / ervenyes URL / HTTP-hiba /
                              enabled: false / LAPOZAS (90 jel -> 5 uzenet, Block
                              Kit korlatok, reszleges hiba). HERMETIKUS: sajat
                              _ENV_FILE-t allit be, kulonben az eles .env-beli
                              SLACK_WEBHOOK_URL 8 tesztet megbuktat.
                              Futtatas: python test_slack_alerts.py

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
  04-rendszer-audit-2026-07-28.md   — RENDSZER-AUDIT. OLVASD EL, mielott barmit
                                      meresre alapozol: kiderult, hogy a playwright
                                      dedup nem mukodik (1309 poszt = 33 szal), a
                                      digest 100-nal elvagja a sort (32 jel
                                      strandolt), es a graphisoft-posztok 100%-a
                                      megkeruli az 1 eves korlatot. A mai szamok
                                      ezert nem azt mutatjak, amit hisznek roluk.
                                      Megismetelheto: /nodu-audit
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
16. **Az LLM enum-választása torzít — ha döntés kell, PONTOZTASD és a kód válasszon.** Mérés (2026-07-27, LinkedIn-motor): 7 stratégiából enum-választással 5 posztból 4-5 ugyanazt kapta. A lista átrendezése után a torzítás **átvándorolt** az új első elemekre (`missing_perspective` → `systems_thinking`) — tehát nem a tartalom döntött, hanem a pozíció és az, hogy melyik hangzik „okosabban". Javítás: a modell **minden** opciót pontoz 0–10-re, a győztest a kód veszi ki (`pick_strategy`, dokumentált fallback-levonással). Eredmény: 5 posztra 4 különböző stratégia, és a döntés auditálható (a pontszám-vektor a válaszban van). Ez ugyanaz az elv, mint a `01-architektura-audit §7`: „a Scorer determinisztikus — az LLM mezőket ad, a pontszámot a kód számolja". **Általánosítva: az LLM legyen a szenzor, ne a bíró.**
17. **A YAML az `off`/`on`/`yes`/`no` szavakat BOOLEANNÁ alakítja** (YAML 1.1). A `brand_positioning: off` így `False` lett, nem `"off"` — a string-összehasonlítás csendben mindig hamis, tehát a beállítás látszólag működött, de rossz okból. Idézőjel kell (`'off'`), ÉS a kód normalizálja a booleant. Ha új on/off-jellegű config-kulcsot vezetsz be, ezt nézd meg. **Pontosítás (2026-07-28, §4/19 felderítése):** ez a csapda KÉZI szerkesztésre él (szövegszerkesztőben idézőjel nélkül beírt érték). A programozott írók mérve helyesen idézőjeleznek: a régi `yaml.dump` is, és az új `storage/config_writer.py` is (`yaml.safe_load`-dal ellenőrzi a plain formát írás előtt).
18. **Ha a modellnek „bizonyítékot" kell adnia, ellenőrizd a kódban.** A LinkedIn-motor `explicit_tool_request` mezője mellé kötelező a `tool_request_quote` — és a kód megkeresi az idézetet a posztban (normalizált részszöveg, min. 3 szó). Enélkül a mező hallucinációra hívás lett volna: a modell „igen, kértek eszközt" állítását semmi nem cáfolta volna. Ugyanaz az elv, mint a kötelező `sourceUrl` a SalesOS-ingestnél.
20. **A `.env` formátuma szigorú, és a hiba NÉMA volt.** A `SLACK_WEBHOOK_URL` először `SLACK WEBHOOK: https://...` formában került a fájlba (szóköz + kettőspont). Az `env_secrets._load_env_file()` a `=` jel nélküli sorokat eldobta, tehát a titok fizikailag ott volt, a rendszer mégis „nincs beállítva" állapotot mutatott — ugyanaz a hibaosztály, mint a §4/6-os Playwright-eset: a hiányzó dolog és az elrontott dolog egyformán néz ki. **Javítva:** az `env_secrets` mostantól **kiírja** a `=` nélküli sorokat (`[env] A .env N. sora '=' nélkül van…`, az érték nélkül, csak a kulcs-részt), és a `--test-slack` azonnal megmutatja az eredményt. Ha új titkot vezetsz be: `KULCS=ertek`, idézőjel és szóköz nélkül, ÉS legyen hozzá egy „küldj egy tesztet" út.
19. **✅ MEGOLDVA (2026-07-28): az admin „Mentés" gombja mostantól NEM törli a config.yaml kommentjeit.** A régi `ui/app.py → save_config()` `yaml.dump`-pal írta ki a fájlt, a PyYAML pedig nem tartja meg a kommenteket — ez a config.yaml **működési szabályokat hordozó** kommentjeit (206 komment-only + 8 inline sor) egyetlen mentéssel elvitte volna. Megoldás: `storage/config_writer.py` — célzott, 15 útra (11 skalár + 4 blokk-lista, ld. `PATCHABLE`) whitelistelt szöveg-patcher, ami a fájl MEGLÉVŐ szövegében cseréli ki a birtokolt kulcs sorát; minden más byte érintetlen marad. Nincs új függőség (`ruamel.yaml` mérlegelve és elvetve — nem bájt-egzakt, és a projekt konvenciója sem vesz fel függőséget kis feladatra). A skalár idézőjel-igényét `yaml.safe_load` dönti el (ha a plain forma ugyanazt a stringet adja vissza, plainben írható — ez a döntőbíró, nem egy kézzel másolt resolver-tábla). Írás → memóriabeli hitelesítés → atomi `.tmp`+`os.replace` → kötelező lemezes visszaolvasás → eltérésnél visszaállítás az eredeti bájtokra (`config.yaml.bak-<ISO>` sidecar, ha még ez is hibázik). Ugyanebben a körben javítva a szomszédos adatvesztési hibák is (`ui/app.py /save`): üres/hiányzó mező = **változatlan** marad, nem placeholder-felülírás (ez okozta a `d42c3c8` regressziót); a három kulcsszó-textarea (`kw_primary`/`kw_pain`/`kw_context`) egymástól FÜGGETLEN feltétel (korábban egy guard őrizte mindhármat); a 3 checkbox mellé rejtett kísérő-mező került, hogy egy részleges POST ne tudjon átfordítani egy meg sem említett boolt; hiányzó szekció → HTTP 400 látható hibasávval, nem 500/stacktrace. Élesben verifikálva: egy `weekly_report.language`-et módosító admin-mentés után `git diff` **pontosan 1 sort** mutat, 206/8 komment megmarad, ismételt mentés azonos értékkel bájtra no-op (sha256 egyezik), `curl -d "reddit_client_id=x"` nem érinti a `gemini_enabled`/`slack.enabled` boolt. `test_config_writer.py` **75/75**, a teljes suite (242 teszt) zöld. **Két pontosítás a felderítésből, ami a fenti (eredeti) szöveget javítja:** (1) a `updated_at`-szabály a Zendesknél NEM config.yaml-kommentben él — a `connectors/zendesk_connector.py:25-32`-ben van (ld. §2 és §7/M); a fenti eredeti mondat rossz helyre mutatott. (2) A §4/17-es `'off'`-csapda **kézi szerkesztésre** igaz — a `yaml.dump` (mérve) helyesen idézőjelezte az ilyen stringeket, tehát a régi `save_config()` ebből a szempontból NEM volt hibás, kizárólag a kommentvesztés miatt kellett lecserélni. **Egy harmadik, most mért tény, ami szintén korrekció:** a `keywords.pain_points` listában ÉLESBEN két beágyazott kommentblokk van (11 sor: a 69-72. és a 98-104. sor, a kulcs és az első elem között, illetve két elem között) — ha ezt a mezőt valaha szerkesztik az Adminban, ez a 11 sor elvész (dokumentált korlát, a writer figyelmeztetést logol). A másik 3 whitelistelt lista (`reddit.subreddits`, `keywords.primary`, `keywords.context`) tiszta, azoknál nincs veszteség — tehát a terv „0 veszteség a mai fájlon" állítása pontatlan volt, csak 3/4 listára igaz.
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
| `.env` (git-ignorált) | Itt élnek a titkok: `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `BRIDGE_API_KEY`, `BRAVE_API_KEY`, **`SLACK_WEBHOOK_URL`** beállítva; `REDDIT_CLIENT_ID`/`_SECRET` üres. Olvasó: `env_secrets.py` (env → .env → config.yaml fallback). **Formátum: `KULCS=ertek`** — a `=` nélküli sort kihagyja, de 2026-07-27 óta ki is írja (§4/20) |
| `classifier` | ✅ `enabled: true`, `batch_size: 25`, `delay_seconds: 13`, `draft_min_severity: 3` |
| `health` | ✅ Connector-heartbeat, 6 óránként. `main.py --health` kézzel is |
| `backup` | ✅ Napi 03:30 `VACUUM INTO` snapshot a `backups/`-ba, 7 napos rotáció. `main.py --backup` kézzel is |
| `responder.auto_generate` | ✅ Napi 07:30 draft-generálás a fájdalom-jelekből |
| `responder.exclude_platforms` | ✅ **Új, 2026-07-26.** `[speckle, graphisoft-support]` — ezekre NEM készül válasz (se batch, se kézi gomb). A poszt bejön és jelként látszik. Okok: `speckle` = versenytárs fóruma (döntés, §7/K), `graphisoft-support` = nincs kinek válaszolni (tényállítás, §7/M) |
| `zendesk` | ✅ **Új, 2026-07-26.** `enabled: true`, 720 perc. Két szekció a `support.graphisoft.com`-ról. Egy kör: 960 cikk → 91 a cél-szekciókban → **32 poszt**, ~26 s. Rate limit nincs |
| `linkedin.brand_positioning` | ✅ **Új, 2026-07-27.** `'on_request'` (default): a NODU Bridge CSAK akkor említhető a LinkedIn-kommentben, ha a poszt kifejezetten eszközt kér, az idézett kérdés **ellenőrizhetően szerepel** a posztban, és a téma Bridge-relevans. Alternatívák: `'off'` (soha, kérdésre sem), `'auto'` (a régi három-ágú márkadöntés). **Idézőjel kell** — YAML boolean-csapda, §4/17 |
| `alerts.slack` | ✅ **ÉL (2026-07-27).** `enabled: true`, a `webhook_url` a config.yaml-ben szándékosan `''` — a valódi URL a `.env` `SLACK_WEBHOOK_URL` sorában van (§7/C, §4/20). Egy csatorna kap mindent: digest, heartbeat, heti összefoglaló, tartalom-javaslatok. Teszt bármikor: `main.py --test-slack` (HTTP 200 = él) |
| `alerts.email/webhook` | ❌ **Nincs beállítva** (`enabled: false`). Az e-mail SMTP app-passwordot igényel, az `alerts.webhook` pedig a kivezetett n8n-út (a SalesOS-ingest ma közvetlen, ld. §2) — egyik sincs napirenden, a riasztási csatorna a Slack |
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
python main.py --test-slack     # Slack-webhook teszt a VALODI riasztasi uton (exit 0/1)
python main.py --calibrate 25   # 25 mar osztalyozott poszt UJRAERTEKELESE a mai
                                # prompttal, PAROS osszevetes. A DB-t NEM irja.
```

### Adatbazis visszaallitasa snapshotbol (§5/12 — eddig nem volt dokumentalva)

```powershell
# 1. Alld le a szervert (kulonben ir a DB-be)
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*server.py*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# 2. Valaszd ki a snapshotot es ELLENORIZD, mielott bizol benne
Get-ChildItem "backups\nodu_monitor.db.*.db" | Sort-Object Name -Descending | Select-Object -First 5
& "C:\Users\ZoltanPoczai\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "import sys; sys.path.insert(0,'.'); from storage.backup import verify_snapshot; print(verify_snapshot(r'backups\nodu_monitor.db.<IDOBELYEG>.db'))"

# 3. A JELENLEGI DB-t NE torold — nevezd at (a WAL/SHM fajlokkal egyutt)
Rename-Item nodu_monitor.db  ("nodu_monitor.db.before-restore." + (Get-Date -Format "yyyyMMddHHmmss"))
Remove-Item nodu_monitor.db-wal, nodu_monitor.db-shm -ErrorAction SilentlyContinue

# 4. Masold be a snapshotot, majd indits: az init_db visszakapcsolja a WAL-modot
Copy-Item "backups\nodu_monitor.db.<IDOBELYEG>.db" nodu_monitor.db
& "C:\Users\ZoltanPoczai\AppData\Local\Python\pythoncore-3.14-64\python.exe" server.py
```

A snapshotok `journal_mode`-ja `delete` (a `VACUUM INTO` nem viszi a WAL-t) — ez NEM
hiba, az `init_db()` inditasnal visszaallitja a WAL-t. A visszaallitas utan futtasd le
a `python main.py --health`-et: a `stale` sorok megmutatjak, mi maradt le kozben.

A `--test-slack` azert kell, mert a digest csak akkor kuld, ha VAN kikuldheto jel, a
heartbeat pedig csak akkor, ha VAN hibas connector — egy friss webhook-beallitast
egyik uttal sem lehet azonnal igazolni.

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
| C | **Slack-webhook** (`alerts.slack`) | ✅ **KÉSZ (2026-07-27), ÉLESBEN VERIFIKÁLVA — a riasztási lánc ÉL.** `--test-slack` → **HTTP 200**, a teszt-üzenet kiment a csatornába; az admin UI „Csatorna kész"-t mutat. **Egy csapda a beállításnál (jegyezd meg):** az URL első nekifutásra `SLACK WEBHOOK: https://...` formában került a `.env`-be — szóközzel és kettősponttal. Az `env_secrets._load_env_file()` a `=` jel nélküli sorokat **csendben eldobja**, tehát a titok ott volt a fájlban, mégis „nincs beállítva" állapot látszott. Javítva a soron (`SLACK_WEBHOOK_URL=<url>`); a `--test-slack` pontosan ezért kell, mert enélkül ez a néma hiba csak a következő digestnél derült volna ki. A csatorna `enabled: true`, a webhook-URL-t a `.env` `SLACK_WEBHOOK_URL` sorából oldja fel (`alerts/notifier.slack_webhook_url`, env → .env → config.yaml fallback) — **nem** a git-tracked config.yaml-ből, ugyanazon okból, amiért a `GEMINI_API_KEY` sem ott van (§5). **URL nélkül minden Slack-út csendben kihagyja magát**, és — ez a fontos — a digest **nem** állítja `alerted`-re a posztokat: a `send_slack` mostantól `bool`-t ad vissza, és a `send_alerts` csak valódi kiküldés után írja be a `slack`-et a `delivered`-be (korábban a puszta „nincs kivétel" is kiküldésnek számított volna — ez a §3.6-os hibaosztály). Új: `python main.py --test-slack` (a valódi `_post_slack_blocks` úton, exit-kód 0/1), az admin UI Slack-kártyája pedig **állapotot** mutat, nem szerkeszthető titkot. **Mérés:** 24/24 lánc-teszt zöld (URL nélkül / rossz host / érvényes URL / HTTP-hiba / `enabled: false`), és élesben, URL nélkül: `--test-slack` → „nincs webhook-URL" (exit 1), `--digest` → **90 találat `new`-ban MARAD** (nem tűnt el). URL-lel: `--test-slack` → HTTP 200. **Csatorna-döntés (Zoltán, 2026-07-27): EGY csatorna mindennek** (digest + heartbeat + heti összefoglaló + tartalom-javaslatok) — a mai kód pontosan ezt teszi, tehát a szétválasztásra (külön `SLACK_WEBHOOK_URL_HEALTH`) NINCS szükség; ne írd meg elvileg |
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

| O | **LinkedIn Thought Leadership Engine (kommentgenerálás újratervezve)** | ✅ **Kész (2026-07-27), élesben verifikálva.** Új modul: `responder/linkedin_engine.py`; a `draft_generator.generate_linkedin_reply` vékony delegáló lett (a route-ot nem kellett átírni). **A régi baj:** egy prompt kérte a döntést ÉS a szöveget, ezért a modell a legkönnyebb utat választotta — összefoglalt, egyetértett, dicsért. **Most:** `REASON` (1 strukturált hívás: intent, core thesis, missing perspective, strategia-pontozás, egy insight) → `COMPOSE` (1 hívás) → **determinisztikus kapu** kódban. **2 hívás, nem 9** — a projekt saját elve (01-audit §6/§7) és a brief token-korlátja miatt; a 9 felelősség sémamezőnként megmaradt. **A stratégiát a KÓD választja** a modell 0–10-es pontszámaiból (`pick_strategy`), mert enum-választásnál pozíció-torzítást mutatott: 5 posztból 4-5 ugyanazt kapta. Pontozás után: 5 posztra 4 különböző stratégia. **A kapu determinisztikus**, nem LLM-es önértékelés: tiltott fordulatok (EN+HU), hossz, bekezdésszám, márkaemlítés, emoji/hashtag/felkiáltójel, és **4-gram átfedés a poszttal** (az „összefoglalta" hiba mérhető proxyja: eredeti komment 0%, poszt-visszamondás 65%). Sértésnél EGY célzott újraírás, a konkrét hibákkal. **Token:** a régi kód a teljes NODU tudásbázist (~274 KB ≈ 70k token) beforgatta MINDEN hívás promptjába — kivezetve. **13 kapu-teszt + 5 éles poszt** (EN/HU), 0 újraírás kellett. Élő mérés: 83–105 szó, átfedés 0%, `/linkedin/compose` mind a 8 legacy mezőt adja |
| P | **Márkaemlítés: a poszt tulajdonsága, nem beállítás** | ✅ **Kész (2026-07-27), élesben verifikálva.** Új reasoning-mező: `explicit_tool_request` + `tool_request_quote`. A `linkedin.brand_positioning` alapértelmezése `'on_request'` (volt: `'off'`). **Három kapu, mind kell:** (1) a poszt kifejezetten eszközt kér; (2) az idézett kérdés **ellenőrizhetően szerepel a posztban** — normalizált részszöveg-keresés, min. 3 szó (a projekt zero-hallucination elve: a modell „igen, kértek eszközt" állítását nem fogadjuk el a szavára); (3) a téma ∈ {archicad, revit, interoperability, ifc} — egy renderelő-kérdés nem meghívó a Bridge-re. Engedve is szigorú a keret: EGY tagmondat, tényszerűen, egy opció a többi közt, link és állítás nélkül. **Élő A/B ugyanazzal a fájdalommal:** kérdéssel → megnevezi (`brand_mode=bridge`), kérdés nélkül → nem említi és `business_impact` stratégiára vált (`none`), más témában feltett eszköz-kérdésre → elutasítja és helyette hasznos renderelési választ ad. **17 teszt** (hamis pozitívok: hallucinált idézet, túl rövid idézet, téma-eltérés, `off` szigorú mód). Minden válasz tartalmazza a döntés indokát: `brand_gate_reason` |
| N | **„Lehetőségek" fül: csatorna-szűrő + valódi totál** | ✅ **Kész (2026-07-27), élesben verifikálva.** A kérés csak a szűrő volt, de a mérés egy nagyobb hibát is kidobott: a `dashboard()` route `limit=100`-cal kérte a lehetőségeket, **305-ből** — és a nav-badge meg a metrika-kártya a *lista hosszát* írta ki totalként, tehát „100"-at. Ugyanaz a hiba, mint §7/J-ben. **Ha csak kliens-oldalon szűrtem volna, az OSArch 14 helyett 2-t mutatott volna.** Három javítás: (1) új `count_opportunities()` + `get_opportunity_platform_counts()` a `_opportunity_where()` közös WHERE-re épülve (mint `_posts_where()` a §7/J-nél) — így a számláló és a lista **ugyanarra a halmazra** vonatkozik; (2) a badge/metrika a **valódi** totált mutatja, a render-keret `ui.opportunities_limit` (default 400), és ha mégis csonkol, a status-sor **kiírja**; (3) pill-sor a szekcióban, **a platform-listát az adatból építve** (nem beégetve, így új forrás automatikusan megjelenik), a darabszámok SQL-ből. **Mérés:** 305 kártya renderelve, `osarch` → 14, `IfcOpenShell/IfcOpenShell` → 37 (a `/` miatt `CSS.escape` kell a szelektorban), „Összes" → 305. Két szomszédos hibát is javítottam: a `selectChannelFilter` globális `.filter-pills-row .filter-pill` szelektora **a másik két fül aktív pilljét is levette** (most `#s-raw`-ra szűkítve), és a Discourse-pill `<button>`-je `</label>`-lel volt zárva |
| **Q** | **Slack-digest: MINDEN jel kimegy, lapozva** | ✅ **Kész (2026-07-27), élesben verifikálva.** Zoltán döntése: a régi „első 5 részletezve, a többi «… és még N további»" viselkedés nem elfogadható, mert a digest utána `alerted`-re állítja mindet — a 90 felgyűlt jelből **85 láthatatlanul elhasználódott volna**. **Miért nem megy egy üzenetben:** a Block Kit **50 blokk/üzenet** korlátot ír elő, a section-blokk `text`-je max **3000 karakter** ([docs.slack.dev/reference/block-kit/blocks](https://docs.slack.dev/reference/block-kit/blocks), [section-block](https://docs.slack.dev/reference/block-kit/blocks/section-block)), az incoming webhook pedig **1 üzenet/másodperc** ([rate limits](https://docs.slack.dev/apis/web-api/rate-limits)) — ezért `posts_per_message: 20` (config, felső korlát 49 a fejléc miatt) + **1,2 s szünet** a lapok között, és a 3000 feletti szöveg levágva, nem hibára futva. **A részleges hiba nem számít kiküldésnek:** ha egy lap elbukik, a `send_slack` `False`-t ad, a digest NEM állít `alerted`-re semmit, a következő futás újrapróbálja (ismétlés elfogadható, jelvesztés nem). **Mérés:** 37/37 teszt (lapszám, blokk-limit, section-limit, „mind a 90 cím benne van", config-kapcsoló, 49-es plafon, részleges hiba), majd élesben **90 jel → 5 üzenet (20/20/20/20/10)**, mind `alerted`, a rákövetkező `--digest` **0 jel** |
| **V** | **Az audit P2-es tételei (§3.1–3.9, §5/#11–12)** | ✅ **Kész (2026-07-28), élesben verifikálva. `test_p2_fixes.py` 42/42.** **(3.4–3.5) Az LLM szenzor, nem bíró:** a `nodu_mention` kivezetve a sémából — a márkaemlítést `detect_brand_mention()` regex dönti el (a modell 1431 jelből 1-ben jelölte, a regex ugyanazt találja); a `competitor_name` mellé **kötelező `competitor_quote`**, amit a kód megkeres a posztban (min. 3 szó, normalizált részszöveg), és ha nincs meg, a jelölést eldobja — **élesben azonnal fogott egy hallucinációt** („similar to the IFC Structure tree in BIM Vision", ami nem szerepelt a posztban). Ez a §4/16 és §4/18 elv alkalmazása. **(3.1)** A severity-prompt mind az öt fokozatát horgonyoztuk, `CLASSIFIER_VERSION` → **v4**, és új `main.py --calibrate N` (páros újraértékelés, a DB-t NEM írja). **A mérés kimondja, hogy a severity nem lesz prioritási kapcsoló** — ld. lentebb. **(3.2)** A `confidence` **kikerült minden rendezésből** (sd=0,037), a `buying_intent` a `severity` elé. **(3.3)** A SalesOS-score `severity×2 (+1 intent, −1 solved_internally)`: **4 → 7 distinct érték**, Qualified 113 → 125/177. **(3.8)** A classifier-sor **FIFO** + `posts.classify_attempts` (3 kísérlet után kiesik): a 4 napja várakozó posztok sorra kerültek, hátralék **104 → 31**. **(3.9)** `delay_seconds` **13 → 2**, mért alapon: 13 s → 4,5 RPM, 5 s → 9,7, 2 s → 18,1; tartós 30-as kör 3,9 s/poszt (15,2 RPM), **0 db 429**. 100 poszt átfutása ~3 óra → **~6,5 perc**. **(3.6)** `stackoverflow` → `enabled: false` (1887 nyers elem → 5 poszt → 0 jel); a kód és a config marad, CLI-ból futtatható. **(3.7)** `revitforum`: már nem volt ütemezve (`forums: {}`). **(§5/11)** `max_output_tokens` 200 → **320**. **(§5/12)** `storage/backup.verify_snapshot()`: `integrity_check` + tábla-olvasás minden mentés után, **a rotáció előtt** — sérült vagy 0 posztos snapshot nem szorít ki egy jót. **Egy kölcsönhatás, amit tudni kell:** üres DB-n a backup mostantól szándékosan `None`-t ad („gyanúsan üres"), ezért a P1-teszt fixture-jébe be kell szúrni egy posztot |
| **U** | **Az audit hét P1-ese (§2.1–2.7)** | ✅ **Kész (2026-07-28), élesben verifikálva. `test_p1_fixes.py` 38/38.** **(2.1)** A draft-generálás NEM állítja `alerted`-re a posztot — a `mark_alerted` két hívása kivezetve `responder/draft_generator.py`-ból. Ez vette el a jeleket a 07:30-as draft-jobbal a 08:00-as digest elől, és emiatt volt 1692 posztból **0** a `draft_ready` státuszban. A draft-küszöb (`classifier.draft_min_severity`) mostantól a digest-küszöböt követi, ha nincs külön megadva — két külön döntés, de nem csúszhat szét véletlenül. **(2.2)** Új `main.connector_schedule()` = **EGY igazság**: ebből regisztrálja a jobokat az ütemező ÉS ebből tudja a heartbeat, mire kell számítania. Új `stale` státusz a `get_connector_health`-ben (`expected` + `health.stale_factor: 2.5`): ami ütemezve van, de nem fut, riaszt — eddig láthatatlan volt, mert a riport csak a lefutott körökből épült. **Élesben azonnal kidobta a `backup` és a `digest` hiányát, és Slack-riasztást küldött.** **(2.3)** A `backup` és a `digest` `runs`-bejegyzést ír, tehát a kimaradásuk mostantól `stale`-ként látszik. **(2.4)** A 274 KB-os tudásbázis kivezetve a fórum-draft promptból: **260 126 → 1 361 karakter**; a heti tartalom-/trend-generálásnál `knowledge_base.prompt_max_chars` (8000) a keret. Nem csak költség: belső anyag (sprint-tervek, licenc-kalkulátor) került a modell elé, amikor NYILVÁNOS kommentet írt. **(2.5)** Új `_FirstRunPlanner`: az első futás `utolsó futás + periódus`-ból számolódik (+20 s/job stagger), nem `now`-ból. **Mérés: újraindítás után 0 connector-kör 45 s-en belül** (előtte mind a 11 azonnal; 07-27-én ez 3 óra alatt 71 futást és 132 Brave-queryt jelentett). **(2.6)** `server._SecretRedactingFilter` mindkét log-handleren: `AIza…`, `hooks.slack.com/services/…`, `?key=`, `Bearer`, Brave-kulcs. ⚠️ **A MEGLÉVŐ logsorokat nem javítja** — a `logs/monitor.log`-ban lévő CSE-kulcsot a GCP-n vissza kell vonni (felhasználói lépés). **(2.7)** A jelszókapu mind a **8** mutáló végponton (`/save`, `/run/<action>`, `/draft/*/approve|reject`, `/lead/*/to-sales-os`, `/lead/*/draft`, `/linkedin/compose`, `/search/adhoc`) — eddig csak az `/admin` GET-en volt, tehát egy beállított jelszó hamis biztonságérzetet adott. Plusz `_run_in_bg` egyidejűség-védelem: a második indítás **409**, nem indul két Chromium. **Két csapda, amit menet közben kellett kezelni:** a `reddit` kulcs nélkül nem ír `runs`-sort → `expect_runs: False`, különben tartós hamis 503; a `digest` `items_seen`-je **1** („lefutott"), nem a várakozók száma → különben 5 csendes nap után hamis `blind` riasztás |
| **T** | **Khoros-dedup + digest-halmaz (az audit két P0-ja)** | ✅ **Kész (2026-07-28), élesben verifikálva.** **(1) Dedup:** új `connectors/khoros_url.py` — `canonical_external_id()` = `<host>:<message-id>` a `/m-p/`, `/ta-p/`, `/td-p/` mintából, a query és a fragment nélkül; a connector ÉS a migráció **ugyanezt** hívja (külön implementáció esetén a két kulcs elcsúszhatna, és a dedup újra elromlana). Migráció: `migrations/2026_07_28_khoros_dedup.py`, dry-run alapértelmezés + `--apply`, ami **saját snapshotot** készít (`keep=99`, hogy a napi rotáció ne vigye el) és egyetlen tranzakcióban fut. A túlélő-választás sorrendje: van draftja → van signalja → legkisebb id; a statusz a csoport legelőrehaladottabb státuszát örökli, hogy egy már kiküldött jel ne kerülhessen vissza `new`-ba. **Mérés: `posts` 1692 → 446, Khoros 1309 → 33, `signals` 1431 → 317, Lehetőségek 504 → 129; `integrity_check` ok, 0 árva sor; a törölt 6 draft mind `pending` volt, jóváhagyott nem esett ki.** Éles kör a javítás után: **48 elem → 0 új** (előtte ugyanabból 30), `items_seen=48`, tehát a heartbeat sem ad hamis riasztást. **(2) Digest-halmaz:** `_opportunity_where` kapott `post_status` paramétert, a `run_digest` **SQL-ben** szűr `'new'`-ra, és a `limit`-et a `count_opportunities`-ból veszi, plusz hangosan jelez, ha mégis csonkolna. **A 32 „strandolt" jel maga is duplikátum volt** (már kiküldött szálak másolatai) — valódi lead nem esett ki, a javítás értéke előretekintő. Teszt: `test_dedup_and_digest.py` **20/20**, benne a régi logika szimulációja ugyanazon az adaton (30 várakozóból **0**-t adott volna vissza) |
| **S** | **Draft-döntés naplózása: ki hagyta jóvá** | ✅ **Kész (2026-07-27), élesben migrálva.** `drafts` + 3 oszlop: `decided_by`, `decided_at`, `decided_by_source`. **A kért név `approved_by` volt — `decided_by`-ra változtattam**, mert ugyanaz az út kezeli az elutasítást is, és egy `approved_by='Kata'` egy `rejected` sornál félrevezető. **A `_by_source` a napló SÚLYA, és ez a lényeg:** ma nincs felhasználó-azonosítás (a `ui.admin_password` egyetlen közös jelszó, a basic-auth username-t senki nem ellenőrzi), tehát a webes név **önbevallás** → `'form'`; a CLI (`--review`) az OS-felhasználót írja → `'cli'`; a `'auth'` érték a jövendő hitelesített útra van fenntartva. Így ha egyszer lesz auth, a régi sorokról is látszik marad, hogy gyengébb bizonyítékok. **Név nélkül a régi viselkedés marad** (NULL = „nem tudjuk", mint `runs.items_seen`), és a statuszváltás akkor is megtörténik — a napló nem kapu. Felvétel sorrendje: űrlap/JSON `decided_by` → basic-auth username → `ui.default_decider`. A dashboard egyszer kérdezi a nevet és `localStorage`-ben tartja. Olvasás: `GET /api/decisions?limit=N` (csak a nevesített döntések). **Mérés:** 30/30 teszt ([test_draft_decisions.py](../test_draft_decisions.py)) — migráció régi sémán, idempotencia, régi sorok érintetlensége, trimmelés/80 karakter, mindkét route, basic-auth fallback, névtelen kérés; élesben a `drafts` megkapta a 3 oszlopot, a meglévő 12 pending + 1 approved sértetlen, `/api/decisions` → 200 |
| **R** | **Csapat-hozzáférés: ma csak Slack-láthatóság** | 🟡 **Zoltán döntése (2026-07-27): a kollégák EGYELŐRE csak Slackben kapják a jeleket — ez ideiglenes, nem végállapot.** Jóváhagyni ma nem tudnak, két okból: (1) az incoming webhook **egyirányú** — Slack-gombhoz internetről elérhető interactivity request URL kell aláírás-ellenőrzéssel; (2) a dashboard `127.0.0.1:5050`-en hallgat ([server.py:140](../server.py:140)), és a `ui.admin_password` **üres**, tehát a felület hálózatra nyitása ma az API-kulcsokat és a connector-indítást is védelem nélkül tenné közzé. **A sorrend, ha ez napirendre kerül:** valódi többfelhasználós auth (tudni kell, KI hagyta jóvá — a mai egy-jelszavas basic-auth erre nem elég) → hálózati elérés (LAN-IP vagy overlay/HTTPS proxy) → Windows Service (§7/F, a mai processz nem éli túl az újraindítást) → és csak ezután Slack-interaktivitás, ott is inkább „nyisd meg a dashboardon" link, mint gomb: a jóváhagyás naplózandó esemény. **Nyitott kérdés Zoltántól (2026-07-27, félbehagyott mondat):** a felületek és a kommentgenerálás elhelyezéséről volt kezdő gondolata — tisztázandó, mielőtt bármi épül |
| M | **support.graphisoft.com bekötve — de NEM leadforrás** | ✅ **Kész (2026-07-26), élesben verifikálva.** Zendesk Help Center, nyílt API. **32 poszt** a két interop-szekcióból. **De tudni kell, mi ez:** a cikkeket a Graphisoft supportja írja, `comments_disabled: true`, a szerző staff — **nincs kit megszólítani**, ezért a `graphisoft-support` rajta van a `responder.exclude_platforms` listán. A classifier ezt magától is felismerte: **6,2% fájdalom-arány** (32-ből 2), a leggyengébb az összes forrás közül — ez itt NEM hiba, hanem a helyes viselkedés. Amit ad: piaci intelligencia arról, melyik interop-probléma fordul elő elégszer ahhoz, hogy KB-cikk szülessen róla |

> **Két mérésből jött döntés a Zendesk-connectorban — ne „javítsd" vissza.** (1) A poszt `created_at` mezőjébe az **`updated_at`** kerül: a 234 kulcsszó-találatból `created_at` szerint csak **45** esne 1 éven belülre, és pont a jók esnének ki („Unable to import a Revit file into Archicad", score 25, 2024-es cikk 2026-os frissítéssel; „IFC import, how to translate Revit stories", 23). `updated_at` szerint mind a 234 bejön, és 0 esett ki kor miatt. Egy KB-cikknél a frissítés dátuma a releváns, nem a születésé. (2) Csak **két szekcióból** gyűjtünk („Collaboration with Other Software", „Project Data & BIM"): a maradék ~200 találat licencelési/BIMcloud/BIMx/renderelési zaj, a magas score-ú interop-cikkek mind ebben a kettőben vannak. A szekciókat **név szerint** konfiguráljuk, futásidőben oldódnak fel id-re — a site-on 5 db azonos nevű („General") szekció is van.

> **A Zendesk community HALOTT** — 5 poszt, mind 2020-12-03, és azok a Zendesk **gyári demo-bejegyzései** („What is the community?", „Feature a post"), amiket sosem töröltek. A connector ezért a community-végpontot meg sem hívja. Ha valaki később mégis rákeresne: nem elfelejtettük, hanem nincs ott semmi.

> **Lefedetlen források, amiket a Brave-kereső felhozott** (P3-jelöltek): ~~`community.osarch.org`~~ (✅ A pont), ~~`speckle.community`~~ (✅ 2026-07-26), ~~`support.graphisoft.com`~~ (✅ 2026-07-26, M pont). **A lista elfogyott.** Új forrásnál ELŐBB mérd meg a motort (§4/13), a rate limitet (§4/14) ÉS a robots.txt-t (§4/15) — és kérdezd meg magadtól, hogy van-e ott EMBER, akinek válaszolni lehet (§7/M tanulsága).

---

## 8. Folytatás sorrendje (javasolt)

1. Olvasd el ezt a fájlt. Ha mélyebb kontextus kell: `docs/02-lead-volume-audit-2026-07.md` (üzemállapot, mérések, döntések), majd `docs/01-architektura-audit-2026-07.md` (stratégia).
2. **Ellenőrizd a rendszer állapotát:** `python main.py --health` vagy `GET localhost:5050/health`. Ha nem fut a szerver, indítsd (§6) — **absolute interpreter-úttal** (§4/6!).
3. **A §7/C KÉSZ — a Slack él, és a felgyűlt készlet KI IS MENT.** Ellenőrzés egy paranccsal: `python main.py --test-slack` (HTTP 200 = a lánc rendben). A 90 felgyűlt jel 2026-07-27-én **5 Slack-üzenetben, mind a 90 részletezve** kiküldve (§7/Q), utána mind `alerted`; egy második `--digest` **0 jelet** talált, tehát nincs duplikáció. Innentől a napi digest normál üzemben fut.
4. Utána szabadon választható, prioritási sorrendben:
   - **A LinkedIn-motor kapu-paramétereinek hangolása** éles használat után (`MAX_NGRAM_OVERLAP=0.22`, 60–175 szó, `_STRATEGY_BIAS`). Ezek az ELSŐ hangolás értékei, 5 poszton mérve — 20-30 valódi komment után lesz értelme finomítani. A `quality_issues` és a `rewrites` mező minden válaszban ott van, tehát mérhető, mi bukik el.
   - **A LinkedIn-motor stratégia-diverzitásának ellenőrzése** nagyobb mintán: a `strategy_fit` pontszámok szorosak (8-9), tehát a `_STRATEGY_BIAS` finomhangolása változtathat a mixen.
   - **Reddit-kulcs** (B pont), ha közben megjött a jóváhagyás.
   - Új forrás: a P3-as lefedetlen lista elfogyott, tehát ez már felderítést igényel (a Brave-kereső `websearch` posztjainak domain-megoszlása a jó kiindulás — az hozta fel az OSArch-ot és a Speckle-t is).

> **Amit NE tegyél:** ne told a LinkedIn-motort 9 külön LLM-hívásra „mert a spec úgy írta" — a 2 hívásos felépítés indoka a modul-docstringben van (költség, latencia, és a projekt §6/§7 elve). És ne tedd az LLM-et bíróvá ott, ahol pontoztatni is lehet (§4/16).
