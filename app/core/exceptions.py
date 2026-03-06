from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass
class AppException(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)


class ValidationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details or {},
        )


class GenerationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="GENERATION_ERROR",
            message=message,
            status_code=500,
            details=details or {},
        )


class DeduplicationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="DEDUPLICATION_ERROR",
            message=message,
            status_code=409,
            details=details or {},
        )


class NodeValidationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="NODE_VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details or {},
        )


class NodeExecutionError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="NODE_EXECUTION_ERROR",
            message=message,
            status_code=500,
            details=details or {},
        )


class WorkflowError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="WORKFLOW_ERROR",
            message=message,
            status_code=500,
            details=details or {},
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Unexpected internal error",
                    "details": {"exception": str(exc)},
                }
            },
        )
