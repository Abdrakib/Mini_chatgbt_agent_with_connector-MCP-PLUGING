import sys
from pathlib import Path
from typing import Any, Dict, List

from ddgs import DDGS

try:
    from tools.search import _clean_query
except ModuleNotFoundError:  # running as `python tools/deep_search.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.search import _clean_query

_UNAVAILABLE = "Sorry deep search is not available right now."
_SUMMARY_MAX = 200


def _truncate_summary(text: str, max_len: int = _SUMMARY_MAX) -> str:
    t = text.strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[:max_len]


def _dedupe_key(item: Dict[str, Any]) -> str:
    url = (item.get("href") or item.get("url") or "").strip()
    if url:
        return url
    title = (item.get("title") or "").strip()
    body = (item.get("body") or "").strip()[:80]
    return f"{title}|{body}"


def run_deep_search(message: str) -> str:
    base = _clean_query(message)
    if not base:
        return _UNAVAILABLE

    queries = [
        base,
        f"{base} detailed explanation",
        f"{base} latest information",
    ]

    collected: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                chunk = list(ddgs.text(q, max_results=2))
                collected.extend(chunk)
    except Exception:
        return _UNAVAILABLE

    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for item in collected:
        key = _dedupe_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)

    if not unique:
        return _UNAVAILABLE

    lines = ["Deep Search Results:", ""]
    for i, item in enumerate(unique, start=1):
        title = (item.get("title") or "").strip() or "(no title)"
        body = (item.get("body") or "").strip()
        summary = _truncate_summary(body)
        lines.append(f"{i}. Title: {title}")
        lines.append(f"   Summary: {summary}")
        if i < len(unique):
            lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(run_deep_search("what is the latest in quantum computing"))
