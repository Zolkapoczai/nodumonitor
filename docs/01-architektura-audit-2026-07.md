# NODU Monitor — Architektúra-audit és pivot-döntés
**Dátum:** 2026-07-19 · **Szerep:** Principal Architect review · **Tárgy:** hírfigyelőből → Buying Signal Detection Engine

---

## 1. Vezetői összefoglaló

**Verdikt: a pivot helyes, az architektúra-kérdésre a válasz pedig: "az agyat újraépíteni, a csöveket megtartani."**

A jelenlegi Monitor egy **begyűjtő váz** (harvesting skeleton): connectorok, deduplikáció, ütemezés, jóváhagyási workflow, n8n→Pipedrive híd. Ez a kód ~30%-a, és **újrahasznosítható**. Amit a pivot igényel — intent-detektálás, fájdalom-osztályozás, cég/személy-feloldás, opportunity-modell, pontozó motor — az **ma nem létezik a kódbázisban, tehát zöldmezős fejlesztés lenne akkor is, ha "inkrementálisnak" hívjuk, és akkor is, ha "újraírásnak".**

A legfontosabb, előre kimondandó ellenvélemény a briefben szereplő elvárásokkal szemben: **ez nem big-data probléma.** Az Archicad↔Revit interop-fájdalom globálisan is szűk sáv: a releváns források együtt napi 50–300 nyers elemet termelnek, ebből valódi buying signal heti néhány darab. A javasolt üzenetsorok, vektoradatbázis-klaszterek, horizontálisan skálázó agent-flották ezen a volumenen **nettó kárt okoznak**: üzemeltetési terhet adnak egy egyszemélyes csapatnak, miközben a szűk keresztmetszet nem az áteresztőképesség, hanem a **jelminőség és a forráslefedettség**. A helyes architektúra: **moduláris monolit, tiszta stage-szerződésekkel, cserélhető szolgáltatói adapterekkel** — ami *interfész-szinten* felkészül a későbbi queue-ra/vektortárra, de *nem telepíti* őket, amíg a volumen nem indokolja.

---

## 2. A jelenlegi Monitor értékelése

### Ami jól sikerült
| Elem | Miért érték |
|---|---|
| Connector-minta (`connectors/`) | Forrásonként izolált, hibatűrő, `run()` szerződéssel — bővíthető újratervezés nélkül |
| Dedup a DB-szinten (`UNIQUE(platform, external_id)`) | Olcsó, determinisztikus első szűrő |
| `runs` napló | Auditálhatóság csírája már megvan |
| Draft → emberi jóváhagyás workflow (`drafts` tábla + dashboard) | **Ez a legértékesebb termék-DNS**: human-in-the-loop outreach — pontosan ez kell a jövőben is |
| Webhook-alapú CRM-leválasztás | A CRM-írás külön modul — a célpont cseréje (Pipedrive → SalesOS ingest API) nem érinti a pipeline többi részét |
| Egyprocesszes futás (server.py, 1. fázis refaktor) | Alacsony üzemeltetési költség — megőrzendő tulajdonság |

### Ami elvi szinten elavult a pivot után
| Elem | Probléma |
|---|---|
| **Kulcsszó-szűrő mint döntéshozó** (`filters/keyword_filter.py`) | Szó-egyezést lát, intentet nem. A "IFC export" találat ≠ fájdalom. A pivot lényege pont ennek a meghaladása |
| **`score` = kulcsszám-darabszám** | Egydimenziós, kalibrálhatatlan, üzletileg értelmezhetetlen |
| **Lapos `posts` tábla** | Link-lista adatmodell. Nincs személy, nincs cég, nincs opportunity, nincs életciklus — a termék kimenete nem reprezentálható benne |
| **Google CSE connector** | Halott: a Google 2026-ban lezárta az API-t új ügyfelek előtt (élesben verifikálva ebben a projektben). Törlendő |
| **HTML-connector a Khoros fórumokra** | 403-mal blokkolt, jelenleg nulla értéket termel |
| **Config-YAML-t írogató admin UI** | Titkok plain textben, párhuzamos írás veszélye — a 2. fázisban amúgy is env-be szánt megoldás |
| Nincs visszacsatolási hurok | A jóváhagyott/elutasított draftok kimenete sehova nem folyik vissza — pedig ez lenne a jövőbeli címkézett tanítóadat |

