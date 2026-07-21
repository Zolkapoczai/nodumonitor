# ⚠️ ELAVULT (2026-07-20) — n8n Workflow — NODU Monitor → Pipedrive integráció

> **A Pipedrive kikerült a láncból** (SalesOS "tiszta lap" döntés). A CRM-cél a NODU SalesOS
> `POST /api/bridge/ingest` végpontja, **közvetlen hívással** (n8n nélkül) — kontraktus:
> `C:\NODU\SalesOS\docs\08-bridge-integracio.md`. Az n8n szerepe a publikus élre szűkül
> (wishlist-form, RB2B webhook-fogadó). Részletek: `docs/01-architektura-audit-2026-07.md` §6/§10.
> Az alábbi tartalom történeti referenciaként marad meg.

## Áttekintés

Három fő lead-forrás csatornázódik n8n-en keresztül Pipedrive-ba:

| Forrás | Mikor aktív | Mit azonosít |
|--------|------------|--------------|
| **nodu-monitor scraper** | Most | Fórumokon/Redditen kérdező BIM szakemberek |
| **Wishlist** (nodu.build/bridge) | Amint az aloldal él | Önként feliratkozó, minősített érdeklődők |
| **RB2B** (rb2b.com) | Ingyenes most (Slack), Pro 2026 szept. | Anonim weboldal-látogatók |

---

## 1. n8n telepítés

### Cloud (ajánlott induláshoz)
1. Regisztráció: https://n8n.io → Start Free
2. Workspace létrehozása
3. Webhook URL másolása (lásd lent)

