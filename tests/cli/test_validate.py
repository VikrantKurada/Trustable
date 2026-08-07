from pathlib import Path

from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()

PRD_YAML = """
version: "1.0"
project: "my-llm-app"
modules:
  security:
    enabled: true
    pii_masking: ["EMAIL", "API_KEYS"]
    block_injections: true
  audit:
    enabled: true
    sink: "databricks"
    log_level: "silver"
"""


def test_validate_accepts_prd_yaml(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text(PRD_YAML)
    result = runner.invoke(create_app(), ["validate", str(p)])
    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_validate_rejects_bad_log_level(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text('project: x\nmodules:\n  audit:\n    enabled: true\n    log_level: platinum\n')
    result = runner.invoke(create_app(), ["validate", str(p)])
    assert result.exit_code == 1
    assert "audit" in result.output


def test_validate_missing_file(tmp_path: Path):
    result = runner.invoke(create_app(), ["validate", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 1
