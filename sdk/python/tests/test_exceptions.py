"""Tests for DJ Tech SDK exceptions"""
import pytest

from djtech_sdk.exceptions import (
    DJTechError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    RateLimitError,
    ServerError,
    TimeoutError,
    NetworkError,
    map_http_error,
)


class TestDJTechError:
    def test_base_exception(self):
        error = DJTechError("Test error")
        assert str(error) == "Test error"
        assert error.details == {}

    def test_with_details(self):
        error = DJTechError("Test error", {"key": "value"})
        assert "Test error" in str(error)
        assert error.details == {"key": "value"}


class TestAPIError:
    def test_creation(self):
        error = APIError("API error", 400, "ERROR_CODE", {"detail": "info"})
        assert error.message == "API error"
        assert error.status_code == 400
        assert error.code == "ERROR_CODE"
        assert error.details == {"detail": "info"}


class TestAuthenticationError:
    def test_default_message(self):
        error = AuthenticationError()
        assert error.message == "Authentication failed"
        assert error.status_code == 401
        assert error.code == "AUTHENTICATION_ERROR"

    def test_custom_message(self):
        error = AuthenticationError("Invalid API key")
        assert error.message == "Invalid API key"


class TestAuthorizationError:
    def test_default_message(self):
        error = AuthorizationError()
        assert error.message == "Access denied"
        assert error.status_code == 403
        assert error.code == "AUTHORIZATION_ERROR"


class TestNotFoundError:
    def test_default_message(self):
        error = NotFoundError()
        assert error.message == "Resource not found"
        assert error.status_code == 404
        assert error.code == "NOT_FOUND"


class TestValidationError:
    def test_default_message(self):
        error = ValidationError()
        assert error.message == "Validation failed"
        assert error.status_code == 400
        assert error.code == "VALIDATION_ERROR"


class TestConflictError:
    def test_default_message(self):
        error = ConflictError()
        assert error.message == "Resource conflict"
        assert error.status_code == 409
        assert error.code == "CONFLICT"


class TestRateLimitError:
    def test_default_message(self):
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.code == "RATE_LIMIT"
        assert error.retry_after is None

    def test_with_retry_after(self):
        error = RateLimitError(retry_after=60)
        assert error.retry_after == 60


class TestServerError:
    def test_default(self):
        error = ServerError()
        assert error.message == "Internal server error"
        assert error.status_code == 500
        assert error.code == "SERVER_ERROR"

    def test_custom_status(self):
        error = ServerError("Service unavailable", 503)
        assert error.status_code == 503


class TestTimeoutError:
    def test_creation(self):
        error = TimeoutError("Request timed out")
        assert error.message == "Request timed out"
        assert isinstance(error, DJTechError)
        assert not isinstance(error, APIError)


class TestNetworkError:
    def test_creation(self):
        error = NetworkError("Connection refused")
        assert error.message == "Connection refused"
        assert isinstance(error, DJTechError)
        assert not isinstance(error, APIError)


class TestMapHttpError:
    def test_400_validation(self):
        error = map_http_error(400, "Bad request")
        assert isinstance(error, ValidationError)

    def test_401_auth(self):
        error = map_http_error(401, "Unauthorized")
        assert isinstance(error, AuthenticationError)

    def test_403_forbidden(self):
        error = map_http_error(403, "Forbidden")
        assert isinstance(error, AuthorizationError)

    def test_404_not_found(self):
        error = map_http_error(404, "Not found")
        assert isinstance(error, NotFoundError)

    def test_409_conflict(self):
        error = map_http_error(409, "Conflict")
        assert isinstance(error, ConflictError)

    def test_429_rate_limit(self):
        error = map_http_error(429, "Rate limited")
        assert isinstance(error, RateLimitError)

    def test_500_server(self):
        error = map_http_error(500, "Internal error")
        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_503_server(self):
        error = map_http_error(503, "Unavailable")
        assert isinstance(error, ServerError)
        assert error.status_code == 503

    def test_unknown_status(self):
        error = map_http_error(418, "I'm a teapot")
        assert isinstance(error, APIError)
        assert not isinstance(error, ValidationError)
        assert error.status_code == 418


if __name__ == "__main__":
    pytest.main([__file__, "-v"])