_memory_store = {}

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

import tools.memory as _mem_module

_mem_module._FORCE_OFFLINE_STORE = True
_mem_module._OFFLINE_STORE = _memory_store


def _get_app_memory():
    return _memory_store


# ── Tool state ────────────────────────────────────────────────────────────────
_tool_state = {
    "search": True,
    "weather": True,
    "calc": True,
    "memory": True,
    "deep_search": True,
    "github": False,
}
_github_token = {"value": ""}

_BADGE_META = [
    ("search",      "🔍", "Web Search",  "#E3F2FD", "#1565C0"),
    ("weather",     "🌤", "Weather",     "#FFF3E0", "#E65100"),
    ("calc",        "🧮", "Calculator",  "#E8F5E9", "#2E7D32"),
    ("memory",      "🧠", "Memory",      "#F3E5F5", "#6A1B9A"),
    ("deep_search", "🔬", "Deep Search", "#E0F7FA", "#006064"),
    ("github",      "🐙", "GitHub",      "#EDE7F6", "#4527A0"),
]


def _badges_html() -> str:
    parts = []
    for key, emoji, name, bg, fg in _BADGE_META:
        if _tool_state.get(key):
            parts.append(
                f'<span style="display:inline-block;background:{bg};color:{fg};'
                f'font-size:0.78rem;font-weight:600;padding:3px 10px;'
                f'border-radius:999px;margin:0 4px 4px 0">{emoji} {name}</span>'
            )
    if not parts:
        return ""
    return (
        '<div style="display:flex;flex-wrap:wrap;padding:6px 0 2px 0">'
        + "".join(parts) + "</div>"
    )


def _title_from(hist):
    if not hist:
        return "Empty chat"
    first = hist[0]
    text = first[0] if isinstance(first, (list, tuple)) else (first.get("content") or "")
    text = str(text).strip().replace("\n", " ")
    return (text[:48] + "…") if len(text) > 48 else (text or "Empty chat")


def chat(user_message, history):
    if not (user_message or "").strip():
        return history, ""

    active = dict(_tool_state)
    routed = route(user_message, active)

    if routed.get("auto_enabled"):
        t = routed.get("tool")
        if t and t != "none":
            _tool_state[t] = True

    tool_name = routed["tool"]
    tool_result = ""

    if tool_name == "weather":       tool_result = run_weather(user_message)
    elif tool_name == "search":      tool_result = run_search(user_message)
    elif tool_name == "deep_search": tool_result = run_deep_search(user_message)
    elif tool_name == "calc":        tool_result = run_calculator(user_message)
    elif tool_name == "memory":      tool_result = run_memory(user_message)
    elif tool_name == "github":      tool_result = run_github(user_message, _github_token["value"])

    if tool_name == 'memory' and tool_result == 'Got it! I will remember that':
        reply = 'Got it! I will remember that.' + '\n\n*Tool used: 🧠 Memory*'
        history = list(history or [])
        history.append((user_message, reply))
        return history, ''

    if tool_name == 'memory' and tool_result.startswith('Here is what I know'):
        reply = tool_result + '\n\n*Tool used: 🧠 Memory*'
        history = list(history or [])
        history.append((user_message, reply))
        return history, ''

    full_prompt = build_prompt(user_message, tool_result, get_memory_context())

    auto_notice = ""
    if routed.get("auto_enabled") and tool_name not in (None, "none"):
        auto_notice = build_auto_enable_notice(tool_name)

    reply = generate_response(full_prompt)
    if auto_notice:
        reply = f"{auto_notice}\n\n{reply}"

    labels = {
        "weather": "🌤 Weather", "search": "🔍 Web Search",
        "deep_search": "🔬 Deep Search", "calc": "🧮 Calculator",
        "memory": "🧠 Memory", "github": "🐙 GitHub", "none": "No tool",
    }
    reply += f"\n\n*Tool used: {labels.get(tool_name, 'No tool')}*"

    history = list(history or [])
    history.append((user_message, reply))
    return history, ""


