# NODU Bridge Community Monitor

BIM koordinátorok és architektek online közösségeinek figyelése. Automatikusan észleli az Archicad-Revit adatcsere, IFC konverzió és interoperabilitás témájú bejegyzéseket.

---

## Telepítés

```
pip install -r requirements.txt
```

Python 3.10+ szükséges.

---

## Beállítás (config.yaml)

### 1. Reddit API (kötelező az r/Revit és r/ArchiCAD figyeléséhez)

1. Nyisd meg: https://www.reddit.com/prefs/apps
2. Kattints "create another app" gombra
3. Típus: **script**
4. Redirect URI: `http://localhost:8080`
5. A létrehozás után megkapod:
   - `client_id`: az app neve alatti rövid kód
   - `client_secret`: a "secret" mező

```yaml
reddit:
  client_id: "AbCdEfGhIj1234"
  client_secret: "xYzAbCdEfGhIjKlMnOpQrStUv"
  user_agent: "NODU-Bridge-Monitor/0.1 by sajat_felhasznalonev"
```

### 2. Playwright (kötelező a Graphisoft/Autodesk fórumok figyeléséhez)

```
pip install playwright
playwright install chromium
```

A Khoros-alapú fórumok (Graphisoft Community, Autodesk Community) JavaScript
SPA-k — sima HTTP-vel 403-at adnak, csak headless böngészővel olvashatók.
Nincs API kulcs, csak a fenti telepítés. Beállítás: `config.yaml` ->
`playwright.forums`.

### 3. Email riasztás (opcionális)

Gmail esetén "App password" szükséges (nem a Google fiók jelszava):
1. Google fiók -> Biztonság -> 2 lépéses azonosítás -> Alkalmazásjelszavak
2. Hozz létre egy "NODU Monitor" nevű alkalmazásjelszót

```yaml
alerts:
  email:
    enabled: true
    from_address: "sajat@gmail.com"
    to_address: "poczai@nodu.build"
    app_password: "abcd efgh ijkl mnop"
```

### 4. Slack riasztás (opcionális)

1. Slack -> Apps -> Incoming Webhooks -> Add New Webhook
2. Válaszd ki a csatornát
3. Másold a webhook URL-t:

```yaml
alerts:
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/T.../B.../..."
```

---

## Futtatás

```bash
# Egyszeri futás (minden connector)
python main.py

# Csak Reddit
python main.py --reddit

# Csak a JS-alapú fórumok (Graphisoft, Autodesk — Playwright)
python main.py --playwright

# Fórum HTML scraping (phpBB, RevitForum)
python main.py --forums

# Napi összefoglaló megjelenítése és riasztás küldése
python main.py --digest

# Ütemezett futás (folyamatosan, háttérben)
python main.py --schedule
```

---

## Adatbázis lekérdezése

Az eredmények a `nodu_monitor.db` SQLite fájlban tárolódnak.

```bash
# Összes új találat
python -c "
from storage.db import get_new_posts
import sqlite3, sys
sys.path.insert(0, '.')
posts = get_new_posts('nodu_monitor.db')
for p in posts:
    print(f\"[{p['platform']}] {p['title'][:60]}\")
    print(f\"  Score: {p['score']} | Keywords: {p['keywords']}\")
    print(f\"  {p['url']}\")
    print()
"
```

Vagy bármely SQLite klienssel (pl. DB Browser for SQLite).

---

## Platform státusz

| Platform | Connector | Állapot |
|---|---|---|
| r/Revit (Reddit) | PRAW API | Müködik, API kulcs szükséges |
| r/ArchiCAD (Reddit) | PRAW API | Müködik, API kulcs szükséges |
| r/BIM (Reddit) | PRAW API | Müködik, API kulcs szükséges |
| Graphisoft Community | Playwright (headless Chromium) | Müködik, `pip install playwright && playwright install chromium` |
| Autodesk Community | Playwright (headless Chromium) | Müködik |
| RevitForum.org | HTML scraping | Müködik |
| Discord | Bot API | Nem implementált (bot invite szükséges) |
| LinkedIn | Manuális | Scraping tiltott |

---

## Fórumok és scraping korlátai

A Graphisoft Community és Autodesk Community Khoros alapú SPA-k (JavaScript renderelt oldalak). Közvetlen HTML scraping nem müködik (403), ezért a `playwright_connector.py` headless Chromiummal rendereli az oldalt és onnan olvassa ki a posztokat — valós idejü, API-kulcs nélkül. Fórumonként eltérő, gyakran nem dokumentált a DOM-szerkezet (pl. a keresési találatok nézete class-onként eltér a normál poszt-nézettől), ezért új fórum hozzáadásakor számíts rá, hogy a szelektorokat (`message_selector`/`title_selector`/`body_selector`/`author_selector` a configban) fel kell térképezni.

> A Google Custom Search API-ra épülő korábbi megoldás (search_connector.py) 2026-07-20-án kikerült: a Google 2026-ban lezárta ezt az API-t új ügyfelek elől. Részletek: `docs/01-architektura-audit-2026-07.md`.
