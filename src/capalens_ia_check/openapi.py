"""Static checks of an OpenAPI 3.0 / 3.1 document (JSON, or YAML with the optional ``yaml`` extra).

The document is read, never executed or called: no request is sent to the servers it describes, and external
``$ref``s are listed, not fetched.
"""

from __future__ import annotations

import re
from typing import Any

from .model import Report, arr, obj
from .net import HttpClient, is_loopback, load_json_bytes, public_location
from .results import Results
from .screens import text_screens
from .sources import is_url, read

METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
_TEMPLATE = re.compile(r"\{([^{}/]+)\}")


def parse(data: bytes) -> tuple[Any, str | None]:
    """(document, problem). JSON first; YAML when the text is not JSON and PyYAML is installed."""
    text = data.decode("utf-8-sig", "replace").lstrip()
    if text.startswith("{"):
        try:
            return load_json_bytes(data), None
        except (ValueError, UnicodeDecodeError) as exc:
            return None, f"invalid JSON: {exc}"
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return None, "YAML needs the optional extra: pip install 'capalens-ia-check[yaml]'"
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as exc:
        return None, f"invalid YAML: {str(exc)[:200]}"


def _pointer(doc: Any, ref: str) -> bool:
    """Does the internal reference ``#/a/b`` point at something?"""
    node = doc
    for raw in ref[2:].split("/") if ref.startswith("#/") else []:
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and key in node:
            node = node[key]
        elif isinstance(node, list) and key.isdigit() and int(key) < len(node):
            node = node[int(key)]
        else:
            return False
    return ref == "#" or ref.startswith("#/")


