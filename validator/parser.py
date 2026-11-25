r"""
Parser for the supported PlantUML ER diagram subset.

Reads PlantUML text (from a string or a .puml file) and builds a DiagramModel
representing the entities, attributes, keys, and crow's-foot relationships in
the diagram. Diagrams must render in PlantUML without errors, though
only a defined subset of PlantUML ER syntax is supported; anything outside
that subset raises ParseError with a 1-based line number.

Supported subset:
- Diagram wrapper: @startuml ... @enduml (one diagram per file).
- Comments & directives: lines starting with ' are comments; title, skinparam,
  hide, show, and layout direction lines are ignored because they affect
  visual layout rather than schema structure.
- Entities: entity Name { ... } or entity Name {} where Name matches
  [A-Za-z_]\w*.
- Attributes inside an entity: [*] name : type [<<PK>>] [<<FK>>].
  Leading * means mandatory; -- lines are separators and ignored; stereotypes
  can be separate (<<PK>> <<FK>>) or comma-separated (<<PK, FK>>).
- Relationships: Left <left_card>--<right_card> Right [: label] (also
  accepting .. in place of --) using crow's-foot symbols:
  - Left side:  || (exactly one), |o (zero or one), }| (one or more),
    }o (zero or more).
  - Right side: || (exactly one), o| (zero or one), |{ (one or more),
    o{ (zero or more).

Behavior and notes:
- Relationships can appear before or after their entity blocks; missing
  entities are checked after all lines are read.
- PlantUML does not state which PK an FK targets, so _infer_references fills
  in Attribute.references ("TargetEntity.pk_name") by matching FK names to PK
  names across connected entities (skipping self-references). Unmatched
  FKs stay None so validation rules can inspect them.
"""

from __future__ import annotations

import re
from pathlib import Path

from validator.model import (
    Attribute,
    Cardinality,
    DiagramModel,
    Entity,
    Relationship,
)


class ParseError(Exception):
    """Raised when input text uses syntax outside the supported subset."""


# Crow's-foot symbols look different on the left vs. right end of a line,
# so each side has its own mapping to Cardinality.
_LEFT_SYMBOLS: dict[str, Cardinality] = {
    "||": Cardinality.EXACTLY_ONE,
    "|o": Cardinality.ZERO_OR_ONE,
    "}|": Cardinality.ONE_OR_MORE,
    "}o": Cardinality.ZERO_OR_MORE,
}

_RIGHT_SYMBOLS: dict[str, Cardinality] = {
    "||": Cardinality.EXACTLY_ONE,
    "o|": Cardinality.ZERO_OR_ONE,
    "|{": Cardinality.ONE_OR_MORE,
    "o{": Cardinality.ZERO_OR_MORE,
}


def _symbol_pattern(symbols: dict[str, Cardinality]) -> str:
    """Build a regex alternation string from a cardinality symbol map."""
    return "|".join(re.escape(symbol) for symbol in symbols)


# Matches `entity Name {` (multi-line block) or `entity Name {}` (inline empty block).
_ENTITY_RE = re.compile(
    r"^entity\s+(?P<name>[A-Za-z_]\w*)\s*\{\s*(?P<close>\})?$"
)

# Matches `Left <card>--<card> Right` (or `..`) with an optional `: label`.
_RELATIONSHIP_RE = re.compile(
    r"^(?P<left>[A-Za-z_]\w*)\s*"
    + rf"(?P<left_card>{_symbol_pattern(_LEFT_SYMBOLS)})"
    + r"(?:--|\.\.)"
    + rf"(?P<right_card>{_symbol_pattern(_RIGHT_SYMBOLS)})"
    + r"\s*(?P<right>[A-Za-z_]\w*)(?:\s*:\s*(?P<label>.+))?$"
)

# Matches `[*] name : type` plus zero or more `<<...>>` stereotype tags.
_ATTRIBUTE_RE = re.compile(
    r"^(?P<mandatory>\*)?\s*(?P<name>[A-Za-z_]\w*)\s*:\s*"
    + r"(?P<type>[^<\s][^<]*?)\s*(?P<stereotypes>(?:<<[^>]*>>\s*)*)$"
)

