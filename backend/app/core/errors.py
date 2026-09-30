"""Consistent API error contract.

Clients can distinguish validation / authentication / permission / unavailable /
timeout / not-found / internal errors without ever seeing a stack trace.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"


_STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.AUTHENTICATION_ERROR: 401,
    ErrorCode.PERMISSION_ERROR: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL_ERROR: 500,
}


class IntllmError(Exception):
    """Base class for all INTLLM domain errors."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        else:
            self.status_code = _STATUS_BY_CODE.get(self.code, 500)
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        error: dict[str, Any] = {"message": self.message, "type": self.code.value}
        if self.details:
            error["details"] = self.details
        return {"error": error}


class ValidationError(IntllmError):
    code = ErrorCode.VALIDATION_ERROR


class AuthenticationError(IntllmError):
    code = ErrorCode.AUTHENTICATION_ERROR


class PermissionDeniedError(IntllmError):
    code = ErrorCode.PERMISSION_ERROR


class NotFoundError(IntllmError):
    code = ErrorCode.NOT_FOUND


class ConflictError(IntllmError):
    code = ErrorCode.CONFLICT


class ServiceUnavailableError(IntllmError):
    code = ErrorCode.SERVICE_UNAVAILABLE


class TimeoutError_(IntllmError):
    code = ErrorCode.TIMEOUT


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IntllmError)
    async def _intllm_error(_: Request, exc: IntllmError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("request failed", extra={"intllm_extra": {"error": exc.code.value}})
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": "Request validation failed",
                    "type": ErrorCode.VALIDATION_ERROR.value,
                    "details": {"issues": exc.errors()},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: ErrorCode.AUTHENTICATION_ERROR,
            403: ErrorCode.PERMISSION_ERROR,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            503: ErrorCode.SERVICE_UNAVAILABLE,
            504: ErrorCode.TIMEOUT,
        }.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": str(exc.detail), "type": code.value}},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        # Log the real exception; never leak it to the client.
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": ErrorCode.INTERNAL_ERROR.value,
                }
            },
        )
