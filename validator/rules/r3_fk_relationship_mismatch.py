"""R3: every FK needs a relationship, and every relationship needs an FK."""

from __future__ import annotations

from validator.model import DiagramModel, Entity, Violation
from validator.rules._common import describe, referenced_entity

RULE_ID = "R3"
SEVERITY = "ERROR"


def _has_fk_to(entity: Entity, other_name: str) -> bool:
    """True if some FK of `entity` references a PK of `other_name`."""
    return any(
        referenced_entity(fk.references) == other_name
        for fk in entity.foreign_keys
    )


def check(model: DiagramModel) -> list[Violation]:
    """
    Flag (a) relationships with no FK referencing across them and
    (b) FKs that reference no primary key of a related entity.

    Many-to-many relationships are skipped (R5 owns them), as are
    self-relationships. Direction is ignored (R2 owns FK placement).
    """
    violations: list[Violation] = []

    seen_pairs: set[frozenset[str]] = set()
    for relationship in model.relationships:
        if relationship.left == relationship.right or relationship.is_many_to_many:
            continue
        left = model.get_entity(relationship.left)
        right = model.get_entity(relationship.right)
        if left is None or right is None:
            continue
        if _has_fk_to(left, right.name) or _has_fk_to(right, left.name):
            continue
        pair = frozenset((left.name, right.name))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        violations.append(
            Violation(
                RULE_ID,
                SEVERITY,
                describe(relationship),
                f"Relationship between {left.name} and {right.name} "
                f"has no foreign key referencing across it",
            )
        )

    for entity in model.entities:
        for fk in entity.foreign_keys:
            if fk.references is None:
                target = f"{entity.name}.{fk.name}"
                violations.append(
                    Violation(
                        RULE_ID,
                        SEVERITY,
                        target,
                        f"Foreign key {target} does not reference a primary key "
                        f"of any related entity",
                    )
                )

    return violations
