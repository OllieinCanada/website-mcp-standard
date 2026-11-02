Enforce prepared expiry and submitted transaction audit fields

Schema-only change; no runtime security or deployed-vulnerability claim.

Schema guarantees cover structure and presence. They do not prove runtime expiry enforcement, truthful/complete history, approval, or idempotent effects; this is not a deployed-vulnerability claim.

Validation: the complete integration passes 76 tests and 27 examples on fresh Python 3.10.22 and 3.14.8, plus an earlier Python 3.12 run. Focused regressions are included with each contribution. GitHub CI has not yet run.
