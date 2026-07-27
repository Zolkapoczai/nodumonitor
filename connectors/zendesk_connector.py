"""
Zendesk Help Center connector — Graphisoft support (support.graphisoft.com).

FIGYELEM, MIELOTT EZT LEADFORRASNAK NEZED: ez NEM az. A cikkeket a Graphisoft
SAJAT supportja irja (`author_id` = staff, `comments_disabled: true`), tehat
nincs kit megszolitani — nincs szerzo, akinek valaszolhatnank, es nincs vasarloi
szandek. Ezert a `graphisoft-support` platform rajta van a
`responder.exclude_platforms` listan: valasz NEM keszul ra. Amit ad, az PIACI
INTELLIGENCIA: azt dokumentalja, MELYIK interop-problema fordul elo elegszer
ahhoz, hogy a Graphisoft KB-cikket irjon rola. Ld. HANDOFF §7/M.

MOTOR (elesben merve 2026-07-26): Zendesk Help Center.
  - `/api/v2/help_center/{locale}/articles.json` — nyilt, hitelesites nelkul,
    100 cikk/lap. A teljes tudasbazis 960 cikk = 10 lap.
  - `/api/v2/help_center/{locale}/sections.json` — szekciok (kategoriak).
  - A community HALOTT: 5 poszt, mind 2020-12-03, es azok a Zendesk GYARI
    demo-bejegyzesei ("What is the community?") — sosem torolte senki. Ezert
    a community-vegpontot meg sem hivjuk.
  - robots.txt: az API-ra csak a `*/stats/view` vegpontok tiltottak, azokat nem
    hasznaljuk. A `/hc/*/search` tiltott — keresest nem is hasznalunk.
  - Rate limit: 8 gyors keres mind 200 (0,3-0,4 s). 1 s szunet boven eleg.

KET DONTES, AMI MERESBOL JOTT (ne "javitsd" vissza):

1. `updated_at`-et irunk a poszt `created_at` mezojebe, NEM a cikk
   `created_at`-jet. Egy KB-cikknel az szamit, mikor frissitettek utoljara,
   nem hogy mikor irtak. A kulonbseg drasztikus: a 234 kulcsszo-talalatbol
   `created_at` szerint csak 45 esik 1 even belulre (az `insert_post` a tobbit
   eldobja) — es pont a JOK esnek ki: "Unable to import a Revit file into
   Archicad" (score 25, 2024-es cikk, de 2026-07-07-en frissitve), "IFC import,
   how to translate Revit stories for ArchiCAD" (23), "IFC export warning..."
   (26). `updated_at` szerint mind a 234 bejon.

2. Alapbol csak KET szekciobol gyujtunk: "Collaboration with Other Software" es
   "Project Data & BIM". A teljes KB 234 kulcsszo-talalatabol a maradek ~200
   licencelesi, BIMcloud-, BIMx- es renderelesi zaj ("BIMx error code 1111",
   "billboard trees when rendering"), ami csak a classifier-kvotat egetne. A
   ket cel-szekcioban van az OSSZES magas score-u interop-cikk.
   A szekciokat NEV szerint konfiguraljuk es futasidoben oldjuk fel id-re: a
   sitenak tobb azonos nevu szekcioja is van (5 db "General"), ezert a nev->id
   feloldas tobb id-t is adhat, es ez igy helyes.
"""
import html
import re
import time
from datetime import datetime, timezone

import requests

from filters.keyword_filter import KeywordFilter
from storage.db import insert_post, log_run

_DELAY_S = 1.0
_PER_PAGE = 100
_MAX_PAGES = 30  # biztonsagi fek egy vegtelen lapozas ellen

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_DEFAULT_SECTIONS = ["Collaboration with Other Software", "Project Data & BIM"]


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _strip_html(raw: str, limit: int = 2000) -> str:
    """A Zendesk `body` teljes HTML-cikk. Csonkitas MEG a kulcsszo-szuro elott
    (a `keyword_filter` erzekeny a hosszu szovegre — HANDOFF §4/10)."""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()[:limit]


