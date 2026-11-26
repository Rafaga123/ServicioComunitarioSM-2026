from sqlmodel import Session, SQLModel, create_engine, text

from app.core.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, DEBUG
from app.core.semilla import sembrar_datos

# Construcción de la URL corregida para PostgreSQL
sql_url = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(sql_url, echo=DEBUG)


def create_db_tables():
  with engine.begin() as conn:
    # Instalando las extensiones en lab base de datos
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

  SQLModel.metadata.create_all(engine)

  # Migración no destructiva: `create_all()` no altera enums existentes.
  # Este valor es necesario para registrar PDFs de docentes.
  with engine.begin() as conn:
    conn.execute(
      text(
        "ALTER TABLE usuarios "
        "ADD COLUMN IF NOT EXISTS version_tokens INTEGER NOT NULL DEFAULT 0"
      )
    )
    conn.execute(text("ALTER TYPE tipodocumento ADD VALUE IF NOT EXISTS 'docentes'"))


def inicializar_base_datos() -> tuple[int, int]:
  """Crea el esquema y carga la semilla institucional si hace falta."""
  create_db_tables()

  with Session(engine) as session:
    return sembrar_datos(session)


def get_session():
  with Session(engine) as session:
    yield session
