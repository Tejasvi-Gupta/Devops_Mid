"""FastAPI application."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="Environment Provisioning Platform", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "Idempotency-Key"],
)
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(AppError)
async def app_error(_request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


def _validation_message(error: dict) -> tuple[str, str]:
    location = [str(part) for part in error.get("loc", ()) if part != "body"]
    field = location[-1] if location else "request"
    text = str(error.get("msg", "This value is invalid"))
    if text.startswith("Value error, "):
        text = text.removeprefix("Value error, ")
    if field == "password":
        text = "Use at least 12 characters, with at least one letter and one number."
    return field, text


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    fields = {}
    for item in exc.errors():
        field, text = _validation_message(item)
        fields.setdefault(field, text)
    message = next(iter(fields.values()), "The request is invalid")
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": message, "details": {"fields": fields}}},
    )


@app.exception_handler(Exception)
async def unexpected(_request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail), "details": {}}},
        )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Something went wrong.", "details": {}}},
    )
