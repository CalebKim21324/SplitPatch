"""Structured patch-note output (PLAN.md 3.7). The writer must return exactly this shape."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

Value = float | list[float]


class Line(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    field: str
    label: str
    from_: Value = Field(alias="from")
    to: Value
    text: str


class PatchNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    champion: str
    context: str
    lines: list[Line]


class Tooltip(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ability: str
    text: str
    values: dict[str, Value]


class Notes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patch_note: PatchNote
    tooltips: list[Tooltip]


_VALUE = {"anyOf": [{"type": "number"}, {"type": "array", "items": {"type": "number"}}]}

# JSON schema for structured outputs (additionalProperties false everywhere; `values` keys vary,
# so tooltips carry values as a list of {name, value} pairs and are converted after parsing).
JSON_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["patch_note", "tooltips"],
    "properties": {
        "patch_note": {
            "type": "object", "additionalProperties": False, "required": ["champion", "context", "lines"],
            "properties": {
                "champion": {"type": "string"},
                "context": {"type": "string"},
                "lines": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["field", "label", "from", "to", "text"],
                    "properties": {"field": {"type": "string"}, "label": {"type": "string"},
                                   "from": _VALUE, "to": _VALUE, "text": {"type": "string"}}}},
            },
        },
        "tooltips": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["ability", "text", "values"],
            "properties": {
                "ability": {"type": "string"}, "text": {"type": "string"},
                "values": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["name", "value"],
                    "properties": {"name": {"type": "string"}, "value": _VALUE}}},
            }}},
    },
}


def from_json(data: dict) -> Notes:
    """Convert the structured-output JSON (values as pairs) into Notes."""
    data = dict(data)
    data["tooltips"] = [{**t, "values": {v["name"]: v["value"] for v in t["values"]}} for t in data["tooltips"]]
    return Notes.model_validate(data)
