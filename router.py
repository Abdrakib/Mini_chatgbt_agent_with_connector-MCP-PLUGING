import re
from typing import Any, Dict

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
    """
    First-match routing. Order: memory → github → weather → calc → deep_search → search.
    Calc is checked before search so expressions like 'what is 5 + 3' prefer calc.
    Deep search is checked before generic search so 'deep search' does not match only 'search'.
    """
    if _contains_any(message, _MEMORY_KEYS):
        return "memory"
    if _contains_any(message, _GITHUB_KEYS):
        return "github"
    if _contains_any(message, _WEATHER_KEYS):
        return "weather"
    if _is_calc(message):
        return "calc"
    if _contains_any(message, _DEEP_SEARCH_KEYS):
        return "deep_search"
    if _contains_any(message, _SEARCH_KEYS):
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
    )
    for m in _msgs:
        tools = dict(_all_on)
        print(repr(m), "->", route(m, tools))
