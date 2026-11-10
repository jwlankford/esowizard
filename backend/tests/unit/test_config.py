from app.core.config import Settings


def test_database_urls_are_translated_for_each_driver():
    settings = Settings(
        database_url="postgresql://user:pw@ep-x-pooler.neon.tech/db?sslmode=require&channel_binding=require"
    )
    assert settings.async_database_url == (
        "postgresql+asyncpg://user:pw@ep-x-pooler.neon.tech/db?ssl=require"
    )
    assert settings.sync_database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in settings.sync_database_url


def test_direct_url_is_used_for_migrations_only():
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@pooler/db",
        database_direct_url="postgresql://u:p@direct/db?sslmode=require",
    )
    assert "pooler" in settings.async_database_url
    assert "direct" in settings.sync_database_url


def test_chunk_overlap_must_be_smaller_than_chunk_size():
    import pytest

    with pytest.raises(ValueError):
        Settings(chunk_size=200, chunk_overlap=200)


def test_verification_modes_are_preserved_for_asyncpg():
    for mode in ("verify-ca", "verify-full"):
        settings = Settings(database_url=f"postgresql://u:p@host/db?sslmode={mode}")
        assert f"ssl={mode}" in settings.async_database_url
