# Proposal: a bounded, read-only Core conformance checker

This is a draft for maintainer discussion, not a posted issue or an acceptance
decision.

## Use case

An implementer can validate the published response examples today, but cannot
check whether their own `/mcp` endpoint exposes the five Core tools, implements
MCP initialization, returns valid structured results, or resolves section and
search references. Section 12 already describes a conformance checker; this
contribution supplies its first, Core-only milestone.

## Proposed contribution

Add a Python command-line tool that takes a website host, derives its HTTPS
`/mcp` endpoint, and emits either readable output or a versioned JSON report.
Use the official MCP SDK for Streamable HTTP, negotiation, session headers,
JSON/SSE responses, and lifecycle notifications. Use the repository's strict
JSON loader and normative schemas for response validation.

Exercise the ten Core groups in §12, linking evidence to permanent requirement
IDs: `MCPWP-MCP-001`–`003`, `MCPWP-DISC-001`–`005`, `MCPWP-CORE-001`–`006`,
`MCPWP-CORE-010`, `MCPWP-CORE-040`–`042`, `MCPWP-CORE-050`–`052`,
`MCPWP-DECL-001`–`003`, `MCPWP-RES-001`/`010`/`011`, and `MCPWP-EXTN-001`.
Distinguish mandatory failures from recommendations such as alternate-host
support (`MCPWP-DISC-003`) and advertised output schemas (`MCPWP-CORE-005`).

## Boundaries and reporting

- Call only the five Core tools, without credentials. Never call transaction
  tools or accept a remote `test: true` declaration as authorization to do so.
- Bound request counts, wall time, pagination, redirects, and content samples.
  Report incomplete coverage and blocked dependencies explicitly.
- Report PASS, FAIL, SKIP, and NOT TESTED with concise evidence. A passing
  sampled run is not certification of every page, every possible input, human
  site consistency, privacy, or absence of side effects.
- Mark Extended and Transactional behavior NOT TESTED. Declared standard tool
  presence can be observed through `tools/list`, but presence does not prove
  behavior or custom-module completeness.
- Test locally against controlled JSON/SSE fixture servers in CI. Live runs
  require an operator to invoke the CLI for the chosen host.

## Acceptance

The repository's corrected schemas/examples and strict-validation regressions
remain green. Local fixtures exercise lifecycle/session headers, pagination,
redirects, result contracts, declarations, reference resolution, failures, and
budget exhaustion. Reports retain useful partial evidence when an assessment
cannot finish. No production endpoint is needed to validate this contribution.

Broader module checking, transactional integration tests, packaging as a public
service, and a report registry are later milestones outside this proposal.
