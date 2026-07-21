"""
Félautomata válasz-javaslat generátor.

Müködés:
1. Lekéri az adatbázisból az 'alerted' státuszú releváns bejegyzéseket
2. Gemini API-val valasz-javaslatot generál mindegyikre
3. A javaslatokat 'drafts' táblába menti 'pending' státusszal
4. A review_drafts() CLI loop segítségével az operator megnézheti,
   elfogadhatja vagy elutasíthatja az egyes javaslatokat

Az elfogadott szöveg másolható és kézzel postolható a megfelelő fórumon.
"""
import json
from google import genai
from google.genai import types
from datetime import datetime, timezone
from storage.db import (
    save_draft, get_pending_drafts, mark_draft, mark_alerted,
    get_post_with_signal, get_pain_posts_without_draft,
    get_recent_pain_signals,
)


_SYSTEM_PROMPT = """
Te a NODU Bridge BIM szoftver közösségi menedzsere vagy.
A NODU Bridge egyetlen értékajánlata: parametrikus adatcsere Archicad és Revit között -
az elemek logikáját (nem statikus geometriát) konvertálja, nyitott IFC helyett
natív mapping scriptekkel.

Feladatod: releváns fórumbejegyzésekre valasz-javaslatot írni.

Szabályok:
- A válasz ELSŐSORBAN valódi segítség legyen a feltett problémára
- MAX 70-80 SZÓ, EGY bekezdésben. NINCS szamozott vagy pontozott lista,
  NINCS tobblepeses "1. 2. 3." forma — ez egy rovid, tomor hozzaszolas,
  nem egy mini-cikk
- Ha a megoldas termeszete szerint tobb lepest igenyelne, NE irde le mind:
  csak jelezd, hogy van ra mod ("van egy egyszeru workaround erre, szolj
  ha erdekel a reszlet") — a celzas is segitseg, nem kell mindent kifejteni
- A NODU Bridge-et csak akkor emlitsd, ha ténylegesen megoldja a leirt problémát
- Ha emlited, EGY mondat, nem reklámnyelv - inkabb "van egy eszköz amit használunk" hangnem
- A 70-80 szavas limit a PROZAI szovegre vonatkozik — ha a feladat linket
  is kér, azt a mondat vegen, valtoztatas nelkul, TELJES formaban illeszd
  be (ne rovidisd, ne vagd le)
- Angol nyelv (kivéve ha a bejegyzes más nyelvu)
- Nincs emoji, nincs marketingzsargon
- Ha a problema nem illik a NODU Bridge profiljahoz, írj hasznos valaszt a termék megemlitese nelkul
- Soha ne hazudj, ne tulígerd a terméket
""".strip()

_USER_TEMPLATE = """
Platform: {platform} | Forrás: {source}
Szerzo: {author}
Cim: {title}
Szoveg: {body}
Kulcsszavak (miert kerult figyelobe): {keywords}
{pain_block}
Írj egy valasz-javaslatot erre a bejegyzesre.

FONTOS ISMETLES: max 70-80 SZO, EGY bekezdesben, NINCS szamozott/pontozott
lista es NINCS ket kulon bekezdes (pl. "technikai resz" + "Bridge-pitch"
kulon) — mindent egyetlen tomor bekezdesbe surits.
""".strip()


def _pain_context(post: dict) -> str:
    """
    A Pain Classifier detektalt fajdalom-kontextusa (ha a poszt mar
    osztalyozva van, get_post_with_signal 'sig_' mezoi). Ezt kapja a modell,
    hogy a valasz a VALODI problemara reflektaljon, ne a nyers kulcsszora.
    Ures string, ha nincs signal (visszafele kompatibilis a regi hivasokkal).
    """
    summary = post.get("sig_pain_summary")
    if not summary:
        return ""
    parts = ["", "Detektalt fajdalom (a rendszer AI-osztalyozasabol):",
             f"- Problema: {summary}"]
    if post.get("sig_tech_summary"):
        parts.append(f"- Technikai kontextus: {post['sig_tech_summary']}")
    if post.get("sig_issue_types"):
        parts.append(f"- Problema-tipus: {post['sig_issue_types']}")
    if post.get("sig_role_hypothesis"):
        parts.append(f"- Szerzo feltetelezett szerepe: {post['sig_role_hypothesis']}")
    parts.append("A valasz KONKRETAN erre a fajdalomra reflektaljon, ne altalanossagban.")
    return "\n".join(parts) + "\n"