### Self-hosted (Docker)
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```
Elérhető: http://localhost:5678

---

## 2. Pipedrive API token megszerzése

1. Pipedrive → Settings → Personal preferences → API
2. API token másolása
3. n8n-ben: Credentials → Add → Pipedrive API → token beillesztése

---

## 3. n8n Workflow importálása

A `nodu-monitor-n8n-workflow.json` fájlt importáld be:
n8n → Workflows → Import from file

A workflow az alábbi lépésekből áll:

```
[Webhook] → [Score Filter] → [Pipedrive: Search Person]
                                      ↓ (not found)
                             [Pipedrive: Create Person]
                                      ↓
                             [Pipedrive: Create Deal]
                                      ↓
                             [Pipedrive: Add Note]
                                      ↓
                             [Slack: Notify #sales-leads]
```

---

## 4. Webhook URL beállítása

1. n8n-ben aktiváld a workflow-t → Webhook node → Production URL másolása
2. `config.yaml`-ban:
   ```yaml
   alerts:
     webhook:
       enabled: true
       url: "https://your-n8n-instance.app.n8n.cloud/webhook/nodu-monitor"
       min_score: 5
   ```

---

## 5. Pipedrive pipeline stages

Kézzel hozd létre a Pipedrive-ban (Settings → Pipelines):

| Stage neve        | Leírás                                          |
|-------------------|-------------------------------------------------|
| Inbound           | Scraper-leadek (score >= 5), automatikusan      |
| Waitlist          | Wishlist feliratkozó (nodu.build/bridge)        |
| Website Visitor   | RB2B weboldal-látogató (hidegebb lead)          |
| Contacted         | Ment ki komment / LinkedIn üzenet               |
| Responded         | Válaszolt a lead                                |
| Demo / Onboarding | Egyeztetett bemutató, bevezetés indítása        |
| Aktív felhasználó | Rendszeresen használja a Bridge-et              |

A pipeline neve legyen: **NODU Bridge Inbound**. Három belépő stage tölthető automatikusan
(Inbound, Waitlist, Website Visitor); a Waitlist a legmelegebb, mert a feliratkozó önként
adta meg az adatait.

---

## 6. Webhook payload formátuma

A Python scraper ezt küldi n8n-nek:

```json
{
  "source": "nodu-monitor",
  "generated_at": "2026-06-29T10:00:00+00:00",
  "leads": [
    {
      "platform": "reddit",
      "source": "reddit",
      "title": "Post title here",
      "author": "username",
      "url": "https://reddit.com/r/Revit/...",
      "score": 7,
      "keywords": "archicad revit, ifc conversion",
      "body_excerpt": "First 500 chars of post body...",
      "created_at": "2026-06-29T09:00:00+00:00"
    }
  ]
}
```

Az n8n workflow a `leads` tömböt iterálja (`Split In Batches` vagy `Loop Over Items` node).

---

## 7. n8n Workflow JSON (importálható)

Mentsd el `nodu-monitor-n8n-workflow.json` névvel és importáld n8n-be:

```json
{
  "name": "NODU Monitor → Pipedrive",
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "nodu-monitor",
        "httpMethod": "POST",
        "responseMode": "onReceived"
      }
    },
    {
      "name": "Loop Over Leads",
      "type": "n8n-nodes-base.splitInBatches",
      "parameters": { "batchSize": 1 }
    },
    {
      "name": "Score Filter",
      "type": "n8n-nodes-base.filter",
      "parameters": {
        "conditions": {
          "number": [{ "value1": "={{ $json.score }}", "operation": "largerEqual", "value2": 5 }]
        }
      }
    },
    {
      "name": "Pipedrive - Create Person",
      "type": "n8n-nodes-base.pipedrive",
      "parameters": {
        "resource": "person",
        "operation": "create",
        "name": "={{ $json.author }}",
        "additionalFields": {
          "label": "={{ $json.platform }}"
        }
      }
    },
    {
      "name": "Pipedrive - Create Deal",
      "type": "n8n-nodes-base.pipedrive",
      "parameters": {
        "resource": "deal",
        "operation": "create",
        "title": "={{ '[' + $json.platform.toUpperCase() + '] ' + $json.title.slice(0, 80) }}",
        "additionalFields": {
          "stage_id": 1,
          "person_id": "={{ $('Pipedrive - Create Person').item.json.id }}"
        }
      }
    },
    {
      "name": "Pipedrive - Add Note",
      "type": "n8n-nodes-base.pipedrive",
      "parameters": {
        "resource": "note",
        "operation": "create",
        "content": "={{ 'Forrás: ' + $json.platform + '\\nURL: ' + $json.url + '\\nScore: ' + $json.score + '\\nKulcsszavak: ' + $json.keywords + '\\n\\n' + $json.body_excerpt }}",
        "additionalFields": {
          "deal_id": "={{ $('Pipedrive - Create Deal').item.json.id }}"
        }
      }
    },
    {
      "name": "Slack Notify",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "#sales-leads",
        "text": "={{ ':mag: Új NODU lead | ' + $json.platform + ' | Score: ' + $json.score + '\\n' + $json.title + '\\n' + $json.url }}"
      }
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "Loop Over Leads" }]] },
    "Loop Over Leads": { "main": [[{ "node": "Score Filter" }]] },
    "Score Filter": { "main": [[{ "node": "Pipedrive - Create Person" }]] },
    "Pipedrive - Create Person": { "main": [[{ "node": "Pipedrive - Create Deal" }]] },
    "Pipedrive - Create Deal": { "main": [[{ "node": "Pipedrive - Add Note" }]] },
    "Pipedrive - Add Note": { "main": [[{ "node": "Slack Notify" }]] }
  }
}
```

---

## 8. Wishlist → Pipedrive workflow (a weboldalról)

A `nodu.build/bridge` waitlist-űrlap (referencia: `OUTPUTS/index/bridge-waitlist.html`)
közvetlenül erre a webhookra POST-ol, a Python scraper megkerülésével. Külön workflow,
"Wishlist → Pipedrive" névvel.

**Webhook payload (a form ezt küldi):**
```json
{
  "source": "wishlist",
  "email": "kovacs.marton@iroda.hu",
  "name": "Kovács Márton",
  "role": "BIM Coordinator",
  "pain_point": "IFC-exportnál eltűnnek a paraméterek.",
  "consent": true,
  "utm_source": "reddit",
  "utm_medium": "forum_comment",
  "utm_campaign": "bridge_waitlist",
  "page_url": "https://nodu.build/bridge?utm_source=reddit",
  "submitted_at": "2026-06-30T10:00:00Z"
}
```

**Workflow lépések:**
```
[Webhook: bridge-waitlist] → [Consent Filter (consent === true)]
        → [Double opt-in: megerősítő email küldése]   ← csak megerősítés után tovább
        → [Pipedrive: Search Person]
                ↓ (not found)
        → [Pipedrive: Create Person]   (label: source=waitlist)
        → [Pipedrive: Create Deal]     (stage: Waitlist)
        → [Pipedrive: Add Note]        (szerepkör, fájdalompont, UTM-forrás)
        → [Slack: Notify #sales-leads]
```

**Double opt-in (GDPR):** EU-s érintettek miatt kötelező. A megerősítő emailt az n8n küldi
(pl. egy egyedi token-linkkel egy "confirm" webhookra); a feliratkozó csak a megerősítés
után kerül a "Waitlist" stage-be. A `bridge-waitlist.html` köszönő szövege már ezt jelzi.

**Importálható JSON:**
```json
{
  "name": "Wishlist → Pipedrive",
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": { "path": "bridge-waitlist", "httpMethod": "POST", "responseMode": "onReceived" }
    },
    {
      "name": "Consent Filter",
      "type": "n8n-nodes-base.filter",
      "parameters": {
        "conditions": { "boolean": [{ "value1": "={{ $json.consent }}", "value2": true }] }
      }
    },
    {
      "name": "Pipedrive - Create Person",
      "type": "n8n-nodes-base.pipedrive",
      "parameters": {
        "resource": "person",
        "operation": "create",
        "name": "={{ $json.name || $json.email }}",
        "additionalFields": { "email": "={{ $json.email }}", "label": "waitlist" }
      }
    },
    {
      "name": "Pipedrive - Create Deal",
      "type": "n8n-nodes-base.pipedrive",
      "parameters": {
        "resource": "deal",
        "operation": "create",
        "title": "={{ '[WAITLIST] ' + ($json.name || $json.email) }}",
        "additionalFields": {
          "stage_id": 2,
          "person_id": "={{ $('Pipedrive - Create Person').item.json.id }}"
        }
      }
    },
    {
      "name": "Pipedrive - Add Note",
      "type": "n8n-nodes-base.pipedrive",
      "parameters": {
        "resource": "note",
        "operation": "create",
        "content": "={{ 'Szerepkor: ' + $json.role + '\\nFajdalompont: ' + $json.pain_point + '\\nForras: ' + $json.utm_source + ' / ' + $json.utm_medium + '\\nOldal: ' + $json.page_url }}",
        "additionalFields": { "deal_id": "={{ $('Pipedrive - Create Deal').item.json.id }}" }
      }
    },
    {
      "name": "Slack Notify",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "#sales-leads",
        "text": "={{ ':sparkles: Uj wishlist feliratkozo | ' + ($json.name || $json.email) + ' | ' + $json.role + '\\nFajdalompont: ' + $json.pain_point }}"
      }
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "Consent Filter" }]] },
    "Consent Filter": { "main": [[{ "node": "Pipedrive - Create Person" }]] },
    "Pipedrive - Create Person": { "main": [[{ "node": "Pipedrive - Create Deal" }]] },
    "Pipedrive - Create Deal": { "main": [[{ "node": "Pipedrive - Add Note" }]] },
    "Pipedrive - Add Note": { "main": [[{ "node": "Slack Notify" }]] }
  }
}
```

A `stage_id: 2` a "Waitlist" stage azonosítója; cseréld a Pipedrive-ban létrejött tényleges
azonosítóra. A workflow aktiválása után a Production webhook URL-t illeszd a
`bridge-waitlist.html` `WEBHOOK_URL` konstansába.

---

## 9. LinkedIn Apify integráció (7. fázis)

A LinkedIn profilkereséshez külön n8n workflow szükséges:

**Trigger**: Cron (naponta egyszer, reggel 7:00)
**Lépések**:
1. HTTP Request node → Apify API (LinkedIn Profile Scraper actor)
   - URL: `https://api.apify.com/v2/acts/curious_coder~linkedin-profile-scraper/runs`
   - Body: `{"searchQuery": "BIM Coordinator Archicad Revit", "maxItems": 50}`
