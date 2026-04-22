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

_tool_state = {
    "search": True,
    "weather": True,
    "calc": True,
    "memory": True,
    "deep_search": True,
    "github": False,
}
_github_token = {"value": ""}

def _title_from(hist):
    if not hist:
        return "New chat"
    first = hist[0]
    if isinstance(first, dict):
        text = str(first.get("content") or "").strip().replace("\n", " ")
    else:
        text = first[0] if isinstance(first, (list, tuple)) else (first.get("content") or "")
        text = str(text).strip().replace("\n", " ")
    return (text[:45] + "…") if len(text) > 45 else (text or "New chat")

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

    if tool_name == "memory" and tool_result == "Got it! I will remember that":
        reply = "✅ Got it! I will remember that.\n\n*Tool used: 🧠 Memory*"
        history = list(history or [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return history, ""

    if tool_name == "memory" and tool_result.startswith("Here is what I know"):
        reply = tool_result + "\n\n*Tool used: 🧠 Memory*"
        history = list(history or [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return history, ""

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
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap');

* { box-sizing: border-box; }

body, .gradio-container {
    background: #FFFEF8 !important;
    color: #4A3200 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

footer { display: none !important; }

.block-container {
    padding: 8px !important;
    margin: 0 auto !important;
    max-width: 100% !important;
}

/* Sidebar */
.sidebar-col {
    background: #FFFBF0 !important;
    border-right: 1.5px solid #F0DDA0 !important;
    min-height: 100vh;
    padding: 20px 12px !important;
}

.app-title {
    font-size: 0.88rem;
    font-weight: 600;
    color: #4A3200;
    padding: 6px 6px 14px 6px;
    border-bottom: 1px solid #F0DDA0;
    margin-bottom: 12px;
}

#chatbot {
    background: #FFFEF8 !important;
    border: none !important;
    flex: 1 !important;
}

#chatbot .wrap {
    min-height: 200px !important;
}

/* User bubble */
#chatbot .message-wrap .user {
    background: #D97706 !important;
    color: #ffffff !important;
    border-radius: 18px 18px 3px 18px !important;
    padding: 10px 14px !important;
    margin-left: auto !important;
    border: none !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.93rem !important;
    line-height: 1.6 !important;
}

/* Bot bubble */
#chatbot .message-wrap .bot {
    background: #FEF9E7 !important;
    color: #4A3200 !important;
    border-radius: 18px 18px 18px 3px !important;
    padding: 10px 14px !important;
    border: 1px solid #F0DDA0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.93rem !important;
    line-height: 1.6 !important;
}

/* Input */
#msg-input textarea {
    background: #ffffff !important;
    border: 1.5px solid #F0DDA0 !important;
    border-radius: 12px !important;
    color: #4A3200 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.93rem !important;
    padding: 13px 16px !important;
    transition: border-color 0.2s !important;
}

#msg-input textarea:focus {
    border-color: #D97706 !important;
    box-shadow: 0 0 0 3px #D9770618 !important;
    outline: none !important;
}

#msg-input textarea::placeholder { color: #B8922A !important; }

/* Send button */
#send-btn {
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    border-radius: 10px !important;
    padding: 0 !important;
    font-size: 1rem !important;
    background: #D97706 !important;
    color: white !important;
    border: none !important;
    transition: all 0.2s !important;
}

#send-btn:hover {
    background: #B45309 !important;
    transform: scale(1.04) !important;
}

/* New chat button */
.new-chat-btn button {
    background: #FEF9E7 !important;
    border: 1.5px solid #F0DDA0 !important;
    color: #4A3200 !important;
    border-radius: 10px !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
    width: 100% !important;
}

.new-chat-btn button:hover {
    background: #F0DDA0 !important;
    border-color: #D97706 !important;
}

/* History buttons */
.history-btn button {
    background: transparent !important;
    border: none !important;
    color: #8A6A1A !important;
    text-align: left !important;
    font-size: 0.81rem !important;
    padding: 7px 8px !important;
    border-radius: 8px !important;
    transition: all 0.15s !important;
    width: 100% !important;
}

