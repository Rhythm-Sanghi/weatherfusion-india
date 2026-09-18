import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings)
    logger = logging.getLogger("weatherfusion.lifecycle")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("application_startup environment=%s", runtime_settings.app_env)
        yield
        logger.info("application_shutdown")

    app = FastAPI(
        title=runtime_settings.app_name,
        debug=runtime_settings.debug,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
    )
    install_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