def _refs(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            out.append(ref)
        for value in node.values():
            _refs(value, out)
    elif isinstance(node, list):
        for value in node:
            _refs(value, out)


def _resolve(doc: dict[str, Any], node: Any) -> Any:
    """One level of an internal $ref (for parameters); anything else as is."""
    if isinstance(node, dict) and isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/"):
        target: Any = doc
        for raw in node["$ref"][2:].split("/"):
            key = raw.replace("~1", "/").replace("~0", "~")
            target = target.get(key) if isinstance(target, dict) else None
        return target
    return node


def check(location: str, http: HttpClient | None = None, *, name: str | None = None) -> Report:
    report = Report("openapi", public_location(location) if is_url(location) else location, name)
    res = Results(report)
    data, problem = read(location, http)
    if http is not None:
        report.requests = http.requests
    if data is None:
        res.set("OAS-001", "unknown", problem or "unreadable")
        res.rest("unknown", "the document could not be read")
        return res.finish()
    doc, problem = parse(data)
    if problem:
        res.set("OAS-001", "unknown" if "optional extra" in problem else "fail", problem)
        res.rest("unknown", "the document could not be parsed")
        return res.finish()
    if not isinstance(doc, dict):
        res.set("OAS-001", "fail", "the document is not an object")
        res.rest("unknown", "the document is not an object")
        return res.finish()
    res.set("OAS-001", "pass", "parsed")
    version = doc.get("openapi")
    if isinstance(version, str) and re.fullmatch(r"3\.[01]\.\d+(-.+)?", version):
        res.set("OAS-002", "pass", f"openapi {version}")
    else:
        found = f"swagger {doc.get('swagger')}" if "swagger" in doc else f"openapi {version!r}"
        res.set("OAS-002", "fail", f"{found}: only OpenAPI 3.0.x and 3.1.x are checked")
        res.rest("skip", "not an OpenAPI 3.0/3.1 document")
        return res.finish()
    v30 = version.startswith("3.0")
    info = obj(doc.get("info"))
    missing = [k for k in ("title", "version") if not (isinstance(info.get(k), str) and info[k].strip())]
    if missing:
        res.set("OAS-003", "fail", f"info lacks {', '.join(missing)}")
    else:
        res.set("OAS-003", "pass", f"{info['title'][:80]!r} version {info['version'][:40]!r}")

    paths = obj(doc.get("paths"))
    operations: list[tuple[str, str, dict[str, Any], list[Any]]] = []
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        shared = arr(item.get("parameters"))
        for method in METHODS:
            op = item.get(method)
            if isinstance(op, dict):
                operations.append((str(path), method, op, shared))
    webhooks = doc.get("webhooks")
    if operations or (isinstance(webhooks, dict) and webhooks):
        res.set("OAS-004", "pass", f"{len(operations)} operation(s) in {len(paths)} path(s)")
    else:
        res.set("OAS-004", "fail", "no operations and no webhooks")

    ids = [str(op["operationId"]) for _, _, op, _ in operations if isinstance(op.get("operationId"), str)]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        res.set("OAS-005", "fail", f"{len(dupes)} duplicate operationId(s)", duplicates=dupes[:20])
    else:
        res.set("OAS-005", "pass", f"{len(ids)} operationId(s), {len(operations) - len(ids)} operation(s) without one")

    undeclared: list[str] = []
    for path, method, op, shared in operations:
        params = [_resolve(doc, p) for p in shared + arr(op.get("parameters"))]
        in_path = {p.get("name"): p for p in params if isinstance(p, dict) and p.get("in") == "path"}
        for template in _TEMPLATE.findall(path):
            p = in_path.get(template)
            if p is None:
                undeclared.append(f"{method.upper()} {path}: {{{template}}} not declared")
            elif p.get("required") is not True:
                undeclared.append(f"{method.upper()} {path}: {{{template}}} not required: true")
    if undeclared:
        res.set("OAS-006", "fail", f"{len(undeclared)} path parameter problem(s)", problems=undeclared[:20])
    else:
        res.set("OAS-006", "pass", "every path template parameter declared")

    refs: list[str] = []
    _refs(doc, refs)
    internal = [r for r in refs if r.startswith("#")]
    broken = sorted({r for r in internal if not _pointer(doc, r)})
    external = sorted({r for r in refs if not r.startswith("#")})
    if broken:
        res.set("OAS-007", "fail", f"{len(broken)} internal $ref(s) point nowhere", broken=broken[:20])
    else:
        res.set("OAS-007", "pass", f"{len(internal)} internal $ref(s) resolve", external=external[:20])

    scheme_names = set(obj(obj(doc.get("components")).get("securitySchemes")))
    requirements: list[Any] = list(arr(doc.get("security")))
    for _, _, op, _ in operations:
        requirements += arr(op.get("security"))
    unknown = sorted({k for req in requirements if isinstance(req, dict) for k in req if k not in scheme_names})
    if not requirements:
        res.set("OAS-008", "skip", "no security requirements declared")
    elif unknown:
        res.set("OAS-008", "fail", f"undeclared scheme(s): {', '.join(unknown)}", undeclared=unknown)
    else:
        res.set("OAS-008", "pass", f"{len(requirements)} requirement(s) name declared schemes")

    servers = [str(s["url"]) for s in arr(doc.get("servers")) if isinstance(s, dict) and isinstance(s.get("url"), str)]
    insecure = [u for u in servers if u.lower().startswith("http://") and "{" not in u and not is_loopback(u)]
    if not servers:
        res.set("OAS-009", "skip", "no servers listed")
    elif insecure:
        res.set("OAS-009", "fail", f"{len(insecure)} server URL(s) use plain HTTP", servers=insecure[:10])
    else:
        res.set("OAS-009", "pass", f"{len(servers)} server URL(s)")

    if not v30:
        res.set("OAS-010", "skip", "responses are optional in OpenAPI 3.1")
    else:
        lacking = [
            f"{m.upper()} {p}"
            for p, m, op, _ in operations
            if not (isinstance(op.get("responses"), dict) and op["responses"])
        ]
        if lacking:
            res.set("OAS-010", "fail", f"{len(lacking)} operation(s) without responses", operations=lacking[:20])
        else:
            res.set("OAS-010", "pass", f"{len(operations)} operation(s) declare responses")

    units: list[tuple[str, str]] = [
        (f"info.{k}", info[k]) for k in ("title", "description") if isinstance(info.get(k), str)
    ]
    for path, method, op, _ in operations:
        for key in ("summary", "description"):
            if isinstance(op.get(key), str):
                units.append((f"{method.upper()} {path}.{key}", op[key]))
        for p in arr(op.get("parameters")):
            if isinstance(p, dict) and isinstance(p.get("description"), str):
                units.append((f"{method.upper()} {path}.parameters.{p.get('name')}", p["description"]))
    text_screens(res, units)
    report.facts.update(
        openapi=version,
        title=info.get("title"),
        apiVersion=info.get("version"),
        pathCount=len(paths),
        operationCount=len(operations),
        securitySchemes=sorted(scheme_names),
        externalRefs=len(external),
    )
    return res.finish()
