"""R4: an FK must have the same type as the primary key it references."""

from __future__ import annotations

from validator.model import DiagramModel, Violation

RULE_ID = "R4"
SEVERITY = "ERROR"


def _normalize(type_name: str) -> str:
    """Lowercase and drop all whitespace so `VARCHAR( 50 )` == `varchar(50)`."""
    return "".join(type_name.split()).lower()


def check(model: DiagramModel) -> list[Violation]:
    """Flag each FK whose type differs from its referenced PK's type."""
    violations: list[Violation] = []
    for entity in model.entities:
        for fk in entity.foreign_keys:
            if fk.references is None:
                continue  # R3 reports FKs with no target
            target_name, _, pk_name = fk.references.partition(".")
            target = model.get_entity(target_name)
            pk = target.get_attribute(pk_name) if target is not None else None
            if pk is None:
                continue
            if _normalize(fk.type) != _normalize(pk.type):
                name = f"{entity.name}.{fk.name}"
                violations.append(
                    Violation(
                        RULE_ID,
                        SEVERITY,
                        name,
                        f"{name} has type {fk.type} but references "
                        f"{fk.references} which has type {pk.type}",
                    )
                )
    return violations
