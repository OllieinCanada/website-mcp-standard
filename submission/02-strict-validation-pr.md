Reject ambiguous JSON and incomplete example validation; add CI

Depends on event-contract correction so strict validation accepts the published fixture.

Depends on the event fixture correction landing first. Intentionally invalid regression payloads stay under tests; every published example must validate.

Validation: the complete integration passes 76 tests and 27 examples on fresh Python 3.10.22 and 3.14.8, plus an earlier Python 3.12 run. Focused regressions are included with each contribution. GitHub CI has not yet run.
