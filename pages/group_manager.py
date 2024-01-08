import streamlit as st
from stream_app import USER_FULLNAMES
from streamlit_utility import initialize_page


cookie_manager = initialize_page()  # must be at the top of every page

st.subheader("Group Manager")

with st.form("Create Group"):
    st.text_input("Group Name")
    st.text_input("Group Description")
    st.multiselect("Members", USER_FULLNAMES.keys())
    submitted = st.form_submit_button("Create Group")
    if submitted:
        st.write("Group created")

