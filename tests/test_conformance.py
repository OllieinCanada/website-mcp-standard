"""Core checker coverage with the real official SDK and local fixture servers."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx2

from tools.check_conformance import (
    Checker, Config, RedirectBlocked, RedirectTransport, main,
    normalize_endpoint, is_initialize_response,
)
try:
    from tests.fixture_mcp_server import FixtureServer
except ModuleNotFoundError:
    from fixture_mcp_server import FixtureServer


class CheckerTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, fixture, **settings):
        config = Config(fixture.url, discovery_probes=False, **settings)
        transport = RedirectTransport(fixture.url, httpx2.AsyncHTTPTransport(trust_env=False))
        return await Checker(config, transport=transport).run()

    async def test_input_probe_uses_the_checked_site_host(self):
        def mutate(tools):
            for tool in tools:
                if tool["name"] == "get_page":
                    tool["inputSchema"]["properties"]["url"]["pattern"] = r"^(/|https://127\.0\.0\.1)"
            return tools
        with FixtureServer(canonical_host="127.0.0.1", mutate_tools=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "passed", report)

    async def test_default_search_query_stays_within_standard_input_limit(self):
        long_title = "A" * 501
        def mutate(name, args, result):
            content = result["structuredContent"]
            if name == "get_site_info":
                content["sections"][0]["title"] = long_title
            elif name == "search_site" and args["query"] == long_title[:500]:
                content["results"] = [{"id": "about", "title": "About", "url": "https://127.0.0.1/about"}]
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
            queries = [request["json"]["params"]["arguments"]["query"]
                       for request in fixture.requests if request["json"]
                       and request["json"].get("method") == "tools/call"
                       and request["json"]["params"]["name"] == "search_site"]
        self.assertTrue(queries)
        self.assertTrue(all(1 <= len(query) <= 500 for query in queries))
        self.assertEqual(report["overall"], "passed", report)

    async def test_stateless_server(self):
        with FixtureServer(stateless=True, canonical_host="127.0.0.1") as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "passed", report)

    async def test_repeated_cursor_is_incomplete(self):
        with FixtureServer(paginated=True, repeat_cursor=True, canonical_host="127.0.0.1") as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "incomplete", report)
        self.assertTrue(any("repeated" in str(r["evidence"]) for r in report["checks"]))

    async def test_empty_opaque_cursors_are_preserved_and_coverage_is_incomplete(self):
        def mutate(name, args, result):
            if name == "search_site" and result["structuredContent"]["results"]:
                result["structuredContent"]["next_cursor"] = ""
            return result
        with FixtureServer(paginated=True, cursor_value="", canonical_host="127.0.0.1",
                           mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "incomplete", report)
        self.assertFalse(any(r["outcome"] == "FAIL" for r in report["checks"]))
        self.assertTrue(any(r["id"] == "tools.pagination" and r["outcome"] == "PASS" for r in report["checks"]))
        self.assertTrue(any(r["id"] == "search.coverage" and r["outcome"] == "NOT TESTED" for r in report["checks"]))

    async def test_malformed_typed_result_is_failure(self):
        def mutate(name, args, result):
            if name == "get_contact":
                result["content"] = "not-an-array"
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed", report)

    async def test_invalid_unexercised_input_schema_branch_fails(self):
        def mutate(tools):
            tools[0]["inputSchema"]["properties"]["unused"] = {"type": 42}
            return tools
        with FixtureServer(canonical_host="127.0.0.1", mutate_tools=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed", report)
        self.assertTrue(any(r["id"] == "get_site_info.inputs" and r["outcome"] == "FAIL"
                            for r in report["checks"]))

    async def test_nonstring_status_fails_and_independent_calls_continue(self):
        def mutate(name, args, result):
            if name == "get_services":
                result["structuredContent"]["status"] = []
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed", report)
        self.assertTrue(any(r["id"] == "get_contact.schema" and r["outcome"] == "PASS"
                            for r in report["checks"]))

    async def test_old_protocol_version_is_failure(self):
        with FixtureServer(protocol_version="2024-11-05", canonical_host="127.0.0.1") as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed", report)

    async def test_json_and_sse_complete_initialization_and_pagination(self):
        for sse in (False, True):
            with self.subTest(sse=sse), FixtureServer(sse=sse, paginated=True, canonical_host="127.0.0.1") as fixture:
                report = await self.check(fixture)
                self.assertEqual(report["overall"], "passed", report)
                self.assertTrue(fixture.initialized)
                requests = [r for r in fixture.requests if r["json"]]
                methods = [r["json"]["method"] for r in requests]
                self.assertEqual(methods[:2], ["initialize", "notifications/initialized"])
                self.assertEqual(methods.count("tools/list"), 2)
                for request in requests[1:]:
                    headers = {k.lower(): v for k, v in request["headers"].items()}
                    self.assertEqual(headers["mcp-session-id"], "fixture-session")
                    self.assertEqual(headers["mcp-protocol-version"], "2025-06-18")
                called = {r["json"]["params"]["name"] for r in requests if r["json"]["method"] == "tools/call"}
                self.assertEqual(called, {"get_site_info", "get_services", "get_contact", "search_site", "get_page"})
                self.assertEqual(report["coverage"]["search_results_tested"], 1)

    async def test_missing_core_tool_is_failure(self):
        with FixtureServer(canonical_host="127.0.0.1", mutate_tools=lambda tools: tools[:-1]) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed")
        self.assertTrue(any(r["id"] == "tools.core" and r["outcome"] == "FAIL" for r in report["checks"]))

    async def test_advertised_output_schema_is_recommendation(self):
        def mutate(tools):
            for tool in tools:
                tool["outputSchema"] = {"type": "object", "required": ["unsupported_field"]}
            return tools
        with FixtureServer(canonical_host="127.0.0.1", mutate_tools=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "passed", report)
        self.assertTrue(any("does not match advertised" in w for w in report["warnings"]))

    async def test_status_and_error_flag_disagreement_fails(self):
        def mutate(name, args, result):
            if name == "get_page" and result["isError"]:
                result["isError"] = False
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed")
        self.assertTrue(any(r["outcome"] == "FAIL" and r["id"].endswith(".envelope") for r in report["checks"]))

    async def test_missing_structured_content_fails(self):
        def mutate(name, args, result):
            if name == "get_contact":
                del result["structuredContent"]
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed")

    async def test_declaration_inconsistency_fails(self):
        def mutate(name, args, result):
            if name == "get_site_info":
                result["structuredContent"]["mcpwp"]["levels"].append("extended")
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed")

    async def test_declared_module_missing_tools_and_reserved_extension_fail(self):
        def mutate(name, args, result):
            if name == "get_site_info":
                result["structuredContent"]["mcpwp"] = {
                    "version": "0.1", "levels": ["core", "extended"],
                    "modules": ["core", "events"], "extensions": [{"tool": "get_event"}]}
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        failed = {r["id"] for r in report["checks"] if r["outcome"] == "FAIL"}
        self.assertIn("declaration.events", failed)
        self.assertIn("extensions.reserved", failed)

    async def test_public_unauthorized_fails(self):
        def mutate(name, args, result):
            if name == "get_contact":
                result["structuredContent"] = {"status": "unauthorized", "error": {"message": "Login"}}
                result["isError"] = True
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed")

    async def test_rate_limit_is_incomplete_not_conformance_failure(self):
        def mutate(name, args, result):
            if name == "get_services":
                result["structuredContent"] = {"status": "rate_limited", "error": {"message": "Later", "retry_after_seconds": 30}}
                result["isError"] = True
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "incomplete", report)
        self.assertFalse(any(r["outcome"] == "FAIL" for r in report["checks"]))

    async def test_unresolved_section_or_search_reference_fails(self):
        def mutate(name, args, result):
            if name == "get_page" and result["structuredContent"]["status"] == "ok":
                result["structuredContent"] = {"status": "not_found", "error": {"message": "Missing"}}
                result["isError"] = True
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed")

    async def test_request_and_page_budgets_are_explicitly_incomplete(self):
        for limits in ({"max_requests": 2}, {"max_pages": 1}):
            with self.subTest(limits=limits), FixtureServer(canonical_host="127.0.0.1", paginated=True) as fixture:
                report = await self.check(fixture, **limits)
            self.assertEqual(report["overall"], "incomplete", report)
            self.assertLessEqual(report["coverage"]["mcp_requests"], limits.get("max_requests", 100))

    async def test_sampling_marks_unvisited_content_incomplete(self):
        def mutate(name, args, result):
            if name == "get_site_info":
                result["structuredContent"]["sections"].append({"id": "about2", "title": "About", "url": "https://127.0.0.1/about"})
            if name == "search_site" and result["structuredContent"]["results"]:
                result["structuredContent"]["next_cursor"] = "more"
            return result
        with FixtureServer(canonical_host="127.0.0.1", mutate_result=mutate) as fixture:
            report = await self.check(fixture, section_limit=1)
        self.assertEqual(report["overall"], "incomplete", report)
        self.assertTrue(any(r["id"] == "sections.coverage" for r in report["checks"]))
        self.assertTrue(any(r["id"] == "search.coverage" for r in report["checks"]))

    async def test_timeout_and_http_auth_denial(self):
        with FixtureServer(delay=0.15, canonical_host="127.0.0.1") as fixture:
            report = await self.check(fixture, timeout=0.03)
        self.assertEqual(report["overall"], "incomplete")
        with FixtureServer(http_status=401, canonical_host="127.0.0.1") as fixture:
            report = await self.check(fixture)
        self.assertEqual(report["overall"], "failed", report)


class RedirectTests(unittest.IsolatedAsyncioTestCase):
    async def test_https_307_counterpart_preserves_method_and_body(self):
        requests = []
        async def handler(request):
            requests.append(request)
            if request.url.host == "example.test":
                return httpx2.Response(307, headers={"location": "https://www.example.test/mcp"})
            return httpx2.Response(200, json={"ok": True})
        transport = RedirectTransport("https://example.test/mcp", httpx2.MockTransport(handler))
        async with httpx2.AsyncClient(transport=transport) as client:
            response = await client.post("https://example.test/mcp", content=b"test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r.method for r in requests], ["POST", "POST"])
        self.assertEqual([r.content for r in requests], [b"test", b"test"])
        self.assertEqual(transport.resolved, "https://www.example.test/mcp")

    async def test_cross_domain_http_downgrade_wrong_code_and_loops_block(self):
        for code, target in [(307, "https://other.test/mcp"), (308, "http://example.test/mcp"),
                             (302, "https://www.example.test/mcp"), (307, "https://example.test/mcp")]:
            with self.subTest(code=code, target=target):
                async def handler(request):
                    return httpx2.Response(code, headers={"location": target})
                transport = RedirectTransport("https://example.test/mcp", httpx2.MockTransport(handler))
                async with httpx2.AsyncClient(transport=transport) as client:
                    with self.assertRaises(RedirectBlocked):
                        await client.post("https://example.test/mcp", content=b"test")


class CommandTests(unittest.TestCase):
    def test_plain_http_probe_requires_actual_mcp_result(self):
        for content in ({"hello": "world"}, {"jsonrpc": "2.0", "id": 0, "result": {}}):
            self.assertFalse(is_initialize_response(httpx2.Response(200, json=content)))
        self.assertFalse(is_initialize_response(httpx2.Response(200, text="<html>hello</html>")))
        message = {"jsonrpc": "2.0", "id": 0, "result": {
            "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
            "serverInfo": {"name": "fixture", "version": "1"}}}
        self.assertTrue(is_initialize_response(httpx2.Response(200, json=message)))
        self.assertTrue(is_initialize_response(httpx2.Response(200, text="data: " + json.dumps(message) + "\n\n",
                                                              headers={"content-type": "text/event-stream"})))
    def test_endpoint_validation(self):
        self.assertEqual(normalize_endpoint("www.example.test"), "https://www.example.test/mcp")
        self.assertEqual(normalize_endpoint("https://example.test/"), "https://example.test/mcp")
        for host in ["http://example.test", "https://user:pass@example.test", "https://example.test/mcp", "https://example.test?x=1"]:
            with self.subTest(host=host), self.assertRaises(ValueError):
                normalize_endpoint(host)

    def test_exit_codes_and_json_output_file(self):
        for overall, code in [("passed", 0), ("failed", 1), ("incomplete", 2)]:
            async def run(checker):
                return {"overall": overall}
            with self.subTest(overall=overall), patch.object(Checker, "run", run):
                with tempfile.TemporaryDirectory() as directory:
                    destination = Path(directory) / "report.json"
                    self.assertEqual(main(["example.test", "--format", "json", "--output", str(destination)]), code)
                    self.assertEqual(json.loads(destination.read_text())["overall"], overall)


if __name__ == "__main__":
    unittest.main()
