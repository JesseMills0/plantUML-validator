import re
from typing import Iterable

import sqlglot

from .models import Column, ForeignKey, Schema, Table


def _clean(value: str) -> str:
    return value.strip().strip("`\"[]").lower()


def _parts(value: str):
    return [_clean(part) for part in value.split(",") if part.strip()]


def _definitions(body: str):
    result, current, depth = [], [], 0
    for char in body:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        result.append("".join(current).strip())
    return result


def _parse_create(statement: str, schema: Schema):
    match = re.search(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([^\s(]+)\s*\((.*)\)\s*;?\s*$",
                      statement, re.I | re.S)
    if not match:
        return
    table_name = _clean(match.group(1))
    table = Table(table_name)
    definitions = _definitions(match.group(2))
    pending_fks = []
    for definition in definitions:
        text = re.sub(r"\s+", " ", definition.strip())
        upper = text.upper()
        if upper.startswith(("PRIMARY KEY", "CONSTRAINT")) and "PRIMARY KEY" in upper:
            key = re.search(r"PRIMARY\s+KEY\s*\(([^)]*)\)", text, re.I)
            if key:
                table.primary_key = _parts(key.group(1))
            continue
        if upper.startswith(("UNIQUE", "CONSTRAINT")) and re.search(r"\bUNIQUE\b", text, re.I):
            key = re.search(r"UNIQUE\s*(?:KEY|INDEX)?\s*\(([^)]*)\)", text, re.I)
            if key:
                table.unique_keys.append(_parts(key.group(1)))
            continue
        fk = re.search(
            r"(?:constraint\s+\S+\s+)?foreign\s+key\s*\(([^)]*)\)\s*"
            r"references\s+([^\s(]+)\s*\(([^)]*)\)(.*)",
            text, re.I,
        )
        if fk:
            on_delete = re.search(r"on\s+delete\s+(cascade|restrict|set\s+null|set\s+default|no\s+action)",
                                  fk.group(4), re.I)
            pending_fks.append(ForeignKey(
                table_name, _parts(fk.group(1)), _clean(fk.group(2)), _parts(fk.group(3)),
                on_delete.group(1).upper() if on_delete else None,
            ))
            continue
        column = re.match(r"([^\s]+)\s+([^\s]+(?:\s*\([^)]*\))?)\s*(.*)", text, re.I)
        if not column:
            continue
        name, data_type, constraints = _clean(column.group(1)), column.group(2).upper(), column.group(3).upper()
        table.columns[name] = Column(
            name, data_type, "NOT NULL" not in constraints,
            "PRIMARY KEY" in constraints, "UNIQUE" in constraints,
        )
        if table.columns[name].primary_key:
            table.primary_key.append(name)
        if table.columns[name].unique:
            table.unique_keys.append([name])
        inline_fk = re.search(r"references\s+([^\s(]+)\s*\(([^)]*)\)(.*)", constraints, re.I)
        if inline_fk:
            on_delete = re.search(r"on\s+delete\s+(cascade|restrict|set\s+null|set\s+default|no\s+action)",
                                  inline_fk.group(3), re.I)
            pending_fks.append(ForeignKey(table_name, [name], _clean(inline_fk.group(1)),
                                          _parts(inline_fk.group(2)),
                                          on_delete.group(1).upper() if on_delete else None))
    table.foreign_keys.extend(pending_fks)
    schema.tables[table_name] = table


def parse_schema(sql: str) -> Schema:
    """Parse CREATE TABLE statements using sqlglot's statement boundaries."""
    schema = Schema()
    try:
        statements = sqlglot.parse(sql)
        sources = [statement.sql() for statement in statements]
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Unable to parse SQL: {exc}") from exc
    for statement in sources:
        if re.match(r"\s*create\s+table\b", statement, re.I):
            _parse_create(statement, schema)
    return schema

