Top-level `status` currently uses event lifecycle values, rejecting standard `ok`/error outcomes and leaving success-field requirements ineffective. The published example also repeats `status`, silently replacing `ok` during ordinary JSON parsing.

Reserve outer `status` for tool outcomes and use optional `event_status` consistently in detail and list items. Restore successful detail requirements, correct both examples, and update the specification/changelog. This is a draft field-name change proposed for maintainer agreement (MCPWP-EVT-001/003; MCPWP-RES-001/010/011).

Validation: eight focused event regressions pass as part of the integrated suite on Python 3.10, 3.12, and 3.14. The complete integration passes 76 tests and all 27 examples. The event-only branch contains the focused tests; later contributions add the validator and CI.
