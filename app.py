from __future__ import annotations
import dataclasses
import enum
from typing import Literal
import streamlit as st
import time
import asyncio
import numpy as npm

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import pandas as pd
import numpy as np
import graphviz
from pydantic import BaseModel
from sqlmodel import Field, SQLModel
import os
from dotenv import load_dotenv

load_dotenv()

from streamlit_utility import USER_FULLNAMES, initialize_page, get_username

cookie_manager = initialize_page() # must be at the top of every page

username:str = get_username()

# Create the database engine
DATABASE_URL=f"""postgresql://{os.environ["DB_USERNAME"]}:{os.environ["DB_PASSWORD"]}@localhost:{os.environ["DB_PORT"]}/{os.environ["DB_NAME"]}"""
engine = create_engine('sqlite:///db.sqlite3')
Base = declarative_base()
session = sessionmaker(
  autocommit = False,
  autoflush = True,
  bind = engine
)

class User(SQLModel, table=True):
    username : str = Field(default=None, primary_key=True)
    first_name : str|None
    last_name : str|None

def format_fullname(username):
    fullname = USER_FULLNAMES[username]
    return f"{fullname} ({username})"


USER_REVERSE_FORMATTED_FULLNAMES = {format_fullname(k): k for k, v in USER_FULLNAMES.items()}

Status = Literal["ToDo", "InProgress", "Done", "Skipped"]

class ActionNode(BaseModel):
    assigned_user: str
    name : str
    requirements: list[str]
    status: Status
    memo: str

class Workflow(BaseModel):
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

    def to_dataframe(self):
        actions = [action.model_dump() for action in self.actions]
        df = pd.DataFrame(actions, index=range(1, len(self.actions)+1))
        df["assigned_user"] = np.vectorize(format_fullname)(df["assigned_user"])
        return df

    @staticmethod
    def from_dataframe(df):
        records = df.to_dict("records")
        return Workflow(actions = [ActionNode(**record) for record in records])

    def finished(self):
        return all(action.status in ("Done", "Skipped") for action in self.actions)

BASE_TASK = Workflow(actions=[
    ActionNode(assigned_user="ponta2", name="test", requirements=[], status= "Done", memo=""),
    ActionNode(assigned_user="ponta", name="test2", requirements=["test"], status= "InProgress", memo="start"),
    ActionNode(assigned_user="ponta", name="test3", requirements=["test", "test2"], status= "ToDo", memo="start"),
    ])

def get_task() -> Workflow:
    if "task" not in st.session_state:
        st.session_state["task"] = BASE_TASK
    return st.session_state["task"]

def check_diff_df(df_bef, df_aft)->list[dict]:
    diffs = []
    for i, (bef, aft) in enumerate(zip(df_bef.to_dict("records"), df_aft.to_dict("records"))):
        for key in bef.keys():
            if key not in aft.keys():
                continue
            if bef[key] != aft[key]:
                diff = {"index": i+1, "key": key, "value": (bef[key], aft[key])}
                diffs.append(diff)
    return diffs

def st_action_form():
    task: Workflow = get_task()
    action_in_progress = task.get_action_in_progress()
    if action_in_progress:
        if username == action_in_progress.assigned_user:
            st.subheader("Update your task")
            text_area_memo = st.text_area("Memo", 
                                value=action_in_progress.memo if action_in_progress else "")
            *_, col1, col2, col3 = st.columns(5)
            with col1:
                btn_done = st.button("Done")
                if btn_done:
                    task.update_state("Done", text_area_memo)
                    st.rerun()
            with col2:
                btn_skip = st.button("Skip")
                if btn_skip:
                    task.update_state("Skipped", text_area_memo)
                    st.rerun()
            with col3:
                btn_update = st.button("Update")
                if btn_update and "task_diffs" in st.session_state:
                    diffs = st.session_state.pop("task_diffs")
                    for diff in diffs:
                        value = diff["value"][1]
                        if diff["key"] == "assigned_user":
                            value = USER_REVERSE_FORMATTED_FULLNAMES[value]
                        task.actions[diff["index"]-1].__setattr__(diff["key"], value)
                    st.rerun()
    elif task.finished():
        st.success("This task has been finished.")
    else:
        btn_start = st.button("Start the task")
        if btn_start:
            task.start()

STATUS_COLOR = {
    "InProgress": "#FDF5E6", 
    "Done": "#90EE90",
    "Skipped": "#D3D3D3",
    "ToDo": "#F0FFFF",
}

def add_style_to_df(df:pd.DataFrame):
    def add_color(value):
        return f"background-color: {STATUS_COLOR[value]}"
    df_styled = (df
                .style
                .map(add_color, subset=["status"])
                )
    return df_styled

def get_column_config():
    assigned_user_column_config = st.column_config.SelectboxColumn(
                "Assigned User",
                help="Assigned user for the task",
                options=USER_REVERSE_FORMATTED_FULLNAMES.keys(),
                required=True,)
    
    column_config = {
        "assigned_user": assigned_user_column_config,
        "memo": st.column_config.Column("Memo",help="Memo for the task",),
        "requirements": st.column_config.ListColumn("Requirements", )
    }
    return column_config

def st_action_list():
    task: Workflow = get_task()
    st.subheader("Action list")
    df = task.to_dataframe()
    df_styled = add_style_to_df(df)

    editable_cols = ["assigned_user", "memo", "requirements"]
    disabled_cols = [col for col in df.columns if col not in editable_cols]
    df_new = st.data_editor(df_styled, disabled=disabled_cols, 
                            column_config= get_column_config(), use_container_width=True,
                            )
    diffs = check_diff_df(df, df_new)
    if diffs:
        output = ("You're updating the following items.  \n"
                +"Please press **Update** button if this is correct.\n")
        is_ok = True
        for diff in diffs:
            if diff["key"] not in ("assigned_user", "memo"):
                is_ok = False
                output = "You only allow to update assigned_user or memo\n"
                break
            output += f"- [Line {diff['index']}] `{diff['key']}`: `{diff['value'][0]}`  ⇒  `{diff['value'][1]}`\n"
        st.warning(output)
        if is_ok:
            st.session_state["task_diffs"] = diffs

def st_action_graph():
    task = get_task()
    st.subheader("Flow chart")
    graph = graphviz.Digraph()
    graph.attr('node', shape='box', color='#888888')
    graph.attr('edge', color='#888888')
    for action in task.actions:
        fillcolor = STATUS_COLOR[action.status]
        graph.node(action.name, style='filled', fillcolor=fillcolor)
        for req in (action.requirements or []):
            graph.edge(req, action.name)
    st.graphviz_chart(graph)

def main():
    st_action_form()
    st_action_list()
    st_action_graph()

main()
