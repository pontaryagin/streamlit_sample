import dataclasses
import enum
from typing import Literal, Optional
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
from sqlmodel import Field, Relationship, SQLModel, Session, select
import os
from dotenv import load_dotenv
from sys import argv

class User(SQLModel, table=True):
    id : str = Field(default=None, primary_key=True)
    first_name : str|None
    last_name : str|None
    assigned_actions : list["ActionNode"] = Relationship(back_populates="assigned_user")

class Status(enum.Enum):
    ToDo = "ToDo"
    InProgress = "InProgress"
    Done = "Done"
    Skipped = "Skipped"

class ActionLink(SQLModel, table=True):
    parent_id: Optional[int] = Field(
        default=None, foreign_key="ActionNode.id".lower(), primary_key=True
    )
    child_id: Optional[int] = Field(
        default=None, foreign_key="ActionNode.id".lower(), primary_key=True
    )
class ActionNode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    assigned_user_id: Optional[str] = Field(default=None, foreign_key="User.id".lower())
    assigned_user: User = Relationship(back_populates="assigned_actions")
    name : str
    status: Status
    memo: str
    workflow_id: Optional[int] = Field(default=None, foreign_key="Workflow.id".lower())
    workflow: Optional["Workflow"] = Relationship(back_populates="actions".lower())
    parents: list["ActionNode"] = Relationship(
        back_populates="children",
        link_model=ActionLink,
        sa_relationship_kwargs=dict(
            primaryjoin="ActionNode.id==ActionLink.child_id",
            secondaryjoin="ActionNode.id==ActionLink.parent_id",
        ),
    )
    children: list["ActionNode"] = Relationship(
        back_populates="parents",
        link_model=ActionLink,
        sa_relationship_kwargs=dict(
            primaryjoin="ActionNode.id==ActionLink.parent_id",
            secondaryjoin="ActionNode.id==ActionLink.child_id",
        ),
    )
class Workflow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    actions : list[ActionNode] = Relationship(back_populates="workflow")

def add_items(session, items: list[SQLModel]):
    for item in items:
        session.add(item)

def refresh_items(session, items: list[SQLModel]):
    for item in items:
        session.refresh(item)

def test():
    ECHO_DB = False
    if len(argv) > 1 and argv[1] == "dev":
        ECHO_DB = True

    # Create the database engine
    load_dotenv()
    DATABASE_URL="sqlite:///:memory:"
    # DATABASE_URL=f"""postgresql://{os.environ["DB_USERNAME"]}:{os.environ["DB_PASSWORD"]}@localhost:{os.environ["DB_PORT"]}/{os.environ["DB_NAME"]}"""
    engine = create_engine(DATABASE_URL, echo=ECHO_DB)
    session = sessionmaker(
    autocommit = False,
    autoflush = True,
    bind = engine
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        users = [User(id=f"test{i}", first_name=f"first{i}", last_name=f"last{i}") for i in range(3)]
        for user in users:
            session.add(user)
        workflow = Workflow(name="wf1")
        session.add(workflow)
        node = ActionNode(name="node1", status=Status.ToDo, memo="memo", 
                          assigned_user=users[0], workflow=workflow)
        node2 = ActionNode(name="node2", status=Status.ToDo, memo="memo", 
                          assigned_user=users[0], workflow=workflow)
        node3 = ActionNode(name="node3", status=Status.ToDo, memo="memo", 
                          assigned_user=users[0], workflow=workflow)
        
        node2.parents.append(node)
        node3.parents.append(node)
        node3.parents.append(node2)

        add_items(session, [node, node2, node3])
        session.commit()
        refresh_items(session, [node, node2, node3])
        wf = session.exec(select(Workflow)).one()
        assert wf
        a = wf.actions

        assert len(node.children) == 2
        assert len(node2.children) == 1
        assert len(node3.children) == 0
        session.commit()

if __name__ == "__main__":
    test()
