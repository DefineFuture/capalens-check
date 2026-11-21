"""Command line: ``capalens-check <kind> <target>``, ``run <targets.json>``, ``demo`` and ``checks``.

Exit codes: 0 nothing at or above ``--fail-on``; 1 something is; 2 usage or input error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from . import __version__, agent_card, mcp, openapi, skill
from .checks import CATALOGUE
from .model import Report, obj
from .net import HttpClient
from .render import render
from .sources import is_url

KINDS = ("mcp", "openapi", "agent-card", "skill")
FAIL_ON = {"fail": ("fail",), "review": ("fail", "review"), "unknown": ("fail", "review", "unknown"), "never": ()}


class UsageError(Exception):
    pass


def _headers(args: argparse.Namespace) -> dict[str, str]:
    headers: dict[str, str] = {}
    for raw in args.header or []:
        key, sep, value = raw.partition(":")
        if not sep or not key.strip():
            raise UsageError("--header needs 'Name: value' (the value is not shown here)")
        headers[key.strip()] = value.strip()
    if args.bearer_env:
        token = os.environ.get(args.bearer_env)
        if not token:
            raise UsageError(f"environment variable {args.bearer_env} is not set")
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _client(timeout: float, max_requests: int, headers: dict[str, str] | None = None) -> HttpClient:
    return HttpClient(timeout=timeout, max_requests=max_requests, headers=headers)


def _load_json(path: str, what: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise UsageError(f"{what} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise UsageError(f"{what} {path}: not a JSON object")
    return value


def check_one(
    kind: str,
    location: str,
    *,
    name: str | None = None,
    timeout: float = 15.0,
    max_requests: int = 25,
    headers: dict[str, str] | None = None,
    baseline: dict[str, Any] | None = None,
) -> Report:
    if kind not in KINDS:
        raise UsageError(f"unknown kind {kind!r} (one of {', '.join(KINDS)})")
    if kind == "mcp":
        if not is_url(location):
            raise UsageError("an MCP target is an http(s) URL")
        return mcp.check(location, _client(timeout, max_requests, headers), name=name, baseline=baseline)
    if not is_url(location) and not Path(location).exists():
        raise UsageError(f"no such file or directory: {location}")
    if kind == "skill":
        if is_url(location):
            raise UsageError("a skill is a local directory")
        return skill.check(location, name=name)
    client = _client(timeout, max_requests, headers) if is_url(location) else None
    if kind == "openapi":
        return openapi.check(location, client, name=name)
    return agent_card.check(location, client, name=name)


def _display_path(path: Path) -> str:
    """Relative to the working directory when inside it (reports and SARIF then carry repository paths)."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(resolved)


def run_targets(path: str, baseline: dict[str, Any] | None, timeout: float, max_requests: int) -> list[Report]:
    """Every target of a targets file. Credentials come from environment variables named in the file."""
    spec = _load_json(path, "targets file")
    targets = spec.get("targets")
    if not isinstance(targets, list) or not targets:
        raise UsageError(f"targets file {path}: 'targets' must be a non-empty list")
    defaults = obj(spec.get("defaults"))
    base = Path(path).resolve().parent
    reports = []
    for idx, t in enumerate(targets):
        if not isinstance(t, dict) or not isinstance(t.get("kind"), str) or not isinstance(t.get("location"), str):
            raise UsageError(f"targets[{idx}]: needs 'kind' and 'location'")
        location = t["location"] if is_url(t["location"]) else _display_path(base / t["location"])
        headers: dict[str, str] = {}
        if isinstance(t.get("bearerEnv"), str):
            token = os.environ.get(t["bearerEnv"])
            if not token:
                raise UsageError(f"targets[{idx}]: environment variable {t['bearerEnv']} is not set")
            headers["Authorization"] = f"Bearer {token}"
        for header, var in (t.get("headersEnv") or {}).items() if isinstance(t.get("headersEnv"), dict) else ():
            if not os.environ.get(str(var)):
                raise UsageError(f"targets[{idx}]: environment variable {var} is not set")
            headers[str(header)] = os.environ[str(var)]
        reports.append(
            check_one(
                t["kind"],
                location,
                name=t.get("name") if isinstance(t.get("name"), str) else None,
                timeout=float(t.get("timeout", defaults.get("timeout", timeout))),
                max_requests=int(t.get("maxRequests", defaults.get("maxRequests", max_requests))),
                headers=headers,
                baseline=baseline,
            )
        )
    return reports


def demo() -> list[Report]:
    from .demo import DemoServer

    data = resources.files("capalens_check").joinpath("data/demo")
    reports = []
    with DemoServer() as server, resources.as_file(data) as folder:
        reports.append(check_one("mcp", server.url("good"), name="demo MCP server (well-behaved)"))
        reports.append(check_one("mcp", server.url("risky"), name="demo MCP server (risky on purpose)"))
        reports.append(check_one("openapi", str(folder / "openapi.json"), name="demo OpenAPI document"))
        reports.append(check_one("agent-card", str(folder / "agent-card.json"), name="demo A2A Agent Card"))
        reports.append(check_one("skill", str(folder / "weather-report"), name="demo Agent Skill"))
    return reports


