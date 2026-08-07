from pathlib import Path

from trustable.config.loader import load_config
from trustable.plugins.registry import ModuleRegistry

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


def test_load_config_full_flow(tmp_path: Path):
    p = tmp_path / "trustable.yaml"
    p.write_text(PRD_YAML)
    loaded = load_config(p, ModuleRegistry())
    assert loaded.config.project == "my-llm-app"
    assert loaded.module_configs["security"].enabled is True
    assert loaded.discovery_errors == []
