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
    "search":      True,
    "weather":     True,
    "calc":        True,
    "memory":      True,
    "deep_search": True,
    "github":      False,
}

_github_token = {"value": ""}


# ── Core chat function ─────────────────────────────────────────────────────────
def chat(user_message: str, history: list) -> tuple:
    if not user_message.strip():
        return history, ""

    active_tools = dict(_tool_state)
    routed = route(user_message, active_tools)

    # Update tool state if auto-enabled
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

    memory_context = get_memory_context()
    full_prompt = build_prompt(user_message, tool_result, memory_context)

    auto_notice = ""
    if routed.get("auto_enabled") and tool_name not in (None, "none"):
        auto_notice = build_auto_enable_notice(tool_name)

    reply = generate_response(full_prompt)

    if auto_notice:
        reply = f"{auto_notice}\n\n{reply}"

    # Add tool info footer
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

    history.append((user_message, reply))
    return history, ""


# ── Tool toggle functions ──────────────────────────────────────────────────────
def toggle_search(val):   _tool_state["search"] = val
def toggle_weather(val):  _tool_state["weather"] = val
def toggle_calc(val):     _tool_state["calc"] = val
def toggle_memory(val):   _tool_state["memory"] = val
def toggle_deep(val):     _tool_state["deep_search"] = val
def toggle_github(val):   _tool_state["github"] = val
def update_token(val):    _github_token["value"] = val


# ── Gradio UI ──────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="Mini ChatGPT Agent",
    theme=gr.themes.Soft(),
    css="""
    #chatbot { height: 500px; }
    .tool-row { gap: 8px; }
    footer { display: none !important; }
    """,
) as demo:

    gr.Markdown("# 🤖 Mini ChatGPT Agent")
    gr.Markdown("*Powered by Qwen2.5 · Web Search · Weather · Calculator · Memory · Deep Search · GitHub*")

    with gr.Row():
        # ── Sidebar ──────────────────────────────────────────────────────────
        with gr.Column(scale=1, min_width=200):
            gr.Markdown("### 🛠 Tools")

            cb_search = gr.Checkbox(label="🔍 Web Search",  value=True)
            cb_weather = gr.Checkbox(label="🌤 Weather",     value=True)
            cb_calc    = gr.Checkbox(label="🧮 Calculator",  value=True)
            cb_memory  = gr.Checkbox(label="🧠 Memory",      value=True)
            cb_deep    = gr.Checkbox(label="🔬 Deep Search", value=True)
            cb_github  = gr.Checkbox(label="🐙 GitHub",      value=False)

            github_token = gr.Textbox(
                label="GitHub Token",
                placeholder="Paste your token here",
                type="password",
                visible=False,
            )

            cb_search.change(toggle_search,  cb_search,  None)
            cb_weather.change(toggle_weather, cb_weather, None)
            cb_calc.change(toggle_calc,    cb_calc,    None)
            cb_memory.change(toggle_memory,  cb_memory,  None)
            cb_deep.change(toggle_deep,    cb_deep,    None)
            cb_github.change(toggle_github,  cb_github,  None)
            cb_github.change(lambda v: gr.update(visible=v), cb_github, github_token)
            github_token.change(update_token, github_token, None)

        # ── Chat area ─────────────────────────────────────────────────────────
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                label="",
                show_label=False,
                bubble_full_width=False,
            )

            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Message",
                    show_label=False,
                    scale=9,
                    container=False,
                )
                send_btn = gr.Button("↑", scale=1, variant="primary")

            clear_btn = gr.Button("🗑 Clear chat", size="sm", variant="secondary")

    # ── Event handlers ────────────────────────────────────────────────────────
    msg.submit(chat, [msg, chatbot], [chatbot, msg])
    send_btn.click(chat, [msg, chatbot], [chatbot, msg])
    clear_btn.click(lambda: ([], ""), None, [chatbot, msg])


if __name__ == "__main__":
    demo.launch()
