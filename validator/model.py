"""Shared data model for the ER diagram validator.

This file is the contract between the parser, writer, rules, and tools.
Do not change it without the whole team agreeing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import override


@dataclass
class Attribute:
    """A single attribute (column) of an entity in a UML diagram.
    
    Ex: `customer_id : int <<FK>> is an attribute with name "customer_id", 
    type "int",and is a foreign key.
    """

    name: str
    type: str
    is_pk: bool = False
    is_fk: bool = False
    mandatory: bool = False
    # For an FK: the primary key it points to, written "Entity.attribute".
    # None if unknown (see the note in the team chat about how this gets filled).
    references: str | None = None


@dataclass
class Entity:
    """Represents one box in a UML diagram.
    Has a name (ex. Order) and a list of attributes (columns).
    """

    name: str
    attributes: list[Attribute] = field(default_factory=list)

    @property
    def primary_keys(self) -> list[Attribute]:
        return [a for a in self.attributes if a.is_pk]

    @property
    def foreign_keys(self) -> list[Attribute]:
        return [a for a in self.attributes if a.is_fk]

    def get_attribute(self, name: str) -> Attribute | None:
        """Return the attribute with this name, or None."""
        for attr in self.attributes:
            if attr.name == name:
                return attr
        return None


class Cardinality(Enum):
    """One end of a relationship line (crow's-foot notation).

    The PlantUML symbols for a value differ depending on which side of the
    line they sit on, mapping is done by the UML parser.
    """

    EXACTLY_ONE = "exactly_one"      # ||
    ZERO_OR_ONE = "zero_or_one"      # |o (left end), o| (right end)
    ONE_OR_MORE = "one_or_more"      # }| (left end), |{ (right end)
    ZERO_OR_MORE = "zero_or_more"    # }o (left end), o{ (right end)

    @property
    def is_many(self) -> bool:
        """True if this end allows more than one instance."""
        return self in (Cardinality.ONE_OR_MORE, Cardinality.ZERO_OR_MORE)

    @property
    def is_mandatory(self) -> bool:
        """True if this end requires at least one instance."""
        return self in (Cardinality.EXACTLY_ONE, Cardinality.ONE_OR_MORE)


@dataclass
class Relationship:
    """A relationship line between two entities.
    Each cardinality describes the marker on that end of the line: how many
    instances of that entity relate to one instance of the other entity.
    
    Example: `Customer ||--o{ Order` is
        left="Customer", left_card=EXACTLY_ONE,
        right="Order",   right_card=ZERO_OR_MORE
    (each order has exactly one customer; a customer has zero or more orders).
    """

    left: str
    right: str
    left_card: Cardinality
    right_card: Cardinality
    label: str | None = None

    @property
    def is_many_to_many(self) -> bool:
        return self.left_card.is_many and self.right_card.is_many


@dataclass
class DiagramModel:
    """A whole parsed ER diagram."""

    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def get_entity(self, name: str) -> Entity | None:
        """Return the entity with this name, or None."""
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None

    def relationships_of(self, entity_name: str) -> list[Relationship]:
        """Return every relationship that has this entity on either end."""
        return [
            r for r in self.relationships
            if entity_name in (r.left, r.right)
        ]


@dataclass
class Violation:
    """One problem a rule found in a diagram."""

    rule_id: str      # "R1", "R2", ...
    severity: str     # "ERROR" or "WARN"
    target: str       # entity, attribute ("Order.customer_id"), or relationship
    message: str

    @override
    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule_id}  {self.message}"