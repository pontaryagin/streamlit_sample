import streamlit as st
from streamlit_utility import initialize_page
from streamlit_utility import initialize_page, get_manager

initialize_page()

cookie_manager = get_manager()

st.write(f"Hello {cookie_manager.get('username')}")