2. Loop Over Items → Score/filter
3. Pipedrive Create Person (LinkedIn source)
4. Gemini API (HTTP Request) → LinkedIn DM draft generálás
5. Slack message + Approve/Reject gomb (n8n `Wait for Webhook`)

Apify regisztráció: https://apify.com → free tier 5$/hó kredit

---

## 10. RB2B weboldal-látogató azonosítás

**Mi az RB2B?**
Az RB2B (rb2b.com) egy JavaScript snippet-alapú SaaS, amely a weboldal anonim látogatóit
azonosítja IP-egyeztetéssel.

**Ingyenes csomag (már most bekötheto):**
- A snippet beilleszthető a `nodu.build/bridge` oldal `<head>` részébe, amint az aloldal él.
- Korlátok: csak USA-beli látogató, a forgalom kb. 15-20 százaléka, 2026 januárja óta csak
  cégszintű (nem személyszintű) azonosítás, és **kizárólag Slack** értesítés.
- **Nincs webhook, nincs n8n, nincs automatikus Pipedrive** az ingyenes csomagban. Ez most
  "bemelegítő": a látogató cégek a Slackben láthatók, manuális utánkövetéssel.

**Pro csomag (2026 szeptember, az éles weboldali forgalom mellé):**
- Személyszintű LinkedIn-azonosítás és webhook. Ekkor él az alábbi automatikus workflow.

