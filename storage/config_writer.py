"""
Celzott, whitelistelt szoveg-patcher a config.yaml-hoz (HANDOFF SS4/19).

Miert nem yaml.dump: a PyYAML nem tud kommentet visszairni, egy admin-mentes
206 komment-only es 8 inline kommentsort torolne (mert: 524 sor/23346 bajt ->
318 sor/~7044 bajt). A config.yaml kommentjei mukodesi szabalyokat hordoznak
(pl. a stackoverflow tag-szeparator, a YAML off/on csapda, a webhook-URL
.env-be valo szandeka) - ezek ujrafelfedezese draga. Ld. docs/HANDOFF.md SS4/19
es docs/04-rendszer-audit-2026-07-28.md.

Miert nem ruamel.yaml: a projekt konvencioja nem vesz fel uj fuggoseget kis
feladatra (env_secrets.py docstring), es a ruamel sem bajt-egzakt, tehat a
tiszta git-diff cel nem teljesulne vele.

A modul a config.yaml MEGLEVO szovegeben cachereli ki csak a PATCHABLE-ben
felsorolt utak erteket - minden mas byte-ra erintetlen marad.
"""
import copy
import os
import re
import threading
from datetime import datetime, timezone

import yaml

_LOCK = threading.Lock()

_LINE_RE = re.compile(r"[^\n]*\n|[^\n]+\Z")

_MISSING = object()

# A 15 whitelistelt ut (11 skalar + 4 blokk-lista). Ami nincs itt, azt a
# writer nem irhatja - ld. ui/app.py /save route-jat es a terv "Amit tilos
# irni" szakaszat (a 3 titok: scoring.gemini_api_key, youtube.api_key,
# alerts.slack.webhook_url - ezek a .env-ben elnek).
PATCHABLE = frozenset({
    ("reddit", "client_id"),
    ("reddit", "client_secret"),
    ("reddit", "subreddits"),
    ("scoring", "gemini_enabled"),
    ("scoring", "gemini_model"),
    ("alerts", "email", "enabled"),
    ("alerts", "email", "from_address"),
    ("alerts", "email", "to_address"),
    ("alerts", "email", "app_password"),
    ("alerts", "slack", "enabled"),
    ("linkedin_content", "language"),
    ("weekly_report", "language"),
    ("keywords", "primary"),
    ("keywords", "pain_points"),
    ("keywords", "context"),
})

_LIST_PATHS = frozenset({
    ("reddit", "subreddits"),
    ("keywords", "primary"),
    ("keywords", "pain_points"),
    ("keywords", "context"),
})


class ConfigPatchError(Exception):
    pass


# --- sor-hasitas es -osztalyozas --------------------------------------------

def _split_lines(text):
    return _LINE_RE.findall(text)


def _line_body_and_eol(line):
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def _line_kind(line):
    """
    ('blank'|'comment'|'other', indent, body_eol_nelkul).

    'other' = strukturalis sor (kulcs- vagy lista-elem-sor). A hivo ebbol
    donti el, hogy szekcio-/lista-hatar lehet-e - a komment- es ures sorokat
    FUGGETLENUL a sajat indentjuktol at kell ugorni, kulonben egy col-0
    kommentblokk ket top-level szekcio kozott hamis hatarnak latszana.
    """
    body, _ = _line_body_and_eol(line)
    stripped = body.lstrip(" ")
    if stripped == "":
        return "blank", 0, body
    if stripped.startswith("#"):
        return "comment", len(body) - len(stripped), body
    return "other", len(body) - len(stripped), body


def _is_key_at(line, indent, key):
    kind, li, body = _line_kind(line)
    if kind != "other" or li != indent:
        return False
    return body[indent:].startswith(key + ":")


def _is_item_at(line, indent):
    kind, li, body = _line_kind(line)
    if kind != "other" or li != indent:
        return False
    rest = body[indent:]
    return rest == "-" or rest.startswith("- ")