---

## 3. Megtartani vs. lecserélni

| Réteg | Döntés | Indoklás |
|---|---|---|
| Reddit connector (PRAW) | **Megtartani** | Működő, ingyenes API; csak a kimenetét kell az új modellre kötni |
| Stack Overflow connector | **Megtartani** | Működik, alacsony érték, de nulla költség |
| Playwright connector | **Megtartani + élesíteni** | Ez az egyetlen járható út a Khoros fórumokra (Graphisoft/Autodesk) — a legmagasabb jelsűrűségű forrásokra |
| RSS/HTML connector | **Lecserélni** | 403-blokkolt; helyette Playwright + új Discourse/GitHub connectorok |
| Google CSE | **Törölni** | API megszűnt új ügyfeleknek; adapter-interfész mögé Brave/Serper/Exa kerülhet |
| Kulcsszó-szűrő | **Visszaminősíteni** | Nem döntéshozó, hanem olcsó **elő-szűrő** (mi kerüljön LLM elé) — így a szerepe megmarad, a hatalma nem |
| SQLite | **Megtartani (egyelőre)** | Napi pár száz rekordnál a Postgres-migráció idő előtti; a váltási pont definiálva (ld. 12.) |
| `posts/runs/drafts` séma | **Lecserélni** | Új domain-modell kell (ld. 8.); a `posts` átnevezve `source_items`-ként túlél |
| Flask dashboard | **Megtartani rövid távon** | Az opportunity-review UI ráépíthető; hosszú távon a NODU Sales CRM UI váltja ki |
| APScheduler + waitress egyproc | **Megtartani** | Az 1. fázis refaktor eredménye pontosan a jó irány |
| CRM-híd (n8n → Pipedrive) | **Átirányítani** | A Pipedrive kikerült (SalesOS "tiszta lap" döntés); az új cél a SalesOS `POST /api/bridge/ingest` — **közvetlen hívással, n8n nélkül** (ld. 6. és 10.) |
| Gemini draft-generátor | **Átépíteni** | A koncepció (AI-javaslat + emberi jóváhagyás) marad, de provider-adapter mögé kerül, és az opportunity-kontextusból táplálkozik |

**Mérleg: a kód ~30%-a él tovább változatlanul, ~20%-a átalakítva, ~50%-a (az intelligencia-réteg) új.**

---

## 4. Ajánlott termékirány

1. **A termék kimenete az Opportunity-objektum, nem a találati lista.** Minden más (UI, pontozás, CRM-push) ebből vezethető le.
2. **Jelminőség > jelmennyiség.** Napi 3 jó opportunity többet ér, mint 300 link. A rendszer sikerkritériuma: a jóváhagyási arány (approved / detected) növekedése.
3. **Human-in-the-loop kötelező kapu az outreach előtt.** Automatikus fórum-válasz vagy tömeges hideg-DM bant, brandkárt és GDPR-kockázatot termel. A meglévő draft-jóváhagyási minta a helyes: az AI javasol, ember enged ki.
4. **A moat a niche-lefedettség + osztályozási minőség**, nem az infrastruktúra. Senki más nem indexeli célzottan a Graphisoft Community + Bonsai GitHub issues + buildingSMART fórum metszetét fájdalom-lencsével.
5. **Minden emberi döntés címkézett adat.** Az approve/reject/won/lost visszafolyik a pontozás kalibrálásába — ez a rendszer tanulási hurka, és idővel ez lesz a legnehezebben másolható eszköz.

---

## 5. Cél-architektúra

**Moduláris monolit, pipeline-topológiával, DB-vezérelt állapotgéppel.**

