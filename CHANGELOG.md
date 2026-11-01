# Changelog

All notable changes to the Agent-Ready Web Profile are recorded here.

## [0.1] — 2026-11-01 — Proposed Draft

First public draft.

- `/mcp` discovery convention over MCP Streamable HTTP (MCP 2025-06-18 or later).
- Core profile (mandatory): `get_site_info`, `get_services`, `get_contact`, `search_site`, `get_page`.
- Insights profile (optional): `search_insights`, `get_insight`, `latest_insights`, `list_topics`.
- Common result envelope: `status` in `structuredContent` aligned with MCP `isError`. Includes `not_applicable`.
- ARWP declaration in `get_site_info.arwp`, versioning rules, and extension rules (`ext`, `x-` profiles).
- Reserved tool names for a future Transactions profile.
- Security, privacy and trust requirements.
- JSON Schemas for all tool inputs and outputs, examples, and a validation script.
- AI4Enterprise mapping and alignment plan as the reference implementation.
- Licensing: specification text under CC BY 4.0; schemas, examples and tools under Apache 2.0.
