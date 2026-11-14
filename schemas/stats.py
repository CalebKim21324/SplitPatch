"""Stats rows and diagnosis output (PLAN.md 3.1, 3.4)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from schemas.proposal import Category


class SoloQRow(BaseModel):
    """One row of data/stats/soloq.csv (Emerald+). Rates are percentages, e.g. 49.3."""

    model_config = ConfigDict(extra="forbid")
    patch: str
    champion: str
    wr: float = Field(ge=0, le=100)
    pr: float = Field(ge=0, le=100)
    br: float = Field(ge=0, le=100)
    games: int = Field(ge=0)


class ProRow(BaseModel):
    """One row of data/stats/pro.csv. presence/wr are percentages.

    gol.gg publishes only presence per patch; the other columns are blank (None) there.
    """

    model_config = ConfigDict(extra="forbid")
    patch: str
    champion: str
    presence: float = Field(ge=0, le=100)
    picks: int | None = Field(default=None, ge=0)
    bans: int | None = Field(default=None, ge=0)
    wr: float | None = Field(default=None, ge=0, le=100)
    games: int | None = Field(default=None, ge=0)


class Band(BaseModel):
    """Allowed relative change of an index, as fractions (-0.15 = -15%). None = unbounded."""

    model_config = ConfigDict(extra="forbid")
    lo: float | None = None
    hi: float | None = None

    def contains(self, x: float) -> bool:
        return (self.lo is None or x >= self.lo) and (self.hi is None or x <= self.hi)


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pro_index: Band = Band()
    soloq_index: Band = Band()


class Diagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    champion: str
    patch: str
    category: Category
    target: Target
    reasons: list[str]  # human-readable rule trace
    lever_hints: list[str] = []  # complaint tags that agree with the category, most-cited first