# Pulls the text inside each `<<...>>` stereotype block.
_STEREOTYPE_RE = re.compile(r"<<([^>]*)>>")

# PlantUML lines that only affect rendering/layout rather than ER structure.
_IGNORED_PREFIXES = (
    "title",
    "skinparam",
    "hide",
    "show",
    "left to right direction",
    "top to bottom direction",
)


def _error(line_number: int, message: str) -> ParseError:
    """Create a ParseError prefixed with a 1-based line number."""
    return ParseError(f"line {line_number}: {message}")


def _is_ignored_directive(lowered: str) -> bool:
    """Return True if a lowercased line is an ignored layout/display directive."""
    return any(
        lowered == prefix or lowered.startswith(prefix + " ")
        for prefix in _IGNORED_PREFIXES
    )


def parse_file(path: str | Path) -> DiagramModel:
    """
    Read a UTF-8 .puml file from disk and parse it into a DiagramModel.

    Args:
        path: Path or string path to the .puml file.

    Returns:
        A DiagramModel with the parsed entities and relationships.

    Raises:
        ParseError: If the diagram uses unsupported syntax.
        OSError: If the file cannot be read.
    """
    return parse_puml(Path(path).read_text(encoding="utf-8"))


def parse_puml(text: str) -> DiagramModel:
    """
    Parse PlantUML ER diagram text into a DiagramModel.

    Scans line by line to track @startuml/@enduml and open entity blocks,
    collects relationships (allowing forward or backward entity references),
    checks that all referenced entities exist, and infers FK targets by name.

    Args:
        text: Raw PlantUML diagram text.

    Returns:
        A populated DiagramModel instance.

    Raises:
        ParseError: On missing/duplicate/misplaced delimiters, unclosed entities,
            duplicate entity names, bad attribute/line syntax, or undefined
            relationship endpoints.
    """
    model = DiagramModel()
    pending_relationships: list[tuple[int, Relationship]] = []
    started = False
    ended = False
    current_entity: Entity | None = None
    current_start_line = 0

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        # Ignore blank lines and ' comments.
        if not line or line.startswith("'"):
            continue

        lowered = line.lower()

        # Disallow extra content after @enduml.
        if ended:
            raise _error(line_no, "unexpected content after @enduml")

        if lowered == "@startuml" or lowered.startswith("@startuml "):
            if started:
                raise _error(
                    line_no,
                    "duplicate @startuml; only one diagram per file is supported",
                )
            started = True
            continue

        if not started:
            raise _error(line_no, "expected @startuml before diagram content")

        if lowered == "@enduml":
            if current_entity is not None:
                raise _error(
                    current_start_line,
                    'entity "' + current_entity.name + '" is never closed with "}"',
                )
            ended = True
            continue

        # Inside an `entity Name {` block: parse attributes or close with `}`.
        if current_entity is not None:
            if line == "}":
                model.entities.append(current_entity)
                current_entity = None
            elif line != "--":
                current_entity.attributes.append(_parse_attribute(line, line_no))
            continue

        # Top-level entity header.
        entity_match = _ENTITY_RE.match(line)
        if entity_match is not None:
            entity_name: str = entity_match.group("name")
            if model.get_entity(entity_name) is not None:
                raise _error(line_no, 'duplicate entity definition "' + entity_name + '"')

            entity = Entity(name=entity_name)
            if entity_match.group("close") is not None:
                model.entities.append(entity)
            else:
                current_entity = entity
                current_start_line = line_no
            continue

        # Top-level crow's-foot relationship line.
        rel_match = _RELATIONSHIP_RE.match(line)
        if rel_match is not None:
            raw_label: str | None = rel_match.group("label")
            label: str = raw_label.strip() if raw_label is not None else ""
            left_sym: str = rel_match.group("left_card")
            right_sym: str = rel_match.group("right_card")
            relationship = Relationship(
                left=rel_match.group("left"),
                right=rel_match.group("right"),
                left_card=_LEFT_SYMBOLS[left_sym],
                right_card=_RIGHT_SYMBOLS[right_sym],
                label=label or None,
            )
            model.relationships.append(relationship)
            pending_relationships.append((line_no, relationship))
            continue

        if _is_ignored_directive(lowered):
            continue

        if lowered.startswith("entity"):
            raise _error(
                line_no,
                "unsupported entity declaration: " + repr(line) + " (expected 'entity Name {')",
            )

        raise _error(line_no, "unsupported syntax: " + repr(line))

    # Check start/end markers and entity braces after reading all lines.
    if not started:
        raise ParseError("missing @startuml")
    if current_entity is not None:
        raise _error(
            current_start_line,
            'entity "' + current_entity.name + '" is never closed with "}"',
        )
    if not ended:
        raise ParseError("missing @enduml")

    # Verify relationship targets after all entities have been collected.
    for line_no, relationship in pending_relationships:
        for endpoint in (relationship.left, relationship.right):
            if model.get_entity(endpoint) is None:
                raise _error(
                    line_no,
                    'relationship refers to undefined entity "' + endpoint + '"',
                )

    _infer_references(model)
    return model


