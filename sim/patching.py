"""Apply a proposal's diff to a kit, in memory. Never writes to data/."""
from __future__ import annotations

from schemas import Kit, Proposal


def get_field(kit: Kit, field: str):
    parts = field.split(".")
    if parts[0] == "base":
        return getattr(kit.base, "as_" if parts[1] == "as" else parts[1], None)
    ab = kit.abilities.get(parts[1])
    return getattr(ab, parts[2], None) if ab is not None else None


def apply(kit: Kit, proposal: Proposal) -> Kit:
    """Return a patched copy of `kit`. Assumes the proposal already passed schema checks."""
    new = kit.model_copy(deep=True)
    for ch in proposal.changes:
        parts = ch.field.split(".")
        target = new.base if parts[0] == "base" else new.abilities[parts[1]]
        name = parts[1] if parts[0] == "base" else parts[2]
        setattr(target, "as_" if name == "as" else name, ch.to)
    return new
