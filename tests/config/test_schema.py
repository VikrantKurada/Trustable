import pytest
from pydantic import ValidationError

from trustable.config.schema import (
    AuditConfig,
    RawModuleConfig,
    SecurityConfig,
    TrustableConfig,
)


def test_envelope_requires_project():
    with pytest.raises(ValidationError):
        TrustableConfig()  # type: ignore[call-arg]


def test_raw_module_allows_extra_keys():
    raw = RawModuleConfig(enabled=True, pii_masking=["EMAIL"])  # type: ignore[call-arg]
    assert raw.enabled is True


def test_module_config_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        SecurityConfig(enabled=True, bogus=1)  # type: ignore[call-arg]


def test_audit_log_level_is_constrained():
    assert AuditConfig(enabled=True, log_level="silver").log_level == "silver"
    with pytest.raises(ValidationError):
        AuditConfig(enabled=True, log_level="platinum")  # type: ignore[arg-type]
