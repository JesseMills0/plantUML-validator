"""R1: every entity must have at least one primary key attribute."""

from __future__ import annotations

from validator.model import DiagramModel, Violation

RULE_ID = "R1"
SEVERITY = "ERROR"


def check(model: DiagramModel) -> list[Violation]:
    """Flag each entity that has no <<PK>> attribute."""
    return [
        Violation(
            RULE_ID,
            SEVERITY,
            entity.name,
            f'Entity "{entity.name}" has no primary key',
        )
        for entity in model.entities
        if not entity.primary_keys
    ]
