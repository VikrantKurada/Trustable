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
