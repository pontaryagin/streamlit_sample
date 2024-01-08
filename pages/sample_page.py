import streamlit as st
from streamlit_utility import initialize_page

cookie_manager = initialize_page()  # must be at the top of every page

st.write(f"Hello {cookie_manager.get('username')}")
