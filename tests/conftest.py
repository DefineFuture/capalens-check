from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from capalens_check.demo import DemoServer
from capalens_check.model import Report

ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA = Path(str(resources.files("capalens_check").joinpath("data/demo")))


@pytest.fixture(scope="session")
def demo() -> Iterator[DemoServer]:
    with DemoServer() as server:
        yield server


def outcomes(report: Report) -> dict[str, str]:
    return {r.check.id: r.outcome for r in report.results}


def evidence(report: Report, check_id: str) -> dict[str, Any]:
    return next(r.evidence for r in report.results if r.check.id == check_id)


Route = Callable[[BaseHTTPRequestHandler], None]


class LocalServer:
    """A loopback HTTP server whose answers a test defines, one function per path."""

    def __init__(self, routes: dict[str, Route]) -> None:
        routes_ = routes

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def _route(self) -> None:
                routes_.get(self.path.split("?")[0], lambda h: h.send_error(404))(self)

            do_GET = do_POST = do_DELETE = _route

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def __enter__(self) -> LocalServer:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def send(handler: BaseHTTPRequestHandler, status: int, body: Any = b"", headers: dict[str, str] | None = None) -> None:
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    handler.send_response(status)
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
