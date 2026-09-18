from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass(slots=True)
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int = 400


class ProviderConfigurationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(code="provider_configuration_error", message=message, status_code=500)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
