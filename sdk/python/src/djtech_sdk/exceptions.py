"""
Exceptions for DJ Tech Agent Runtime SDK
"""

from typing import Any, Dict, Optional


class DJTechError(Exception):
    """Base exception for DJ Tech SDK"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class APIError(DJTechError):
    """API returned an error response"""

    def __init__(
        self,
        message: str,
        status_code: int,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.status_code = status_code
        self.code = code


class AuthenticationError(APIError):
    """Authentication failed (401)"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 401, "AUTHENTICATION_ERROR", details)


class AuthorizationError(APIError):
    """Authorization failed (403)"""

    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 403, "AUTHORIZATION_ERROR", details)


class NotFoundError(APIError):
    """Resource not found (404)"""

    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 404, "NOT_FOUND", details)


class ValidationError(APIError):
    """Request validation failed (400)"""

    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, "VALIDATION_ERROR", details)


class ConflictError(APIError):
    """Resource conflict (409)"""

    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 409, "CONFLICT", details)


class RateLimitError(APIError):
    """Rate limit exceeded (429)"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, 429, "RATE_LIMIT", details)
        self.retry_after = retry_after


class ServerError(APIError):
    """Server error (5xx)"""

    def __init__(self, message: str = "Internal server error", status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, "SERVER_ERROR", details)


class TimeoutError(DJTechError):
    """Request timeout"""

    def __init__(self, message: str = "Request timed out", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class NetworkError(DJTechError):
    """Network connection error"""

    def __init__(self, message: str = "Network error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


def map_http_error(status_code: int, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> APIError:
    """Map HTTP status code to appropriate exception"""
    if status_code == 400:
        return ValidationError(message, details)
    elif status_code == 401:
        return AuthenticationError(message, details)
    elif status_code == 403:
        return AuthorizationError(message, details)
    elif status_code == 404:
        return NotFoundError(message, details)
    elif status_code == 409:
        return ConflictError(message, details)
    elif status_code == 429:
        return RateLimitError(message, details)
    elif 500 <= status_code < 600:
        return ServerError(message, status_code, details)
    else:
        return APIError(message, status_code, code, details)