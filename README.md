# SQL Validator

`sql-validator` checks `CREATE TABLE` statements against configurable schema
integrity rules and emits a PASS/FAIL result plus a Mermaid ER diagram.

## Usage

```bash
sql-validator schema.sql --config rules.json --data-dir sample-data
```

CSV files in `sample-data` are named after their tables (for example,
`enrollments.csv`). A configuration file can enable or disable rule IDs and
set the data-aware violation threshold:

```json
{
  "violation_rate_threshold": 0.1,
  "rules": {
    "CIRCULAR_FK": {"enabled": false},
    "DATA_CARDINALITY": {"severity": "warning", "enabled": true}
  }
}
```

The supported rules are `FK_REFERENCES_KEY`, `FK_TYPE_MISMATCH`,
`CIRCULAR_FK`, `JUNCTION_MISSING_FK`, `SET_NULL_NOT_NULL`,
`COMPOSITE_FK_MISMATCH`, and `DATA_CARDINALITY`.
