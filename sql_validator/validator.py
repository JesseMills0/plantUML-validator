from collections import defaultdict
from typing import Mapping, Optional

from .models import Config, ForeignKey, Schema, Table, ValidationResult, Violation


def _enabled(config, rule):
    return config.rules.get(rule, {}).get("enabled", False)


def _violation(config, rule, message, **kwargs):
    if not _enabled(config, rule):
        return None
    return Violation(rule, str(config.rules[rule].get("severity", "error")), message, **kwargs)


def _is_key(table: Table, columns):
    return columns == table.primary_key or columns in table.unique_keys


def _junction(table: Table):
    return len(table.columns) >= 2 and len(table.foreign_keys) < 2 and len(table.primary_key) >= 2


def validate(schema: Schema, config: Optional[Config] = None,
             sample_data: Optional[Mapping[str, list]] = None) -> ValidationResult:
    config = config or Config()
    violations = []
    graph = defaultdict(set)
    for table in schema.tables.values():
        for fk in table.foreign_keys:
            graph[table.name].add(fk.ref_table)
            target = schema.tables.get(fk.ref_table)
            if not target or not _is_key(target, fk.ref_columns):
                item = _violation(config, "FK_REFERENCES_KEY",
                    f"{table.name}({', '.join(fk.columns)}) references non-key "
                    f"columns {fk.ref_table}({', '.join(fk.ref_columns)})",
                    table=table.name, columns=tuple(fk.columns), ref_table=fk.ref_table)
                if item: violations.append(item)
            if target:
                for local, remote in zip(fk.columns, fk.ref_columns):
                    if local in table.columns and remote in target.columns:
                        if table.columns[local].data_type != target.columns[remote].data_type:
                            item = _violation(config, "FK_TYPE_MISMATCH",
                                f"{table.name}.{local} type does not match {fk.ref_table}.{remote}",
                                table=table.name, columns=(local,), ref_table=fk.ref_table)
                            if item: violations.append(item)
            if fk.on_delete == "SET NULL" and any(
                not table.columns.get(col, type("Missing", (), {"nullable": True})()).nullable
                for col in fk.columns
            ):
                item = _violation(config, "SET_NULL_NOT_NULL",
                    f"{table.name} FK uses ON DELETE SET NULL on NOT NULL columns",
                    table=table.name, columns=tuple(fk.columns), ref_table=fk.ref_table)
                if item: violations.append(item)
            if len(fk.columns) != len(fk.ref_columns) or (
                target and len(fk.columns) > 1 and fk.ref_columns != target.primary_key
            ):
                item = _violation(config, "COMPOSITE_FK_MISMATCH",
                    f"{table.name} composite FK does not match {fk.ref_table} primary key",
                    table=table.name, columns=tuple(fk.columns), ref_table=fk.ref_table)
                if item: violations.append(item)
        if _junction(table):
            item = _violation(config, "JUNCTION_MISSING_FK",
                f"{table.name} appears to be a junction table but has fewer than two foreign keys",
                table=table.name)
            if item: violations.append(item)

    def reaches(start, current, seen):
        if current == start:
            return True
        if current in seen:
            return False
        return any(reaches(start, child, seen | {current}) for child in graph[current])
    for table in list(graph):
        if any(reaches(table, child, {table}) for child in graph[table]):
            item = _violation(config, "CIRCULAR_FK",
                f"Foreign keys create a circular dependency involving {table}", table=table)
            if item: violations.append(item)
            break
    if sample_data:
        violations.extend(_data_violations(schema, config, sample_data))
    return ValidationResult(violations)


def _data_violations(schema, config, sample_data):
    result = []
    for table in schema.tables.values():
        if len(table.foreign_keys) != 2 or not table.primary_key:
            continue
        rows = sample_data.get(table.name, [])
        if not rows:
            continue
        fk1, fk2 = table.foreign_keys
        pairs = {(tuple(row.get(c) for c in fk1.columns), tuple(row.get(c) for c in fk2.columns))
                 for row in rows}
        left = defaultdict(set)
        right = defaultdict(set)
        for one, two in pairs:
            left[one].add(two)
            right[two].add(one)
        bad = sum(len(values) > 1 for values in left.values()) + sum(len(values) > 1 for values in right.values())
        rate = bad / max(1, len(left) + len(right))
        if rate > config.violation_rate_threshold:
            item = _violation(config, "DATA_CARDINALITY",
                f"{table.name} sample data indicates many-to-many cardinality (rate {rate:.2f})",
                table=table.name)
            if item: result.append(item)
    return result