def _wishlist_link(config: dict, source: str, medium: str) -> str:
    """UTM-cimkezett wishlist hivatkozas a configbol. Ures string, ha nincs url."""
    wl = config.get("wishlist", {})
    url = wl.get("url", "")
    if not url:
        return ""
    campaign = wl.get("utm_campaign", "bridge_waitlist")
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}"


def _append_cta(draft_text: str, config: dict, source: str) -> str:
    """
    A korai-hozzaferesi linket a KOD fuzi a valaszhoz (nem a modell) — csak
    akkor, ha a cta be van kapcsolva ES a modell tenylegesen emlitette a
    NODU Bridge-et (ez a relevancia-jelzes). Igy a link sosem csonkul es a
    prozai szolimit szorosan tarthato (2026-07-21 architektura-valtas).
    """
    wl = config.get("wishlist", {})
    if not (wl.get("cta_in_drafts") and wl.get("url")):
        return draft_text
    if "bridge" not in (draft_text or "").lower():
        return draft_text
    link = _wishlist_link(config, source, "forum_comment")
    if not link or link in draft_text:
        return draft_text
    return f"{draft_text}\n\nKorai hozzaferes: {link}"


def _build_system_prompt(config: dict) -> str:
    """Az alap system prompt + opcionalis wishlist CTA szabaly (configbol)."""
    base = _SYSTEM_PROMPT
    wl = config.get("wishlist", {})
    if wl.get("cta_in_drafts") and wl.get("url"):
        base += (
            "\n\nHa a valasz valoban segit ES a NODU Bridge tenylegesen releváns a leirt "
            "problemara, emlitsd meg EGY rovid mondatban a NODU Bridge-et mint eszkozt. "
            "NE irj be URL-t vagy linket — a korai-hozzaferesi hivatkozas automatikusan "
            "hozzaadodik, ha a Bridge-et emlited. Ha a problema nem illik a termekhez, "
            "egyaltalan ne emlitsd. Soha ne legyen tolakodo."
        )
    return base


