import logging

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure concise process-wide logging without exposing runtime secrets."""

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
