"""R9: every entity should take part in at least one relationship."""

from __future__ import annotations

from validator.model import DiagramModel, Violation

RULE_ID = "R9"
SEVERITY = "WARN"


def check(model: DiagramModel) -> list[Violation]:
    """Flag entities in no relationship (only if the diagram has 2+ entities)."""
    if len(model.entities) < 2:
        return []
    return [
        Violation(
            RULE_ID,
            SEVERITY,
            entity.name,
            f'Entity "{entity.name}" is not part of any relationship',
        )
        for entity in model.entities
        if not model.relationships_of(entity.name)
    ]
