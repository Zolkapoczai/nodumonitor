"""
A `storage/config_writer.py` (celzott config.yaml-iro) tesztje (HANDOFF §4/19).

A) Megorzes  - nem patchelt sorok bajtra azonosak; CRLF/BOM; az elo config.yaml
               masolatan a 206 komment-only + 8 inline komment megmarad
B) Celzas    - hatarolt kereses (language ketszer, enabled haromszor), nem
               letezo/duplikalt/nem-whitelistelt ut -> hiba, fajl valtozatlan
C) Tipizalas - a dontobiro maga yaml.safe_load, nem a kezzel masolt resolver
D) Listak    - hatar-detektalas (elotte/utana komment), ures/nem-ures valtas,
               tobb patch egy hivasban (index-eltolodas)
E) Rollback  - iras elotti/utani hitelesites, visszaallitas, nincs .tmp maradek
F) Route     - ui/app.py /save: ures mezo = valtozatlan, kw_* fuggetlen,
               reszleges POST nem valt boolt, hianyzo szekcio -> 400 nem 500
"""
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml

import storage.config_writer as cw
from storage.config_writer import patch_config_file, ConfigPatchError, PATCHABLE

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LIVE_CONFIG = os.path.join(PROJECT_ROOT, "config.yaml")
TMPDIR = tempfile.mkdtemp(prefix="nodu-cw-test-")


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def read_text(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def count_comment_only(text):
    return sum(1 for l in text.splitlines() if l.strip().startswith("#"))


def count_inline_comments(text):
    n = 0
    for l in text.splitlines():
        s = l.strip()
        if s.startswith("#"):
            continue
        if "#" in l:
            n += 1
    return n


# --- fixture: kis, tobb-szekcios YAML minden csapdaval, CRLF-mel ------------
# (col-0 kommentblokk ket szekcio kozott, indentalt komment beagyazott map
# elott, komment a lista-kulcs FOLOTT es az utolso elem UTAN, inline komment
# egy skalaron, 'language' ketszer, harom szintu ut, ures flow-lista [])
FIXTURE_LINES = [
    "reddit:",
    "  client_id: YOUR_ID",
    "  client_secret: YOUR_SECRET",
    "  # ez egy indentalt komment egy beagyazott map elott",
    "  nested:",
    "    inner: value",
    "  # komment a lista-kulcs felett",
    "  subreddits:",
    "  - Revit",
    "  - ArchiCAD",
    "  # komment az utolso elem alatt (meg a subreddits-hez tartozik)",
    "  max_search_queries: 12",
    "scoring:",
    "  gemini_enabled: true",
    "  gemini_model: gemini-2.5-flash  # inline komment, ne vesszen el",
    "alerts:",
    "  email:",
    "    enabled: false",
    "    from_address: old@example.com",
    "    to_address: old2@example.com",
    "    app_password: oldpass",
    "  slack:",
    "    enabled: true",
    "  webhook:",
    "    enabled: false",
    "# col-0 kommentblokk a ket szekcio kozott - ez NEM hatar",
    "# meg egy sor ugyanabbol a blokkbol",
    "keywords:",
    "  primary: []",
    "  pain_points:",
    "  - meglevo elem",
    "  context:",
    "  - ctx elem",
    "linkedin_content:",
    "  language: en",
    "weekly_report:",
    "  language: hu",
]
FIXTURE_TEXT = "\r\n".join(FIXTURE_LINES) + "\r\n"


def make_fixture(name="fixture.yaml", text=FIXTURE_TEXT):
    path = os.path.join(TMPDIR, name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def line_diff(before_text, after_text):
    """Az elteroe (1-idx) sorszamok listaja, ha a sorszam AZONOS marad."""
    b = before_text.split("\r\n")
    a = after_text.split("\r\n")
    if len(a) != len(b):
        return None
    return [i for i, (x, y) in enumerate(zip(b, a), 1) if x != y]


# =============================================================================
# A) Megorzes
# =============================================================================

fx = make_fixture("a1.yaml")
before_text = read_text(fx)
patch_config_file(fx, {("weekly_report", "language"): "en"})
after_text = read_text(fx)
diff = line_diff(before_text, after_text)
check("A1 csak az erintett sor valtozik, tobbi bajtra azonos", diff == [37], f"{diff}")
check("A2 a fajl CRLF marad", after_text.count("\r\n") == after_text.count("\n"))
check("A3 nincs BOM", not read_bytes(fx).startswith(b"\xef\xbb\xbf"))

fx = make_fixture("a4.yaml")
b1 = read_bytes(fx)
changed = patch_config_file(fx, {("weekly_report", "language"): "hu"})  # mar 'hu'
check("A4 no-op mentes -> ures lista, fajl bajtra valtozatlan",
      changed == [] and read_bytes(fx) == b1)

live_copy = make_fixture("live_a.yaml", None) if False else os.path.join(TMPDIR, "live_a.yaml")
shutil.copy(LIVE_CONFIG, live_copy)
live_before = read_text(live_copy)
# A kiindulo szamot a FAJLBOL vesszuk, nem beegetve: a config.yaml elo dokumentum
# (2026-07-29-en pl. a linkedin.intent_layer 14 komment-sorral bovult), es egy
# beegetett darabszam minden legitim config-szerkesztesnel elhasal, holott a
# MERT INVARIANS nem a szam, hanem hogy az iras utan UGYANANNYI marad.
live_comment_lines = count_comment_only(live_before)
live_inline_comments = count_inline_comments(live_before)
check("A5 elo config: erdemben kommentelt (a komment-only sorok szama > 150)",
      live_comment_lines > 150, str(live_comment_lines))
check("A6 elo config: van inline komment is", live_inline_comments >= 8,
      str(live_inline_comments))
patch_config_file(live_copy, {("weekly_report", "language"): "en"})
live_after = read_text(live_copy)
check("A7 elo config MASOLATAN egy mezo irasa utan MIND a komment-only sor marad",
      count_comment_only(live_after) == live_comment_lines,
      f"{count_comment_only(live_after)} != {live_comment_lines}")
check("A8 elo config MASOLATAN egy mezo irasa utan MIND az inline komment marad",
      count_inline_comments(live_after) == live_inline_comments,
      f"{count_inline_comments(live_after)} != {live_inline_comments}")
b_after1 = read_bytes(live_copy)
changed2 = patch_config_file(live_copy, {("weekly_report", "language"): "en"})  # ismetelt, valtozatlan
check("A9 elo config masolat: ismetelt mentes ugyanazzal az ertekkel -> bajtra no-op",
      changed2 == [] and read_bytes(live_copy) == b_after1)


# =============================================================================
# B) Celzas
# =============================================================================

fx = make_fixture("b1.yaml")
patch_config_file(fx, {("linkedin_content", "language"): "de"})
loaded = yaml.safe_load(read_text(fx))
check("B1 linkedin_content.language irasa nem nyul weekly_report.language-hez",
      loaded["linkedin_content"]["language"] == "de" and loaded["weekly_report"]["language"] == "hu")

fx = make_fixture("b2.yaml")
patch_config_file(fx, {("alerts", "email", "enabled"): True})
loaded = yaml.safe_load(read_text(fx))
check("B2 alerts.email.enabled irasa nem nyul slack/webhook enabled-hez",
      loaded["alerts"]["email"]["enabled"] is True
      and loaded["alerts"]["slack"]["enabled"] is True
      and loaded["alerts"]["webhook"]["enabled"] is False)

fx = make_fixture("b3.yaml")
before_text = read_text(fx)
patch_config_file(fx, {("linkedin_content", "language"): "de"})
after_text = read_text(fx)
comment_block = after_text.split("\r\n")[25:27]  # a col-0 blokk 2 sora (26-27. sor)
check("B3 a col-0 kommentblokk a szekciok kozott nem serul (nem hatar)",
      all(l.strip().startswith("#") for l in comment_block), comment_block)

fx = make_fixture("b4_nincsslack.yaml", text=FIXTURE_TEXT.replace(
    "  slack:\r\n    enabled: true\r\n", ""))
try:
    patch_config_file(fx, {("alerts", "slack", "enabled"): False})
    check("B4 nem letezo ut (hianyzo kulcs a fajlban) -> hiba", False)
except ConfigPatchError:
    check("B4 nem letezo ut (hianyzo kulcs a fajlban) -> hiba", True)
check("B4b a fajl valtozatlan maradt a hiba utan", read_text(fx) == FIXTURE_TEXT.replace(
    "  slack:\r\n    enabled: true\r\n", ""))

dup_text = FIXTURE_TEXT.replace(
    "  slack:\r\n    enabled: true\r\n",
    "  slack:\r\n    enabled: true\r\n    enabled: true\r\n",
)
fx = make_fixture("b5_dup.yaml", text=dup_text)
try:
    patch_config_file(fx, {("alerts", "slack", "enabled"): False})
    check("B5 duplikalt kulcs -> hiba (ketertelmu fajlba nem irunk)", False)
except ConfigPatchError:
    check("B5 duplikalt kulcs -> hiba (ketertelmu fajlba nem irunk)", True)
check("B5b a fajl valtozatlan maradt a hiba utan", read_text(fx) == dup_text)

fx = make_fixture("b6.yaml")
b1 = read_bytes(fx)
try:
    patch_config_file(fx, {("youtube", "api_key"): "x"})
    check("B6 nem-whitelistelt ut -> hiba", False)
except ConfigPatchError:
    check("B6 nem-whitelistelt ut -> hiba", True)
check("B6b a fajl valtozatlan maradt (nem-whitelistelt ut eseten hozza sem nyulunk)",
      read_bytes(fx) == b1)


# =============================================================================
# C) Tipizalas
# =============================================================================

def _typed(name, value, expected_roundtrip=None):
    fx = make_fixture(f"c_{name}.yaml")
    patch_config_file(fx, {("scoring", "gemini_model"): value})
    text = read_text(fx)
    loaded = yaml.safe_load(text)["scoring"]["gemini_model"]
    exp = value if expected_roundtrip is None else expected_roundtrip
    return text, loaded, exp


for tok in ("off", "on", "yes", "no", "null", "~", "true", "false"):
    text, loaded, exp = _typed(f"trap_{tok}", tok)
    check(f"C '{tok}' stringkent olvasodik vissza es idezojeles a sorban",
          loaded == tok and f"gemini_model: '{tok}'" in text, f"{loaded!r} in {text!r}")

for tok in ("1.0", "007", "0x1f", "1_0", ".inf"):
    text, loaded, exp = _typed(f"num_{tok}", tok)
    check(f"C '{tok}' stringkent olvasodik vissza (nem szammal)",
          loaded == tok and isinstance(loaded, str), f"{loaded!r}")

text, loaded, exp = _typed("plain", "gemini-2.5-flash")
check("C 'gemini-2.5-flash' idezojel NELKUL irodik (nincs diff-zaj)",
      loaded == "gemini-2.5-flash" and "'gemini-2.5-flash'" not in text
      and "gemini_model: gemini-2.5-flash" in text)

fx = make_fixture("c_comment.yaml")
patch_config_file(fx, {("scoring", "gemini_model"): "gemini-2.5-pro"})
line = [l for l in read_text(fx).split("\r\n") if l.startswith("  gemini_model:")][0]
check("C inline komment megmarad a skalar-patch utan is",
      line == "  gemini_model: gemini-2.5-pro  # inline komment, ne vesszen el", line)

text, loaded, exp = _typed("apostrophe", "it's: a test")  # a ": " kenyszeriti az idezojelezest
check("C \"it's\" apostrof megduplazva idezojelezve (ha a kenyszer amugy is idezojelet ker)",
      loaded == "it's: a test" and "'it''s: a test'" in text, text)

text, loaded, exp = _typed("empty", "")
check("C ures string -> '' nem None", loaded == "" and isinstance(loaded, str))

text, loaded, exp = _typed("utf8", "árvíztűrő tükörfúrógép")
check("C UTF-8 nyersen (nincs \\u escape)", loaded == "árvíztűrő tükörfúrógép"
      and "\\u" not in text)

fx = make_fixture("c_newline.yaml")
b1 = read_bytes(fx)
try:
    patch_config_file(fx, {("scoring", "gemini_model"): "sor1\nsor2"})
    check("C ujsoros ertek -> hiba (nem tort YAML)", False)
except ConfigPatchError:
    check("C ujsoros ertek -> hiba (nem tort YAML)", True)
check("C ujsoros ertek: a fajl valtozatlan maradt", read_bytes(fx) == b1)

fx = make_fixture("c_bool.yaml")
patch_config_file(fx, {("scoring", "gemini_enabled"): False})
loaded_bool_text = read_text(fx)
check("C bool False -> 'false' kisbetuvel",
      "gemini_enabled: false" in loaded_bool_text
      and yaml.safe_load(loaded_bool_text)["scoring"]["gemini_enabled"] is False)


# =============================================================================
# D) Listak
# =============================================================================

fx = make_fixture("d1.yaml")
before_lines = read_text(fx).split("\r\n")
patch_config_file(fx, {("reddit", "subreddits"): ["Revit"]})
after_lines = read_text(fx).split("\r\n")
before_comment = "  # komment a lista-kulcs felett"
after_comment = "  # komment az utolso elem alatt (meg a subreddits-hez tartozik)"
check("D1a a lista ELOTTI kommentsor megmarad", before_comment in after_lines)
check("D1b a lista UTANI kommentsor megmarad", after_comment in after_lines)
check("D1c a lista utani kulcs (max_search_queries) erteke valtozatlan",
      "  max_search_queries: 12" in after_lines)
check("D1d az uj elem-indent = az eredeti (2 szokoz)", "  - Revit" in after_lines)

fx = make_fixture("d3.yaml")
patch_config_file(fx, {("reddit", "subreddits"): []})
loaded = yaml.safe_load(read_text(fx))
check("D3 uresre valtas -> [] (nem None), es SOHA nem csupasz 'subreddits:'",
      loaded["reddit"]["subreddits"] == [] and "  subreddits: []" in read_text(fx).split("\r\n"))

fx = make_fixture("d4.yaml")
patch_config_file(fx, {("keywords", "primary"): ["nodu", "nodu bridge"]})
lines = read_text(fx).split("\r\n")
loaded = yaml.safe_load(read_text(fx))
check("D4 []-rol nem-uresre: kulcssor 'primary:' (nincs inline []), es a lista visszaolvasva jo",
      "  primary:" in lines and loaded["keywords"]["primary"] == ["nodu", "nodu bridge"])

mid_list_text = FIXTURE_TEXT.replace(
    "  pain_points:\r\n  - meglevo elem\r\n",
    "  pain_points:\r\n  - elso elem\r\n  # kozbulso komment, ez elveszik\r\n  - masodik elem\r\n",
)
fx = make_fixture("d5_midlist.yaml", text=mid_list_text)
_stdout = sys.stdout
sys.stdout = io.StringIO()
try:
    patch_config_file(fx, {("keywords", "pain_points"): ["elso elem", "masodik elem", "harmadik"]})
    warn_output = sys.stdout.getvalue()
finally:
    sys.stdout = _stdout
loaded = yaml.safe_load(read_text(fx))
check("D5a kozbulso komment mellett a patch NEM hasal el",
      loaded["keywords"]["pain_points"] == ["elso elem", "masodik elem", "harmadik"])
check("D5b a kozbulso komment-veszteseg logolt figyelmeztetest ad",
      "FIGYELEM" in warn_output and "pain_points" in warn_output, warn_output)

fx = make_fixture("d6.yaml")
all_updates = {
    ("reddit", "client_id"): "new_id",
    ("reddit", "client_secret"): "new_secret",
    ("reddit", "subreddits"): ["Revit", "ArchiCAD", "BIM"],
    ("scoring", "gemini_enabled"): False,
    ("scoring", "gemini_model"): "gemini-2.5-pro",
    ("alerts", "email", "enabled"): True,
    ("alerts", "email", "from_address"): "a@b.com",
    ("alerts", "email", "to_address"): "c@d.com",
    ("alerts", "email", "app_password"): "newpass",
    ("alerts", "slack", "enabled"): False,
    ("linkedin_content", "language"): "hu",
    ("weekly_report", "language"): "en",
    ("keywords", "primary"): ["a", "b", "c", "d"],
    ("keywords", "pain_points"): ["x"],
    ("keywords", "context"): [],
}
check("D6 pontosan a 15 whitelistelt utat probaljuk egy hivasban", len(all_updates) == 15
      and set(all_updates) == PATCHABLE)
changed = patch_config_file(fx, all_updates)
loaded = yaml.safe_load(read_text(fx))
check("D6a mind a 15 ut valtozottkent jott vissza (index-eltolodas ellenere)",
      sorted(changed) == sorted(".".join(p) for p in all_updates), sorted(changed))
check("D6b minden ertek helyesen irodott (mintaellenorzes)",
      loaded["reddit"]["client_id"] == "new_id"
      and loaded["reddit"]["subreddits"] == ["Revit", "ArchiCAD", "BIM"]
      and loaded["scoring"]["gemini_enabled"] is False
      and loaded["alerts"]["slack"]["enabled"] is False
      and loaded["keywords"]["context"] == []
      and loaded["keywords"]["primary"] == ["a", "b", "c", "d"]
      and loaded["weekly_report"]["language"] == "en"
      and loaded["linkedin_content"]["language"] == "hu")
check("D6c a nested.inner mezo (nem-whitelistelt) erintetlen", loaded["reddit"]["nested"]["inner"] == "value")


# =============================================================================
# E) Rollback
# =============================================================================

fx = make_fixture("e1_badyaml.yaml")
b1 = read_bytes(fx)
real_format = cw._format_scalar
cw._format_scalar = lambda v: "[unclosed"
try:
    try:
        patch_config_file(fx, {("weekly_report", "language"): "en"})
        check("E1 torott-YAML-t ado iro -> hiba, iras nelkul", False)
    except ConfigPatchError as e:
        check("E1 torott-YAML-t ado iro -> hiba, iras nelkul", "hitelesites" in str(e) or "parse" in str(e), str(e))
finally:
    cw._format_scalar = real_format
check("E1b a fajl bajtra az eredeti maradt", read_bytes(fx) == b1)
check("E1c nincs .tmp maradek", not os.path.exists(fx + ".tmp"))

fx = make_fixture("e2_wrongvalue.yaml")
b1 = read_bytes(fx)
cw._format_scalar = lambda v: "'SZANDEKOSAN_ROSSZ'"
try:
    try:
        patch_config_file(fx, {("weekly_report", "language"): "en"})
        check("E2 ervenyes, de MAS erteket ado iro -> hiba (szemantikai check)", False)
    except ConfigPatchError as e:
        check("E2 ervenyes, de MAS erteket ado iro -> hiba (szemantikai check)", True, str(e))
finally:
    cw._format_scalar = real_format
check("E2b a fajl bajtra az eredeti maradt", read_bytes(fx) == b1)
check("E2c nincs .tmp maradek", not os.path.exists(fx + ".tmp"))

fx = make_fixture("e3_diskcorrupt.yaml")
b1 = read_bytes(fx)
real_replace = cw.os.replace
_replace_calls = [0]


def _corrupt_first_replace_only(src, dst):
    # Csak az ELSO (elsodleges) irast "rontjuk el" - a masodikat (a
    # visszaallitast) a valodi os.replace vegzi, kulonben a mock maga
    # akadalyozna meg a helyreallitast.
    real_replace(src, dst)
    _replace_calls[0] += 1
    if _replace_calls[0] == 1:
        with open(dst, "a", encoding="utf-8", newline="") as f:
            f.write("suto_extra_kulcs_amit_a_diszk_visszaolvasas_eszrevesz: 999\r\n")


cw.os.replace = _corrupt_first_replace_only
try:
    try:
        patch_config_file(fx, {("weekly_report", "language"): "en"})
        check("E3 lemezes visszaolvasas elteres -> hiba, es a fajl VISSZAALL", False)
    except ConfigPatchError as e:
        check("E3 lemezes visszaolvasas elteres -> hiba, es a fajl VISSZAALL",
              read_bytes(fx) == b1, str(e))
finally:
    cw.os.replace = real_replace
check("E3b nincs .tmp maradek a visszaallitas utan", not os.path.exists(fx + ".tmp"))

fx = make_fixture("e4_unparsable.yaml", text="reddit:\r\n  client_id: [ez nem zarul be\r\n")
b1 = read_bytes(fx)
try:
    patch_config_file(fx, {("reddit", "client_id"): "x"})
    check("E4 parse-olhatatlan kiindulo fajl -> hiba, hozza sem nyulunk", False)
except ConfigPatchError:
    check("E4 parse-olhatatlan kiindulo fajl -> hiba, hozza sem nyulunk", True)
check("E4b a fajl bajtra az eredeti maradt", read_bytes(fx) == b1)
check("E4c nincs .tmp maradek", not os.path.exists(fx + ".tmp"))

check("E5 egyik hiba-agon sem maradt .tmp fajl a tmp konyvtarban",
      not any(f.endswith(".tmp") for f in os.listdir(TMPDIR)))


# =============================================================================
# F) Route-szint (ui/app.py /save)
# =============================================================================

sys.path.insert(0, PROJECT_ROOT)
import ui.app as uiapp  # noqa: E402

route_cfg = os.path.join(TMPDIR, "route_config.yaml")
shutil.copy(LIVE_CONFIG, route_cfg)
uiapp.CONFIG_PATH = route_cfg
client = uiapp.app.test_client()

before = yaml.safe_load(read_text(route_cfg))
resp = client.post("/save", data={"reddit_client_id": "abc123"})
after = yaml.safe_load(read_text(route_cfg))
check("F1 ures reddit_subreddits -> a 8 subreddit valtozatlan",
      after["reddit"]["subreddits"] == before["reddit"]["subreddits"]
      and len(after["reddit"]["subreddits"]) == 8)
check("F1b a nem-ures mezo (client_id) megis irodott", after["reddit"]["client_id"] == "abc123")
check("F1c a valasz redirect + warn parameter", resp.status_code == 302
      and "warn=" in resp.headers.get("Location", ""))

shutil.copy(LIVE_CONFIG, route_cfg)
before_pain = yaml.safe_load(read_text(route_cfg))["keywords"]["pain_points"]
client.post("/save", data={"kw_primary": "foo\nbar"})
after = yaml.safe_load(read_text(route_cfg))
check("F2 kw_primary megvan, kw_pain nincs -> az 54 pain-kulcsszo valtozatlan",
      after["keywords"]["pain_points"] == before_pain and after["keywords"]["primary"] == ["foo", "bar"])

shutil.copy(LIVE_CONFIG, route_cfg)
raw = read_text(route_cfg).replace("app_password: YOUR_APP_PASSWORD", "app_password: realsecret123")
with open(route_cfg, "w", encoding="utf-8", newline="") as f:
    f.write(raw)
client.post("/save", data={"reddit_client_id": "x"})
after = yaml.safe_load(read_text(route_cfg))
check("F3 ures email_password -> az elo jelszo valtozatlan (nincs placeholder-felulirás)",
      after["alerts"]["email"]["app_password"] == "realsecret123")

shutil.copy(LIVE_CONFIG, route_cfg)
before = yaml.safe_load(read_text(route_cfg))
client.post("/save", data={"reddit_client_id": "x"})
after = yaml.safe_load(read_text(route_cfg))
check("F4 reszleges POST -> gemini_enabled valtozatlan",
      after["scoring"]["gemini_enabled"] == before["scoring"]["gemini_enabled"])
check("F4b reszleges POST -> alerts.slack.enabled valtozatlan",
      after["alerts"]["slack"]["enabled"] == before["alerts"]["slack"]["enabled"])

shutil.copy(LIVE_CONFIG, route_cfg)
client.post("/save", data={"reddit_client_id": "x", "gemini_enabled__present": "1"})
after = yaml.safe_load(read_text(route_cfg))
check("F4c valodi form (kiserto mezovel, checkbox nincs bepipalva) -> a bool TENYLEGESEN False-ra all",
      after["scoring"]["gemini_enabled"] is False)

shutil.copy(LIVE_CONFIG, route_cfg)
raw = read_text(route_cfg).replace("scoring:\r\n", "scoring_renamed:\r\n", 1)
with open(route_cfg, "w", encoding="utf-8", newline="") as f:
    f.write(raw)
before_bytes = read_bytes(route_cfg)
resp = client.post("/save", data={"gemini_model": "gemini-2.5-pro"})
check("F5 hianyzo szekcio -> HTTP 400, nem 500", resp.status_code == 400, resp.status_code)
check("F5b a fajl erintetlen maradt", read_bytes(route_cfg) == before_bytes)
check("F5c lathato hibasav, nem stacktrace", b"save-banner error" in resp.data and b"Traceback" not in resp.data)

form_paths = {
    ("reddit", "client_id"), ("reddit", "client_secret"), ("reddit", "subreddits"),
    ("scoring", "gemini_enabled"), ("scoring", "gemini_model"),
    ("alerts", "email", "enabled"), ("alerts", "email", "from_address"),
    ("alerts", "email", "to_address"), ("alerts", "email", "app_password"),
    ("alerts", "slack", "enabled"),
    ("keywords", "primary"), ("keywords", "pain_points"), ("keywords", "context"),
    ("linkedin_content", "language"), ("weekly_report", "language"),
}
check("F6 a form osszes irt utja == PATCHABLE (uj mezo hozzaadasa buktatna ezt)",
      form_paths == PATCHABLE, form_paths ^ PATCHABLE)


# =============================================================================
print()
bad = 0
for name, ok, detail in results:
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail else ""))
print(f"\n{len(results) - bad}/{len(results)} teszt zold.")

shutil.rmtree(TMPDIR, ignore_errors=True)
sys.exit(1 if bad else 0)
