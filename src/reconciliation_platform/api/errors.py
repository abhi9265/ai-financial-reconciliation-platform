"""Consistent error responses for the public API."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _error(request: Request, code: str, message: str, status: int, details=None) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request.headers.get("X-Request-ID"),
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


async def _http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "request failed"
    return _error(request, "HTTP_ERROR", detail, exc.status_code)


async def _validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(request, "VALIDATION_ERROR", "request validation failed", 422, exc.errors())


def install_api_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception)
    app.add_exception_handler(RequestValidationError, _validation_exception)
