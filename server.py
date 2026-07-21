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


def setup_logging() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "monitor.log"),
        maxBytes=2_000_000, backupCount=5, encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    # A konzol-handler az eredeti stderr-re ír, mert a sys.stdout/stderr
    # lentebb átirányításra kerül a loggerbe (különben végtelen kör lenne).
    console = logging.StreamHandler(sys.__stderr__)
    console.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console)

    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO)
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR)


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
