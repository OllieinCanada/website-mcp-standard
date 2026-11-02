#!/usr/bin/env python3
"""Validate the MCP-WP JSON Schemas and every example response against them.

Usage:  pip install jsonschema && python3 tools/validate_examples.py

Example files are named <tool>.json or <tool>.<variant>.json and contain the
`structuredContent` of an MCP tool result.
Duplicate JSON object member names are rejected in both schemas and examples.
"""
import json
import pathlib
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


def _unique_members(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member {key!r}")
        result[key] = value
    return result


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=_unique_members)


def main():
    failures = 0
    outputs = {}
    for path in sorted(SCHEMAS.rglob("*.json")):
        schema = load(path)
        Draft202012Validator.check_schema(schema)
        if path.name.endswith(".output.json"):
            outputs[path.name[: -len(".output.json")]] = schema

    for path in sorted(EXAMPLES.rglob("*.json")):
        tool = path.name.split(".")[0]
        schema = outputs.get(tool)
        rel = path.relative_to(ROOT)
        if schema is None:
            print(f"SKIP {rel}: no output schema for '{tool}'")
            continue
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(load(path)), key=lambda e: list(e.path))
        if errors:
            failures += 1
            print(f"FAIL {rel}")
            for err in errors:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                print(f"     {loc}: {err.message}")
        else:
            print(f"PASS {rel}")

    print(f"\n{len(outputs)} output schemas; {failures} failing example(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
