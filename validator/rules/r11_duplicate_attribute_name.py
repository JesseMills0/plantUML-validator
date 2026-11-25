"""R11: attribute names must be unique within an entity."""

from __future__ import annotations

from collections import Counter

from validator.model import DiagramModel, Violation

RULE_ID = "R11"
SEVERITY = "ERROR"


def check(model: DiagramModel) -> list[Violation]:
    """Flag each attribute name used more than once in the same entity."""
    violations: list[Violation] = []
    for entity in model.entities:
        counts = Counter(attribute.name for attribute in entity.attributes)
        for name, count in counts.items():
            if count > 1:
                target = f"{entity.name}.{name}"
                violations.append(
                    Violation(
                        RULE_ID,
                        SEVERITY,
                        target,
                        f"Attribute {target} is declared {count} times",
                    )
                )
    return violations
