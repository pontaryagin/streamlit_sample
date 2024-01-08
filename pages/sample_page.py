import streamlit as st
from streamlit_utility import initialize_page, get_username

cookie_manager = initialize_page()  # must be at the top of every page

st.write(f"Hello {get_username()}")
