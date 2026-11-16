import argparse
import csv
import json
from pathlib import Path

from .models import Config
from .parser import parse_schema
from .render import mermaid_er
from .validator import validate


def _load_csv(directory):
    if not directory:
        return {}
    data = {}
    for path in Path(directory).glob("*.csv"):
        with path.open(newline="") as stream:
            data[path.stem.lower()] = list(csv.DictReader(stream))
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a SQL database schema.")
    parser.add_argument("sql_file", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--data-dir", type=Path, help="Directory containing table-name.csv files")
    parser.add_argument("--mermaid", type=Path, help="Write the Mermaid ER diagram to this file")
    args = parser.parse_args(argv)
    config = Config.from_dict(json.loads(args.config.read_text())) if args.config else Config()
    result = validate(parse_schema(args.sql_file.read_text()), config, _load_csv(args.data_dir))
    print("PASS" if result.passed else "FAIL")
    for violation in result.violations:
        print(f"[{violation.severity.upper()}] {violation.rule_id}: {violation.message}")
    diagram = mermaid_er(parse_schema(args.sql_file.read_text()), result.violations)
    if args.mermaid:
        args.mermaid.write_text(diagram + "\n")
    else:
        print("\n" + diagram)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
