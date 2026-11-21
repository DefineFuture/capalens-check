"""The check catalogue: one entry per check. Docs, SARIF rules and reports all read this table.

Ids are stable: a check that changes meaning gets a new id. Levels:

* ``must``      a requirement of the specification (a ``fail`` is an error);
* ``should``    a recommendation or a widely relied-on convention (a ``fail`` is a warning);
* ``heuristic`` a word-list screen whose ``review`` is a candidate for a human (never a verdict);
* ``info``      a recorded fact with no expectation attached.
"""

from __future__ import annotations

from .model import Check

MCP_SPEC = "https://modelcontextprotocol.io/specification/2025-11-25"
OAS_SPEC = "https://spec.openapis.org/oas/v3.1.0"
A2A_SPEC = "https://a2a-protocol.org/latest/specification/"
SKILLS_SPEC = "https://agentskills.io/specification"

CATALOGUE: list[Check] = [
    # ------------------------------------------------------------------ MCP (live, read-only)
    Check("MCP-001", "Endpoint uses HTTPS", "mcp", "L0", "must", f"{MCP_SPEC}/basic/transports",
          "Remote MCP traffic carries tool definitions and credentials; plain HTTP is accepted only on loopback."),
    Check("MCP-002", "Endpoint answers over HTTP", "mcp", "L0", "must", f"{MCP_SPEC}/basic/transports",
          "A network or TLS error means nothing else can be observed."),
    Check("MCP-003", "Handshake returns a JSON-RPC result", "mcp", "L1", "must", f"{MCP_SPEC}/basic/lifecycle",
          "initialize (or server/discover on 2026-07-28) must answer with a result carrying the negotiated version."),
    Check("MCP-004", "Negotiated protocol version is a published revision", "mcp", "L1", "must",
          f"{MCP_SPEC}/basic/lifecycle#version-negotiation",
          "Clients can only rely on behaviour of a revision they know; an unknown version cannot be checked."),
    Check("MCP-005", "serverInfo names the implementation", "mcp", "L1", "must", f"{MCP_SPEC}/basic/lifecycle",
          "serverInfo.name is required and identifies the server in logs and reports."),
    Check("MCP-006", "Responses echo the request id", "mcp", "L1", "must", "https://www.jsonrpc.org/specification#response_object",
          "JSON-RPC 2.0: a response carries the id of the request it answers."),
    Check("MCP-007", "Session id uses visible ASCII only", "mcp", "L1", "must", f"{MCP_SPEC}/basic/transports#session-management",
          "Mcp-Session-Id must contain only visible ASCII (0x21-0x7E)."),
    Check("MCP-008", "tools/list returns a tool array", "mcp", "L1", "must", f"{MCP_SPEC}/server/tools#listing-tools",
          "A server declaring the tools capability answers tools/list with result.tools."),
    Check("MCP-009", "Tool names follow the naming rules", "mcp", "L1", "should", f"{MCP_SPEC}/server/tools#tool-names",
          "Names should be 1-128 characters of A-Z a-z 0-9 _ - . so clients can route and display them."),
    Check("MCP-010", "Tool names are unique", "mcp", "L1", "must", f"{MCP_SPEC}/server/tools#tool-names",
          "Two tools with one name make every call ambiguous."),
    Check("MCP-011", "Tool input schemas are JSON Schema objects", "mcp", "L1", "must", f"{MCP_SPEC}/server/tools#tool",
          "inputSchema must be a JSON Schema object with type 'object'."),
    Check("MCP-012", "Pagination terminates", "mcp", "L1", "must", f"{MCP_SPEC}/server/utilities/pagination",
          "nextCursor must lead to the end of the list without repeating a cursor."),
    Check("MCP-013", "Unknown methods get JSON-RPC error -32601", "mcp", "L1", "should",
          "https://www.jsonrpc.org/specification#error_object",
          "A method the server does not implement is answered with 'Method not found', not a result."),
    Check("MCP-014", "Listed features match declared capabilities", "mcp", "L1", "must", f"{MCP_SPEC}/basic/lifecycle#capability-negotiation",
          "A server that serves tools declares the tools capability in its handshake."),
    # ------------------------------------------------------------------ OpenAPI (static)
    Check("OAS-001", "Document parses as JSON or YAML", "openapi", "L1", "must", OAS_SPEC,
          "Nothing else can be read from a document that does not parse."),
    Check("OAS-002", "OpenAPI version is 3.0.x or 3.1.x", "openapi", "L1", "must", f"{OAS_SPEC}#openapi-object",
          "The 'openapi' field names the specification version; Swagger 2.0 is out of scope."),
    Check("OAS-003", "info has title and version", "openapi", "L1", "must", f"{OAS_SPEC}#info-object",
          "info.title and info.version are required."),
    Check("OAS-004", "Document describes paths or webhooks", "openapi", "L1", "should", f"{OAS_SPEC}#openapi-object",
          "A description without operations gives an agent nothing to call."),
    Check("OAS-005", "operationIds are unique", "openapi", "L1", "must", f"{OAS_SPEC}#operation-object",
          "operationId must be unique among all operations; tools generated from it collide otherwise."),
    Check("OAS-006", "Path template parameters are declared", "openapi", "L1", "must", f"{OAS_SPEC}#path-item-object",
          "Every {name} in a path needs a parameter with in: path and required: true."),
    Check("OAS-007", "Internal $refs resolve", "openapi", "L1", "must", f"{OAS_SPEC}#reference-object",
          "A '#/...' reference that points nowhere breaks every client that follows it."),
    Check("OAS-008", "Security requirements name declared schemes", "openapi", "L1", "must", f"{OAS_SPEC}#security-requirement-object",
          "Each security requirement key must match components.securitySchemes."),
    Check("OAS-009", "Server URLs use HTTPS", "openapi", "L0", "should", f"{OAS_SPEC}#server-object",
          "Absolute server URLs should use HTTPS (loopback and relative URLs are accepted)."),
    Check("OAS-010", "OpenAPI 3.0 operations declare responses", "openapi", "L1", "must", "https://spec.openapis.org/oas/v3.0.3#operation-object",
          "In OpenAPI 3.0 every operation must have a responses object (optional in 3.1)."),
    # ------------------------------------------------------------------ A2A Agent Card (static)
    Check("A2A-001", "Agent Card parses as a JSON object", "agent-card", "L1", "must", A2A_SPEC,
          "Nothing else can be read from a card that does not parse."),
    Check("A2A-002", "Required Agent Card fields are present", "agent-card", "L1", "must", A2A_SPEC,
          "name, description, version, capabilities, default modes, skills and the interface fields are required."),
    Check("A2A-003", "Skills have id, name, description and tags; ids are unique", "agent-card", "L1", "must", A2A_SPEC,
          "Clients select skills by id and present them by name and description."),
    Check("A2A-004", "Interface URLs use HTTPS", "agent-card", "L0", "should", A2A_SPEC,
          "Agents exchange messages and credentials over these URLs (loopback accepted)."),
    Check("A2A-005", "Security requirements name declared schemes", "agent-card", "L1", "must", A2A_SPEC,
          "Each security requirement key must match securitySchemes."),
    # ------------------------------------------------------------------ Agent Skills (static)
    Check("SKILL-001", "SKILL.md has readable front matter", "skill", "L1", "must", SKILLS_SPEC,
          "A skill is a directory with SKILL.md starting with YAML front matter."),
    Check("SKILL-002", "name and description are present and within limits", "skill", "L1", "must", SKILLS_SPEC,
          "name (1-64) and description (1-1024 characters) are required."),
    Check("SKILL-003", "name format matches the directory", "skill", "L1", "must", SKILLS_SPEC,
          "Lower-case letters, digits and single hyphens, equal to the directory name."),
    Check("SKILL-004", "Only specified front matter fields are used", "skill", "L1", "should", SKILLS_SPEC,
          "Allowed: name, description, license, compatibility, metadata, allowed-tools."),
    Check("SKILL-005", "SKILL.md body stays within the recommended size", "skill", "L1", "should", SKILLS_SPEC,
          "Agents load the whole body; under 500 lines is recommended."),
    Check("SKILL-006", "Bundled executable files are listed", "skill", "L1", "info", SKILLS_SPEC,
          "Scripts ship with skills; they are listed for review and never executed by this tool."),
    # ------------------------------------------------------------------ security candidates (all kinds)
    Check("SEC-001", "No prompt-injection or exfiltration wording in descriptions", "any", "L3", "heuristic",
          "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
          "Descriptions are read by models; instruction overrides, secret paths and exfiltration URLs are candidates."),
    Check("SEC-002", "No invisible or bidirectional control characters", "any", "L3", "heuristic",
          "https://unicode.org/reports/tr36/",
          "Invisible characters can hide instructions from a human reviewer while a model still reads them."),
    Check("SEC-003", "Declared tool annotations agree with the tool text", "mcp", "L3", "heuristic",
          f"{MCP_SPEC}/server/tools#tool-annotations",
          "A tool declared read-only whose text deletes, writes or executes is a candidate for review."),
    Check("SEC-004", "Tool definitions unchanged since the baseline", "mcp", "L3", "heuristic",
          f"{MCP_SPEC}/server/tools#list-changed-notification",
          "A changed definition after approval (a 'rug pull') needs another look; needs --baseline."),
]  # fmt: skip

CHECKS: dict[str, Check] = {c.id: c for c in CATALOGUE}


def for_kind(kind: str) -> list[Check]:
    """The checks that apply to one kind of target, in catalogue order."""
    return [c for c in CATALOGUE if c.kind in (kind, "any")]
