from dataclasses import dataclass


@dataclass(slots=True)
class DomainError(Exception):
    """Base class for expected application-domain failures."""

    message: str
    code: str = "domain_error"

    def __str__(self) -> str:
        return self.message


class ConfigurationError(DomainError):
    """Raised when required application configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="configuration_error")


class ExternalServiceError(DomainError):
    """Raised when an external dependency fails safely."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="external_service_error")
