from __future__ import annotations

from pydantic import ValidationError


class ConfigError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigNotFoundError(ConfigError):
    pass


class ConfigParseError(ConfigError):
    pass


class ConfigValidationError(ConfigError):
    pass


def format_validation_error(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(root)"
        lines.append(f"  - {loc}: {err['msg']}")
    return "\n".join(lines)