def _catalogue(fmt: str) -> str:
    if fmt == "json":
        return json.dumps([c.to_json() for c in CATALOGUE], indent=2) + "\n"
    if fmt == "markdown":
        lines = [
            "# Checks",
            "",
            "Generated by `capalens-check checks --format markdown`; do not edit by hand.",
            "",
            "Levels: **must** (a requirement; a fail is an error), **should** (a recommendation; a fail is a warning),",
            "**heuristic** (a word-list screen; `review` is a candidate for a human, never a verdict),",
            "**info** (a fact).",
            "",
        ]
        for kind in (*KINDS, "any"):
            items = [c for c in CATALOGUE if c.kind == kind]
            title = {"any": "Security candidates (every kind)"}.get(kind, f"`{kind}`")
            lines += [f"## {title}", "", "| Id | Check | Layer | Level | Why |", "| --- | --- | --- | --- | --- |"]
            lines += [f"| [{c.id}]({c.reference}) | {c.title} | {c.layer} | {c.level} | {c.rationale} |" for c in items]
            lines.append("")
        return "\n".join(lines)
    return "\n".join(f"{c.id:<9} {c.kind:<10} {c.layer} {c.level:<9} {c.title}" for c in CATALOGUE) + "\n"


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    out = common.add_argument_group("output")
    out.add_argument("--format", choices=("text", "json", "markdown", "sarif"), default="text", help="printed format")
    out.add_argument("--json-out", metavar="FILE", help="also write the JSON report here")
    out.add_argument("--markdown-out", metavar="FILE", help="also write a Markdown report here")
    out.add_argument("--sarif-out", metavar="FILE", help="also write SARIF 2.1.0 here")
    out.add_argument("--fail-on", choices=tuple(FAIL_ON), default="fail",
                     help="exit 1 when any result is at or above this outcome (default: fail)")  # fmt: skip
    out.add_argument("-v", "--verbose", action="store_true", help="show skipped checks and evidence")
    net = argparse.ArgumentParser(add_help=False)
    g = net.add_argument_group("network (URLs only)")
    g.add_argument("--timeout", type=float, default=15.0, help="seconds per request (default 15)")
    g.add_argument("--max-requests", type=int, default=25, help="request budget per target (default 25)")
    g.add_argument("--bearer-env", metavar="VAR", help="send 'Authorization: Bearer $VAR' (the value is never printed)")
    g.add_argument("--header", action="append", metavar="'NAME: VALUE'", help="extra request header (repeatable)")

    p = argparse.ArgumentParser(
        prog="capalens-check",
        description="Read-only checks for MCP servers, OpenAPI documents, A2A Agent Cards and Agent Skills. "
        "Evidence for every result; no scores.",
    )
    p.add_argument("--version", action="version", version=f"capalens-check {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("mcp", parents=[common, net], help="check a remote MCP server (Streamable HTTP URL)")
    m.add_argument("url")
    m.add_argument("--baseline", metavar="REPORT", help="an earlier JSON report: flag changed tool definitions")
    for kind, what in (("openapi", "an OpenAPI 3.x document"), ("agent-card", "an A2A Agent Card")):
        s = sub.add_parser(kind, parents=[common, net], help=f"check {what} (file or URL)")
        s.add_argument("location")
    s = sub.add_parser("skill", parents=[common], help="check an Agent Skill directory (with SKILL.md)")
    s.add_argument("location")
    r = sub.add_parser("run", parents=[common, net], help="check every target listed in a targets file")
    r.add_argument("targets")
    r.add_argument("--baseline", metavar="REPORT", help="an earlier JSON report of the same targets")
    sub.add_parser("demo", parents=[common], help="start a local demo server and check it and the bundled examples")
    c = sub.add_parser("checks", help="list every check")
    c.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    return p


def _write(path: str | None, content: str) -> None:
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.command == "checks":
        sys.stdout.write(_catalogue(args.format))
        return 0
    try:
        baseline = _load_json(args.baseline, "baseline") if getattr(args, "baseline", None) else None
        if args.command == "demo":
            reports = demo()
        elif args.command == "run":
            reports = run_targets(args.targets, baseline, args.timeout, args.max_requests)
        else:
            location = args.url if args.command == "mcp" else args.location
            headers = _headers(args) if args.command != "skill" else None
            reports = [
                check_one(
                    args.command,
                    location,
                    timeout=getattr(args, "timeout", 15.0),
                    max_requests=getattr(args, "max_requests", 25),
                    headers=headers,
                    baseline=baseline,
                )
            ]
    except UsageError as exc:
        sys.stderr.write(f"capalens-check: {exc}\n")
        return 2
    sys.stdout.write(render(reports, args.format, verbose=args.verbose))
    _write(args.json_out, render(reports, "json"))
    _write(args.markdown_out, render(reports, "markdown"))
    _write(args.sarif_out, render(reports, "sarif"))
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file and os.environ.get("CAPALENS_STEP_SUMMARY", "1") == "1":
        with open(summary_file, "a", encoding="utf-8") as fh:
            fh.write(render(reports, "markdown"))
    if args.command == "demo":
        sys.stdout.write("The demo's 'risky' server and the OpenAPI path parameter fail on purpose.\n")
        return 0
    blocking = FAIL_ON[args.fail_on]
    return 1 if any(r.outcome in blocking for rep in reports for r in rep.results) else 0
