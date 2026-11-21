"""The command line, the report formats, the catalogue and the shared heuristics."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from capalens_ia_check import cli
from capalens_ia_check.checks import CATALOGUE, CHECKS, for_kind
from capalens_ia_check.demo import DemoServer
from capalens_ia_check.heuristics import action_labels
from tests.conftest import DEMO_DATA, ROOT

SCHEMA = json.loads((ROOT / "schemas" / "report.schema.json").read_text(encoding="utf-8"))


def validate(document: dict[str, object]) -> None:
    jsonschema = pytest.importorskip("jsonschema")  # a dev dependency; the tool itself has none
    jsonschema.Draft202012Validator(SCHEMA).validate(document)


def run_cli(args: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = cli.main(args)
    return code, capsys.readouterr().out


def test_exit_codes_follow_fail_on(demo: DemoServer, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["mcp", demo.url("good")], capsys)[0] == 0
    assert run_cli(["mcp", demo.url("risky")], capsys)[0] == 1
    assert run_cli(["mcp", demo.url("risky"), "--fail-on", "never"], capsys)[0] == 0
    assert run_cli(["mcp", demo.url("auth")], capsys)[0] == 0  # unknown does not block by default
    assert run_cli(["mcp", demo.url("auth"), "--fail-on", "unknown"], capsys)[0] == 1


def test_bearer_from_the_environment(
    demo: DemoServer, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_TOKEN", "demo-token")
    code, out = run_cli(["mcp", demo.url("auth"), "--bearer-env", "DEMO_TOKEN", "--format", "json"], capsys)
    assert code == 0 and "demo-token" not in out
    assert {r["id"]: r["outcome"] for r in json.loads(out)["results"]}["MCP-003"] == "pass"


@pytest.mark.parametrize(
    "args",
    [
        ["mcp", "not-a-url"],
        ["openapi", "no/such/file.json"],
        ["mcp", "http://127.0.0.1:9/mcp", "--bearer-env", "CAPALENS_SURELY_UNSET"],
        ["mcp", "http://127.0.0.1:9/mcp", "--header", "no-colon-secret"],
        ["run", "no/such/targets.json"],
    ],
)
def test_usage_errors_exit_2(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(args) == 2
    assert "no-colon-secret" not in capsys.readouterr().err


def test_every_format_and_file_output(demo: DemoServer, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    outs = {k: tmp_path / f"r.{k}" for k in ("json", "md", "sarif")}
    code, text = run_cli(["mcp", demo.url("risky"), "--json-out", str(outs["json"]), "--markdown-out",
                          str(outs["md"]), "--sarif-out", str(outs["sarif"])], capsys)  # fmt: skip
    assert code == 1 and "[FAIL   ] MCP-005" in text and "[SKIP" not in text
    report = json.loads(outs["json"].read_text(encoding="utf-8"))
    validate(report)
    assert "score" not in json.dumps(report).lower().replace("no score", "")
    md = outs["md"].read_text(encoding="utf-8")
    assert "| FAIL | [MCP-005]" in md and "<details>" in md
    sarif = json.loads(outs["sarif"].read_text(encoding="utf-8"))
    run = sarif["runs"][0]
    assert sarif["version"] == "2.1.0" and run["tool"]["driver"]["name"] == "capalens-ia-check"
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert {r["ruleId"] for r in run["results"]} <= rule_ids
    levels = {r["ruleId"]: r["level"] for r in run["results"]}
    assert levels["MCP-005"] == "error" and levels["MCP-009"] == "warning" and levels["SEC-001"] == "warning"


def test_targets_file_with_relative_paths(demo: DemoServer, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "card.json").write_text((DEMO_DATA / "agent-card.json").read_text(encoding="utf-8"), encoding="utf-8")
    targets = {
        "defaults": {"timeout": 5},
        "targets": [
            {"name": "good", "kind": "mcp", "location": demo.url("good")},
            {"name": "card", "kind": "agent-card", "location": "card.json"},
        ],
    }
    path = tmp_path / "targets.json"
    path.write_text(json.dumps(targets), encoding="utf-8")
    out = tmp_path / "run.json"
    code, _ = run_cli(["run", str(path), "--json-out", str(out)], capsys)
    data = json.loads(out.read_text(encoding="utf-8"))
    validate(data)
    assert code == 0 and data["format"] == "capalens-ia-check.run/1" and len(data["reports"]) == 2
    code, _ = run_cli(["run", str(path), "--baseline", str(out), "--format", "json"], capsys)
    assert code == 0


def test_step_summary_is_written_on_github(demo: DemoServer, tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                           monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    run_cli(["mcp", demo.url("good")], capsys)
    assert "# capalens-ia-check report" in summary.read_text(encoding="utf-8")


def test_demo_runs_every_kind(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run_cli(["demo", "--format", "json"], capsys)
    data = json.loads(out[: out.rindex("}") + 1])
    assert code == 0 and [r["target"]["kind"] for r in data["reports"]] == [
        "mcp",
        "mcp",
        "openapi",
        "agent-card",
        "skill",
    ]


def test_checks_doc_is_in_sync(capsys: pytest.CaptureFixture[str]) -> None:
    _, out = run_cli(["checks", "--format", "markdown"], capsys)
    assert (ROOT / "docs" / "checks.md").read_text(encoding="utf-8") == out, (
        "run: capalens-ia-check checks --format markdown > docs/checks.md"
    )


def test_catalogue_is_consistent() -> None:
    ids = [c.id for c in CATALOGUE]
    assert len(ids) == len(set(ids)) == len(CHECKS)
    source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "capalens_ia_check").glob("*.py"))
    for cid in ids:  # every check is set somewhere: no dead catalogue entries
        assert re.search(rf'"{cid}"', source.replace(f'Check("{cid}"', "")), cid
    for kind in ("mcp", "openapi", "agent-card", "skill"):
        assert {"SEC-001", "SEC-002"} <= {c.id for c in for_kind(kind)}


@pytest.mark.parametrize(
    ("description", "conflict"),
    [
        ("Does not install, run or configure anything.", False),
        ('optional pricing:"summary" adds them to comparison-summary.', False),
        ("Adds a record to the database.", True),
        ("Deletes the repository and all branches.", True),
        ("Does not delete anything and wipes the cache.", True),
    ],
)
def test_shared_action_heuristic_is_intact(description: str, conflict: bool) -> None:
    tool = {"name": "t", "description": description, "annotations": {"readOnlyHint": True, "destructiveHint": False}}
    assert action_labels(tool)["annotationConflict"] is conflict


def test_readmes_state_the_number_of_checks() -> None:
    n = len(CATALOGUE)
    assert f"{n} checks in three layers" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"共 {n} 项" in (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
