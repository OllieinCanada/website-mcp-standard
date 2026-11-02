"""Exercise duplicate-key handling through the production loader and CLI."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.validate_examples import load


ROOT = Path(__file__).resolve().parents[1]


class ExampleLoaderTests(unittest.TestCase):
    def test_production_loader_rejects_duplicate_keys(self):
        payloads = (
            '{"status":"ok","status":"scheduled"}',
            '{"event":{"id":"a","id":"b"}}',
            '{"id":"a","\\u0069d":"b"}',
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            for payload in payloads:
                path.write_text(payload, encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "duplicate object member"):
                    load(path)

    def test_identical_names_in_distinct_objects_are_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text('{"first":{"id":"a"},"second":{"id":"b"}}', encoding="utf-8")
            self.assertEqual(load(path), {"first": {"id": "a"}, "second": {"id": "b"}})

    def test_validator_cli_rejects_duplicate_schema_and_example_keys(self):
        # Run an exact copy of the production program against isolated inputs,
        # preserving its default ROOT-based discovery without new CLI options.
        for duplicate in ("schema", "example", None):
            with self.subTest(duplicate=duplicate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in ("tools", "schemas", "examples"):
                    (root / name).mkdir()
                script = root / "tools/validate_examples.py"
                shutil.copyfile(ROOT / "tools/validate_examples.py", script)
                schema = '{"type":"object","required":["status"],"properties":{"status":{"const":"ok"}}}'
                example = '{"status":"ok"}'
                if duplicate == "schema":
                    schema = schema[:-1] + ',"type":"object"}'
                elif duplicate == "example":
                    example = '{"status":"wrong","status":"ok"}'
                (root / "schemas/sample.output.json").write_text(schema, encoding="utf-8")
                (root / "examples/sample.json").write_text(example, encoding="utf-8")
                result = subprocess.run([sys.executable, str(script)], cwd=root,
                                        capture_output=True, text=True, timeout=20)
                if duplicate:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("duplicate object member", result.stdout + result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("PASS examples/sample.json", result.stdout)

    def test_published_examples_pass_the_production_cli(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/validate_examples.py")],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sum(line.startswith("PASS ") for line in result.stdout.splitlines()), 27)


if __name__ == "__main__":
    unittest.main()
