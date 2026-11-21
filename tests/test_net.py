"""The HTTP client's limits: redirects, size, budget, strict JSON, and what reports show of a URL."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler

import pytest

from capalens_ia_check.net import BudgetExceeded, HttpClient, load_json_bytes, public_location
from capalens_ia_check.sources import read
from tests.conftest import LocalServer, Route, send


def test_cross_host_redirect_is_not_followed() -> None:
    def hop(h: BaseHTTPRequestHandler) -> None:
        send(h, 302, headers={"Location": "http://localhost:1/elsewhere"})  # another host name

    with LocalServer({"/doc": hop}) as srv:
        data, problem = read(srv.url("/doc"), HttpClient(timeout=5))
    assert data is None and problem is not None and "302" in problem


def test_same_host_get_redirect_is_followed() -> None:
    routes: dict[str, Route] = {}
    with LocalServer(routes) as srv:  # the server reads the dict on every request
        routes["/old"] = lambda h: send(h, 301, headers={"Location": srv.url("/new")})
        routes["/new"] = lambda h: send(h, 200, {"ok": True}, {"Content-Type": "application/json"})
        data, problem = read(srv.url("/old"), HttpClient(timeout=5))
    assert problem is None and data == b'{"ok": true}'


def test_post_is_never_redirected() -> None:
    def redirect(h: BaseHTTPRequestHandler) -> None:
        # read the body first: answering with unread request data can reset the connection on Windows
        h.rfile.read(int(h.headers.get("Content-Length") or 0))
        send(h, 307, headers={"Location": "/mcp2"})

    with LocalServer({"/mcp": redirect}) as srv:
        resp = HttpClient(timeout=5).request("POST", srv.url("/mcp"), body=b"{}")
    assert resp.status == 307, resp.error
    assert resp.error and "redirect" in resp.error


def test_response_size_is_capped() -> None:
    with LocalServer({"/big": lambda h: send(h, 200, b"x" * 5000, {"Content-Type": "text/plain"})}) as srv:
        resp = HttpClient(timeout=5, max_bytes=1000).request("GET", srv.url("/big"))
    assert resp.error and "larger than 1000" in resp.error and len(resp.body) == 1000


def test_budget_is_enforced() -> None:
    with LocalServer({"/a": lambda h: send(h, 200, b"{}")}) as srv:
        client = HttpClient(timeout=5, max_requests=2)
        client.request("GET", srv.url("/a"))
        client.request("GET", srv.url("/a"))
        with pytest.raises(BudgetExceeded):
            client.request("GET", srv.url("/a"))


def test_user_agent_and_headers_are_sent() -> None:
    seen: dict[str, str] = {}

    def echo(h: BaseHTTPRequestHandler) -> None:
        seen.update({k.lower(): v for k, v in h.headers.items()})
        send(h, 200, b"{}")

    with LocalServer({"/a": echo}) as srv:
        HttpClient(timeout=5, headers={"X-Api-Key": "k"}).request("GET", srv.url("/a"))
    assert seen["user-agent"].startswith("capalens-ia-check/") and seen["x-api-key"] == "k"


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        (
            "https://user:pw@mcp.example.com:8443/mcp?token=abc&x=1#frag",
            "https://mcp.example.com:8443/mcp?token=...&x=...",
        ),
        ("https://mcp.example.com/mcp", "https://mcp.example.com/mcp"),
    ],
)
def test_public_location_drops_credentials(raw: str, shown: str) -> None:
    assert public_location(raw) == shown


@pytest.mark.parametrize("data", [b'{"a": 1, "a": 2}', b'{"a": NaN}', b"\xff"])
def test_strict_json(data: bytes) -> None:
    with pytest.raises((ValueError, UnicodeDecodeError)):
        load_json_bytes(data)
