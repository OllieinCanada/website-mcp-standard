# Agent-Ready Web Profile (ARWP)

**A simple, MCP-based standard that lets AI agents use any participating website the same way.**

> **Status:** v0.1 — Proposed Draft, open for comment. Not yet stable.

Websites are built for people. Agents can read them, but every site has different navigation, layout and terminology. ARWP gives agents a predictable front door:

```text
https://<your-site>/mcp
```

Behind that door, every ARWP site provides the same five read-only [MCP](https://modelcontextprotocol.io/) tools:

| Tool | Answers |
|---|---|
| `get_site_info` | What is this site, who runs it, and what are its main sections? |
| `get_services` | What does it offer? (or an explicit `not_applicable`) |
| `get_contact` | How can I get in touch or engage? |
| `search_site` | Where on the site is information about *X*? |
| `get_page` | Give me this page as clean Markdown. |

Sites that publish articles or research can add the optional **Insights** profile (`search_insights`, `get_insight`, `latest_insights`, `list_topics`). Any site can add its own extension tools as well.

ARWP is a *profile* of MCP. It reuses MCP's transport, tool discovery and structured output, and adds only conventions: a fixed path, standard tool names and standard result shapes. No AI model is needed on the website.

## Read the standard

- **[SPECIFICATION.md](SPECIFICATION.md)**: the normative v0.1 specification
- **[schemas/](schemas/)**: JSON Schema (2020-12) for every tool's input and output
- **[examples/](examples/)**: example results for a consultancy site and a personal blog
- **[CHANGELOG.md](CHANGELOG.md)** · **[CONTRIBUTING.md](CONTRIBUTING.md)**

## Implementing ARWP on your site: a checklist

1. Serve an MCP server (Streamable HTTP, MCP revision 2025-06-18 or later) at `https://<canonical-host>/mcp`. Do not require authentication for the Core tools.
2. Implement the five Core tools with the exact names above. Mark them `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true` and `openWorldHint: false`.
3. Return `structuredContent` that validates against [`schemas/core/`](schemas/core/), and include `status` in every result. Also return the same JSON as a `text` content block.
4. In `get_site_info`, declare `"arwp": { "version": "0.1", "profiles": ["core"] }`. Add `"insights"` if you implement that profile.
5. Make sure every `search_site` result and every section URL can be fetched with `get_page`. Make sure `get_page` never fetches off-site URLs.
6. Use `not_applicable` (with a `reason`) rather than inventing content, for example `get_services` on a personal blog.
7. Optionally: add CORS headers, redirect the apex/`www` host's `/mcp` with 307/308, mention `/mcp` in your `llms.txt`, and serve a human-readable page for browser `GET /mcp`.

## Reference implementation

[AI4Enterprise](https://www.ai4enterprise.ca/) runs an MCP server at `https://www.ai4enterprise.ca/mcp`. It already provides `get_services`, `get_contact` and the four Insights tools, and it is being aligned with v0.1. See [SPECIFICATION.md §12](SPECIFICATION.md#12-reference-implementation-ai4enterprise-informative).

## Validating the schemas and examples

```bash
pip install jsonschema
```

```bash
python3 tools/validate_examples.py
```

## Repository layout

```text
SPECIFICATION.md          Normative specification (v0.1)
schemas/core/             Core tool input/output JSON Schemas
schemas/insights/         Insights tool input/output JSON Schemas
examples/consultancy/     Example results: business site with Core + Insights
examples/personal-blog/   Example results: personal site (shows not_applicable)
tools/validate_examples.py  Validates every example against its schema
```

## Roadmap

- **v0.1** (this draft): Core and Insights profiles, schemas, examples, and AI4Enterprise alignment.
- **Next:** a reference conformance checker, more implementations, and feedback from different site types.
- **v0.2:** a Transactions profile (bookings, orders, applications) with consent and safety controls, alignment with MCP discovery work (Server Cards), and multilingual sites.

## Contributing

Feedback is very welcome, especially from people implementing ARWP on real sites or building agents that consume it. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

To be decided by the maintainers before the first tagged release.
