import re
from urllib.parse import quote

import requests

_FAILURE = "Sorry I could not get the weather right now. Please try again."
_DEFAULT_CITY = "Philadelphia"

# Skip weak matches like "in the morning" (leading token after "in")
_SKIP_LEADING = frozenset(
    {"the", "a", "an", "this", "that", "these", "those", "my", "your", "its", "our", "their"}
)

_CITY_PATTERN = re.compile(r"(?i)\bin\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)")


def _title_city(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split())


def _extract_city(message: str) -> str:
    matches = list(_CITY_PATTERN.finditer(message.strip()))
    if not matches:
        return _DEFAULT_CITY
    for m in reversed(matches):
        raw = m.group(1).strip()
        if not raw:
            continue
        first = raw.split(maxsplit=1)[0].lower()
        if first in _SKIP_LEADING:
            continue
        return _title_city(raw)
    # All matches were skipped; use last raw capture or default
    last = matches[-1].group(1).strip()
    return _title_city(last) if last else _DEFAULT_CITY


def run_weather(message: str) -> str:
    city = _extract_city(message)
    url = f"https://wttr.in/{quote(city)}?format=3"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        body = resp.text.strip()
        if not body:
            return _FAILURE
        if ":" in body:
            rest = body.split(":", 1)[1].strip()
        else:
            rest = body
        return f"Current weather in {city}: {rest}"
    except (requests.RequestException, OSError):
        return _FAILURE


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    for phrase in (
        "what is the weather in Philadelphia",
        "what should I wear today in New York",
        "is it cold in Chicago",
    ):
        print(phrase, "->", run_weather(phrase))
