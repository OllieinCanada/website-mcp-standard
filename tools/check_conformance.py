#!/usr/bin/env python3
"""Run bounded, unauthenticated MCP-WP 0.1 Core checks.

This is a sample-based diagnostic, not a certification. Only the five Core
tools are called. Run ``python3 tools/check_conformance.py --help`` for usage.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import importlib.metadata
import ipaddress
import json
from pathlib import Path
import sys
import uuid
from urllib.parse import urljoin, urlsplit, urlunsplit

import anyio
import httpx2
from jsonschema import Draft202012Validator
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import mcp_types as types
from pydantic import ValidationError

try:
    from tools import validate_examples
except ModuleNotFoundError:
    import validate_examples


ROOT = Path(__file__).resolve().parent.parent
CHECKER_VERSION = "0.1.0"
CORE = ("get_site_info", "get_services", "get_contact", "search_site", "get_page")
MODULES = {
    "core": CORE,
    "insights": ("search_insights", "get_insight", "latest_insights", "list_topics"),
    "service_details": ("get_service",),
    "people": ("get_people", "get_person"),
    "events": ("get_events", "get_event"),
    "transactions": ("list_transaction_types", "prepare_transaction",
                     "submit_transaction", "get_transaction_status"),
}
RESERVED = set().union(*MODULES.values(), {"check_availability", "cancel_transaction"})
ERROR_STATUSES = {"invalid_request", "not_found", "unauthorized", "forbidden",
                  "conflict", "rate_limited", "unavailable", "internal_error"}
TRANSIENT = {"rate_limited", "unavailable", "internal_error"}
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False,
               "idempotentHint": True, "openWorldHint": False}


@dataclass
class Config:
    endpoint: str
    query: str | None = None
    timeout: float = 10
    run_timeout: float = 120
    max_requests: int = 100
    max_pages: int = 10
    section_limit: int = 10
    search_limit: int = 10
    schema_root: Path = ROOT / "schemas"
    discovery_probes: bool = True


class Incomplete(Exception):
    """A bound or an unavailable prerequisite prevented an observation."""


class RedirectBlocked(Incomplete):
    pass


class EnvironmentTransport(httpx2.AsyncBaseTransport):
    """Forward with the normal client so inherited proxy and CA settings apply."""

    def __init__(self):
        self.client = httpx2.AsyncClient(follow_redirects=False)

    async def handle_async_request(self, request):
        return await self.client.send(request, stream=True, follow_redirects=False)

    async def aclose(self):
        await self.client.aclose()


def normalize_endpoint(host: str) -> str:
    value = host if "://" in host else "https://" + host
    parts = urlsplit(value)
    if (parts.scheme != "https" or not parts.hostname or parts.username
            or parts.password or parts.path not in ("", "/") or parts.query or parts.fragment):
        raise ValueError("HOST must be a hostname or HTTPS origin without a path or credentials")
    # Accessing port also rejects malformed port numbers before making requests.
    _ = parts.port
    return urlunsplit(("https", parts.netloc, "/mcp", "", ""))


def counterpart(host: str) -> str | None:
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    if "." not in host:
        return None
    return host[4:] if host.startswith("www.") else "www." + host


class RedirectTransport(httpx2.AsyncBaseTransport):
    """Apply a narrow site-host redirect policy around the SDK's HTTP transport."""

    def __init__(self, endpoint, inner=None):
        self.original = endpoint
        self.resolved = endpoint
        host = urlsplit(endpoint).hostname
        self.hosts = {host, counterpart(host)} - {None}
        self.inner = inner or EnvironmentTransport()
        self.redirects = []
        self.responses = []

    async def handle_async_request(self, request):
        body = await request.aread()
        target = self.resolved if str(request.url) == self.original else str(request.url)
        visited = set()
        for hop in range(6):
            if target in visited:
                raise RedirectBlocked("redirect loop")
            visited.add(target)
            headers = dict(request.headers)
            headers.pop("host", None)
            forwarded = httpx2.Request(request.method, target, headers=headers,
                                       content=body, extensions=request.extensions)
            response = await self.inner.handle_async_request(forwarded)
            response.request = forwarded
            self.responses.append({"url": target, "status": response.status_code})
            if response.status_code not in (301, 302, 303, 307, 308):
                self.resolved = target
                return response
            location = response.headers.get("location")
            await response.aclose()
            following = urljoin(target, location or "")
            parsed = urlsplit(following)
            if (response.status_code not in (307, 308) or not location
                    or parsed.scheme != "https" or parsed.hostname not in self.hosts
                    or parsed.username or parsed.password or hop == 5):
                raise RedirectBlocked("redirect not followed: only up to five HTTPS 307/308 "
                                      "hops on the submitted host or its www counterpart are allowed")
            self.redirects.append({"from": target, "to": following,
                                   "status": response.status_code})
            target = following
        raise RedirectBlocked("redirect limit reached")

    async def aclose(self):
        await self.inner.aclose()


