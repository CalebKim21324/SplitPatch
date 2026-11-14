"""Proposal format: a diff to one champion's kit (PLAN.md 3.5)."""
from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

Value = float | list[float]


class Category(str, Enum):
    PRO_JAIL = "PRO_JAIL"
    OVERALL_STRONG = "OVERALL_STRONG"
    OVERALL_WEAK = "OVERALL_WEAK"
    SOLOQ_ONLY_STRONG = "SOLOQ_ONLY_STRONG"
    HOLD = "HOLD"


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    field: str                      # dotted path, e.g. abilities.W_soldier_attack.ap_ratio
    from_: Value = Field(alias="from")
    to: Value

    @field_validator("field")
    @classmethod
    def _dotted(cls, v: str) -> str:
        parts = v.split(".")
        if parts[0] not in ("base", "abilities") or len(parts) != (2 if parts[0] == "base" else 3):
            raise ValueError("field must be base.<stat> or abilities.<key>.<field>")
        return v


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    champion: str
    patch: str
    category: Category
    changes: list[Change]
    rationale: str

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json", by_alias=True), sort_keys=False)

    @classmethod
    def from_yaml(cls, text: str) -> "Proposal":
        return cls.model_validate(yaml.safe_load(text))

    @classmethod
    def load(cls, path: str | Path) -> "Proposal":
        return cls.from_yaml(Path(path).read_text(encoding="utf-8"))