.history-btn button:hover {
    background: #F0DDA055 !important;
    color: #4A3200 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #FFFBF0; }
::-webkit-scrollbar-thumb { background: #F0DDA0; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #D97706; }

.gradio-container > .main > .wrap > .padding {
    padding-bottom: 0 !important;
}
div.svelte-1gfkn6j {
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
}

.gradio-container {
    padding-bottom: 0 !important;
}

.main {
    padding-bottom: 0 !important;
}

.wrap.svelte-1gfkn6j {
    gap: 0 !important;
}
"""

WELCOME_HTML = """
<div style='text-align:center;padding:100px 20px 20px 20px'>
    <h2 style='font-size:1.6rem;font-weight:600;color:#4A3200;
               margin:0 0 6px 0;font-family:"Plus Jakarta Sans",sans-serif;
               letter-spacing:-0.02em'>
        Welcome to Mini ChatGPT Agent
    </h2>
    <p style='color:#B8922A;font-size:0.88rem;margin:0;
              font-family:"Plus Jakarta Sans",sans-serif'>
        Ask me anything
    </p>
</div>
"""

with gr.Blocks(title="Mini ChatGPT Agent", css=CSS) as demo:

    archive_state = gr.State([])

    with gr.Row():

        with gr.Column(scale=1, min_width=220, elem_classes=["sidebar-col"]):
            gr.HTML('<div class="app-title">🤖 Mini ChatGPT Agent</div>')

            new_chat_btn = gr.Button(
                "＋  New chat",
                elem_classes=["new-chat-btn"],
                size="sm"
            )

            gr.HTML('<div style="color:#B8922A;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;padding:14px 6px 6px 6px">Recent</div>')

            @gr.render(inputs=[archive_state])
            def render_history(archives):
                for conv in (archives or []):
                    b = gr.Button(
                        "💬  " + (conv.get("title") or "Untitled")[:36],
                        elem_classes=["history-btn"],
                        size="sm",
                    )
                    b.click(
                        lambda c=conv: c.get("messages") or [],
                        None, chatbot
                    )

        with gr.Column(scale=5):

            chatbot = gr.Chatbot(
                elem_id="chatbot",
                label="",
                show_label=False,
                height=480,
                bubble_full_width=False,
                placeholder=WELCOME_HTML,
                type="messages",
            )

            with gr.Row(equal_height=True):
                with gr.Column(scale=1, min_width=110):
                    with gr.Accordion("⚡ Tools", open=False):
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
                            placeholder="ghp_xxxxxxxxxxxx",
                        )

                msg = gr.Textbox(
                    placeholder="Message Mini ChatGPT Agent...",
                    show_label=False,
                    scale=9,
                    container=False,
                    elem_id="msg-input",
                )
                send = gr.Button("↑", elem_id="send-btn", scale=1)

    def _toggle(key, val):
        _tool_state[key] = val

    def _toggle_github(val):
        _tool_state["github"] = val
        return gr.update(visible=val)

    cb_search.change(lambda v: _toggle("search", v),    cb_search,  None)
    cb_weather.change(lambda v: _toggle("weather", v),  cb_weather, None)
    cb_calc.change(lambda v: _toggle("calc", v),        cb_calc,    None)
    cb_memory.change(lambda v: _toggle("memory", v),    cb_memory,  None)
    cb_deep.change(lambda v: _toggle("deep_search", v), cb_deep,    None)
    cb_github.change(_toggle_github, cb_github, gh_token)
    gh_token.change(lambda v: _github_token.update({"value": v}), gh_token, None)

    new_chat_btn.click(new_chat, [chatbot, archive_state], [chatbot, archive_state])
    msg.submit(chat, [msg, chatbot], [chatbot, msg])
    send.click(chat, [msg, chatbot], [chatbot, msg])

if __name__ == "__main__":
    demo.launch()
