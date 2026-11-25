"""R6: a cycle of mandatory relationships can never be satisfied."""

from __future__ import annotations

from validator.model import DiagramModel, Violation

RULE_ID = "R6"
SEVERITY = "ERROR"


def check(model: DiagramModel) -> list[Violation]:
    """
    Flag each cycle of mandatory requirements.

    Entity A "requires" entity B if the marker at B's end of a relationship
    between them is mandatory (||, }|, |{). A cycle of requirements means no
    instance in the cycle can be created first. A self-relationship with a
    mandatory end is a cycle of one. One violation is reported per group of
    entities that all require each other.
    """
    requires: dict[str, set[str]] = {}
    for relationship in model.relationships:
        if relationship.right_card.is_mandatory:
            requires.setdefault(relationship.left, set()).add(relationship.right)
        if relationship.left_card.is_mandatory:
            requires.setdefault(relationship.right, set()).add(relationship.left)

    def reachable(start: str) -> set[str]:
        """Entities reachable from `start` by one or more requirement edges."""
        seen: set[str] = set()
        stack = list(requires.get(start, ()))
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(requires.get(node, ()))
        return seen

    reach = {name: reachable(name) for name in requires}
    order = [entity.name for entity in model.entities]

    violations: list[Violation] = []
    assigned: set[str] = set()
    for name in order:
        # `name in reach[name]` means name sits on a cycle (self-loops included).
        if name in assigned or name not in reach.get(name, set()):
            continue
        group = {other for other in reach[name] if name in reach.get(other, set())}
        assigned |= group
        members = [member for member in order if member in group]
        if len(members) == 1:
            message = (
                f"Entity {members[0]} has a mandatory relationship to itself, "
                f"so no instance can be created first"
            )
        else:
            message = (
                f"Entities {', '.join(members)} each require an instance of "
                f"another, so no instance can be created first"
            )
        violations.append(Violation(RULE_ID, SEVERITY, ", ".join(members), message))
    return violations
