"""R8: the same relationship should not be drawn twice."""

from __future__ import annotations

from validator.model import DiagramModel, Relationship, Violation
from validator.rules._common import describe

RULE_ID = "R8"
SEVERITY = "WARN"


def _key(relationship: Relationship) -> tuple[tuple[str, str], tuple[str, str]]:
    """Direction-independent key: each entity paired with its end's cardinality."""
    return tuple(  # type: ignore[return-value]
        sorted(
            (
                (relationship.left, relationship.left_card.value),
                (relationship.right, relationship.right_card.value),
            )
        )
    )


def check(model: DiagramModel) -> list[Violation]:
    """Flag each group of relationships with identical cardinalities between
    the same two entities (either direction). Labels are ignored."""
    counts: dict[tuple[tuple[str, str], tuple[str, str]], int] = {}
    first: dict[tuple[tuple[str, str], tuple[str, str]], Relationship] = {}
    for relationship in model.relationships:
        key = _key(relationship)
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, relationship)

    return [
        Violation(
            RULE_ID,
            SEVERITY,
            describe(first[key]),
            f"Relationship between {first[key].left} and {first[key].right} "
            f"is defined {count} times with the same cardinalities",
        )
        for key, count in counts.items()
        if count > 1
    ]
