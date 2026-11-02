Reject ambiguous JSON and incomplete example validation; add CI

Depends on event-contract correction so strict validation accepts the published fixture.

Depends on the event fixture correction landing first. Intentionally invalid regression payloads stay under tests; every published example must validate.

Validation: the complete integration passes 76 tests and 27 examples on fresh Python 3.10.22 and 3.14.8, plus an earlier Python 3.12 run. Focused regressions are included with each contribution. GitHub Actions passes on Python 3.10 and 3.14: https://github.com/OllieinCanada/website-mcp-standard/actions/runs/41376843245 .

Validation commands:

```bash
python3 -m pip install -r requirements-dev.txt
python3 tools/validate_examples.py
python3 -m unittest discover -s tests -v
```
