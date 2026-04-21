_TOOL_DISPLAY = {
    "weather": "Weather",
    "search": "Search",
    "deep_search": "Deep Search",
    "calc": "Calculator",
    "memory": "Memory",
    "github": "GitHub",
}


def build_prompt(message: str, tool_result: str, memory_context: str) -> str:
    parts = []
    if memory_context:
        parts.append(f"Facts about the user: {memory_context}")
    if tool_result:
        parts.append(f"Use this information to answer: {tool_result}")
        parts.append(f"Question: {message}")
        parts.append(
            "Answer using ONLY the information provided above. Do not add, change or interpret any values. Use the exact words from the information."
        )
    else:
        parts.append(f"Question: {message}")
        parts.append("Give a short direct answer in 1-2 sentences.")
    return "\n".join(parts)


def build_auto_enable_notice(tool_name: str) -> str:
    key = (tool_name or "").strip().lower()
    label = _TOOL_DISPLAY.get(key, tool_name.strip().title() if tool_name else "tool")
    return (
        f"I noticed your {label} tool was off. I turned it on to help you better 🔧"
    )


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    print("--- build_prompt: tool + memory ---")
    print(
        build_prompt(
            "What should I pack?",
            "Philadelphia: Sunny, 72F",
            "name is Rakib; city is Philadelphia",
        )
    )
    print()
    print("--- build_prompt: tool only ---")
    print(
        build_prompt(
            "Summarize this.",
            "Search result line 1\nSearch result line 2",
            "",
        )
    )
    print()
    print("--- build_prompt: no tool, no memory ---")
    print(build_prompt("Hello there!", "", ""))
    print()
    print("--- build_auto_enable_notice ---")
    print(build_auto_enable_notice("weather"))
