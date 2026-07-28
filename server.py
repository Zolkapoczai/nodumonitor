"""
NODU Monitor — egyetlen belépési pont: UI + ütemezett gyűjtés egy processzben.

Futtatás:   python server.py
Leállítás:  Ctrl+C

Amit indít:
  - waitress WSGI szerver a Flask UI-jal (dashboard + admin)
  - APScheduler háttér-ütemező (Reddit, fórumok, Playwright, SO, keresés,
    napi digest, heti riport, LinkedIn javaslatok — lásd main.register_jobs)

Naplózás: logs/monitor.log (rotálva, max 5 x 2 MB) + konzol.
A connectorok print() kimenete is a logba kerül, így Windows service-ként
futtatva sem veszik el semmi.
"""
import atexit
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

LOG_DIR = os.path.join(BASE_DIR, "logs")


class _StreamToLogger:
    """A print()-eket a loggerbe irányítja (service módban nincs konzol)."""

    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level

    def write(self, msg: str) -> None:
        msg = msg.rstrip()
        if msg:
            self.logger.log(self.level, msg)

    def flush(self) -> None:
        pass


class _SecretRedactingFilter(logging.Filter):
    """
    Titok-maszkolas MINDEN naplosorban, mielott fajlba/konzolra kerul.

    Miert kell: a `logs/monitor.log`-ban 2026-07-28-an **60 db** eles formatumu
    Google API-kulcs volt plain textben (`...customsearch/v1?key=AIzaSy...`), mert
    a `requests` HTTPError a TELJES URL-t naplozza. A kulcs a mar kivezetett CSE-hez
    tartozott, es a `logs/` git-ignoralt — de barmely log-masolat, screenshot vagy
    hibajelentes viszi magaval (docs/04-rendszer-audit-2026-07-28.md §2.6).

    A szuro a MINTAT maszkolja, nem konkret erteket: igy egy jovoben bekerulo uj
    kulcs is le van fedve. A meglevo sorokat NEM javitja (azt a kulcs visszavonasa
    zarja le).
    """

    _PATTERNS = [
        re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),                      # Google API-kulcs
        re.compile(r"(hooks\.slack\.com/services/)[^\s\"']+"),       # Slack webhook
        re.compile(r"((?:api[_-]?)?key=)[^\s&\"']+", re.IGNORECASE),  # ?key=... / api_key=...
        re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{12,}"),              # Bearer token
        re.compile(r"(BSA[A-Za-z0-9_\-]{20,})"),                     # Brave Search kulcs
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        for pat in cls._PATTERNS:
            if pat.groups:
                text = pat.sub(lambda m: m.group(1) + "***REDACTED***", text)
            else:
                text = pat.sub("***REDACTED***", text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = self.redact(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: self.redact(v) if isinstance(v, str) else v
                                   for k, v in record.args.items()}
                else:
                    record.args = tuple(self.redact(a) if isinstance(a, str) else a
                                        for a in record.args)
        except Exception:
            pass   # a naplozas soha ne dontse el a futast
        return True


def setup_logging() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s")
    redactor = _SecretRedactingFilter()

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "monitor.log"),
        maxBytes=2_000_000, backupCount=5, encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(redactor)

    # A konzol-handler az eredeti stderr-re ír, mert a sys.stdout/stderr
    # lentebb átirányításra kerül a loggerbe (különben végtelen kör lenne).
    console = logging.StreamHandler(sys.__stderr__)
    console.setFormatter(fmt)
    console.addFilter(redactor)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console)

    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO)
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR)


def preflight(config: dict) -> None:
    """
    Indulasi onellenorzes. Azert van, mert 2026-07-21 → 07-24 kozott a
    Playwright-connector 46 futason keresztul csendben halott volt, es semmi
    nem jelezte (ld. docs/02-lead-volume-audit-2026-07.md §3.1).

    Ket dolgot naploz ERROR szinten, ha baj van:
      1. melyik Python-interpreter fut — a Microsoft Store-os
         `WindowsApps\\python.exe` alias alatt a %LOCALAPPDATA% olvasasa
         virtualizalt, ezert a telepitett Chromium "nem letezik";
      2. letezik-e valojaban a Playwright bongeszo-binaris.
    """
    log = logging.getLogger("preflight")
    log.info("Interpreter: %s", sys.executable)

    if "\\WindowsApps\\" in sys.executable or "/WindowsApps/" in sys.executable:
        log.error(
            "ROSSZ INTERPRETER: a Microsoft Store-os Python alias fut. Ez alatt a "
            "%%LOCALAPPDATA%%\\ms-playwright olvasasa virtualizalt, ezert a Playwright "
            "nem talalja a bongeszot. Inditsd absolute uttal: "
            "...\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe server.py"
        )

    if not config.get("playwright", {}).get("enabled", True):
        log.info("Playwright letiltva a configban — bongeszo-ellenorzes kihagyva.")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright nincs telepitve (pip install playwright) — a Khoros-forumok nem gyujthetok.")
        return

    try:
        with sync_playwright() as p:
            exe = p.chromium.executable_path
        if os.path.exists(exe):
            log.info("Playwright chromium OK: %s", exe)
        else:
            log.error(
                "PLAYWRIGHT BONGESZO HIANYZIK: %s. A Graphisoft/Autodesk gyujtes NEM fog "
                "mukodni. Javitas: 'playwright install chromium' UGYANAZZAL az interpreterrel, "
                "amivel a server.py fut.", exe,
            )
    except Exception as e:
        log.error("Playwright onellenorzes nem futott le: %s", e)


def main() -> None:
    setup_logging()
    log = logging.getLogger("server")

    from apscheduler.schedulers.background import BackgroundScheduler
    from waitress import serve

    from main import JOB_DEFAULTS, describe_schedule, load_config, register_jobs
    from storage.db import init_db
    from ui.app import app

    config = load_config()
    db_path = os.path.join(BASE_DIR, config.get("database", {}).get("path", "nodu_monitor.db"))
    init_db(db_path)
    log.info("Adatbázis: %s", db_path)

    preflight(config)

    scheduler = BackgroundScheduler(job_defaults=JOB_DEFAULTS)
    register_jobs(scheduler, config, db_path)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    log.info("Ütemező elindult. %s", describe_schedule(config))

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5050))
    log.info("NODU Monitor vezérlőpult: http://%s:%d", host, port)
    serve(app, host=host, port=port, threads=8)


if __name__ == "__main__":
    main()
