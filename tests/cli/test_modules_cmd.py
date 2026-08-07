from pathlib import Path

import pytest
from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()


def test_modules_list_shows_builtins():
    result = runner.invoke(create_app(), ["modules", "list"])
    assert result.exit_code == 0
    for name in ("security", "audit", "test", "explainability", "noop"):
        assert name in result.output


def test_modules_list_marks_noop_capabilities():
    result = runner.invoke(create_app(), ["modules", "list"])
    assert "InputGuard" in result.output  # noop advertises capabilities


def test_modules_info_shows_schema_fields():
    result = runner.invoke(create_app(), ["modules", "info", "audit"])
    assert result.exit_code == 0
    assert "log_level" in result.output
    assert "sink" in result.output


def test_modules_info_unknown_exits_nonzero():
    result = runner.invoke(create_app(), ["modules", "info", "nope"])
    assert result.exit_code == 1


def test_modules_list_reflects_real_project_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = """
version: "1.0"
project: "demo"
plugins:
  - ref: "does.not:exist"
modules:
  noop:
    enabled: true
"""
    (tmp_path / "trustable.yaml").write_text(config)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(create_app(), ["modules", "list"])

    assert result.exit_code == 0
    noop_line = next(line for line in result.output.splitlines() if line.startswith("noop"))
    assert "enabled=yes" in noop_line
    assert "does.not:exist" in result.output