```
┌────────────────────────── EGY PROCESSZ (ma) ──────────────────────────┐
│                                                                        │
│  Collectors ──▶ source_items (raw, immutable)                          │
│                     │  status: new                                     │
│  Pre-filter ────────▶ status: prefiltered / discarded                  │
│  (kulcsszó, olcsó)  │                                                  │
│  Classifier ────────▶ signals (LLM: pain, intent, tech, severity)      │
│  (LLM-adapter)      │                                                  │
│  Resolver ──────────▶ persons / companies (konfidenciával, félautomata)│
│  Scorer ────────────▶ opportunities (verziózott súlyprofillal)         │
│                     │  lifecycle: detected → triaged → ... → converted │
│  Review UI (Flask) ─▶ emberi kapu: approve / reject / edit             │
│  Outreach gen ──────▶ outreach_assets (draft: reply / DM / email)      │
│  CRM Writer ────────▶ SalesOS POST /api/bridge/ingest (közvetlen)      │
│  Feedback loop ─────▶ outcome-ok vissza a scoring-kalibrációba         │
└────────────────────────────────────────────────────────────────────────┘
```

Kulcsdöntések:
- **Stage-szerződés:** minden lépés bemenete/kimenete DB-rekord státusszal. Egy stage = egy idempotens függvény, ami `status=X` rekordokat visz `status=Y`-ba. Ez adja ingyen: újraindíthatóság, párhuzamosíthatóság, auditálhatóság, és azt, hogy **bármely stage külön processzbe/queue-ba emelhető később kódmódosítás nélkül** — ez a valódi "future-proofing", nem a Kafka.
- **Provider-adapterek:** `LLMProvider`, `EmbeddingProvider`, `SearchProvider` interfészek. A Gemini/Claude/OpenAI, ill. Brave/Serper/Exa e mögött cserélhető. Nincs LangChain — vékony, saját adapter (kevesebb függőség, teljes kontroll).
- **Nincs üzenetsor, nincs vektor-DB, nincs microservice — ma.** A DB-as-queue (státuszoszlopok) ezen a volumenen egyszerűbb és ugyanazt tudja. A beemelési pontok definiálva (ld. 12.).
- **Embedding szerepe szűkítve:** cross-source duplikátum-felismerésre és visszatérő fájdalom-témák klaszterezésére hasznos; SQLite mellett fájl-alapú (sqlite-vec vagy numpy), Postgres-váltáskor pgvector. Külön vektoradatbázis **nem indokolt**.

---

## 6. Adatáramlás (célfolyamat)

1. **Collection** — connectorok forrásonkénti ütemezéssel → `source_items` (nyers, változatlan, forrás-URL-lel).
2. **Normalizálás** — egységes mezőkészlet (már ma is így megy be a DB-be — megtartva).
3. **Dedup** — (a) exakt: platform+external_id (megvan); (b) szemantikus: embedding-hasonlóság cross-source (új, pl. ugyanaz a kérdés Redditen és fórumon).
4. **Nyelvdetektálás** — olcsó lib (lingua/fasttext); nem-angol tartalom megjelölése. Fordítás csak osztályozáshoz, on-the-fly az LLM-ben (a modern modellek natívan többnyelvűek — külön fordító-stage felesleges).
5. **Elő-szűrés** — a mai kulcsszó-készlet, kiterjesztve: csak az kerül LLM elé, ami átmegy. Cél: LLM-költség kordában tartása (~70–90% kiszűrése).
6. **AI-osztályozás** — egyetlen strukturált LLM-hívás/elem, JSON-kimenettel: fájdalom-e, fájdalom-összefoglaló, technikai összefoglaló, érintett technológiák (Archicad/Revit/IFC valószínűségek), probléma-típus (parametrikus adat / metaadat / geometria / koordináció), súlyosság, buying-intent jelek, szerző-szerep hipotézis, konfidencia + indoklás. **Egy hívás, egy séma — nem 6 külön "agent-hívás"** (költség és latencia miatt).
7. **Cég/személy-feloldás** — LLM-kivonatolás a posztból + profiloldalból (aláírás, "we are a 50-person firm in Munich" típusú jelek); alacsony konfidencia esetén **emberi megerősítésre vár** — a feloldás félautomata, és ez szándékos (GDPR + hallucináció-kockázat, ld. 11.).
8. **Pontozás** — verziózott súlyprofil (ld. 9.).
9. **Opportunity-létrehozás/összevonás** — ugyanazon személy/cég ismételt jelei EGY opportunity alá aggregálódnak (a jel-ismétlődés maga is pontszám-emelő).
10. **Review UI** — emberi kapu.
11. **Outreach-generálás** — jóváhagyott opportunity-hoz: publikus válasz-draft, LinkedIn-nyitó, hideg e-mail — a signal-kontextusból.
12. **CRM-írás** — **közvetlen POST a SalesOS `/api/bridge/ingest` végpontjára** (Bearer `BRIDGE_API_KEY`; kontraktus: SalesOS `docs/08-bridge-integracio.md`, implementálva és élesben verifikálva v1.2-ben). N8n erre az útra nem kell: két saját, azonos gépen futó rendszer közé middleware-t tenni felesleges hop.
13. **Visszacsatolás** — approve/reject/won/lost → scoring-kalibráció + prompt-finomítás alapanyaga.

