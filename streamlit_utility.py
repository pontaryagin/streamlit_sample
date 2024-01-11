import streamlit as st
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx
import extra_streamlit_components as stx
import time
from threading import Lock

def get_remote_ip() -> str|None:
    """Get remote ip."""

    try:
        ctx = get_script_run_ctx()
        if ctx is None:
            return None

        session_info = runtime.get_instance().get_client(ctx.session_id)
        if session_info is None:
            return None
    except Exception as e:
        return None
    return session_info.request.remote_ip #type: ignore

def delete_cookie(cookie_manager, key):
    cookie_manager.delete(key)
    i = 0
    while cookie_manager.get(key) is not None and i != 100:  # somehow this is needed to make sure that cookie is deleted
        time.sleep(0.01)
        i += 1
    if i == 100:
        st.error("Failed to delete cookie")

def update_cookie(cookie_manager: stx.CookieManager, key, value):
    if cookie_manager.get(key) == value:
        return
    if cookie_manager.get(key) is not None:
        delete_cookie(cookie_manager, key)
    cookie_manager.set(key, value)
    i = 0
    while cookie_manager.get(key) != value and i != 100:  # somehow this is needed to make sure that cookie is deleted
        time.sleep(0.01)
        i += 1
    if i == 100:
        st.error("Failed to update cookie")

def get_cookie_manager():
    cookie_manager = stx.CookieManager()
    return cookie_manager

def form_username(cookie_manager):
    if st.session_state.get("username") is not None:
        return
    username = cookie_manager.get("username")
    if username is None:
        username = st.text_input("Enter your username")
        if username:
            update_cookie(cookie_manager, "username", username)
        st.stop()
    st.session_state["username"] = username

def get_username()->str:
    if username := st.session_state.get("username"):
        return username
    st.error("Username not found")
    st.stop()

def initialize_page():
    st.set_page_config(page_title="Workflow generator", layout="wide", initial_sidebar_state="collapsed")
    cookie_manager = get_cookie_manager()

    # adjust page style
    margin_top = -5
    st.markdown(
        f"""
            <style>
                .appview-container .main .block-container {{
                    margin-top: {margin_top}rem;
                    }}

            </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        if st.button("Logout"):
            st.session_state.pop("username", None)
            delete_cookie(cookie_manager, "username")
            st.rerun()
    form_username(cookie_manager)
    return cookie_manager

USER_FULLNAMES = {
    "ponta": "ponta tanuki",
    "ponta2": "ponta2 tanuki",
}
