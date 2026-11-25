"""
Write the shared diagram model as PlantUML text.

This is the inverse of validator.parser: it turns a DiagramModel back into
PlantUML in the supported ER subset, so that parse_puml(write_puml(model))
reproduces the same model (entities, attributes, keys, relationships).

Output layout:
- @startuml ... @enduml wrapper.
- One `entity Name { ... }` block per entity, in model order. Empty entities
  are written inline as `entity Name {}`.
- Attributes as `[*] name : type [<<PK>>] [<<FK>>]`. If the entity's primary
  keys are a leading run of attributes, a `--` separator is added after them
  (PlantUML convention; the parser ignores it). Attribute order is never
  changed.
- One crow's-foot relationship line per relationship, after the entities:
  `Left <left_card>--<right_card> Right [: label]`.

Notes:
- Attribute.references is not written: PlantUML has no syntax for it, and the
  parser re-infers it from FK/PK names.
"""

from __future__ import annotations

from pathlib import Path

from validator.model import (
    Attribute,
    Cardinality,
    DiagramModel,
    Entity,
    Relationship,
)

# Inverse of the parser's symbol maps. The left and right ends of a line use
# different symbols for the same cardinality (e.g. `|o` on the left, `o|` on
# the right). Kept here so the writer does not depend on parser internals.
_LEFT_SYMBOLS: dict[Cardinality, str] = {
    Cardinality.EXACTLY_ONE: "||",
    Cardinality.ZERO_OR_ONE: "|o",
    Cardinality.ONE_OR_MORE: "}|",
    Cardinality.ZERO_OR_MORE: "}o",
}

_RIGHT_SYMBOLS: dict[Cardinality, str] = {
    Cardinality.EXACTLY_ONE: "||",
    Cardinality.ZERO_OR_ONE: "o|",
    Cardinality.ONE_OR_MORE: "|{",
    Cardinality.ZERO_OR_MORE: "o{",
}

_INDENT = "  "


def write_file(model: DiagramModel, path: str | Path) -> None:
    """
    Write a DiagramModel to disk as a UTF-8 .puml file.

    Args:
        model: The diagram to write.
        path: Destination path; parent directories must already exist.

    Raises:
        OSError: If the file cannot be written.
    """
    _ = Path(path).write_text(write_puml(model), encoding="utf-8")


def write_puml(model: DiagramModel) -> str:
    """
    Render a DiagramModel as PlantUML ER diagram text.

    Args:
        model: The diagram to render.

    Returns:
        PlantUML text ending in a newline, accepted by parser.parse_puml.
    """
    lines: list[str] = ["@startuml"]

    for entity in model.entities:
        lines.append("")
        lines.extend(_write_entity(entity))

    if model.relationships:
        lines.append("")
        lines.extend(_write_relationship(r) for r in model.relationships)

    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def _write_entity(entity: Entity) -> list[str]:
    """Render one entity as the lines of its `entity Name { ... }` block."""
    if not entity.attributes:
        return [f"entity {entity.name} {{}}"]

    lines = [f"entity {entity.name} {{"]

    # Length of the leading run of PK attributes; a `--` goes right after it
    # when non-PK attributes follow. Only a leading run is separated so the
    # original attribute order is preserved exactly.
    leading_pks = 0
    for attribute in entity.attributes:
        if not attribute.is_pk:
            break
        leading_pks += 1
    has_separator = 0 < leading_pks < len(entity.attributes)

    for index, attribute in enumerate(entity.attributes):
        lines.append(_INDENT + _write_attribute(attribute))
        if has_separator and index == leading_pks - 1:
            lines.append(_INDENT + "--")

    lines.append("}")
    return lines


def _write_attribute(attribute: Attribute) -> str:
    """Render one attribute as `[*] name : type [<<PK>>] [<<FK>>]`."""
    text = f"{'* ' if attribute.mandatory else ''}{attribute.name} : {attribute.type}"
    if attribute.is_pk:
        text += " <<PK>>"
    if attribute.is_fk:
        text += " <<FK>>"
    return text


def _write_relationship(relationship: Relationship) -> str:
    """Render one relationship as `Left <card>--<card> Right [: label]`."""
    text = (
        f"{relationship.left} "
        f"{_LEFT_SYMBOLS[relationship.left_card]}--"
        f"{_RIGHT_SYMBOLS[relationship.right_card]} "
        f"{relationship.right}"
    )
    if relationship.label:
        text += f" : {relationship.label}"
    return text