import json
import uuid

import streamlit as st

from model import generate_response
from prompt_builder import build_auto_enable_notice, build_prompt
from router import route
from tools.calculator import run_calculator
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
    "tool_github": False,
}

_ROUTER_TO_SESSION = {
    "search": "tool_search",
    "weather": "tool_weather",
    "calc": "tool_calc",
    "memory": "tool_memory",
    "github": "tool_github",
}

_TOOL_USED_LABEL = {
    "weather": "Weather",
    "search": "Web Search",
    "calc": "Calculator",
    "memory": "Memory",
    "github": "GitHub",
    "none": "No tool",
}

_TOOL_CHIPS = (
    ("tool_search", "🔍", "Web Search"),
    ("tool_weather", "🌤", "Weather"),
    ("tool_calc", "🧮", "Calculator"),
    ("tool_memory", "🧠", "Memory"),
    ("tool_github", "🐙", "GitHub"),
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "archived_chats" not in st.session_state:
    st.session_state.archived_chats = []

if "github_token" not in st.session_state:
    st.session_state.github_token = ""

for key, default in _TOOL_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "auto_enabled_tool" in st.session_state:
    _enabled = st.session_state.pop("auto_enabled_tool")
    if _enabled and _enabled != "none":
        _session_key = _ROUTER_TO_SESSION.get(_enabled)
        if _session_key:
            st.session_state[_session_key] = True


def _messages_signature(messages: list) -> str:
    """Stable compare for deciding whether to archive before switching chats."""
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


# --- Sidebar: app name, new chat, history ---
with st.sidebar:
    st.markdown("### 🤖 Mini ChatGPT Agent")
    if st.button("➕ New chat", use_container_width=True, key="new_chat_btn"):
        _archive_current_if_nonempty()
        st.session_state.messages = []
        st.rerun()

    st.markdown("**Chats**")
    for conv in list(st.session_state.archived_chats):
        cid = conv["id"]
        title = conv.get("title") or "Untitled"
        if st.button(
            title,
            key=f"sidebar_chat_{cid}",
            use_container_width=True,
        ):
            cur = st.session_state.get("messages") or []
            target_sig = _messages_signature(conv.get("messages") or [])
            if cur and _messages_signature(cur) != target_sig:
                _archive_current_if_nonempty()
            st.session_state.messages = [dict(m) for m in (conv.get("messages") or [])]
            st.rerun()

# --- Main chat ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            _render_assistant_footer(message.get("tool_used", "none"))

# --- Tool chips (above chat input) ---
_chip_cols = st.columns(len(_TOOL_CHIPS), gap="small")
for i, (state_key, emoji, name) in enumerate(_TOOL_CHIPS):
    with _chip_cols[i]:
        is_on = st.session_state.get(state_key, _TOOL_DEFAULTS.get(state_key, False))
        if st.button(
            f"{emoji} {name}",
            key=f"chip_toggle_{state_key}",
            use_container_width=True,
            type="primary" if is_on else "secondary",
        ):
            st.session_state[state_key] = not is_on
            st.rerun()

if st.session_state.get("tool_github"):
    _tok_row = st.columns(len(_TOOL_CHIPS), gap="small")
    for _j in range(len(_TOOL_CHIPS) - 1):
        _tok_row[_j].empty()
    with _tok_row[-1]:
        st.text_input(
            "GitHub token",
            type="password",
            help="Personal access token for GitHub API",
            key="github_token",
        )

if prompt := st.chat_input("Message"):
    with st.chat_message("user"):
        st.markdown(prompt)

    active_tools = {
        "search": st.session_state["tool_search"],
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

    with st.chat_message("assistant"):
        st.markdown(content)
        _render_assistant_footer(tool_name)

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": content,
            "tool_used": tool_name,
        }
    )