class ZendeskConnector:
    def __init__(self, config: dict, db_path: str):
        self.config = config
        self.db_path = db_path
        self.zd_config = config.get("zendesk", {})
        self.kf = KeywordFilter(config)
        self._failed_requests: list[str] = []

    def _get_json(self, url: str, params: dict = None):
        try:
            resp = requests.get(
                url, params=params,
                headers={"User-Agent": "NODU-Bridge-Monitor/0.1"},
                timeout=25,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            # Gyujtjuk, hogy a runs.error-ban latszodjon — enelkul egy vegig
            # hibas kor "0 elem"-nek, azaz eltort connectornak tunne.
            self._failed_requests.append(f"{url.rsplit('/', 1)[-1]}: {e}")
            print(f"[zendesk] API hiba ({url}): {e}")
            return None
        finally:
            time.sleep(_DELAY_S)

    def _paged(self, url: str, kulcs: str) -> list[dict]:
        """Zendesk-lapozas: a valasz `next_page`-e null, ha nincs tobb lap."""
        out: list[dict] = []
        for page in range(1, _MAX_PAGES + 1):
            data = self._get_json(url, {"per_page": _PER_PAGE, "page": page})
            if not data:
                break
            out.extend(data.get(kulcs, []))
            if not data.get("next_page"):
                break
        return out

    def _section_ids(self, base_url: str, locale: str, nevek: list[str]) -> set:
        """Szekcio-nevek -> id-k. Tobb szekcionak lehet AZONOS neve (5 db
        'General'), ezert halmazt adunk vissza, nem egyetlen id-t."""
        if not nevek:
            return set()
        sections = self._paged(f"{base_url}/api/v2/help_center/{locale}/sections.json", "sections")
        keresett = {n.strip().lower() for n in nevek}
        ids = {s["id"] for s in sections if (s.get("name") or "").strip().lower() in keresett}
        talalt = {(s.get("name") or "") for s in sections if s["id"] in ids}
        hianyzo = keresett - {n.lower() for n in talalt}
        if hianyzo:
            # Nem hiba, de tudni kell rola: elirt vagy atnevezett szekcio
            # csendben 0 cikket adna.
            print(f"[zendesk] FIGYELEM: nincs ilyen szekcio: {', '.join(sorted(hianyzo))}")
        return ids

    def _rows(self, articles: list[dict], section_ids: set) -> list[dict]:
        results = []
        for a in articles:
            if section_ids and a.get("section_id") not in section_ids:
                continue
            url = a.get("html_url") or a.get("url") or ""
            if not url:
                continue
            results.append({
                "url": url,
                "title": a.get("title", "") or "",
                "body": _strip_html(a.get("body") or ""),
                # A cikkeket a support irja, nincs megszolithato szerzo.
                "author": "Graphisoft Support",
                "external_id": f"article_{a.get('id')}",
                # SZANDEKOS: updated_at, nem created_at — ld. a modul-docstringet.
                "created_at": a.get("updated_at") or a.get("created_at") or _now(),
            })
        return results

    def _save(self, site_name: str, items: list[dict],
              search_term: str = None, require_keywords: bool = True) -> int:
        saved = 0
        for item in items:
            combined = f"{item['title']} {item['body']}"
            keywords, score = self.kf.match(combined)
            if require_keywords and not keywords:
                continue

            post = {
                "source": "zendesk",
                "platform": site_name,
                "external_id": item["external_id"],
                "url": item["url"],
                "author": item["author"],
                "title": item["title"],
                "body": item["body"],
                "created_at": item["created_at"],
                "fetched_at": _now(),
                "keywords": ", ".join(keywords),
                "score": score,
                "search_term": search_term,
            }
            if insert_post(self.db_path, post):
                saved += 1
        return saved

    def run(self) -> int:
        sites = self.zd_config.get("sites", {})
        total = 0
        total_seen = 0
        started = _now()
        error_msg = None

        try:
            for site_name, site_cfg in sites.items():
                base_url = site_cfg.get("base_url", "").rstrip("/")
                if not base_url:
                    continue
                locale = site_cfg.get("locale", "en-us")
                sections = site_cfg.get("sections", _DEFAULT_SECTIONS)

                section_ids = self._section_ids(base_url, locale, sections)
                if sections and not section_ids:
                    print(f"[zendesk] {site_name}: egyetlen konfiguralt szekcio sem talalhato, kihagy")
                    continue

                articles = self._paged(
                    f"{base_url}/api/v2/help_center/{locale}/articles.json", "articles")
                rows = self._rows(articles, section_ids)
                total_seen += len(rows)
                total += self._save(site_name, rows)
                print(f"[zendesk] {site_name}: {len(articles)} cikk letoltve, "
                      f"{len(rows)} a cel-szekciokban, {total} uj bejegyzes")
        except Exception as e:
            error_msg = str(e)
            print(f"[zendesk] HIBA: {e}")

        if error_msg is None and self._failed_requests:
            error_msg = (f"{len(self._failed_requests)} keres hibara futott "
                         f"(elso: {self._failed_requests[0][:150]})")

        log_run(
            self.db_path,
            connector="zendesk",
            started_at=started,
            finished_at=_now(),
            new_posts=total,
            error=error_msg,
            items_seen=total_seen,
        )
        return total
