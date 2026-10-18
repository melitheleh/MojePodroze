"""Uruchamianie migracji Alembica z kodu (przy starcie aplikacji i w testach)."""

from alembic import command
from alembic.config import Config

from app.config import BACKEND_DIR
from app.db.session import ensure_sqlite_directory


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    # ConfigParser traktuje „%” specjalnie, dlatego trzeba je podwoić.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    # Nie nadpisuj konfiguracji logowania uvicorna/pytesta.
    config.attributes["configure_logger"] = False
    return config


def upgrade_to_head(database_url: str) -> None:
    ensure_sqlite_directory(database_url)
    command.upgrade(alembic_config(database_url), "head")
