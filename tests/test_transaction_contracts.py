"""Schema-level guarantees for MCPWP-TXN-031 and MCPWP-TXN-040."""

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("prepare_transaction", "submit_transaction", "get_transaction_status", "cancel_transaction")
SUBMITTED = ("pending", "confirmed", "completed", "rejected", "cancellation_pending", "cancelled", "failed")
STATES = ("prepared",) + SUBMITTED + ("expired",)
AT = "2026-11-01T21:00:00Z"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def transaction(state):
    result = {"transaction_id": "txn_example_123", "type": "test-booking", "status": state, "summary": "Test booking"}
    if state == "prepared":
        result["expires_at"] = "2026-11-01T21:15:00Z"
    if state in SUBMITTED:
        result["created_at"] = AT
    return result


def history_entry(state):
    return {"status": state, "at": AT, "actor": "system"}


class TransactionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {}
        cls.outputs = {}
        cls.transactions = {}
        for tool in TOOLS:
            schema = load_json(ROOT / "schemas" / "transactional" / f"{tool}.output.json")
            Draft202012Validator.check_schema(schema)
            cls.schemas[tool] = schema
            cls.outputs[tool] = Draft202012Validator(schema, format_checker=FormatChecker())
            cls.transactions[tool] = Draft202012Validator(
                {"$ref": "#/$defs/transaction", "$defs": schema["$defs"]}, format_checker=FormatChecker()
            )

    def test_transaction_definitions_stay_synchronized(self):
        expected = self.schemas["prepare_transaction"]["$defs"]["transaction"]
        for tool, schema in self.schemas.items():
            with self.subTest(tool=tool):
                self.assertEqual(schema["$defs"]["transaction"], expected)

    def test_prepared_transactions_require_expiry_everywhere(self):
        for tool, validator in self.transactions.items():
            draft = transaction("prepared")
            with self.subTest(tool=tool):
                validator.validate(draft)
                del draft["expires_at"]
                self.assertFalse(validator.is_valid(draft))

    def test_preparation_success_has_only_prepared_state(self):
        validator = self.outputs["prepare_transaction"]
        for state in STATES:
            with self.subTest(state=state):
                self.assertEqual(validator.is_valid({"status": "ok", "transaction": transaction(state)}), state == "prepared")

    def test_submitted_transactions_require_creation_time_everywhere(self):
        for tool, validator in self.transactions.items():
            for state in SUBMITTED:
                result = transaction(state)
                with self.subTest(tool=tool, state=state):
                    validator.validate(result)
                    del result["created_at"]
                    self.assertFalse(validator.is_valid(result))

    def test_status_response_always_requires_history(self):
        validator = self.outputs["get_transaction_status"]
        for state in STATES:
            result = transaction(state)
            with self.subTest(state=state):
                self.assertFalse(validator.is_valid({"status": "ok", "transaction": result}))
                result["history"] = [history_entry(state)]
                validator.validate({"status": "ok", "transaction": result})

    def test_submitted_status_history_cannot_be_empty(self):
        validator = self.outputs["get_transaction_status"]
        for state in STATES:
            result = transaction(state)
            result["history"] = []
            with self.subTest(state=state):
                self.assertEqual(validator.is_valid({"status": "ok", "transaction": result}), state not in SUBMITTED)

    def test_every_history_entry_requires_state_timestamp_and_actor(self):
        for tool, validator in self.transactions.items():
            for field in ("status", "at", "actor"):
                result = transaction("confirmed")
                result["history"] = [history_entry("prepared"), history_entry("confirmed")]
                del result["history"][1][field]
                with self.subTest(tool=tool, field=field):
                    self.assertFalse(validator.is_valid(result))

    def test_expired_drafts_do_not_require_submitted_audit_fields(self):
        for tool, validator in self.transactions.items():
            result = transaction("expired")
            with self.subTest(tool=tool):
                validator.validate(result)
                result["history"] = [history_entry("prepared"), history_entry("expired")]
                validator.validate(result)
                self.outputs["get_transaction_status"].validate({"status": "ok", "transaction": result})

    def test_expired_submitted_history_requires_creation_time(self):
        for tool, validator in self.transactions.items():
            for state in SUBMITTED:
                result = transaction("expired")
                result["history"] = [history_entry("prepared"), history_entry(state), history_entry("expired")]
                with self.subTest(tool=tool, prior_state=state):
                    self.assertFalse(validator.is_valid(result))
                    result["created_at"] = AT
                    validator.validate(result)
                    self.outputs["get_transaction_status"].validate({"status": "ok", "transaction": result})

    def test_action_responses_may_omit_history(self):
        for tool, state in (("prepare_transaction", "prepared"), ("submit_transaction", "confirmed"), ("cancel_transaction", "cancelled")):
            with self.subTest(tool=tool):
                self.outputs[tool].validate({"status": "ok", "transaction": transaction(state)})

    def test_error_responses_need_no_transaction(self):
        for tool, validator in self.outputs.items():
            for status in self.schemas[tool]["properties"]["status"]["enum"]:
                if status == "ok":
                    continue
                with self.subTest(tool=tool, status=status):
                    validator.validate({"status": status, "error": {"message": "Try again"}})

    def test_transaction_timestamps_require_rfc3339_with_offset(self):
        for tool, validator in self.transactions.items():
            for field in ("expires_at", "created_at", "at"):
                result = transaction("prepared" if field == "expires_at" else "confirmed")
                if field == "at":
                    result["history"] = [history_entry("confirmed")]
                    result["history"][0]["at"] = "2026-11-01T21:00:00"
                else:
                    result[field] = "2026-11-01T21:00:00"
                with self.subTest(tool=tool, field=field):
                    self.assertFalse(validator.is_valid(result))

    def test_published_transaction_examples_validate(self):
        for tool, validator in self.outputs.items():
            with self.subTest(tool=tool):
                validator.validate(load_json(ROOT / "examples" / "consultancy" / f"{tool}.json"))

    def test_published_lifecycle_keeps_creation_time_stable(self):
        creation_times = {
            load_json(ROOT / "examples" / "consultancy" / f"{tool}.json")["transaction"]["created_at"]
            for tool in TOOLS
        }
        self.assertEqual(creation_times, {AT})


if __name__ == "__main__":
    unittest.main()
