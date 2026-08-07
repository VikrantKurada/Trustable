import pytest

from trustable.config.schema import ModuleConfig
from trustable.plugins.module import ModuleSpec
from trustable.plugins.registry import DuplicateModuleError, ModuleRegistry


def _spec(name: str, priority: int = 100) -> ModuleSpec:
    return ModuleSpec(
        name=name, factory=lambda c: object(), config_model=ModuleConfig, priority=priority
    )


def test_register_and_get():
    reg = ModuleRegistry()
    reg.register(_spec("audit"), source="builtin")
    assert "audit" in reg
    assert reg.get("audit").name == "audit"
    assert reg.source_of("audit") == "builtin"
    assert reg.names() == ["audit"]


def test_duplicate_registration_raises():
    reg = ModuleRegistry()
    reg.register(_spec("audit"))
    with pytest.raises(DuplicateModuleError):
        reg.register(_spec("audit"))


def test_get_unknown_raises_keyerror():
    reg = ModuleRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")
