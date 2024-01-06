import dataclasses
import enum
from typing import Literal
import streamlit as st
import time
import asyncio
import numpy as npm

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pandas as pd
from streamlit_server_state import server_state, server_state_lock
import streamlit_authenticator as stauth
import yaml
import extra_streamlit_components as stx
import numpy as np

from streamlit_utility import initialize_page

initialize_page()

@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

with st.sidebar:
    if st.button("Logout"):
        cookie_manager.delete("username")

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
    username = st.text_input("Enter your username")
    if username:
        st.session_state["username"] = username
        cookie_manager.set("username", username)
        while cookie_manager.get("username") is None:
            time.sleep(0.1)

username = cookie_manager.get("username")

if username is None:
    form_username()
    exit()


def format_fullname(username):
    fullname = fullnames[username]
    return f"{fullname} ({username})"

fullnames = {
    "ponta": "ponta tanuki",
    "ponta2": "ponta2 tanuki",
}

reverse_formated_fullnames = {format_fullname(k): k for k, v in fullnames.items()}

Status = Literal["ToDo", "InProgress", "Done", "Skipped"]

@dataclasses.dataclass
class ActionNode:
    assigned_user: str
    name : str
    status: Status
    memo: str

@dataclasses.dataclass
class Workflow:
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

base_task = Workflow(actions=[
    ActionNode(assigned_user="ponta2", name="test", status= "Done", memo=""),
    ActionNode(assigned_user="ponta", name="test2", status= "InProgress", memo="start"),
    ActionNode(assigned_user="ponta", name="test3", status= "ToDo", memo="start"),
    ])

if "task" not in st.session_state:
    st.session_state["task"] = base_task

task: Workflow = st.session_state["task"]

action_in_progress = task.get_action_in_progress()
text_area_memo = st.text_area("Memo", 
                    value=action_in_progress.memo if action_in_progress else "")
if action_in_progress:
    if username == action_in_progress.assigned_user:
        *_, col1, col2, col3 = st.columns(5)
        with col1:
            btn_done = st.button("Done")
            if btn_done:
                task.update_state("Done", text_area_memo)
        with col2:
            btn_skip = st.button("Skip")
            if btn_skip:
                task.update_state("Skipped", text_area_memo)
        with col3:
            btn_update = st.button("Update")
            if btn_update and "task_diffs" in st.session_state:
                diffs = st.session_state.pop("task_diffs")
                for diff in diffs:
                    value = diff["value"][1]
                    if diff["key"] == "assigned_user":
                        value = reverse_formated_fullnames[value]
                    task.actions[diff["index"]-1].__setattr__(diff["key"], value)
else:
    btn_start = st.button("Start the task")
    if btn_start:
        task.start()

def check_diff_df(df_bef, df_aft)->list[dict]:
    diffs = []
    for i, (bef, aft) in enumerate(zip(df_bef.to_dict("records"), df_aft.to_dict("records"))):
        for key in bef.keys():
            if bef[key] != aft[key]:
                diff = {"index": i+1, "key": key, "value": (bef[key], aft[key]),
                        "values_bef": bef, "values_aft": aft}
                diffs.append(diff)
    return diffs

st.subheader("Action list")
df = pd.DataFrame(task.actions, index=range(1, len(task.actions)+1))
def add_color(val, color):
    return f"background-color: {color}" if val == username else ""
df["assigned_user"] = np.vectorize(format_fullname)(df["assigned_user"])
df["assigned_user"] = pd.Categorical(df["assigned_user"], categories=reverse_formated_fullnames.keys())
df_styled = (df[["name", "status", "assigned_user", "memo"]]
            .style.map(add_color, color="linen"))
df_new = st.data_editor(df_styled, disabled=["fullname", "name", "status"], use_container_width=True)

diffs = check_diff_df(df, df_new)
if diffs:
    output = ("You're updating the following items.  \n"
             +"Please press **Update** button if this is correct.\n")
    is_ok = True
    for diff in diffs:
        if diff["key"] not in ("assigned_user", "memo"):
            is_ok = False
            ouput = "You only allow to update assigned_user or memo\n"
            break
        output += f"- [Line {diff['index']}] `{diff['key']}`: `{diff['value'][0]}`  ⇒  `{diff['value'][1]}`\n"
    st.warning(output)
    if is_ok:
        st.session_state["task_diffs"] = diffs