def new_chat(current_hist, archives):
    arch = list(archives or [])
    if current_hist:
        arch.insert(0, {
            "id": uuid.uuid4().hex,
            "title": _title_from(current_hist),
            "messages": copy.deepcopy(current_hist),
        })
    return [], arch


CSS = """
footer { display: none !important; }
#send-btn {
    min-width: 42px !important;
    max-width: 42px !important;
    height: 42px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    font-size: 1.1rem !important;
    background: #2563eb !important;
    color: white !important;
    border: none !important;
}
#send-btn:hover { background: #1d4ed8 !important; }
#msg-input textarea { border-radius: 20px !important; padding: 10px 16px !important; }
"""

with gr.Blocks(title="Mini ChatGPT Agent", theme=gr.themes.Soft(), css=CSS) as demo:

    archive_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=1, min_width=180):
            gr.Markdown("##### 🤖 Mini ChatGPT Agent")
            new_chat_btn = gr.Button("➕ New chat", size="sm")
            gr.Markdown("**Chats**")

            @gr.render(inputs=[archive_state])
            def render_history(archives):
                for conv in (archives or []):
                    b = gr.Button(
                        (conv.get("title") or "Untitled")[:60],
                        size="sm",
                        variant="secondary",
                    )
                    b.click(
                        lambda c=conv: c.get("messages") or [],
                        None, chatbot
                    )

        with gr.Column(scale=4):

            chatbot = gr.Chatbot(
                label="",
                show_label=False,
                height=480,
                bubble_full_width=False,
            )

            badges = gr.HTML(value=_badges_html())

            with gr.Row(equal_height=True):
                with gr.Column(scale=1, min_width=120):
                    with gr.Accordion("➕ Tools", open=False):
                        cb_search  = gr.Checkbox(label="🔍 Web Search",  value=True)
                        cb_weather = gr.Checkbox(label="🌤 Weather",      value=True)
                        cb_calc    = gr.Checkbox(label="🧮 Calculator",   value=True)
                        cb_memory  = gr.Checkbox(label="🧠 Memory",       value=True)
                        cb_deep    = gr.Checkbox(label="🔬 Deep Search",  value=True)
                        cb_github  = gr.Checkbox(label="🐙 GitHub",       value=False)
                        gh_token   = gr.Textbox(
                            label="GitHub Token",
                            type="password",
                            visible=False,
                        )

                msg = gr.Textbox(
                    placeholder="Message",
                    show_label=False,
                    scale=9,
                    container=False,
                    elem_id="msg-input",
                )
                send = gr.Button("↑", elem_id="send-btn", scale=1)

            clear = gr.Button("🗑 Clear chat", size="sm", variant="secondary")

    def _toggle(key, val):
        _tool_state[key] = val
        return gr.update(value=_badges_html())

    def _toggle_github(val):
        _tool_state["github"] = val
        return gr.update(visible=val), gr.update(value=_badges_html())

    cb_search.change(lambda v: _toggle("search", v),      cb_search,  badges)
    cb_weather.change(lambda v: _toggle("weather", v),    cb_weather, badges)
    cb_calc.change(lambda v: _toggle("calc", v),          cb_calc,    badges)
    cb_memory.change(lambda v: _toggle("memory", v),      cb_memory,  badges)
    cb_deep.change(lambda v: _toggle("deep_search", v),   cb_deep,    badges)
    cb_github.change(_toggle_github, cb_github, [gh_token, badges])
    gh_token.change(lambda v: _github_token.update({"value": v}), gh_token, None)

    new_chat_btn.click(new_chat, [chatbot, archive_state], [chatbot, archive_state])
    msg.submit(chat, [msg, chatbot], [chatbot, msg])
    send.click(chat,  [msg, chatbot], [chatbot, msg])
    clear.click(lambda: ([], ""), None, [chatbot, msg])


if __name__ == "__main__":
    demo.launch()
