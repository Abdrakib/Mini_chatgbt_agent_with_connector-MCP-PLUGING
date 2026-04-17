import copy
import uuid

import gradio as gr

from model import generate_response
from prompt_builder import build_auto_enable_notice, build_prompt
from router import route
from tools.calculator import run_calculator
from tools.deep_search import run_deep_search
from tools.github import run_github
from tools.memory import get_memory_context, run_memory
from tools.search import run_search
from tools.weather import run_weather

# ── Tool state (module-level so it persists per session) ──────────────────────
_tool_state = {
    "search": True,
    "weather": True,
    "calc": True,
    "memory": True,
    "deep_search": True,
    "github": False,
}

_github_token = {"value": ""}

_BADGE_STYLE = (
    ("search", "🔍", "Web Search", "#E3F2FD", "#1565C0"),
    ("weather", "🌤", "Weather", "#FFF3E0", "#E65100"),
    ("calc", "🧮", "Calculator", "#E8F5E9", "#2E7D32"),
    ("memory", "🧠", "Memory", "#F3E5F5", "#6A1B9A"),
    ("deep_search", "🔬", "Deep Search", "#E0F7FA", "#006064"),
    ("github", "🐙", "GitHub", "#EDE7F6", "#4527A0"),
)


def _badges_html() -> str:
    parts = []
    for key, emoji, name, bg, fg in _BADGE_STYLE:
        if _tool_state.get(key):
            parts.append(
                f'<span style="display:inline-block;background:{bg};color:{fg};'
                f"font-size:0.78rem;font-weight:600;padding:3px 10px;border-radius:999px;"
                f'margin:0 6px 6px 0;white-space:nowrap">{emoji} {name}</span>'
            )
    if not parts:
        return "<div style='min-height:1.25rem'></div>"
    return (
        '<div style="display:flex;flex-wrap:wrap;align-items:center;margin:4px 0 8px 0">'
        + "".join(parts)
        + "</div>"
    )


def _title_from_history(hist: list) -> str:
    if not hist:
        return "Empty chat"
    first = hist[0]
    text = ""
    if isinstance(first, dict):
        text = (first.get("content") or "").strip()
    elif isinstance(first, (list, tuple)) and len(first) >= 1:
        text = str(first[0] or "").strip()
    text = text.replace("\n", " ")
    if not text:
        return "Empty chat"
    return text[:48] + ("…" if len(text) > 48 else "")


# ── Core chat function ─────────────────────────────────────────────────────────
def chat(user_message: str, history: list) -> tuple:
    if not user_message.strip():
        return history, ""

    active_tools = dict(_tool_state)
    routed = route(user_message, active_tools)

    if routed.get("auto_enabled"):
        tool = routed.get("tool")
        if tool and tool != "none":
            _tool_state[tool] = True

    tool_name = routed["tool"]
    tool_result = ""

    if tool_name == "weather":
        tool_result = run_weather(user_message)
    elif tool_name == "search":
        tool_result = run_search(user_message)
    elif tool_name == "deep_search":
        tool_result = run_deep_search(user_message)
    elif tool_name == "calc":
        tool_result = run_calculator(user_message)
    elif tool_name == "memory":
        tool_result = run_memory(user_message)
    elif tool_name == "github":
        tool_result = run_github(user_message, _github_token["value"])
    elif tool_name == "none":
        tool_result = ""

    memory_context = get_memory_context()
    full_prompt = build_prompt(user_message, tool_result, memory_context)

    auto_notice = ""
    if routed.get("auto_enabled") and tool_name not in (None, "none"):
        auto_notice = build_auto_enable_notice(tool_name)

    reply = generate_response(full_prompt)

    if auto_notice:
        reply = f"{auto_notice}\n\n{reply}"

    tool_label = {
        "weather": "🌤 Weather",
        "search": "🔍 Web Search",
        "deep_search": "🔬 Deep Search",
        "calc": "🧮 Calculator",
        "memory": "🧠 Memory",
        "github": "🐙 GitHub",
        "none": "No tool",
    }.get(tool_name, "No tool")

    reply += f"\n\n*Tool used: {tool_label}*"

    history = list(history or [])
    history.append((user_message, reply))
    return history, ""


