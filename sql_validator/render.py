from .models import Schema, Violation


def mermaid_er(schema: Schema, violations: list[Violation]) -> str:
    flagged = {v.table for v in violations} | {v.ref_table for v in violations}
    lines = ["erDiagram"]
    for table in schema.tables.values():
        lines.append(f"    {table.name} {{")
        for column in table.columns.values():
            marker = " PK" if column.name in table.primary_key else ""
            lines.append(f"        {column.data_type} {column.name}{marker}")
        lines.append("    }")
    for table in schema.tables.values():
        for fk in table.foreign_keys:
            lines.append(f"    {table.name} }}o--|| {fk.ref_table} : "
                         f"\"FK {', '.join(fk.columns)}\"")
    if flagged:
        lines.append("    %% Violations: " + ", ".join(sorted(flagged)))
    return "\n".join(lines)
