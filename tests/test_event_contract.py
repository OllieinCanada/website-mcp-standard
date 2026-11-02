"""Regression coverage for MCPWP-EVT-001/003 and MCPWP-RES-001/011."""

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


class EventContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators = {}
        cls.examples = {}
        for tool in ("get_event", "get_events"):
            schema = load_json(ROOT / "schemas" / "extended" / f"{tool}.output.json")
            Draft202012Validator.check_schema(schema)
            cls.validators[tool] = Draft202012Validator(schema, format_checker=FormatChecker())
            cls.examples[tool] = load_json(ROOT / "examples" / "consultancy" / f"{tool}.json")

    def test_published_examples_preserve_outcome_and_lifecycle(self):
        for tool, example in self.examples.items():
            with self.subTest(tool=tool):
                self.validators[tool].validate(example)
                self.assertEqual(example["status"], "ok")
        self.assertEqual(self.examples["get_event"]["event_status"], "scheduled")
        self.assertEqual(self.examples["get_events"]["events"][0]["event_status"], "scheduled")

    def test_success_requires_event_metadata_and_content(self):
        for field in ("id", "name", "url", "start", "content", "content_format"):
            example = copy.deepcopy(self.examples["get_event"])
            del example[field]
            with self.subTest(field=field):
                self.assertFalse(self.validators["get_event"].is_valid(example))

    def test_error_outcomes_require_message_without_event_details(self):
        for status in ("not_found", "invalid_request", "rate_limited", "unavailable", "internal_error"):
            with self.subTest(status=status):
                self.validators["get_event"].validate({"status": status, "error": {"message": "Try again"}})
                self.assertFalse(self.validators["get_event"].is_valid({"status": status}))
                self.assertFalse(self.validators["get_event"].is_valid({"status": status, "error": {}}))

    def test_lifecycle_cannot_replace_call_outcome(self):
        for status in ("scheduled", "postponed", "rescheduled", "cancelled", "sold_out", "completed"):
            with self.subTest(status=status):
                self.assertFalse(self.validators["get_event"].is_valid({"status": status}))
                example = copy.deepcopy(self.examples["get_event"])
                example["status"] = status
                self.assertFalse(self.validators["get_event"].is_valid(example))

    def test_lifecycle_values_are_consistent_between_list_and_detail(self):
        for status in ("scheduled", "postponed", "rescheduled", "cancelled", "sold_out", "completed"):
            for tool, original in self.examples.items():
                example = copy.deepcopy(original)
                event = example if tool == "get_event" else example["events"][0]
                event["event_status"] = status
                with self.subTest(status=status, tool=tool):
                    self.validators[tool].validate(example)

    def test_lifecycle_is_optional_but_validated_when_present(self):
        for tool, original in self.examples.items():
            example = copy.deepcopy(original)
            event = example if tool == "get_event" else example["events"][0]
            del event["event_status"]
            with self.subTest(tool=tool):
                self.validators[tool].validate(example)
                event["event_status"] = "unknown"
                self.assertFalse(self.validators[tool].is_valid(example))

    def test_event_times_require_a_utc_offset(self):
        example = copy.deepcopy(self.examples["get_event"])
        example["start"] = "2026-11-19T08:00:00"
        self.assertFalse(self.validators["get_event"].is_valid(example))

    def test_duplicate_keys_are_rejected_when_loading_regression_fixtures(self):
        for source in ('{"status":"ok","status":"scheduled"}', '{"event":{"id":"a","id":"b"}}'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                json.loads(source, object_pairs_hook=unique_object)


if __name__ == "__main__":
    unittest.main()
