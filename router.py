import re
from typing import Any, Dict

from thefuzz import fuzz

_WEATHER_KEYS = (
    "weather",
    "temperature",
    "forecast",
    "wear",
    "cold",
    "hot",
    "raining",
    "sunny",
    "umbrella",
    "coat",
    "jacket",
    "outside",
    "humid",
    "wind",
)

_DEEP_SEARCH_KEYS = (
    "deep search",
    "research",
    "explain in detail",
    "comprehensive",
    "everything about",
    "full explanation",
    "in depth",
    "deep dive",
)

_SEARCH_KEYS = (
    "search",
    "look up",
    "find",
    "who is",
    "what is",
    "tell me about",
    "news",
    "latest",
    "current events",
)

_CALC_WORD_KEYS = (
    "calculate",
    "plus",
    "minus",
    "times",
    "divided",
    "multiply",
    "percent",
    "square root",
)

_MEMORY_KEYS = (
    "remember",
    "my name is",
    "i am",
    "i live",
    "i like",
    "i work",
    "what do you know",
    "do you remember",
    "what is my",
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

_GITHUB_KEYS = (
    "my repos",
    "my repositories",
    "my profile",
    "github",
    "my code",
)


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    low = haystack.lower()
    return any(n in low for n in needles)


def _fuzzy_contains(message: str, keywords: tuple, threshold: int = 80) -> bool:
    words = message.lower().split()
    for word in words:
        for keyword in keywords:
            if len(keyword.split()) == 1:
                if fuzz.ratio(word, keyword) >= threshold:
                    return True
            else:
                if fuzz.partial_ratio(message.lower(), keyword) >= threshold:
                    return True
    return False


def _is_calc(message: str) -> bool:
    """Calculator intent: math keywords, digit+operator patterns, or 'what is' with digits."""
    if _contains_any(message, _CALC_WORD_KEYS):
        return True
    if re.search(r"\d", message) and re.search(r"[+\-*/×÷]", message):
        return True
    low = message.lower()
    if "what is" in low and re.search(r"\d", message):
        return True
    return False


def _detect_tool(message: str) -> str:
    if _contains_any(message, _WEATHER_KEYS) or _fuzzy_contains(message, _WEATHER_KEYS, threshold=80):
        return "weather"
    if _contains_any(message, _MEMORY_KEYS) or _fuzzy_contains(message, _MEMORY_KEYS, threshold=85):
        return "memory"
    if _contains_any(message, _GITHUB_KEYS) or _fuzzy_contains(message, _GITHUB_KEYS, threshold=85):
        return "github"
    if _is_calc(message):
        return "calc"
    if _contains_any(message, _DEEP_SEARCH_KEYS) or _fuzzy_contains(message, _DEEP_SEARCH_KEYS, threshold=85):
        return "deep_search"
    if _contains_any(message, _SEARCH_KEYS) or _fuzzy_contains(message, _SEARCH_KEYS, threshold=85):
        return "search"
    return "none"


def route(message: str, active_tools: Dict[str, Any]) -> Dict[str, Any]:
    tool = _detect_tool(message)
    if tool == "none":
        return {"tool": "none", "auto_enabled": False}

    was_off = not bool(active_tools.get(tool, False))
    if was_off:
        active_tools[tool] = True

    return {"tool": tool, "auto_enabled": was_off}


if __name__ == "__main__":
    _all_on = {
        "search": True,
        "deep_search": True,
        "weather": True,
        "calc": True,
        "memory": True,
        "github": True,
    }
    _msgs = (
        "what is the weather in Philadelphia",
        "what should I wear today",
        "what is 25 times 4",
        "my name is Rakib",
        "search for AI news",
        "show my github repos",
        "hello how are you",
        "research quantum computing",
        "deep dive into neural networks",
        "explain in detail how transformers work",
        "wheather in philadelphia",
        "wat is the wether today",
        "serach for AI news",
        "calcualte 25 times 4",
    )
    for m in _msgs:
        tools = dict(_all_on)
        print(repr(m), "->", route(m, tools))
