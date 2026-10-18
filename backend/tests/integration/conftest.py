"""Fixtury testów integracyjnych.

* Każdy test dostaje własną, świeżą bazę SQLite w katalogu tymczasowym. Schemat powstaje przez
  prawdziwe migracje Alembica (raz na sesję, do pliku-wzorca), a potem plik jest kopiowany —
  to szybkie i testuje migracje razem z API.
* Zewnętrzne API (Open-Meteo, NBP) są podmienione atrapami, a „dzisiejsza” data jest zamrożona.
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_rates_client, get_today, get_weather_client
from app.config import Settings
from app.db.migrations import upgrade_to_head
from app.main import create_app
from tests.integration.fakes import FakeRatesClient, FakeWeatherClient
from tests.integration.helpers import FROZEN_TODAY, MAX_UPLOAD_BYTES, ApiUser, register_user


@pytest.fixture(scope="session")
def migrated_db_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("db-template") / "template.db"
    upgrade_to_head(f"sqlite:///{path.as_posix()}")
    return path


@pytest.fixture
def settings(tmp_path: Path, migrated_db_template: Path) -> Settings:
    db_path = tmp_path / "test.db"
    shutil.copyfile(migrated_db_template, db_path)
    return Settings(
        database_url=f"sqlite:///{db_path.as_posix()}",
        upload_dir=tmp_path / "uploads",
        max_upload_bytes=MAX_UPLOAD_BYTES,
        auto_migrate=False,
    )


@pytest.fixture
def fake_weather() -> FakeWeatherClient:
    return FakeWeatherClient()


@pytest.fixture
def fake_rates() -> FakeRatesClient:
    return FakeRatesClient()


@pytest.fixture
def app(
    settings: Settings, fake_weather: FakeWeatherClient, fake_rates: FakeRatesClient
) -> FastAPI:
    application = create_app(settings)
    application.dependency_overrides[get_weather_client] = lambda: fake_weather
    application.dependency_overrides[get_rates_client] = lambda: fake_rates
    application.dependency_overrides[get_today] = lambda: FROZEN_TODAY
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user(client: TestClient) -> ApiUser:
    return register_user(client, "ania")


@pytest.fixture
def other_user(client: TestClient) -> ApiUser:
    return register_user(client, "bartek")
