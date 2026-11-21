"""A small, careful HTTP client (standard library only).

* A request budget and a per-request timeout; a cap on response size.
* Redirects: none for POST; for GET at most three, same host only, never from HTTPS to HTTP.
* TLS is always verified. Header values given by the user are sent and never written to a report.
* Server-sent events are read line by line until the expected JSON-RPC answer arrives, so a stream the
  server keeps open does not hang the check.
"""

from __future__ import annotations

import ipaddress
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from . import __version__

USER_AGENT = f"capalens-check/{__version__} (+https://github.com/Capalens/capalens-check)"
MAX_BYTES = 5 * 1024 * 1024


class BudgetExceeded(Exception):
    """The request budget for this target is spent; the remaining checks are unknown."""


@dataclass
class Response:
    status: int | None
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    error: str | None = None  # network, TLS, size or redirect problem, in words
    messages: list[dict[str, Any]] | None = None  # JSON objects read from an event stream

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()

    def header(self, name: str) -> str | None:
        return self.headers.get(name.lower())


def is_loopback(url: str) -> bool:
    host = urllib.parse.urlsplit(url).hostname or ""
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def public_location(url: str) -> str:
    """The URL as reports show it: no user info, no query values, no fragment."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    query = "&".join(f"{k}=..." for k, _ in urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    return urllib.parse.urlunsplit((parts.scheme, host, parts.path, query, ""))


class _NoPostRedirect(urllib.request.HTTPRedirectHandler):
    """Same-host GET redirects only, at most three, never HTTPS to HTTP."""

    max_redirections = 3

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        old, new = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if req.get_method() != "GET":
            return None
        if new.hostname != old.hostname or new.scheme not in ("http", "https"):
            return None
        if old.scheme == "https" and new.scheme == "http":
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpClient:
    def __init__(
        self,
        *,
        timeout: float = 15.0,
        max_requests: int = 25,
        max_bytes: int = MAX_BYTES,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_requests = max_requests
        self.max_bytes = max_bytes
        self.extra_headers = dict(headers or {})
        self.requests = 0
        self._opener = urllib.request.build_opener(
            _NoPostRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        until: Callable[[dict[str, Any]], bool] | None = None,
    ) -> Response:
        """One request. ``until``: for an event stream, stop reading once a message satisfies it."""
        if self.requests >= self.max_requests:
            raise BudgetExceeded(f"request budget of {self.max_requests} spent")
        self.requests += 1
        h = {"User-Agent": USER_AGENT, **self.extra_headers, **(headers or {})}
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            raw = self._opener.open(req, timeout=self.timeout)
        except urllib.error.HTTPError as err:  # a status >= 400 (or a refused redirect) is an answer
            hdrs = {k.lower(): v for k, v in err.headers.items()} if err.headers else {}
            data = _read_capped(err, self.max_bytes)
            payload = data[0] if isinstance(data, tuple) else data
            if 300 <= err.code < 400:
                return Response(err.code, hdrs, payload, error=f"redirect not followed (HTTP {err.code})")
            return Response(err.code, hdrs, payload)
        except (TimeoutError, urllib.error.URLError, OSError, ssl.SSLError, ValueError) as err:
            reason = getattr(err, "reason", err)
            return Response(None, error=f"{type(reason).__name__}: {reason}"[:300])
        with raw:
            hdrs = {k.lower(): v for k, v in raw.headers.items()}
            ctype = hdrs.get("content-type", "").split(";")[0].strip().lower()
            if ctype == "text/event-stream":
                messages, error = _read_events(raw, self.max_bytes, self.timeout, until)
                return Response(raw.status, hdrs, b"", error=error, messages=messages)
            data = _read_capped(raw, self.max_bytes)
            if isinstance(data, tuple):
                return Response(raw.status, hdrs, data[0], error=data[1])
            return Response(raw.status, hdrs, data)


def _read_capped(fp: Any, limit: int) -> bytes | tuple[bytes, str]:
    try:
        data: bytes = fp.read(limit + 1)
    except (TimeoutError, OSError) as err:
        return b"", f"read failed: {type(err).__name__}"
    if len(data) > limit:
        return data[:limit], f"response larger than {limit} bytes"
    return data


def _read_events(
    fp: Any, limit: int, timeout: float, until: Callable[[dict[str, Any]], bool] | None
) -> tuple[list[dict[str, Any]], str | None]:
    """JSON objects from ``data:`` lines, until ``until`` matches, the stream ends, or a limit is hit."""
    messages: list[dict[str, Any]] = []
    data: list[str] = []
    seen = 0
    deadline = time.monotonic() + timeout
    while True:
        if time.monotonic() > deadline:
            return messages, "event stream: no answer before the timeout"
        try:
            line_b = fp.readline(limit)
        except (TimeoutError, OSError):
            return messages, "event stream: read timed out"
        if not line_b:
            break
        seen += len(line_b)
        if seen > limit:
            return messages, f"event stream larger than {limit} bytes"
        line = line_b.decode("utf-8", "replace").rstrip("\r\n")
        if line == "":
            if data:
                obj = _json_object("\n".join(data))
                data = []
                if obj is not None:
                    messages.append(obj)
                    if until is not None and until(obj):
                        return messages, None
            continue
        if line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    if data and (obj := _json_object("\n".join(data))) is not None:
        messages.append(obj)
    return messages, None


def _json_object(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def load_json_bytes(data: bytes) -> Any:
    """Strict JSON: UTF-8 (a BOM is accepted), no NaN or Infinity, duplicate keys refused."""

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate key {key!r}")
            out[key] = value
        return out

    def no_constant(name: str) -> Any:
        raise ValueError(f"{name} is not JSON")

    text = data.decode("utf-8-sig")
    return json.loads(text, object_pairs_hook=no_duplicates, parse_constant=no_constant)
