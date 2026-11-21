"""Read-only checks of a remote MCP server over Streamable HTTP.

What is sent, and nothing else: the handshake (``initialize`` + ``notifications/initialized``, or
``server/discover`` for the stateless 2026-07-28 revision), ``tools/list`` (all pages), ``prompts/list`` and
``resources/list`` when declared, one request for a method that does not exist, and a ``DELETE`` that ends
the session when the server issued one. No tool is ever called, no resource read, no prompt fetched.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from . import __version__
from .heuristics import action_labels, analyse_tools
from .model import Report, arr, obj
from .net import BudgetExceeded, HttpClient, Response, is_loopback, load_json_bytes, public_location
from .results import Results
from .screens import text_screens

KNOWN_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25", "2026-07-28")
OFFERED_VERSION = "2025-11-25"  # offered in initialize; the server may answer with any version it supports
MODERN_VERSION = "2026-07-28"  # stateless revision: server/discover, _meta on every request
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_INFO = "io.modelcontextprotocol/clientInfo"
META_SERVER = "io.modelcontextprotocol/serverInfo"
CLIENT_INFO = {"name": "capalens-check", "version": __version__}
TOOL_NAME = re.compile(r"[A-Za-z0-9_.\-]{1,128}")
MAX_PAGES = 20
UNKNOWN_METHOD = "capalens-check/no-such-method"


@dataclass
class Reply:
    status: int | None
    message: dict[str, Any] | None
    id_matches: bool | None  # None when there was no answer to compare
    error_text: str | None = None
    content_type: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def result(self) -> dict[str, Any] | None:
        value = (self.message or {}).get("result")
        return value if isinstance(value, dict) else None

    @property
    def error_code(self) -> int | None:
        error = (self.message or {}).get("error")
        code = error.get("code") if isinstance(error, dict) else None
        return code if isinstance(code, int) else None

    def describe(self) -> str:
        if self.status is None:
            return self.error_text or "no answer"
        parts = [f"HTTP {self.status}"]
        if self.content_type:
            parts.append(self.content_type)
        if self.error_code is not None:
            parts.append(f"JSON-RPC error {self.error_code}")
        if self.error_text:
            parts.append(self.error_text)
        return ", ".join(parts)


def _reply(resp: Response, rid: int | None) -> Reply:
    def make(message: dict[str, Any] | None, matches: bool | None) -> Reply:
        return Reply(resp.status, message, matches, resp.error, resp.content_type, resp.headers)

    candidates: list[dict[str, Any]] = []
    if resp.messages is not None:
        candidates = resp.messages
    elif resp.body[:1] in (b"{", b"["):
        try:
            value = load_json_bytes(resp.body)
        except (ValueError, UnicodeDecodeError):
            return make(None, None)
        candidates = [value] if isinstance(value, dict) else []
    answers = [m for m in candidates if m.get("jsonrpc") == "2.0" and ("result" in m or "error" in m)]
    mine = next((m for m in answers if m.get("id") == rid), None)
    if mine is not None:
        return make(mine, True)
    if answers:
        # an error for an unreadable request may carry id null (JSON-RPC 2.0 §5)
        other = answers[0]
        return make(other, other.get("id") is None and "error" in other)
    return make(None, None)


class McpSession:
    def __init__(self, http: HttpClient, url: str) -> None:
        self.http = http
        self.url = url
        self.era: str | None = None  # "initialize" or "discover" once a handshake worked
        self.version: str | None = None
        self.session_id: str | None = None
        self.id_checks: list[bool] = []
        self._next = 0

    def _headers(self, method: str) -> dict[str, str]:
        h = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.era == "discover":
            h["MCP-Protocol-Version"] = MODERN_VERSION
            h["Mcp-Method"] = method
        elif self.version and method != "initialize":
            h["MCP-Protocol-Version"] = self.version
        if self.session_id and self.era == "initialize":
            h["Mcp-Session-Id"] = self.session_id
        return h

    def rpc(self, method: str, params: dict[str, Any] | None = None, *, notify: bool = False) -> Reply:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        p = dict(params or {})
        if self.era == "discover":
            p["_meta"] = {META_VERSION: MODERN_VERSION, META_CAPS: {}, META_INFO: CLIENT_INFO}
        if p or not notify:
            payload["params"] = p
        rid: int | None = None
        if not notify:
            self._next += 1
            rid = self._next
            payload["id"] = rid
        resp = self.http.request(
            "POST",
            self.url,
            headers=self._headers(method),
            body=json.dumps(payload).encode("utf-8"),
            until=lambda m: m.get("id") == rid and ("result" in m or "error" in m),
        )
        reply = _reply(resp, rid)
        if rid is not None and reply.id_matches is not None:
            self.id_checks.append(reply.id_matches)
        return reply

    def handshake(self) -> tuple[Reply, list[str]]:
        """(the reply that decided, the attempts made). Tries initialize, then server/discover."""
        attempts = ["initialize"]
        init = self.rpc(
            "initialize", {"protocolVersion": OFFERED_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO}
        )
        if init.result is not None:
            self.era = "initialize"
            version = init.result.get("protocolVersion")
            self.version = version if isinstance(version, str) else None
            self.session_id = init.headers.get("mcp-session-id")
            self.rpc("notifications/initialized", notify=True)
            return init, attempts
        if init.status in (400, 404, 405) or init.error_code in (-32601, -32602, -32022):
            attempts.append("server/discover")
            self.era = "discover"
            disc = self.rpc("server/discover")
            if disc.result is not None:
                self.version = MODERN_VERSION
                return disc, attempts
            self.era = None
        return init, attempts

    def list_all(self, method: str, key: str) -> tuple[list[Any] | None, str | None, int, Reply | None]:
        """(items, problem, pages, last reply). problem: None, repeated-cursor, too-many-pages, invalid."""
        items: list[Any] = []
        seen: set[str] = set()
        cursor: str | None = None
        last: Reply | None = None
        for page in range(1, MAX_PAGES + 1):
            last = self.rpc(method, {"cursor": cursor} if cursor else None)
            result = last.result
            if result is None or not isinstance(result.get(key), list):
                return None, "invalid", page, last
            items.extend(result[key])
            nxt = result.get("nextCursor")
            if not isinstance(nxt, str) or not nxt:
                return items, None, page, last
            if nxt in seen:
                return items, "repeated-cursor", page, last
            seen.add(nxt)
            cursor = nxt
        return items, "too-many-pages", MAX_PAGES, last

    def close(self) -> None:
        if self.session_id and self.era == "initialize":
            with contextlib.suppress(BudgetExceeded):  # ending the session is a courtesy, not a check
                self.http.request("DELETE", self.url, headers=self._headers("DELETE"))


def tool_hash(tool: Any) -> str:
    canonical = json.dumps(tool, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _texts(kind: str, items: list[Any]) -> list[tuple[str, str]]:
    """(label, text) pairs a model reads: names, titles, descriptions, argument and parameter descriptions."""
    out: list[tuple[str, str]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        label = f"{kind}[{item.get('name', i)}]"
        for key in ("name", "title", "description"):
            if isinstance(item.get(key), str):
                out.append((f"{label}.{key}", item[key]))
        schema = item.get("inputSchema")
        props = schema.get("properties") if isinstance(schema, dict) else None
        for prop, sub in props.items() if isinstance(props, dict) else ():
            if isinstance(sub, dict) and isinstance(sub.get("description"), str):
                out.append((f"{label}.inputSchema.{prop}", sub["description"]))
        for arg in arr(item.get("arguments")):
            if isinstance(arg, dict) and isinstance(arg.get("description"), str):
                out.append((f"{label}.arguments.{arg.get('name')}", arg["description"]))
    return out


def _baseline_tools(baseline: dict[str, Any] | None, location: str, name: str | None) -> dict[str, str] | None:
    if not baseline:
        return None
    reports = arr(baseline.get("reports")) if "reports" in baseline else [baseline]
    for rep in reports:
        target = obj(obj(rep).get("target"))
        if target.get("kind") != "mcp":
            continue
        if target.get("location") == location or (name and target.get("name") == name):
            tools = obj(rep).get("facts", {}).get("tools")
            if isinstance(tools, list):
                return {str(t.get("name")): str(t.get("sha256")) for t in tools if isinstance(t, dict)}
    return None


def transport_outcome(url: str) -> tuple[str, str]:
    """MCP-001: HTTPS, or plain HTTP on a loopback address only."""
    scheme = url.split(":", 1)[0].lower()
    if scheme == "https":
        return "pass", "HTTPS"
    if scheme == "http" and is_loopback(url):
        return "pass", "plain HTTP on a loopback address (local testing)"
    return "fail", f"{scheme.upper()} to a non-loopback address"


def check(
    url: str,
    http: HttpClient,
    *,
    name: str | None = None,
    baseline: dict[str, Any] | None = None,
) -> Report:
    report = Report("mcp", public_location(url), name)
    res = Results(report)
    res.set("MCP-001", *transport_outcome(url))
    session = McpSession(http, url)
    try:
        _run(session, res, report, baseline)
    except BudgetExceeded as exc:
        report.notes.append(str(exc))
        res.rest("unknown", "request budget spent before this check (raise --max-requests)")
    finally:
        try:
            session.close()
        finally:
            report.requests = http.requests
    return res.finish()


def _run(session: McpSession, res: Results, report: Report, baseline: dict[str, Any] | None) -> None:
    hs, attempts = session.handshake()
    report.facts["handshakeAttempts"] = attempts
    if hs.status is None:
        res.set("MCP-002", "fail", hs.describe())
        res.rest("unknown", "the endpoint did not answer")
        return
    res.set("MCP-002", "pass", f"HTTP {hs.status}")
    if hs.status in (401, 403):
        res.rest("unknown", f"authentication required (HTTP {hs.status}); pass a token with --bearer-env")
        report.facts["authRequired"] = True
        return
    result = hs.result
    if result is None:
        res.set("MCP-003", "fail", f"no handshake result ({hs.describe()})", attempts=attempts)
        res.rest("unknown", "no handshake result")
        return
    res.set("MCP-003", "pass", f"{attempts[-1]} answered", method=attempts[-1])
    version = session.version
    report.facts["protocolVersion"] = version
    report.facts["handshake"] = attempts[-1]
    if version in KNOWN_VERSIONS:
        res.set("MCP-004", "pass", f"protocol version {version}")
    else:
        res.set("MCP-004", "fail", f"server answered protocol version {version!r}", known=list(KNOWN_VERSIONS))
    info = result.get("serverInfo") if session.era == "initialize" else (result.get("_meta") or {}).get(META_SERVER)
    if isinstance(info, dict) and isinstance(info.get("name"), str) and info["name"].strip():
        res.set("MCP-005", "pass", f"serverInfo.name = {info['name'][:80]!r}")
        report.facts["serverInfo"] = {k: str(info.get(k))[:120] for k in ("name", "version", "title") if k in info}
    else:
        res.set("MCP-005", "fail", "serverInfo.name missing or empty")
    if session.era != "initialize":
        res.set("MCP-007", "skip", "stateless revision: no session")
    elif session.session_id is None:
        res.set("MCP-007", "skip", "the server issued no session id")
    elif all(0x21 <= ord(c) <= 0x7E for c in session.session_id):
        res.set("MCP-007", "pass", "visible ASCII only")
    else:
        res.set("MCP-007", "fail", "Mcp-Session-Id contains characters outside 0x21-0x7E")
    report.facts["sessionIssued"] = session.session_id is not None
    raw_caps = result.get("capabilities")
    caps: dict[str, Any] = raw_caps if isinstance(raw_caps, dict) else {}
    report.facts["capabilities"] = sorted(caps)

    tools, problem, pages, last = session.list_all("tools/list", "tools")
    declared = "tools" in caps
    if tools is None:
        if declared:
            res.set("MCP-008", "fail", f"tools/list gave no tool array ({last.describe() if last else 'no answer'})")
            res.set("MCP-014", "fail", "tools declared but tools/list does not answer with tools")
        else:
            res.set("MCP-008", "skip", "the server does not declare tools")
            res.set("MCP-014", "pass", "tools neither declared nor served")
        for cid in ("MCP-009", "MCP-010", "MCP-011", "MCP-012", "SEC-003", "SEC-004"):
            res.set(cid, "skip", "no tool list")
        tools = []
    else:
        res.set("MCP-008", "pass", f"{len(tools)} tool(s) in {pages} page(s)")
        if declared or not tools:
            res.set("MCP-014", "pass", "tools capability declared" if declared else "no tools")
        else:
            res.set("MCP-014", "fail", f"{len(tools)} tool(s) served without the tools capability")
        _tool_checks(res, report, tools, problem, pages, baseline)

    other: list[tuple[str, str]] = []
    for cap, method, key in (("prompts", "prompts/list", "prompts"), ("resources", "resources/list", "resources")):
        if cap not in caps:
            continue
        items, _, _, last = session.list_all(method, key)
        if items is None:
            if res.outcome("MCP-014") == "pass":
                answer = last.describe() if last else "no answer"
                res.set("MCP-014", "fail", f"{cap} declared but {method} gave no list ({answer})")
            continue
        report.facts[f"{key[:-1]}Count"] = len(items)
        other += _texts(key[:-1], items)
    text_screens(res, _texts("tool", tools) + other)

    probe = session.rpc(UNKNOWN_METHOD)
    if probe.error_code == -32601:
        res.set("MCP-013", "pass", "answered -32601 Method not found")
    elif probe.result is not None:
        res.set("MCP-013", "fail", "a method that does not exist returned a result")
    elif probe.status is None:
        res.set("MCP-013", "unknown", probe.describe())
    else:
        res.set("MCP-013", "fail", f"answered {probe.describe()} instead of -32601")

    if session.id_checks and all(session.id_checks):
        res.set("MCP-006", "pass", f"{len(session.id_checks)} response(s) checked")
    elif session.id_checks:
        res.set("MCP-006", "fail", f"{session.id_checks.count(False)} response(s) carried another id")
    else:
        res.set("MCP-006", "unknown", "no response to compare")


def _tool_checks(
    res: Results,
    report: Report,
    tools: list[Any],
    problem: str | None,
    pages: int,
    baseline: dict[str, Any] | None,
) -> None:
    objects = [t for t in tools if isinstance(t, dict)]
    names = [t.get("name") for t in objects]
    bad = [n if isinstance(n, str) else repr(n) for n in names if not (isinstance(n, str) and TOOL_NAME.fullmatch(n))]
    if bad:
        res.set("MCP-009", "fail", f"{len(bad)} name(s) outside 1-128 of A-Z a-z 0-9 _ - .", names=bad[:20])
    else:
        res.set("MCP-009", "pass", f"{len(names)} name(s) checked")
    dupes = sorted({n for n in names if isinstance(n, str) and names.count(n) > 1})
    if dupes or len(objects) != len(tools):
        res.set("MCP-010", "fail", "duplicate or malformed tool entries", duplicates=dupes)
    else:
        res.set("MCP-010", "pass", "all names unique")
    schema_bad = [
        str(t.get("name"))
        for t in objects
        if not (isinstance(t.get("inputSchema"), dict) and t["inputSchema"].get("type") == "object")
    ]
    if schema_bad:
        res.set("MCP-011", "fail", f"{len(schema_bad)} tool(s) without an object inputSchema", tools=schema_bad[:20])
    else:
        res.set("MCP-011", "pass", f"{len(objects)} schema(s) checked")
    if problem is None:
        res.set("MCP-012", "pass", f"ended after {pages} page(s)")
    elif problem == "repeated-cursor":
        res.set("MCP-012", "fail", "nextCursor repeated an earlier cursor")
    else:
        res.set("MCP-012", "unknown", f"stopped after {pages} pages")

    risk = analyse_tools(objects)
    conflicts = []
    for item in risk["actionLabels"]:
        if item["annotationConflict"]:
            counted = [
                {k: h[k] for k in ("field", "word", "basis", "fragment")} for h in item["evidence"] if h["counted"]
            ]
            conflicts.append({"tool": item["name"], "reasons": item["conflictReasons"], "evidence": counted[:5]})
    if conflicts:
        res.set(
            "SEC-003",
            "review",
            f"{len(conflicts)} tool(s): declared hints and tool text disagree (candidates, not observed actions)",
            method=risk["actionMethod"],
            conflicts=conflicts[:20],
        )
    else:
        annotated = sum(1 for t in objects if isinstance(t.get("annotations"), dict))
        res.set("SEC-003", "pass", f"no conflict among {annotated} annotated tool(s)", method=risk["actionMethod"])

    pinned = [
        {
            "name": str(t.get("name")),
            "sha256": tool_hash(t),
            "readOnlyHint": (t.get("annotations") or {}).get("readOnlyHint")
            if isinstance(t.get("annotations"), dict)
            else None,
            "labels": action_labels(t)["heuristic"],
        }
        for t in objects
    ]
    report.facts["toolCount"] = len(tools)
    report.facts["tools"] = pinned
    before = _baseline_tools(baseline, report.target, report.name)
    if before is None:
        res.set("SEC-004", "skip", "no baseline given (--baseline <earlier report>)")
        return
    now = {p["name"]: p["sha256"] for p in pinned}
    added = sorted(set(now) - set(before))
    removed = sorted(set(before) - set(now))
    changed = sorted(n for n in set(now) & set(before) if now[n] != before[n])
    if added or removed or changed:
        res.set(
            "SEC-004",
            "review",
            f"{len(changed)} changed, {len(added)} added, {len(removed)} removed since the baseline",
            changed=changed,
            added=added,
            removed=removed,
        )
    else:
        res.set("SEC-004", "pass", f"{len(now)} definition(s) identical to the baseline")
