# Contributing to MCP-WP (MCP Website Profile)

Thank you for helping make websites usable by agents in a consistent way.

## Ways to contribute

- **Implementation reports.** Tell us what was easy or hard when you implemented MCP-WP on a real site. Include the site type: business, blog, government, nonprofit, shop, and so on.
- **Client feedback.** If you build an agent or MCP client that consumes MCP-WP, tell us what was missing or ambiguous.
- **Issues.** Report an ambiguity, an error or a gap in the specification. Please cite the requirement ID (e.g. `MCPWP-CORE-041`).
- **Pull requests.** Fixes to the specification, schemas and examples are welcome.

## Ground rules for changes

1. **Keep Core small.** New mandatory requirements need a strong case and evidence that small sites can meet them.
2. **Stay MCP-native.** Do not re-specify anything MCP already defines.
3. **Put new capabilities in the right level.** Read-only information belongs in an Extended module. Anything with real-world consequences belongs in the Transactional level and must keep its approval, idempotency and audit controls.
4. **Keep the spec, schemas and examples in sync.** A change to a result field must update `SPECIFICATION.md`, the matching file in `schemas/`, and any affected examples. Then run:

   ```bash
   python3 -m pip install -r requirements-checker.txt
   python3 tools/validate_examples.py
   python3 -m unittest discover -s tests -v
   ```

   Keep intentionally invalid regression payloads in tests, with an explicit
   expected result; JSON files under `examples/` must all validate. The validator
   rejects duplicate keys and incomplete discovery rather than skipping files.

5. **Requirement IDs are permanent.** IDs take the form `MCPWP-<AREA>-<NNN>`. Do not renumber existing IDs. Retire an obsolete ID by marking it *removed* rather than reusing it.
6. **Record changes** in `CHANGELOG.md`.

## Licensing of contributions

By submitting a contribution you agree that it is licensed under the same terms as the files it changes: changes to the specification and other Markdown documents under [CC BY 4.0](LICENSE-SPEC), and changes to `schemas/`, `examples/` and `tools/` under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE). You must have the right to submit the work.

## Decision process (v0.x)

Until there are several independent implementations, the maintainers (initially AI4 Enterprise) edit the draft and decide by rough consensus in issues and pull requests. Substantial proposals, such as new modules, should start as an issue that describes the use case. A more formal governance model will be proposed before 1.0.

### Proposing a sector module

Sector modules start life with an `x-` prefix (for example `x-retail`). Publish your module's documentation and schemas, implement it on at least one real site, then open an issue proposing it for standardisation. Once it has been accepted and has two or more independent implementations, it can drop the prefix.