def _first_structural_indent(lines, start, end):
    for j in range(start, end):
        kind, li, _ = _line_kind(lines[j])
        if kind == "other":
            return li
    return None


def _section_end(lines, start, end, max_indent):
    """Az elso strukturalis sor indexe (start,end)-ben, amelynek indentje
    <= max_indent - ez a jelenlegi kulcs szekciojanak (exclusive) vege."""
    for j in range(start, end):
        kind, li, _ = _line_kind(lines[j])
        if kind != "other":
            continue
        if li <= max_indent:
            return j
    return end


def _find_unique_key(lines, start, end, indent, key):
    matches = [j for j in range(start, end) if _is_key_at(lines[j], indent, key)]
    if not matches:
        raise ConfigPatchError(f"kulcs nem talalhato a fajlban: '{key}' (indent={indent})")
    if len(matches) > 1:
        raise ConfigPatchError(
            f"tobbertelmu (duplikalt) kulcs: '{key}' (indent={indent}, {len(matches)}x) - "
            f"ketertelmu fajlba nem irunk"
        )
    return matches[0]


def _locate(lines, path):
    """
    Vegigmegy a path szegmensein az AKTUALIS sorlistan (mert egy korabbi
    patch mar valtoztathatott rajta - ld. patch_config_file). Minden szinten
    a gyerek-indentet MERI (az elso strukturalis sor indentjebol), nem 2-nek
    felteteleszi, mert a level-kulcsok nem egyediek a fajlban (pl. 'language'
    ketszer indent-2-n, 'enabled' haromszor indent-4-en - csak a sajat
    szekciojukra szukitett kereses ket egyertelmu talalatot ad).

    Visszaadja az UTOLSO szegmens (kulcssor-index, szekciovege-exclusive,
    indent) harmasat. Lista-utaknal a hivo (_list_item_region) dolgozza fel
    az elem-tartomanyt a visszaadott hataron belul.
    """
    start, end, indent, idx = 0, len(lines), 0, None
    for depth, key in enumerate(path):
        idx = _find_unique_key(lines, start, end, indent, key)
        if depth == len(path) - 1:
            return idx, end, indent
        child_start = idx + 1
        child_end = _section_end(lines, child_start, end, indent)
        child_indent = _first_structural_indent(lines, child_start, child_end)
        if child_indent is None:
            raise ConfigPatchError(f"ures szekcio: {'.'.join(path[:depth + 1])}")
        start, end, indent = child_start, child_end, child_indent
    return idx, end, indent


def _list_item_region(lines, key_idx, section_end, indent):
    """
    Az utolso '- ' elem indexe (inclusive) `key_idx` utan, indentless
    listastilusban (az elem-indent == a kulcs-indent). A kozbulso komment-/
    ures sorokat feltetelesen lepi at: ha utanuk MEG jon elem, resze marad a
    tartomanynak, kulonben (a kovetkezo strukturalis sor mar egy sibling
    kulcs) a hatar az utolso valodi elemnel marad - ez vedi a lista UTANI
    kommentblokkot. Visszaadja azt is, hany komment-sor esik a hasznalt
    tartomanyba (ezek elvesznek az ujraírásnal - dokumentalt korlat, log-
    figyelmeztetes a hivoban).
    """
    last_idx = key_idx
    j = key_idx + 1
    while j < section_end:
        kind, li, _ = _line_kind(lines[j])
        if kind in ("blank", "comment"):
            j += 1
            continue
        if li == indent and _is_item_at(lines[j], indent):
            last_idx = j
            j += 1
            continue
        break
    inner_comments = sum(
        1 for k in range(key_idx + 1, last_idx + 1) if _line_kind(lines[k])[0] == "comment"
    )
    return last_idx, inner_comments


# --- ertek-formazas es inline komment ---------------------------------------

