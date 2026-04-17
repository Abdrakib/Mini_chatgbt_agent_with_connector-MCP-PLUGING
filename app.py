import json
import uuid

import streamlit as st

from model import generate_response
from prompt_builder import build_auto_enable_notice, build_prompt
from router import route
from tools.calculator import run_calculator
from tools.deep_search import run_deep_search
from tools.github import run_github
from tools.memory import get_memory_context, run_memory
from tools.search import run_search
from tools.weather import run_weather

st.set_page_config(
    page_title="Mini ChatGPT Agent",
    page_icon="🤖",
)

_TOOL_DEFAULTS = {
    "tool_search": True,
    "tool_weather": True,
    "tool_calc": True,
    "tool_memory": True,
    "tool_deep_search": True,
    "tool_github": False,
}

_ROUTER_TO_SESSION = {
    "search": "tool_search",
    "deep_search": "tool_deep_search",
    "weather": "tool_weather",
    "calc": "tool_calc",
    "memory": "tool_memory",
    "github": "tool_github",
}

_TOOL_USED_LABEL = {
    "weather": "Weather",
    "search": "Web Search",
    "deep_search": "Deep Search",
    "calc": "Calculator",
    "memory": "Memory",
    "github": "GitHub",
    "none": "No tool",
}

_BADGES = (
    ("tool_search", "🔍", "Web Search", "#E3F2FD", "#1565C0"),
    ("tool_weather", "🌤", "Weather", "#FFF3E0", "#E65100"),
    ("tool_calc", "🧮", "Calculator", "#E8F5E9", "#2E7D32"),
    ("tool_memory", "🧠", "Memory", "#F3E5F5", "#6A1B9A"),
    ("tool_deep_search", "🔬", "Deep Search", "#E0F7FA", "#006064"),
    ("tool_github", "🐙", "GitHub", "#EDE7F6", "#4527A0"),
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "archived_chats" not in st.session_state:
    st.session_state.archived_chats = []

if "github_token" not in st.session_state:
    st.session_state.github_token = ""

if "composer_draft" not in st.session_state:
    st.session_state.composer_draft = ""

for key, default in _TOOL_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "auto_enabled_tool" in st.session_state:
    _enabled = st.session_state.pop("auto_enabled_tool")
    if _enabled and _enabled != "none":
        _session_key = _ROUTER_TO_SESSION.get(_enabled)
        if _session_key:
            st.session_state[_session_key] = True


def chat_started() -> bool:
    return bool(st.session_state.get("messages"))


def inject_app_css(*, fixed_bottom_composer: bool) -> None:
    """Layout CSS: padded main when composer is fixed; bottom bar targets .fixed-composer-shell anchor + sibling container."""
    pad = "120px" if fixed_bottom_composer else "32px"
    bottom_rules = ""
    if fixed_bottom_composer:
        bottom_rules = """
        /* Anchor lives in first element-container; composer widgets live in the next element-container */
        section.main div.element-container:has(#bottom-composer-anchor) + div.element-container {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 1000 !important;
            width: 100% !important;
            max-width: min(900px, 100vw) !important;
            margin: 0 auto !important;
            box-sizing: border-box !important;
            background: var(--background-color, #ffffff) !important;
            border-top: 1px solid rgba(0, 0, 0, 0.08) !important;
            padding: 10px 12px calc(10px + env(safe-area-inset-bottom, 0px)) !important;
            box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.06) !important;
        }
        @media (max-width: 640px) {
            section.main div.element-container:has(#bottom-composer-anchor) + div.element-container {
                max-width: 100% !important;
                padding-left: max(8px, env(safe-area-inset-left, 0px)) !important;
                padding-right: max(8px, env(safe-area-inset-right, 0px)) !important;
            }
        }
        """
    composer_skin = """
/* One unified “chat bar”: bordered shell + soft textarea + compact send */
section.main [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTextArea"]) {
    border-radius: 999px !important;
    border: 1px solid rgba(49, 51, 63, 0.12) !important;
    background: rgba(49, 51, 63, 0.04) !important;
    padding: 6px 8px 6px 10px !important;
    box-shadow: 0 1px 2px rgba(49, 51, 63, 0.06) !important;
}
section.main [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTextArea"]) [data-testid="stHorizontalBlock"] {
    align-items: center !important;
}
section.main [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTextArea"]) [data-testid="stTextArea"] {
    margin-bottom: 0 !important;
}
section.main [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTextArea"]) textarea {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 10px 12px !important;
    min-height: 44px !important;
    line-height: 1.45 !important;
    resize: none !important;
}
section.main [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTextArea"]) [data-testid="column"]:has(button) {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
section.main [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTextArea"]) [data-testid="column"]:has(button) button {
    border-radius: 999px !important;
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    min-width: 36px !important;
    max-height: 36px !important;
    padding: 0 !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
"""
    st.markdown(
        f"""
<style>
section.main .block-container {{
    padding-bottom: {pad} !important;
    max-width: 900px !important;
    margin-left: auto !important;
    margin-right: auto !important;
}}
{bottom_rules}
{composer_skin}
</style>
""",
        unsafe_allow_html=True,
    )


def _messages_signature(messages: list) -> str:
    try:
        return json.dumps(
            [
                {"role": m.get("role"), "content": m.get("content"), "tool_used": m.get("tool_used")}
                for m in messages
            ],
            sort_keys=True,
        )
    except (TypeError, ValueError):
        return ""


def _first_user_title(messages: list, max_len: int = 48) -> str:
    for m in messages:
        if m.get("role") == "user":
            t = (m.get("content") or "").strip().replace("\n", " ")
            if not t:
                continue
            return t[:max_len] + ("…" if len(t) > max_len else "")
    return "Empty chat"


def _archive_current_if_nonempty() -> None:
    msgs = st.session_state.get("messages") or []
    if not msgs:
        return
    st.session_state.archived_chats.insert(
        0,
        {
            "id": str(uuid.uuid4()),
            "title": _first_user_title(msgs),
            "messages": [dict(m) for m in msgs],
        },
    )


def _active_tools_label() -> str:
    labels = []
    if st.session_state.get("tool_search", True):
        labels.append("Web Search")
    if st.session_state.get("tool_weather", True):
        labels.append("Weather")
    if st.session_state.get("tool_calc", True):
        labels.append("Calculator")
    if st.session_state.get("tool_memory", True):
        labels.append("Memory")
    if st.session_state.get("tool_deep_search", True):
        labels.append("Deep Search")
    if st.session_state.get("tool_github", False):
        labels.append("GitHub")
    return ", ".join(labels) if labels else "None"


def _tool_used_line(tool_key: str) -> str:
    k = tool_key or "none"
    return _TOOL_USED_LABEL.get(k, k.title() if k else "No tool")


def _render_assistant_footer(tool_key: str) -> None:
    st.markdown(
        f'<p style="color:#888;font-size:0.85em;margin-top:0.5rem;">'
        f"Tool used: {_tool_used_line(tool_key)}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:#888;font-size:0.85em;">'
        f"Tools on: {_active_tools_label()}</p>",
        unsafe_allow_html=True,
    )


def render_tools_popover() -> None:
    with st.popover("➕"):
        st.markdown("**Tools**")
        st.checkbox("🔍 Web Search", key="tool_search")
        st.checkbox("🌤 Weather", key="tool_weather")
        st.checkbox("🧮 Calculator", key="tool_calc")
        st.checkbox("🧠 Memory", key="tool_memory")
        st.checkbox("🔬 Deep Search", key="tool_deep_search")
        st.checkbox("🐙 GitHub", key="tool_github")
        if st.session_state.get("tool_github"):
            st.text_input("GitHub token", type="password", key="github_token")


def render_welcome_screen() -> None:
    st.markdown(
        """
        <div style="text-align:center; padding: 80px 20px 20px 20px; color: #888;">
        <h2>🤖 Mini ChatGPT Agent</h2>
        <p>Powered by Qwen2.5 · Ask me anything</p>
        <p style="font-size:0.85em">Use the ➕ button to enable tools</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        col_plus, col_input = st.columns([1, 11])
        with col_plus:
            render_tools_popover()
        with col_input:
            ta, btn = st.columns([6, 1])
            with ta:
                st.text_area(
                    "Message",
                    key="composer_draft",
                    height=88,
                    placeholder="Message…",
                    label_visibility="collapsed",
                )
            with btn:
                if st.button("↑", type="primary", key="send_msg", help="Send", use_container_width=False):
                    handle_send()


def render_tool_badges() -> None:
    parts = []
    for state_key, emoji, name, bg, fg in _BADGES:
        if st.session_state.get(state_key, _TOOL_DEFAULTS.get(state_key, False)):
            parts.append(
                f'<span style="display:inline-block;background:{bg};color:{fg};'
                f"font-size:0.78rem;font-weight:600;padding:3px 10px;border-radius:999px;"
                f'margin:0 6px 6px 0;white-space:nowrap">{emoji} {name}</span>'
            )
    if parts:
        st.markdown(
            '<div style="display:flex;flex-wrap:wrap;margin-bottom:4px">'
            + "".join(parts)
            + "</div>",
            unsafe_allow_html=True,
        )


def render_messages() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                _render_assistant_footer(message.get("tool_used", "none"))


def render_bottom_composer() -> None:
    """Fixed bar is styled via #bottom-composer-anchor + next element-container (see inject_app_css)."""
    st.markdown(
        '<div id="bottom-composer-anchor" class="fixed-composer-shell" '
        'style="height:0;margin:0;padding:0;overflow:hidden;" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    with st.container():
        with st.container(border=True):
            col_plus, col_mid = st.columns([1, 11])
            with col_plus:
                render_tools_popover()
            with col_mid:
                ta, btn = st.columns([6, 1])
                with ta:
                    st.text_area(
                        "Message",
                        key="composer_draft",
                        height=72,
                        placeholder="Message…",
                        label_visibility="collapsed",
                    )
                with btn:
                    if st.button("↑", type="primary", key="send_msg", help="Send", use_container_width=False):
                        handle_send()


def process_user_message(prompt: str) -> None:
    active_tools = {
        "search": st.session_state["tool_search"],
        "deep_search": st.session_state["tool_deep_search"],
        "weather": st.session_state["tool_weather"],
        "calc": st.session_state["tool_calc"],
        "memory": st.session_state["tool_memory"],
        "github": st.session_state["tool_github"],
    }

    routed = route(prompt, active_tools)
    if routed.get("auto_enabled"):
        st.session_state["auto_enabled_tool"] = routed["tool"]

    tool_name = routed["tool"]
    tool_result = ""

    if tool_name == "weather":
        tool_result = run_weather(prompt)
    elif tool_name == "search":
        tool_result = run_search(prompt)
    elif tool_name == "deep_search":
        tool_result = run_deep_search(prompt)
    elif tool_name == "calc":
        tool_result = run_calculator(prompt)
    elif tool_name == "memory":
        tool_result = run_memory(prompt)
    elif tool_name == "github":
        tool_result = run_github(prompt, st.session_state.get("github_token", ""))
    elif tool_name == "none":
        tool_result = ""

    memory_context = get_memory_context()
    full_prompt = build_prompt(prompt, tool_result, memory_context)

    auto_notice = ""
    if routed.get("auto_enabled") and routed.get("tool") not in (None, "none"):
        auto_notice = build_auto_enable_notice(routed["tool"])

    with st.spinner("Thinking..."):
        reply = generate_response(full_prompt)

    body_parts = []
    if auto_notice:
        body_parts.append(auto_notice)
    body_parts.append(reply)
    content = "\n\n".join(body_parts)

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": content,
            "tool_used": tool_name,
        }
    )


def handle_send() -> None:
    """Queue composer text for processing on the next script run (avoids mixing welcome + chat UI)."""
    t = (st.session_state.get("composer_draft") or "").strip()
    if t:
        st.session_state.pending_send_text = t
    st.rerun()


def process_pending_send() -> None:
    if "pending_send_text" not in st.session_state:
        return
    text = st.session_state.pop("pending_send_text")
    prompt = (text or "").strip()
    st.session_state.composer_draft = ""
    if prompt:
        process_user_message(prompt)
    st.rerun()


# --- Sidebar ---
st.sidebar.markdown("##### Mini ChatGPT Agent")
if st.sidebar.button("➕ New chat", use_container_width=True, key="new_chat_btn"):
    _archive_current_if_nonempty()
    st.session_state.messages = []
    st.session_state.composer_draft = ""
    st.session_state.pop("pending_send_text", None)
    st.rerun()

st.sidebar.markdown("**Chats**")
for conv in list(st.session_state.archived_chats):
    cid = conv["id"]
    title = conv.get("title") or "Untitled"
    if st.sidebar.button(
        title,
        key=f"sidebar_chat_{cid}",
        use_container_width=True,
    ):
        cur = st.session_state.get("messages") or []
        target_sig = _messages_signature(conv.get("messages") or [])
        if cur and _messages_signature(cur) != target_sig:
            _archive_current_if_nonempty()
        st.session_state.messages = [dict(m) for m in (conv.get("messages") or [])]
        st.session_state.composer_draft = ""
        st.rerun()

process_pending_send()

started = chat_started()
inject_app_css(fixed_bottom_composer=started)

if not started:
    render_welcome_screen()
else:
    render_messages()
    render_tool_badges()
    render_bottom_composer()
