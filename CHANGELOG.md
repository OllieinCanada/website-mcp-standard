# Changelog

All notable changes to the MCP Website Profile (MCP-WP) are recorded here.

## Unreleased

- Require prepared-state expiry, preparation responses in `prepared`, submitted-state creation timestamps, status-response history, and actors on history entries. Keep expired drafts distinct from expired submitted transactions and synchronize the four transaction-result definitions and examples (`MCPWP-TXN-031`, `MCPWP-TXN-040`).
- Enforce declaration level/module equivalences, including `x-*` Extended modules, and reject Transactional-only outcomes in all Core and Extended output schemas (`MCPWP-DECL-001`, `MCPWP-DECL-002`, `MCPWP-DISC-005`, `MCPWP-RES-010`).
- Reject ambiguous or malformed JSON, invalid schemas, duplicate schema mappings, unmapped examples, and empty validation discovery; report coverage counts and exercise command exit codes. Add pinned format-checking dependencies and Python 3.10/3.14 CI.
- Separate event lifecycle into optional `event_status` in detail and list results, reserving outer `status` for call outcomes. Restore required successful detail fields and correct the duplicate-key example. This changes the draft event field name without an alias (`MCPWP-EVT-001`, `MCPWP-EVT-003`, `MCPWP-RES-001`, `MCPWP-RES-010`, `MCPWP-RES-011`).

## [0.1] — 2026-11-01 — Proposed Draft

First public draft.

- Named **MCP Website Profile (MCP-WP)**. Earlier working drafts called it the Agent-Ready Web Profile (ARWP).
- `/mcp` discovery convention over MCP Streamable HTTP (MCP 2025-06-18 or later).
- Three conformance levels made of modules:
  - **Core** (mandatory): `get_site_info`, `get_services`, `get_contact`, `search_site`, `get_page`.
  - **Extended** (optional): modules `insights` (`search_insights`, `get_insight`, `latest_insights`, `list_topics`), `service_details` (`get_service`), `people` (`get_people`, `get_person`), `events` (`get_events`, `get_event`), and sector modules (`x-*`).
  - **Transactional** (optional, provisional): module `transactions` (`list_transaction_types`, `check_availability`, `prepare_transaction`, `submit_transaction`, `get_transaction_status`, `cancel_transaction`), with MCP authorisation, explicit user approval, idempotency, audit history, no payment data in tools, and `test` types for safe conformance testing.
- Common result envelope: `status` in `structuredContent` aligned with MCP `isError`, including `not_applicable` and `conflict`.
- `mcpwp` declaration in `get_site_info` (version, levels, modules, extensions), versioning rules, and extension rules (`ext`, reserved tool names).
- Security, privacy and trust requirements.
- JSON Schemas for all 20 tools' inputs and outputs, examples, and a validation script.
- AI4Enterprise mapping and alignment plan as the reference implementation.
- Licensing: specification text under CC BY 4.0; schemas, examples and tools under Apache 2.0.
