"""R7: an FK's mandatory marker must match its relationship's optionality."""

from __future__ import annotations

from validator.model import DiagramModel, Violation
from validator.rules._common import parent_and_child, referenced_entity

RULE_ID = "R7"
SEVERITY = "ERROR"


def check(model: DiagramModel) -> list[Violation]:
    """
    Flag FKs in the child of a one-to-many relationship whose `*` marker
    disagrees with the parent end: `||` needs a mandatory FK, `|o` needs an
    optional one.
    """
    violations: list[Violation] = []
    seen: set[str] = set()
    for relationship in model.relationships:
        pair = parent_and_child(relationship)
        if pair is None:
            continue
        parent_name, child_name = pair
        if parent_name == child_name:
            continue
        child = model.get_entity(child_name)
        if child is None:
            continue

        # Marker at the parent's end: how many parents each child has.
        parent_card = (
            relationship.left_card
            if relationship.left == parent_name
            else relationship.right_card
        )
        must_be_mandatory = parent_card.is_mandatory

        for fk in child.foreign_keys:
            if referenced_entity(fk.references) != parent_name:
                continue
            if fk.mandatory == must_be_mandatory:
                continue
            target = f"{child_name}.{fk.name}"
            if target in seen:
                continue
            seen.add(target)
            expected = "mandatory (*)" if must_be_mandatory else "optional (no *)"
            actual = "mandatory" if fk.mandatory else "optional"
            violations.append(
                Violation(
                    RULE_ID,
                    SEVERITY,
                    target,
                    f"{target} is {actual} but its relationship with "
                    + f"{parent_name} requires it to be {expected}",
                )
            )
    return violations
