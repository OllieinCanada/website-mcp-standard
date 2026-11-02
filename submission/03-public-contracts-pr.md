Enforce capability declarations and public tool outcomes

Submit as its own contribution after the baseline fixes; maintain permanent IDs.

Enforces existing obligations in MCPWP-DECL-002, MCPWP-DISC-005, and the section 10 status table. This adds no mandatory Core capability.

Validation: the complete integration passes 76 tests and 27 examples on fresh Python 3.10.22 and 3.14.8, plus an earlier Python 3.12 run. Focused regressions are included with each contribution. GitHub Actions passes on Python 3.10 and 3.14: https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376860909 .

Validation commands:

```bash
python3 -m pip install -r requirements-dev.txt
python3 tools/validate_examples.py
python3 -m unittest discover -s tests -v
```
