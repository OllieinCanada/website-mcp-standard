# Changelog

All notable changes to the MCP Website Profile (MCP-WP) are recorded here.

## [Unreleased]

- §11.1: added a non-normative note explaining why SEC-001 matters. Every public `/mcp` endpoint feeds text straight into the visiting agent, so all server-supplied strings, including tool descriptions and `instructions`, are data, not instructions. Thanks to Sebastian Mondragon for the framing.

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
