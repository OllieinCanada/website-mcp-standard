"""Regression coverage for MCPWP-EVT-001/003 and MCPWP-RES-001/011."""

import copy
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from tools.validate_examples import load as load_json


ROOT = Path(__file__).resolve().parents[1]


class EventContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators = {}
        cls.schemas = {}
        cls.examples = {}
        for tool in ("get_event", "get_events"):
            schema = load_json(ROOT / "schemas" / "extended" / f"{tool}.output.json")
            Draft202012Validator.check_schema(schema)
            cls.schemas[tool] = schema
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
        invalid = (
            "2026-11-20T08:00:00", "2026-11-20", "2026-11-20T08:00:00+0800",
            "2026-11-20T08:00:00+08", "2026-11-20T08:00:00Z\n",
            "2026-11-20T08:00:00+00:00 ",
        )
        self.check_event_times(invalid, False)

    def test_event_times_accept_utc_and_numeric_offsets(self):
        valid = (
            "2026-11-20T08:00:00Z", "2026-11-20T08:00:00z",
            "2026-11-20T08:00:00.123+05:30", "2026-11-20T08:00:00-08:00",
        )
        self.check_event_times(valid, True)

    def check_event_times(self, values, expected):
        for tool in self.schemas:
            for validator in (self.validators[tool], Draft202012Validator(self.schemas[tool])):
                for field in ("start", "end"):
                    for value in values:
                        example = copy.deepcopy(self.examples[tool])
                        event = example if tool == "get_event" else example["events"][0]
                        event.update(start="2026-11-19T00:00:00Z", end="2026-11-21T00:00:00Z")
                        event[field] = value
                        with self.subTest(tool=tool, field=field, value=value,
                                          formats=validator.format_checker is not None):
                            self.assertEqual(validator.is_valid(example), expected)

    def test_end_remains_optional(self):
        for tool in self.schemas:
            example = copy.deepcopy(self.examples[tool])
            event = example if tool == "get_event" else example["events"][0]
            del event["end"]
            with self.subTest(tool=tool):
                self.validators[tool].validate(example)

    def test_error_enum_matches_event_listing_until_shared_cleanup(self):
        detail = self.schemas["get_event"]["properties"]["status"]["enum"]
        listing = self.schemas["get_events"]["properties"]["status"]["enum"]
        self.assertEqual(set(detail), set(listing))
        for status in ("unauthorized", "forbidden"):
            with self.subTest(status=status):
                self.validators["get_event"].validate({"status": status, "error": {"message": "Unavailable"}})
                self.assertFalse(self.validators["get_event"].is_valid({"status": status}))


if __name__ == "__main__":
    unittest.main()