### Monitor ↔ SalesOS munkamegosztás (a 08-as spec tükrében)

A SalesOS ingest-kontraktus **account-centrikus**: cég-adat nélkül (név / houseNo / céges e-mail) 422-vel elutasít — szándékosan. Ez a munkamegosztást is kijelöli, és pontosan egybevág az audit resolver-kapujával:

| Kérdés | Válasz |
|---|---|
| Mi mehet át a SalesOS-be? | Csak **cég-feloldott** opportunity (a Resolver emberi megerősítése után) |
| Hol élnek a feloldatlan jelek? | A **Monitorban** (review UI) — a SalesOS spec explicit így rendelkezik: "az azonosítatlan Reddit-posztok a Bridge oldalán maradnak, amíg cég nem köthető hozzájuk" |
| Score-leképezés | Monitor `score_total` (0–100) → ingest `score` (0–10): osztás 10-zel, kerekítve; a stage-küszöbök (Qualified ≥7, Lead ≥5) a SalesOS env-jében élnek, ott hangolhatók |
| Idempotencia | Monitor opportunity-azonosító → `externalId` (a SalesOS dedup no-op-ot ad ismételt küldésre) |
| `painConfirmed` | A Monitor SOHA nem írja — emberi MEDDIC-kvalifikáció a SalesOS-ben (08 §5) |
| Kötelező mező | `sourceUrl` — a Monitor forrás-URL-je adja (zero-hallucination elv mindkét oldalon) |

---

## 7. "Agent"-architektúra — őszintén

A briefben kért 12 agent valójában **pipeline-stage**, nem autonóm ágens. Determinisztikus orchestráció kell (ütemező hívja őket sorban), nem ágens-autonómia — az outreach-javaslaton kívül sehol nincs szükség LLM-döntésre a *vezérlésben*. Ez olcsóbb, debugolhatóbb, auditálhatóbb.

| Stage (modul) | Felelősség | LLM? |
|---|---|---|
| Collector(ök) | Forrás-API/scraping → nyers elem | Nem |
| Normalizer | Egységes rekordformátum | Nem |
| Deduplicator | Exakt + szemantikus duplikátum-jelölés | Csak embedding |
| Language Detector | Nyelv-címke | Nem (lib) |
| Pre-filter | Kulcsszavas olcsó szűrés LLM elé | Nem |
| Classifier | Fájdalom/intent/tech/súlyosság strukturált kinyerése | **Igen** (1 hívás/elem) |
| Entity Resolver | Cég/személy-hipotézis + konfidencia | **Igen** + emberi kapu |
| Scorer | Súlyozott pontszám a signal-mezőkből | Nem (determinisztikus!) |
| Opportunity Manager | Aggregálás, életciklus-léptetés | Nem |
| Outreach Generator | Válasz/DM/e-mail draftok | **Igen** |
| CRM Writer | SalesOS ingest-payload összeállítás + közvetlen POST (idempotens `externalId`-vel, retry-val) | Nem |
| Feedback Collector | Kimenetek visszaírása kalibrációhoz | Nem |

Fontos elv: **a Scorer determinisztikus** — az LLM mezőket ad (súlyosság, intent-jelek), de a pontszámot súlyprofil számolja. Így a pontozás magyarázható, verziózható, visszamenőleg újraszámolható.

---

## 8. Domain-modell

