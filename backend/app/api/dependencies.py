from app.core.config import get_settings
from app.core.errors import ProviderConfigurationError
from app.domain.providers import GeospatialProvider, VerificationProvider
from app.integrations.geospatial.mock_provider import MockGeospatialProvider
from app.integrations.verification.mock_provider import MockVerificationProvider


def get_verification_provider() -> VerificationProvider:
    provider = get_settings().verification_provider.lower()
    if provider == "mock":
        return MockVerificationProvider()
    raise ProviderConfigurationError(f"Unsupported verification provider: {provider}")


def get_geospatial_provider() -> GeospatialProvider:
    provider = get_settings().geospatial_provider.lower()
    if provider == "mock":
        return MockGeospatialProvider()
    raise ProviderConfigurationError(f"Unsupported geospatial provider: {provider}")