def validator(schema):
    """No remote schema retrieval, including server-provided $refs."""
    Draft202012Validator.check_schema(schema)
    return validate_examples.make_validator(schema)


def leaf_exceptions(error):
    children = getattr(error, "exceptions", None)
    if children:
        return [leaf for child in children for leaf in leaf_exceptions(child)]
    return [error]


class Checker:
    def __init__(self, config, transport=None):
        self.config = config
        self.rows = []
        self.warnings = []
        self.tools = {}
        self.outputs = {}
        self.session = None
        self.transport = transport
        self.request_count = 0
        self.http_probes = 0
        self.protocol = None
        self.sections_tested = 0
        self.search_tested = 0
        self.search_observed = 0
        self.schema_version = "0.1"

    def add(self, name, group, requirements, outcome, evidence, required=True):
        self.rows.append({"id": name, "group": group,
                          "requirements": ["MCPWP-" + r for r in requirements],
                          "outcome": outcome, "evidence": evidence, "required": required})

    def expect(self, condition, name, group, requirements, evidence):
        self.add(name, group, requirements, "PASS" if condition else "FAIL", evidence)

    def reserve(self):
        if self.request_count >= self.config.max_requests:
            raise Incomplete(f"MCP request budget ({self.config.max_requests}) exhausted")
        self.request_count += 1

    def unavailable(self, name, group, requirements, error):
        leaves = leaf_exceptions(error)
        auth = any(isinstance(e, httpx2.HTTPStatusError)
                   and e.response.status_code in (401, 403) for e in leaves)
        if self.transport and self.transport.responses:
            auth = auth or self.transport.responses[-1]["status"] in (401, 403)
        malformed = any(isinstance(e, (ValidationError, json.JSONDecodeError))
                        or "Unsupported protocol version from the server" in str(e)
                        or "Failed to parse" in str(e) for e in leaves)
        messages = "; ".join(dict.fromkeys(str(e)[:350] for e in leaves))
        # Transport failures do not establish a normative server violation.
        self.add(name, group, requirements, "FAIL" if auth or malformed else "NOT TESTED", messages)

    async def call(self, name, arguments, label, group):
        if name not in self.tools:
            self.add(label, group, ["CORE-005"], "NOT TESTED", f"{name} is absent")
            return None
        self.reserve()
        try:
            result = await self.session.send_request(
                types.CallToolRequest(params=types.CallToolRequestParams(
                    name=name, arguments=arguments)), types.CallToolResult,
                request_read_timeout_seconds=self.config.timeout)
        except Exception as error:
            self.unavailable(label, group, ["CORE-005", "DISC-005"], error)
            return None
        payload = result.structured_content
        valid = isinstance(payload, dict)
        errors = []
        if valid:
            try:
                errors = [e.message for e in self.outputs[name].iter_errors(payload)]
            except Exception as error:
                errors = [f"schema validation failed: {error}"]
            valid = not errors
        self.expect(valid, label + ".schema", group, ["CORE-005", "RES-001"],
                    {"tool": name, "arguments": arguments, "errors": errors[:5],
                     "structured_content_present": isinstance(payload, dict)})
        if not isinstance(payload, dict):
            return None
        status = payload.get("status")
        if not isinstance(status, str):
            self.add(label + ".envelope", 9, ["RES-001"], "FAIL", "status must be a string")
            return None
        known = status in ERROR_STATUSES | {"ok", "not_applicable"}
        envelope = (known and result.is_error == (status in ERROR_STATUSES)
                    and status not in {"unauthorized", "forbidden", "conflict"}
                    and (not result.is_error or isinstance(payload.get("error"), dict)
                         and isinstance(payload["error"].get("message"), str)))
        self.expect(envelope, label + ".envelope", 9,
                    ["RES-010", "RES-011", "DISC-005"],
                    {"tool": name, "status": status, "isError": result.is_error})
        declared = self.tools[name].get("outputSchema")
        if declared:
            try:
                if not validator(declared).is_valid(payload):
                    self.warnings.append(f"{name}: observed result does not match advertised outputSchema (CORE-005 SHOULD)")
            except Exception as error:
                self.warnings.append(f"{name}: advertised outputSchema cannot be checked locally: {error}")
        if status in TRANSIENT:
            self.add(label + ".availability", group, ["CORE-005"], "NOT TESTED",
                     f"{name} returned {status}; no automatic retry")
            return None
        return payload if valid and envelope else None

    def expected_status(self, payload, expected, label, group, requirements):
        if payload is not None:
            self.expect(payload.get("status") == expected, label, group, requirements,
                        {"expected_status": expected, "observed_status": payload.get("status")})

    async def discovery(self):
        if not self.config.discovery_probes:
            self.add("discovery.http", 2, ["DISC-004"], "SKIP", "discovery probes disabled for local fixture")
            return
        parsed = urlsplit(self.config.endpoint)
        headers = {"accept": "application/json, text/event-stream"}
        initialize = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "mcpwp-checker-probe", "version": CHECKER_VERSION}}}
        async with httpx2.AsyncClient(timeout=self.config.timeout, follow_redirects=False) as client:
            plain = urlunsplit(("http", parsed.netloc, "/mcp", "", ""))
            try:
                self.http_probes += 1
                response = await client.post(plain, json=initialize, headers=headers)
                content_type = response.headers.get("content-type", "").split(";")[0]
                serves = is_initialize_response(response)
                self.expect(not serves, "discovery.http", 2, ["DISC-004"],
                            {"url": plain, "http_status": response.status_code,
                             "content_type": content_type})
            except httpx2.ConnectError as error:
                if "refused" in str(error).lower():
                    self.add("discovery.http", 2, ["DISC-004"], "PASS", "plain HTTP connection refused")
                else:
                    self.unavailable("discovery.http", 2, ["DISC-004"], error)
            except Exception as error:
                self.unavailable("discovery.http", 2, ["DISC-004"], error)
            alternate = counterpart(parsed.hostname)
            if alternate:
                url = "https://" + alternate + (f":{parsed.port}" if parsed.port else "") + "/mcp"
                try:
                    self.http_probes += 1
                    self.reserve()
                    async with httpx2.AsyncClient(transport=RedirectTransport(url), timeout=self.config.timeout) as alternate_client:
                        async with streamable_http_client(url, http_client=alternate_client) as streams:
                            async with ClientSession(*streams, read_timeout_seconds=self.config.timeout) as session:
                                result = await session.initialize()
                    valid = result.protocol_version >= "2025-06-18" and result.capabilities.tools is not None
                    if not valid:
                        self.warnings.append("alternate host did not establish MCP-WP initialization (DISC-003 SHOULD)")
                    self.add("discovery.alternate", 2, ["DISC-003"],
                             "PASS" if valid else "NOT TESTED",
                             {"url": url, "protocol_version": result.protocol_version}, required=False)
                except Exception as error:
                    self.warnings.append("alternate site host could not be verified (DISC-003 SHOULD)")
                    self.add("discovery.alternate", 2, ["DISC-003"], "NOT TESTED", str(error)[:350], required=False)
            else:
                self.add("discovery.alternate", 2, ["DISC-003"], "SKIP", "no apex/www counterpart", required=False)

    async def list_tools(self):
        cursor = None
        seen = set()
        for page in range(self.config.max_pages):
            self.reserve()
            result = await self.session.list_tools(
                params=types.PaginatedRequestParams(cursor=cursor) if cursor is not None else None)
            for tool in result.tools:
                value = tool.model_dump(by_alias=True, mode="json", exclude_none=True)
                name = value["name"]
                if name in self.tools:
                    self.add("tools.duplicate", 3, ["CORE-001"], "FAIL", f"duplicate tool name: {name}")
                self.tools[name] = value
            cursor = result.next_cursor
            if cursor is None:
                self.add("tools.pagination", 3, ["CORE-001"], "PASS", f"{page + 1} page(s); {len(self.tools)} tools")
                return
            if cursor in seen:
                raise Incomplete("tools/list returned a repeated pagination cursor")
            seen.add(cursor)
        raise Incomplete(f"tools/list exceeds {self.config.max_pages} pages")

    def inventory(self):
        endpoint = urlsplit(self.config.endpoint)
        page_url = urlunsplit(("https", endpoint.netloc, "/sample", "", ""))
        missing = sorted(set(CORE) - self.tools.keys())
        self.expect(not missing, "tools.core", 3, ["CORE-001"], {"missing": missing})
        for name in CORE:
            if name not in self.tools:
                continue
            tool = self.tools[name]
            annotations = tool.get("annotations", {})
            self.expect(all(annotations.get(k) is v for k, v in ANNOTATIONS.items()),
                        name + ".annotations", 3, ["CORE-003"], annotations)
            if not tool.get("outputSchema"):
                self.warnings.append(f"{name}: no advertised outputSchema (CORE-005 SHOULD)")
            probes = {
                "get_site_info": [{}], "get_contact": [{}],
                "get_services": [{}, {"limit": 1}, {"limit": 100},
                                 {"category": "sample", "cursor": "sample", "limit": 50}],
                "search_site": [{"query": "a"}, {"query": "a" * 500, "limit": 50},
                                {"query": "sample", "limit": 1, "cursor": "sample", "type": "sample"}],
                "get_page": [{"id": "a"}, {"id": "a" * 512}, {"url": "/sample"},
                             {"url": page_url}],
            }[name]
            try:
                check = validator(tool["inputSchema"])
                errors = [{"arguments": p, "errors": [e.message for e in check.iter_errors(p)]}
                          for p in probes]
                self.expect(not any(p["errors"] for p in errors), name + ".inputs", 3,
                            ["CORE-004"], {"coverage": "representative standard arguments", "probes": errors})
            except Exception as error:
                self.add(name + ".inputs", 3, ["CORE-004"], "FAIL", str(error)[:350])

    def declaration(self, site):
        declaration = site.get("mcpwp", {})
        levels, modules = declaration.get("levels", []), declaration.get("modules", [])
        extended = any(m in {"insights", "service_details", "people", "events"}
                       or m.startswith("x-") for m in modules)
        coherent = ("core" in levels and "core" in modules
                    and ("extended" in levels) == extended
                    and ("transactional" in levels) == ("transactions" in modules))
        self.expect(coherent, "site.declaration", 4, ["DECL-001", "DECL-002"], declaration)
        self.schema_version = declaration.get("version", "unknown")
        if self.schema_version != "0.1":
            self.add("site.version", 4, ["VER-002"], "NOT TESTED",
                     f"profile {self.schema_version}; bundled checks and schemas target 0.1")
        for module in modules:
            if module in MODULES:
                missing = sorted(set(MODULES[module]) - self.tools.keys())
                self.expect(not missing, "declaration." + module, 4, ["DECL-003", "LVL-004"],
                            {"missing_tools": missing, "coverage": "inventory only; no non-Core calls"})
            else:
                self.add("declaration." + module, 4, ["DECL-003"], "NOT TESTED",
                         "custom module completeness requires its definition", required=False)
        collisions = [item.get("tool") for item in declaration.get("extensions", [])
                      if item.get("tool") in RESERVED]
        self.expect(not collisions, "extensions.reserved", 10, ["EXTN-001"], {"collisions": collisions})

    async def core_calls(self):
        site = await self.call("get_site_info", {}, "site", 4)
        if site is not None:
            self.expected_status(site, "ok", "site.status", 4, ["CORE-005"])
        if site and site.get("status") == "ok":
            self.declaration(site)
            canonical = urlsplit(site["canonical_url"])
            endpoint = urlsplit(self.transport.resolved)
            self.expect(canonical.hostname == endpoint.hostname and canonical.scheme == "https",
                        "site.canonical", 4, ["DISC-001"],
                        {"canonical_url": site["canonical_url"], "endpoint": self.transport.resolved})
            sections = site["sections"]
            for index, section in enumerate(sections[:self.config.section_limit]):
                label = "section." + str(index)
                page = await self.call("get_page", {"url": section["url"]}, label, 5)
                self.sections_tested += 1
                self.expected_status(page, "ok", label + ".retrievable", 5, ["CORE-010"])
            if len(sections) > self.config.section_limit:
                self.add("sections.coverage", 5, ["CORE-010"], "NOT TESTED",
                         f"sampled {self.config.section_limit} of {len(sections)} section URLs")
        else:
            self.add("site.dependent", 4, ["DECL-001", "DECL-002", "CORE-010", "EXTN-001"],
                     "NOT TESTED", "usable site information is unavailable")
        for name in ("get_services", "get_contact"):
            result = await self.call(name, {}, name, 6)
            if result is not None:
                self.expect(result.get("status") in ("ok", "not_applicable"), name + ".status", 6,
                            ["CORE-006"], {"status": result.get("status")})
        query = self.config.query or (site["sections"][0]["title"][:500]
                                     if site and site.get("status") == "ok" else "about")
        search = await self.call("search_site", {"query": query, "limit": self.config.search_limit}, "search", 7)
        if search:
            self.expected_status(search, "ok", "search.status", 7, ["CORE-040"])
            results = search.get("results", [])
            self.search_observed = len(results)
            if not results:
                self.add("search.references", 7, ["CORE-041"], "NOT TESTED", "positive search returned no reference to test")
            for index, item in enumerate(results[:self.config.search_limit]):
                for key in ("id", "url"):
                    label = f"search.reference.{index}.{key}"
                    page = await self.call("get_page", {key: item[key]}, label, 7)
                    self.expected_status(page, "ok", label + ".retrievable", 7, ["CORE-041"])
                self.search_tested += 1
            if search.get("next_cursor") is not None or len(results) > self.config.search_limit:
                self.add("search.coverage", 7, ["CORE-041"], "NOT TESTED",
                         "search reference sampling limit reached; further results were not traversed")
        nonsense = "mcpwp-no-match-" + uuid.uuid4().hex
        empty = await self.call("search_site", {"query": nonsense}, "search.empty", 7)
        if empty:
            self.expect(empty.get("status") == "ok" and empty.get("results") == [],
                        "search.empty.status", 7, ["CORE-042"],
                        {"query": nonsense, "status": empty.get("status"), "result_count": len(empty.get("results", []))})
        probes = [({"url": "https://mcpwp-offsite-" + uuid.uuid4().hex + ".invalid/"}, "invalid_request", "CORE-050"),
                  ({"url": "/mcpwp-unknown-" + uuid.uuid4().hex}, "not_found", "CORE-052"),
                  ({}, "invalid_request", "CORE-004"),
                  ({"id": "sample", "url": "/sample"}, "invalid_request", "CORE-004")]
        for index, (args, status, requirement) in enumerate(probes):
            label = "page.error." + str(index)
            payload = await self.call("get_page", args, label, 8)
            self.expected_status(payload, status, label + ".status", 8, [requirement])

    async def run(self):
        try:
            outputs = validate_examples.load_schemas(self.config.schema_root)
            self.outputs = {name: validator(outputs[name]) for name in CORE}
        except Exception as error:
            self.add("checker.schemas", 0, [], "NOT TESTED", f"bundled schema setup failed: {error}")
            return self.report()
        try:
            with anyio.fail_after(self.config.run_timeout):
                await self.discovery()
                self.transport = self.transport or RedirectTransport(self.config.endpoint)
                async with httpx2.AsyncClient(transport=self.transport, timeout=self.config.timeout) as client:
                    async with streamable_http_client(self.config.endpoint, http_client=client) as streams:
                        async with ClientSession(*streams, read_timeout_seconds=self.config.timeout) as session:
                            self.session = session
                            self.reserve()
                            initialized = await session.initialize()
                            self.protocol = initialized.protocol_version
                            self.expect(self.protocol >= "2025-06-18" and initialized.capabilities.tools is not None,
                                        "mcp.initialize", 1, ["MCP-001", "MCP-002", "MCP-003", "DISC-005"],
                                        {"protocol_version": self.protocol, "tools_capability": initialized.capabilities.tools is not None})
                            await self.list_tools()
                            self.inventory()
                            await self.core_calls()
        except Exception as error:
            self.unavailable("run.incomplete", 1 if not self.protocol else 3,
                             ["MCP-001", "DISC-005"] if not self.protocol else ["CORE-001"], error)
        return self.report()

    def report(self):
        self.add("extended", 0, [], "NOT TESTED", "Extended behavior is outside this Core checker", required=False)
        self.add("transactional", 0, [], "NOT TESTED", "Transactional tools are never called", required=False)
        covered = {row["group"] for row in self.rows}
        for group in range(1, 11):
            if group not in covered:
                self.add(f"core.group.{group}", group, [], "NOT TESTED", "prerequisite did not complete")
        required = [r for r in self.rows if r["required"]]
        overall = ("failed" if any(r["outcome"] == "FAIL" for r in required) else
                   "incomplete" if any(r["outcome"] == "NOT TESTED" for r in required) else "passed")
        return {"report_version": "1", "checker_version": CHECKER_VERSION,
                "profile_version": "0.1", "declared_profile_version": self.schema_version,
                "schema_version": "0.1", "sdk_version": importlib.metadata.version("mcp"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "endpoint": self.config.endpoint,
                "resolved_endpoint": self.transport.resolved if self.transport else None,
                "protocol_version": self.protocol, "overall": overall,
                "redirects": self.transport.redirects if self.transport else [],
                "coverage": {"scope": "sampled Core checks; not certification",
                             "mcp_requests": self.request_count, "http_probes": self.http_probes,
                             "sections_tested": self.sections_tested,
                             "search_results_observed": self.search_observed,
                             "search_results_tested": self.search_tested,
                             "limits": {k: v for k, v in asdict(self.config).items()
                                        if k in {"timeout", "run_timeout", "max_requests", "max_pages", "section_limit", "search_limit"}},
                             "not_established": ["all valid input values", "complete search coverage",
                                                 "agreement with human-visible content", "actual absence of side effects",
                                                 "Extended and Transactional behavior"]},
                "checks": self.rows, "warnings": list(dict.fromkeys(self.warnings))}


def render_text(report):
    lines = [f"Core checks: {report['overall']} (sampled; not certification)",
             f"Endpoint: {report['resolved_endpoint'] or report['endpoint']}",
             f"MCP: {report['protocol_version'] or 'not negotiated'}"]
    for check in report["checks"]:
        evidence = check["evidence"]
        if not isinstance(evidence, str):
            evidence = json.dumps(evidence, ensure_ascii=False)
        lines.append(f"{check['outcome']:10} {check['id']}: {evidence}")
    lines.extend("WARNING: " + warning for warning in report["warnings"])
    lines.append("Coverage: " + json.dumps(report["coverage"], ensure_ascii=False))
    return "\n".join(lines) + "\n"


def is_initialize_response(response):
    """Recognize successful MCP initialization, rather than generic HTTP JSON."""
    if not response.is_success:
        return False
    content_type = response.headers.get("content-type", "").split(";")[0]
    candidates = []
    if content_type == "application/json":
        candidates = [response.text]
    elif content_type == "text/event-stream":
        # This probe only recognizes evidence. The official SDK owns transport
        # parsing for all actual conformance calls and alternate-host sessions.
        for event in response.text.replace("\r\n", "\n").split("\n\n"):
            candidates.append("\n".join(line[5:].lstrip(" ") for line in event.splitlines()
                                         if line.startswith("data:")))
    for candidate in candidates:
        try:
            message = json.loads(candidate)
            if (message.get("jsonrpc") == "2.0" and "result" in message
                    and message.get("id") == 0):
                types.InitializeResult.model_validate(message["result"])
                return True
        except (ValueError, TypeError, AttributeError):
            continue
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", metavar="HOST", help="hostname or HTTPS origin")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, help="write the report to this file")
    parser.add_argument("--query", help="positive search query (default: first section title)")
    args = parser.parse_args(argv)
    try:
        endpoint = normalize_endpoint(args.host)
    except ValueError as error:
        parser.error(str(error))
    if args.query is not None and not 1 <= len(args.query) <= 500:
        parser.error("--query must contain 1 to 500 characters")
    report = asyncio.run(Checker(Config(endpoint, query=args.query)).run())
    content = (json.dumps(report, indent=2, ensure_ascii=False) + "\n"
               if args.format == "json" else render_text(report))
    if args.output:
        try:
            args.output.write_text(content, encoding="utf-8")
        except OSError as error:
            print(f"Cannot write report: {error}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(content)
    return {"passed": 0, "failed": 1, "incomplete": 2}[report["overall"]]


if __name__ == "__main__":
    sys.exit(main())
