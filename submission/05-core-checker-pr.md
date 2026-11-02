Add a bounded read-only Core conformance checker

Post the use-case issue and seek maintainer feedback before upstream checker submission; no acceptance is established.

This is the Core-only milestone from the checker proposal. Please link the proposal issue here before submission. Recommendations remain separate from mandatory failures; Extended and Transactional behavior is NOT TESTED.

Validation: the complete integration passes 76 tests and 27 examples on fresh Python 3.10.22 and 3.14.8, plus an earlier Python 3.12 run. Focused regressions are included with each contribution. GitHub CI has not yet run.
