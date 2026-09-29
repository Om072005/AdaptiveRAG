"""Local API for the local page. Run: python -m adaptiverag serve"""

from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from adaptiverag import __version__
from adaptiverag.config import models
from adaptiverag.eval.judge import JudgeFailed
from adaptiverag.llm import BudgetExceeded, RateLimited
from adaptiverag.pipeline import answer_query, judge_answer
from adaptiverag.serialize import response_from_trace
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


class QueryIn(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    mode: Literal["auto", "vector", "graph", "hybrid"] = "auto"


@app.post("/api/query")
def query(body: QueryIn) -> Any:
    """Answer one question live; the body is the QueryResponse stored on its trace."""
    try:
        result = answer_query(body.question.strip(), body.mode, source="demo")
    except (RateLimited, BudgetExceeded) as e:
        return JSONResponse(
            {"error": {"message": str(e), "fields": None}, "replay_suggested": None},
            status_code=503,
        )
    except NotImplementedError as e:
        return error(503, str(e))
    return response_from_trace(result.trace_id)


class JudgeIn(BaseModel):
    trace_id: str = Field(pattern=r"^[0-9a-f-]{36}$")


@app.post("/api/judge")
def judge(body: JudgeIn) -> Any:
    """Judge a stored answer once; later calls return the stored judgement without a model call."""
    try:
        return judge_answer(body.trace_id)
    except KeyError:
        return error(404, f"no trace {body.trace_id}")
    except (RateLimited, JudgeFailed) as e:
        return error(503, str(e))
