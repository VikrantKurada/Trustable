from pathlib import Path

from typer.testing import CliRunner

from trustable.cli.main import create_app

runner = CliRunner()


def test_init_scaffolds_config_and_dirs(tmp_path: Path):
    result = runner.invoke(create_app(), ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "trustable.yaml").is_file()
    assert (tmp_path / "prompts").is_dir()
    assert (tmp_path / "tests").is_dir()
    assert "my-llm-app" in (tmp_path / "trustable.yaml").read_text()


def test_init_refuses_overwrite_without_force(tmp_path: Path):
    (tmp_path / "trustable.yaml").write_text("existing")
    result = runner.invoke(create_app(), ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 1
    assert (tmp_path / "trustable.yaml").read_text() == "existing"


def test_init_force_overwrites(tmp_path: Path):
    (tmp_path / "trustable.yaml").write_text("existing")
    result = runner.invoke(create_app(), ["init", "--dir", str(tmp_path), "--force"])
    assert result.exit_code == 0
    assert "my-llm-app" in (tmp_path / "trustable.yaml").read_text()
