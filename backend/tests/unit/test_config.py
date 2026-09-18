from app.core.config import Settings


def test_settings_can_be_instantiated_for_test_environment() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://example:example@localhost:5432/example",
        cors_origins=["http://testserver"],
    )

    assert settings.app_env == "test"
    assert settings.cors_origins == ["http://testserver"]
