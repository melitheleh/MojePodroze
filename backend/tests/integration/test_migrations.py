"""Migracje Alembica: zgodność z modelami ORM, cofanie i dane słownikowe."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.config import Settings
from app.db.base import Base
from app.db.migrations import alembic_config, upgrade_to_head
from app.main import create_app


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_migrations_match_orm_models(tmp_path: Path) -> None:
    """Gdy ktoś zmieni model i zapomni o migracji, ten test to wykryje."""
    url = sqlite_url(tmp_path / "check.db")
    upgrade_to_head(url)
    engine = create_engine(url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []


def test_downgrade_to_base_and_upgrade_again(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path / "roundtrip.db")
    upgrade_to_head(url)
    command.downgrade(alembic_config(url), "base")
    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
    upgrade_to_head(url)
    engine = create_engine(url)
    assert "trips" in inspect(engine).get_table_names()
    engine.dispose()


def test_dictionaries_are_seeded_by_migration(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path / "seed.db")
    upgrade_to_head(url)
    engine = create_engine(url)
    with engine.connect() as connection:
        counts = {
            table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()  # noqa: S608
            for table in ("trip_characters", "transport_means", "expense_categories")
        }
    engine.dispose()
    assert counts == {"trip_characters": 6, "transport_means": 8, "expense_categories": 6}


def test_app_runs_migrations_on_startup(tmp_path: Path) -> None:
    settings = Settings(
        database_url=sqlite_url(tmp_path / "data" / "app.db"),
        upload_dir=tmp_path / "uploads",
        auto_migrate=True,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/dictionaries").json()["trip_characters"]
    assert (tmp_path / "data" / "app.db").exists()
    assert (tmp_path / "uploads").is_dir()
