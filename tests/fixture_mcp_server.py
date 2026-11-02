"""Small loopback MCP server for exercising the real HTTP client transport.

``mutate_result`` receives (tool_name, arguments, MCP_result) and returns an MCP
result. ``mutate_tools`` receives the complete tools list and returns a list.
Neither callback sees objects shared with another response.
"""

from __future__ import annotations

import copy
import json
import pathlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE_TOOLS = ("get_site_info", "get_services", "get_contact", "search_site", "get_page")


def _error(status, message):
    return {"status": status, "error": {"message": message}}


class FixtureServer:
    """Context manager serving deterministic JSON or SSE MCP responses."""

    def __init__(
        self,
        *,
        sse=False,
        paginated=False,
        mutate_result=None,
        mutate_tools=None,
        delay=0,
        strict=True,
        http_status=200,
        protocol_version="2025-06-18",
        canonical_host="example.test",
        stateless=False,
        repeat_cursor=False,
        cursor_value="second-page",
    ):
        self.sse = sse
        self.paginated = paginated
        self.mutate_result = mutate_result
        self.mutate_tools = mutate_tools
        self.delay = delay
        self.strict = strict
        self.http_status = http_status
        self.protocol_version = protocol_version
        self.canonical_host = canonical_host
        self.repeat_cursor = repeat_cursor
        self.cursor_value = cursor_value
        self.requests = []
        self.initialized = False
        self.session_id = None if stateless else "fixture-session"
        self.tools = []
        for name in CORE_TOOLS:
            with open(ROOT / "schemas" / "core" / f"{name}.input.json", encoding="utf-8") as handle:
                schema = json.load(handle)
            self.tools.append(
                {
                    "name": name,
                    "description": f"MCP-WP Core {name}",
                    "inputSchema": schema,
                    "annotations": {
                        "readOnlyHint": True,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                }
            )
        self.server = None
        self.thread = None

    @property
    def url(self):
        if self.server is None:
            raise RuntimeError("FixtureServer has not started")
        return f"http://127.0.0.1:{self.server.server_port}/mcp"

    def tool_result(self, name, arguments):
        base = f"https://{self.canonical_host}"
        if name == "get_site_info":
            content = {
                "status": "ok",
                "mcpwp": {"version": "0.1", "levels": ["core"], "modules": ["core"]},
                "name": "Fixture site",
                "description": "A local MCP conformance fixture.",
                "canonical_url": base,
                "language": "en",
                "site_type": "other",
                "sections": [{"id": "about", "title": "About", "url": base + "/about"}],
            }
        elif name in ("get_services", "get_contact"):
            content = {"status": "not_applicable", "reason": "Fixture has no public offerings or contact channels."}
        elif name == "search_site":
            query = arguments.get("query", "")
            content = {"status": "ok", "query": query, "results": []}
            if isinstance(query, str) and query.casefold() in ("about", "fixture", "fixture site"):
                content["results"].append({"id": "about", "title": "About", "url": base + "/about"})
        elif name == "get_page":
            page_id, page_url = arguments.get("id"), arguments.get("url")
            if bool(page_id is not None) == bool(page_url is not None):
                content = _error("invalid_request", "Supply exactly one of id or url.")
            elif page_url and urlsplit(page_url).hostname not in (None, self.canonical_host):
                content = _error("invalid_request", "Only this site's content is available.")
            elif page_id == "about" or page_url in ("/about", base + "/about"):
                content = {
                    "status": "ok",
                    "id": "about",
                    "title": "About",
                    "url": base + "/about",
                    "content_format": "text/markdown",
                    "content": "# About\n\nPublic fixture content.",
                }
            else:
                content = _error("not_found", "No published page has that identifier.")
        else:
            raise KeyError(name)
        payload = {
            "content": [{"type": "text", "text": json.dumps(content)}],
            "structuredContent": content,
            "isError": content["status"] not in ("ok", "not_applicable"),
        }
        if self.mutate_result:
            payload = self.mutate_result(name, copy.deepcopy(arguments), copy.deepcopy(payload))
        return payload

    def __enter__(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def send_body(self, status, body=b"", content_type="application/json", headers=None):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def record(self, body=None):
                fixture.requests.append(
                    {"method": self.command, "path": self.path, "headers": dict(self.headers), "json": body}
                )

            def do_GET(self):
                self.record()
                self.send_body(405)

            def do_DELETE(self):
                self.record()
                self.send_body(200)

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                try:
                    request = json.loads(raw)
                except (ValueError, UnicodeError):
                    self.record()
                    self.send_body(400)
                    return
                self.record(request)
                if self.path != "/mcp":
                    self.send_body(404)
                    return
                if fixture.delay:
                    time.sleep(fixture.delay)
                if fixture.http_status != 200:
                    self.send_body(fixture.http_status)
                    return
                method = request.get("method")
                if method != "initialize" and fixture.strict:
                    if self.headers.get("Mcp-Session-Id") != fixture.session_id:
                        self.send_body(400, b'{"error":"Missing session header"}')
                        return
                    if self.headers.get("MCP-Protocol-Version") != fixture.protocol_version:
                        self.send_body(400, b'{"error":"Missing protocol version header"}')
                        return
                headers = None
                if method == "initialize":
                    result = {
                        "protocolVersion": fixture.protocol_version,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fixture-mcpwp", "version": "1"},
                    }
                    headers = {"Mcp-Session-Id": fixture.session_id} if fixture.session_id else None
                elif method == "notifications/initialized":
                    fixture.initialized = True
                    self.send_body(202)
                    return
                elif method == "tools/list":
                    tools = copy.deepcopy(fixture.tools)
                    if fixture.mutate_tools:
                        tools = fixture.mutate_tools(tools)
                    if fixture.paginated:
                        cursor = request.get("params", {}).get("cursor")
                        if cursor is not None:
                            result = {"tools": tools[2:]}
                            if fixture.repeat_cursor:
                                result["nextCursor"] = cursor
                        else:
                            result = {"tools": tools[:2], "nextCursor": fixture.cursor_value}
                    else:
                        result = {"tools": tools}
                elif method == "tools/call":
                    params = request.get("params", {})
                    try:
                        result = fixture.tool_result(params.get("name"), params.get("arguments") or {})
                    except KeyError:
                        self.send_body(400)
                        return
                else:
                    self.send_body(400)
                    return
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                encoded = json.dumps(response).encode()
                if fixture.sse:
                    self.send_body(200, b"event: message\ndata: " + encoded + b"\n\n", "text/event-stream", headers)
                else:
                    self.send_body(200, encoded, headers=headers)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
