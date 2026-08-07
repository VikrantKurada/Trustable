from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()


def test_version_command_prints_version():
    result = runner.invoke(create_app(), ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_version_flag_prints_version():
    result = runner.invoke(create_app(), ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