```
source_items   — nyers begyűjtött elem (immutable)
  id, source, platform, external_id, url, author_handle, title, body,
  lang, created_at, fetched_at, status
  status: new → prefiltered | discarded → classified

signals        — osztályozott jel (1:1 a source_item-mel)
  id, source_item_id, is_pain, pain_summary, tech_summary,
  archicad_p, revit_p, ifc_involved, issue_type[], severity,
  buying_intent_signals[], role_hypothesis, confidence, rationale,
  classifier_version

persons        — szerző-identitás
  id, platform_handle(s), display_name, resolved_role, resolved_company_id,
  resolution_confidence, resolution_status (unresolved|hypothesis|confirmed),
  gdpr_basis, first_seen, last_seen

companies      — feloldott szervezet
  id, name, domain, country, size_estimate, bim_ecosystem, confidence

opportunities  — A TERMÉK
  id, person_id?, company_id?, signal_ids[], scores(json), score_total,
  scoring_version, status, recommended_action, created_at, updated_at
  lifecycle: detected → triaged → approved → contacted → responded
             → qualified → converted | dropped | expired

outreach_assets — draftok (a mai drafts utódja)
  id, opportunity_id, kind (public_reply|linkedin|email),
  text, status (pending|approved|rejected|sent), outcome

scoring_configs — verziózott súlyprofilok
events          — audit-napló (minden státuszváltás, ki/mi/mikor)
```

**Állapotátmenetek:** csak előre definiált élek mentén, minden átmenet `events`-be íródik (auditálhatóság). `expired`: ha egy detected/triaged opportunity N napig (default 21) nem lép, automatikusan lezárul — a frissesség üzleti követelmény.

**Retenció:** `source_items` raw body 90 nap után törölhető (a signal-összefoglaló marad); személyes adat (persons) GDPR-alapon kezelve: jogos érdek dokumentálva, törlési kérés kiszolgálható (person → anonimizálás, opportunity megmarad cég-szinten).

---

## 9. Pontozási modell

Dimenziók (0–100, a Classifier/Resolver mezőiből determinisztikusan képezve):

| Dimenzió | Forrás |
|---|---|
| pain_severity | Classifier: súlyosság + megfogalmazás intenzitása |
| buying_intent | "megoldást keresünk / hetek óta / deadline" jelek |
| role_seniority | Resolver: szerep-hipotézis (BIM Manager > végfelhasználó) |
| company_confidence | Resolver konfidencia |
| recency | Poszt kora (exponenciális lecsengés, felezési idő ~7 nap) |
| tech_fit | Archicad↔Revit + parametrikus/IFC érintettség |
| interop_relevance | Probléma-típus távolsága a NODU Bridge value proptól |
| commercial_potential | Cégméret-becslés + ökoszisztéma |

`score_total = Σ (w_i × dim_i)` — a súlyok **DB-ben tárolt, verziózott profilban** (`scoring_configs`), nem kódban. Minden opportunity tárolja, melyik verzióval számolódott → visszamenőleg újrapontozható, A/B-zhető. Kalibráció: negyedévente a won/lost kimenetek tükrében súly-igazítás (először kézzel, később regresszióval).

---

## 10. Technológiai javaslatok

