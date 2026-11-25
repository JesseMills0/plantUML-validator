"""R5: a many-to-many relationship must go through a junction entity."""

from __future__ import annotations

from validator.model import DiagramModel, Violation
from validator.rules._common import describe

RULE_ID = "R5"
SEVERITY = "ERROR"


def check(model: DiagramModel) -> list[Violation]:
    """Flag every relationship where both ends are "many"."""
    return [
        Violation(
            RULE_ID,
            SEVERITY,
            describe(relationship),
            f"Relationship between {relationship.left} and {relationship.right} "
            f"is many-to-many; model it with a junction entity",
        )
        for relationship in model.relationships
        if relationship.is_many_to_many
    ]
