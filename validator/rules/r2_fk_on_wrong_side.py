"""R2: in a one-to-many relationship the FK belongs on the "many" side."""

from __future__ import annotations

from validator.model import DiagramModel, Violation
from validator.rules._common import parent_and_child, referenced_entity

RULE_ID = "R2"
SEVERITY = "ERROR"


def check(model: DiagramModel) -> list[Violation]:
    """Flag an FK held by the parent (one side) that references its child."""
    violations: list[Violation] = []
    seen: set[str] = set()
    for relationship in model.relationships:
        pair = parent_and_child(relationship)
        if pair is None:
            continue
        parent_name, child_name = pair
        if parent_name == child_name:
            continue
        parent = model.get_entity(parent_name)
        if parent is None:
            continue
        for fk in parent.foreign_keys:
            if referenced_entity(fk.references) != child_name:
                continue
            target = f"{parent_name}.{fk.name}"
            if target in seen:
                continue
            seen.add(target)
            violations.append(
                Violation(
                    RULE_ID,
                    SEVERITY,
                    target,
                    f"{target} is a foreign key to {child_name}, but {parent_name} "
                    + 'is the "one" side of the relationship; '
                    + f"the FK belongs in {child_name}",
                )
            )
    return violations