def generate_draft_for_post(config: dict, db_path: str, post_id: int):
    """
    Egyetlen posztra general valasztervezetet (a dashboard 'Valasztervezet' gombja).
    Visszaadja a draft_id-t, vagy None ha nem sikerult.
    """
    sc = config.get("scoring", {})
    api_key = sc.get("gemini_api_key", "")
    if not sc.get("gemini_enabled", False) or not api_key or api_key == "YOUR_GEMINI_API_KEY":
        print("[responder] Gemini API nincs beallitva. Kihagy.")
        return None

    post = get_post_with_signal(db_path, post_id)
    if not post:
        print(f"[responder] Nincs ilyen poszt: {post_id}")
        return None

    model = sc.get("gemini_model", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    system_prompt = _build_system_prompt(config)

    user_msg = _USER_TEMPLATE.format(
        platform=post.get("platform", ""),
        source=post.get("source", ""),
        author=post.get("author", ""),
        title=post.get("title", ""),
        body=(post.get("body", "") or "")[:800],
        keywords=post.get("keywords", ""),
        pain_block=_pain_context(post),
    )

    try:
        resp = client.models.generate_content(
            model=model,
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                # 200 token: eleg egy teljes 70-90 szavas valaszhoz akar
                # magyarul is (tobb token/szo), de meg mindig rovidsegre
                # kenyszerit. A linket NEM a modell irja, hanem a kod fuzi
                # hozza (_append_cta) — igy a link sosem csonkul, es a szoros
                # prozai limit tarthato (2026-07-21 architektura-valtas).
                max_output_tokens=200,
                # thinking_budget=0: a gemini-2.5-flash kulonben a keret nagy
                # reszet "gondolkodasra" kolti, es a valasz csonka lesz
                # (2026-07-20-i eles hiba). A classifier ugyanezt igenyelte.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        draft_text = (resp.text or "").strip()
    except Exception as e:
        print(f"[responder] HIBA ({post_id}): {e}")
        return None

    draft_text = _append_cta(draft_text, config, post.get("platform") or "nodu")
    draft_id = save_draft(db_path, post["id"], draft_text)
    mark_alerted(db_path, [post["id"]])
    return draft_id


def generate_drafts(config: dict, db_path: str, batch_size: int = 10) -> int:
    sc = config.get("scoring", {})
    if not sc.get("gemini_enabled", False):
        print("[responder] Gemini API ki van kapcsolva (scoring.gemini_enabled: false). Kihagy.")
        return 0

    api_key = sc.get("gemini_api_key", "")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        print("[responder] Nincs Gemini API kulcs beállítva. Kihagy.")
        return 0

    model = sc.get("gemini_model", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    system_prompt = _build_system_prompt(config)

    # Signal-vezerelt szelekcio: a Pain Classifier valodi fajdalom-jeleire
    # generalunk valaszt (nem a nyers kulcsszo-score-ra), amelyekhez meg
    # nincs draft. Kuszob: classifier.draft_min_severity (default 3).
    min_sev = config.get("classifier", {}).get("draft_min_severity", 3)
    posts = get_pain_posts_without_draft(db_path, min_severity=min_sev, limit=batch_size)
    if not posts:
        print("[responder] Nincs draft nelkuli fajdalom-jel (futtasd eloszor: --classify).")
        return 0

    generated = 0
    for post in posts:
        user_msg = _USER_TEMPLATE.format(
            platform=post.get("platform", ""),
            source=post.get("source", ""),
            author=post.get("author", ""),
            title=post.get("title", ""),
            body=(post.get("body", "") or "")[:800],
            keywords=post.get("keywords", ""),
            pain_block=_pain_context(post),
        )
        try:
            resp = client.models.generate_content(
                model=model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=200,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            draft_text = (resp.text or "").strip()
            draft_text = _append_cta(draft_text, config, post.get("platform") or "nodu")
            save_draft(db_path, post["id"], draft_text)
            mark_alerted(db_path, [post["id"]])
            generated += 1
            print(f"  [draft] '{post['title'][:60]}' -> draft mentve")
        except Exception as e:
            print(f"  [draft] HIBA ({post['id']}): {e}")

    return generated


def review_drafts(db_path: str) -> None:
    """
    Interaktív CLI loop: megjeleníti a pending draft-okat,
    az operator [a]ccept / [s]kip / [d]elete / [q]uit döntéssel kezeli.
    """
    drafts = get_pending_drafts(db_path)
    if not drafts:
        print("Nincs feldolgozásra váró draft.")
        return

    print(f"\n{len(drafts)} draft vár jóváhagyásra.\n")

    for i, d in enumerate(drafts, 1):
        print("=" * 70)
        print(f"[{i}/{len(drafts)}] {d['platform'].upper()} | {d['source']}")
        print(f"Cim  : {d['title']}")
        print(f"URL  : {d['url']}")
        print(f"Score: {d['score']} | Keywords: {d['keywords']}")
        print(f"\n--- Eredeti bejegyzes ---")
        print((d.get("body") or "")[:400])
        print(f"\n--- Javasolt valasz ---")
        print(d["draft_text"])
        print()

        while True:
            choice = input("[a]ccept  [s]kip  [d]elete  [q]uit > ").strip().lower()
            if choice in ("a", "accept"):
                mark_draft(db_path, d["draft_id"], "approved")
                print("Jóváhagyva. Másold ki a szoveget és postold kézzel.")
                print("\n--- MASOLAS ---")
                print(d["draft_text"])
                print("--- VEGE ---\n")
                break
            elif choice in ("s", "skip"):
                print("Kihagyva (marad 'pending').")
                break
            elif choice in ("d", "delete"):
                mark_draft(db_path, d["draft_id"], "rejected", "manuálisan visszautasítva")
                print("Törölve.")
                break
            elif choice in ("q", "quit"):
                print("Kilépés a review-ból.")
                return
            else:
                print("Érvénytelen: [a]ccept / [s]kip / [d]elete / [q]uit")

    print("\nReview befejezve.")


_LINKEDIN_SYSTEM_PROMPT = """
Te a NODU Bridge BIM szoftver tartalomfelelose vagy. A NODU Bridge parametrikus
adatcsere Archicad es Revit kozott: az elemek logikajat konvertalja, nem statikus
geometriat.

Feladatod: rovid, ertekes LinkedIn poszt-javaslatokat irni BIM koordinatoroknak es
menedzsereknek, a valos kozossegi fajdalompontok alapjan.

Szabalyok:
- Minden poszt egy konkret, valos fajdalompontbol induljon ki (a felhasznaloi uzenet adja meg)
- Elsodlegesen ertekes szakmai gondolat legyen, ne reklam
- A NODU Bridge-et finoman, legfeljebb a poszt vegen emlitsd
- A poszt vegen egyetlen, vilagos felhivas: a korai hozzaferesi lista hivatkozasa
  (a felhasznaloi uzenet adja meg a pontos linket, valtoztatas nelkul azt hasznald)
- Magyar nyelv, 120-180 szo posztonkent
- Nincs emoji; legfeljebb 2-3 relevans hashtag a poszt vegen
- Soha ne tulígerd a terméket
""".strip()


def generate_linkedin_content(config: dict, db_path: str) -> list[str]:
    """
    Heti LinkedIn poszt-javaslatok a DB leggyakoribb fajdalompontjaibol.
    Visszaadja a poszt-javaslatok listajat (a Slack-kuldest a hivo vegzi).
    """
    lc = config.get("linkedin_content", {})
    if not lc.get("enabled", False):
        print("[linkedin] linkedin_content.enabled: false. Kihagy.")
        return []

    sc = config.get("scoring", {})
    api_key = sc.get("gemini_api_key", "")
    if not sc.get("gemini_enabled", False) or not api_key or api_key == "YOUR_GEMINI_API_KEY":
        print("[linkedin] Gemini API nincs beallitva (scoring.gemini_enabled / api_key). Kihagy.")
        return []

    lookback = lc.get("lookback_days", 7)
    # A poszt-javaslatok mostantol a Pain Classifier valodi fajdalom-jeleire
    # epulnek (pain_summary), nem a nyers kulcsszo-gyakorisagra (2026-07-21).
    signals = get_recent_pain_signals(db_path, lookback_days=lookback, limit=8)
    if not signals:
        print("[linkedin] Nincs osztalyozott fajdalom-jel a periodusban "
              "(futtasd eloszor: --classify). Kihagy.")
        return []

    n_posts = lc.get("posts_per_week", 2)
    link = _wishlist_link(config, "linkedin", "organic")
    pain_lines = "\n".join(
        f"- (sulyossag {s['severity']}) {s['pain_summary']}"
        + (f" [tipus: {s['issue_types']}]" if s.get("issue_types") else "")
        for s in signals
    )

    user_msg = (
        f"A kozossegben az elmult {lookback} napban ezeket a VALODI fajdalmakat "
        f"detektalta a rendszer (sulyossaggal, a legsulyosabb elol):\n{pain_lines}\n\n"
        f"Irj {n_posts} kulonbozo LinkedIn poszt-javaslatot. Mindegyik EGY konkret "
        f"fajdalombol induljon ki (valaszd a legsulyosabbakat/legrelevansabbakat). "
        f"A poszt vegere ezt a pontos hivatkozast tedd felhivaskent: {link}\n\n"
        f"A posztokat valaszd el egymastol egy onallo sorban allo '---' jellel."
    )

    model = sc.get("gemini_model", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    try:
        resp = client.models.generate_content(
            model=model,
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=_LINKEDIN_SYSTEM_PROMPT,
                max_output_tokens=1600,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = resp.text.strip()
    except Exception as e:
        print(f"[linkedin] HIBA: {e}")
        return []

    posts = [p.strip() for p in text.split("---") if p.strip()]
    print(f"[linkedin] {len(posts)} poszt-javaslat generalva.")
    for i, p in enumerate(posts, 1):
        print(f"\n--- LinkedIn poszt-javaslat {i} ---\n{p}\n")
    return posts


_LINKEDIN_REPLY_SYSTEM_PROMPT = """
Te a nodu.build BIM/IFC tanacsado cegcsoport LinkedIn-kozossegi jelenlete vagy.
A nodu.build BIM/IFC tanacsadassal foglalkozik, es egyik konkret terméke a
NODU Bridge: parametrikus adatcsere Archicad es Revit kozott (az elemek
LOGIKAJAT konvertalja, nem statikus geometriat, nativ mapping scriptekkel,
nyitott IFC helyett).

Feladatod: egy beillesztett LinkedIn-poszt szovegere valaszt irni.

A VALASZ ELOTT vegezd el a kovetkezo elemzest — a JSON-mezoket EBBEN A
SORRENDBEN toltsd ki:

1. topic — A poszt FOTEAMJA. Szemantikusan sorold be (ne kulcsszavakbol kovetkeztess).
   Valaszthato ertekek: archicad, revit, interoperability, bim, ifc, ai,
   automation, digital_construction, design, engineering, project_management,
   construction, startup, business, leadership, career, event, technology,
   software, general.
   Mindig EGYET valassz.

2. post_type — A poszt KOMMUNIKACIOS TIPUSA.
   Valaszthato ertekek: opinion, question, announcement, case_study,
   success_story, technical_problem, industry_news, discussion, experience,
   hiring, event, product, general.

3. engagement_intent — Milyen tipusu valasz MUKODNE LEGJOBBAN erre a posztra.
   Valaszthato ertekek: educate, agree, challenge, expand, ask_question,
   share_experience, congratulate, support, connect.

4. reply_style — A valasz HANGNEME.
   Valaszthato ertekek: insight, expert, conversational, analytical, practical.

5. brand_mode — A nodu.build/Bridge szerepe a valaszban:
   - "bridge" — a poszt KONKRETAN Archicad-Revit (vagy tagabban BIM-szoftverek
     kozotti) adatcsere/interoperabilitas fajdalomrol szol, amit a NODU Bridge
     tenylegesen megoldana. Ilyenkor a valasz finoman, 1 mondatban megemlitheti
     a Bridge-et — nem reklamnyelvvel, inkabb "van egy eszkoz amit hasznalunk"
     hangnemben.
   - "nodu" — tagabb BIM/IFC/epitesipari koordinacios szakmai tema, ahol a
     Bridge NEM oldana meg a leirt problemat, de a nodu.build szakertoi hangja
     relevans hozzaszolast tud adni. NE emlitsd a Bridge-et — csak szakmai
     erteket adj.
   - "none" — nincs termeszetes kapcsolodas. Semleges, udvarias, erteket ado
     valasz, MARKAEMLITES NELKUL.
   Semmilyen eroszakolt marketing NEM megengedett.

6. confidence — Mennyire biztos vagy a donteseidben (0.0–1.0 lebegopontos ertek).

7. reply_text — A KESZ VALASZ a posztra. Az engagement_intent es reply_style
   MEGHATAROZZA a valasz jellget — kovetkezetesen alkalmazd oket.

8. rationale — 1 mondat angolul: MIERT ezt a topic/post_type/brand_mode
   kombinaciot valasztottad.

VALASZ-STILUS (LinkedIn kommenthez, NEM forum-valaszhoz igazitva):
- Rovid: max 60-80 szo (LinkedIn kommentben senki nem olvas el egy falat)
- Publikus, professzionalis hangnem, elso szemelyben
- Nincs emoji, nincs marketingzsargon, nincs "!!!" vagy tulzo lelkesedes
- A reply_text-et MINDIG a poszt SAJAT nyelven ird — ha a poszt angolul van,
  angolul valaszolj; ha magyarul, magyarul. Ne valts nyelvet.
- Soha ne hazudj, ne tuligerd a Bridge-et vagy a nodu.build-et
""".strip()

_LINKEDIN_REPLY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "topic": {
            "type": "STRING",
            "enum": [
                "archicad", "revit", "interoperability", "bim", "ifc", "ai",
                "automation", "digital_construction", "design", "engineering",
                "project_management", "construction", "startup", "business",
                "leadership", "career", "event", "technology", "software",
                "general",
            ],
        },
        "post_type": {
            "type": "STRING",
            "enum": [
                "opinion", "question", "announcement", "case_study",
                "success_story", "technical_problem", "industry_news",
                "discussion", "experience", "hiring", "event", "product",
                "general",
            ],
        },
        "engagement_intent": {
            "type": "STRING",
            "enum": [
                "educate", "agree", "challenge", "expand", "ask_question",
                "share_experience", "congratulate", "support", "connect",
            ],
        },
        "reply_style": {
            "type": "STRING",
            "enum": [
                "insight", "expert", "conversational", "analytical", "practical",
            ],
        },
        "brand_mode": {"type": "STRING", "enum": ["bridge", "nodu", "none"]},
        "confidence": {"type": "NUMBER"},
        "reply_text": {"type": "STRING"},
        "rationale": {"type": "STRING"},
    },
    "required": [
        "topic", "post_type", "engagement_intent", "reply_style",
        "brand_mode", "confidence", "reply_text", "rationale",
    ],
}


def generate_linkedin_reply(config: dict, post_text: str, author_name: str = "",
                            author_role: str = "") -> dict | None:
    """
    Egy beillesztett LinkedIn-poszthoz ir valaszt, egyetlen strukturalt Gemini-
    hivassal. A modell 5 lepeses dontest hoz (topic, post_type, engagement_intent,
    reply_style, brand_mode), majd ezek alapjan irja a valaszt. Visszaadja a
    strukturalt eredmenyt (8 mezo), vagy None-t hiba/hianyzo kulcs eseten.
    Nincs DB-perzisztencia — szinkron, egyszeri hasznalatra.
    """
    sc = config.get("scoring", {})
    api_key = sc.get("gemini_api_key", "")
    if not sc.get("gemini_enabled", False) or not api_key or api_key == "YOUR_GEMINI_API_KEY":
        print("[linkedin-reply] Gemini API nincs beallitva. Kihagy.")
        return None

    post_text = (post_text or "").strip()
    if not post_text:
        return None

    author_line = ""
    if author_name or author_role:
        author_line = f"Szerzo: {author_name or 'ismeretlen'}{' — ' + author_role if author_role else ''}\n"

    # A rendszerprompt (magyar nyelvu) nyelvi "sodrasa" ellen kulon, a
    # feladat-uzenetben megismetelt utasitas kell — elo tesztben (2026-07-20)
    # a modell a system-prompt-beli szabaly ellenere is magyarra valtott
    # angol nyelvu posztnal, amig ez a kozvetlen, ismetelt utasitas nem kerult be.
    user_msg = (
        f"{author_line}LinkedIn poszt:\n{post_text[:2000]}\n\n"
        "IMPORTANT: Write reply_text in the SAME language as the LinkedIn post "
        "above. If the post is in English, reply_text must be in English. "
        "Do NOT translate to Hungarian unless the post itself is Hungarian."
    )

    model = sc.get("gemini_model", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    try:
        resp = client.models.generate_content(
            model=model,
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=_LINKEDIN_REPLY_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_LINKEDIN_REPLY_SCHEMA,
                max_output_tokens=1000,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        if not resp.text:
            print("[linkedin-reply] Ures valasz.")
            return None
        return json.loads(resp.text)
    except Exception as e:
        print(f"[linkedin-reply] HIBA: {e}")
        return None
