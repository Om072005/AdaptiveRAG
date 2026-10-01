"""Local API for the local page. Run: python -m adaptiverag serve"""

import asyncio
import json
import logging
import os
import queue
import threading
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from adaptiverag import __version__
from adaptiverag.config import models
from adaptiverag.eval.judge import JudgeFailed
from adaptiverag.llm import BudgetExceeded, ProviderError, RateLimited
from adaptiverag.pipeline import answer_query, judge_answer
from adaptiverag.serialize import response_from_trace
from adaptiverag.stores.db import conn
from adaptiverag.telemetry.trace import Listener, ListenerStop

LOCAL_PAGE_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # vite dev server
log = logging.getLogger(__name__)
# demo page sets this so each live question also prints its steps in the API's terminal
SHOW_STEPS = os.environ.get("ADAPTIVERAG_SHOW_STEPS") == "1"

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


def terminal() -> Listener | None:
    """A step printer for the API's own terminal when SHOW_STEPS is on."""
    if not SHOW_STEPS:
        return None
    from adaptiverag.demo.show import LivePrinter

    return LivePrinter()


POLL_S = 0.5  # how often a waiting stream checks that the page is still there


def run_live(
    body: QueryIn, events: "queue.Queue[dict[str, Any] | None]", gone: threading.Event
) -> None:
    """The worker behind one stream: answer, then report done or error. Stops at the next step
    or streamed piece once the page has gone, so a reload does not leave a model call running."""
    printer = terminal()

    def hear(event: dict[str, Any]) -> None:
        if gone.is_set():
            raise ListenerStop("the page closed the stream")
        events.put(event)
        if printer is not None:
            printer(event)

    try:
        result = answer_query(body.question.strip(), body.mode, source="demo", listener=hear)
        events.put({"type": "done", "response": response_from_trace(result.trace_id)})
    except ListenerStop:
        log.info("live query stopped: the page closed the stream")
    except (RateLimited, BudgetExceeded, NotImplementedError) as e:
        events.put({"type": "error", "message": str(e)})
    except ProviderError:
        log.exception("live query refused by the model server")
        events.put(
            {"type": "error", "message": "the model server refused the request, see the API log"}
        )
    except Exception:
        log.exception("live query failed")
        events.put({"type": "error", "message": "the query failed, see the API log"})
    finally:
        events.put(None)


@app.post("/api/query/stream")
def query_stream(body: QueryIn, request: Request) -> StreamingResponse:
    """Answer one question live and stream it as JSON lines while it runs: one line per step as
    it ends ({type: step}), the model's reasoning and answer as they arrive ({type: delta}), then
    {type: done, response} with the same body /api/query returns, or {type: error, message}."""
    events: queue.Queue[dict[str, Any] | None] = queue.Queue()
    gone = threading.Event()

    async def lines() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    event = await asyncio.to_thread(events.get, True, POLL_S)
                except queue.Empty:
                    if await request.is_disconnected():
                        return
                    continue
                if event is None:
                    return
                yield json.dumps(event, default=str) + "\n"
        finally:
            gone.set()  # ends the worker at its next step if the page left early

    threading.Thread(target=run_live, args=(body, events, gone), daemon=True).start()
    return StreamingResponse(lines(), media_type="application/x-ndjson")


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
