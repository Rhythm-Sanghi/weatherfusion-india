from app.api.dependencies import get_geospatial_provider, get_verification_provider
from app.integrations.geospatial.mock_provider import MockGeospatialProvider
from app.integrations.verification.mock_provider import MockVerificationProvider


def test_provider_dependencies_resolve_configured_mock_implementations() -> None:
    assert isinstance(get_verification_provider(), MockVerificationProvider)
    assert isinstance(get_geospatial_provider(), MockGeospatialProvider)