| Terület | Javaslat | Miért |
|---|---|---|
| Nyelv/runtime | Python marad | Meglévő kód, ökoszisztéma, egy fő fejleszti |
| DB | **SQLite most → Postgres+pgvector később** | Váltási trigger: több párhuzamos író VAGY >100k source_item VAGY multi-user |
| Queue | **Nincs** (DB-státusz mint queue) → RQ/Redis, ha kell | A stage-szerződés miatt a beemelés később fájdalommentes |
| Vektor | sqlite-vec / numpy fájl → pgvector | Külön vektor-DB (Qdrant stb.) e volumenen indokolatlan üzemeltetés |
| LLM | **Adapter-interfész**; osztályozásra olcsó-gyors modell (Haiku/Flash osztály), outreach-re erősebb (Sonnet/Pro osztály) | Költség: ~200 elem/nap × ~1K token ≈ **filléres napi költség**; vendor-lock elkerülve |
| Orchestráció | Saját vékony adapter, structured output (JSON schema) | LangChain-t kerülni: felesleges absztrakció, gyors API-drift |
| Reddit | PRAW (megvan) | Ingyenes, stabil, ToS-tiszta |
| Graphisoft/Autodesk (Khoros) | **Playwright** headless, mérsékelt ütem (2-4 óránként), respektált robots.txt | RSS letiltva, sima HTTP 403 — verifikált tény; ez a legmagasabb jelsűrűségű forrás, megéri |
| buildingSMART fórum | **Discourse JSON API** (`/latest.json`, `/search.json`) | Nyílt, hivatalos, ingyen — quick win |
| GitHub | Issues API: IfcOpenShell, Bonsai (BlenderBIM), Speckle, xeokit repo-k | Fejlett userek fájdalma első kézből; ingyenes API — **alulértékelt aranybánya** |
| YouTube | Data API, interop-tutorial videók kommentjei | Ingyenes kvóta bőven elég |
| Web-keresés (CSE-pótlás) | `SearchProvider` adapter: **Brave Search API** (olcsó) v. Serper.dev; Exa, ha szemantikus kell | Google CSE halott; adapter mögött cserélhető |
| LinkedIn | **Csak manuális/fél-manuális** (kereső-linkek generálása a review UI-ban) | Scraping = ToS-sértés + GDPR-kockázat; nem építünk rá automatikát |
| CRM-integráció | **Közvetlen `POST /api/bridge/ingest`** a SalesOS-be (localhost, Bearer-kulcs); **n8n csak a publikus élre** marad: wishlist-form és RB2B webhook-fogadó, amíg a SalesOS-nek nincs publikus végpontja | Két saját rendszer közé middleware = plusz hibapont és credential-felület nulla transzformációs értékért; a kontraktus a SalesOS-ben kész és tesztelt |
| Cache | DB-szintű (LLM-hívás hash → eredmény) | Újrafuttatás ingyen, idempotencia |
| Observability | Meglévő log + `runs`/`events` tábla + `/health` (2. fázis) | Elég; APM-platform overkill |

---

## 11. Kockázatok

1. **GDPR / személyes adat** (legsúlyosabb): EU-s szakemberek nevének, szerepének, cégének gyűjtése és pontozása = személyesadat-kezelés. Kötelező: jogos érdek mérlegelés dokumentálása, retenciós szabály, törlési folyamat, és **semmilyen automatikus outreach emberi jóváhagyás nélkül**. A person-feloldás félautomata kapuja nem kényelmi, hanem jogi feature.
2. **Platform-ToS / ban-kockázat:** Khoros-scraping és bármilyen automatizált válaszolgatás. Mitigáció: alacsony frekvencia, csak olvasás automatán, írás mindig kézzel (a draft copy-paste marad).
3. **LLM-hallucináció a cégfeloldásban:** rossz céghez kötött fájdalom → kínos outreach. Mitigáció: konfidencia-küszöb + emberi megerősítés + "confidence explanation" mező kötelező.
4. **Alacsony jelvolumen** (termék-kockázat): lehet, hogy heti 2-3 valódi opportunity van összesen. Ez nem architektúra-hiba — de a várakozásokat ehhez kell állítani, és a forrás-bővítést (nyelvek! német/holland/skandináv BIM-közösségek) előre venni.
5. **Egygépes üzemeltetés:** a Windows-gép ma SPOF. A 3. fázis (service + tunnel) enyhíti; a valódi megoldás a későbbi VPS-költözés — az egyprocesszes design miatt egy délutános munka marad.
6. **Költség-kúszás az enrichment-APIknál** (Clearbit-félék): kerülendő az elején; LLM-kivonatolás + kézi megerősítés ingyen tudja ugyanazt e volumenen.

---

## 12. Skálázhatóság

A skálázás releváns tengelye itt **nem a TPS, hanem: források száma × nyelvek száma × osztályozási mélység.**

