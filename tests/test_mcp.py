"""MCP checks against the bundled demo server and small local servers. Nothing leaves the machine."""

from __future__ import annotations

import copy
import json
import time
from http.server import BaseHTTPRequestHandler
from typing import Any

import pytest

from capalens_ia_check import mcp
from capalens_ia_check.demo import DemoServer
from capalens_ia_check.model import Report
from capalens_ia_check.net import HttpClient
from tests.conftest import LocalServer, evidence, outcomes, send


def run(url: str, *, budget: int = 25, **kw: Any) -> Report:
    return mcp.check(url, HttpClient(timeout=5, max_requests=budget), **kw)


def test_good_server_has_no_fail(demo: DemoServer) -> None:
    report = run(demo.url("good"))
    got = outcomes(report)
    assert "fail" not in got.values() and "review" not in got.values() and "unknown" not in got.values()
    assert got["SEC-004"] == "skip"
    assert report.facts["protocolVersion"] == "2025-11-25" and report.facts["toolCount"] == 4
    assert report.facts["serverInfo"]["name"] == "capalens-demo-good" and report.facts["sessionIssued"] is True
    assert all(t["sha256"].startswith("sha256:") for t in report.facts["tools"])
    assert report.requests == 7  # initialize, initialized, 2 x tools/list, prompts/list, unknown method, DELETE


def test_event_stream_answers_are_read(demo: DemoServer) -> None:
    got = outcomes(run(demo.url("sse")))
    assert got["MCP-003"] == "pass" and got["MCP-008"] == "pass" and got["MCP-006"] == "pass"


def test_stateless_revision_uses_server_discover(demo: DemoServer) -> None:
    report = run(demo.url("modern"))
    got = outcomes(report)
    assert report.facts["handshake"] == "server/discover" and report.facts["protocolVersion"] == "2026-07-28"
    assert got["MCP-003"] == got["MCP-004"] == got["MCP-005"] == got["MCP-008"] == "pass"
    assert got["MCP-007"] == "skip"


def test_risky_server_fails_and_flags(demo: DemoServer) -> None:
    report = run(demo.url("risky"))
    got = outcomes(report)
    for cid in ("MCP-005", "MCP-007", "MCP-009", "MCP-010", "MCP-011", "MCP-012", "MCP-013", "MCP-014"):
        assert got[cid] == "fail", cid
    assert got["SEC-001"] == got["SEC-002"] == got["SEC-003"] == "review"
    assert evidence(report, "MCP-010")["duplicates"] == ["read_file"]
    categories = {c["category"] for c in evidence(report, "SEC-001")["candidates"]}
    assert {"hidden-directive", "local-secret-access", "exfiltration"} <= categories
    conflict = evidence(report, "SEC-003")["conflicts"][0]
    assert conflict["tool"] == "cleanup cache!" and conflict["evidence"][0]["word"] == "Deletes"


def test_authentication_is_reported_not_guessed(demo: DemoServer) -> None:
    report = run(demo.url("auth"))
    got = outcomes(report)
    assert got["MCP-002"] == "pass" and got["MCP-003"] == "unknown" and report.facts["authRequired"] is True
    client = HttpClient(timeout=5, headers={"Authorization": "Bearer demo-token"})
    assert outcomes(mcp.check(demo.url("auth"), client))["MCP-003"] == "pass"


def test_token_never_reaches_the_report(demo: DemoServer) -> None:
    client = HttpClient(timeout=5, headers={"Authorization": "Bearer demo-token"})
    report = mcp.check(demo.url("auth") + "?key=secret-value", client)
    text = json.dumps(report.to_json())
    assert "demo-token" not in text and "secret-value" not in text and "key=..." in text


def test_unreachable_endpoint() -> None:
    with LocalServer({}) as server:
        url = server.url("/mcp")
    report = run(url)  # the server is closed now
    got = outcomes(report)
    assert got["MCP-002"] == "fail" and got["MCP-003"] == "unknown"


def test_budget_spent_is_unknown_not_fail(demo: DemoServer) -> None:
    report = run(demo.url("good"), budget=3)
    got = outcomes(report)
    assert got["MCP-003"] == "pass" and got["MCP-013"] == "unknown"
    assert any("budget" in n for n in report.notes)


@pytest.mark.parametrize(
    ("url", "outcome"),
    [
        ("https://mcp.example.com/mcp", "pass"),
        ("http://127.0.0.1:8000/mcp", "pass"),
        ("http://localhost/mcp", "pass"),
        ("http://[::1]:9000/mcp", "pass"),
        ("http://mcp.example.com/mcp", "fail"),
        ("http://10.0.0.5/mcp", "fail"),
    ],
)
def test_https_rule(url: str, outcome: str) -> None:
    assert mcp.transport_outcome(url)[0] == outcome


def test_drift_against_a_baseline(demo: DemoServer) -> None:
    first = run(demo.url("good"))
    same = run(demo.url("good"), baseline=first.to_json())
    assert outcomes(same)["SEC-004"] == "pass"
    changed = copy.deepcopy(first.to_json())
    changed["facts"]["tools"][0]["sha256"] = "sha256:" + "0" * 64
    changed["facts"]["tools"].append({"name": "gone_tool", "sha256": "sha256:" + "1" * 64})
    report = run(demo.url("good"), baseline={"reports": [changed]})  # a run report works as a baseline too
    assert outcomes(report)["SEC-004"] == "review"
    ev = evidence(report, "SEC-004")
    assert ev["changed"] == ["get_forecast"] and ev["removed"] == ["gone_tool"] and ev["added"] == []


def test_handshake_falls_back_only_on_protocol_answers() -> None:
    calls: list[str] = []

    def mcp_route(h: BaseHTTPRequestHandler) -> None:
        body = json.loads(h.rfile.read(int(h.headers["Content-Length"])))
        calls.append(body["method"])
        send(h, 500, b"boom", {"Content-Type": "text/plain"})

    with LocalServer({"/mcp": mcp_route}) as server:
        report = run(server.url("/mcp"))
    assert calls == ["initialize"]  # a server error is not a sign of the stateless revision
    assert outcomes(report)["MCP-003"] == "fail"


def test_an_event_stream_left_open_does_not_hang() -> None:
    def mcp_route(h: BaseHTTPRequestHandler) -> None:
        body = json.loads(h.rfile.read(int(h.headers["Content-Length"])))
        h.send_response(200)
        h.send_header("Content-Type", "text/event-stream")
        h.end_headers()
        if "id" in body:
            result = {"protocolVersion": "2025-11-25", "capabilities": {}, "serverInfo": {"name": "s"}}
            h.wfile.write(f"data: {json.dumps({'jsonrpc': '2.0', 'id': body['id'], 'result': result})}\n\n".encode())
            h.wfile.flush()
            time.sleep(3)  # keeps the stream open

    with LocalServer({"/mcp": mcp_route}) as server:
        started = time.monotonic()
        session = mcp.McpSession(HttpClient(timeout=10), server.url("/mcp"))
        reply = session.rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {}})
        assert reply.result is not None and time.monotonic() - started < 2.5