def _parse_attribute(line: str, line_no: int) -> Attribute:
    """
    Parse one attribute line inside an entity block into an Attribute.

    Reads optional leading *, attribute name, type, and <<PK>> / <<FK>>
    stereotypes. Raises ParseError on bad syntax or unsupported stereotypes.
    """
    match = _ATTRIBUTE_RE.match(line)
    if match is None:
        raise _error(
            line_no,
            "unsupported attribute syntax: "
            + repr(line)
            + " (expected '[*] name : type [<<PK>>] [<<FK>>]')",
        )

    is_pk = False
    is_fk = False
    raw_stereotypes: str | None = match.group("stereotypes")
    stereotypes_str: str = raw_stereotypes if raw_stereotypes is not None else ""
    stereotype_blocks: list[str] = _STEREOTYPE_RE.findall(stereotypes_str)

    block: str
    for block in stereotype_blocks:
        raw_tag: str
        for raw_tag in block.split(","):
            cleaned_tag: str = raw_tag.strip()
            tag: str = cleaned_tag.upper()
            if not tag:
                continue
            if tag == "PK":
                is_pk = True
            elif tag == "FK":
                is_fk = True
            else:
                raise _error(
                    line_no,
                    "unsupported stereotype <<"
                    + cleaned_tag
                    + ">> (only PK and FK are supported)",
                )

    raw_type: str | None = match.group("type")
    attr_type: str = raw_type.strip() if raw_type is not None else ""
    attr_name: str = match.group("name")
    is_mandatory: bool = match.group("mandatory") is not None

    return Attribute(
        name=attr_name,
        type=attr_type,
        is_pk=is_pk,
        is_fk=is_fk,
        mandatory=is_mandatory,
    )


def _infer_references(model: DiagramModel) -> None:
    """
    Fill in Attribute.references by matching FK names to related PKs.

    Checks both directions of each non-self-referential relationship and sets
    fk.references to "TargetEntity.pk_name" when an FK name matches a PK name
    on the other entity. Leaves fk.references as None if no match is found.
    """
    for relationship in model.relationships:
        if relationship.left == relationship.right:
            continue

        pairs = (
            (relationship.left, relationship.right),
            (relationship.right, relationship.left),
        )
        for owner_name, target_name in pairs:
            owner = model.get_entity(owner_name)
            target = model.get_entity(target_name)
            if owner is None or target is None:
                continue

            for fk in owner.foreign_keys:
                if fk.references is not None:
                    continue
                matched_pk = next(
                    (pk for pk in target.primary_keys if pk.name == fk.name),
                    None,
                )
                if matched_pk is not None:
                    fk.references = target.name + "." + matched_pk.name