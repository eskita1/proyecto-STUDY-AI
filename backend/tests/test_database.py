import importlib

from sqlalchemy.orm import Session

from app.config import Settings, get_settings

DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/studyai"


def test_settings_load_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)

    settings = Settings()

    assert settings.database_url == DATABASE_URL


def test_database_session_factory_does_not_connect_eagerly(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    get_settings.cache_clear()
    database = importlib.import_module("app.database.db")

    session = database.SessionLocal()

    assert isinstance(session, Session)
    assert session.bind is database.engine

    session.close()
    database.engine.dispose()
    get_settings.cache_clear()
