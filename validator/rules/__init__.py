"""Rule registry: maps a rule ID (as used in configs/*.yaml) to its check function."""

from __future__ import annotations

from validator.rules import (
    r1_missing_primary_key,
    r2_fk_on_wrong_side,
    r3_fk_relationship_mismatch,
    r4_fk_type_mismatch,
    r5_many_to_many_without_junction,
    r6_mandatory_cycle,
    r7_fk_mandatory_marker_mismatch,
    r8_duplicate_relationship,
    r9_orphan_entity,
    r10_pk_not_mandatory,
    r11_duplicate_attribute_name,
)
from validator.rules._common import Rule

RULES: dict[str, Rule] = {
    "R1": r1_missing_primary_key.check,
    "R2": r2_fk_on_wrong_side.check,
    "R3": r3_fk_relationship_mismatch.check,
    "R4": r4_fk_type_mismatch.check,
    "R5": r5_many_to_many_without_junction.check,
    "R6": r6_mandatory_cycle.check,
    "R7": r7_fk_mandatory_marker_mismatch.check,
    "R8": r8_duplicate_relationship.check,
    "R9": r9_orphan_entity.check,
    "R10": r10_pk_not_mandatory.check,
    "R11": r11_duplicate_attribute_name.check,
}


def get_rule(rule_id: str) -> Rule:
    """Return the check function for a rule ID, or raise a clear KeyError."""
    try:
        return RULES[rule_id]
    except KeyError:
        known = ", ".join(RULES)
        raise KeyError(
            f"unknown rule {rule_id!r} (implemented rules: {known})"
        ) from None
