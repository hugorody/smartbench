"""Service-layer exceptions."""

from __future__ import annotations


class ServiceError(Exception):
    """Base service exception."""


class NotFoundError(ServiceError):
    """Raised when a requested domain object does not exist."""


class ValidationError(ServiceError):
    """Raised for domain validation failures."""


class PermissionDeniedError(ServiceError):
    """Raised when actor lacks permission for operation."""
