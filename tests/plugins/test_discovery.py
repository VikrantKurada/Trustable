from pathlib import Path

from trustable.config.schema import PluginRef, TrustableConfig
from trustable.plugins.discovery import discover_modules
from trustable.plugins.registry import ModuleRegistry

_PLUGIN_SRC = """
from trustable.plugins.module import ModuleSpec
from trustable.config.schema import ModuleConfig


def provider():
    return ModuleSpec("custom", lambda c: object(), ModuleConfig, 200)
"""


def test_discovers_builtins():
    reg = ModuleRegistry()
    errors = discover_modules(TrustableConfig(project="x"), reg)
    assert errors == []
    assert "security" in reg and "noop" in reg


def test_discovers_config_plugin_ref(tmp_path: Path, monkeypatch):
    (tmp_path / "myplugin.py").write_text(_PLUGIN_SRC)
    monkeypatch.syspath_prepend(str(tmp_path))
    reg = ModuleRegistry()
    cfg = TrustableConfig(project="x", plugins=[PluginRef(ref="myplugin:provider")])
    errors = discover_modules(cfg, reg)
    assert errors == []
    assert "custom" in reg
    assert reg.source_of("custom") == "config"


def test_broken_plugin_ref_becomes_error_row():
    reg = ModuleRegistry()
    cfg = TrustableConfig(project="x", plugins=[PluginRef(ref="does.not:exist")])
    errors = discover_modules(cfg, reg)
    assert len(errors) == 1
    assert errors[0].source == "config"
    assert "does.not:exist" in errors[0].ref
