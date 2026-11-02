"""MCPWP-DECL-002 and public-tool result contract regressions."""

import copy
import itertools
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class DeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = load_json(ROOT / "schemas" / "core" / "get_site_info.output.json")
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        cls.example = load_json(ROOT / "examples" / "personal-blog" / "get_site_info.json")

    def test_levels_match_every_combination_of_modules(self):
        optional_modules = ("insights", "service_details", "people", "events", "x-retail", "transactions")
        for present in itertools.product((False, True), repeat=len(optional_modules)):
            modules = ["core"] + [module for module, included in zip(optional_modules, present) if included]
            for extended, transactional in itertools.product((False, True), repeat=2):
                levels = ["core"]
                if extended:
                    levels.append("extended")
                if transactional:
                    levels.append("transactional")
                example = copy.deepcopy(self.example)
                example["mcpwp"]["modules"] = modules
                example["mcpwp"]["levels"] = levels
                expected = (extended == any(module not in ("core", "transactions") for module in modules)
                            and transactional == ("transactions" in modules))
                with self.subTest(levels=levels, modules=modules):
                    self.assertEqual(self.validator.is_valid(example), expected)

    def test_site_specific_tools_do_not_imply_an_extended_module(self):
        example = copy.deepcopy(self.example)
        example["mcpwp"]["extensions"] = [{"tool": "get_company_profile"}]
        self.validator.validate(example)

    def test_core_remains_required_and_arrays_are_unique(self):
        for field in ("levels", "modules"):
            for value in ([], ["core", "core"]):
                example = copy.deepcopy(self.example)
                example["mcpwp"][field] = value
                with self.subTest(field=field, value=value):
                    self.assertFalse(self.validator.is_valid(example))

    def test_unknown_or_malformed_modules_remain_invalid(self):
        for module in ("unknown", "x-", "x-Retail"):
            example = copy.deepcopy(self.example)
            example["mcpwp"]["modules"].append(module)
            example["mcpwp"]["levels"].append("extended")
            with self.subTest(module=module):
                self.assertFalse(self.validator.is_valid(example))

    def test_published_site_declarations_validate(self):
        for path in sorted((ROOT / "examples").glob("*/get_site_info.json")):
            with self.subTest(path=path):
                self.validator.validate(load_json(path))


class PublicOutcomeTests(unittest.TestCase):
    def test_public_tools_reject_transaction_only_outcomes(self):
        for level in ("core", "extended"):
            for path in sorted((ROOT / "schemas" / level).glob("*.output.json")):
                schema = load_json(path)
                Draft202012Validator.check_schema(schema)
                validator = Draft202012Validator(schema, format_checker=FormatChecker())
                for status in ("unauthorized", "forbidden", "conflict"):
                    with self.subTest(tool=path.stem, status=status):
                        self.assertFalse(validator.is_valid({"status": status, "error": {"message": "Unavailable"}}))

    def test_public_error_outcomes_still_require_an_error_message(self):
        for level in ("core", "extended"):
            for path in sorted((ROOT / "schemas" / level).glob("*.output.json")):
                schema = load_json(path)
                validator = Draft202012Validator(schema, format_checker=FormatChecker())
                for status in schema["properties"]["status"]["enum"]:
                    if status in ("ok", "not_applicable"):
                        continue
                    with self.subTest(tool=path.stem, status=status):
                        validator.validate({"status": status, "error": {"message": "Try again"}})
                        self.assertFalse(validator.is_valid({"status": status}))
                        self.assertFalse(validator.is_valid({"status": status, "error": {}}))

    def test_not_applicable_is_limited_to_services_and_contact(self):
        for level in ("core", "extended"):
            for path in sorted((ROOT / "schemas" / level).glob("*.output.json")):
                validator = Draft202012Validator(load_json(path), format_checker=FormatChecker())
                expected = path.name in ("get_services.output.json", "get_contact.output.json")
                with self.subTest(tool=path.stem):
                    self.assertEqual(validator.is_valid({"status": "not_applicable", "reason": "Personal blog"}), expected)
                    self.assertFalse(validator.is_valid({"status": "not_applicable"}))

    def test_transactional_tools_retain_authentication_outcomes(self):
        for path in sorted((ROOT / "schemas" / "transactional").glob("*.output.json")):
            validator = Draft202012Validator(load_json(path), format_checker=FormatChecker())
            for status in ("unauthorized", "forbidden"):
                with self.subTest(tool=path.stem, status=status):
                    validator.validate({"status": status, "error": {"message": "Authentication required"}})


if __name__ == "__main__":
    unittest.main()
