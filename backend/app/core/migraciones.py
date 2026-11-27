"""Migraciones manuales acumuladas: `create_all()` no altera tablas existentes.

Se ejecutan desde `models/session.py` después de `create_all()`. Las sentencias
propias de PostgreSQL se aplican solo en ese dialecto para que las verificaciones
con SQLite sigan funcionando.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Índices de apoyo (principalmente claves foráneas) que `create_all()` no crea.
# Los nombres son estables para que `IF NOT EXISTS` baste en arranques repetidos.
DDL_INDICES = (
  "CREATE INDEX IF NOT EXISTS ix_asignaturas_docentes_id_docente "
  "ON asignaturas_docentes (id_docente)",
  "CREATE INDEX IF NOT EXISTS ix_secciones_id_docente_titular "
  "ON secciones (id_docente_titular)",
  "CREATE INDEX IF NOT EXISTS ix_estudiantes_id_seccion ON estudiantes (id_seccion)",
  "CREATE INDEX IF NOT EXISTS ix_estudiantes_id_representante "
  "ON estudiantes (id_representante)",
  "CREATE INDEX IF NOT EXISTS ix_estudiantes_vigentes "
  "ON estudiantes (id_seccion) "
  "WHERE fecha_eliminacion IS NULL AND fecha_egreso IS NULL",
  "CREATE INDEX IF NOT EXISTS ix_reportes_id_estudiante ON reportes (id_estudiante)",
  "CREATE INDEX IF NOT EXISTS ix_reportes_id_usuario ON reportes (id_usuario)",
  "CREATE INDEX IF NOT EXISTS ix_reportes_id_docente ON reportes (id_docente)",
  "CREATE INDEX IF NOT EXISTS ix_reportes_id_asignatura ON reportes (id_asignatura)",
  "CREATE INDEX IF NOT EXISTS ix_pases_id_estudiante ON pases (id_estudiante)",
  "CREATE INDEX IF NOT EXISTS ix_pases_id_usuario ON pases (id_usuario)",
  "CREATE INDEX IF NOT EXISTS ix_pases_id_docente ON pases (id_docente)",
  "CREATE INDEX IF NOT EXISTS ix_pases_id_asignatura ON pases (id_asignatura)",
  "CREATE INDEX IF NOT EXISTS ix_horarios_id_seccion ON horarios (id_seccion)",
  "CREATE INDEX IF NOT EXISTS ix_horarios_id_bloque ON horarios (id_bloque)",
  "CREATE INDEX IF NOT EXISTS ix_horarios_id_asignatura ON horarios (id_asignatura)",
  "CREATE INDEX IF NOT EXISTS ix_horarios_id_docente ON horarios (id_docente)",
  "CREATE INDEX IF NOT EXISTS ix_auditorias_usuario_id ON auditorias (usuario_id)",
  "CREATE INDEX IF NOT EXISTS ix_documentos_generados_id_grado "
  "ON documentos_generados (id_grado)",
  "CREATE INDEX IF NOT EXISTS ix_documentos_generados_id_seccion "
  "ON documentos_generados (id_seccion)",
  "CREATE INDEX IF NOT EXISTS ix_documentos_generados_generado_por "
  "ON documentos_generados (generado_por)",
  "CREATE INDEX IF NOT EXISTS ix_tokens_revocados_usuario_id "
  "ON tokens_revocados (usuario_id)",
  "CREATE INDEX IF NOT EXISTS ix_documentos_firmas_documento_id "
  "ON documentos_firmas (documento_id)",
)


def _es_postgres(engine: Engine) -> bool:
  """Indica si el engine usa PostgreSQL."""
  return engine.dialect.name == "postgresql"


def preparar_extensiones(engine: Engine) -> None:
  """Instala las extensiones que necesita PostgreSQL."""
  if not _es_postgres(engine):
    return

  with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))


def _columnas(engine: Engine, tabla: str) -> set[str]:
  """Devuelve los nombres de las columnas existentes en una tabla."""
  return {columna["name"] for columna in inspect(engine).get_columns(tabla)}


def _agregar_columna(
  engine: Engine,
  tabla: str,
  columna: str,
  ddl_postgres: str,
  ddl_sqlite: str,
) -> None:
  """Agrega la columna solo si la tabla todavía no la tiene."""
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
      conn.execute(text("ALTER TYPE tipodocumento ADD VALUE IF NOT EXISTS 'docentes'"))

  _agregar_columna(
    engine,
    "reportes",
    "id_asignatura",
    "ALTER TABLE reportes "
    "ADD COLUMN IF NOT EXISTS id_asignatura INTEGER REFERENCES asignaturas(id)",
    "ALTER TABLE reportes ADD COLUMN id_asignatura INTEGER REFERENCES asignaturas(id)",
  )

  with engine.begin() as conn:
    for ddl in DDL_INDICES:
      conn.execute(text(ddl))
