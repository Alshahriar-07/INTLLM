"""INTLLM FastAPI application entry point."""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.router import api_router
from app.api.routes.openai import router as openai_router
from app.config.settings import get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.metrics import metrics
from app.db.session import get_database
from app.services.api_server.service import is_loopback_host
from app.services.background.service import get_background_service
from app.services.browser.service import get_browser_service
from app.services.system.db_init import initialize as initialize_database

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
    # Drive the database through initializing -> connected / disconnected /
    # error, applying the schema (Alembic or metadata DDL) and verifying every
    # required table. Failures never crash startup; they are reported honestly.
    # `intllm serve` (CLI / wheel path) gets the same managed-PostgreSQL
    # provisioning as the desktop launcher before schema initialization.
    import asyncio

    from app.services.system.postgres_runtime import ensure_postgres_available

    try:
        runtime = await asyncio.to_thread(ensure_postgres_available, settings)
        logger.info("postgres runtime", extra={"intllm_extra": runtime.as_dict()})
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        logger.warning("postgres runtime provisioning failed: %s", exc)
    report = await initialize_database()
    logger.info(
        "database readiness",
        extra={"intllm_extra": report.as_dict()},
    )
    if report.status != "running":
        logger.warning("database not ready", extra={"intllm_extra": report.as_dict()})

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
        # Technical API schema stays available alongside the INTLLM Docs page.
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS is scoped to the explicitly configured local origins. There is no
    # wildcard fallback: API clients (CLI/SDK) do not use browser CORS, and the
    # packaged UI is same-origin, so an empty list simply allows no cross-origin
    # browser access.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "x-api-key"],
    )

    @app.middleware("http")
    async def request_size_limit(request: Request, call_next):
        """Reject oversized bodies early instead of buffering them."""
        raw_length = request.headers.get("content-length")
        if raw_length is not None:
            try:
                declared = int(raw_length)
            except ValueError:
                declared = max_bytes + 1
            if declared > max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "message": f"Request body exceeds the {max_bytes} byte limit",
                            "type": "validation_error",
                        }
                    },
                )
        return await call_next(request)

    @app.middleware("http")
    async def access_control(request: Request, call_next):
        """Keep internal routes loopback-only; expose only ``/v1`` to the LAN.

        When LAN access is disabled, every non-loopback request is rejected.
        When it is enabled, only the public OpenAI-compatible ``/v1`` API is
        reachable from other machines — management routes (``/api``), the SPA,
        docs and diagnostics stay loopback-only. Authentication for ``/v1`` is
        enforced separately by the API-key dependency.
        """
        client_host = request.client.host if request.client else None
        if not is_loopback_host(client_host):
            path = request.url.path
            is_public_api = path == "/v1" or path.startswith("/v1/")
            if not (is_public_api and get_settings().lan_enabled):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "message": (
                                "This endpoint is only available on the local "
                                "machine."
                            ),
                            "type": "permission_error",
                        }
                    },
                )
        return await call_next(request)

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - started) * 1000.0
        metrics.observe("http.request", duration)
        metrics.increment("http.request.count")
        response.headers["X-Process-Time-Ms"] = f"{duration:.2f}"
        return response

    max_bytes = settings.intllm_max_request_bytes
    install_exception_handlers(app)

    app.include_router(api_router, prefix=settings.intllm_api_prefix)
    app.include_router(openai_router)

    # --- Internal runtime meta (diagnostic; not the application UI) --------
    @app.get(f"{settings.intllm_api_prefix}/meta", tags=["meta"])
    async def meta() -> dict[str, object]:
        """Non-secret runtime description for diagnostics and tooling."""
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
    # /api/*, /v1/*, /docs and the meta routes keep precedence. API paths are
    # explicitly excluded from the SPA fallback: a frontend route can never
    # receive an API-shaped response as its application page.
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

            @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
            async def spa(full_path: str) -> FileResponse | JSONResponse:
                # API/OpenAI paths never fall back to the SPA.
                if full_path.startswith("api/") or full_path.startswith("v1/"):
                    return JSONResponse(
                        status_code=404,
                        content={
                            "error": {
                                "message": f"No such API endpoint: /{full_path}",
                                "type": "not_found_error",
                            }
                        },
                    )
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

            # "/" is part of the SPA catch-all above (full_path=""), so the
            # browser never sees the raw JSON diagnostic as the main page.
            # The JSON contract stays available at /api/meta for tooling.

    else:

        # Development / headless API mode (no static build): the backend root
        # is an explicit diagnostic, never a fake application page.
        @app.get("/", tags=["meta"])
        async def root() -> dict[str, object]:
            return {
                "name": "INTLLM",
                "version": __version__,
                "ui": "not served by this process (build the frontend or run "
                "the desktop app; the UI is served from the backend root when "
                "INTLLM_SERVE_STATIC=1)",
                "api_prefix": settings.intllm_api_prefix,
                "openai_base": "/v1",
                "runtime_endpoint": settings.runtime_endpoint,
            }

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    os.environ.setdefault("INTLLM_EFFECTIVE_PORT", str(settings.intllm_port))
    uvicorn.run(
        "app.main:app",
        # Local mode binds loopback; LAN mode binds the LAN interface.
        host=settings.api_bind_host,
        port=settings.intllm_port,
        log_level=settings.intllm_log_level.lower(),
    )


def launch() -> None:
    """Packaged-application entrypoint (INTLLM.exe)."""
    from app.launcher import main as launcher_main

    raise SystemExit(launcher_main())


if __name__ == "__main__":
    run()