def _on_new_chat(current_hist: list, archives: list):
    arch = list(archives or [])
    if current_hist:
        arch.insert(
            0,
            {
                "id": uuid.uuid4().hex,
                "title": _title_from_history(current_hist),
                "messages": copy.deepcopy(current_hist),
            },
        )
    return [], arch


def _on_github_toggle(val: bool):
    _tool_state["github"] = val
    return gr.update(visible=val), gr.update(value=_badges_html())


def _set_tool(key: str, val: bool):
    _tool_state[key] = val
    return gr.update(value=_badges_html())


def _on_token_change(val: str):
    _github_token["value"] = val or ""


with gr.Blocks(
    title="Mini ChatGPT Agent",
    theme=gr.themes.Soft(),
    css="""
    footer { display: none !important; }
    """,
) as demo:
    # Past conversations (titles + message lists). Live transcript is the Chatbot value.
    archive_state = gr.State([])

    # Render chatbot after sidebar so @gr.render archive buttons can wire .click → chatbot.
    chatbot = gr.Chatbot(
        label="",
        show_label=False,
        bubble_full_width=False,
        height=500,
        render=False,
    )

    with gr.Row():
        with gr.Column(scale=1, min_width=200):
            gr.Markdown("##### 🤖 Mini ChatGPT Agent")
            new_chat_btn = gr.Button("➕ New chat")
            gr.Markdown("**Chats**")

            @gr.render(inputs=[archive_state])
            def _render_archive_list(archives: list):
                for conv in archives or []:
                    title = (conv.get("title") or "Untitled")[:80]
                    b = gr.Button(title, size="sm")
                    b.click(lambda c=conv: c.get("messages") or [], None, chatbot)

        with gr.Column(scale=4):
            chatbot.render()
            badges_html = gr.HTML(value=_badges_html())

            # Gradio has no gr.Popover in current releases; Accordion matches a compact tool tray.
            with gr.Row():
                with gr.Column(scale=1, min_width=56):
                    with gr.Accordion("➕", open=False):
                        cb_search = gr.Checkbox(label="🔍 Web Search", value=True)
                        cb_weather = gr.Checkbox(label="🌤 Weather", value=True)
                        cb_calc = gr.Checkbox(label="🧮 Calculator", value=True)
                        cb_memory = gr.Checkbox(label="🧠 Memory", value=True)
                        cb_deep = gr.Checkbox(label="🔬 Deep Search", value=True)
                        cb_github = gr.Checkbox(label="🐙 GitHub", value=False)
                        github_token = gr.Textbox(
                            label="GitHub token",
                            type="password",
                            visible=False,
                            show_label=True,
                        )

                msg = gr.Textbox(
                    placeholder="Message…",
                    show_label=False,
                    lines=1,
                    scale=11,
                    container=False,
                )
                send_btn = gr.Button("↑", variant="secondary", scale=1)

            clear_btn = gr.Button("🗑 Clear chat", size="sm", variant="secondary")

    cb_search.change(lambda v: _set_tool("search", v), cb_search, badges_html)
    cb_weather.change(lambda v: _set_tool("weather", v), cb_weather, badges_html)
    cb_calc.change(lambda v: _set_tool("calc", v), cb_calc, badges_html)
    cb_memory.change(lambda v: _set_tool("memory", v), cb_memory, badges_html)
    cb_deep.change(lambda v: _set_tool("deep_search", v), cb_deep, badges_html)
    cb_github.change(_on_github_toggle, cb_github, [github_token, badges_html])
    github_token.change(_on_token_change, github_token, None)

    new_chat_btn.click(_on_new_chat, [chatbot, archive_state], [chatbot, archive_state])

    msg.submit(chat, [msg, chatbot], [chatbot, msg])
    send_btn.click(chat, [msg, chatbot], [chatbot, msg])
    clear_btn.click(lambda: ([], ""), None, [chatbot, msg])


if __name__ == "__main__":
    demo.launch()
