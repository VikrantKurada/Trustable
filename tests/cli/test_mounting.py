from pathlib import Path

from typer.testing import CliRunner

from trustable.cli.main import build_app

runner = CliRunner()

CONFIG_WITH_NOOP = 'project: x\nmodules:\n  noop:\n    enabled: true\n'


def test_enabled_command_provider_is_mounted(tmp_path: Path, monkeypatch):
    (tmp_path / "trustable.yaml").write_text(CONFIG_WITH_NOOP)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(build_app(), ["noop-ping"])
    assert result.exit_code == 0
    assert "pong" in result.output


def test_build_app_survives_missing_config(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no trustable.yaml present
    result = runner.invoke(build_app(), ["version"])
    assert result.exit_code == 0  # core commands still work
