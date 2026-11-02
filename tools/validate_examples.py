#!/usr/bin/env python3
"""Validate the MCP-WP JSON Schemas and every example response against them.

Usage:  python3 tools/validate_examples.py

Example files are named <tool>.json or <tool>.<variant>.json and contain the
`structuredContent` of an MCP tool result.
"""
import argparse
import json
import pathlib
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry
from referencing.exceptions import Unresolvable

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


def _invalid_constant(value):
    raise ValueError(f"invalid JSON constant {value!r}")


def load(path):
    """Load JSON without silently changing duplicate-key or non-JSON input."""
    with open(path, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=_unique_members,
                         parse_constant=_invalid_constant)


def make_validator(schema):
    """Validate formats and resolve internal references without network access."""
    checker = FormatChecker()
    missing = {"date", "date-time", "uri"}.difference(checker.checkers)
    if missing:
        raise ValueError("missing JSON Schema format checkers: "
                         f"{', '.join(sorted(missing))}; "
                         "install requirements-dev.txt")
    return Draft202012Validator(schema, format_checker=checker,
                                 registry=Registry())


def _read_schemas(schema_root):
    paths = sorted(pathlib.Path(schema_root).rglob("*.json"))
    outputs = {}
    problems = []
    if not paths:
        problems.append(f"{schema_root}: no JSON schemas discovered")
    for path in paths:
        try:
            schema = load(path)
            Draft202012Validator.check_schema(schema)
        except (OSError, ValueError, SchemaError) as exc:
            problems.append(f"{path}: {exc}")
            continue
        if path.name.endswith(".output.json"):
            tool = path.name[: -len(".output.json")]
            if tool in outputs:
                problems.append(f"{path}: duplicate output schema for {tool!r}")
            else:
                outputs[tool] = schema
    if paths and not outputs:
        problems.append(f"{schema_root}: no usable output schemas discovered")
    return len(paths), outputs, problems


def load_schemas(schema_root=SCHEMAS):
    """Return output schemas keyed by tool, rejecting incomplete discovery."""
    _, outputs, problems = _read_schemas(schema_root)
    if problems:
        raise ValueError("\n".join(problems))
    return outputs


def validate(schema_root=SCHEMAS, example_root=EXAMPLES):
    schema_count, outputs, problems = _read_schemas(schema_root)
    paths = sorted(pathlib.Path(example_root).rglob("*.json"))
    if not paths:
        problems.append(f"{example_root}: no JSON examples discovered")
    for problem in problems:
        print(f"FAIL {problem}")

    failing = validated = unmapped = 0
    for path in paths:
        tool = path.name.split(".")[0]
        schema = outputs.get(tool)
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if schema is None:
            print(f"FAIL {rel}: no output schema for '{tool}'")
            unmapped += 1
            failing += 1
            continue
        try:
            payload = load(path)
            errors = sorted(make_validator(schema).iter_errors(payload),
                            key=lambda e: (e.json_path, e.message))
            validated += 1
        except (OSError, ValueError, Unresolvable) as exc:
            failing += 1
            print(f"FAIL {rel}: {exc}")
            continue
        if errors:
            failing += 1
            print(f"FAIL {rel}")
            for err in errors:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                print(f"     {loc}: {err.message}")
        else:
            print(f"PASS {rel}")

    print(f"\n{schema_count} schemas discovered; {len(outputs)} output schemas; "
          f"{len(paths)} examples discovered; {validated} validated; "
          f"{unmapped} unmapped; {failing} failing example(s); "
          f"{len(problems)} schema/discovery error(s).")
    return 1 if failing or problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schemas", type=pathlib.Path, default=SCHEMAS)
    parser.add_argument("--examples", type=pathlib.Path, default=EXAMPLES)
    args = parser.parse_args(argv)
    return validate(args.schemas, args.examples)


if __name__ == "__main__":
    sys.exit(main())
