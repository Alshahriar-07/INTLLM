"""INTLLM FastAPI application entry point."""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.router import api_router
from app.api.routes.openai import router as openai_router
from app.config.settings import get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.metrics import metrics
from app.db.session import get_database
from app.services.background.service import get_background_service
from app.services.browser.service import get_browser_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.intllm_log_level)
    logger.info(
        "starting INTLLM backend",
        extra={"intllm_extra": {"version": __version__, "env": settings.intllm_env}},
    )

    database = get_database()
    available, error = await database.ping()
    if available:
        logger.info("postgres connected")
    else:
        # Start anyway and report status honestly rather than crashing.
        logger.warning("postgres unavailable at startup", extra={"intllm_extra": {"error": error}})

    await get_background_service().start()
    try:
        yield
    finally:
        await get_background_service().stop()
        await get_browser_service().close()
        await database.dispose()
        logger.info("INTLLM backend stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="INTLLM Local API",
        version=__version__,
        description="Local-first AI runtime: memory, retrieval, tools and an OpenAI-compatible API.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - started) * 1000.0
        metrics.observe("http.request", duration)
        metrics.increment("http.request.count")
        response.headers["X-Process-Time-Ms"] = f"{duration:.2f}"
        return response

    install_exception_handlers(app)

    app.include_router(api_router, prefix=settings.intllm_api_prefix)
    app.include_router(openai_router)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, object]:
        return {
            "name": "INTLLM",
            "version": __version__,
            "api_prefix": settings.intllm_api_prefix,
            "openai_base": "/v1",
            "runtime_endpoint": settings.runtime_endpoint,
        }

    # --- Production frontend serving (packaged app) -----------------------
    # Enabled by the INTLLM.exe launcher: serves the built SPA from the root
    # with an index.html fallback so client-side routes (/chat, /models, ...)
    # never 404 on direct navigation. The catch-all is registered LAST, so
    # /api/*, /v1/*, /docs and the meta routes keep precedence. Development
    # mode (vite dev server) is unaffected.
    static_root_raw = os.environ.get("INTLLM_STATIC_ROOT", "")
    if os.environ.get("INTLLM_SERVE_STATIC") == "1" and static_root_raw:
        static_root = Path(static_root_raw)
        index_html = static_root / "index.html"
        if index_html.is_file():
            assets_dir = static_root / "assets"
            if assets_dir.is_dir():
                app.mount(
                    "/assets",
                    StaticFiles(directory=str(assets_dir)),
                    name="frontend-assets",
                )

            @app.get("/{full_path:path}", include_in_schema=False)
            async def spa(full_path: str) -> FileResponse:
                # Real file wins (favicon, icons...); everything else falls
                # back to index.html for SPA routing.
                candidate = (static_root / full_path).resolve()
                try:
                    candidate.relative_to(static_root.resolve())
                except ValueError:
                    candidate = index_html
                if candidate.is_file():
                    return FileResponse(candidate)
                return FileResponse(index_html)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.intllm_host,
        port=settings.intllm_port,
        log_level=settings.intllm_log_level.lower(),
    )


def launch() -> None:
    """Packaged-application entrypoint (INTLLM.exe)."""
    from app.launcher import main as launcher_main

    raise SystemExit(launcher_main())


if __name__ == "__main__":
    run()
