from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv
import os

from src.backend import BackendSession


load_dotenv()


def _default_config() -> Dict:
    return {
        "provider": os.getenv("LLM_PROVIDER", "groq"),
        "groq": {"api_key": "", "model": os.getenv("GROQ_MODEL", "")},
        "openai": {"api_key": "", "model": os.getenv("OPENAI_MODEL", "")},
        "anthropic": {"api_key": "", "model": os.getenv("ANTHROPIC_MODEL", "")},
        "generation": {
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
            "max_output_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
        },
    }


def ensure_session() -> BackendSession:
    if "backend" not in st.session_state:
        st.session_state.backend = BackendSession(_default_config())
    return st.session_state.backend


def reset_session() -> None:
    st.session_state.backend = BackendSession(_default_config())
    st.session_state.history = []


def save_upload(uploaded_file) -> str:
    dest_dir = Path("dataset/design/netlist")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"uploaded_{uploaded_file.name}"
    dest_path.write_bytes(uploaded_file.getbuffer())
    return str(dest_path)


st.set_page_config(page_title="LLM Netlist Assistant", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap');

:root {
    --bg: #0b0f14;
    --panel: #111823;
    --panel-soft: #162130;
    --text: #eaf1f6;
    --muted: #9db0c3;
    --accent: #00c2a8;
    --accent-2: #ffb454;
    --border: #253246;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', system-ui, sans-serif;
    color: var(--text);
}

.stApp {
    background: radial-gradient(circle at 12% 10%, #162132 0%, #0b0f14 45%, #090c10 100%);
}

.app-hero {
    background: linear-gradient(135deg, #162130 0%, #0f161f 60%, #1b2a3b 100%);
    border: 1px solid var(--border);
    padding: 20px 24px;
    border-radius: 18px;
    margin-bottom: 18px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
}

.app-hero h1 {
    margin: 0 0 6px 0;
    font-weight: 600;
    color: var(--text);
}

.app-hero p {
    margin: 0;
    color: var(--muted);
}

.mono {
    font-family: 'IBM Plex Mono', monospace;
}

section[data-testid="stSidebar"] {
    background-color: #0f151e;
    border-right: 1px solid var(--border);
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stFileUploader"] {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent);
}

div.stButton > button {
    background: linear-gradient(120deg, var(--accent) 0%, #19e5b8 100%);
    color: #091016;
    border: none;
    font-weight: 600;
}

div.stButton > button:hover {
    background: linear-gradient(120deg, #12d1b1 0%, #2af0c2 100%);
    color: #051014;
}

div[data-testid="stCodeBlock"] {
    background: var(--panel-soft);
    border: 1px solid var(--border);
}

div[data-testid="stMarkdownContainer"] strong {
    color: var(--accent-2);
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="app-hero">
  <h1>LLM-Assisted Netlist Exploration</h1>
  <p>Send natural-language EDA requests to your backend and track results in one session.</p>
</div>
""",
    unsafe_allow_html=True,
)

backend = ensure_session()
if "history" not in st.session_state:
    st.session_state.history = []

if st.sidebar.button("Reset testcase"):
    reset_session()
    st.sidebar.success("Session reset.")

left, right = st.columns([1, 2])

with left:
    st.subheader("Design file")
    uploaded = st.file_uploader("Upload .v", type=["v"])  # keep simple
    if uploaded and st.button("Save and load"):
        saved_path = save_upload(uploaded)
        result = backend.process_query(f"Read design {saved_path}")
        st.session_state.history.append(
            {
                "request": f"Read design {saved_path}",
                "message": result["message"],
                "block": result["block"],
                "command": result["command"],
            }
        )
        st.success(result["message"])

    st.subheader("Quick examples")
    st.code(
        """
This is testcase case8.
Read design dataset/design/netlist/sample.v
What is the max depth from a to out0?
Insert and gate on n1 with c
Write design case8_out.v
""".strip(),
        language="text",
    )

with right:
    st.subheader("Ask a question")
    with st.form("query_form", clear_on_submit=True):
        request = st.text_area("Natural-language request", height=120)
        submitted = st.form_submit_button("Submit")

    if submitted and request.strip():
        for line in [l.strip() for l in request.splitlines() if l.strip()]:
            result = backend.process_query(line)
            st.session_state.history.append(
                {
                    "request": line,
                    "message": result["message"],
                    "block": result["block"],
                    "command": result["command"],
                }
            )

    st.subheader("Latest response")
    if st.session_state.history:
        st.markdown(st.session_state.history[-1]["message"])
    else:
        st.info("No responses yet.")

    st.subheader("History")
    for item in st.session_state.history:
        st.markdown(f"**Request:** {item['request']}")
        st.markdown(f"**Response:** {item['message']}")
        st.caption(f"LLM command: {item['command']}")
        st.divider()


