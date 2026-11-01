# Contributing to ARWP

Thank you for helping make websites usable by agents in a consistent way.

## Ways to contribute

- **Implementation reports.** Tell us what was easy or hard when you implemented ARWP on a real site. Include the site type: business, blog, government, nonprofit, shop, and so on.
- **Client feedback.** If you build an agent or MCP client that consumes ARWP, tell us what was missing or ambiguous.
- **Issues.** Report an ambiguity, an error or a gap in the specification. Please cite the requirement ID (e.g. `ARWP-CORE-041`).
- **Pull requests.** Fixes to the specification, schemas and examples are welcome.

## Ground rules for changes

1. **Keep Core small.** New mandatory requirements need a strong case and evidence that small sites can meet them.
2. **Stay MCP-native.** Do not re-specify anything MCP already defines.
3. **Keep the spec, schemas and examples in sync.** A change to a result field must update `SPECIFICATION.md`, the matching file in `schemas/`, and any affected examples. Then run:

   ```bash
   python3 tools/validate_examples.py
   ```

4. **Requirement IDs are permanent.** Do not renumber existing IDs. Retire an obsolete ID by marking it *removed* rather than reusing it.
5. **Record changes** in `CHANGELOG.md`.

## Decision process (v0.x)

Until there are several independent implementations, the maintainers (initially AI4 Enterprise) edit the draft and decide by rough consensus in issues and pull requests. Substantial proposals, such as new profiles, should start as an issue that describes the use case. A more formal governance model will be proposed before 1.0.
