import re
from typing import Dict

_OFFLINE_STORE: Dict[str, str] = {}
# Set True in __main__ so CLI tests never touch Streamlit (avoids import noise).
_FORCE_OFFLINE_STORE = False

_RECALL_PHRASES = (
    "what do you know",
    "do you remember",
    "what is my",
)

_SAVE_TRIGGERS = (
    "remember",
    "my name is",
    "i am",
    "i live",
    "i like",
    "i work",
)


def _get_memory_store() -> Dict[str, str]:
    """Return the dict backing `memory_store` (session state in Streamlit, else module fallback)."""
    if _FORCE_OFFLINE_STORE:
        return _OFFLINE_STORE
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is not None:
            import streamlit as st

            if "memory_store" not in st.session_state:
                st.session_state.memory_store = {}
            return st.session_state.memory_store
    except ImportError:
        pass
    return _OFFLINE_STORE


def _strip_trailing_punct(s: str) -> str:
    return s.strip().rstrip(".!?")


def _extract_fact(message: str) -> tuple[str, str] | None:
    """Return (key, value) if a known pattern matches."""
    text = message.strip()

    patterns: tuple[tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"(?i)my\s+name\s+is\s+(.+)"), "name"),
        (re.compile(r"(?i)i\s+live\s+in\s+(.+)"), "city"),
        (re.compile(r"(?i)i\s+like\s+(.+)"), "likes"),
        (re.compile(r"(?i)i\s+work\s+(.+)"), "work"),
        (re.compile(r"(?i)i\s+am\s+(.+)"), "about"),
        (re.compile(r"(?i)remember(?:\s+that)?\s+(.+)"), "remembered"),
    )
    for pat, key in patterns:
        m = pat.search(text)
        if m:
            val = _strip_trailing_punct(m.group(1))
            if val:
                return key, val

    low = text.lower()
    if "i live" in low and "i live in" not in low:
        m = re.search(r"(?i)i\s+live\s+(.+)", text)
        if m:
            val = _strip_trailing_punct(m.group(1))
            if val:
                return "location", val

    return None


def _wants_recall(message: str) -> bool:
    low = message.lower()
    return any(phrase in low for phrase in _RECALL_PHRASES)


def _wants_save(message: str) -> bool:
    low = message.lower()
    return any(t in low for t in _SAVE_TRIGGERS)


def _format_facts_line(store: Dict[str, str]) -> str:
    parts = [f"{k} is {v}" for k, v in store.items()]
    return "Here is what I know about you: " + ", ".join(parts)


def run_memory(message: str) -> str:
    store = _get_memory_store()

    if _wants_recall(message):
        if not store:
            return "I do not know anything about you yet. Tell me something!"
        return _format_facts_line(store)

    if _wants_save(message):
        fact = _extract_fact(message)
        if fact:
            key, value = fact
            store[key] = value
        else:
            store["note"] = message.strip()
        return "Got it! I will remember that"

    return ""


def get_memory_context() -> str:
    store = _get_memory_store()
    if not store:
        return ""
    return "; ".join(f"{k} is {v}" for k, v in store.items())


if __name__ == "__main__":
    _FORCE_OFFLINE_STORE = True
    _OFFLINE_STORE.clear()
    run_memory("my name is Rakib")
    run_memory("I live in Philadelphia")
    run_memory("I like machine learning")
    print(run_memory("what do you know about me"))
    print(get_memory_context())
