import dataclasses
import enum
from typing import Literal
import streamlit as st
import time
import asyncio
import numpy as np

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pandas as pd
from streamlit_server_state import server_state, server_state_lock
from streamlit_utility import get_remote_ip

user_ip = get_remote_ip()


st.set_page_config(page_title="Page Title", layout="wide")
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

# Create the database engine
engine = create_engine('sqlite:///db.sqlite3')
Base = declarative_base()
session = sessionmaker(
  autocommit = False,
  autoflush = True,
  bind = engine
)

# Define a sample table
class User(Base):
    __tablename__ = 'users'
    name = Column(String, primary_key=True)
    fullname = Column(String)

def form_username():
    with server_state_lock.username_cache:
        if "username_cache" not in server_state:
            server_state.username_cache = {}

    with st.form("form_username"):
        with server_state_lock.username_cache:
            default_username = server_state.username_cache.get(user_ip, "")
        username = st.text_input("Enter your username", value=default_username)
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state["username"] = username
            with server_state_lock.username_cache:
                server_state.username_cache.update({user_ip : username})
            st.rerun()

if "username" not in st.session_state:
    form_username()
    exit()

username = st.session_state["username"]

fullnames = {
    "ponta": "ponta tanuki",
    "ponta2": "ponta2 tanuki",
}

Status = Literal["ToDo", "InProgress", "Done", "Skipped"]

@dataclasses.dataclass
class ActionNode:
    assigned_user: str
    name : str
    status: Status
    memo: str

@dataclasses.dataclass
class TaskUnit:
    actions : list[ActionNode]

    def save(self):
        st.session_state["task"] = self

    def start(self):
        action_in_progress = self.get_action_in_progress()
        assert action_in_progress is None
        self.actions[0].status = "InProgress"
        self.save()

    def get_action_in_progress(self):
        for action in self.actions:
            if action.status == "InProgress":
                return action
        return None

    def update_state(self, status: Literal["Done", "Skipped"], memo: str):
        action_in_progress = self.get_action_in_progress()
        if action_in_progress is None:
            return
        action_in_progress.status = status
        action_in_progress.memo = memo
        progress_pos = self.actions.index(action_in_progress)
        if progress_pos == len(self.actions) - 1:
            self.save()
            return
        action_next = self.actions[progress_pos+1]
        action_next.status = "InProgress"
        # send message to self.actions[pro].assigned_user
        self.save()

base_task = TaskUnit(actions=[
    ActionNode(assigned_user="ponta2", name="test", status= "Done", memo=""),
    ActionNode(assigned_user="ponta", name="test2", status= "InProgress", memo="start"),
    ActionNode(assigned_user="ponta", name="test3", status= "ToDo", memo="start"),
    ])

if "task" not in st.session_state:
    st.session_state["task"] = base_task

task = st.session_state["task"]

action_in_progress = task.get_action_in_progress()
text_area_memo = st.text_area("Memo", 
                    value=action_in_progress.memo if action_in_progress else "")
if action_in_progress:
    if username == action_in_progress.assigned_user:
        col1, col2 = st.columns(2)
        with col1:
            btn_done = st.button("Mark as Done")
            if btn_done:
                task.update_state("Done", text_area_memo)
        with col2:
            btn_skip = st.button("Skip")
            if btn_skip:
                task.update_state("Skipped", text_area_memo)
else:
    btn_start = st.button("Start the task")
    if btn_start:
        task.start()

st.header("Action list")
df = pd.DataFrame(task.actions, index=range(1, len(task.actions)+1))
df.style.applymap(lambda x: "background-color: yellow" if x== username else "", subset=["assigned_user"])
st.data_editor(df)



# bt = st.button("Click me")
# if bt:
#     st.session_state["abc"] = st.session_state.get("abc", 0) + 1

# async def do(tab):
#     with tab:
#         st.write("This is the tab ")
#         # print(str(tab))
#         for i in range(10):
#             await asyncio.sleep(0.1)    
#             st.write(i)
            

# async def main():
#     await asyncio.gather(do(tab1), do(tab2), do(tab3))

# asyncio.run(main())
    