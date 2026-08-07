from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class PluginRef(BaseModel):
    ref: str


class RawModuleConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    enabled: bool = False


class TrustableConfig(BaseModel):
    version: str = "1.0"
    project: str
    plugins: list[PluginRef] = []
    modules: dict[str, RawModuleConfig] = {}


class ModuleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False


class SecurityConfig(ModuleConfig):
    pii_masking: list[str] = []
    block_injections: bool = True


class AuditConfig(ModuleConfig):
    sink: str = "local"
    log_level: Literal["bronze", "silver", "gold"] = "silver"


class TestConfig(ModuleConfig):
    evaluator_model: str | None = None
    golden_dataset: str | None = None


class ExplainabilityConfig(ModuleConfig):
    capture_rag_context: bool = False