def _split_inline_comment(text):
    """(ertek_resz, komment_resz). A komment_resz "" vagy '#'-tal kezdodik,
    verbatim visszakerul. Csak az idezojeleken KIVULI, whitespace-szel
    elozott '#' szamit vagasi pontnak."""
    in_squote = in_dquote = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if in_squote:
            if ch == "'":
                if i + 1 < n and text[i + 1] == "'":
                    i += 2
                    continue
                in_squote = False
            i += 1
            continue
        if in_dquote:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                in_dquote = False
            i += 1
            continue
        if ch == "'":
            in_squote = True
        elif ch == '"':
            in_dquote = True
        elif ch == "#" and (i == 0 or text[i - 1] in (" ", "\t")):
            return text[:i], text[i:]
        i += 1
    return text, ""


def _format_scalar(value):
    """
    A dontobiro maga az olvaso: nem masoljuk le a PyYAML resolver-tablajat
    (off/yes/~/1_0/.inf - kezzel eltevedni garantalt). Ha a plain jelolt
    yaml.safe_load-dal visszaolvasva UGYANAZT a stringet adja, plainben
    irjuk; kulonben single-quote (a belso '-t megduplazva).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ConfigPatchError(f"tobbsoros ertek nem tamogatott ezen az uton: {text!r}")
    try:
        probe = yaml.safe_load(f"x: {text}\n")
        loaded = probe.get("x") if isinstance(probe, dict) else None
        plain_ok = isinstance(loaded, str) and loaded == text
    except yaml.YAMLError:
        plain_ok = False
    if plain_ok:
        return text
    return "'" + text.replace("'", "''") + "'"


def _apply_scalar_patch(lines, path, value):
    idx, _end, indent = _locate(lines, path)
    key = path[-1]
    body, eol = _line_body_and_eol(lines[idx])
    remainder = body[indent + len(key) + 1:]
    _, comment = _split_inline_comment(remainder)
    new_line = f"{' ' * indent}{key}: {_format_scalar(value)}"
    if comment:
        new_line += "  " + comment
    lines[idx] = new_line + eol


def _apply_list_patch(lines, path, values):
    idx, section_end, indent = _locate(lines, path)
    key = path[-1]
    last_idx, inner_comments = _list_item_region(lines, idx, section_end, indent)
    if inner_comments:
        print(
            f"[config] FIGYELEM: '{'.'.join(path)}' listan beluli {inner_comments} "
            f"kommentsor elveszik ennel a mentesnel (dokumentalt korlat, HANDOFF SS4/19)."
        )
    body, eol = _line_body_and_eol(lines[idx])
    remainder = body[indent + len(key) + 1:]
    _, comment = _split_inline_comment(remainder)
    key_line = f"{' ' * indent}{key}:"
    if not values:
        # Soha nem csupasz "key:" - az None-kent olvasodna vissza es eltorne
        # a hivo oldali `for x in ...` iteraciot.
        key_line += " []"
    if comment:
        key_line += "  " + comment
    new_lines = [key_line + eol]
    for item in values:
        new_lines.append(f"{' ' * indent}- {_format_scalar(item)}{eol}")
    lines[idx:last_idx + 1] = new_lines


# --- nested dict segedek -----------------------------------------------------

def _get_nested(d, path):
    cur = d
    for i, key in enumerate(path):
        if not isinstance(cur, dict) or key not in cur:
            raise ConfigPatchError(f"hianyzo szekcio/kulcs: {'.'.join(path[:i + 1])}")
        cur = cur[key]
    return cur


def _set_nested(d, path, value):
    cur = d
    for key in path[:-1]:
        if not isinstance(cur, dict) or key not in cur:
            raise ConfigPatchError(f"hianyzo szekcio: {'.'.join(path)}")
        cur = cur[key]
    if not isinstance(cur, dict):
        raise ConfigPatchError(f"hianyzo szekcio: {'.'.join(path)}")
    cur[path[-1]] = value


def _diff_paths(expected, actual, prefix=()):
    diffs = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for k in sorted(set(expected) | set(actual), key=str):
            diffs.extend(_diff_paths(
                expected.get(k, _MISSING), actual.get(k, _MISSING), prefix + (str(k),)
            ))
        return diffs
    if expected != actual:
        diffs.append(".".join(prefix) if prefix else "<root>")
    return diffs


# --- publikus API -------------------------------------------------------------

def patch_config_file(path, updates):
    """
    Csak a PATCHABLE-ben whitelistelt utak erteket irja at a `path` fajlban,
    minden mas bajtot erintetlenul hagyva. Visszaadja a tenylegesen
    megvaltozott utak listajat (dotted string-kent) - ures lista, ha nem
    irtunk (no-op update vagy mar egyezo ertekek).

    `updates`: dict[tuple[str, ...], object]. Nem-whitelistelt ut, duplikalt
    vagy hianyzo kulcs, illetve tobbsoros ertek eseten ConfigPatchError-t dob
    ES A FAJLHOZ NEM NYUL. Az iras utan lemezes visszaolvasassal ellenorzi
    onmagat; elteresnel visszaallitja az eredeti bajtokat (ha ez is hibazik,
    <path>.bak-<ISO> sidecarba menti oket) - az eredeti soha nem veszhet el.
    """
    if not updates:
        return []
    for p in updates:
        if p not in PATCHABLE:
            raise ConfigPatchError(f"nem engedelyezett ut: {'.'.join(p)}")

    with _LOCK:
        with open(path, "r", encoding="utf-8", newline="") as f:
            original_text = f.read()
        original_bytes = original_text.encode("utf-8")

        try:
            before = yaml.safe_load(original_text)
        except yaml.YAMLError as e:
            raise ConfigPatchError(f"a fajl nem yaml-kent olvashato, nem nyulunk hozza: {e}")
        if not isinstance(before, dict):
            raise ConfigPatchError("a config gyokere nem map - nem nyulunk hozza")

        expected = copy.deepcopy(before)
        for p, value in updates.items():
            _set_nested(expected, p, value)

        if expected == before:
            return []

        lines = _split_lines(original_text)
        changed = []
        for p, value in updates.items():
            if _get_nested(before, p) == value:
                continue
            if p in _LIST_PATHS:
                _apply_list_patch(lines, p, value)
            else:
                _apply_scalar_patch(lines, p, value)
            changed.append(".".join(p))

        if not changed:
            return []

        new_text = "".join(lines)

        try:
            reloaded_mem = yaml.safe_load(new_text)
        except yaml.YAMLError as e:
            raise ConfigPatchError(f"belso hitelesites: az uj szoveg nem yaml-parse-olhato, iras nelkul: {e}")
        mem_diff = _diff_paths(expected, reloaded_mem)
        if mem_diff:
            raise ConfigPatchError(f"belso hitelesites hiba, iras nelkul: {mem_diff}")

        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)

        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                disk_text = f.read()
            disk_val = yaml.safe_load(disk_text)
            disk_diff = _diff_paths(expected, disk_val)
        except (OSError, yaml.YAMLError) as e:
            disk_text, disk_diff = None, [str(e)]

        if disk_text is None or disk_diff:
            try:
                restore_tmp = path + ".tmp"
                with open(restore_tmp, "w", encoding="utf-8", newline="") as f:
                    f.write(original_text)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(restore_tmp, path)
            except OSError as restore_err:
                stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                sidecar = f"{path}.bak-{stamp}"
                with open(sidecar, "wb") as f:
                    f.write(original_bytes)
                raise ConfigPatchError(
                    f"KRITIKUS: a lemezes ellenorzes hibazott ES a visszaallitas is "
                    f"hibazott ({restore_err}); az eredeti fajl mentve ide: {sidecar}"
                ) from restore_err
            raise ConfigPatchError(
                f"lemezes ellenorzes hiba, az eredeti fajl visszaallitva: {disk_diff}"
            )

        return changed
