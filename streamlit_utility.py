import streamlit as st
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx
import extra_streamlit_components as stx

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

def initialize_page():
    st.set_page_config(page_title="Workflow generator", layout="wide", initial_sidebar_state="collapsed")
    st.markdown("""
        <style>
            .reportview-container {
                margin-top: -2em;
            }
            #MainMenu {visibility: hidden;}
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            #stDecoration {display:none;}
        </style>
    """, unsafe_allow_html=True)


@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()
