"""Application errors and response helpers."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def unauthorized(message: str = "Authentication is required") -> AppError:
    return AppError("unauthorized", message, 401)


def forbidden(message: str = "You do not have access to this resource") -> AppError:
    return AppError("forbidden", message, 403)


def not_found(message: str = "Resource not found") -> AppError:
    return AppError("not_found", message, 404)


def conflict(message: str, details: dict | None = None) -> AppError:
    return AppError("conflict", message, 409, details)


def invalid_state(message: str) -> AppError:
    return AppError("invalid_state", message, 409)


def validation_error(message: str, details: dict | None = None) -> AppError:
    return AppError("validation_error", message, 422, details)


def rate_limited(message: str = "Too many requests. Try again later.") -> AppError:
    return AppError("rate_limited", message, 429)
