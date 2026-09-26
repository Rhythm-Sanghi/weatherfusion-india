from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ProviderConfigurationError
from app.db import get_db_session
from app.domain.providers import GeospatialProvider, VerificationProvider
from app.integrations.geospatial.mock_provider import MockGeospatialProvider
from app.integrations.geospatial.postgis_provider import PostgisGeospatialProvider
from app.integrations.verification.ml_provider import MLVerificationProvider
from app.integrations.verification.mock_provider import MockVerificationProvider
from app.integrations.verification.operational_provider import OperationalVerificationProvider


def get_verification_provider(
    session: Annotated[Session | None, Depends(get_db_session)] = None,
) -> VerificationProvider:
    provider = get_settings().verification_provider.lower()
    if provider == "mock":
        return MockVerificationProvider()
    if provider == "operational":
        if session is None:
            raise ProviderConfigurationError(
                "Operational verification provider requires a database session."
            )
        return OperationalVerificationProvider(session, get_settings())
    if provider == "ml":
        if session is None:
            raise ProviderConfigurationError("ML verification provider requires a database session.")
        return MLVerificationProvider(session, get_settings())
    raise ProviderConfigurationError(f"Unsupported verification provider: {provider}")


def get_geospatial_provider(
    session: Annotated[Session | None, Depends(get_db_session)] = None,
) -> GeospatialProvider:
    provider = get_settings().geospatial_provider.lower()
    if provider == "mock":
        return MockGeospatialProvider()
    if provider == "postgis":
        if session is None:
            raise ProviderConfigurationError("PostGIS provider requires a database session.")
        return PostgisGeospatialProvider(session)
    raise ProviderConfigurationError(f"Unsupported geospatial provider: {provider}")
