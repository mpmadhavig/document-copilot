"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.chat import router as chat_router
from app.assistant.runtime import create_agent_runtime
from app.auth.dependencies import CurrentUser
from app.config import settings
from app.observability import configure_logging, new_error_reference

configure_logging(settings.backend_log_path, settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    runtime = create_agent_runtime()
    app.state.agent_runtime = runtime
    try:
        yield
    finally:
        await runtime.openai_client.close()


app = FastAPI(title="Document Copilot", lifespan=lifespan)


@app.middleware("http")
async def log_unhandled_request_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as error:
        reference = new_error_reference()
        logger.exception(
            "unhandled_request_error",
            error_reference=reference,
            error_type=type(error).__name__,
            method=request.method,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "The request could not be completed.",
                "error_reference": reference,
            },
            headers={"X-Error-Reference": reference},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(current_user: CurrentUser) -> dict[str, str | None]:
    """Return the identity verified from the request's Supabase access token."""
    return {"id": str(current_user.id), "email": current_user.email}
