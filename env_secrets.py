"""
Titkok olvasasa kornyezeti valtozobol vagy a projekt `.env` fajljabol.

Miert kell: a `config.yaml` ma plain textben tartja az API-kulcsokat, es az
admin UI vissza is irja oket (a 01-es audit §2 ezt explicit szagnak nevezi, a
2. fazis "env-titkok" pontja pedig el volt halasztva). Az UJ titkokat (SalesOS
BRIDGE_API_KEY, kereso-provider kulcs) ezert nem tesszuk a config.yaml-be:
env-bol vagy `.env`-bol jonnek, es a `.gitignore` mar kizarja a `.env`-et.

Nincs uj fuggoseg (nem python-dotenv) — a `.env` formatum itt szandekosan
minimalis: `KULCS=ertek` soronkent, `#` komment, opcionalis idezojelek.
A meglevo kulcsok (Gemini, YouTube, Reddit) maradnak a configban; azok
kivezetese kulon feladat, nem ennek a valtozasnak a hatokore.
"""
import os

_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_cache: dict[str, str] | None = None


def _load_env_file() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache
    values: dict[str, str] = {}
    if os.path.exists(_ENV_FILE):
        try:
            with open(_ENV_FILE, encoding="utf-8") as f:
                for lineno, raw in enumerate(f, 1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        # NEM csendben dobjuk el: a SLACK_WEBHOOK_URL eloszor
                        # `SLACK WEBHOOK: https://...` formaban kerult ide, es a
                        # titok "ott volt a fajlban", megis beallitatlannak
                        # latszott. Egy `=` nelkuli sor szinte mindig elirt kulcs.
                        print(f"[env] A .env {lineno}. sora '=' nelkul van, kihagyva: "
                              f"{line.split(':')[0][:24]!r}... (helyes forma: KULCS=ertek)")
                        continue
                    key, _, val = line.partition("=")
                    values[key.strip()] = val.strip().strip('"').strip("'")
        except OSError as e:
            print(f"[env] A .env nem olvashato ({e}) — kihagyva.")
    _cache = values
    return values


def get_secret(name: str, config_value: str = None) -> str:
    """
    Egy titok feloldasa, ebben a sorrendben:
      1. kornyezeti valtozo
      2. a projekt `.env` fajlja
      3. a kapott config-ertek (visszafele-kompatibilitas)

    A placeholder-ertekeket ('', 'YOUR_...') ures stringnek tekinti, hogy a
    hivo egyszeruen `if not key:` alapjan tudjon kihagyni — ugyanaz a minta,
    mint a tobbi connectorban.
    """
    for candidate in (os.environ.get(name), _load_env_file().get(name), config_value):
        if not candidate:
            continue
        value = str(candidate).strip()
        if not value or value.upper().startswith("YOUR_"):
            continue
        return value
    return ""
