"""Migraciones manuales acumuladas: `create_all()` no altera tablas existentes.

Se ejecutan desde `models/session.py` después de `create_all()`. Las sentencias
propias de PostgreSQL se aplican solo en ese dialecto para que las verificaciones
con SQLite sigan funcionando.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _es_postgres(engine: Engine) -> bool:
  return engine.dialect.name == "postgresql"


def preparar_extensiones(engine: Engine) -> None:
  """Instala las extensiones que necesita PostgreSQL."""
  if not _es_postgres(engine):
    return

  with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))


def _columnas(engine: Engine, tabla: str) -> set[str]:
  return {columna["name"] for columna in inspect(engine).get_columns(tabla)}


def _agregar_columna(
  engine: Engine,
  tabla: str,
  columna: str,
  ddl_postgres: str,
  ddl_sqlite: str,
) -> None:
  if columna in _columnas(engine, tabla):
    return

  ddl = ddl_postgres if _es_postgres(engine) else ddl_sqlite
  with engine.begin() as conn:
    conn.execute(text(ddl))


def aplicar_migraciones(engine: Engine) -> None:
  """Aplica los `ALTER`/`CREATE INDEX` acumulados de forma idempotente."""
  _agregar_columna(
    engine,
    "usuarios",
    "version_tokens",
    "ALTER TABLE usuarios "
    "ADD COLUMN IF NOT EXISTS version_tokens INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE usuarios ADD COLUMN version_tokens INTEGER NOT NULL DEFAULT 0",
  )

  if _es_postgres(engine):
    with engine.begin() as conn:
      conn.execute(
        text("ALTER TYPE tipodocumento ADD VALUE IF NOT EXISTS 'docentes'")
      )

  _agregar_columna(
    engine,
    "reportes",
    "id_asignatura",
    "ALTER TABLE reportes "
    "ADD COLUMN IF NOT EXISTS id_asignatura INTEGER REFERENCES asignaturas(id)",
    "ALTER TABLE reportes "
    "ADD COLUMN id_asignatura INTEGER REFERENCES asignaturas(id)",
  )

  with engine.begin() as conn:
    conn.execute(
      text(
        "CREATE INDEX IF NOT EXISTS ix_reportes_id_asignatura "
        "ON reportes (id_asignatura)"
      )
    )
