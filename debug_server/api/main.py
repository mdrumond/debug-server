# ruff: noqa: B008
"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import Depends, FastAPI

from debug_server.api.auth import BearerTokenAuth
from debug_server.api.context import AppContext, get_app_context
from debug_server.api.middleware import AuditLoggerMiddleware
from debug_server.api.routers import auth as auth_router
from debug_server.api.routers import commands, repository, sessions
from debug_server.api.routers import debug as debug_router
from debug_server.api.routers import logs as log_router
from debug_server.api.schemas import APIMessage
from debug_server.api.streams import DebugBroker, LogManager
from debug_server.db import AuthToken, MetadataStore
from debug_server.db.session import create_engine_from_url, init_db
from debug_server.version import __version__


def create_app(context: AppContext | None = None) -> FastAPI:
    """Instantiate the FastAPI application with all routers."""

    if context is None:
        engine = create_engine_from_url()
        init_db(engine)
        context = AppContext(
            metadata_store=MetadataStore(engine),
            log_manager=LogManager(),
            debug_broker=DebugBroker(),
        )
    else:
        context.log_manager = context.log_manager or LogManager()
        context.debug_broker = context.debug_broker or DebugBroker()
    app = FastAPI(
        title="Debug Server API",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.context = context
    app.add_middleware(AuditLoggerMiddleware)

    app.include_router(repository.router)
    app.include_router(sessions.router)
    app.include_router(commands.router)
    app.include_router(debug_router.router)
    app.include_router(log_router.router)
    app.include_router(auth_router.router)

    @app.get("/healthz", response_model=APIMessage, tags=["system"])
    def healthz() -> APIMessage:
        return APIMessage(message="ok")

    @app.get("/readyz", response_model=APIMessage, tags=["system"])
    def readyz(_: AppContext = Depends(get_app_context)) -> APIMessage:
        return APIMessage(message="ready")

    @app.get("/whoami", response_model=APIMessage, tags=["system"])
    def whoami(token: AuthToken = Depends(BearerTokenAuth())) -> APIMessage:
        return APIMessage(message=token.name)

    return app


app = create_app()

__all__ = ["app", "create_app"]
