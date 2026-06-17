import os
from datetime import datetime, timedelta, timezone

import jwt
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from audit import log_login, log_query
from guardrails import (
    _REDIRECT_MESSAGE,
    check_input,
    check_output_safety,
    is_irrelevant_response,
    redact_pii,
    requires_human_approval,
)
from main import build_chain
from user_store import authenticate, init_db
from vector import get_retriever_for_role, initialize_vector_store

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="MedCare Document Assistant",
    page_icon="🏥",
    layout="centered",
)

init_db()  # ensure table exists on every startup


def _generate_token(identity: dict) -> str:
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not set.")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": identity["user_id"],
        "email": identity["email"],
        "role": identity["role"],
        "iat": now,
        "exp": now + timedelta(hours=8),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


# ------------------------------------------------------------------
# Session state defaults
# ------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "identity" not in st.session_state:
    st.session_state.identity = None
if "messages" not in st.session_state:
    st.session_state.messages = []


# ------------------------------------------------------------------
# Cached backend — initialised once per role across reruns
# ------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading documents into vector store…")
def load_backend(role: str):
    initialize_vector_store()
    retriever = get_retriever_for_role(role)
    chain = build_chain(retriever)
    return chain, retriever


# ------------------------------------------------------------------
# Login screen
# ------------------------------------------------------------------
def show_login():
    st.title("MedCare Document Assistant")
    st.markdown("Sign in with your company credentials.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("Please enter your username and password.")
            return

        identity = authenticate(username, password)
        if not identity:
            st.error("Invalid username or password.")
            return

        try:
            _generate_token(identity)  # validates JWT_SECRET_KEY is set
        except RuntimeError as e:
            st.error(str(e))
            return

        st.session_state.authenticated = True
        st.session_state.identity = identity
        log_login(identity["user_id"], identity["role"], identity["email"])
        st.rerun()


# ------------------------------------------------------------------
# Chat screen
# ------------------------------------------------------------------
def show_chat():
    identity = st.session_state.identity
    chain, retriever = load_backend(identity["role"])

    with st.sidebar:
        st.markdown(f"**User:** {identity['user_id']}")
        st.markdown(f"**Role:** `{identity['role']}`")
        st.markdown(f"**Email:** {identity['email']}")
        st.divider()
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        if st.button("Sign out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.identity = None
            st.session_state.messages = []
            st.rerun()

    st.title("MedCare Document Assistant")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Ask a question about company documents…")
    if not question:
        return

    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    # Layer 1: Deterministic input filter
    valid, rejection = check_input(question)
    if not valid:
        with st.chat_message("assistant"):
            st.warning(rejection)
        st.session_state.messages.append({"role": "assistant", "content": rejection})
        return

    # Layer 2 (input): PII redaction
    question, pii_in = redact_pii(question, output=False)
    if pii_in:
        st.info(f"PII removed from your query: {', '.join(pii_in)}")

    # Layer 3: Sensitive query notice
    if requires_human_approval(question):
        st.warning("This query accesses sensitive information. Proceeding as you are authorised for this role.")

    # Generate answer
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            retrieved_docs = retriever.invoke(question)
            log_query(identity["user_id"], identity["role"], question, retrieved_docs)
            answer = chain.invoke(question)

        if is_irrelevant_response(answer):
            answer = _REDIRECT_MESSAGE
        else:
            answer, pii_out = redact_pii(answer, output=True)
            if pii_out:
                st.info(f"PII removed from response: {', '.join(pii_out)}")

            is_safe, safety_msg = check_output_safety(answer)
            if not is_safe:
                st.error(f"Response blocked: {safety_msg}")
                answer = _REDIRECT_MESSAGE

        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})


# ------------------------------------------------------------------
# Router
# ------------------------------------------------------------------
if st.session_state.authenticated:
    show_chat()
else:
    show_login()