- **Ma → 10×:** semmi teendő; az egyprocesszes pipeline óránként simán feldolgoz több ezer elemet.
- **Postgres-váltás triggere:** párhuzamos írók, multi-user review, vagy NODU Sales CRM-be integrálás.
- **Queue-váltás triggere:** ha egy stage (realistán: Playwright-collection vagy LLM-hívás) rendszeresen blokkolja a többit. A stage-szerződés (státusz-alapú, idempotens) miatt bármely stage külön workerbe emelhető átírás nélkül.
- **Horizontális skálázás:** forrás-szintű párhuzamosítás (connector/worker), nem elem-szintű — a volumen sosem fogja az utóbbit indokolni.

---

## 13. Roadmap

| Fázis | Tartalom | Idő (becslés) |
|---|---|---|
| **0. Stabilizálás** | Reddit-kulcs beállítás, Playwright chromium telepítés + Khoros-scraping élesítés, Discourse (buildingSMART) + GitHub Issues connector, CSE-kód törlése | 1 hét |
| **1. Az agy — MVP** | Classifier stage a meglévő `posts`-ra (LLM-adapter + strukturált kimenet), elő-szűrő visszaminősítése, kézi kiértékelés: **2 hét adatán bizonyítani, hogy a jelminőség valós** | 1–2 hét |
| **2. Domain-modell + pontozás** | Új séma (source_items/signals/opportunities), scoring v1, review UI a dashboardon, SalesOS ingest-integráció (közvetlen POST) | 2–3 hét |
| **3. Feloldás + outreach** | Person/company resolver emberi kapuval, outreach-generátor (reply/DM/email), feedback-hurok | 2–3 hét |
| **4. Bővítés** | Többnyelvű források (DE/NL/nordics), szemantikus dedup, scoring-kalibráció az első kimenetekből, VPS-költözés | folyamatos |

Az 1. fázis a **kapudöntés**: ha az LLM-osztályozás a valós adaton nem termel meggyőző jeleket, a további építkezés előtt a forrásstratégián kell igazítani — ezért kerül ez minden más elé.

---

## 14. Migrációs stratégia (strangler-minta)

1. `posts` → `source_items` átnevezés + státuszoszlop; a meglévő connectorok változatlanul írnak bele.
2. Új táblák (`signals`, `opportunities`, …) a régiek MELLÉ, nem helyére.
3. Classifier stage párhuzamosan fut a régi kulcsszó-score-ral → **két hétig dual-run**, összevetés.
4. Dashboard átáll az opportunity-nézetre; a régi lista marad "nyers feed" fülként.
5. Kulcsszó-score megszűnik döntéshozó lenni (elő-szűrővé fokozódik le); Google CSE kód törlődik.
6. `drafts` → `outreach_assets` migráció; a `config.alerts.webhook` (n8n→Pipedrive maradvány) és a `N8N_SETUP.md` Pipedrive-workflow-k kivezetése — a CRM Writer közvetlenül a SalesOS ingest API-t hívja.

Nincs big-bang: a rendszer minden nap működőképes marad, és bármely lépés után meg lehet állni értékelhető állapotban.

---

## 15. Végső ajánlás

**Ne írd újra a Monitort — de ne is "fejleszd tovább": cseréld ki a magját.** A begyűjtő váz (connectorok, ütemező, dedup, jóváhagyási workflow, leválasztott CRM-írás) megtartandó és jó alap — a CRM-cél a SalesOS ingest API, közvetlen hívással. A kulcsszó-központú értékelés, a lapos adatmodell és a link-lista-szemlélet viszont nem evolválható a célterməkké — ezeket egy új domain-modell (opportunity-központú) és egy LLM-alapú osztályozó-pontozó mag váltja le, strangler-mintával, fázisonként leállítható módon.

Ugyanilyen fontos, hogy **mit ne építs meg:** üzenetsort, vektoradatbázis-klasztert, microservice-agentflottát, LinkedIn-scrapert, automata fórum-válaszolót. Ezek e volumen és e csapatméret mellett nem versenyelőnyt, hanem üzemeltetési adósságot és jogi kockázatot termelnek. A versenyelőny három dolog: **niche-forráslefedettség, osztályozási minőség, és a jóváhagyási hurokból épülő saját címkézett adatvagyon.** Minden architekturális döntés ezt a hármat szolgálja.

*— Architektúra-audit vége*
