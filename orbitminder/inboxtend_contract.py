"""Validated, metadata-only Inboxtend task feed contract.

This is a transport contract, not a database table or a live connection.
Inboxtend remains authoritative for task status and native agent execution.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Literal

from pydantic import ConfigDict, Field, HttpUrl, model_validator
from sqlmodel import SQLModel


class InboxtendTask(SQLModel, table=False):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    project: str | None = Field(default=None, max_length=200)
    status: Literal["new", "in_progress", "waiting", "done"]
    priority: Literal["low", "medium", "high"]
    due_at: datetime | None = None
    due_date: date | None = None
    due_timezone: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = None
    review_state: str = Field(min_length=1, max_length=100)
    assigned_agent: str | None = Field(default=None, max_length=200)
    executor: Literal["inboxtend", "agentsteers"] | None = None
    agent_job_id: str | None = Field(default=None, max_length=200)
    agent_status: str | None = Field(default=None, max_length=100)
    updated_at: datetime
    revision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_time_and_execution(self):
        if self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("due_at must be timezone-aware")
        if self.agent_job_id and self.executor is None:
            raise ValueError("agent_job_id requires an explicit executor")
        return self


class InboxtendTaskPage(SQLModel, table=False):
    """A single authorized snapshot page; no mailbox contents or tokens."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: Literal["inboxtend"]
    schema_version: Literal[1]
    snapshot_at: datetime
    items: list[InboxtendTask] = Field(default_factory=list, max_length=100)
    next_cursor: str | None = Field(default=None, min_length=1, max_length=2048)
    has_more: bool

    @model_validator(mode="after")
    def validate_page(self):
        if self.snapshot_at.tzinfo is None:
            raise ValueError("snapshot_at must be timezone-aware")
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("next_cursor is required exactly when has_more is true")
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("duplicate task IDs in a page")
        return self
