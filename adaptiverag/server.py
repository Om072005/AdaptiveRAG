"""Local API for the local page. Run: python -m adaptiverag serve"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from adaptiverag import __version__
from adaptiverag.config import models
from adaptiverag.stores.db import conn

LOCAL_PAGE_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # vite dev server

app = FastAPI(title="AdaptiveRAG", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=LOCAL_PAGE_ORIGINS, allow_methods=["GET", "POST"])


def error(status: int, message: str, fields: dict[str, str] | None = None) -> JSONResponse:
    """The contract error shape: { error: { message, fields } }."""
    return JSONResponse({"error": {"message": message, "fields": fields}}, status_code=status)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = {".".join(str(p) for p in e["loc"][1:]) or "body": e["msg"] for e in exc.errors()}
    return error(400, "Invalid request", fields)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return error(exc.status_code, str(exc.detail))


def db_ok() -> bool:
    try:
        with conn() as c:
            return c.execute("select 1").fetchone() == (1,)
    except Exception:
        return False


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "db": db_ok(),
        "version": __version__,
        "models": {role: spec.model for role, spec in models().items()},
    }
