"""Helpers shared by the rule implementations."""

from __future__ import annotations

from collections.abc import Callable

from validator.model import DiagramModel, Relationship, Violation

# Every rule is a function from a parsed diagram to its violations.
Rule = Callable[[DiagramModel], list[Violation]]


def parent_and_child(relationship: Relationship) -> tuple[str, str] | None:
    """
    Return (parent, child) entity names for a one-to-many relationship.

    The child is the entity at the "many" end (it holds the FK) and the parent
    is the entity at the "one" end. Returns None if the relationship is not
    one-to-many (one-to-one or many-to-many).
    """
    left_many = relationship.left_card.is_many
    right_many = relationship.right_card.is_many
    if left_many == right_many:
        return None
    if left_many:
        return relationship.right, relationship.left
    return relationship.left, relationship.right


def referenced_entity(reference: str | None) -> str | None:
    """Return the entity part of an "Entity.pk_name" reference, or None."""
    if reference is None:
        return None
    return reference.split(".", 1)[0]


def describe(relationship: Relationship) -> str:
    """Short label for a relationship, used as a violation target."""
    return f"{relationship.left} -- {relationship.right}"
