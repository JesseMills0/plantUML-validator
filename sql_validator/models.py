from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Column:
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False


@dataclass
class ForeignKey:
    table: str
    columns: List[str]
    ref_table: str
    ref_columns: List[str]
    on_delete: Optional[str] = None


@dataclass
class Table:
    name: str
    columns: Dict[str, Column] = field(default_factory=dict)
    primary_key: List[str] = field(default_factory=list)
    unique_keys: List[List[str]] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)


@dataclass
class Schema:
    tables: Dict[str, Table] = field(default_factory=dict)


DEFAULT_RULES = {
    "FK_REFERENCES_KEY": {"severity": "error", "enabled": True},
    "FK_TYPE_MISMATCH": {"severity": "error", "enabled": True},
    "CIRCULAR_FK": {"severity": "error", "enabled": True},
    "JUNCTION_MISSING_FK": {"severity": "error", "enabled": True},
    "SET_NULL_NOT_NULL": {"severity": "error", "enabled": True},
    "COMPOSITE_FK_MISMATCH": {"severity": "error", "enabled": True},
    "DATA_CARDINALITY": {"severity": "warning", "enabled": True},
}


@dataclass
class Config:
    rules: Dict[str, Dict[str, object]] = field(
        default_factory=lambda: {key: value.copy() for key, value in DEFAULT_RULES.items()}
    )
    violation_rate_threshold: float = 0.0

    @classmethod
    def from_dict(cls, value):
        rules = {key: item.copy() for key, item in DEFAULT_RULES.items()}
        rules.update(value.get("rules", {}))
        return cls(rules, float(value.get("violation_rate_threshold", 0.0)))


@dataclass
class Violation:
    rule_id: str
    severity: str
    message: str
    table: Optional[str] = None
    columns: Tuple[str, ...] = ()
    ref_table: Optional[str] = None


@dataclass
class ValidationResult:
    violations: List[Violation]

    @property
    def passed(self):
        return not any(v.severity.lower() == "error" for v in self.violations)

