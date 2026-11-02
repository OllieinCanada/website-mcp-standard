"""Exercise validation failures through the actual command-line exit status."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from jsonschema import FormatChecker
from tools.validate_examples import load, load_schemas, make_validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate_examples.py"
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["status"],
    "properties": {"status": {"const": "ok"}},
}


class ValidatorCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.schemas = self.root / "schemas"
        self.examples = self.root / "examples"
        self.schemas.mkdir()
        self.examples.mkdir()
        self.write_schema(SCHEMA)
        self.write_example('{"status":"ok"}')

    def write_schema(self, schema, name="sample.output.json"):
        (self.schemas / name).write_text(json.dumps(schema), encoding="utf-8")

    def write_example(self, text, name="sample.json"):
        (self.examples / name).write_text(text, encoding="utf-8")

    def run_cli(self, expected=0, text=""):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--schemas", str(self.schemas),
             "--examples", str(self.examples)],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertIn(text, result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        return result.stdout

    def test_valid_example_and_variant_are_counted(self):
        self.write_example('{"status":"ok"}', "sample.other.json")
        output = self.run_cli(text="2 examples discovered; 2 validated")
        self.assertIn("0 failing example(s)", output)

    def test_duplicate_key_is_rejected_at_every_depth(self):
        for payload in ('{"status":"wrong","status":"ok"}',
                        '{"status":"ok","nested":{"x":1,"x":2}}'):
            with self.subTest(payload=payload):
                self.write_example(payload)
                self.run_cli(1, "duplicate object member")

    def test_invalid_json_and_non_json_numbers_are_rejected(self):
        for payload in ('{"status":', '{"status":"ok","n":NaN}',
                        '{"status":"ok","n":Infinity}'):
            with self.subTest(payload=payload):
                self.write_example(payload)
                self.run_cli(1, "FAIL")

    def test_invalid_output_is_rejected(self):
        self.write_example('{"status":"wrong"}')
        self.run_cli(1, "1 failing example(s)")

    def test_unmapped_example_is_failure(self):
        self.write_example("{}", "typo.json")
        self.run_cli(1, "1 unmapped")

    def test_empty_and_missing_discovery_fail(self):
        for path in self.schemas.iterdir():
            path.unlink()
        for path in self.examples.iterdir():
            path.unlink()
        output = self.run_cli(1, "no JSON schemas discovered")
        self.assertIn("no JSON examples discovered", output)
        self.schemas.rmdir()
        self.examples.rmdir()
        self.run_cli(1, "no JSON schemas discovered")

    def test_no_output_schema_fails(self):
        (self.schemas / "sample.output.json").rename(self.schemas / "sample.input.json")
        self.run_cli(1, "no usable output schemas")

    def test_invalid_schema_and_malformed_schema_fail(self):
        for content in ('{"type":42}', '{"type":"object","type":"string"}', '{'):
            with self.subTest(content=content):
                (self.schemas / "sample.output.json").write_text(content, encoding="utf-8")
                self.run_cli(1, "schema/discovery error(s)")

    def test_duplicate_tool_mapping_fails(self):
        nested = self.schemas / "nested"
        nested.mkdir()
        (nested / "sample.output.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
        self.run_cli(1, "duplicate output schema")

    def test_input_schemas_are_checked_too(self):
        self.write_schema({"type": 42}, "sample.input.json")
        self.run_cli(1, "1 schema/discovery error(s)")

    def test_boolean_output_schema_is_supported(self):
        self.write_schema(False)
        self.run_cli(1, "False schema")

    def test_formats_are_checked(self):
        self.write_schema({"type": "string", "format": "date-time"})
        self.write_example('"2026-11-02T10:00:00"')
        self.run_cli(1, "date-time")

    def test_external_refs_fail_without_network_access(self):
        self.write_schema({"$ref": "https://example.invalid/schema.json"})
        self.run_cli(1, "Unresolvable")

    def test_mixed_error_paths_do_not_crash_sorting(self):
        self.write_schema({"type": "object", "additionalProperties": {
            "anyOf": [{"type": "object", "additionalProperties": {"type": "integer"}},
                      {"type": "array", "items": {"type": "integer"}}]}})
        self.write_example('{"a":{"x":"bad"},"b":["bad"]}')
        self.run_cli(1, "1 failing example(s)")

    def test_load_schemas_exposes_strict_catalog(self):
        self.assertEqual(load_schemas(self.schemas), {"sample": SCHEMA})
        self.write_schema({"type": 42}, "broken.input.json")
        with self.assertRaises(ValueError):
            load_schemas(self.schemas)

    def test_strict_loader_keeps_valid_nested_objects(self):
        path = self.examples / "sample.json"
        self.write_example('{"a":{"x":1},"b":{"x":2}}')
        self.assertEqual(load(path), {"a": {"x": 1}, "b": {"x": 2}})

    def test_make_validator_checks_date_time_offsets(self):
        validator = make_validator({"type": "string", "format": "date-time"})
        self.assertTrue(validator.is_valid("2026-11-02T10:00:00Z"))
        self.assertFalse(validator.is_valid("2026-11-02T10:00:00"))

    def test_missing_format_extras_fail_explicitly(self):
        checkers = dict(FormatChecker.checkers)
        del checkers["date-time"]
        with mock.patch.object(FormatChecker, "checkers", checkers):
            with self.assertRaisesRegex(ValueError, "install requirements-dev.txt"):
                make_validator(SCHEMA)


if __name__ == "__main__":
    unittest.main()
