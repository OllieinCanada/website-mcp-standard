Enforce prepared expiry and submitted transaction audit fields

Schema-only change; no runtime security or deployed-vulnerability claim.

Schema guarantees cover structure and presence. They do not prove runtime expiry enforcement, truthful/complete history, approval, or idempotent effects; this is not a deployed-vulnerability claim.

Validation: the complete integration passes 76 tests and 27 examples on fresh Python 3.10.22 and 3.14.8, plus an earlier Python 3.12 run. Focused regressions are included with each contribution. GitHub Actions passes on Python 3.10 and 3.14: https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376863237 .

Validation commands:

```bash
python3 -m pip install -r requirements-dev.txt
python3 tools/validate_examples.py
python3 -m unittest discover -s tests -v
```
