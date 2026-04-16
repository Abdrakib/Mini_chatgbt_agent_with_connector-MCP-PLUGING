import re
from typing import List

from ddgs import DDGS

_NOTHING = "Sorry I could not find anything about that."
_UNAVAILABLE = "Sorry the search is not available right now."
_SUMMARY_MAX = 150

# Longest phrases first so "search for" wins over "search" if we ever add shorter overlaps
_FILLERS = (
    "search for",
    "tell me about",
    "look up",
    "what is",
    "who is",
    "find",
)


def _clean_query(message: str) -> str:
    q = message.strip()
    if not q:
        return q
    changed = True
    while changed:
        changed = False
        ql = q.lower()
        for phrase in _FILLERS:
            if ql.startswith(phrase):
                q = q[len(phrase) :].strip()
                q = re.sub(r"^[?.,!:;\s]+", "", q)
                changed = True
                break
    return q.strip() if q.strip() else message.strip()


def _truncate_summary(text: str) -> str:
    t = text.strip().replace("\n", " ")
    if len(t) <= _SUMMARY_MAX:
        return t
    return t[:_SUMMARY_MAX]


def _format_results(items: List[dict]) -> str:
    lines = ["Here is what I found:", ""]
    for i, item in enumerate(items, start=1):
        title = (item.get("title") or "").strip() or "(no title)"
        body = (item.get("body") or "").strip()
        summary = _truncate_summary(body)
        lines.append(f"{i}. Title: {title}")
        lines.append(f"   Summary: {summary}")
        if i < len(items):
            lines.append("")
    return "\n".join(lines)


def run_search(message: str) -> str:
    query = _clean_query(message)
    if not query:
        return _NOTHING
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
    except Exception:
        return _UNAVAILABLE
    if not results:
        return _NOTHING
    return _format_results(results)


if __name__ == "__main__":
    for phrase in (
        "search for latest news about artificial intelligence",
        "who is Elon Musk",
        "what is machine learning",
    ):
        print("---")
        print(phrase)
        print(run_search(phrase))
