"""Structured complaint JSON (PLAN.md 3.3).

This is the only form in which Reddit content reaches the diagnoser or patcher.
Anything that doesn't validate is rejected outright.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Tag = Literal["mana", "survivability", "damage", "cooldown", "range", "cc", "mobility", "too_strong"]


class Complaint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tag: Tag
    direction: Literal["buff", "nerf"]
    count: int = Field(ge=0)
    example_ids: list[str] = Field(default_factory=list, max_length=10)


class Complaints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaints: list[Complaint]
    n_posts: int = Field(ge=0)

    @model_validator(mode="after")
    def _counts_fit(self) -> "Complaints":
        for c in self.complaints:
            if c.count > self.n_posts:
                raise ValueError(f"complaint {c.tag} count {c.count} > n_posts {self.n_posts}")
        return self
