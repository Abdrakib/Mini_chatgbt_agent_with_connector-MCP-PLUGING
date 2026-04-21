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
    "my favorite",
    "i love",
    "i hate",
    "i prefer",
    "i enjoy",
    "my car is",
    "my age is",
    "my job is",
    "my major is",
    "i study",
    "i was born",
    "my birthday is",
    "my dog is",
    "my cat is",
    "my phone is",
    "my email is",
)


def _get_memory_store() -> Dict[str, str]:
    if _FORCE_OFFLINE_STORE:
        return _OFFLINE_STORE
    try:
        import streamlit as st

        if hasattr(st, "session_state"):
            if "memory_store" not in st.session_state:
                st.session_state.memory_store = {}
            return st.session_state.memory_store
    except Exception:
        pass
    return _OFFLINE_STORE


def _strip_trailing_punct(s: str) -> str:
    return s.strip().rstrip(".!?")


def _extract_fact(message: str) -> tuple[str, str] | None:
    """Return (key, value) if a known pattern matches."""
    text = message.strip()

    patterns: tuple[tuple[re.Pattern[str], str | None], ...] = (
        (re.compile(r"(?i)my\s+name\s+is\s+(.+)"), "name"),
        (re.compile(r"(?i)i\s+live\s+in\s+(.+)"), "city"),
        (re.compile(r"(?i)i\s+like\s+(.+)"), "likes"),
        (re.compile(r"(?i)i\s+work\s+(.+)"), "work"),
        (re.compile(r"(?i)i\s+am\s+(.+)"), "about"),
        (re.compile(r"(?i)remember(?:\s+that)?\s+(.+)"), "remembered"),
        (re.compile(r"(?i)my\s+favorite\s+(.+?)\s+is\s+(.+)"), None),
        (re.compile(r"(?i)i\s+love\s+(.+)"), "loves"),
        (re.compile(r"(?i)i\s+hate\s+(.+)"), "hates"),
        (re.compile(r"(?i)i\s+enjoy\s+(.+)"), "enjoys"),
        (re.compile(r"(?i)i\s+prefer\s+(.+)"), "prefers"),
        (re.compile(r"(?i)my\s+(\w+(?:\s+\w+)?)\s+is\s+(.+)"), None),
    )
    for pat, key in patterns:
        m = pat.search(text)
        if m:
            if key is None:
                if len(m.groups()) == 2:
                    key = _strip_trailing_punct(m.group(1)).lower().replace(" ", "_")
                    val = _strip_trailing_punct(m.group(2))
                else:
                    continue
            else:
                val = _strip_trailing_punct(m.group(1))
            if key and val:
                return key, val

    low = text.lower()
    if "i live" in low and "i live in" not in low:
        m = re.search(r"(?i)i\s+live\s+(.+)", text)
        if m:
            val = _strip_trailing_punct(m.group(1))
            if val:
                return "location", val

    return None


def _llm_extract_fact(message: str):
    try:
        from model import generate_response

        prompt = (
            f"Extract a personal fact from this sentence as a key:value pair.\n"
            f"Rules:\n"
            f"- Reply with ONLY 'key: value' nothing else\n"
            f"- key should be a single word like 'car', 'food', 'name', 'city'\n"
            f"- value should be what was stated\n"
            f"- If no personal fact exists reply with 'none'\n"
            f"Sentence: {message}\n"
            f"Answer:"
        )
        result = generate_response(prompt).strip()
        if result.lower() == "none" or ":" not in result:
            return None
        parts = result.split(":", 1)
        key = parts[0].strip().lower()
        value = parts[1].strip()
        if key and value:
            return key, value
        return None
    except Exception:
        return None


def _wants_recall(message: str) -> bool:
    low = message.lower()
    return any(phrase in low for phrase in _RECALL_PHRASES)


def _wants_save(message: str) -> bool:
    low = message.lower()
    return any(t in low for t in _SAVE_TRIGGERS)


def _format_facts_line(store: Dict[str, str]) -> str:
    parts = []
    for k, v in store.items():
        key_clean = k.replace("_", " ")
        parts.append(f"Your {key_clean} is {v}")
    return "Here is what I know about you: " + ", ".join(parts)


def run_memory(message: str) -> str:
    store = _get_memory_store()

    if _wants_recall(message):
        if not store:
            return "I do not know anything about you yet. Tell me something!"
        return _format_facts_line(store)

    if _wants_save(message):
        fact = _extract_fact(message)
        if not fact:
            fact = _llm_extract_fact(message)
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
