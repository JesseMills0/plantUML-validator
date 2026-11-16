import unittest

from sql_validator import Config, parse_schema, validate

class ValidatorTests(unittest.TestCase):
    def test_schema_rules_and_cycle(self):
        schema = parse_schema("""
            CREATE TABLE a (id INTEGER PRIMARY KEY, b_id INTEGER NOT NULL,
              FOREIGN KEY (b_id) REFERENCES b(id) ON DELETE SET NULL);
            CREATE TABLE b (id TEXT PRIMARY KEY, a_id TEXT,
              FOREIGN KEY (a_id) REFERENCES a(id));
        """)
        rule_ids = {item.rule_id for item in validate(schema).violations}
        self.assertTrue({"FK_TYPE_MISMATCH", "SET_NULL_NOT_NULL", "CIRCULAR_FK"} <= rule_ids)

    def test_disabled_rules_are_respected(self):
        schema = parse_schema("CREATE TABLE child (id INTEGER, parent_id INTEGER, "
                              "FOREIGN KEY(parent_id) REFERENCES parent(id));")
        config = Config.from_dict({"rules": {"FK_REFERENCES_KEY": {"enabled": False}}})
        self.assertFalse(any(v.rule_id == "FK_REFERENCES_KEY"
                             for v in validate(schema, config).violations))

    def test_mermaid_can_be_generated(self):
        from sql_validator.render import mermaid_er
        schema = parse_schema("CREATE TABLE parent (id INTEGER PRIMARY KEY); "
                              "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER, "
                              "FOREIGN KEY(parent_id) REFERENCES parent(id));")
        self.assertIn("erDiagram", mermaid_er(schema, validate(schema).violations))
