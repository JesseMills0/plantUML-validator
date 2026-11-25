"""R10: primary key attributes must carry the mandatory (*) marker."""

from __future__ import annotations

from validator.model import DiagramModel, Violation

RULE_ID = "R10"
SEVERITY = "ERROR"


def check(model: DiagramModel) -> list[Violation]:
    """Flag each PK attribute that is not marked mandatory."""
    violations: list[Violation] = []
    for entity in model.entities:
        for pk in entity.primary_keys:
            if not pk.mandatory:
                target = f"{entity.name}.{pk.name}"
                violations.append(
                    Violation(
                        RULE_ID,
                        SEVERITY,
                        target,
                        f"Primary key {target} is not marked mandatory (*)",
                    )
                )
    return violations