**Mit küld RB2B (webhook payload-minta):**
```json
{
  "first_name": "Márton",
  "last_name": "Kovács",
  "linkedin_url": "https://linkedin.com/in/marton-kovacs",
  "company": "Bánáti + Hartvig Építész Iroda",
  "title": "BIM Coordinator",
  "page_url": "https://nodubridge.com/pricing",
  "timestamp": "2026-09-15T14:32:00Z"
}
```

**n8n workflow (külön, "RB2B → Pipedrive" névvel):**

```
[Webhook: RB2B] → [ICP Filter] → [Pipedrive: Search Person]
                                         ↓ (not found)
                                  [Pipedrive: Create Person]
                                         ↓
                                  [Pipedrive: Create Deal]  ← stage: "Website Visitor"
                                         ↓
                                  [Gemini API: LinkedIn DM draft]
                                         ↓
                                  [Slack: Approve/Reject gomb]
```

**ICP Filter feltételek** (n8n IF node):
- `title` tartalmaz: "BIM", "Coordinator", "Manager", "Architect", "Designer"
- VAGY `page_url` tartalmaz: "pricing", "features", "archicad", "revit"

**Pipedrive stage**: "Website Visitor" (az Inbound stage előtt — hidegebb lead)

**Gemini API LinkedIn DM draft** (HTTP Request node):
```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_GEMINI_API_KEY
Body:
{
  "system_instruction": {
    "parts": [{ "text": "Te a NODU Bridge BIM-eszköz alapítójának nevében írsz LinkedIn üzenetet. Rövid, személyes, nem marketingszöveg. Max 3 mondat." }]
  },
  "contents": [{
    "parts": [{ "text": "Látom, hogy {{ $json.first_name }} {{ $json.last_name }} ({{ $json.title }}, {{ $json.company }}) meglátogatta a NODU Bridge weboldalát. Írj egy személyes LinkedIn kapcsolatfelvétel üzenetet." }]
  }],
  "generationConfig": { "maxOutputTokens": 200 }
}
```

**Beállítás lépései:**
1. rb2b.com → Sign up → Pro plan
2. Settings → Webhook → URL: `https://your-n8n.com/webhook/rb2b`
3. JavaScript snippet beillesztése a NODU Bridge website `<head>` részébe
4. n8n-ben aktiválni a "RB2B → Pipedrive" workflow-t

---

## 11. Heti digest workflow

**Két lehetőség:**

**A) Python scraper (beépítve):** a `main.py --weekly-report` a `get_weekly_stats()` alapján
Slack-összefoglalót küld (forrásonkénti poszt-szám, top fájdalompontok, jóváhagyásra váró
draftok). Ütemezett módban (`--schedule`) hétfőnként automatikusan fut, lásd
`config.yaml` → `weekly_report`. Ehhez csak a Slack webhook kell, n8n nem szükséges.

**B) n8n cron:** ha a riportot n8n-ben szeretnéd, Cron node (hétfő 08:00) →
Pipedrive Deals report → Slack `#sales-leads`.
