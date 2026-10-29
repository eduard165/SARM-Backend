from collections.abc import Generator
from typing import Any
import psycopg
from psycopg.rows import dict_row
from app.core.config import get_settings


def get_db() -> Generator[Any, None, None]:
    settings = get_settings()
    settings.validate_database()
    # El usuario SQL del backend puede ignorar RLS: las rutas siempre deben
    # verificar autenticacion, rol y pertenencia al negocio ANTES de consultar.
    conn = psycopg.connect(
        settings.database_url,
        connect_timeout=settings.db_connect_timeout,
        sslmode='require',
        row_factory=dict_row,
    )
    try:
        yield conn
    finally:
        conn.close()
